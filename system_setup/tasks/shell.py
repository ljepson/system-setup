"""Shell configuration task."""

import subprocess
from pathlib import Path

from system_setup.config import Config
from system_setup.logger import get_logger
from system_setup.platform import Platform
from system_setup.platform.macos import MacOSPlatform
from system_setup.state import StateManager


class ShellTask:
    """Manages shell configuration."""

    def __init__(
        self,
        config: Config,
        state: StateManager,
        platform: Platform,
        dry_run: bool = False,
        auto_yes: bool = False,
    ) -> None:
        """
        Initialize shell task.

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
        Execute shell configuration task.

        Returns:
            True if successful
        """
        if self.state.is_complete('shell_configured'):
            self.logger.info("Shell already configured (skipping)")
            return True

        self.logger.section("Shell Configuration")

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
        """Configure shell on Linux (zsh)."""
        zsh_path = "/usr/bin/zsh"

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

        try:
            subprocess.run(['chsh', '-s', zsh_path], check=True)
            self.logger.success("Shell changed successfully")
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
