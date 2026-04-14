"""
Show command implementation for displaying content of registry YAML files.
"""

import argparse
import json
import textwrap
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityType, OutputFormat
from hxc.core.operations.show import ShowOperation
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError


@register_command
class ShowCommand(BaseCommand):
    """Command for showing the content of registry files"""

    name = "show"
    help = "Show the content of a registry file"

    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)

        # Add arguments
        parser.add_argument("identifier", help="ID or UID of the entity to show")
        parser.add_argument(
            "--type",
            choices=EntityType.values(),
            help="Entity type (program, project, mission, action). If not specified, all types will be searched.",
        )
        parser.add_argument(
            "--format",
            choices=[
                OutputFormat.PRETTY.value,
                OutputFormat.YAML.value,
                OutputFormat.JSON.value,
            ],
            default=OutputFormat.PRETTY.value,
            help="Output format (default: pretty)",
        )
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Display raw file content without processing",
        )
        parser.add_argument(
            "--registry",
            help="Path to registry (defaults to current or configured registry)",
        )

        return parser

    @classmethod
    def execute(cls, args):
        try:
            # Convert string arguments to enums early
            try:
                entity_type = EntityType.from_string(args.type) if args.type else None
                output_format = OutputFormat.from_string(args.format)
            except ValueError as e:
                print(f"❌ Invalid argument: {e}")
                return 1

            identifier = args.identifier
            raw = args.raw

            # Get the registry path
            registry_path = cls._get_registry_path(args.registry)
            if not registry_path:
                print(
                    "❌ No registry found. Please specify with --registry or initialize one with 'hxc init'"
                )
                return 1

            # Use ShowOperation for entity retrieval
            operation = ShowOperation(registry_path)
            result = operation.get_entity(
                identifier=identifier,
                entity_type=entity_type,
                include_raw=raw,
            )

            if not result["success"]:
                print(f"❌ {result['error']}")
                if entity_type:
                    print(f"   (search limited to type: {entity_type.value})")
                return 1

            # Display the content
            file_path = Path(result["file_path"])

            if raw:
                # Display raw file content
                print(result["raw_content"])
                return 0

            # Display formatted content
            return cls.display_file(file_path, result["entity"], output_format)

        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error displaying file: {e}")
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
    def find_file(
        cls,
        registry_path: str,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[Path]:
        """
        Find a file by ID or UID.

        This method delegates to ShowOperation for consistent behavior
        between CLI and MCP interfaces.

        Args:
            registry_path: Root directory of the registry
            identifier: ID or UID to search for
            entity_type: Optional entity type enum to filter by

        Returns:
            Path to the entity file if found, None otherwise

        Raises:
            PathSecurityError: If any path operation attempts to escape the registry
        """
        operation = ShowOperation(registry_path)
        return operation.find_entity_file(identifier, entity_type)

    @classmethod
    def display_file(
        cls, file_path: Path, content: Dict[str, Any], output_format: OutputFormat
    ) -> int:
        """
        Display the entity content in the specified format.

        Args:
            file_path: Path to the file (for display purposes)
            content: Parsed entity data dictionary
            output_format: OutputFormat enum for output

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            if output_format == OutputFormat.JSON:
                print(json.dumps(content, indent=2))
            elif output_format == OutputFormat.YAML:
                print(yaml.dump(content, default_flow_style=False, sort_keys=False))
            else:  # pretty format
                cls.display_pretty(content, file_path)

            return 0
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            return 1

    @classmethod
    def display_pretty(cls, content: Dict[str, Any], file_path: Path) -> None:
        """Display the content in a pretty human-readable format"""
        # Get basic info
        entity_type = content.get("type", "unknown")
        entity_id = content.get("id", "No ID")
        entity_uid = content.get("uid", "No UID")
        title = content.get("title", "Untitled")

        # Print header
        print(f"═══════════════════════════════════════════════════════")
        print(f"  {title} [{entity_type.upper()}]")
        print(f"  ID: {entity_id} | UID: {entity_uid} | File: {file_path.name}")
        print(f"═══════════════════════════════════════════════════════")

        # Print description if available
        if "description" in content:
            desc = content["description"]
            print("\n📝 Description:")
            print(
                textwrap.fill(
                    desc, width=80, initial_indent="  ", subsequent_indent="  "
                )
            )

        # Print status information
        print("\n📊 Status:")
        status_fields = [
            "status",
            "start_date",
            "due_date",
            "completion_date",
            "duration_estimate",
        ]
        for field in status_fields:
            if field in content:
                print(f"  {field.replace('_', ' ').title()}: {content[field]}")

        # Print classification
        print("\n🔖 Classification:")
        if "category" in content:
            print(f"  Category: {content['category']}")
        if "tags" in content and content["tags"]:
            tags = content["tags"]
            if isinstance(tags, list):
                print(f"  Tags: {', '.join(tags)}")
            else:
                print(f"  Tags: {tags}")

        # Print hierarchy
        hierarchy_fields = ["parent", "children", "related"]
        has_hierarchy = any(field in content for field in hierarchy_fields)
        if has_hierarchy:
            print("\n🌲 Hierarchy:")
            for field in hierarchy_fields:
                if field in content and content[field]:
                    value = content[field]
                    if isinstance(value, list):
                        if value:
                            print(
                                f"  {field.title()}: {', '.join(str(v) for v in value)}"
                            )
                    else:
                        print(f"  {field.title()}: {value}")

        # Print repositories
        if "repositories" in content and content["repositories"]:
            print("\n📚 Repositories:")
            for repo in content["repositories"]:
                name = repo.get("name", "unnamed")
                url = repo.get("url", repo.get("path", "no location"))
                print(f"  • {name}: {url}")

        # Print storage
        if "storage" in content and content["storage"]:
            print("\n💾 Storage:")
            for storage in content["storage"]:
                name = storage.get("name", "unnamed")
                provider = storage.get("provider", "unknown")
                url = storage.get("url", "no url")
                print(f"  • {name} ({provider}): {url}")

        # Print databases
        if "databases" in content and content["databases"]:
            print("\n🗄️  Databases:")
            for db in content["databases"]:
                name = db.get("name", "unnamed")
                db_type = db.get("type", "unknown")
                location = db.get("url", db.get("path", "no location"))
                print(f"  • {name} ({db_type}): {location}")

        # Print tools
        if "tools" in content and content["tools"]:
            print("\n🔧 Tools:")
            for tool in content["tools"]:
                name = tool.get("name", "unnamed")
                provider = tool.get("provider", "unknown")
                url = tool.get("url", "no url")
                print(f"  • {name} ({provider}): {url}")

        # Print models and knowledge bases
        if "models" in content and content["models"]:
            print("\n🧠 Models:")
            for model in content["models"]:
                model_id = model.get("id", "unnamed")
                provider = model.get("provider", "unknown")
                url = model.get("url", "no url")
                print(f"  • {model_id} ({provider}): {url}")

        if "knowledge_bases" in content and content["knowledge_bases"]:
            print("\n📚 Knowledge Bases:")
            for kb in content["knowledge_bases"]:
                kb_id = kb.get("id", "unnamed")
                url = kb.get("url", "no url")
                print(f"  • {kb_id}: {url}")

        # Print template if available
        if "template" in content:
            print(f"\n📋 Template: {content['template']}")

        print("\n" + "─" * 60)