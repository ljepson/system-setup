"""Tests for new modules: paru, chezmoi, fish, hyprland, modern_tools."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestParuManager:
    """Tests for ParuManager."""

    def test_paru_manager_name(self):
        """Test paru manager name property."""
        from system_setup.packages.paru import ParuManager

        manager = ParuManager(dry_run=True)
        assert manager.name == "paru"

    @patch('shutil.which')
    def test_paru_is_available(self, mock_which):
        """Test paru availability check."""
        from system_setup.packages.paru import ParuManager

        mock_which.return_value = "/usr/bin/paru"
        manager = ParuManager()
        assert manager.is_available() is True

        mock_which.return_value = None
        assert manager.is_available() is False

    @patch('shutil.which')
    def test_paru_can_install(self, mock_which):
        """Test paru installation prerequisites."""
        from system_setup.packages.paru import ParuManager

        # Both pacman and git available
        mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x in ['pacman', 'git'] else None
        assert ParuManager.can_install() is True

        # Only pacman available
        mock_which.side_effect = lambda x: "/usr/bin/pacman" if x == 'pacman' else None
        assert ParuManager.can_install() is False


class TestChezmoiTask:
    """Tests for ChezmoiTask."""

    def test_chezmoi_task_initialization(self):
        """Test ChezmoiTask initializes correctly."""
        from system_setup.tasks.chezmoi import ChezmoiTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = ChezmoiTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
            dry_run=True,
        )

        assert task.dry_run is True
        assert task.chezmoi_path == Path.home() / ".local" / "share" / "chezmoi"

    def test_chezmoi_skips_if_complete(self):
        """Test ChezmoiTask skips if already complete."""
        from system_setup.tasks.chezmoi import ChezmoiTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_state.is_complete.return_value = True
        mock_platform = MagicMock()

        task = ChezmoiTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
        )

        result = task.run()
        assert result is True
        mock_state.is_complete.assert_called_with('chezmoi_configured')


class TestFishTask:
    """Tests for FishTask."""

    def test_fish_task_initialization(self):
        """Test FishTask initializes correctly."""
        from system_setup.tasks.fish import FishTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = FishTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
            dry_run=True,
        )

        assert task.dry_run is True
        assert task.config_dir == Path.home() / ".config" / "fish"

    def test_fish_config_generation(self):
        """Test Fish config generation."""
        from system_setup.tasks.fish import FishTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = FishTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
        )

        config = task._generate_config()
        assert "fish_greeting" in config
        assert "mise" in config
        assert "zoxide" in config


class TestModernToolsTask:
    """Tests for ModernToolsTask."""

    def test_modern_tools_initialization(self):
        """Test ModernToolsTask initializes correctly."""
        from system_setup.tasks.modern_tools import ModernToolsTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = ModernToolsTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
            dry_run=True,
        )

        assert task.dry_run is True

    def test_modern_tools_list_methods(self):
        """Test tool listing methods."""
        from system_setup.tasks.modern_tools import ModernToolsTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = ModernToolsTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
        )

        # These methods should return lists
        installed = task.list_installed()
        available = task.list_available()

        assert isinstance(installed, list)
        assert isinstance(available, list)

    def test_modern_tools_tool_info(self):
        """Test tool info retrieval."""
        from system_setup.tasks.modern_tools import ModernToolsTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = ModernToolsTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
        )

        # Known tool
        info = task.get_tool_info("eza")
        assert info is not None
        assert "replaces" in info

        # Unknown tool
        assert task.get_tool_info("nonexistent") is None


class TestHyprlandTask:
    """Tests for HyprlandTask."""

    def test_hyprland_task_initialization(self):
        """Test HyprlandTask initializes correctly."""
        from system_setup.tasks.hyprland import HyprlandTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = HyprlandTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
            dry_run=True,
        )

        assert task.dry_run is True
        assert task.hypr_config_dir == Path.home() / ".config" / "hypr"


class TestConfigExtensions:
    """Tests for new Config properties."""

    def test_config_chezmoi_properties(self):
        """Test chezmoi-related config properties."""
        from system_setup.config import Config

        # Empty config should return defaults
        config = Config(config_path=Path("/nonexistent"))

        assert config.chezmoi == {}
        assert config.dotfiles_repo is None

    def test_config_hyprland_properties(self):
        """Test Hyprland-related config properties."""
        from system_setup.config import Config

        config = Config(config_path=Path("/nonexistent"))

        assert config.hyprland_enabled is True
        assert config.hyprland_terminal == "ghostty"
        assert config.hyprland_launcher == "walker"
        assert config.hyprland_bar == "hyprpanel"

    def test_config_fish_properties(self):
        """Test Fish-related config properties."""
        from system_setup.config import Config

        config = Config(config_path=Path("/nonexistent"))

        assert config.fish_enabled is True
        assert config.fish_set_default is True
        assert config.fish_plugins == []

    def test_config_modern_tools_properties(self):
        """Test modern tools-related config properties."""
        from system_setup.config import Config

        config = Config(config_path=Path("/nonexistent"))

        assert config.modern_tools_enabled is True
        assert config.modern_tools_skip == []

    def test_config_theme_properties(self):
        """Test theme-related config properties."""
        from system_setup.config import Config

        config = Config(config_path=Path("/nonexistent"))

        assert config.theme_colorscheme == "catppuccin-mocha"
        assert config.theme_font == "JetBrainsMono Nerd Font"
        assert config.theme_icons == "Papirus-Dark"
