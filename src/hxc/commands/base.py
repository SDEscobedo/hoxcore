# src/hxc/commands/base.py
"""
Base command class definition
"""
import abc
import argparse
from typing import Any


class BaseCommand(abc.ABC):
    """Base class for all commands"""
    
    # Command name (to be defined by subclasses)
    name = ""
    
    # Command help text (to be defined by subclasses)
    help = ""
    
    @classmethod
    @abc.abstractmethod
    def register_subparser(cls, subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
        """
        Register command-specific arguments
        
        Args:
            subparsers: Subparsers action from main parser
            
        Returns:
            Command's subparser
        """
        parser = subparsers.add_parser(cls.name, help=cls.help)
        return parser
    
    @classmethod
    @abc.abstractmethod
    def execute(cls, args: argparse.Namespace) -> int:
        """
        Execute the command
        
        Args:
            args: Parsed arguments
            
        Returns:
            Exit code
        """
        pass
