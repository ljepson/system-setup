"""Configuration management for system setup."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class Config:
    """Manages configuration from files and environment variables."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Initialize configuration.

        Args:
            config_path: Optional path to configuration file.
                        If not provided, searches standard locations.
        """
        self._config: Dict[str, Any] = {}
        self._load_config(config_path)

    def _load_config(self, config_path: Optional[Path] = None) -> None:
        """
        Load configuration from file(s).

        Search order:
        1. Provided config_path
        2. ./system_setup.yaml
        3. ./system_setup.yml
        4. ~/.system_setup.yaml
        5. ~/.system_setup.yml
        6. ~/.config/system_setup.yaml
        """
        search_paths: List[Path] = []

        if config_path:
            search_paths.append(config_path)
        else:
            # Current directory
            search_paths.extend([
                Path.cwd() / "system_setup.yaml",
                Path.cwd() / "system_setup.yml",
            ])

            # Home directory
            home = Path.home()
            search_paths.extend([
                home / ".system_setup.yaml",
                home / ".system_setup.yml",
                home / ".config" / "system_setup.yaml",
                home / ".config" / "system_setup.yml",
            ])

        for path in search_paths:
            if path.exists() and path.is_file():
                try:
                    with path.open("r") as f:
                        self._config = yaml.safe_load(f) or {}
                    return
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid YAML in {path}: {e}") from e

        # No config file found - use defaults
        self._config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Supports nested keys with dot notation: 'packages.additional_packages'

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Check environment variable first (e.g., SYSTEM_SETUP_PACKAGES_ADDITIONAL_PACKAGES)
        env_key = f"SYSTEM_SETUP_{key.upper().replace('.', '_')}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        # Navigate nested dict
        value = self._config
        for part in key.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """
        Get configuration value as a list.

        If value is a comma-separated string, split it.
        If value is already a list, return as-is.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            List of values
        """
        if default is None:
            default = []

        value = self.get(key, default)

        if isinstance(value, str):
            # Split comma-separated string
            return [v.strip() for v in value.split(',') if v.strip()]
        elif isinstance(value, list):
            return value
        else:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Get configuration value as boolean.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Boolean value
        """
        value = self.get(key, default)

        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        else:
            return bool(value)

    @property
    def dotfiles_gdrive_id(self) -> str:
        """Get Google Drive ID for dotfiles."""
        return self.get(
            'dotfiles.gdrive_id',
            '1ijyAcpSGqlYji-ojPBnsSnaMmpj7Dn4D'
        )

    @property
    def dotfiles_checksum(self) -> Optional[str]:
        """Get expected SHA256 checksum for dotfiles (None to skip verification)."""
        checksum = self.get('dotfiles.checksum', 'skip')
        return None if checksum == 'skip' else checksum

    @property
    def additional_packages(self) -> List[str]:
        """Get list of additional packages to install."""
        return self.get_list('packages.additional_packages', [])

    @property
    def security_profile(self) -> str:
        """Get security profile (normal, strict, reduced)."""
        return self.get('security.profile', 'normal')

    @property
    def checksum_required(self) -> bool:
        """Whether checksum verification is required."""
        return self.get_bool('dotfiles.checksum_required', False)
