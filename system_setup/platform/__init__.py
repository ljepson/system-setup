"""Platform detection and abstraction."""

from system_setup.platform.base import Platform
from system_setup.platform.detector import detect_platform

__all__ = ["Platform", "detect_platform"]
