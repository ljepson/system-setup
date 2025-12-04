"""Tests for utility functions."""

import tempfile
from pathlib import Path

import pytest

from system_setup.utils.checksum import calculate_sha256, verify_sha256


def test_calculate_sha256(tmp_path):
    """Test SHA256 calculation."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    # Known SHA256 of "Hello, World!"
    expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    actual = calculate_sha256(test_file)

    assert actual == expected


def test_verify_sha256_success(tmp_path):
    """Test successful checksum verification."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    expected = "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
    assert verify_sha256(test_file, expected) is True


def test_verify_sha256_failure(tmp_path):
    """Test failed checksum verification."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    wrong_hash = "0" * 64
    assert verify_sha256(test_file, wrong_hash) is False


def test_verify_sha256_missing_file(tmp_path):
    """Test checksum verification with missing file."""
    missing_file = tmp_path / "nonexistent.txt"

    with pytest.raises(FileNotFoundError):
        verify_sha256(missing_file, "0" * 64)
