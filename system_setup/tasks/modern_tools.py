"""Modern CLI tools installation task."""

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from system_setup.config import Config
from system_setup.logger import get_logger
from system_setup.packages.factory import get_package_manager
from system_setup.platform import Platform
from system_setup.state import StateManager


# Core modern CLI tools that replace traditional ones
MODERN_CLI_TOOLS = {
    # File operations
    "eza": {
        "replaces": "ls",
        "description": "Modern ls replacement with git integration",
        "package": "eza",
    },
    "bat": {
        "replaces": "cat",
        "description": "Cat clone with syntax highlighting",
        "package": "bat",
    },
    "fd": {
        "replaces": "find",
        "description": "Fast and user-friendly find alternative",
        "package": "fd",
    },
    "ripgrep": {
        "replaces": "grep",
        "description": "Fast recursive grep alternative",
        "package": "ripgrep",
    },
    "sd": {
        "replaces": "sed",
        "description": "Intuitive find & replace CLI",
        "package": "sd",
    },
    "dust": {
        "replaces": "du",
        "description": "More intuitive version of du",
        "package": "dust",
    },
    "duf": {
        "replaces": "df",
        "description": "Better disk usage/free utility",
        "package": "duf",
    },
    "procs": {
        "replaces": "ps",
        "description": "Modern replacement for ps",
        "package": "procs",
    },
    "bottom": {
        "replaces": "top/htop",
        "description": "Cross-platform graphical process/system monitor",
        "package": "bottom",
    },
    "btop": {
        "replaces": "top/htop",
        "description": "Beautiful resource monitor",
        "package": "btop",
    },
    "zoxide": {
        "replaces": "cd",
        "description": "Smarter cd command with learning",
        "package": "zoxide",
    },
    "fzf": {
        "replaces": "ctrl+r",
        "description": "Fuzzy finder for command line",
        "package": "fzf",
    },
    "delta": {
        "replaces": "diff",
        "description": "Syntax-highlighting pager for git/diff",
        "package": "git-delta",
    },
    "jq": {
        "replaces": "grep (for JSON)",
        "description": "Command-line JSON processor",
        "package": "jq",
    },
    "yq": {
        "replaces": "grep (for YAML)",
        "description": "Command-line YAML/XML processor",
        "package": "yq",
    },
}

# Development tools
DEV_TOOLS = {
    "mise": {
        "description": "Fast, polyglot version manager (asdf alternative)",
        "package": "mise",
    },
    "starship": {
        "description": "Cross-shell prompt",
        "package": "starship",
    },
    "lazygit": {
        "description": "Terminal UI for git",
        "package": "lazygit",
    },
    "lazydocker": {
        "description": "Terminal UI for docker",
        "package": "lazydocker",
    },
    "tokei": {
        "description": "Count lines of code",
        "package": "tokei",
    },
    "hyperfine": {
        "description": "Command-line benchmarking tool",
        "package": "hyperfine",
    },
    "tealdeer": {
        "description": "Fast tldr client",
        "package": "tealdeer",
    },
}

# AUR-only packages (Arch Linux)
AUR_PACKAGES = [
    "lazydocker",
]


