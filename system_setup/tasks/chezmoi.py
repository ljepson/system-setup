"""Chezmoi dotfiles management task."""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from system_setup.config import Config
from system_setup.logger import get_logger
from system_setup.packages.factory import get_package_manager
from system_setup.platform import Platform
from system_setup.state import StateManager


class ChezmoiTask:
    """Manages dotfiles using chezmoi.

    Chezmoi is a modern dotfiles manager that supports:
    - Git repository syncing
    - Template files with machine-specific variables
    - Secrets management (age encryption, Bitwarden, 1Password, etc.)
    - Multi-machine support with different configurations
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
        Initialize chezmoi task.

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
        self.chezmoi_path = Path.home() / ".local" / "share" / "chezmoi"

    def run(self) -> bool:
        """
        Execute chezmoi dotfiles management task.

        Returns:
            True if successful
        """
        if self.state.is_complete('chezmoi_configured'):
            self.logger.info("Chezmoi already configured (skipping)")
            return True

        self.logger.section("Chezmoi Dotfiles Management")

        # Step 1: Ensure chezmoi is installed
        if not self._ensure_chezmoi_installed():
            return False

        # Step 2: Initialize or update from repo
        if not self._init_or_update():
            return False

        # Step 3: Apply dotfiles
        if not self._apply_dotfiles():
            return False

        self.state.mark_complete('chezmoi_configured')
        self.logger.success("Chezmoi configuration complete")
        return True

    def _ensure_chezmoi_installed(self) -> bool:
        """Ensure chezmoi is installed."""
        if shutil.which('chezmoi'):
            self.logger.info("Chezmoi is already installed")
            return True

        self.logger.info("Installing chezmoi...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would install chezmoi")
            return True

        # Try package manager first
        pkg_manager = get_package_manager(self.platform, self.dry_run)
        if pkg_manager:
            if pkg_manager.install(['chezmoi']):
                self.logger.success("Chezmoi installed via package manager")
                return True

        # Fallback to install script
        try:
            subprocess.run(
                ['sh', '-c', 'curl -fsLS get.chezmoi.io | sh'],
                check=True,
            )
            self.logger.success("Chezmoi installed via install script")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install chezmoi: {e}")
            return False

    def _init_or_update(self) -> bool:
        """Initialize chezmoi from repo or update existing."""
        repo_url = self._get_repo_url()

        if not repo_url:
            # No repo configured, just ensure chezmoi is initialized
            if not self.chezmoi_path.exists():
                self.logger.info("No dotfiles repo configured, initializing empty chezmoi")
                if self.dry_run:
                    self.logger.info("[DRY RUN] Would run: chezmoi init")
                    return True
                try:
                    subprocess.run(['chezmoi', 'init'], check=True)
                    return True
                except subprocess.CalledProcessError as e:
                    self.logger.error(f"Failed to initialize chezmoi: {e}")
                    return False
            return True

        if self.chezmoi_path.exists():
            # Already initialized, update from remote
            return self._update_from_remote()
        else:
            # Fresh initialization from repo
            return self._init_from_repo(repo_url)

    def _get_repo_url(self) -> Optional[str]:
        """Get the dotfiles repository URL from config."""
        # Check for chezmoi-specific config
        chezmoi_config = getattr(self.config, 'chezmoi', None)
        if chezmoi_config:
            return chezmoi_config.get('repo')

        # Check for generic dotfiles repo
        return getattr(self.config, 'dotfiles_repo', None)

    def _init_from_repo(self, repo_url: str) -> bool:
        """Initialize chezmoi from a git repository."""
        self.logger.info(f"Initializing chezmoi from {repo_url}...")

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would run: chezmoi init {repo_url}")
            return True

        try:
            cmd = ['chezmoi', 'init', repo_url]

            # Add SSH flag for GitHub repos if needed
            if 'github.com' in repo_url and not repo_url.startswith('http'):
                cmd.append('--ssh')

            subprocess.run(cmd, check=True)
            self.logger.success("Chezmoi initialized from repository")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to initialize chezmoi from repo: {e}")
            return False

    def _update_from_remote(self) -> bool:
        """Update chezmoi source from remote repository."""
        self.logger.info("Updating chezmoi from remote...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would run: chezmoi update --apply=false")
            return True

        try:
            # Pull changes without applying (we'll apply separately)
            subprocess.run(
                ['chezmoi', 'git', 'pull', '--', '--rebase'],
                check=True,
            )
            self.logger.success("Chezmoi source updated from remote")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to update from remote: {e}")
            # Not fatal - we can still apply existing dotfiles
            return True

    def _apply_dotfiles(self) -> bool:
        """Apply chezmoi dotfiles to home directory."""
        if not self.auto_yes:
            # Show diff first
            self.logger.info("Checking for changes...")
            try:
                result = subprocess.run(
                    ['chezmoi', 'diff'],
                    capture_output=True,
                    text=True,
                )
                if result.stdout:
                    self.logger.info("Changes to be applied:")
                    print(result.stdout[:2000])  # Limit output
                    if len(result.stdout) > 2000:
                        print("... (output truncated)")
                else:
                    self.logger.info("No changes to apply")
                    return True
            except subprocess.CalledProcessError:
                pass

            response = input("Apply chezmoi dotfiles? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipping chezmoi apply")
                return True

        if self.dry_run:
            self.logger.info("[DRY RUN] Would run: chezmoi apply")
            return True

        try:
            subprocess.run(['chezmoi', 'apply', '--verbose'], check=True)
            self.logger.success("Dotfiles applied successfully")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to apply dotfiles: {e}")
            return False

    def add_file(self, path: Path) -> bool:
        """
        Add a file to chezmoi management.

        Args:
            path: Path to file to add

        Returns:
            True if successful
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would add {path} to chezmoi")
            return True

        try:
            subprocess.run(['chezmoi', 'add', str(path)], check=True)
            self.logger.success(f"Added {path} to chezmoi")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to add {path}: {e}")
            return False

    def add_template(self, path: Path) -> bool:
        """
        Add a file as a template to chezmoi.

        Templates support variable substitution for machine-specific configs.

        Args:
            path: Path to file to add as template

        Returns:
            True if successful
        """
        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would add {path} as template to chezmoi")
            return True

        try:
            subprocess.run(['chezmoi', 'add', '--template', str(path)], check=True)
            self.logger.success(f"Added {path} as template to chezmoi")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to add {path} as template: {e}")
            return False

    def configure_data(self, data: Dict[str, str]) -> bool:
        """
        Configure chezmoi template data.

        This creates/updates ~/.config/chezmoi/chezmoi.toml with data
        that can be used in templates.

        Args:
            data: Dictionary of key-value pairs for templates

        Returns:
            True if successful
        """
        config_path = Path.home() / ".config" / "chezmoi" / "chezmoi.toml"

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would configure chezmoi data in {config_path}")
            return True

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Read existing config if present
            existing_content = ""
            if config_path.exists():
                existing_content = config_path.read_text()

            # Build data section
            data_lines = ["[data]"]
            for key, value in data.items():
                # Quote string values
                if isinstance(value, str):
                    data_lines.append(f'    {key} = "{value}"')
                else:
                    data_lines.append(f'    {key} = {value}')

            data_section = "\n".join(data_lines) + "\n"

            # Replace or append data section
            if "[data]" in existing_content:
                # Find and replace existing data section
                import re
                pattern = r'\[data\].*?(?=\n\[|$)'
                new_content = re.sub(pattern, data_section.strip(), existing_content, flags=re.DOTALL)
            else:
                new_content = existing_content + "\n" + data_section

            config_path.write_text(new_content)
            self.logger.success("Chezmoi data configured")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure chezmoi data: {e}")
            return False

    def setup_bitwarden_integration(self) -> bool:
        """
        Configure chezmoi to use Bitwarden for secrets.

        This enables using {{ bitwarden "item-name" }} in templates.

        Returns:
            True if successful
        """
        if not shutil.which('bw'):
            self.logger.warning("Bitwarden CLI not installed, skipping integration")
            return True

        config_path = Path.home() / ".config" / "chezmoi" / "chezmoi.toml"

        if self.dry_run:
            self.logger.info("[DRY RUN] Would configure Bitwarden integration")
            return True

        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)

            bitwarden_config = """
[bitwarden]
    command = "bw"
"""

            if config_path.exists():
                content = config_path.read_text()
                if "[bitwarden]" not in content:
                    content += bitwarden_config
                    config_path.write_text(content)
            else:
                config_path.write_text(bitwarden_config)

            self.logger.success("Bitwarden integration configured")
            return True

        except Exception as e:
            self.logger.error(f"Failed to configure Bitwarden: {e}")
            return False

    def get_managed_files(self) -> List[str]:
        """
        Get list of files managed by chezmoi.

        Returns:
            List of managed file paths
        """
        try:
            result = subprocess.run(
                ['chezmoi', 'managed'],
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip().split('\n') if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            return []

    def get_status(self) -> Dict[str, str]:
        """
        Get status of managed files.

        Returns:
            Dictionary mapping file paths to their status
        """
        try:
            result = subprocess.run(
                ['chezmoi', 'status'],
                capture_output=True,
                text=True,
                check=True,
            )
            status = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        status[parts[1]] = parts[0]
            return status
        except subprocess.CalledProcessError:
            return {}
