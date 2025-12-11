"""Fish shell configuration task."""

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from system_setup.config import Config
from system_setup.logger import get_logger
from system_setup.packages.factory import get_package_manager
from system_setup.platform import Platform
from system_setup.state import StateManager


# Fish plugins to install via Fisher
FISHER_PLUGINS = [
    "jorgebucaran/fisher",  # Plugin manager itself
    "IlanCosman/tide@v6",  # Tide prompt
    "PatrickF1/fzf.fish",  # Fzf integration
    "jethrokuan/z",  # Directory jumping
]

# Abbreviations to set up
FISH_ABBREVIATIONS = [
    ("g", "git"),
    ("ga", "git add"),
    ("gc", "git commit"),
    ("gco", "git checkout"),
    ("gd", "git diff"),
    ("gl", "git log --oneline"),
    ("gp", "git push"),
    ("gpl", "git pull"),
    ("gs", "git status"),
    ("lg", "lazygit"),
    ("v", "hx"),  # Helix editor
    ("cat", "bat"),
    ("ls", "eza"),
    ("ll", "eza -la"),
    ("la", "eza -a"),
    ("tree", "eza --tree"),
]


class FishTask:
    """Manages Fish shell configuration.

    Sets up Fish shell with:
    - Fisher plugin manager
    - Tide prompt (beautiful, modern prompt)
    - Useful plugins (fzf, z, etc.)
    - Abbreviations for common commands
    - Integration with modern tools (eza, bat, etc.)
    """

    def __init__(
        self,
        config: Config,
        state: StateManager,
        platform: Platform,
        dry_run: bool = False,
        auto_yes: bool = False,
    ) -> None:
        """
        Initialize Fish shell task.

        Args:
            config: Configuration instance
            state: State manager instance
            platform: Platform instance
            dry_run: If True, don't actually make changes
            auto_yes: If True, automatically answer yes to prompts
        """
        self.config = config
        self.state = state
        self.platform = platform
        self.dry_run = dry_run
        self.auto_yes = auto_yes
        self.logger = get_logger()
        self.config_dir = Path.home() / ".config" / "fish"

    def run(self) -> bool:
        """
        Execute Fish shell configuration task.

        Returns:
            True if successful
        """
        if self.state.is_complete('fish_configured'):
            self.logger.info("Fish shell already configured (skipping)")
            return True

        self.logger.section("Fish Shell Configuration")

        # Step 1: Ensure Fish is installed
        if not self._ensure_fish_installed():
            return False

        # Step 2: Set Fish as default shell
        if not self._set_default_shell():
            return False

        # Step 3: Install Fisher plugin manager
        if not self._install_fisher():
            return False

        # Step 4: Install plugins (including Tide)
        if not self._install_plugins():
            return False

        # Step 5: Create base config
        if not self._create_config():
            return False

        # Step 6: Set up abbreviations
        if not self._setup_abbreviations():
            return False

        self.state.mark_complete('fish_configured')
        self.logger.success("Fish shell configuration complete")
        self.logger.info("Run 'tide configure' to customize your prompt")
        return True

    def _ensure_fish_installed(self) -> bool:
        """Ensure Fish shell is installed."""
        if shutil.which('fish'):
            self.logger.info("Fish shell is already installed")
            return True

        self.logger.info("Installing Fish shell...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would install fish")
            return True

        pkg_manager = get_package_manager(self.platform, self.dry_run)
        if not pkg_manager:
            self.logger.error("No package manager available")
            return False

        if pkg_manager.install(['fish']):
            self.logger.success("Fish shell installed")
            return True
        else:
            self.logger.error("Failed to install Fish shell")
            return False

    def _set_default_shell(self) -> bool:
        """Set Fish as the default shell."""
        fish_path = shutil.which('fish')
        if not fish_path:
            fish_path = "/usr/bin/fish"

        # Check if already default
        import os
        current_shell = os.environ.get('SHELL', '')
        if 'fish' in current_shell:
            self.logger.info("Fish is already the default shell")
            return True

        if not self.auto_yes:
            response = input(f"Set {fish_path} as default shell? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipping shell change")
                return True

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would set {fish_path} as default shell")
            return True

        # Add to /etc/shells if needed (Linux)
        if self.platform.is_linux:
            try:
                with open('/etc/shells', 'r') as f:
                    shells = f.read()
                if fish_path not in shells:
                    self.logger.info(f"Adding {fish_path} to /etc/shells...")
                    subprocess.run(
                        f'echo "{fish_path}" | sudo tee -a /etc/shells',
                        shell=True,
                        check=True,
                        capture_output=True,
                    )
            except Exception as e:
                self.logger.warning(f"Could not modify /etc/shells: {e}")

        # Change default shell
        try:
            self.logger.info(f"Changing default shell to {fish_path}...")
            subprocess.run(['chsh', '-s', fish_path], check=True)
            self.logger.success("Default shell changed to Fish")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to change shell: {e}")
            return False

    def _install_fisher(self) -> bool:
        """Install Fisher plugin manager."""
        # Check if Fisher is already installed
        functions_dir = self.config_dir / "functions"
        fisher_file = functions_dir / "fisher.fish"

        if fisher_file.exists():
            self.logger.info("Fisher is already installed")
            return True

        self.logger.info("Installing Fisher plugin manager...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would install Fisher")
            return True

        try:
            # Install Fisher using the official method
            install_cmd = (
                "curl -sL https://raw.githubusercontent.com/jorgebucaran/fisher/main/functions/fisher.fish | "
                "source && fisher install jorgebucaran/fisher"
            )
            subprocess.run(
                ['fish', '-c', install_cmd],
                check=True,
            )
            self.logger.success("Fisher installed")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install Fisher: {e}")
            return False

    def _install_plugins(self) -> bool:
        """Install Fish plugins via Fisher."""
        self.logger.info("Installing Fish plugins...")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would install plugins: {', '.join(FISHER_PLUGINS)}")
            return True

        for plugin in FISHER_PLUGINS:
            # Skip Fisher itself (already installed)
            if plugin == "jorgebucaran/fisher":
                continue

            try:
                self.logger.info(f"  Installing {plugin}...")
                subprocess.run(
                    ['fish', '-c', f'fisher install {plugin}'],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to install {plugin}: {e}")
                # Continue with other plugins

        self.logger.success("Plugins installed")
        return True

    def _create_config(self) -> bool:
        """Create Fish configuration file."""
        config_file = self.config_dir / "config.fish"

        if config_file.exists():
            self.logger.info("Fish config already exists, preserving")
            return True

        self.logger.info("Creating Fish configuration...")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would create {config_file}")
            return True

        config_content = self._generate_config()

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            config_file.write_text(config_content)
            self.logger.success(f"Created {config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create config: {e}")
            return False

    def _generate_config(self) -> str:
        """Generate Fish shell configuration."""
        return '''# Fish shell configuration
# Generated by system-setup

# Disable greeting
set -g fish_greeting

# Environment variables
set -gx EDITOR hx
set -gx VISUAL hx
set -gx PAGER less

# XDG Base Directory
set -gx XDG_CONFIG_HOME $HOME/.config
set -gx XDG_DATA_HOME $HOME/.local/share
set -gx XDG_CACHE_HOME $HOME/.cache
set -gx XDG_STATE_HOME $HOME/.local/state

# Path additions
fish_add_path $HOME/.local/bin
fish_add_path $HOME/.cargo/bin

# Mise (asdf-compatible version manager)
if command -q mise
    mise activate fish | source
end

# Zoxide (smart cd)
if command -q zoxide
    zoxide init fish | source
end

# FZF configuration
set -gx FZF_DEFAULT_OPTS "--height 40% --layout=reverse --border --preview 'bat --color=always --style=numbers --line-range=:500 {}'"

# Use eza instead of ls (if available)
if command -q eza
    alias ls='eza'
    alias ll='eza -la --git'
    alias la='eza -a'
    alias tree='eza --tree'
end

# Use bat instead of cat (if available)
if command -q bat
    alias cat='bat --paging=never'
end

# Wayland/Hyprland specifics
if test "$XDG_SESSION_TYPE" = "wayland"
    set -gx MOZ_ENABLE_WAYLAND 1
    set -gx QT_QPA_PLATFORM wayland
end

# Useful functions
function mkcd -d "Create directory and cd into it"
    mkdir -p $argv[1] && cd $argv[1]
end

function extract -d "Extract common archive formats"
    switch $argv[1]
        case '*.tar.bz2'
            tar xjf $argv[1]
        case '*.tar.gz'
            tar xzf $argv[1]
        case '*.tar.xz'
            tar xJf $argv[1]
        case '*.bz2'
            bunzip2 $argv[1]
        case '*.gz'
            gunzip $argv[1]
        case '*.tar'
            tar xf $argv[1]
        case '*.zip'
            unzip $argv[1]
        case '*.7z'
            7z x $argv[1]
        case '*'
            echo "Unknown archive format: $argv[1]"
    end
end

# Git shortcuts
function gcom -d "Git commit with message"
    git commit -m "$argv"
end

function gacp -d "Git add, commit, push"
    git add -A && git commit -m "$argv" && git push
end
'''

    def _setup_abbreviations(self) -> bool:
        """Set up Fish abbreviations."""
        self.logger.info("Setting up abbreviations...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would set up abbreviations")
            return True

        for abbr, expansion in FISH_ABBREVIATIONS:
            try:
                subprocess.run(
                    ['fish', '-c', f'abbr -a {abbr} {expansion}'],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError:
                # Non-fatal - abbreviation might already exist
                pass

        self.logger.success("Abbreviations configured")
        return True

    def install_additional_plugin(self, plugin: str) -> bool:
        """
        Install an additional Fisher plugin.

        Args:
            plugin: Plugin to install (e.g., "user/repo")

        Returns:
            True if successful
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would install plugin: {plugin}")
            return True

        try:
            subprocess.run(
                ['fish', '-c', f'fisher install {plugin}'],
                check=True,
            )
            self.logger.success(f"Installed plugin: {plugin}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install {plugin}: {e}")
            return False

    def configure_tide(self) -> bool:
        """
        Run Tide configuration wizard.

        Returns:
            True (always, as this is interactive)
        """
        if self.dry_run:
            self.logger.info("[DRY RUN] Would run tide configure")
            return True

        self.logger.info("Running Tide configuration wizard...")
        self.logger.info("This is interactive - follow the prompts in your terminal")

        try:
            subprocess.run(['fish', '-c', 'tide configure'], check=True)
            return True
        except subprocess.CalledProcessError:
            self.logger.warning("Tide configuration cancelled or failed")
            return True  # Non-fatal
