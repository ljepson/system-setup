"""Tests for configuration management."""

import tempfile
from pathlib import Path

import pytest

from system_setup.config import Config


def test_config_defaults():
    """Test default configuration values."""
    config = Config()
    assert config.security_profile == 'normal'
    assert config.additional_packages == []


def test_config_from_yaml(tmp_path):
    """Test loading configuration from YAML file."""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text("""
packages:
  additional_packages:
    - docker
    - terraform

security:
  profile: strict
""")

    config = Config(config_path=config_file)
    assert config.additional_packages == ['docker', 'terraform']
    assert config.security_profile == 'strict'


def test_config_get_nested():
    """Test getting nested configuration values."""
    config = Config()
    # Should not raise
    value = config.get('nonexistent.nested.key', 'default')
    assert value == 'default'
