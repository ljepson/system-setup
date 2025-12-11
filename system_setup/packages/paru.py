"""Paru AUR helper package manager implementation."""

import os
import shutil
import subprocess
import tempfile
from typing import List, Optional

from system_setup.packages.base import PackageManager


class ParuManager(PackageManager):
    """Paru AUR helper (Arch Linux).

    Paru is a feature-rich AUR helper written in Rust, designed as a yay successor.
    It can install both official Arch packages and AUR packages.
    """

    @property
    def name(self) -> str:
        """Get package manager name."""
        return "paru"

    def is_available(self) -> bool:
        """Check if Paru is available."""
        return shutil.which('paru') is not None

    @staticmethod
    def can_install() -> bool:
        """Check if paru can be installed (requires pacman and git)."""
        return (
            shutil.which('pacman') is not None and
            shutil.which('git') is not None
        )

    def install_paru(self) -> bool:
        """
        Install paru from AUR.

        Returns:
            True if installation successful
        """
        if self.is_available():
            return True

        if self.dry_run:
            print("[DRY RUN] Would install paru from AUR")
            return True

        # Install base-devel if needed
        try:
            subprocess.run(
                ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'base-devel', 'git'],
                check=True
            )
        except subprocess.CalledProcessError:
            return False

        # Clone and build paru
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                subprocess.run(
                    ['git', 'clone', 'https://aur.archlinux.org/paru.git'],
                    cwd=tmpdir,
                    check=True
                )
                subprocess.run(
                    ['makepkg', '-si', '--noconfirm'],
                    cwd=os.path.join(tmpdir, 'paru'),
                    check=True
                )
                return True
            except subprocess.CalledProcessError:
                return False

    def update(self) -> bool:
        """Update package database and upgrade packages."""
        try:
            self._run_command(['paru', '-Sy'])
            return True
        except subprocess.CalledProcessError:
            return False

    def upgrade(self) -> bool:
        """Upgrade all packages including AUR."""
        try:
            self._run_command(['paru', '-Syu', '--noconfirm'])
            return True
        except subprocess.CalledProcessError:
            return False

    def install(self, packages: List[str]) -> bool:
        """
        Install packages via Paru.

        Handles both official repo packages and AUR packages seamlessly.

        Args:
            packages: List of package names to install

        Returns:
            True if all packages installed successfully
        """
        if not packages:
            return True

        try:
            cmd = ['paru', '-S', '--needed', '--noconfirm'] + packages
            self._run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def install_aur(self, packages: List[str]) -> bool:
        """
        Install AUR-only packages.

        Args:
            packages: List of AUR package names

        Returns:
            True if successful
        """
        if not packages:
            return True

        try:
            # --aur flag restricts to AUR packages only
            cmd = ['paru', '-S', '--aur', '--needed', '--noconfirm'] + packages
            self._run_command(cmd)
            return True
        except subprocess.CalledProcessError:
            return False

    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        try:
            result = self._run_command(
                ['paru', '-Q', package],
                check=False,
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def search(self, query: str) -> List[str]:
        """
        Search for packages in repos and AUR.

        Args:
            query: Search query

        Returns:
            List of matching package names
        """
        try:
            result = self._run_command(
                ['paru', '-Ss', query],
                check=False,
                capture_output=True,
            )
            if result.returncode != 0:
                return []

            # Parse output - package names are at start of lines
            packages = []
            for line in result.stdout.split('\n'):
                if line and not line.startswith(' '):
                    # Format: repo/packagename version
                    parts = line.split('/')
                    if len(parts) >= 2:
                        pkg_part = parts[1].split()[0]
                        packages.append(pkg_part)
            return packages
        except Exception:
            return []

    def clean_cache(self) -> bool:
        """Clean package cache."""
        try:
            self._run_command(['paru', '-Sc', '--noconfirm'])
            return True
        except subprocess.CalledProcessError:
            return False
