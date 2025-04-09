"""
Delete command implementation for removing projects, programs, actions, or missions.
"""
import os
import argparse
import glob
from pathlib import Path
from typing import Optional, List, Tuple

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root


@register_command
class DeleteCommand(BaseCommand):
    """Command for deleting entities from the registry"""
    
    name = "delete"
    help = "Delete a program, project, action, or mission from the registry"
    
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
        parser.add_argument('identifier', help='ID or UID of the entity to delete')
        
        # Optional arguments
        parser.add_argument('--type', '-t', choices=list(cls.ENTITY_FOLDERS.keys()),
                          help='Type of entity to delete (only needed if identifier is ambiguous)')
        parser.add_argument('--force', '-f', action='store_true',
                          help='Skip confirmation prompt')
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
            
        # Find the entity file
        files = cls._find_entity_files(registry_path, args.identifier, args.type)
        
        if not files:
            print(f"❌ No entity found with identifier '{args.identifier}'")
            if args.type:
                print(f"   Note: Filter was applied for entity type: {args.type}")
            return 1

        if len(files) > 1:
            print(f"❌ Multiple entities found with identifier '{args.identifier}':")
            for file_path, entity_type in files:
                print(f"   - {entity_type}: {file_path}")
            print("Please specify the entity type with --type")
            return 1
        
        file_path, entity_type = files[0]
        
        # Ask for confirmation unless --force is used
        if not args.force:
            entity_name = cls._get_entity_name(file_path)
            print(f"⚠️  Warning: About to delete {entity_type} '{entity_name}' at {file_path}")
            confirmation = input("Are you sure? (y/N): ")
            if confirmation.lower() != 'y':
                print("❌ Deletion cancelled")
                return 1
        
        # Delete the file
        try:
            os.remove(file_path)
            print(f"✅ Deleted {entity_type} at {file_path}")
            return 0
        except Exception as e:
            print(f"❌ Error deleting entity: {e}")
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
    def _find_entity_files(cls, registry_path: str, identifier: str, entity_type: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Find entity files matching the identifier
        
        Args:
            registry_path: Path to the registry root
            identifier: ID or UID to search for
            entity_type: Optional entity type to filter by
            
        Returns:
            List of tuples (file_path, entity_type)
        """
        results = []
        
        # Determine which entity types to search
        entity_types = [entity_type] if entity_type else cls.ENTITY_FOLDERS.keys()
        
        for ent_type in entity_types:
            folder = cls.ENTITY_FOLDERS[ent_type]
            prefix = cls.FILE_PREFIXES[ent_type]
            
            # Check for direct match with file name pattern
            folder_path = Path(registry_path) / folder
            
            # Look for files with matching UID in filename (prog-{uid}.yml)
            uid_pattern = f"{prefix}-{identifier}.yml"
            for file_path in folder_path.glob(uid_pattern):
                results.append((str(file_path), ent_type))
            
            # If no direct matches, search inside files for ID field
            if not results:
                for file_path in folder_path.glob(f"{prefix}-*.yml"):
                    # Simple ID check - only check if file contains '"id": "{identifier}"'
                    # or "id: {identifier}" for YAML format
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if f'"id": "{identifier}"' in content or f"id: {identifier}" in content:
                            results.append((str(file_path), ent_type))
        
        return results
    
    @classmethod
    def _get_entity_name(cls, file_path: str) -> str:
        """
        Get entity name from file for confirmation message
        
        This is a simple implementation that extracts the title field from the YAML file.
        """
        try:
            import yaml
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('title', os.path.basename(file_path))
        except Exception:
            # If we can't extract the title, just return the filename
            return os.path.basename(file_path)