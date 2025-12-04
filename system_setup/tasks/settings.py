"""System settings configuration task."""

import subprocess
from typing import Dict, List

from system_setup.config import Config
from system_setup.logger import get_logger
from system_setup.platform import Platform
from system_setup.state import StateManager


class SettingsTask:
    """Manages system settings configuration."""

    def __init__(
        self,
        config: Config,
        state: StateManager,
        platform: Platform,
        dry_run: bool = False,
        auto_yes: bool = False,
    ) -> None:
        """
        Initialize settings task.

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
        Execute settings configuration task.

        Returns:
            True if successful
        """
        if self.state.is_complete('settings_applied'):
            self.logger.info("Settings already applied (skipping)")
            return True

        self.logger.section("System Settings")

        if self.platform.is_macos:
            self._apply_macos_settings()
        elif self.platform.is_linux:
            self._apply_linux_settings()
        elif self.platform.is_windows:
            self._apply_windows_settings()

        self.state.mark_complete('settings_applied')
        return True

    def _apply_macos_settings(self) -> None:
        """Apply macOS settings."""
        settings_groups: Dict[str, List[str]] = {
            "Dock": [
                'defaults write com.apple.dock "autohide" -bool "true"',
                'defaults write com.apple.dock "autohide-delay" -float "0"',
                'defaults write com.apple.dock "show-recents" -bool "false"',
            ],
            "Finder": [
                'defaults write NSGlobalDomain "AppleShowAllExtensions" -bool "true"',
                'defaults write com.apple.finder "AppleShowAllFiles" -bool "true"',
                'defaults write com.apple.finder "ShowPathbar" -bool "true"',
            ],
            "General": [
                'defaults write NSGlobalDomain "ApplePressAndHoldEnabled" -bool "false"',
                'defaults write com.apple.screencapture "type" -string "png"',
            ],
        }

        for group_name, commands in settings_groups.items():
            self._apply_settings_group(group_name, commands)

    def _apply_linux_settings(self) -> None:
        """Apply Linux settings."""
        # GNOME settings
        if subprocess.run(['which', 'gsettings'], capture_output=True).returncode == 0:
            gnome_settings = [
                'gsettings set org.gnome.nautilus.preferences show-hidden-files true',
                'gsettings set org.gnome.desktop.interface show-battery-percentage true',
            ]
            self._apply_settings_group("GNOME", gnome_settings)

    def _apply_windows_settings(self) -> None:
        """Apply Windows settings."""
        self.logger.info("Windows settings not yet implemented")

    def _apply_settings_group(self, name: str, commands: List[str]) -> None:
        """Apply a group of settings."""
        if not self.auto_yes:
            response = input(f"Apply {name} settings? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info(f"Skipped: {name}")
                return

        if self.dry_run:
            self.logger.info(f"[DRY RUN] Would apply {name} settings")
            return

        self.logger.info(f"Applying {name} settings...")
        for cmd in commands:
            try:
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"  Failed: {cmd}")

        self.logger.success(f"{name} settings applied")
        self.logger.track_setting(name)
