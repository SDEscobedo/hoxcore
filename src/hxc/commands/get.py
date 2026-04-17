"""
Get command implementation for retrieving entity property values
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityType
from hxc.core.operations.get import (
    GetPropertyOperation,
    GetPropertyOperationError,
    PropertyType,
)
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError


@register_command
class GetCommand(BaseCommand):
    """Command for retrieving entity property values"""

    name = "get"
    help = "Get a property value from a program, project, action, or mission"

    # Property classification sets - delegated to GetPropertyOperation for consistency
    # but exposed here for backwards compatibility and direct access
    SCALAR_PROPERTIES: Set[str] = GetPropertyOperation.SCALAR_PROPERTIES
    LIST_PROPERTIES: Set[str] = GetPropertyOperation.LIST_PROPERTIES
    COMPLEX_PROPERTIES: Set[str] = GetPropertyOperation.COMPLEX_PROPERTIES
    SPECIAL_PROPERTIES: Set[str] = GetPropertyOperation.SPECIAL_PROPERTIES
    ALL_PROPERTIES: Set[str] = GetPropertyOperation.ALL_PROPERTIES

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

            # Get registry path
            registry_path = cls._get_registry_path(args.registry)
            if not registry_path:
                print(
                    "❌ No registry found. Please specify with --registry or initialize one with 'hxc init'"
                )
                return 1

            # Create the operation
            operation = GetPropertyOperation(registry_path)

            # Validate property name using shared operation
            property_name = args.property.lower()
            is_valid, normalized_name = operation.validate_property_name(property_name)

            if not is_valid:
                print(f"❌ Unknown property '{args.property}'")
                print(
                    f"   Available properties: {', '.join(sorted(operation.ALL_PROPERTIES))}"
                )
                return 1

            # Use the shared operation to get the property
            result = operation.get_property(
                identifier=args.identifier,
                property_name=normalized_name,
                entity_type=entity_type,
                index=args.index,
                key_filter=args.key,
            )

            # Handle errors from the operation
            if not result["success"]:
                error_msg = result.get("error", "Unknown error")

                # Check for entity not found
                if "not found" in error_msg.lower() and "Entity" in error_msg:
                    print(f"❌ No entity found with identifier '{args.identifier}'")
                    if entity_type:
                        print(f"   (search limited to type: {entity_type.value})")
                    return 1

                # Check for property not set
                if "not set" in error_msg.lower():
                    print(f"⚠️  Property '{normalized_name}' is not set")
                    return 1

                # Check for index out of range
                if "out of range" in error_msg.lower():
                    print(f"⚠️  {error_msg}")
                    return 1

                # Check for invalid key filter format
                if "invalid key filter" in error_msg.lower():
                    print(f"⚠️  Invalid key filter format. Use key:value (e.g., name:github)")
                    return 1

                # Check for key filter no match
                if "no items found" in error_msg.lower():
                    print(f"⚠️  {error_msg}")
                    return 1

                # Generic error
                print(f"❌ Error: {error_msg}")
                return 1

            # Get the value from the result
            value = result["value"]

            # Display the value based on format
            cls._display_value(value, args.format, normalized_name)
            return 0

        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except GetPropertyOperationError as e:
            print(f"❌ Error: {e}")
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
    def _display_value(cls, value: Any, format_type: str, property_name: str) -> None:
        """
        Display a property value in the specified format

        Args:
            value: Value to display
            format_type: Output format (raw, yaml, json, pretty)
            property_name: Name of the property (for context in pretty format)
        """
        # Handle 'all' property specially - it returns full entity dict
        if property_name == "all":
            cls._display_all_properties(value, format_type)
            return

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