"""
Registry command implementation for managing registry locations.
"""
import os
import pathlib
import argparse
from typing import Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.core.config import Config
from hxc.utils.helpers import get_project_root


@register_command
class RegistryCommand(BaseCommand):
    """Command for managing registry locations"""
    
    name = "registry"
    help = "Manage registry locations"
    
    # Key used in the config to store the registry path
    CONFIG_KEY = "registry_path"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        
        # Add subcommands
        registry_subparsers = parser.add_subparsers(dest="registry_command")
        
        # Path command
        path_parser = registry_subparsers.add_parser("path", help="Get or set the registry path")
        path_parser.add_argument("--set", metavar="PATH", help="Set the registry path")
        
        # List command (for future expansion to support multiple registries)
        list_parser = registry_subparsers.add_parser("list", help="List all known registries")
        
        return parser
    
    @classmethod
    def execute(cls, args):
        if not hasattr(args, "registry_command") or not args.registry_command:
            # If no subcommand is specified, default to 'path'
            return cls.handle_path(args)
            
        if args.registry_command == "path":
            return cls.handle_path(args)
        elif args.registry_command == "list":
            return cls.handle_list(args)
        else:
            print(f"Unknown registry command: {args.registry_command}")
            return 1
    
    @classmethod
    def handle_path(cls, args):
        """Handle the 'path' subcommand"""
        config = Config()
        
        # If --set is specified, update the registry path
        if hasattr(args, "set") and args.set:
            path = pathlib.Path(args.set).resolve()
            if not cls._validate_registry_path(path):
                print(f"❌ Invalid registry path: {path}")
                print("  Path does not appear to be a valid HXC registry.")
                return 1
                
            config.set(cls.CONFIG_KEY, str(path))
            print(f"✅ Registry path set to: {path}")
            return 0
        
        # Otherwise, get and display the registry path
        registry_path = cls.get_registry_path()
        if registry_path:
            print(registry_path)
            return 0
        else:
            print("No registry path is set.")
            
            # Try to find a registry in the current directory or parent directories
            current_registry = get_project_root()
            if current_registry:
                print(f"Found registry at: {current_registry}")
                print("To set this as your default registry, run:")
                print(f"  hxc registry path --set {current_registry}")
            else:
                print("No registry found in current or parent directories.")
                print("To create a new registry, run 'hxc init'.")
            
            return 1
    
    @classmethod
    def handle_list(cls, args):
        """Handle the 'list' subcommand"""
        # Currently only supports a single registry
        registry_path = cls.get_registry_path()
        if registry_path:
            print(f"Current registry: {registry_path}")
            return 0
        else:
            print("No registries configured.")
            return 1
    
    @classmethod
    def get_registry_path(cls) -> Optional[str]:
        """Get the current registry path from config"""
        config = Config()
        path = config.get(cls.CONFIG_KEY)
        
        if path and cls._validate_registry_path(pathlib.Path(path)):
            return path
        return None
    
    @staticmethod
    def _validate_registry_path(path: pathlib.Path) -> bool:
        """Validate that the given path is a valid registry"""
        # Check if path exists and is a directory
        if not path.exists() or not path.is_dir():
            return False
            
        # Check for key registry files/directories
        markers = [
            path / "config.yml",
            path / "programs",
            path / "projects",
            path / "missions",
            path / "actions"
        ]
        
        return all(marker.exists() for marker in markers)