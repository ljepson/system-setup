"""Logging configuration with rich console output."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme


# Custom theme for consistent styling
THEME = Theme({
    "info": "blue",
    "warning": "yellow",
    "error": "red bold",
    "success": "green bold",
})


class SetupLogger:
    """Enhanced logger with file and console output."""

    def __init__(
        self,
        log_file: Optional[Path] = None,
        verbose: bool = False,
        quiet: bool = False,
    ) -> None:
        """
        Initialize logger.

        Args:
            log_file: Path to log file. If None, creates timestamped file in /tmp
            verbose: Enable debug logging
            quiet: Suppress console output (still logs to file)
        """
        self.console = Console(theme=THEME)
        self.log_file = log_file or self._default_log_file()
        self.verbose = verbose
        self.quiet = quiet

        # Tracking for summary
        self.sections_run: list[str] = []
        self.packages_installed: list[str] = []
        self.settings_applied: list[str] = []
        self.errors: list[str] = []

        self._setup_logging()

    def _default_log_file(self) -> Path:
        """Generate default log file path with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return Path(f"/tmp/system_setup_{timestamp}.log")

    def _setup_logging(self) -> None:
        """Configure logging with file and console handlers."""
        # Create logger
        self.logger = logging.getLogger("system_setup")
        self.logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)

        # Clear existing handlers
        self.logger.handlers.clear()

        # File handler (always DEBUG level)
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
        except OSError as e:
            print(f"Warning: Could not create log file {self.log_file}: {e}", file=sys.stderr)

        # Console handler (respects quiet mode)
        if not self.quiet:
            console_handler = RichHandler(
                console=self.console,
                show_time=False,
                show_path=False,
                markup=True,
            )
            console_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
            self.logger.addHandler(console_handler)

    def info(self, message: str, emoji: str = "ℹ️") -> None:
        """Log info message."""
        self.logger.info(f"{emoji}  {message}")

    def success(self, message: str, emoji: str = "✅") -> None:
        """Log success message."""
        self.console.print(f"[success]{emoji}  {message}[/success]")
        self.logger.info(f"SUCCESS: {message}")

    def warning(self, message: str, emoji: str = "⚠️") -> None:
        """Log warning message."""
        self.logger.warning(f"{emoji}  {message}")

    def error(self, message: str, emoji: str = "❌") -> None:
        """Log error message."""
        self.logger.error(f"{emoji}  {message}")
        self.errors.append(message)

    def debug(self, message: str) -> None:
        """Log debug message."""
        self.logger.debug(message)

    def section(self, title: str) -> None:
        """Print a section header."""
        if not self.quiet:
            self.console.rule(f"[bold blue]{title}[/bold blue]")
        self.logger.info(f"SECTION: {title}")
        self.sections_run.append(title)

    def track_package(self, package: str) -> None:
        """Track installed package for summary."""
        self.packages_installed.append(package)

    def track_setting(self, setting: str) -> None:
        """Track applied setting for summary."""
        self.settings_applied.append(setting)

    def show_summary(self) -> None:
        """Display summary report."""
        # Don't show summary if nothing was done
        if not any([
            self.sections_run,
            self.packages_installed,
            self.settings_applied,
            self.errors,
        ]):
            return

        if not self.quiet:
            self.console.print()
            self.console.rule("[bold blue]📊 SETUP SUMMARY[/bold blue]")
            self.console.print()

        # Sections completed
        if self.sections_run:
            self.console.print("[green]✅ Sections Completed:[/green]")
            for section in self.sections_run:
                self.console.print(f"   • {section}")
            self.console.print()

        # Packages installed
        if self.packages_installed:
            self.console.print("[green]📦 Packages Installed:[/green]")
            for package in self.packages_installed:
                self.console.print(f"   • {package}")
            self.console.print()

        # Settings applied
        if self.settings_applied:
            self.console.print("[green]⚙️  Settings Applied:[/green]")
            for setting in self.settings_applied:
                self.console.print(f"   • {setting}")
            self.console.print()

        # Errors
        if self.errors:
            self.console.print("[error]❌ Errors Encountered:[/error]")
            for error in self.errors:
                self.console.print(f"   • {error}")
        else:
            self.console.print("[green]✅ No errors encountered[/green]")

        self.console.print()
        self.console.rule()
        self.console.print()
        self.console.print(f"📄 Full log saved to: [cyan]{self.log_file}[/cyan]")


# Global logger instance (initialized in CLI)
_logger: Optional[SetupLogger] = None


def setup_logger(
    log_file: Optional[Path] = None,
    verbose: bool = False,
    quiet: bool = False,
) -> SetupLogger:
    """Initialize global logger instance."""
    global _logger
    _logger = SetupLogger(log_file=log_file, verbose=verbose, quiet=quiet)
    return _logger


def get_logger() -> SetupLogger:
    """Get global logger instance."""
    if _logger is None:
        raise RuntimeError("Logger not initialized. Call setup_logger() first.")
    return _logger
