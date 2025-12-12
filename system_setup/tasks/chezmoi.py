"""Chezmoi dotfiles management task."""

import shutil
from pathlib import Path
from typing import Dict, List, Optional

from system_setup.packages.factory import get_package_manager
from system_setup.tasks.base import BaseTask


class ChezmoiTask(BaseTask):
    """Manages dotfiles using chezmoi.

    Chezmoi is a modern dotfiles manager that supports:
    - Git repository syncing
    - Template files with machine-specific variables
    - Secrets management (age encryption, Bitwarden, 1Password, etc.)
    - Multi-machine support with different configurations
    """

    def __init__(self, *args, **kwargs) -> None:
        """Initialize chezmoi task."""
        super().__init__(*args, **kwargs)
        self.chezmoi_source_path = Path.home() / ".local" / "share" / "chezmoi"
        self._chezmoi_bin: Optional[str] = None

    @property
    def name(self) -> str:
        return 'chezmoi'

    @property
    def description(self) -> str:
        return 'Chezmoi Dotfiles Management'

    @property
    def state_key(self) -> str:
        return 'chezmoi_configured'

    def _get_chezmoi_cmd(self) -> str:
        """Get the chezmoi command, checking common install locations."""
        if self._chezmoi_bin:
            return self._chezmoi_bin

        # Check if in PATH
        if shutil.which('chezmoi'):
            self._chezmoi_bin = 'chezmoi'
            return self._chezmoi_bin

        # Check common install locations
        locations = [
            Path.home() / 'bin' / 'chezmoi',
            Path.home() / '.local' / 'bin' / 'chezmoi',
            Path('/usr/local/bin/chezmoi'),
        ]
        for loc in locations:
            if loc.exists() and loc.is_file():
                self._chezmoi_bin = str(loc)
                return self._chezmoi_bin

        # Default to just 'chezmoi' and hope for the best
        self._chezmoi_bin = 'chezmoi'
        return self._chezmoi_bin

    def run(self) -> bool:
        """
        Execute chezmoi dotfiles management task.

        Returns:
            True if successful
        """
        if self.skip_if_complete():
            return True

        self.logger.section(self.description)

        # Step 1: Ensure chezmoi is installed
        if not self._ensure_chezmoi_installed():
            return False

        # Step 2: Initialize or update from repo
        if not self._init_or_update():
            return False

        # Step 3: Apply dotfiles
        if not self._apply_dotfiles():
            return False

        self.mark_complete()
        self.logger.success("Chezmoi configuration complete")
        return True

    def _ensure_chezmoi_installed(self) -> bool:
        """Ensure chezmoi is installed."""
        # Check if already installed (in PATH or common locations)
        chezmoi_cmd = self._get_chezmoi_cmd()
        if shutil.which(chezmoi_cmd) or Path(chezmoi_cmd).exists():
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

        # Fallback to install script - install to ~/.local/bin
        try:
            bin_dir = Path.home() / '.local' / 'bin'
            bin_dir.mkdir(parents=True, exist_ok=True)
            result = self.cmd.run(
                f'curl -fsLS get.chezmoi.io | sh -s -- -b {bin_dir}',
                shell=True,
            )
            if result.success:
                self._chezmoi_bin = str(bin_dir / 'chezmoi')
                self.logger.success("Chezmoi installed via install script")
                return True
            self.logger.error(f"Failed to install chezmoi: {result.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install chezmoi: {e}")
            return False

    def _init_or_update(self) -> bool:
        """Initialize chezmoi from repo or update existing."""
        repo_url = self._get_repo_url()

        if not repo_url:
            # No repo configured, just ensure chezmoi is initialized
            if not self.chezmoi_source_path.exists():
                self.logger.info("No dotfiles repo configured, initializing empty chezmoi")
                if self.dry_run:
                    self.logger.info("[DRY RUN] Would run: chezmoi init")
                    return True
                result = self.cmd.run([self._get_chezmoi_cmd(), 'init'], check=False)
                if result.success:
                    return True
                self.logger.error(f"Failed to initialize chezmoi: {result.stderr}")
                return False
            return True

        if self.chezmoi_source_path.exists():
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

        cmd = [self._get_chezmoi_cmd(), 'init', repo_url]

        # Add SSH flag for GitHub repos if needed
        if 'github.com' in repo_url and not repo_url.startswith('http'):
            cmd.append('--ssh')

        result = self.cmd.run(cmd, check=False)
        if result.success:
            self.logger.success("Chezmoi initialized from repository")
            return True
        self.logger.error(f"Failed to initialize chezmoi from repo: {result.stderr}")
        return False

    def _update_from_remote(self) -> bool:
        """Update chezmoi source from remote repository."""
        self.logger.info("Updating chezmoi from remote...")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would run: chezmoi update --apply=false")
            return True

        # Pull changes without applying (we'll apply separately)
        result = self.cmd.run(
            [self._get_chezmoi_cmd(), 'git', 'pull', '--', '--rebase'],
            check=False,
        )
        if result.success:
            self.logger.success("Chezmoi source updated from remote")
        else:
            self.logger.warning(f"Failed to update from remote: {result.stderr}")
        # Not fatal - we can still apply existing dotfiles
        return True

    def _apply_dotfiles(self) -> bool:
        """Apply chezmoi dotfiles to home directory."""
        if self.dry_run:
            self.logger.info("[DRY RUN] Would run: chezmoi apply")
            return True

        if not self.auto_yes:
            # Show diff first
            self.logger.info("Checking for changes...")
            result = self.cmd.run_quiet([self._get_chezmoi_cmd(), 'diff'])
            if result.stdout:
                self.logger.info("Changes to be applied:")
                print(result.stdout[:2000])  # Limit output
                if len(result.stdout) > 2000:
                    print("... (output truncated)")
            else:
                self.logger.info("No changes to apply")
                return True

            response = input("Apply chezmoi dotfiles? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipping chezmoi apply")
                return True

        result = self.cmd.run([self._get_chezmoi_cmd(), 'apply', '--verbose'], check=False)
        if result.success:
            self.logger.success("Dotfiles applied successfully")
            return True
        self.logger.error(f"Failed to apply dotfiles: {result.stderr}")
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

        result = self.cmd.run([self._get_chezmoi_cmd(), 'add', str(path)], check=False)
        if result.success:
            self.logger.success(f"Added {path} to chezmoi")
            return True
        self.logger.error(f"Failed to add {path}: {result.stderr}")
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

        result = self.cmd.run(
            [self._get_chezmoi_cmd(), 'add', '--template', str(path)],
            check=False,
        )
        if result.success:
            self.logger.success(f"Added {path} as template to chezmoi")
            return True
        self.logger.error(f"Failed to add {path} as template: {result.stderr}")
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
        result = self.cmd.run_quiet([self._get_chezmoi_cmd(), 'managed'])
        if result.success and result.stdout.strip():
            return result.stdout.strip().split('\n')
        return []

    def get_status(self) -> Dict[str, str]:
        """
        Get status of managed files.

        Returns:
            Dictionary mapping file paths to their status
        """
        result = self.cmd.run_quiet([self._get_chezmoi_cmd(), 'status'])
        if not result.success:
            return {}
        status = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    status[parts[1]] = parts[0]
        return status
