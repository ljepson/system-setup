"""Download utilities."""

import subprocess
from pathlib import Path
from typing import Optional

import requests


def download_file(url: str, destination: Path, timeout: int = 300) -> bool:
    """
    Download a file from URL.

    Args:
        url: URL to download from
        destination: Destination file path
        timeout: Download timeout in seconds

    Returns:
        True if download successful

    Raises:
        requests.RequestException: If download fails
    """
    try:
        # Ensure parent directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Stream download to handle large files
        response = requests.get(url, stream=True, timeout=timeout)
        response.raise_for_status()

        # Write to file
        with destination.open('wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return True
    except requests.RequestException as e:
        # Clean up partial download
        if destination.exists():
            destination.unlink()
        raise


def download_from_gdrive(file_id: str, destination: Path) -> bool:
    """
    Download a file from Google Drive using gdown.

    Args:
        file_id: Google Drive file ID
        destination: Destination file path

    Returns:
        True if download successful

    Raises:
        RuntimeError: If gdown is not available or download fails
    """
    try:
        # Check if gdown is available
        result = subprocess.run(
            ['gdown', '--version'],
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError("gdown is not installed. Install with: pip install gdown")

        # Ensure parent directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # Download using gdown
        cmd = ['gdown', file_id, '-O', str(destination)]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        return destination.exists()

    except subprocess.CalledProcessError as e:
        # Clean up partial download
        if destination.exists():
            destination.unlink()
        raise RuntimeError(f"gdown failed: {e.stderr}") from e


def install_gdown() -> bool:
    """
    Install gdown using pip.

    Returns:
        True if installation successful or gdown already installed
    """
    # Check if already installed
    result = subprocess.run(
        ['gdown', '--version'],
        capture_output=True,
        check=False,
    )
    if result.returncode == 0:
        return True

    # Try to install
    try:
        subprocess.run(
            ['pip3', 'install', 'gdown', '--user'],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        # Try alternative installation method
        try:
            subprocess.run(
                ['pip', 'install', 'gdown', '--user'],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
