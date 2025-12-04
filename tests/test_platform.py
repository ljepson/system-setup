"""Tests for platform detection."""

import platform

import pytest

from system_setup.platform import detect_platform
from system_setup.platform.base import Architecture, OSType


def test_detect_platform():
    """Test platform detection."""
    plat = detect_platform()

    # Should detect current platform
    system = platform.system()
    if system == 'Darwin':
        assert plat.is_macos
        assert plat.os_type == OSType.MACOS
    elif system == 'Linux':
        assert plat.is_linux
        assert plat.os_type == OSType.LINUX
    elif system == 'Windows':
        assert plat.is_windows
        assert plat.os_type == OSType.WINDOWS


def test_platform_package_managers():
    """Test getting available package managers."""
    plat = detect_platform()
    managers = plat.get_available_package_managers()

    # Should return a list
    assert isinstance(managers, list)
