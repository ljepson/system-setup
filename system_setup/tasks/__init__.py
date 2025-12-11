"""Task modules for system setup."""

from system_setup.tasks.chezmoi import ChezmoiTask
from system_setup.tasks.dotfiles import DotfilesTask
from system_setup.tasks.fish import FishTask
from system_setup.tasks.hyprland import HyprlandTask
from system_setup.tasks.modern_tools import ModernToolsTask
from system_setup.tasks.settings import SettingsTask
from system_setup.tasks.shell import ShellTask

__all__ = [
    "ChezmoiTask",
    "DotfilesTask",
    "FishTask",
    "HyprlandTask",
    "ModernToolsTask",
    "SettingsTask",
    "ShellTask",
]
