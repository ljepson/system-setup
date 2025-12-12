"""Centralized command runner for subprocess execution."""

import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional, Union

from system_setup.logger import get_logger


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: List[str]
    return_code: int
    stdout: str
    stderr: str
    duration: float
    dry_run: bool = False

    @property
    def success(self) -> bool:
        """Check if command was successful."""
        return self.return_code == 0

    @property
    def output(self) -> str:
        """Get combined stdout and stderr."""
        return self.stdout + self.stderr


class CommandRunner:
    """Centralized command runner with logging, retries, and dry-run support.

    Provides:
    - Consistent logging of commands
    - Dry-run mode
    - Automatic retries with backoff
    - Timeout handling
    - Error formatting
    """

    def __init__(
        self,
        dry_run: bool = False,
        timeout: int = 300,
        retries: int = 0,
        retry_delay: float = 1.0,
    ) -> None:
        """
        Initialize command runner.

        Args:
            dry_run: If True, don't actually execute commands
            timeout: Default timeout in seconds
            retries: Number of retries on failure (0 = no retries)
            retry_delay: Initial delay between retries (doubles each retry)
        """
        self.dry_run = dry_run
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self._logger = None

    @property
    def logger(self):
        """Get logger instance (lazy initialization)."""
        if self._logger is None:
            try:
                self._logger = get_logger()
            except RuntimeError:
                # Logger not initialized, use a dummy
                self._logger = None
        return self._logger

    def run(
        self,
        command: Union[str, List[str]],
        check: bool = True,
        capture_output: bool = True,
        timeout: Optional[int] = None,
        retries: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        shell: bool = False,
    ) -> CommandResult:
        """
        Run a command with logging and error handling.

        Args:
            command: Command to run (string or list)
            check: Raise exception on non-zero exit code
            capture_output: Capture stdout/stderr
            timeout: Timeout in seconds (None = use default)
            retries: Number of retries (None = use default)
            cwd: Working directory
            env: Environment variables
            shell: Use shell execution (avoid if possible)

        Returns:
            CommandResult with output and status

        Raises:
            subprocess.CalledProcessError: If check=True and command fails
            subprocess.TimeoutExpired: If command times out
        """
        # Normalize command to list
        if isinstance(command, str):
            cmd_list = shlex.split(command) if not shell else [command]
            cmd_str = command
        else:
            cmd_list = command
            cmd_str = ' '.join(command)

        timeout = timeout or self.timeout
        retries = retries if retries is not None else self.retries

        # Dry run mode
        if self.dry_run:
            if self.logger:
                self.logger.debug(f"[DRY RUN] Would run: {cmd_str}")
            else:
                print(f"[DRY RUN] Would run: {cmd_str}")
            return CommandResult(
                command=cmd_list,
                return_code=0,
                stdout="",
                stderr="",
                duration=0.0,
                dry_run=True,
            )

        # Execute with retries
        last_error = None
        delay = self.retry_delay

        for attempt in range(retries + 1):
            try:
                start_time = time.time()

                result = subprocess.run(
                    cmd_list,
                    capture_output=capture_output,
                    text=True,
                    timeout=timeout,
                    cwd=cwd,
                    env=env,
                    shell=shell,
                    check=False,  # We handle check ourselves
                )

                duration = time.time() - start_time

                cmd_result = CommandResult(
                    command=cmd_list,
                    return_code=result.returncode,
                    stdout=result.stdout or "",
                    stderr=result.stderr or "",
                    duration=duration,
                )

                # Log result
                if result.returncode == 0:
                    if self.logger:
                        self.logger.debug(f"Command succeeded: {cmd_str} ({duration:.2f}s)")
                else:
                    if self.logger:
                        self.logger.debug(
                            f"Command failed: {cmd_str} "
                            f"(exit code {result.returncode})"
                        )

                # Check for error
                if check and result.returncode != 0:
                    raise subprocess.CalledProcessError(
                        result.returncode,
                        cmd_list,
                        result.stdout,
                        result.stderr,
                    )

                return cmd_result

            except subprocess.TimeoutExpired:
                last_error = subprocess.TimeoutExpired(cmd_list, timeout)
                if self.logger:
                    self.logger.warning(
                        f"Command timed out after {timeout}s: {cmd_str}"
                    )
            except subprocess.CalledProcessError as e:
                last_error = e
                if attempt < retries:
                    if self.logger:
                        self.logger.warning(
                            f"Command failed (attempt {attempt + 1}/{retries + 1}), "
                            f"retrying in {delay}s: {cmd_str}"
                        )
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

        # All retries exhausted
        if last_error:
            raise last_error

        # Should not reach here
        return CommandResult(
            command=cmd_list,
            return_code=-1,
            stdout="",
            stderr="Unknown error",
            duration=0.0,
        )

    def run_quiet(
        self,
        command: Union[str, List[str]],
        **kwargs,
    ) -> CommandResult:
        """
        Run a command without raising exceptions.

        Same as run() but with check=False by default.
        """
        kwargs.setdefault('check', False)
        return self.run(command, **kwargs)

    def run_sudo(
        self,
        command: Union[str, List[str]],
        **kwargs,
    ) -> CommandResult:
        """
        Run a command with sudo.

        Args:
            command: Command to run
            **kwargs: Additional arguments for run()

        Returns:
            CommandResult
        """
        if isinstance(command, str):
            sudo_cmd = f"sudo {command}"
        else:
            sudo_cmd = ['sudo'] + list(command)

        return self.run(sudo_cmd, **kwargs)

    def which(self, program: str) -> Optional[str]:
        """
        Check if a program is available in PATH.

        Args:
            program: Program name

        Returns:
            Full path to program or None if not found
        """
        try:
            result = self.run(['which', program], check=False, capture_output=True)
            if result.success:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def is_available(self, program: str) -> bool:
        """Check if a program is available in PATH."""
        return self.which(program) is not None


# Convenience function
def run_command(
    command: Union[str, List[str]],
    dry_run: bool = False,
    **kwargs,
) -> CommandResult:
    """
    Run a command with default settings.

    Args:
        command: Command to run
        dry_run: Dry run mode
        **kwargs: Additional arguments for CommandRunner.run()

    Returns:
        CommandResult
    """
    runner = CommandRunner(dry_run=dry_run)
    return runner.run(command, **kwargs)
