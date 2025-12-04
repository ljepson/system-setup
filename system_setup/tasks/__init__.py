"""Task modules for system setup."""

from system_setup.tasks.dotfiles import DotfilesTask
from system_setup.tasks.settings import SettingsTask
from system_setup.tasks.shell import ShellTask

__all__ = ["DotfilesTask", "SettingsTask", "ShellTask"]
