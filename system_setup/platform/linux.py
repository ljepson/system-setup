"""Linux platform implementation."""

import platform
import shutil
from pathlib import Path
from typing import List, Optional

from system_setup.platform.base import Architecture, OSType, Platform


class LinuxPlatform(Platform):
    """Linux-specific platform implementation."""

    def __init__(self) -> None:
        """Initialize Linux platform."""
        super().__init__()
        self._distro = self._detect_distro()

    def _detect_os_type(self) -> OSType:
        """Detect operating system type."""
        return OSType.LINUX

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

    def _detect_distro(self) -> Optional[str]:
        """
        Detect Linux distribution.

        Returns:
            Distribution name (debian, arch, fedora, opensuse) or None
        """
        # Check for package managers to identify distro
        if shutil.which('apt') or shutil.which('apt-get'):
            return 'debian'  # Ubuntu, Debian, Raspberry Pi OS
        elif shutil.which('pacman'):
            return 'arch'
        elif shutil.which('dnf'):
            return 'fedora'
        elif shutil.which('zypper'):
            return 'opensuse'
        elif shutil.which('yum'):
            return 'rhel'  # RHEL, CentOS

        # Try reading /etc/os-release
        try:
            with open('/etc/os-release') as f:
                for line in f:
                    if line.startswith('ID='):
                        distro_id = line.split('=')[1].strip().strip('"')
                        if 'ubuntu' in distro_id or 'debian' in distro_id:
                            return 'debian'
                        elif 'arch' in distro_id:
                            return 'arch'
                        elif 'fedora' in distro_id:
                            return 'fedora'
                        elif 'suse' in distro_id:
                            return 'opensuse'
                        elif 'rhel' in distro_id or 'centos' in distro_id:
                            return 'rhel'
        except FileNotFoundError:
            pass

        return None

    def get_available_package_managers(self) -> List[str]:
        """Get list of available package managers."""
        managers = []

        # Native package managers
        if shutil.which('apt'):
            managers.append('apt')
        if shutil.which('pacman'):
            managers.append('pacman')
        if shutil.which('dnf'):
            managers.append('dnf')
        if shutil.which('zypper'):
            managers.append('zypper')
        if shutil.which('yum'):
            managers.append('yum')

        # AUR helpers
        if shutil.which('paru'):
            managers.append('paru')
        if shutil.which('yay'):
            managers.append('yay')

        # Universal package managers
        if shutil.which('snap'):
            managers.append('snap')
        if shutil.which('flatpak'):
            managers.append('flatpak')

        return managers

    def get_shell_config_file(self) -> str:
        """Get path to shell configuration file."""
        zsh_config = Path.home() / '.zshrc'
        if zsh_config.exists():
            return str(zsh_config)

        # Fallback to bash
        return str(Path.home() / '.bashrc')

    @property
    def has_systemd(self) -> bool:
        """Check if system uses systemd."""
        return Path('/run/systemd/system').exists()
