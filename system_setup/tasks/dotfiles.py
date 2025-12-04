"""Dotfiles management task."""

import shutil
import tarfile
from pathlib import Path
from typing import Optional

from system_setup.config import Config
from system_setup.logger import get_logger
from system_setup.state import StateManager
from system_setup.utils.checksum import verify_sha256
from system_setup.utils.download import download_from_gdrive, install_gdown


class DotfilesTask:
    """Manages dotfiles download and installation."""

    def __init__(
        self,
        config: Config,
        state: StateManager,
        dry_run: bool = False,
        auto_yes: bool = False,
    ) -> None:
        """
        Initialize dotfiles task.

        Args:
            config: Configuration instance
            state: State manager instance
            dry_run: If True, don't actually make changes
            auto_yes: If True, automatically answer yes to prompts
        """
        self.config = config
        self.state = state
        self.dry_run = dry_run
        self.auto_yes = auto_yes
        self.logger = get_logger()

        self.temp_archive = Path("/tmp/dotfiles.tar.gz")
        self.temp_extract = Path("/tmp/dotfiles")

    def run(self) -> bool:
        """
        Execute dotfiles management task.

        Returns:
            True if successful
        """
        if self.state.is_complete('dotfiles_installed'):
            self.logger.info("Dotfiles already installed (skipping)")
            return True

        self.logger.section("Dotfiles Management")

        # Step 1: Download (if needed)
        if not self._download_dotfiles():
            return False

        # Step 2: Extract
        if not self._extract_dotfiles():
            return False

        # Step 3: Install to home directory
        if not self._install_dotfiles():
            return False

        # Step 4: Cleanup
        self._cleanup()

        self.state.mark_complete('dotfiles_installed')
        self.logger.success("Dotfiles management complete")
        return True

    def _download_dotfiles(self) -> bool:
        """Download dotfiles from Google Drive."""
        # Check if already downloaded
        if self.temp_archive.exists():
            self.logger.info(f"Found existing dotfiles archive: {self.temp_archive}")
            return self._verify_checksum()

        if self.temp_extract.exists() and (self.temp_extract / "dotfiles").exists():
            self.logger.info(f"Found existing extracted dotfiles: {self.temp_extract}")
            return True

        # Ask user if they want to download
        if not self.auto_yes:
            response = input(f"Download dotfiles to {self.temp_archive}? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipping dotfiles download")
                return False
        else:
            self.logger.info("Auto-yes: downloading dotfiles")

        if self.dry_run:
            self.logger.info("[DRY RUN] Would download dotfiles")
            return True

        # Ensure gdown is installed
        if not install_gdown():
            self.logger.warning("Could not install gdown - attempting download anyway")

        try:
            self.logger.info("Downloading dotfiles from Google Drive...")
            gdrive_id = self.config.dotfiles_gdrive_id
            download_from_gdrive(gdrive_id, self.temp_archive)
            self.logger.success("Download complete")

            return self._verify_checksum()

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            return False

    def _verify_checksum(self) -> bool:
        """Verify checksum of downloaded archive."""
        expected_checksum = self.config.dotfiles_checksum

        if expected_checksum is None:
            self.logger.info("Checksum verification disabled")
            return True

        if not self.temp_archive.exists():
            return True

        try:
            self.logger.info("Verifying checksum...")
            if verify_sha256(self.temp_archive, expected_checksum):
                self.logger.success("✅ Checksum verified successfully")
                return True
            else:
                self.logger.error("❌ Checksum verification failed!")
                self.logger.error(f"   Expected: {expected_checksum}")

                if self.config.checksum_required:
                    self.logger.error("   Removing potentially compromised file...")
                    self.temp_archive.unlink()
                    return False
                else:
                    self.logger.warning("   Continuing anyway (checksum not required)")
                    return True

        except Exception as e:
            self.logger.error(f"Checksum verification error: {e}")
            return False

    def _extract_dotfiles(self) -> bool:
        """Extract dotfiles archive."""
        if (self.temp_extract / "dotfiles").exists():
            self.logger.info("Dotfiles already extracted")
            return True

        if self.dry_run:
            self.logger.info("[DRY RUN] Would extract dotfiles")
            return True

        if not self.temp_archive.exists():
            self.logger.warning("No dotfiles archive found")
            return False

        try:
            self.logger.info(f"Extracting dotfiles to {self.temp_extract}...")
            self.temp_extract.mkdir(parents=True, exist_ok=True)

            with tarfile.open(self.temp_archive, 'r:gz') as tar:
                tar.extractall(self.temp_extract)

            self.logger.success("Extraction complete")
            return True

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            return False

    def _install_dotfiles(self) -> bool:
        """Install dotfiles to home directory."""
        source_dir = self.temp_extract / "dotfiles"

        if self.dry_run:
            self.logger.info("[DRY RUN] Would install dotfiles to home directory")
            return True

        if not source_dir.exists():
            self.logger.error(f"Dotfiles directory not found: {source_dir}")
            return False

        # Ask user confirmation
        if not self.auto_yes:
            response = input(f"Install dotfiles from {source_dir} to home directory? (y/N): ")
            if response.lower() not in ('y', 'yes'):
                self.logger.info("Skipping dotfiles installation")
                self.logger.info(f"Dotfiles remain in {self.temp_extract} for manual processing")
                return True
        else:
            self.logger.info("Auto-yes: installing dotfiles")

        try:
            dest_dir = Path.home()
            self.logger.info(f"Installing dotfiles from {source_dir} to {dest_dir}...")

            # Process each dotfile/directory
            for item in source_dir.glob('.*'):
                # Skip . and ..
                if item.name in ('.', '..'):
                    continue

                dest_path = dest_dir / item.name

                if item.is_file():
                    self._install_file(item, dest_path)
                elif item.is_dir():
                    self._install_directory(item, dest_path)

            self.logger.success("Dotfiles installed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Installation failed: {e}")
            return False

    def _install_file(self, source: Path, dest: Path) -> None:
        """Install a single dotfile."""
        self.logger.debug(f"Processing file: {source.name}")

        if dest.exists():
            if not self.auto_yes:
                response = input(f"  File '{source.name}' exists. Replace? (y/N): ")
                if response.lower() not in ('y', 'yes'):
                    self.logger.info(f"  Skipped: {source.name}")
                    return

            # Create backup
            backup_path = dest.with_suffix(dest.suffix + '.backup')
            shutil.copy2(dest, backup_path)
            self.logger.info(f"  Created backup: {backup_path}")

        shutil.copy2(source, dest)
        self.logger.info(f"  Installed: {source.name}")

    def _install_directory(self, source: Path, dest: Path) -> None:
        """Install a dotfile directory with merge support."""
        self.logger.debug(f"Processing directory: {source.name}")

        if dest.exists() and dest.is_dir():
            if not self.auto_yes:
                response = input(f"  Directory '{source.name}' exists. Merge contents? (y/N): ")
                if response.lower() not in ('y', 'yes'):
                    self.logger.info(f"  Skipped: {source.name}")
                    return

            # Merge directories using rsync-like behavior
            self._merge_directories(source, dest)
        else:
            # Just copy the whole directory
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(source, dest)
            self.logger.info(f"  Installed directory: {source.name}")

    def _merge_directories(self, source: Path, dest: Path) -> None:
        """Merge two directories, preserving newer files."""
        for item in source.rglob('*'):
            relative_path = item.relative_to(source)
            dest_item = dest / relative_path

            if item.is_file():
                # Copy file if it doesn't exist or source is newer
                if not dest_item.exists() or item.stat().st_mtime > dest_item.stat().st_mtime:
                    dest_item.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_item)
            elif item.is_dir():
                dest_item.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"  Merged directory: {source.name}")

    def _cleanup(self) -> None:
        """Clean up temporary files."""
        if self.dry_run:
            self.logger.info("[DRY RUN] Would clean up temporary files")
            return

        self.logger.info("Cleaning up temporary files...")

        if self.temp_archive.exists():
            self.temp_archive.unlink()
            self.logger.debug(f"  Removed: {self.temp_archive}")

        if self.temp_extract.exists():
            shutil.rmtree(self.temp_extract)
            self.logger.debug(f"  Removed: {self.temp_extract}")

        self.logger.success("Cleanup complete")
