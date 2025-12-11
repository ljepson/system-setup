"""Package manager abstraction."""

from system_setup.packages.base import PackageManager
from system_setup.packages.factory import (
    ensure_paru_installed,
    get_aur_manager,
    get_package_manager,
)
from system_setup.packages.paru import ParuManager

__all__ = [
    "PackageManager",
    "ParuManager",
    "ensure_paru_installed",
    "get_aur_manager",
    "get_package_manager",
]
