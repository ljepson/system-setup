"""Checksum verification utilities."""

import hashlib
from pathlib import Path


def calculate_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calculate SHA256 checksum of a file.

    Args:
        file_path: Path to file
        chunk_size: Read chunk size in bytes

    Returns:
        Hex string of SHA256 hash
    """
    sha256 = hashlib.sha256()

    with file_path.open('rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)

    return sha256.hexdigest()


def verify_sha256(file_path: Path, expected_hash: str) -> bool:
    """
    Verify SHA256 checksum of a file.

    Args:
        file_path: Path to file
        expected_hash: Expected SHA256 hash (hex string)

    Returns:
        True if checksum matches

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    actual_hash = calculate_sha256(file_path)
    return actual_hash.lower() == expected_hash.lower()
