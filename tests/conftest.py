"""Pytest configuration and fixtures."""

import pytest

from system_setup.logger import setup_logger


@pytest.fixture(autouse=True)
def setup_test_logger():
    """Set up logger for all tests."""
    setup_logger(verbose=False, quiet=True)
    yield


@pytest.fixture
def mock_config():
    """Create a mock Config object."""
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def mock_state():
    """Create a mock StateManager object."""
    from unittest.mock import MagicMock
    return MagicMock()


@pytest.fixture
def mock_platform():
    """Create a mock Platform object."""
    from unittest.mock import MagicMock
    platform = MagicMock()
    platform.is_macos = True
    platform.is_linux = False
    platform.is_windows = False
    return platform
