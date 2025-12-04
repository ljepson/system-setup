"""State management for resumable setup operations."""

import json
import time
from pathlib import Path
from typing import Dict, Optional


class StateManager:
    """Manages persistent state for resumable operations."""

    def __init__(self, state_file: Optional[Path] = None) -> None:
        """
        Initialize state manager.

        Args:
            state_file: Path to state file. Defaults to ~/.system_setup_state
        """
        self.state_file = state_file or Path.home() / ".system_setup_state"
        self._state: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        """Load state from file."""
        if self.state_file.exists():
            try:
                with self.state_file.open('r') as f:
                    self._state = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                # Corrupted state file - start fresh
                self._state = {}

    def _save(self) -> None:
        """Save state to file."""
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Write atomically using temp file
            temp_file = self.state_file.with_suffix('.tmp')
            with temp_file.open('w') as f:
                json.dump(self._state, f, indent=2)

            # Atomic rename
            temp_file.replace(self.state_file)
        except OSError as e:
            raise RuntimeError(f"Failed to save state: {e}") from e

    def mark_complete(self, step: str) -> None:
        """
        Mark a step as complete.

        Args:
            step: Step identifier (e.g., 'packages_installed', 'dotfiles_configured')
        """
        self._state[step] = time.time()
        self._save()

    def is_complete(self, step: str) -> bool:
        """
        Check if a step has been completed.

        Args:
            step: Step identifier

        Returns:
            True if step was previously completed
        """
        return step in self._state

    def get_completion_time(self, step: str) -> Optional[float]:
        """
        Get timestamp when step was completed.

        Args:
            step: Step identifier

        Returns:
            Unix timestamp or None if step not completed
        """
        return self._state.get(step)

    def clear(self) -> None:
        """Clear all state (start fresh)."""
        self._state = {}
        if self.state_file.exists():
            self.state_file.unlink()

    def get_completed_steps(self) -> Dict[str, float]:
        """
        Get all completed steps with timestamps.

        Returns:
            Dict mapping step name to completion timestamp
        """
        return self._state.copy()

    def clear_step(self, step: str) -> None:
        """
        Clear a specific step from state.

        Args:
            step: Step identifier to clear
        """
        if step in self._state:
            del self._state[step]
            self._save()
