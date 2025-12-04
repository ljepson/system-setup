"""Package manager factory."""

from typing import Optional

from system_setup.packages.apt import AptManager
from system_setup.packages.base import PackageManager
from system_setup.packages.homebrew import HomebrewManager
from system_setup.packages.pacman import PacmanManager
from system_setup.packages.winget import ChocolateyManager, WingetManager
from system_setup.platform import Platform


def get_package_manager(platform: Platform, dry_run: bool = False) -> Optional[PackageManager]:
    """
    Get the appropriate package manager for the platform.

    Args:
        platform: Platform instance
        dry_run: Enable dry-run mode

    Returns:
        PackageManager instance or None if no suitable manager found
    """
    # Try platform-specific managers in order of preference
    if platform.is_macos:
        managers = [
            HomebrewManager(dry_run),
        ]
    elif platform.is_linux:
        managers = [
            AptManager(dry_run),
            PacmanManager(dry_run),
        ]
    elif platform.is_windows:
        managers = [
            WingetManager(dry_run),
            ChocolateyManager(dry_run),
        ]
    else:
        return None

    # Return first available manager
    for manager in managers:
        if manager.is_available():
            return manager

    return None
