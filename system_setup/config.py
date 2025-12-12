"""Configuration management for system setup."""

import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.

    Override values take precedence. Lists are replaced, not merged.

    Args:
        base: Base dictionary
        override: Override dictionary (takes precedence)

    Returns:
        Merged dictionary
    """
    result = deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)

    return result


class Config:
    """Manages configuration from files and environment variables.

    Configuration is loaded in layers:
    1. Built-in defaults (defaults.yaml in package)
    2. User config file (~/.system_setup.yaml or ./system_setup.yaml)
    3. Profile overrides (if --profile specified)
    4. Environment variables (highest precedence)
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        profile: Optional[str] = None,
    ) -> None:
        """
        Initialize configuration.

        Args:
            config_path: Optional path to configuration file.
                        If not provided, searches standard locations.
            profile: Optional profile name to apply (e.g., 'server', 'desktop')
        """
        self._config: Dict[str, Any] = {}
        self._profile = profile
        self._load_defaults()
        self._load_user_config(config_path)
        self._apply_profile(profile)

    def _load_defaults(self) -> None:
        """Load built-in defaults from package."""
        defaults_path = Path(__file__).parent / "defaults.yaml"

        if defaults_path.exists():
            try:
                with defaults_path.open("r") as f:
                    self._config = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid defaults.yaml: {e}") from e

    def _load_user_config(self, config_path: Optional[Path] = None) -> None:
        """
        Load and merge user configuration.

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
                        user_config = yaml.safe_load(f) or {}
                    # Deep merge user config over defaults
                    self._config = deep_merge(self._config, user_config)
                    self._config_path = path
                    return
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid YAML in {path}: {e}") from e

        self._config_path = None

    def _apply_profile(self, profile: Optional[str]) -> None:
        """Apply profile overrides if specified."""
        if not profile:
            return

        profiles = self._config.get("profiles", {})
        if profile not in profiles:
            available = list(profiles.keys())
            raise ValueError(
                f"Unknown profile: {profile}. "
                f"Available profiles: {', '.join(available)}"
            )

        profile_config = profiles[profile]

        # Merge profile packages
        if "packages" in profile_config:
            self._config["packages"] = deep_merge(
                self._config.get("packages", {}),
                profile_config["packages"],
            )

        # Store skip_tasks for later
        self._config["_profile_skip_tasks"] = profile_config.get("skip_tasks", [])
        self._config["_active_profile"] = profile

    @property
    def active_profile(self) -> Optional[str]:
        """Get the active profile name."""
        return self._config.get("_active_profile")

    @property
    def profile_skip_tasks(self) -> List[str]:
        """Get tasks to skip based on active profile."""
        return self._config.get("_profile_skip_tasks", [])

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Supports nested keys with dot notation: 'packages.macos.formulae'

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Check environment variable first (e.g., SYSTEM_SETUP_PACKAGES_MACOS_FORMULAE)
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

    def list_profiles(self) -> Dict[str, str]:
        """
        Get available profiles with descriptions.

        Returns:
            Dict mapping profile name to description
        """
        profiles = self._config.get("profiles", {})
        return {
            name: config.get("description", "No description")
            for name, config in profiles.items()
        }

    # ==========================================================================
    # Package Configuration
    # ==========================================================================

    def get_packages_for_platform(
        self,
        platform_name: str,
        distro: Optional[str] = None,
    ) -> List[str]:
        """
        Get packages for a specific platform.

        Args:
            platform_name: 'macos', 'linux', or 'windows'
            distro: Linux distribution name (e.g., 'arch', 'debian')

        Returns:
            List of package names
        """
        packages = []
        pkg_config = self.get("packages", {})

        if platform_name == "macos":
            macos_config = pkg_config.get("macos", {})
            packages.extend(macos_config.get("formulae", []))
            # Add casks with .cask suffix
            for cask in macos_config.get("casks", []):
                packages.append(f"{cask}.cask")

        elif platform_name == "linux":
            linux_config = pkg_config.get("linux", {})
            # Common packages first
            packages.extend(linux_config.get("common", []))
            # Distro-specific packages
            if distro and distro in linux_config:
                packages.extend(linux_config[distro])

        elif platform_name == "windows":
            windows_config = pkg_config.get("windows", {})
            packages.extend(windows_config.get("winget", []))

        # Add additional packages
        packages.extend(self.additional_packages)

        return packages

    @property
    def additional_packages(self) -> List[str]:
        """Get list of additional packages to install."""
        return self.get_list('packages.additional', [])

    # ==========================================================================
    # Dotfiles Configuration
    # ==========================================================================

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
    def checksum_required(self) -> bool:
        """Whether checksum verification is required."""
        return self.get_bool('dotfiles.checksum_required', False)

    # ==========================================================================
    # Chezmoi Configuration
    # ==========================================================================

    @property
    def chezmoi(self) -> Dict[str, Any]:
        """Get chezmoi configuration section."""
        return self.get('chezmoi', {})

    @property
    def dotfiles_repo(self) -> Optional[str]:
        """Get dotfiles git repository URL for chezmoi."""
        return self.get('chezmoi.repo') or self.get('dotfiles.repo')

    # ==========================================================================
    # Security Configuration
    # ==========================================================================

    @property
    def security_profile(self) -> str:
        """Get security profile (normal, strict, reduced)."""
        return self.get('security.profile', 'normal')

    # ==========================================================================
    # Hyprland Configuration
    # ==========================================================================

    @property
    def hyprland(self) -> Dict[str, Any]:
        """Get Hyprland configuration section."""
        return self.get('hyprland', {})

    @property
    def hyprland_enabled(self) -> bool:
        """Whether to set up Hyprland desktop."""
        return self.get_bool('hyprland.enabled', True)

    @property
    def hyprland_terminal(self) -> str:
        """Get preferred terminal for Hyprland."""
        return self.get('hyprland.terminal', 'ghostty')

    @property
    def hyprland_launcher(self) -> str:
        """Get preferred launcher for Hyprland."""
        return self.get('hyprland.launcher', 'walker')

    @property
    def hyprland_bar(self) -> str:
        """Get preferred status bar for Hyprland."""
        return self.get('hyprland.bar', 'hyprpanel')

    @property
    def hyprland_theme(self) -> str:
        """Get Hyprland theme name."""
        return self.get('hyprland.theme', 'catppuccin-mocha')

    def get_hyprland_packages(self) -> Dict[str, List[str]]:
        """Get Hyprland packages by category."""
        hypr_pkg = self.get('hyprland.packages', {})
        return {
            'core': hypr_pkg.get('core', []),
            'utils': hypr_pkg.get('utils', []),
            'aur': hypr_pkg.get('aur', []),
        }

    def get_hyprland_theme_colors(self, theme: Optional[str] = None) -> Dict[str, str]:
        """Get colors for a Hyprland theme."""
        theme = theme or self.hyprland_theme
        themes = self.get('hyprland.themes', {})
        default = {
            'active_border': 'rgba(cba6f7ee) rgba(89b4faee) 45deg',
            'inactive_border': 'rgba(585b70aa)',
        }
        return themes.get(theme, default)

    # ==========================================================================
    # Fish Shell Configuration
    # ==========================================================================

    @property
    def fish(self) -> Dict[str, Any]:
        """Get Fish shell configuration section."""
        return self.get('fish', {})

    @property
    def fish_enabled(self) -> bool:
        """Whether to set up Fish shell."""
        return self.get_bool('fish.enabled', True)

    @property
    def fish_set_default(self) -> bool:
        """Whether to set Fish as default shell."""
        return self.get_bool('fish.set_default', True)

    @property
    def fish_plugins(self) -> List[str]:
        """Get Fish plugins to install."""
        return self.get_list('fish.plugins', [])

    @property
    def fish_abbreviations(self) -> Dict[str, str]:
        """Get Fish abbreviations."""
        return self.get('fish.abbreviations', {})

    # ==========================================================================
    # Modern Tools Configuration
    # ==========================================================================

    @property
    def modern_tools(self) -> Dict[str, Any]:
        """Get modern tools configuration section."""
        return self.get('modern_tools', {})

    @property
    def modern_tools_enabled(self) -> bool:
        """Whether to install modern CLI tools."""
        return self.get_bool('modern_tools.enabled', True)

    @property
    def modern_tools_skip(self) -> List[str]:
        """Get list of modern tools to skip installing."""
        return self.get_list('modern_tools.skip', [])

    def get_modern_tools(self) -> Dict[str, List[Dict]]:
        """Get modern tools configuration by category."""
        tools = self.get('modern_tools', {})
        return {
            'core': tools.get('core', []),
            'dev': tools.get('dev', []),
        }

    # ==========================================================================
    # Theme Configuration
    # ==========================================================================

    @property
    def theme(self) -> Dict[str, Any]:
        """Get theme configuration section."""
        return self.get('theme', {})

    @property
    def theme_colorscheme(self) -> str:
        """Get preferred colorscheme."""
        return self.get('theme.colorscheme', 'catppuccin-mocha')

    @property
    def theme_font(self) -> str:
        """Get preferred terminal font."""
        return self.get('theme.font', 'JetBrainsMono Nerd Font')

    @property
    def theme_icons(self) -> str:
        """Get preferred icon theme."""
        return self.get('theme.icons', 'Papirus-Dark')

    @property
    def theme_cursor(self) -> str:
        """Get preferred cursor theme."""
        return self.get('theme.cursor', 'catppuccin-mocha-dark-cursors')

    # ==========================================================================
    # Task Configuration
    # ==========================================================================

    @property
    def task_order(self) -> List[str]:
        """Get default task execution order."""
        return self.get_list('tasks.order', [
            'packages',
            'chezmoi',
            'modern-tools',
            'fish',
            'hyprland',
            'settings',
            'shell',
        ])

    def get_task_platforms(self, task_name: str) -> List[str]:
        """Get supported platforms for a task."""
        platforms = self.get('tasks.platforms', {})
        return platforms.get(task_name, [])
