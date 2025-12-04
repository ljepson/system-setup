"""APT package manager implementation."""

import shutil
import subprocess
from typing import List

from system_setup.packages.base import PackageManager


class AptManager(PackageManager):
    """APT package manager (Debian/Ubuntu)."""

    @property
    def name(self) -> str:
        """Get package manager name."""
        return "apt"

    def is_available(self) -> bool:
        """Check if APT is available."""
        return shutil.which('apt') is not None or shutil.which('apt-get') is not None

    def update(self) -> bool:
        """Update APT package lists."""
        try:
            self._run_command(['sudo', 'apt', 'update'])
            return True
        except subprocess.CalledProcessError:
            return False

    def install(self, packages: List[str]) -> bool:
        """Install packages via APT."""
        if not packages:
            return True

        try:
            cmd = ['sudo', 'apt', 'install', '-y'] + packages
            self._run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            result = self._run_command(
                ['dpkg', '-s', package],
                check=False,
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False
