"""
Get command implementation for retrieving entity property values.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityType, OutputFormat
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError, resolve_safe_path


@register_command
class GetCommand(BaseCommand):
    """Command for retrieving entity property values"""

    name = "get"
    help = "Get a property value from a program, project, action, or mission"

    # Define all accessible properties
    SCALAR_PROPERTIES = {
        "type",
        "uid",
        "id",
        "title",
        "description",
        "status",
        "start_date",
        "due_date",
        "completion_date",
        "duration_estimate",
        "category",
        "parent",
        "template",
    }

    LIST_PROPERTIES = {"tags", "children", "related"}

    COMPLEX_PROPERTIES = {
        "repositories",
        "storage",
        "databases",
        "tools",
        "models",
        "knowledge_bases",
    }

    # Special properties for convenience
    SPECIAL_PROPERTIES = {
        "all",  # Get all properties
        "path",  # Get file path
    }

    ALL_PROPERTIES = (
        SCALAR_PROPERTIES | LIST_PROPERTIES | COMPLEX_PROPERTIES | SPECIAL_PROPERTIES
    )

    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)

        # Required arguments
        parser.add_argument("identifier", help="ID or UID of the entity")
        parser.add_argument(
            "property",
            help="Property name to retrieve (e.g., title, status, tags, all)",
        )

        # Optional arguments
        parser.add_argument(
            "--type",
            "-t",
            choices=EntityType.values(),
            help="Entity type (only needed if identifier is ambiguous)",
        )
        parser.add_argument(
            "--format",
            "-f",
            choices=["raw", "yaml", "json", "pretty"],
            default="raw",
            help="Output format (default: raw)",
        )
        parser.add_argument(
            "--registry",
            help="Path to registry (defaults to current or configured registry)",
        )
        parser.add_argument(
            "--index", type=int, help="For list properties, get item at specific index"
        )
        parser.add_argument(
            "--key",
            help="For complex properties, filter by key:value (e.g., name:github)",
        )

        return parser

    @classmethod
    def execute(cls, args):
        try:
            # Convert entity type if provided
            entity_type = None
            if args.type:
                try:
                    entity_type = EntityType.from_string(args.type)
                except ValueError as e:
                    print(f"❌ Invalid argument: {e}")
                    return 1

            # Validate property name
            property_name = args.property.lower()
            if property_name not in cls.ALL_PROPERTIES:
                print(f"❌ Unknown property '{args.property}'")
                print(
                    f"   Available properties: {', '.join(sorted(cls.ALL_PROPERTIES))}"
                )
                return 1

            # Get registry path
            registry_path = cls._get_registry_path(args.registry)
            if not registry_path:
                print(
                    "❌ No registry found. Please specify with --registry or initialize one with 'hxc init'"
                )
                return 1

            # Find the entity file
            file_path = cls._find_entity_file(
                registry_path, args.identifier, entity_type
            )
            if not file_path:
                print(f"❌ No entity found with identifier '{args.identifier}'")
                if entity_type:
                    print(f"   (search limited to type: {entity_type.value})")
                return 1

            # Load the entity
            try:
                secure_file_path = resolve_safe_path(registry_path, file_path)
                with open(secure_file_path, "r") as f:
                    entity_data = yaml.safe_load(f)
            except PathSecurityError as e:
                print(f"❌ Security error: {e}")
                return 1
            except Exception as e:
                print(f"❌ Error loading entity: {e}")
                return 1

            if not entity_data or not isinstance(entity_data, dict):
                print(f"❌ Invalid entity data in {file_path}")
                return 1

            # Handle special properties
            if property_name == "path":
                print(str(secure_file_path))
                return 0

            if property_name == "all":
                cls._display_all_properties(entity_data, args.format)
                return 0

            # Get the property value
            value = cls._get_property_value(entity_data, property_name, args)

            if value is None:
                print(f"⚠️  Property '{property_name}' is not set")
                return 1

            # Display the value
            cls._display_value(value, args.format, property_name)
            return 0

        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error retrieving property: {e}")
            return 1

    @classmethod
    def _get_registry_path(cls, specified_path: Optional[str] = None) -> Optional[str]:
        """Get registry path from specified path, config, or current directory"""
        if specified_path:
            return specified_path

        # Try from config
        registry_path = RegistryCommand.get_registry_path()
        if registry_path:
            return registry_path

        # Try to find in current directory or parent directories
        return get_project_root()

    @classmethod
    def _find_entity_file(
        cls,
        registry_path: str,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[Path]:
        """
        Find an entity file by ID or UID

        Args:
            registry_path: Root directory of the registry
            identifier: ID or UID to search for
            entity_type: Optional entity type to filter by

        Returns:
            Path to the entity file if found, None otherwise
        """
        types_to_search = [entity_type] if entity_type else list(EntityType)

        for entity_type_enum in types_to_search:
            folder_name = entity_type_enum.get_folder_name()
            file_prefix = entity_type_enum.get_file_prefix()

            try:
                type_dir = resolve_safe_path(registry_path, folder_name)
            except PathSecurityError:
                continue

            if not type_dir.exists():
                continue

            # First, try to match by filename (UID in filename)
            uid_pattern = f"{file_prefix}-{identifier}.yml"
            for file_path in type_dir.glob(uid_pattern):
                try:
                    secure_file_path = resolve_safe_path(registry_path, file_path)
                    return secure_file_path
                except PathSecurityError:
                    continue

            # If no match, search inside files for ID or UID field
            for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
                try:
                    secure_file_path = resolve_safe_path(registry_path, file_path)
                    with open(secure_file_path, "r") as f:
                        data = yaml.safe_load(f)
                        if data and isinstance(data, dict):
                            if (
                                data.get("id") == identifier
                                or data.get("uid") == identifier
                            ):
                                return secure_file_path
                except PathSecurityError:
                    continue
                except Exception:
                    continue

        return None

    @classmethod
    def _get_property_value(
        cls, entity_data: Dict[str, Any], property_name: str, args: argparse.Namespace
    ) -> Optional[Any]:
        """
        Get the value of a property from entity data

        Args:
            entity_data: Entity data dictionary
            property_name: Name of the property to retrieve
            args: Command arguments (for filtering options)

        Returns:
            Property value or None if not found
        """
        value = entity_data.get(property_name)

        if value is None:
            return None

        # Handle list properties with index
        if property_name in cls.LIST_PROPERTIES and isinstance(value, list):
            if args.index is not None:
                if 0 <= args.index < len(value):
                    return value[args.index]
                else:
                    print(
                        f"⚠️  Index {args.index} out of range (list has {len(value)} items)"
                    )
                    return None
            return value

        # Handle complex properties with key filter
        if property_name in cls.COMPLEX_PROPERTIES and isinstance(value, list):
            if args.key:
                # Parse key:value filter
                if ":" not in args.key:
                    print(
                        f"⚠️  Invalid key filter format. Use key:value (e.g., name:github)"
                    )
                    return None

                filter_key, filter_value = args.key.split(":", 1)
                filtered = [
                    item
                    for item in value
                    if isinstance(item, dict) and item.get(filter_key) == filter_value
                ]

                if not filtered:
                    print(f"⚠️  No items found with {filter_key}='{filter_value}'")
                    return None

                # If only one item matches, return it directly
                if len(filtered) == 1:
                    return filtered[0]

                return filtered

            # Handle index for complex properties
            if args.index is not None:
                if 0 <= args.index < len(value):
                    return value[args.index]
                else:
                    print(
                        f"⚠️  Index {args.index} out of range (list has {len(value)} items)"
                    )
                    return None

            return value

        return value

    @classmethod
    def _display_value(cls, value: Any, format_type: str, property_name: str) -> None:
        """
        Display a property value in the specified format

        Args:
            value: Value to display
            format_type: Output format (raw, yaml, json, pretty)
            property_name: Name of the property (for context in pretty format)
        """
        if format_type == "raw":
            cls._display_raw(value)
        elif format_type == "yaml":
            cls._display_yaml(value)
        elif format_type == "json":
            cls._display_json(value)
        elif format_type == "pretty":
            cls._display_pretty(value, property_name)

    @classmethod
    def _display_raw(cls, value: Any) -> None:
        """Display value in raw format (simple string output)"""
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    # For dicts, show key:value pairs on one line
                    parts = [f"{k}={v}" for k, v in item.items()]
                    print(" ".join(parts))
                else:
                    print(item)
        elif isinstance(value, dict):
            for k, v in value.items():
                print(f"{k}={v}")
        else:
            print(value)

    @classmethod
    def _display_yaml(cls, value: Any) -> None:
        """Display value in YAML format"""
        print(yaml.dump(value, default_flow_style=False, sort_keys=False).rstrip())

    @classmethod
    def _display_json(cls, value: Any) -> None:
        """Display value in JSON format"""
        print(json.dumps(value, indent=2))

    @classmethod
    def _display_pretty(cls, value: Any, property_name: str) -> None:
        """Display value in human-readable pretty format"""
        print(f"📋 {property_name}:")
        print()

        if isinstance(value, list):
            if not value:
                print("  (empty)")
            else:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        print(f"  [{i}]")
                        for k, v in item.items():
                            print(f"    {k}: {v}")
                    else:
                        print(f"  • {item}")
        elif isinstance(value, dict):
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"  {value}")

    @classmethod
    def _display_all_properties(
        cls, entity_data: Dict[str, Any], format_type: str
    ) -> None:
        """Display all properties of an entity"""
        if format_type == "yaml":
            print(yaml.dump(entity_data, default_flow_style=False, sort_keys=False))
        elif format_type == "json":
            print(json.dumps(entity_data, indent=2))
        elif format_type == "raw":
            # Display in a simple key=value format
            for key, value in entity_data.items():
                if isinstance(value, (list, dict)):
                    print(f"{key}={yaml.dump(value, default_flow_style=True).rstrip()}")
                else:
                    print(f"{key}={value}")
        else:  # pretty
            print("📄 Entity Properties")
            print("=" * 60)
            print()

            # Basic metadata
            print("🔖 Basic Information:")
            for key in ["type", "uid", "id", "title"]:
                if key in entity_data:
                    print(f"  {key}: {entity_data[key]}")
            print()

            # Description
            if "description" in entity_data and entity_data["description"]:
                print("📝 Description:")
                print(f"  {entity_data['description']}")
                print()

            # Status and dates
            print("📊 Status & Timeline:")
            for key in [
                "status",
                "start_date",
                "due_date",
                "completion_date",
                "duration_estimate",
            ]:
                if key in entity_data and entity_data[key]:
                    print(f"  {key}: {entity_data[key]}")
            print()

            # Classification
            classification_keys = ["category", "tags", "template"]
            if any(
                key in entity_data and entity_data[key] for key in classification_keys
            ):
                print("🏷️  Classification:")
                for key in classification_keys:
                    if key in entity_data and entity_data[key]:
                        value = entity_data[key]
                        if isinstance(value, list):
                            print(f"  {key}: {', '.join(str(v) for v in value)}")
                        else:
                            print(f"  {key}: {value}")
                print()

            # Hierarchy
            hierarchy_keys = ["parent", "children", "related"]
            if any(key in entity_data and entity_data[key] for key in hierarchy_keys):
                print("🌲 Hierarchy:")
                for key in hierarchy_keys:
                    if key in entity_data and entity_data[key]:
                        value = entity_data[key]
                        if isinstance(value, list):
                            print(f"  {key}: {', '.join(str(v) for v in value)}")
                        else:
                            print(f"  {key}: {value}")
                print()

            # Complex properties
            complex_sections = [
                ("repositories", "📚 Repositories"),
                ("storage", "💾 Storage"),
                ("databases", "🗄️  Databases"),
                ("tools", "🔧 Tools"),
                ("models", "🧠 Models"),
                ("knowledge_bases", "📖 Knowledge Bases"),
            ]

            for key, title in complex_sections:
                if key in entity_data and entity_data[key]:
                    print(f"{title}:")
                    items = entity_data[key]
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                # Display first key as identifier
                                first_key = next(iter(item.keys())) if item else None
                                if first_key:
                                    print(f"  • {item[first_key]}")
                                    for k, v in item.items():
                                        if k != first_key:
                                            print(f"      {k}: {v}")
                            else:
                                print(f"  • {item}")
                    print()
