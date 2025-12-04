"""Platform detection logic."""

import platform

from system_setup.platform.base import Platform
from system_setup.platform.linux import LinuxPlatform
from system_setup.platform.macos import MacOSPlatform
from system_setup.platform.windows import WindowsPlatform


def detect_platform() -> Platform:
    """
    Detect the current platform and return appropriate Platform instance.

    Returns:
        Platform instance for the current OS

    Raises:
        RuntimeError: If platform cannot be detected
    """
    system = platform.system()

    if system == 'Darwin':
        return MacOSPlatform()
    elif system == 'Linux':
        return LinuxPlatform()
    elif system == 'Windows':
        return WindowsPlatform()
    else:
        raise RuntimeError(f"Unsupported platform: {system}")
