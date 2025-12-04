"""Pacman package manager implementation."""

import shutil
import subprocess
from typing import List

from system_setup.packages.base import PackageManager


class PacmanManager(PackageManager):
    """Pacman package manager (Arch Linux)."""

    @property
    def name(self) -> str:
        """Get package manager name."""
        return "pacman"

    def is_available(self) -> bool:
        """Check if Pacman is available."""
        return shutil.which('pacman') is not None

    def update(self) -> bool:
        """Update Pacman package database."""
        try:
            self._run_command(['sudo', 'pacman', '-Sy'])
            return True
        except subprocess.CalledProcessError:
            return False

    def install(self, packages: List[str]) -> bool:
        """Install packages via Pacman."""
        if not packages:
            return True

        try:
            cmd = ['sudo', 'pacman', '-S', '--noconfirm'] + packages
            self._run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            result = self._run_command(
                ['pacman', '-Q', package],
                check=False,
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False
