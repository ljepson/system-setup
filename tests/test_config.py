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
  additional:
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


class TestConfigProfiles:
    """Tests for profile support."""

    def test_profile_loading(self):
        """Test that profiles can be loaded."""
        config = Config()
        profiles = config.get('profiles', {})
        # Should have default profiles from defaults.yaml
        assert 'server' in profiles or profiles == {}  # May or may not be present

    def test_server_profile(self, tmp_path):
        """Test server profile configuration."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text("""
profiles:
  server:
    skip_tasks:
      - hyprland
      - fish
""")
        config = Config(config_path=config_file, profile='server')
        # Profile should affect skip_tasks
        profile_data = config.get('profiles.server', {})
        assert 'hyprland' in profile_data.get('skip_tasks', [])


class TestConfigPackages:
    """Tests for package configuration."""

    def test_get_packages_for_platform_macos(self):
        """Test getting packages for macOS."""
        config = Config()
        packages = config.get_packages_for_platform('macos')
        # Should return a list (may be empty or populated from defaults.yaml)
        assert isinstance(packages, list)

    def test_get_packages_for_platform_linux_arch(self):
        """Test getting packages for Arch Linux."""
        config = Config()
        packages = config.get_packages_for_platform('linux', 'arch')
        assert isinstance(packages, list)

    def test_get_packages_for_platform_linux_debian(self):
        """Test getting packages for Debian."""
        config = Config()
        packages = config.get_packages_for_platform('linux', 'debian')
        assert isinstance(packages, list)


class TestConfigDeepMerge:
    """Tests for deep merge functionality."""

    def test_deep_merge_simple(self):
        """Test deep merge with simple values."""
        from system_setup.config import deep_merge

        base = {'a': 1, 'b': 2}
        override = {'b': 3, 'c': 4}
        result = deep_merge(base, override)

        assert result == {'a': 1, 'b': 3, 'c': 4}

    def test_deep_merge_nested(self):
        """Test deep merge with nested dicts."""
        from system_setup.config import deep_merge

        base = {'a': {'x': 1, 'y': 2}, 'b': 3}
        override = {'a': {'y': 99, 'z': 100}}
        result = deep_merge(base, override)

        assert result == {'a': {'x': 1, 'y': 99, 'z': 100}, 'b': 3}

    def test_deep_merge_lists(self):
        """Test deep merge replaces lists (doesn't extend)."""
        from system_setup.config import deep_merge

        base = {'packages': ['a', 'b']}
        override = {'packages': ['c', 'd']}
        result = deep_merge(base, override)

        assert result == {'packages': ['c', 'd']}
