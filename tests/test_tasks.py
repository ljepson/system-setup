"""Tests for task system: BaseTask, TaskRegistry, and PackagesTask."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestBaseTask:
    """Tests for BaseTask abstract base class."""

    def test_base_task_is_abstract(self):
        """Test that BaseTask cannot be instantiated directly."""
        from system_setup.tasks.base import BaseTask

        with pytest.raises(TypeError):
            BaseTask(
                config=MagicMock(),
                state=MagicMock(),
                platform=MagicMock(),
            )

    def test_base_task_properties_required(self):
        """Test that subclasses must implement required properties."""
        from system_setup.tasks.base import BaseTask

        class IncompleteTask(BaseTask):
            pass

        with pytest.raises(TypeError):
            IncompleteTask(
                config=MagicMock(),
                state=MagicMock(),
                platform=MagicMock(),
            )

    def test_base_task_complete_subclass(self):
        """Test that a properly implemented subclass works."""
        from system_setup.tasks.base import BaseTask

        class CompleteTask(BaseTask):
            @property
            def name(self) -> str:
                return 'test-task'

            @property
            def description(self) -> str:
                return 'Test Task'

            def run(self) -> bool:
                return True

        task = CompleteTask(
            config=MagicMock(),
            state=MagicMock(),
            platform=MagicMock(),
        )
        assert task.name == 'test-task'
        assert task.description == 'Test Task'
        assert task.state_key == 'test-task_configured'  # Default

    def test_base_task_skip_if_complete(self):
        """Test skip_if_complete behavior."""
        from system_setup.tasks.base import BaseTask

        class SimpleTask(BaseTask):
            @property
            def name(self) -> str:
                return 'simple'

            @property
            def description(self) -> str:
                return 'Simple Task'

            def run(self) -> bool:
                return True

        mock_state = MagicMock()
        mock_state.is_complete.return_value = True

        task = SimpleTask(
            config=MagicMock(),
            state=mock_state,
            platform=MagicMock(),
        )

        assert task.skip_if_complete() is True
        mock_state.is_complete.assert_called_with('simple_configured')

    def test_base_task_is_supported(self):
        """Test platform support checking."""
        from system_setup.tasks.base import BaseTask

        class LinuxOnlyTask(BaseTask):
            @property
            def name(self) -> str:
                return 'linux-only'

            @property
            def description(self) -> str:
                return 'Linux Only Task'

            @property
            def platforms(self) -> list[str]:
                return ['linux']

            def run(self) -> bool:
                return True

        mock_platform_linux = MagicMock()
        mock_platform_linux.is_linux = True
        mock_platform_linux.is_macos = False
        mock_platform_linux.is_windows = False

        mock_platform_macos = MagicMock()
        mock_platform_macos.is_linux = False
        mock_platform_macos.is_macos = True
        mock_platform_macos.is_windows = False

        task_linux = LinuxOnlyTask(
            config=MagicMock(),
            state=MagicMock(),
            platform=mock_platform_linux,
        )
        task_macos = LinuxOnlyTask(
            config=MagicMock(),
            state=MagicMock(),
            platform=mock_platform_macos,
        )

        assert task_linux.is_supported() is True
        assert task_macos.is_supported() is False


class TestTaskRegistry:
    """Tests for TaskRegistry."""

    def test_registry_discovers_tasks(self):
        """Test that registry can discover task classes."""
        from system_setup.tasks.registry import get_registry

        registry = get_registry()
        tasks = registry.list_tasks()

        assert isinstance(tasks, list)
        # Should find at least some tasks
        assert len(tasks) > 0

    def test_registry_contains_known_tasks(self):
        """Test registry contains expected tasks."""
        from system_setup.tasks.registry import get_registry

        registry = get_registry()
        tasks = registry.list_tasks()

        # These tasks should be registered
        expected_tasks = ['packages', 'chezmoi', 'fish', 'modern-tools', 'settings', 'shell']
        for task_name in expected_tasks:
            assert task_name in tasks, f"Expected task '{task_name}' not found in registry"

    def test_registry_get_task_class(self):
        """Test getting a specific task class."""
        from system_setup.tasks.registry import get_registry
        from system_setup.tasks.base import BaseTask

        registry = get_registry()
        task_class = registry.get('packages')

        assert task_class is not None
        assert issubclass(task_class, BaseTask)

    def test_registry_get_nonexistent_task(self):
        """Test getting a task that doesn't exist."""
        from system_setup.tasks.registry import get_registry

        registry = get_registry()
        task_class = registry.get('nonexistent-task')

        assert task_class is None

    def test_registry_create_task_instance(self):
        """Test creating a task instance through registry."""
        from system_setup.tasks.registry import get_registry

        registry = get_registry()

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = registry.create_task(
            'packages',
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
            dry_run=True,
        )

        assert task is not None
        assert task.name == 'packages'
        assert task.dry_run is True


