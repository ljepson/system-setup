"""Homebrew package manager implementation."""

import shutil
import subprocess
from typing import List

from system_setup.packages.base import PackageManager


class HomebrewManager(PackageManager):
    """Homebrew package manager (macOS/Linux)."""

    @property
    def name(self) -> str:
        """Get package manager name."""
        return "brew"

    def is_available(self) -> bool:
        """Check if Homebrew is available."""
        return shutil.which('brew') is not None

    def update(self) -> bool:
        """Update Homebrew."""
        try:
            self._run_command(['brew', 'update'])
            return True
        except subprocess.CalledProcessError:
            return False

    def install(self, packages: List[str]) -> bool:
        """Install packages via Homebrew."""
        if not packages:
            return True

        try:
            # Separate formulas from casks
            formulas = [p for p in packages if not p.endswith('.cask')]
            casks = [p.replace('.cask', '') for p in packages if p.endswith('.cask')]

            # Install formulas
            if formulas:
                self._run_command(['brew', 'install'] + formulas)

            # Install casks
            if casks:
                self._run_command(['brew', 'install', '--cask'] + casks)

            return True
        except subprocess.CalledProcessError:
            return False

    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            # Check formulas
            result = self._run_command(
                ['brew', 'list', package],
                check=False,
                capture_output=True,
            )
            if result.returncode == 0:
                return True

            # Check casks
            result = self._run_command(
                ['brew', 'list', '--cask', package],
                check=False,
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def install_homebrew(self) -> bool:
        """
        Install Homebrew itself.

        Returns:
            True if installation successful
        """
        if self.is_available():
            return True

        if self.dry_run:
            print("[DRY RUN] Would install Homebrew")
            return True

        try:
            # Download and run Homebrew installer
            cmd = [
                '/bin/bash',
                '-c',
                '$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)'
            ]
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
