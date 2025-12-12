"""Task registry for dynamic task discovery and management."""

from typing import Any, Dict, List, Optional, Type

from system_setup.config import Config
from system_setup.platform import Platform
from system_setup.state import StateManager
from system_setup.tasks.base import BaseTask


# Descriptions for legacy tasks that don't have description property
TASK_DESCRIPTIONS: Dict[str, str] = {
    'packages': 'Package Installation',
    'chezmoi': 'Chezmoi Dotfiles Management',
    'dotfiles': 'Dotfiles Management (Legacy)',
    'fish': 'Fish Shell Configuration',
    'hyprland': 'Hyprland Desktop Environment',
    'modern-tools': 'Modern CLI Tools Installation',
    'settings': 'System Settings',
    'shell': 'Shell Configuration',
}

# State keys for legacy tasks
TASK_STATE_KEYS: Dict[str, str] = {
    'packages': 'packages_installed',
    'chezmoi': 'chezmoi_configured',
    'dotfiles': 'dotfiles_installed',
    'fish': 'fish_configured',
    'hyprland': 'hyprland_setup',
    'modern-tools': 'modern_tools_installed',
    'settings': 'settings_applied',
    'shell': 'shell_configured',
}


class TaskRegistry:
    """Registry for managing available setup tasks.

    Provides:
    - Task registration and discovery
    - Dependency resolution
    - Platform filtering
    - Task instantiation
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._tasks: Dict[str, Type[BaseTask]] = {}

    def register(self, task_class: Type[BaseTask]) -> Type[BaseTask]:
        """
        Register a task class.

        Can be used as a decorator:
            @registry.register
            class MyTask(BaseTask):
                ...

        Args:
            task_class: Task class to register

        Returns:
            The task class (unchanged)
        """
        # Create a temporary instance to get the name
        # This is a bit awkward but necessary since name is a property
        # We'll use __name__ as a fallback
        name = getattr(task_class, '__task_name__', None)
        if name is None:
            # Extract name from class name (e.g., PackagesTask -> packages)
            class_name = task_class.__name__
            if class_name.endswith('Task'):
                name = class_name[:-4].lower()
            else:
                name = class_name.lower()

        self._tasks[name] = task_class
        return task_class

    def register_with_name(self, name: str):
        """
        Register a task class with a specific name.

        Usage:
            @registry.register_with_name('packages')
            class PackageInstallTask(BaseTask):
                ...

        Args:
            name: Name to register the task under

        Returns:
            Decorator function
        """
        def decorator(task_class: Type[BaseTask]) -> Type[BaseTask]:
            self._tasks[name] = task_class
            return task_class
        return decorator

    def get(self, name: str) -> Optional[Type[BaseTask]]:
        """
        Get a task class by name.

        Args:
            name: Task name

        Returns:
            Task class or None if not found
        """
        return self._tasks.get(name)

    def list_tasks(self) -> List[str]:
        """
        Get list of all registered task names.

        Returns:
            Sorted list of task names
        """
        return sorted(self._tasks.keys())

    def list_tasks_for_platform(
        self,
        platform: Platform,
        config: Config,
        state: StateManager,
    ) -> List[str]:
        """
        Get list of tasks supported on the given platform.

        Args:
            platform: Platform instance
            config: Config instance (for instantiation)
            state: State instance (for instantiation)

        Returns:
            List of supported task names
        """
        supported = []
        for name, task_class in self._tasks.items():
            task = task_class(
                config=config,
                state=state,
                platform=platform,
            )
            if task.is_supported():
                supported.append(name)
        return sorted(supported)

    def create_task(
        self,
        name: str,
        config: Config,
        state: StateManager,
        platform: Platform,
        dry_run: bool = False,
        auto_yes: bool = False,
    ) -> Optional[Any]:
        """
        Create a task instance by name.

        Args:
            name: Task name
            config: Configuration instance
            state: State manager instance
            platform: Platform instance
            dry_run: Dry run mode
            auto_yes: Auto-yes mode

        Returns:
            Task instance or None if not found
        """
        task_class = self.get(name)
        if task_class is None:
            return None

        # Try with platform first, fall back to without for legacy tasks
        try:
            return task_class(
                config=config,
                state=state,
                platform=platform,
                dry_run=dry_run,
                auto_yes=auto_yes,
            )
        except TypeError:
            # Legacy task without platform parameter (e.g., DotfilesTask)
            return task_class(
                config=config,
                state=state,
                dry_run=dry_run,
                auto_yes=auto_yes,
            )

    def get_task_info(
        self,
        name: str,
        config: Config,
        state: StateManager,
        platform: Platform,
    ) -> Optional[Dict[str, any]]:
        """
        Get information about a task.

        Args:
            name: Task name
            config: Config instance
            state: State instance
            platform: Platform instance

        Returns:
            Dict with name, description, supported status
        """
        task_class = self.get(name)
        if task_class is None:
            return None

        # Handle legacy tasks that don't take platform in constructor
        try:
            task = task_class(
                config=config,
                state=state,
                platform=platform,
            )
        except TypeError:
            # Legacy task without platform parameter (e.g., DotfilesTask)
            task = task_class(
                config=config,
                state=state,
            )

        # Get task properties with fallbacks for legacy tasks
        task_name = getattr(task, 'name', name)
        description = getattr(task, 'description', TASK_DESCRIPTIONS.get(name, name.title()))

        # Check supported status
        if hasattr(task, 'is_supported'):
            supported = task.is_supported()
        else:
            # Legacy: check platform attribute or default to True
            supported = True
            if hasattr(task, 'platforms') and task.platforms:
                if platform.is_macos and 'macos' not in task.platforms:
                    supported = False
                elif platform.is_linux and 'linux' not in task.platforms:
                    supported = False
                elif platform.is_windows and 'windows' not in task.platforms:
                    supported = False

        # Check completion status
        if hasattr(task, 'is_complete'):
            complete = task.is_complete()
        else:
            # Legacy: check state directly
            state_key = TASK_STATE_KEYS.get(name, f'{name}_configured')
            complete = state.is_complete(state_key)

        # Get dependencies
        depends_on = getattr(task, 'depends_on', [])

        return {
            'name': task_name,
            'description': description,
            'supported': supported,
            'complete': complete,
            'depends_on': depends_on,
        }

    def resolve_dependencies(self, task_names: List[str]) -> List[str]:
        """
        Resolve task dependencies and return execution order.

        Uses topological sort to ensure dependencies run first.

        Args:
            task_names: List of task names to run

        Returns:
            Ordered list of task names with dependencies resolved

        Raises:
            ValueError: If circular dependency detected
        """
        # Build dependency graph
        # For now, we'll implement a simple version that assumes
        # dependencies are already registered
        # Full implementation would do topological sort

        # Simple approach: just ensure we have all names
        # A more sophisticated version would analyze depends_on
        return task_names


# Global registry instance
_registry: Optional[TaskRegistry] = None


def get_registry() -> TaskRegistry:
    """Get or create the global task registry."""
    global _registry
    if _registry is None:
        _registry = TaskRegistry()
        _register_default_tasks(_registry)
    return _registry


def _register_default_tasks(registry: TaskRegistry) -> None:
    """Register all default tasks."""
    # Import task classes
    from system_setup.tasks.packages import PackagesTask
    from system_setup.tasks.chezmoi import ChezmoiTask
    from system_setup.tasks.dotfiles import DotfilesTask
    from system_setup.tasks.fish import FishTask
    from system_setup.tasks.hyprland import HyprlandTask
    from system_setup.tasks.modern_tools import ModernToolsTask
    from system_setup.tasks.settings import SettingsTask
    from system_setup.tasks.shell import ShellTask

    # Register with explicit names
    registry._tasks['packages'] = PackagesTask
    registry._tasks['chezmoi'] = ChezmoiTask
    registry._tasks['dotfiles'] = DotfilesTask
    registry._tasks['fish'] = FishTask
    registry._tasks['hyprland'] = HyprlandTask
    registry._tasks['modern-tools'] = ModernToolsTask
    registry._tasks['settings'] = SettingsTask
    registry._tasks['shell'] = ShellTask
