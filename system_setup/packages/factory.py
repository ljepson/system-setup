"""Package manager factory."""

from typing import Optional

from system_setup.packages.apt import AptManager
from system_setup.packages.base import PackageManager
from system_setup.packages.homebrew import HomebrewManager
from system_setup.packages.pacman import PacmanManager
from system_setup.packages.paru import ParuManager
from system_setup.packages.winget import ChocolateyManager, WingetManager
from system_setup.platform import Platform


def get_package_manager(
    platform: Platform,
    dry_run: bool = False,
    prefer_aur_helper: bool = True
) -> Optional[PackageManager]:
    """
    Get the appropriate package manager for the platform.

    Args:
        platform: Platform instance
        dry_run: Enable dry-run mode
        prefer_aur_helper: On Arch, prefer paru over pacman (default: True)

    Returns:
        PackageManager instance or None if no suitable manager found
    """
    # Try platform-specific managers in order of preference
    if platform.is_macos:
        managers = [
            HomebrewManager(dry_run),
        ]
    elif platform.is_linux:
        if prefer_aur_helper:
            # Prefer paru (AUR helper) on Arch-based distros
            managers = [
                ParuManager(dry_run),  # Paru first (handles AUR + official)
                PacmanManager(dry_run),  # Fallback to pacman
                AptManager(dry_run),  # For Debian/Ubuntu
            ]
        else:
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


def ensure_paru_installed(dry_run: bool = False) -> bool:
    """
    Ensure paru is installed on Arch-based systems.

    If paru is not available but pacman is, this will install paru from AUR.

    Args:
        dry_run: Enable dry-run mode

    Returns:
        True if paru is available after this call
    """
    paru = ParuManager(dry_run)

    if paru.is_available():
        return True

    if not ParuManager.can_install():
        return False

    return paru.install_paru()


def get_aur_manager(dry_run: bool = False) -> Optional[ParuManager]:
    """
    Get paru AUR manager if available.

    Args:
        dry_run: Enable dry-run mode

    Returns:
        ParuManager if available, None otherwise
    """
    paru = ParuManager(dry_run)
    if paru.is_available():
        return paru
    return None
