"""
Create command implementation for generating new projects, programs, actions, or missions.
"""
import os
import uuid
import yaml
import datetime
from pathlib import Path
import argparse
from typing import Dict, Any, List, Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import get_safe_entity_path, PathSecurityError


@register_command
class CreateCommand(BaseCommand):
    """Create a new entity (program, project, action, mission) in the registry"""
    
    name = "create"
    help = "Create a new program, project, action, or mission"
    
    ENTITY_TYPES = ["program", "project", "mission", "action"]
    ENTITY_FOLDERS = {
        "program": "programs",
        "project": "projects",
        "mission": "missions",
        "action": "actions"
    }
    FILE_PREFIXES = {
        "program": "prog",
        "project": "proj",
        "mission": "miss",
        "action": "act"
    }
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        
        # Required arguments
        parser.add_argument('type', choices=cls.ENTITY_TYPES,
                          help='Type of entity to create')
        parser.add_argument('title', 
                          help='Title of the entity')
        
        # Optional arguments
        parser.add_argument('--id', dest='custom_id',
                          help='Custom ID for the entity (e.g., P-001)')
        parser.add_argument('--description', '-d',
                          help='Description of the entity')
        parser.add_argument('--status', default='active',
                          choices=['active', 'completed', 'on-hold', 'canceled'],
                          help='Status of the entity (default: active)')
        parser.add_argument('--start-date',
                          help='Start date in YYYY-MM-DD format (default: today)')
        parser.add_argument('--due-date',
                          help='Due date in YYYY-MM-DD format')
        parser.add_argument('--category',
                          help='Category path (e.g., software.dev/cli-tool)')
        parser.add_argument('--tags', nargs='+',
                          help='List of tags (space separated)')
        parser.add_argument('--parent',
                          help='Parent entity UID or ID')
        parser.add_argument('--template',
                          help='Template to use (e.g., software.dev/cli-tool.default)')
        parser.add_argument('--registry',
                          help='Path to registry (defaults to current or configured registry)')
        
        return parser
    
    @classmethod
    def execute(cls, args):
        # Get registry path
        registry_path = cls._get_registry_path(args.registry)
        if not registry_path:
            print("❌ No registry found. Please specify with --registry or initialize one with 'hxc init'")
            return 1
            
        # Generate entity data based on arguments
        entity_data = cls._build_entity_data(args)
        
        # Determine file name
        entity_type = args.type
        uid = entity_data.get('uid', str(uuid.uuid4())[:8])
        file_prefix = cls.FILE_PREFIXES[entity_type]
        file_name = f"{file_prefix}-{uid}.yml"
        
        # Get safe path using path security utilities
        try:
            file_path = get_safe_entity_path(registry_path, entity_type, file_name)
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except ValueError as e:
            print(f"❌ Invalid entity type: {e}")
            return 1
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        try:
            with open(file_path, 'w') as f:
                yaml.dump(entity_data, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Created {entity_type} '{entity_data['title']}' at {file_path}")
            return 0
        except Exception as e:
            print(f"❌ Error creating {entity_type}: {e}")
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
    def _build_entity_data(cls, args) -> Dict[str, Any]:
        """Build entity data dictionary from arguments"""
        # Generate or use provided UID
        uid = str(uuid.uuid4())[:8]  # Use first 8 chars of a UUID
        
        # Set default dates
        today = datetime.date.today().isoformat()
        
        # Basic entity data
        entity = {
            # Basic Metadata
            "type": args.type,
            "uid": uid,
            "title": args.title,
            
            # Status & Lifecycle 
            "status": args.status,
            "start_date": args.start_date or today,
        }
        
        # Add optional fields if provided
        if args.custom_id:
            entity["id"] = args.custom_id
        
        if args.description:
            entity["description"] = args.description
            
        if args.due_date:
            entity["due_date"] = args.due_date
            
        if args.category:
            entity["category"] = args.category
            
        if args.tags:
            entity["tags"] = args.tags
            
        if args.parent:
            entity["parent"] = args.parent
            
        if args.template:
            entity["template"] = args.template
            
        # Add default empty sections for structure
        entity["children"] = []
        entity["related"] = []
        entity["repositories"] = []
        entity["storage"] = []
        entity["databases"] = []
        entity["tools"] = []
        entity["models"] = []
        entity["knowledge_bases"] = []
        
        return entity