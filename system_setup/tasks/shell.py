"""Shell configuration task."""

import subprocess
from pathlib import Path

from system_setup.platform.macos import MacOSPlatform
from system_setup.tasks.base import BaseTask


class ShellTask(BaseTask):
    """Manages shell configuration."""

    @property
    def name(self) -> str:
        return 'shell'

    @property
    def description(self) -> str:
        return 'Shell Configuration'

    @property
    def state_key(self) -> str:
        return 'shell_configured'

    def run(self) -> bool:
        """
        Execute shell configuration task.

        Returns:
            True if successful
        """
        if self.skip_if_complete():
            return True

        self.logger.section(self.description)

        if self.platform.is_macos:
            return self._configure_macos_shell()
        elif self.platform.is_linux:
            return self._configure_linux_shell()
        elif self.platform.is_windows:
            return self._configure_windows_shell()

        return True

    def _configure_macos_shell(self) -> bool:
        """Configure shell on macOS (zsh)."""
        if not isinstance(self.platform, MacOSPlatform):
            return False

        zsh_path = self.platform.zsh_path

        if not self.auto_yes:
            response = input(f"Set {zsh_path} as default shell? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipped shell configuration")
                self.state.mark_complete('shell_configured')
                return True

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would set {zsh_path} as default shell")
            self.state.mark_complete('shell_configured')
            return True

        # Add zsh to /etc/shells if needed
        try:
            with open('/etc/shells', 'r') as f:
                shells = f.read()

            if zsh_path not in shells:
                self.logger.info(f"Adding {zsh_path} to /etc/shells...")
                subprocess.run(
                    f'echo "{zsh_path}" | sudo tee -a /etc/shells',
                    shell=True,
                    check=True,
                    capture_output=True,
                )
        except Exception as e:
            self.logger.warning(f"Could not modify /etc/shells: {e}")

        # Change default shell
        try:
            self.logger.info(f"Changing default shell to {zsh_path}...")
            subprocess.run(['chsh', '-s', zsh_path], check=True)
            self.logger.success("Shell changed successfully")
            self.state.mark_complete('shell_configured')
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to change shell: {e}")
            return False

    def _configure_linux_shell(self) -> bool:
        """Configure shell on Linux."""
        # Check if fish is enabled and should be default
        if self.config.fish_enabled and self.config.fish_set_default:
            shell_path = "/usr/bin/fish"
            shell_name = "fish"
        else:
            shell_path = "/usr/bin/zsh"
            shell_name = "zsh"

        # Verify shell exists
        if not Path(shell_path).exists():
            self.logger.warning(f"{shell_name} not found at {shell_path}, skipping shell config")
            self.state.mark_complete('shell_configured')
            return True

        if not self.auto_yes:
            response = input(f"Set {shell_path} as default shell? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipped shell configuration")
                self.state.mark_complete('shell_configured')
                return True

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would set {shell_path} as default shell")
            self.state.mark_complete('shell_configured')
            return True

        try:
            subprocess.run(['chsh', '-s', shell_path], check=True)
            self.logger.success(f"Shell changed to {shell_name} successfully")
            self.state.mark_complete('shell_configured')
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to change shell: {e}")
            return False

    def _configure_windows_shell(self) -> bool:
        """Configure shell on Windows (PowerShell)."""
        self.logger.info("Windows shell configuration not yet implemented")
        self.state.mark_complete('shell_configured')
        return True
