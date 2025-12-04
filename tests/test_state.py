"""Tests for state management."""

import tempfile
from pathlib import Path

import pytest

from system_setup.state import StateManager


def test_state_mark_complete(tmp_path):
    """Test marking steps as complete."""
    state_file = tmp_path / "test_state"
    state = StateManager(state_file)

    assert not state.is_complete('test_step')

    state.mark_complete('test_step')
    assert state.is_complete('test_step')


def test_state_persistence(tmp_path):
    """Test state persistence across instances."""
    state_file = tmp_path / "test_state"

    # First instance
    state1 = StateManager(state_file)
    state1.mark_complete('step1')
    state1.mark_complete('step2')

    # Second instance should load saved state
    state2 = StateManager(state_file)
    assert state2.is_complete('step1')
    assert state2.is_complete('step2')
    assert not state2.is_complete('step3')


def test_state_clear(tmp_path):
    """Test clearing state."""
    state_file = tmp_path / "test_state"
    state = StateManager(state_file)

    state.mark_complete('step1')
    assert state.is_complete('step1')

    state.clear()
    assert not state.is_complete('step1')
    assert not state_file.exists()
