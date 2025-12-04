"""Base package manager abstraction."""

import subprocess
from abc import ABC, abstractmethod
from typing import List, Optional


class PackageManager(ABC):
    """Abstract base class for package managers."""

    def __init__(self, dry_run: bool = False) -> None:
        """
        Initialize package manager.

        Args:
            dry_run: If True, don't actually execute commands
        """
        self.dry_run = dry_run

    @property
    @abstractmethod
    def name(self) -> str:
        """Get package manager name."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this package manager is available on the system."""
        pass

    @abstractmethod
    def update(self) -> bool:
        """
        Update package manager metadata/repositories.

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def install(self, packages: List[str]) -> bool:
        """
        Install packages.

        Args:
            packages: List of package names to install

        Returns:
            True if all packages installed successfully
        """
        pass

    @abstractmethod
    def is_installed(self, package: str) -> bool:
        """
        Check if a package is installed.

        Args:
            package: Package name

        Returns:
            True if package is installed
        """
        pass

    def _run_command(
        self,
        cmd: List[str],
        check: bool = True,
        capture_output: bool = False,
    ) -> subprocess.CompletedProcess:
        """
        Run a command with optional dry-run support.

        Args:
            cmd: Command to run as list
            check: Raise exception on non-zero exit code
            capture_output: Capture stdout/stderr

        Returns:
            CompletedProcess instance

        Raises:
            subprocess.CalledProcessError: If command fails and check=True
        """
        if self.dry_run:
            print(f"[DRY RUN] Would run: {' '.join(cmd)}")
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=b"",
                stderr=b"",
            )

        return subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True if capture_output else False,
        )
