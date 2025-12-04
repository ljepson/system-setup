"""Package manager abstraction."""

from system_setup.packages.base import PackageManager
from system_setup.packages.factory import get_package_manager

__all__ = ["PackageManager", "get_package_manager"]
