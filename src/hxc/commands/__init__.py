# src/hxc/commands/__init__.py
"""
Command registration and loading functionality
"""

import importlib
import pkgutil
from typing import Dict, List, Type

from hxc.commands.base import BaseCommand

_commands: Dict[str, Type[BaseCommand]] = {}


def register_command(command_class: Type[BaseCommand]) -> Type[BaseCommand]:
    """
    Decorator to register a command class

    Args:
        command_class: Command class to register

    Returns:
        The same command class
    """
    _commands[command_class.name] = command_class
    return command_class


def discover_commands() -> None:
    """
    Discover and load all command modules
    """
    import hxc.commands as commands_package

    for _, name, is_pkg in pkgutil.iter_modules(commands_package.__path__):
        if not is_pkg and name != "base":
            importlib.import_module(f"hxc.commands.{name}")


def get_available_commands() -> List[str]:
    """
    Get list of available command names

    Returns:
        List of command names
    """
    discover_commands()
    return list(_commands.keys())


def load_command(name: str) -> Type[BaseCommand]:
    """
    Load a command class by name

    Args:
        name: Command name

    Returns:
        Command class

    Raises:
        ValueError: If command not found
    """
    discover_commands()
    if name not in _commands:
        raise ValueError(f"Command '{name}' not found")
    return _commands[name]
