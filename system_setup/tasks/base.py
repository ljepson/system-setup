"""Base task abstraction for system setup."""

from abc import ABC, abstractmethod
from typing import Optional

from system_setup.config import Config
from system_setup.logger import SetupLogger, get_logger
from system_setup.platform import Platform
from system_setup.state import StateManager
from system_setup.utils.command import CommandRunner


class BaseTask(ABC):
    """Abstract base class for all setup tasks.

    All tasks must implement:
    - name: Unique identifier for the task (e.g., 'packages', 'shell')
    - description: Human-readable description
    - run(): Execute the task and return success status

    Tasks optionally implement:
    - platforms: List of supported platforms (default: all)
    - depends_on: List of task names that must run first
    """

    def __init__(
        self,
        config: Config,
        state: StateManager,
        platform: Platform,
        dry_run: bool = False,
        auto_yes: bool = False,
    ) -> None:
        """
        Initialize task.

        Args:
            config: Configuration instance
            state: State manager instance
            platform: Platform instance
            dry_run: If True, don't actually make changes
            auto_yes: If True, automatically answer yes to prompts
        """
        self.config = config
        self.state = state
        self.platform = platform
        self.dry_run = dry_run
        self.auto_yes = auto_yes
        self._logger: Optional[SetupLogger] = None
        self._cmd: Optional[CommandRunner] = None

    @property
    def logger(self) -> SetupLogger:
        """Get logger instance (lazy initialization)."""
        if self._logger is None:
            self._logger = get_logger()
        return self._logger

    @property
    def cmd(self) -> CommandRunner:
        """Get command runner instance (lazy initialization)."""
        if self._cmd is None:
            self._cmd = CommandRunner(dry_run=self.dry_run)
        return self._cmd

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique task identifier (e.g., 'packages', 'shell')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable task description."""
        pass

    @property
    def state_key(self) -> str:
        """State key for tracking completion (defaults to {name}_configured)."""
        return f"{self.name}_configured"

    @property
    def platforms(self) -> list[str]:
        """List of supported platforms. Empty list means all platforms."""
        return []  # Empty = all platforms supported

    @property
    def depends_on(self) -> list[str]:
        """List of task names that must complete before this task."""
        return []

    def is_supported(self) -> bool:
        """Check if this task is supported on the current platform."""
        if not self.platforms:
            return True
        if self.platform.is_macos and 'macos' in self.platforms:
            return True
        if self.platform.is_linux and 'linux' in self.platforms:
            return True
        if self.platform.is_windows and 'windows' in self.platforms:
            return True
        return False

    def is_complete(self) -> bool:
        """Check if this task has already been completed."""
        return self.state.is_complete(self.state_key)

    def mark_complete(self) -> None:
        """Mark this task as completed."""
        self.state.mark_complete(self.state_key)

    def skip_if_complete(self) -> bool:
        """
        Check completion and log skip message if already done.

        Returns:
            True if task should be skipped (already complete)
        """
        if self.is_complete():
            self.logger.info(f"{self.description} already complete (skipping)")
            return True
        return False

    def confirm_action(self, prompt: str) -> bool:
        """
        Ask user for confirmation (respects auto_yes and dry_run).

        Args:
            prompt: Question to ask (e.g., "Install packages?")

        Returns:
            True if action should proceed
        """
        if self.auto_yes:
            return True

        response = input(f"{prompt} (y/N): ")
        return response.lower() in ('y', 'yes')

    def log_dry_run(self, action: str) -> None:
        """Log a dry-run action."""
        self.logger.info(f"[DRY RUN] Would {action}")

    @abstractmethod
    def run(self) -> bool:
        """
        Execute the task.

        Returns:
            True if successful, False otherwise
        """
        pass
