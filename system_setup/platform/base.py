"""Base platform abstraction."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional


class OSType(Enum):
    """Operating system types."""
    MACOS = "macos"
    LINUX = "linux"
    WINDOWS = "windows"
    UNKNOWN = "unknown"


class Architecture(Enum):
    """CPU architectures."""
    X86_64 = "x86_64"
    ARM64 = "arm64"
    AARCH64 = "aarch64"
    I386 = "i386"
    UNKNOWN = "unknown"


class Platform(ABC):
    """Abstract base class for platform-specific operations."""

    def __init__(self) -> None:
        """Initialize platform."""
        self._os_type = self._detect_os_type()
        self._architecture = self._detect_architecture()
        self._distro: Optional[str] = None

    @abstractmethod
    def _detect_os_type(self) -> OSType:
        """Detect operating system type."""
        pass

    @abstractmethod
    def _detect_architecture(self) -> Architecture:
        """Detect CPU architecture."""
        pass

    @property
    def os_type(self) -> OSType:
        """Get operating system type."""
        return self._os_type

    @property
    def architecture(self) -> Architecture:
        """Get CPU architecture."""
        return self._architecture

    @property
    def distro(self) -> Optional[str]:
        """Get Linux distribution name (Linux only)."""
        return self._distro

    @property
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self._os_type == OSType.MACOS

    @property
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self._os_type == OSType.LINUX

    @property
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self._os_type == OSType.WINDOWS

    @property
    def is_arm(self) -> bool:
        """Check if running on ARM architecture."""
        return self._architecture in (Architecture.ARM64, Architecture.AARCH64)

    @abstractmethod
    def get_available_package_managers(self) -> List[str]:
        """
        Get list of available package managers for this platform.

        Returns:
            List of package manager names (e.g., ['brew', 'apt'])
        """
        pass

    @abstractmethod
    def get_shell_config_file(self) -> str:
        """
        Get path to shell configuration file.

        Returns:
            Path to shell config file (e.g., ~/.zshrc, ~/.bashrc)
        """
        pass

    def __str__(self) -> str:
        """String representation."""
        distro_str = f" ({self._distro})" if self._distro else ""
        return f"{self._os_type.value}{distro_str}, {self._architecture.value}"
