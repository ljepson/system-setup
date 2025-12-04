"""macOS platform implementation."""

import platform
import shutil
from pathlib import Path
from typing import List

from system_setup.platform.base import Architecture, OSType, Platform


class MacOSPlatform(Platform):
    """macOS-specific platform implementation."""

    def _detect_os_type(self) -> OSType:
        """Detect operating system type."""
        return OSType.MACOS

    def _detect_architecture(self) -> Architecture:
        """Detect CPU architecture."""
        machine = platform.machine().lower()

        if machine in ('arm64', 'aarch64'):
            return Architecture.ARM64
        elif machine in ('x86_64', 'amd64'):
            return Architecture.X86_64
        elif machine in ('i386', 'i686'):
            return Architecture.I386
        else:
            return Architecture.UNKNOWN

    def get_available_package_managers(self) -> List[str]:
        """Get list of available package managers."""
        managers = []

        if shutil.which('brew'):
            managers.append('brew')

        # MacPorts
        if shutil.which('port'):
            managers.append('port')

        return managers

    def get_shell_config_file(self) -> str:
        """Get path to shell configuration file."""
        shell = Path.home() / '.zshrc'
        if shell.exists():
            return str(shell)

        # Fallback to bash
        return str(Path.home() / '.bashrc')

    @property
    def homebrew_prefix(self) -> str:
        """Get Homebrew installation prefix based on architecture."""
        if self.is_arm:
            return "/opt/homebrew"
        else:
            return "/usr/local"

    @property
    def zsh_path(self) -> str:
        """Get path to Homebrew zsh."""
        return f"{self.homebrew_prefix}/bin/zsh"
