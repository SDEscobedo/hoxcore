"""
List command implementation for retrieving registry items.
"""
import os
import yaml
import pathlib
import datetime
from typing import Dict, List, Optional, Any, Set
from operator import itemgetter
import argparse

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError


@register_command
class ListCommand(BaseCommand):
    """Command for listing registry items"""
    
    name = "list"
    help = "List registry items (projects, programs, missions, actions)"
    
    # Valid item types
    VALID_TYPES = ["project", "program", "mission", "action"]
    # Mapping from item type to directory and file prefix
    TYPE_DIR_MAP = {
        "project": ("projects", "proj-"),
        "program": ("programs", "prog-"),
        "mission": ("missions", "miss-"),
        "action": ("actions", "act-"),
    }
    # Valid status values
    VALID_STATUSES = ["active", "completed", "on-hold", "cancelled", "planned"]
    
    @classmethod
    def register_subparser(cls, subparsers) -> argparse.ArgumentParser:
        parser = super().register_subparser(subparsers)
        
        # Item type argument
        parser.add_argument(
            "type", 
            nargs="?", 
            default="project",
            choices=cls.VALID_TYPES + ["all"],
            help="Type of items to list (default: project)"
        )
        
        # Filtering options
        parser.add_argument(
            "--status", 
            choices=cls.VALID_STATUSES + ["any"],
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
            choices=["title", "id", "due_date", "status", "created", "modified"],
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
            choices=["table", "yaml", "json", "id"],
            default="table",
            help="Output format (default: table)"
        )
        
        return parser
    
    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        try:
            # Get registry path
            registry_path = cls._get_registry_path()
            if not registry_path:
                print("❌ No registry found. Please initialize or set a registry first.")
                return 1
            
            # Determine which types to list
            item_types = cls.VALID_TYPES if args.type == "all" else [args.type]
            
            # Collect and filter items
            all_items = []
            for item_type in item_types:
                items = cls._get_items(registry_path, item_type)
                filtered_items = cls._filter_items(items, args)
                all_items.extend(filtered_items)
            
            # Sort items
            all_items = cls._sort_items(all_items, args.sort, args.desc)
            
            # Apply maximum limit if specified
            if args.max > 0:
                all_items = all_items[:args.max]
            
            # Display items
            cls._display_items(all_items, args.format)
            
            return 0
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
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
    def _get_items(cls, registry_path: str, item_type: str) -> List[Dict[str, Any]]:
        """Get all items of a specific type from registry"""
        items = []
        
        # Get directory and file prefix for this type
        dir_name, file_prefix = cls.TYPE_DIR_MAP[item_type]
        
        # Securely resolve path to the directory containing this type of items
        try:
            type_dir = resolve_safe_path(registry_path, dir_name)
        except PathSecurityError as e:
            print(f"Warning: Security error accessing {dir_name}: {e}")
            return []
        
        if not type_dir.exists():
            return []
        
        # Load each YAML file in the directory
        for file_path in type_dir.glob(f"{file_prefix}*.yml"):
            try:
                # Verify that the file is within the registry
                secure_file_path = resolve_safe_path(registry_path, file_path)
                
                with open(secure_file_path, 'r') as f:
                    item_data = yaml.safe_load(f)
                    
                # Add file metadata
                file_stat = secure_file_path.stat()
                item_data['_file'] = {
                    'path': str(secure_file_path),
                    'name': secure_file_path.name,
                    'created': datetime.datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d'),
                    'modified': datetime.datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d')
                }
                
                items.append(item_data)
            except PathSecurityError as e:
                print(f"Warning: Security error with {file_path}: {e}")
            except Exception as e:
                print(f"Warning: Could not load {file_path}: {e}")
        
        return items
    
    @classmethod
    def _filter_items(cls, items: List[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
        """Filter items based on command arguments"""
        filtered_items = []
        
        for item in items:
            # Filter by status
            if args.status != "any" and item.get("status") != args.status:
                continue
            
            # Filter by tags
            if args.tags:
                item_tags = item.get("tags", [])
                if not all(tag in item_tags for tag in args.tags):
                    continue
            
            # Filter by category
            if args.category and item.get("category") != args.category:
                continue
            
            # Filter by parent
            if args.parent and item.get("parent") != args.parent:
                continue
                
            # Filter by ID
            if args.id:
                item_id = item.get("id", "")
                item_uid = item.get("uid", "")
                if args.id != item_id and args.id != item_uid:
                    continue
            
            # Filter by query text
            if args.query:
                query = args.query.lower()
                title = item.get("title", "").lower()
                description = item.get("description", "").lower()
                if query not in title and query not in description:
                    continue
            
            # Filter by date range
            if args.before:
                due_date = item.get("due_date")
                if due_date and due_date > args.before:
                    continue
                    
            if args.after:
                due_date = item.get("due_date")
                if not due_date or due_date < args.after:
                    continue
            
            filtered_items.append(item)
        
        return filtered_items
    
    @classmethod
    def _sort_items(cls, items: List[Dict[str, Any]], sort_key: str, descending: bool) -> List[Dict[str, Any]]:
        """Sort items by specified key"""
        # Handle special sort keys
        if sort_key == "created":
            items = sorted(items, key=lambda x: x.get("_file", {}).get("created", ""), reverse=descending)
        elif sort_key == "modified":
            items = sorted(items, key=lambda x: x.get("_file", {}).get("modified", ""), reverse=descending)
        else:
            # For all other keys, sort by the actual key in the items
            items = sorted(items, key=lambda x: x.get(sort_key, ""), reverse=descending)
        
        return items
    
    @classmethod
    def _display_items(cls, items: List[Dict[str, Any]], format_type: str) -> None:
        """Display items in the specified format"""
        if not items:
            print("No items found matching criteria.")
            return
            
        if format_type == "table":
            cls._display_table(items)
        elif format_type == "yaml":
            cls._display_yaml(items)
        elif format_type == "json":
            cls._display_json(items)
        elif format_type == "id":
            cls._display_ids(items)
    
    @classmethod
    def _display_table(cls, items: List[Dict[str, Any]]) -> None:
        """Display items in a table format"""
        # Determine common fields across all items
        common_fields = {"type", "title", "id", "uid", "status"}
        
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
        clean_items = []
        for item in items:
            clean_item = {k: v for k, v in item.items() if not k.startswith('_')}
            clean_items.append(clean_item)
            
        print(yaml.dump(clean_items, default_flow_style=False))
    
    @classmethod
    def _display_json(cls, items: List[Dict[str, Any]]) -> None:
        """Display items in JSON format"""
        import json
        
        # Remove internal metadata before display
        clean_items = []
        for item in items:
            clean_item = {k: v for k, v in item.items() if not k.startswith('_')}
            clean_items.append(clean_item)
            
        print(json.dumps(clean_items, indent=2))
    
    @classmethod
    def _display_ids(cls, items: List[Dict[str, Any]]) -> None:
        """Display only item IDs"""
        for item in items:
            item_id = item.get("id", item.get("uid", ""))
            print(item_id)