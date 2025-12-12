"""Package installation task."""

from typing import Callable, List, Optional

from system_setup.config import Config
from system_setup.packages.factory import get_package_manager
from system_setup.platform import Platform
from system_setup.state import StateManager
from system_setup.tasks.base import BaseTask
from system_setup.utils.command import CommandRunner


class PackagesTask(BaseTask):
    """Manages package installation across platforms.

    This task:
    1. Reads package lists from configuration (defaults.yaml + user overrides)
    2. Detects the appropriate package manager for the platform
    3. Installs packages with progress indication
    4. Supports dry-run mode for previewing changes

    Supports:
    - macOS: Homebrew (formulae and casks)
    - Linux: APT (Debian/Ubuntu), Pacman+Paru (Arch), DNF (Fedora)
    - Windows: Winget, Chocolatey
    """

    @property
    def name(self) -> str:
        return 'packages'

    @property
    def description(self) -> str:
        return 'Package Installation'

    @property
    def state_key(self) -> str:
        return 'packages_installed'

    def run(self) -> bool:
        """
        Execute package installation task.

        Returns:
            True if successful
        """
        if self.skip_if_complete():
            return True

        self.logger.section(self.description)

        # Get package manager
        pkg_manager = get_package_manager(self.platform, dry_run=self.dry_run)
        if not pkg_manager:
            self.logger.error("No suitable package manager found")
            return False

        self.logger.info(f"Using package manager: {pkg_manager.name}")

        # Update package manager with progress spinner
        with self.logger.progress_spinner("Updating package manager..."):
            if not pkg_manager.update():
                self.logger.warning("Package manager update failed (continuing anyway)")

        # Get packages to install from config
        packages = self._get_packages()

        if not packages:
            self.logger.warning("No packages defined for this platform")
            self.mark_complete()
            return True

        # Separate regular packages from casks for display purposes
        regular_packages = [p for p in packages if not p.endswith('.cask')]
        cask_packages = [p.replace('.cask', '') for p in packages if p.endswith('.cask')]

        self.logger.info(f"Found {len(packages)} packages to install")
        if cask_packages:
            self.logger.info(f"  ({len(regular_packages)} formulae + {len(cask_packages)} casks)")

        # Ask for confirmation (respects auto_yes)
        if not self.auto_yes:
            self.logger.info("Packages:")
            for pkg in regular_packages[:10]:
                self.logger.info(f"  • {pkg}")
            if len(regular_packages) > 10:
                self.logger.info(f"  ... and {len(regular_packages) - 10} more formulae")

            if cask_packages:
                self.logger.info("GUI Applications (casks):")
                for pkg in cask_packages[:5]:
                    self.logger.info(f"  • {pkg}")
                if len(cask_packages) > 5:
                    self.logger.info(f"  ... and {len(cask_packages) - 5} more casks")

            if not self.confirm_action(f"Install {len(packages)} packages?"):
                self.logger.info("Skipping package installation")
                return True

        # Install all packages (package manager handles .cask suffix internally)
        success = self._install_packages(pkg_manager, packages, "packages")

        if success:
            self.mark_complete()
            self.logger.success(f"Package installation complete ({len(packages)} packages)")

        return success

    def _get_packages(self) -> List[str]:
        """
        Get list of packages to install for current platform.

        Uses config.get_packages_for_platform() which reads from defaults.yaml
        merged with user configuration.

        Returns:
            List of package names (casks have .cask suffix)
        """
        platform_name = 'macos' if self.platform.is_macos else \
                       'linux' if self.platform.is_linux else \
                       'windows' if self.platform.is_windows else 'unknown'

        # Get Linux distro if applicable
        distro = None
        if self.platform.is_linux:
            distro = getattr(self.platform, 'distro', None)
            if distro is None:
                # Try to detect from platform info
                distro = self._detect_linux_distro()

        return self.config.get_packages_for_platform(platform_name, distro)

    def _detect_linux_distro(self) -> Optional[str]:
        """Detect Linux distribution name."""
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                if 'arch' in content.lower():
                    return 'arch'
                elif 'debian' in content.lower() or 'ubuntu' in content.lower():
                    return 'debian'
                elif 'fedora' in content.lower():
                    return 'fedora'
        except (FileNotFoundError, PermissionError):
            pass
        return None

    def _install_packages(
        self,
        pkg_manager,
        packages: List[str],
        label: str = "packages",
    ) -> bool:
        """
        Install packages with progress indication.

        Args:
            pkg_manager: Package manager instance
            packages: List of package names
            label: Label for progress display

        Returns:
            True if successful
        """
        if self.dry_run:
            self.log_dry_run(f"install {len(packages)} {label}")
            for pkg in packages:
                self.logger.track_package(pkg)
            return True

        self.logger.info(f"Installing {len(packages)} {label}...")

        # Use progress bar for visual feedback
        with self.logger.progress_bar(f"Installing {label}", len(packages)) as progress:
            # Install all packages at once (most package managers handle this efficiently)
            success = pkg_manager.install(packages)

            if progress:
                # Update progress to complete
                progress.update(progress._task_id, completed=len(packages))

        if success:
            # Track packages for summary (clean up .cask suffix for display)
            for pkg in packages:
                display_name = pkg.replace('.cask', ' (cask)') if pkg.endswith('.cask') else pkg
                self.logger.track_package(display_name)

        return success
