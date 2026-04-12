"""
Registry command implementation for managing registry locations.

This module provides CLI commands for registry path management using the shared
RegistryOperation for behavioral consistency with MCP tools.
"""

import argparse
import pathlib
from typing import Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.core.config import Config
from hxc.core.operations.registry import (
    InvalidRegistryPathError,
    RegistryOperation,
    RegistryOperationError,
)
from hxc.utils.helpers import get_project_root


@register_command
class RegistryCommand(BaseCommand):
    """Command for managing registry locations"""

    name = "registry"
    help = "Manage registry locations"

    # Key used in the config to store the registry path
    # This matches RegistryOperation.CONFIG_KEY for consistency
    CONFIG_KEY = "registry_path"

    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)

        # Add subcommands
        registry_subparsers = parser.add_subparsers(dest="registry_command")

        # Path command
        path_parser = registry_subparsers.add_parser(
            "path", help="Get or set the registry path"
        )
        path_parser.add_argument("--set", metavar="PATH", help="Set the registry path")

        # List command (for future expansion to support multiple registries)
        list_parser = registry_subparsers.add_parser(
            "list", help="List all known registries"
        )

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
        operation = RegistryOperation()

        # If --set is specified, update the registry path
        if hasattr(args, "set") and args.set:
            path = pathlib.Path(args.set).resolve()

            try:
                result = operation.set_registry_path(str(path), validate=True)
                print(f"✅ Registry path set to: {result['path']}")
                return 0
            except InvalidRegistryPathError as e:
                print(f"❌ Invalid registry path: {e.path}")
                print("  Path does not appear to be a valid HXC registry.")
                if e.missing_components:
                    print(f"  Missing: {', '.join(e.missing_components)}")
                return 1
            except RegistryOperationError as e:
                print(f"❌ Error setting registry path: {e}")
                return 1

        # Otherwise, get and display the registry path
        result = operation.get_registry_path(include_discovery=True)

        if result["success"] and result["path"]:
            if result["is_valid"]:
                print(result["path"])
                return 0
            else:
                # Path is set but invalid
                print(f"Warning: Configured registry path is invalid: {result['path']}")
                if result.get("validation_errors"):
                    print(f"  Missing: {', '.join(result['validation_errors'])}")
                if result.get("discovered_path"):
                    print(f"Found valid registry at: {result['discovered_path']}")
                    print("To set this as your default registry, run:")
                    print(f"  hxc registry path --set {result['discovered_path']}")
                return 1
        else:
            print("No registry path is set.")

            # Try to find a registry in the current directory or parent directories
            discovered_path = result.get("discovered_path")
            if discovered_path:
                print(f"Found registry at: {discovered_path}")
                print("To set this as your default registry, run:")
                print(f"  hxc registry path --set {discovered_path}")
            else:
                print("No registry found in current or parent directories.")
                print("To create a new registry, run 'hxc init'.")

            return 1

    @classmethod
    def handle_list(cls, args):
        """Handle the 'list' subcommand"""
        operation = RegistryOperation()
        result = operation.list_registries()

        if result["count"] == 0:
            print("No registries configured.")
            return 1

        for registry in result["registries"]:
            if registry["is_current"]:
                status = "✓" if registry["is_valid"] else "✗"
                print(f"Current registry: {registry['path']} [{status}]")
            else:
                status = "valid" if registry["is_valid"] else "invalid"
                print(f"  Discovered: {registry['path']} ({status})")

        return 0

    @classmethod
    def get_registry_path(cls) -> Optional[str]:
        """
        Get the current registry path from config.

        This is a convenience method that uses the shared RegistryOperation
        for behavioral consistency with MCP tools.

        Returns:
            Registry path string if set and valid, None otherwise
        """
        operation = RegistryOperation()
        result = operation.get_registry_path(include_discovery=False)

        if result["success"] and result["is_valid"]:
            return result["path"]
        return None

    @staticmethod
    def _validate_registry_path(path: pathlib.Path) -> bool:
        """
        Validate that the given path is a valid registry.

        This method uses the shared RegistryOperation validation logic
        for consistency with MCP tools.

        Args:
            path: Path to validate

        Returns:
            True if path is a valid registry, False otherwise
        """
        result = RegistryOperation.validate_registry_path(path)
        return result["valid"]