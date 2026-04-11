"""
List command implementation for retrieving registry items.

This module provides the CLI interface for listing registry entities.
It delegates core listing logic to the shared ListOperation class to ensure
behavioral consistency with the MCP tools.
"""
import json
import yaml
import argparse
from typing import Dict, List, Optional, Any

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError
from hxc.core.enums import EntityType, EntityStatus, OutputFormat, SortField
from hxc.core.operations.list import ListOperation, ListOperationError


@register_command
class ListCommand(BaseCommand):
    """Command for listing registry items"""
    
    name = "list"
    help = "List registry items (projects, programs, missions, actions)"
    
    @classmethod
    def register_subparser(cls, subparsers) -> argparse.ArgumentParser:
        parser = super().register_subparser(subparsers)
        
        # Item type argument
        parser.add_argument(
            "type", 
            nargs="?", 
            default="project",
            choices=EntityType.values() + ["all"],
            help="Type of items to list (default: project)"
        )
        
        # Filtering options
        parser.add_argument(
            "--status", 
            choices=EntityStatus.values() + ["any"],
            default="any",
            help="Filter by status (default: any)"
        )
        parser.add_argument(
            "--tag", "--tags",
            dest="tags",
            action="append",
            help="Filter by tag (can be used multiple times)"
        )
        parser.add_argument(
            "--category",
            help="Filter by category"
        )
        parser.add_argument(
            "--parent",
            help="Filter by parent ID"
        )
        parser.add_argument(
            "--id",
            help="Filter by ID or UID"
        )
        parser.add_argument(
            "--query", "-q",
            help="Search in title and description"
        )
        parser.add_argument(
            "--before",
            help="Filter by due date before YYYY-MM-DD"
        )
        parser.add_argument(
            "--after",
            help="Filter by due date after YYYY-MM-DD"
        )
        
        # Display options
        parser.add_argument(
            "--max", "-m",
            type=int,
            default=0,
            help="Maximum number of items to show (0 for all)"
        )
        parser.add_argument(
            "--sort",
            choices=SortField.values(),
            default="title",
            help="Sort items by field (default: title)"
        )
        parser.add_argument(
            "--desc",
            action="store_true",
            help="Sort in descending order"
        )
        parser.add_argument(
            "--format",
            choices=OutputFormat.values(),
            default="table",
            help="Output format (default: table)"
        )
        
        return parser
    
    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        try:
            # Validate and convert enum values early
            try:
                # Convert type argument to EntityType enum (or handle "all")
                if args.type == "all":
                    entity_types = list(EntityType)
                else:
                    entity_types = [EntityType.from_string(args.type)]
                
                # Convert status filter to EntityStatus enum (or handle "any")
                status_filter = None if args.status == "any" else EntityStatus.from_string(args.status)
                
                # Convert sort field to SortField enum
                sort_field = SortField.from_string(args.sort)
                
                # Convert output format to OutputFormat enum
                output_format = OutputFormat.from_string(args.format)
                
            except ValueError as e:
                print(f"❌ Invalid argument: {e}")
                return 1
            
            # Get registry path
            registry_path = cls._get_registry_path()
            if not registry_path:
                print("❌ No registry found. Please initialize or set a registry first.")
                return 1
            
            # Use shared ListOperation for loading, filtering, and sorting
            operation = ListOperation(registry_path)
            
            result = operation.list_entities(
                entity_types=entity_types,
                status=status_filter,
                tags=args.tags,
                category=args.category,
                parent=args.parent,
                identifier=args.id,
                query=args.query,
                due_before=args.before,
                due_after=args.after,
                sort_field=sort_field,
                descending=args.desc,
                max_items=args.max,
                include_file_metadata=True,
            )
            
            if not result["success"]:
                print(f"❌ Error listing items: {result.get('error', 'Unknown error')}")
                return 1
            
            # Display items
            cls._display_items(result["entities"], output_format)
            
            return 0
            
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except ListOperationError as e:
            print(f"❌ Error listing items: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error listing items: {e}")
            return 1
    
    @classmethod
    def _get_registry_path(cls) -> Optional[str]:
        """Get registry path, first from config then by looking for local registry"""
        # Try to get from config
        registry_path = RegistryCommand.get_registry_path()
        if registry_path:
            return registry_path
        
        # If not found in config, try to find in current directory or parents
        return get_project_root()
    
    @classmethod
    def _display_items(cls, items: List[Dict[str, Any]], output_format: OutputFormat) -> None:
        """Display items in the specified format using enum"""
        if not items:
            print("No items found matching criteria.")
            return
            
        if output_format == OutputFormat.TABLE:
            cls._display_table(items)
        elif output_format == OutputFormat.YAML:
            cls._display_yaml(items)
        elif output_format == OutputFormat.JSON:
            cls._display_json(items)
        elif output_format == OutputFormat.ID:
            cls._display_ids(items)
        elif output_format == OutputFormat.PRETTY:
            cls._display_table(items)  # Use table format for pretty display
    
    @classmethod
    def _display_table(cls, items: List[Dict[str, Any]]) -> None:
        """Display items in a table format"""
        # Find the maximum width for each column
        widths = {
            "type": max(4, max(len(str(item.get("type", ""))) for item in items)),
            "title": max(5, max(len(str(item.get("title", ""))) for item in items)),
            "id": max(2, max(len(str(item.get("id", item.get("uid", "")))) for item in items)),
            "status": max(6, max(len(str(item.get("status", ""))) for item in items))
        }
        
        # Print header
        header = f"{'TYPE':<{widths['type']}} {'ID':<{widths['id']}} {'TITLE':<{widths['title']}} {'STATUS':<{widths['status']}}"
        print(header)
        print("-" * len(header))
        
        # Print each item
        for item in items:
            item_type = item.get("type", "")
            item_id = item.get("id", item.get("uid", ""))
            item_title = item.get("title", "")
            item_status = item.get("status", "")
            
            print(f"{item_type:<{widths['type']}} {item_id:<{widths['id']}} {item_title:<{widths['title']}} {item_status:<{widths['status']}}")
    
    @classmethod
    def _display_yaml(cls, items: List[Dict[str, Any]]) -> None:
        """Display items in YAML format"""
        # Remove internal metadata before display
        clean_items = ListOperation.clean_entities_for_output(items, remove_file_metadata=True)
        print(yaml.dump(clean_items, default_flow_style=False))
    
    @classmethod
    def _display_json(cls, items: List[Dict[str, Any]]) -> None:
        """Display items in JSON format"""
        # Remove internal metadata before display
        clean_items = ListOperation.clean_entities_for_output(items, remove_file_metadata=True)
        print(json.dumps(clean_items, indent=2))
    
    @classmethod
    def _display_ids(cls, items: List[Dict[str, Any]]) -> None:
        """Display only item IDs"""
        for item in items:
            item_id = item.get("id", item.get("uid", ""))
            print(item_id)