"""System settings configuration task."""

from typing import Dict, List

from system_setup.tasks.base import BaseTask


class SettingsTask(BaseTask):
    """Manages system settings configuration."""

    @property
    def name(self) -> str:
        return 'settings'

    @property
    def description(self) -> str:
        return 'System Settings'

    @property
    def state_key(self) -> str:
        return 'settings_applied'

    def run(self) -> bool:
        """
        Execute settings configuration task.

        Returns:
            True if successful
        """
        if self.skip_if_complete():
            return True

        self.logger.section(self.description)

        if self.platform.is_macos:
            self._apply_macos_settings()
        elif self.platform.is_linux:
            self._apply_linux_settings()
        elif self.platform.is_windows:
            self._apply_windows_settings()

        self.mark_complete()
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
        if self.cmd.is_available('gsettings'):
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
            result = self.cmd.run_quiet(cmd, shell=True)
            if not result.success:
                self.logger.warning(f"  Failed: {cmd}")

        self.logger.success(f"{name} settings applied")
        self.logger.track_setting(name)
