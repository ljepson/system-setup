"""System Setup - Cross-platform system configuration tool."""

__version__ = "2.0.0"
__author__ = "Lonny Jepson"

from system_setup.config import Config
from system_setup.state import StateManager

__all__ = ["Config", "StateManager", "__version__"]
