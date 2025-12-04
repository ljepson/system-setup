"""Windows platform implementation."""

import platform
import shutil
from pathlib import Path
from typing import List

from system_setup.platform.base import Architecture, OSType, Platform


class WindowsPlatform(Platform):
    """Windows-specific platform implementation."""

    def _detect_os_type(self) -> OSType:
        """Detect operating system type."""
        return OSType.WINDOWS

    def _detect_architecture(self) -> Architecture:
        """Detect CPU architecture."""
        machine = platform.machine().lower()

        if machine in ('amd64', 'x86_64'):
            return Architecture.X86_64
        elif machine in ('arm64', 'aarch64'):
            return Architecture.ARM64
        elif machine in ('i386', 'i686', 'x86'):
            return Architecture.I386
        else:
            return Architecture.UNKNOWN

    def get_available_package_managers(self) -> List[str]:
        """Get list of available package managers."""
        managers = []

        # Windows package managers
        if shutil.which('winget'):
            managers.append('winget')
        if shutil.which('choco'):
            managers.append('choco')
        if shutil.which('scoop'):
            managers.append('scoop')

        return managers

    def get_shell_config_file(self) -> str:
        """Get path to shell configuration file."""
        # PowerShell profile
        powershell_profile = (
            Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        )
        if powershell_profile.exists():
            return str(powershell_profile)

        # Git Bash / WSL
        bashrc = Path.home() / '.bashrc'
        if bashrc.exists():
            return str(bashrc)

        # Default to PowerShell profile location
        return str(powershell_profile)

    @property
    def in_wsl(self) -> bool:
        """Check if running in Windows Subsystem for Linux."""
        try:
            with open('/proc/version', 'r') as f:
                return 'microsoft' in f.read().lower()
        except FileNotFoundError:
            return False
