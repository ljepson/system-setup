"""Winget package manager implementation."""

import shutil
import subprocess
from typing import List

from system_setup.packages.base import PackageManager


class WingetManager(PackageManager):
    """Winget package manager (Windows)."""

    @property
    def name(self) -> str:
        """Get package manager name."""
        return "winget"

    def is_available(self) -> bool:
        """Check if Winget is available."""
        return shutil.which('winget') is not None

    def update(self) -> bool:
        """Update Winget sources."""
        try:
            self._run_command(['winget', 'source', 'update'])
            return True
        except subprocess.CalledProcessError:
            return False

    def install(self, packages: List[str]) -> bool:
        """Install packages via Winget."""
        if not packages:
            return True

        try:
            for package in packages:
                cmd = ['winget', 'install', '-e', '--id', package, '--accept-package-agreements']
                self._run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            result = self._run_command(
                ['winget', 'list', '--id', package],
                check=False,
                capture_output=True,
            )
            return result.returncode == 0 and package in result.stdout
        except Exception:
            return False


class ChocolateyManager(PackageManager):
    """Chocolatey package manager (Windows)."""

    @property
    def name(self) -> str:
        """Get package manager name."""
        return "choco"

    def is_available(self) -> bool:
        """Check if Chocolatey is available."""
        return shutil.which('choco') is not None

    def update(self) -> bool:
        """Update Chocolatey."""
        try:
            self._run_command(['choco', 'upgrade', 'chocolatey', '-y'])
            return True
        except subprocess.CalledProcessError:
            return False

    def install(self, packages: List[str]) -> bool:
        """Install packages via Chocolatey."""
        if not packages:
            return True

        try:
            cmd = ['choco', 'install', '-y'] + packages
            self._run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            result = self._run_command(
                ['choco', 'list', '--local-only', package],
                check=False,
                capture_output=True,
            )
            return result.returncode == 0 and package in result.stdout
        except Exception:
            return False