class ModernToolsTask:
    """Installs modern CLI tools.

    Replaces traditional Unix tools with modern, Rust-based alternatives
    that are faster and more user-friendly.
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
        Initialize modern tools task.

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

    def run(self) -> bool:
        """
        Execute modern tools installation task.

        Returns:
            True if successful
        """
        if self.state.is_complete('modern_tools_installed'):
            self.logger.info("Modern tools already installed (skipping)")
            return True

        self.logger.section("Modern CLI Tools Installation")

        # Step 1: Install core modern tools
        if not self._install_core_tools():
            return False

        # Step 2: Install dev tools
        if not self._install_dev_tools():
            return False

        # Step 3: Configure mise
        if not self._configure_mise():
            return False

        # Step 4: Configure starship
        if not self._configure_starship():
            return False

        # Step 5: Configure git delta
        if not self._configure_delta():
            return False

        # Step 6: Update tldr cache
        if not self._update_tldr():
            return False

        self.state.mark_complete('modern_tools_installed')
        self.logger.success("Modern tools installation complete")
        return True

    def _install_core_tools(self) -> bool:
        """Install core modern CLI tools."""
        self.logger.info("Installing core modern tools...")

        pkg_manager = get_package_manager(self.platform, self.dry_run)
        if not pkg_manager:
            self.logger.error("No package manager available")
            return False

        # Collect packages to install
        packages = []
        for tool, info in MODERN_CLI_TOOLS.items():
            pkg_name = info["package"]
            if not shutil.which(tool) and pkg_name not in AUR_PACKAGES:
                packages.append(pkg_name)
                self.logger.info(f"  {tool}: {info['description']} (replaces {info['replaces']})")

        if not packages:
            self.logger.info("All core tools already installed")
            return True

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would install: {', '.join(packages)}")
            return True

        return pkg_manager.install(packages)

    def _install_dev_tools(self) -> bool:
        """Install development tools."""
        self.logger.info("Installing development tools...")

        pkg_manager = get_package_manager(self.platform, self.dry_run)
        if not pkg_manager:
            self.logger.error("No package manager available")
            return False

        # Collect packages to install
        packages = []
        aur_packages = []

        for tool, info in DEV_TOOLS.items():
            pkg_name = info["package"]
            if not shutil.which(tool):
                if pkg_name in AUR_PACKAGES:
                    aur_packages.append(pkg_name)
                else:
                    packages.append(pkg_name)
                self.logger.info(f"  {tool}: {info['description']}")

        if not packages and not aur_packages:
            self.logger.info("All dev tools already installed")
            return True

        if self.dry_run:
            if packages:
                self.logger.info(f"[DRY RUN] Would install: {', '.join(packages)}")
            if aur_packages:
                self.logger.info(f"[DRY RUN] Would install from AUR: {', '.join(aur_packages)}")
            return True

        success = True
        if packages:
            if not pkg_manager.install(packages):
                success = False

        # Install AUR packages if paru is available
        if aur_packages and hasattr(pkg_manager, 'install_aur'):
            if not pkg_manager.install_aur(aur_packages):
                self.logger.warning("Some AUR packages failed to install")

        return success

    def _configure_mise(self) -> bool:
        """Configure mise version manager."""
        if not shutil.which('mise'):
            self.logger.info("mise not installed, skipping configuration")
            return True

        self.logger.info("Configuring mise...")

        config_path = Path.home() / ".config" / "mise" / "config.toml"

        if config_path.exists():
            self.logger.info("mise config already exists")
            return True

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would create {config_path}")
            return True

        config_content = '''# mise configuration
# https://mise.jdx.dev/

[settings]
# Always use the latest version as default
legacy_version_file = true
always_keep_download = false
always_keep_install = false
plugin_autoupdate_last_check_duration = "7d"

# Trusted directories for auto-installing tools
trusted_config_paths = ["~/.config/mise"]

# Default tools to have available globally
[tools]
# python = "latest"
# node = "lts"
# go = "latest"
'''

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(config_content)
            self.logger.success("mise configured")
            return True
        except Exception as e:
            self.logger.error(f"Failed to configure mise: {e}")
            return False

    def _configure_starship(self) -> bool:
        """Configure starship prompt."""
        if not shutil.which('starship'):
            self.logger.info("starship not installed, skipping configuration")
            return True

        self.logger.info("Configuring starship...")

        config_path = Path.home() / ".config" / "starship.toml"

        if config_path.exists():
            self.logger.info("starship config already exists")
            return True

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would create {config_path}")
            return True

        config_content = '''# Starship prompt configuration
# https://starship.rs/config/

# Minimal timeout for responsiveness
command_timeout = 500

# Prompt format - clean and informative
format = """
$directory$git_branch$git_status$python$nodejs$rust$golang$cmd_duration
$character"""

[character]
success_symbol = "[>](bold green)"
error_symbol = "[>](bold red)"

[directory]
truncation_length = 3
truncate_to_repo = true
style = "bold cyan"

[git_branch]
symbol = " "
style = "bold purple"

[git_status]
style = "bold yellow"
conflicted = "!"
ahead = "^"
behind = "v"
diverged = "^v"
modified = "*"
staged = "+"
untracked = "?"

[python]
symbol = " "
style = "bold yellow"

[nodejs]
symbol = " "
style = "bold green"

[rust]
symbol = " "
style = "bold red"

[golang]
symbol = " "
style = "bold cyan"

[cmd_duration]
min_time = 2_000
style = "bold yellow"
format = "[$duration]($style) "
'''

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(config_content)
            self.logger.success("starship configured")
            return True
        except Exception as e:
            self.logger.error(f"Failed to configure starship: {e}")
            return False

    def _configure_delta(self) -> bool:
        """Configure git-delta as git pager."""
        if not shutil.which('delta'):
            self.logger.info("delta not installed, skipping configuration")
            return True

        self.logger.info("Configuring git-delta...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would configure git to use delta")
            return True

        git_configs = [
            ("core.pager", "delta"),
            ("interactive.diffFilter", "delta --color-only"),
            ("delta.navigate", "true"),
            ("delta.light", "false"),
            ("delta.side-by-side", "true"),
            ("delta.line-numbers", "true"),
            ("merge.conflictStyle", "diff3"),
            ("diff.colorMoved", "default"),
        ]

        for key, value in git_configs:
            try:
                subprocess.run(
                    ['git', 'config', '--global', key, value],
                    check=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to set git config {key}: {e}")

        self.logger.success("git-delta configured")
        return True

    def _update_tldr(self) -> bool:
        """Update tealdeer/tldr cache."""
        if not shutil.which('tldr'):
            self.logger.info("tldr not installed, skipping cache update")
            return True

        self.logger.info("Updating tldr cache...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would update tldr cache")
            return True

        try:
            subprocess.run(
                ['tldr', '--update'],
                check=True,
                capture_output=True,
            )
            self.logger.success("tldr cache updated")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to update tldr cache: {e}")
            return True  # Non-fatal

    def get_tool_info(self, tool: str) -> Optional[Dict]:
        """
        Get information about a specific tool.

        Args:
            tool: Tool name

        Returns:
            Tool info dict or None
        """
        if tool in MODERN_CLI_TOOLS:
            return MODERN_CLI_TOOLS[tool]
        if tool in DEV_TOOLS:
            return DEV_TOOLS[tool]
        return None

    def list_installed(self) -> List[str]:
        """
        Get list of installed modern tools.

        Returns:
            List of installed tool names
        """
        installed = []
        for tool in {**MODERN_CLI_TOOLS, **DEV_TOOLS}:
            if shutil.which(tool):
                installed.append(tool)
        return installed

    def list_available(self) -> List[str]:
        """
        Get list of tools not yet installed.

        Returns:
            List of available tool names
        """
        available = []
        for tool in {**MODERN_CLI_TOOLS, **DEV_TOOLS}:
            if not shutil.which(tool):
                available.append(tool)
        return available