class TestPackagesTask:
    """Tests for PackagesTask."""

    def test_packages_task_initialization(self):
        """Test PackagesTask initializes correctly."""
        from system_setup.tasks.packages import PackagesTask
        from system_setup.tasks.base import BaseTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        task = PackagesTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
            dry_run=True,
        )

        assert isinstance(task, BaseTask)
        assert task.name == 'packages'
        assert task.description == 'Package Installation'
        assert task.state_key == 'packages_installed'
        assert task.dry_run is True

    def test_packages_task_skips_if_complete(self):
        """Test PackagesTask skips if already complete."""
        from system_setup.tasks.packages import PackagesTask

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_state.is_complete.return_value = True
        mock_platform = MagicMock()

        task = PackagesTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
        )

        result = task.run()
        assert result is True
        mock_state.is_complete.assert_called_with('packages_installed')

    def test_packages_task_get_packages(self):
        """Test package list retrieval."""
        from system_setup.tasks.packages import PackagesTask

        mock_config = MagicMock()
        mock_config.get_packages_for_platform.return_value = ['vim', 'git', 'curl']

        mock_state = MagicMock()
        mock_platform = MagicMock()
        mock_platform.is_macos = True
        mock_platform.is_linux = False
        mock_platform.is_windows = False

        task = PackagesTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
        )

        packages = task._get_packages()
        assert isinstance(packages, list)

    @patch('system_setup.packages.factory.get_package_manager')
    def test_packages_task_dry_run(self, mock_get_pm):
        """Test PackagesTask in dry-run mode."""
        from system_setup.tasks.packages import PackagesTask

        mock_pm = MagicMock()
        mock_pm.name = 'mock-pm'
        mock_pm.update.return_value = True
        mock_get_pm.return_value = mock_pm

        mock_config = MagicMock()
        mock_config.get_packages_for_platform.return_value = ['vim', 'git']

        mock_state = MagicMock()
        mock_state.is_complete.return_value = False

        mock_platform = MagicMock()
        mock_platform.is_macos = True
        mock_platform.is_linux = False
        mock_platform.is_windows = False

        task = PackagesTask(
            config=mock_config,
            state=mock_state,
            platform=mock_platform,
            dry_run=True,
            auto_yes=True,
        )

        result = task.run()
        assert result is True
        # In dry-run mode, install should not be called
        mock_pm.install.assert_not_called()


class TestAllTasksInheritFromBaseTask:
    """Test that all tasks properly inherit from BaseTask."""

    def test_all_tasks_inherit(self):
        """Verify all task classes inherit from BaseTask."""
        from system_setup.tasks.base import BaseTask
        from system_setup.tasks.packages import PackagesTask
        from system_setup.tasks.chezmoi import ChezmoiTask
        from system_setup.tasks.dotfiles import DotfilesTask
        from system_setup.tasks.fish import FishTask
        from system_setup.tasks.modern_tools import ModernToolsTask
        from system_setup.tasks.settings import SettingsTask
        from system_setup.tasks.shell import ShellTask
        from system_setup.tasks.hyprland import HyprlandTask

        tasks = [
            PackagesTask,
            ChezmoiTask,
            DotfilesTask,
            FishTask,
            ModernToolsTask,
            SettingsTask,
            ShellTask,
            HyprlandTask,
        ]

        for task_class in tasks:
            assert issubclass(task_class, BaseTask), \
                f"{task_class.__name__} does not inherit from BaseTask"

    def test_all_tasks_have_required_properties(self):
        """Verify all tasks implement required properties."""
        from system_setup.tasks.packages import PackagesTask
        from system_setup.tasks.chezmoi import ChezmoiTask
        from system_setup.tasks.dotfiles import DotfilesTask
        from system_setup.tasks.fish import FishTask
        from system_setup.tasks.modern_tools import ModernToolsTask
        from system_setup.tasks.settings import SettingsTask
        from system_setup.tasks.shell import ShellTask
        from system_setup.tasks.hyprland import HyprlandTask

        task_classes = [
            PackagesTask,
            ChezmoiTask,
            DotfilesTask,
            FishTask,
            ModernToolsTask,
            SettingsTask,
            ShellTask,
            HyprlandTask,
        ]

        mock_config = MagicMock()
        mock_state = MagicMock()
        mock_platform = MagicMock()

        for task_class in task_classes:
            task = task_class(
                config=mock_config,
                state=mock_state,
                platform=mock_platform,
            )

            # All tasks must have these
            assert isinstance(task.name, str), f"{task_class.__name__} name is not a string"
            assert len(task.name) > 0, f"{task_class.__name__} name is empty"
            assert isinstance(task.description, str), f"{task_class.__name__} description is not a string"
            assert isinstance(task.state_key, str), f"{task_class.__name__} state_key is not a string"
            assert callable(task.run), f"{task_class.__name__} run is not callable"
