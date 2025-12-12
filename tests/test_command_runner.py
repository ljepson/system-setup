"""Tests for CommandRunner utility."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from system_setup.utils.command import CommandRunner, CommandResult, run_command


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_success_property_true(self):
        """Test success property when return_code is 0."""
        result = CommandResult(
            command=['echo', 'hello'],
            return_code=0,
            stdout='hello\n',
            stderr='',
            duration=0.1,
        )
        assert result.success is True

    def test_success_property_false(self):
        """Test success property when return_code is non-zero."""
        result = CommandResult(
            command=['false'],
            return_code=1,
            stdout='',
            stderr='error',
            duration=0.1,
        )
        assert result.success is False

    def test_output_property(self):
        """Test output property combines stdout and stderr."""
        result = CommandResult(
            command=['test'],
            return_code=0,
            stdout='out',
            stderr='err',
            duration=0.1,
        )
        assert result.output == 'outerr'

    def test_dry_run_flag(self):
        """Test dry_run flag is stored correctly."""
        result = CommandResult(
            command=['test'],
            return_code=0,
            stdout='',
            stderr='',
            duration=0.0,
            dry_run=True,
        )
        assert result.dry_run is True


class TestCommandRunner:
    """Tests for CommandRunner class."""

    def test_dry_run_mode(self):
        """Test dry run mode doesn't execute commands."""
        runner = CommandRunner(dry_run=True)
        result = runner.run(['rm', '-rf', '/'])  # Would be catastrophic if run!

        assert result.success is True
        assert result.dry_run is True
        assert result.return_code == 0
        assert result.duration == 0.0

    def test_run_basic_command(self):
        """Test running a basic command."""
        runner = CommandRunner()
        result = runner.run(['echo', 'hello'])

        assert result.success is True
        assert 'hello' in result.stdout
        assert result.return_code == 0

    def test_run_string_command(self):
        """Test running a string command (shell=False)."""
        runner = CommandRunner()
        result = runner.run('echo hello')

        assert result.success is True
        assert 'hello' in result.stdout

    def test_run_failing_command(self):
        """Test running a command that fails."""
        runner = CommandRunner()
        result = runner.run_quiet(['false'])

        assert result.success is False
        assert result.return_code == 1

    def test_run_check_raises(self):
        """Test check=True raises CalledProcessError."""
        runner = CommandRunner()

        with pytest.raises(subprocess.CalledProcessError):
            runner.run(['false'], check=True)

    def test_run_quiet_no_raise(self):
        """Test run_quiet doesn't raise on failure."""
        runner = CommandRunner()
        result = runner.run_quiet(['false'])

        assert result.success is False
        # Should not raise

    @patch('subprocess.run')
    def test_run_with_retries(self, mock_run):
        """Test retry behavior on failure with check=True."""
        # First call fails (raises CalledProcessError), second succeeds
        mock_run.side_effect = [
            subprocess.CalledProcessError(1, ['test'], '', 'error'),
            MagicMock(returncode=0, stdout='success', stderr=''),
        ]

        runner = CommandRunner(retries=1, retry_delay=0.01)
        # Note: retries only happen with check=True since that's when CalledProcessError is raised
        result = runner.run(['test'], check=True)

        assert mock_run.call_count == 2
        assert result.success is True

    def test_which_existing_command(self):
        """Test which() finds existing commands."""
        runner = CommandRunner()
        path = runner.which('echo')

        assert path is not None
        assert 'echo' in path

    def test_which_nonexistent_command(self):
        """Test which() returns None for nonexistent commands."""
        runner = CommandRunner()
        path = runner.which('definitely_not_a_real_command_12345')

        assert path is None

    def test_is_available_true(self):
        """Test is_available() for existing commands."""
        runner = CommandRunner()
        assert runner.is_available('echo') is True

    def test_is_available_false(self):
        """Test is_available() for nonexistent commands."""
        runner = CommandRunner()
        assert runner.is_available('definitely_not_a_real_command_12345') is False

    def test_run_captures_duration(self):
        """Test that run captures execution duration."""
        runner = CommandRunner()
        result = runner.run(['sleep', '0.1'])

        assert result.duration >= 0.1

    def test_run_with_cwd(self, tmp_path):
        """Test running command in different directory."""
        runner = CommandRunner()
        result = runner.run(['pwd'], cwd=str(tmp_path))

        assert str(tmp_path) in result.stdout

    @patch('subprocess.run')
    def test_timeout_handling(self, mock_run):
        """Test timeout raises TimeoutExpired."""
        mock_run.side_effect = subprocess.TimeoutExpired(['sleep'], 1)

        runner = CommandRunner(timeout=1)

        with pytest.raises(subprocess.TimeoutExpired):
            runner.run(['sleep', '10'])


class TestRunCommandFunction:
    """Tests for the convenience run_command function."""

    def test_run_command_basic(self):
        """Test basic run_command usage."""
        result = run_command(['echo', 'test'])

        assert result.success is True
        assert 'test' in result.stdout

    def test_run_command_dry_run(self):
        """Test run_command with dry_run=True."""
        result = run_command(['rm', '-rf', '/'], dry_run=True)

        assert result.success is True
        assert result.dry_run is True


class TestCommandRunnerIntegration:
    """Integration tests for CommandRunner with tasks."""

    def test_base_task_has_cmd_property(self):
        """Test BaseTask subclasses have cmd property."""
        from system_setup.tasks.base import BaseTask

        class TestTask(BaseTask):
            @property
            def name(self) -> str:
                return 'test'

            @property
            def description(self) -> str:
                return 'Test Task'

            def run(self) -> bool:
                return True

        task = TestTask(
            config=MagicMock(),
            state=MagicMock(),
            platform=MagicMock(),
            dry_run=True,
        )

        assert hasattr(task, 'cmd')
        assert isinstance(task.cmd, CommandRunner)
        assert task.cmd.dry_run is True

    def test_cmd_property_lazy_initialization(self):
        """Test cmd property is lazily initialized."""
        from system_setup.tasks.base import BaseTask

        class TestTask(BaseTask):
            @property
            def name(self) -> str:
                return 'test'

            @property
            def description(self) -> str:
                return 'Test Task'

            def run(self) -> bool:
                return True

        task = TestTask(
            config=MagicMock(),
            state=MagicMock(),
            platform=MagicMock(),
        )

        # Before access, _cmd should be None
        assert task._cmd is None

        # After access, should be initialized
        _ = task.cmd
        assert task._cmd is not None

    def test_cmd_inherits_dry_run_setting(self):
        """Test CommandRunner inherits dry_run from task."""
        from system_setup.tasks.base import BaseTask

        class TestTask(BaseTask):
            @property
            def name(self) -> str:
                return 'test'

            @property
            def description(self) -> str:
                return 'Test Task'

            def run(self) -> bool:
                return True

        # Test with dry_run=False
        task_normal = TestTask(
            config=MagicMock(),
            state=MagicMock(),
            platform=MagicMock(),
            dry_run=False,
        )
        assert task_normal.cmd.dry_run is False

        # Test with dry_run=True
        task_dry = TestTask(
            config=MagicMock(),
            state=MagicMock(),
            platform=MagicMock(),
            dry_run=True,
        )
        assert task_dry.cmd.dry_run is True
