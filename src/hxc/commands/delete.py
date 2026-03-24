"""
Delete command implementation for removing projects, programs, actions, or missions.
"""
import os
import yaml
import argparse
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError
from hxc.utils.git import commit_entity_change, print_commit_result
from hxc.core.enums import EntityType


@register_command
class DeleteCommand(BaseCommand):
    """Command for deleting entities from the registry"""
    
    name = "delete"
    help = "Delete a program, project, action, or mission from the registry"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        
        # Required arguments
        parser.add_argument('identifier', help='ID or UID of the entity to delete')
        
        # Optional arguments
        parser.add_argument('--type', '-t', choices=EntityType.values(),
                          help='Type of entity to delete (only needed if identifier is ambiguous)')
        parser.add_argument('--force', '-f', action='store_true',
                          help='Skip confirmation prompt')
        parser.add_argument('--registry',
                          help='Path to registry (defaults to current or configured registry)')
        parser.add_argument('--no-commit',
                          action='store_true',
                          help='Skip automatic git commit after deleting the entity')
        
        return parser
    
    @classmethod
    def execute(cls, args):
        try:
            # Convert entity type if provided
            entity_type_enum = None
            if args.type:
                try:
                    entity_type_enum = EntityType.from_string(args.type)
                except ValueError as e:
                    print(f"❌ Invalid argument: {e}")
                    return 1
            
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
            
            # Verify the file is within the registry before deletion
            try:
                secure_file_path = resolve_safe_path(registry_path, file_path)
            except PathSecurityError as e:
                print(f"❌ Security error: {e}")
                return 1
            
            # Read entity data before deletion (needed for commit message)
            entity_data = cls._read_entity_data(str(secure_file_path))
            entity_name = entity_data.get('title', os.path.basename(file_path))
            
            # Ask for confirmation unless --force is used
            if not args.force:
                print(f"⚠️  Warning: About to delete {entity_type} '{entity_name}' at {secure_file_path}")
                confirmation = input("Are you sure? (y/N): ")
                if confirmation.lower() != 'y':
                    print("❌ Deletion cancelled")
                    return 1
            
            # Delete the file
            try:
                os.remove(str(secure_file_path))
                print(f"✅ Deleted {entity_type} at {secure_file_path}")
            except Exception as e:
                print(f"❌ Error deleting entity: {e}")
                return 1
            
            # Git commit (unless --no-commit is specified)
            no_commit = getattr(args, 'no_commit', False)
            if no_commit:
                print("⚠️  Changes not committed (--no-commit flag used)")
            else:
                result = commit_entity_change(
                    registry_path=registry_path,
                    file_path=secure_file_path,
                    action="Delete",
                    entity_data=entity_data,
                )
                print_commit_result(result, no_commit_flag=False)
            
            return 0
            
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
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
            
        Raises:
            PathSecurityError: If any path operation attempts to escape the registry
        """
        results = []
        
        # Determine which entity types to search
        if entity_type:
            try:
                entity_types = [EntityType.from_string(entity_type)]
            except ValueError:
                return results
        else:
            entity_types = list(EntityType)
        
        for ent_type in entity_types:
            folder = ent_type.get_folder_name()
            prefix = ent_type.get_file_prefix()
            
            # Securely resolve the folder path
            try:
                folder_path = resolve_safe_path(registry_path, folder)
            except PathSecurityError:
                # Skip this folder if it's not accessible
                continue
            
            if not folder_path.exists():
                continue
            
            # Look for files with matching UID in filename (prog-{uid}.yml)
            uid_pattern = f"{prefix}-{identifier}.yml"
            for file_path in folder_path.glob(uid_pattern):
                try:
                    # Verify the file is within the registry
                    secure_file_path = resolve_safe_path(registry_path, file_path)
                    results.append((str(secure_file_path), ent_type.value))
                except PathSecurityError:
                    # Skip files that are outside the registry
                    continue
            
            # If no direct matches, search inside files for ID field
            if not results:
                for file_path in folder_path.glob(f"{prefix}-*.yml"):
                    try:
                        # Verify the file is within the registry
                        secure_file_path = resolve_safe_path(registry_path, file_path)
                        
                        # Read and check the file content
                        with open(secure_file_path, 'r') as f:
                            data = yaml.safe_load(f)
                            if data and isinstance(data, dict):
                                if data.get('id') == identifier or data.get('uid') == identifier:
                                    results.append((str(secure_file_path), ent_type.value))
                    except PathSecurityError:
                        # Skip files that are outside the registry
                        continue
                    except Exception:
                        # Skip files that can't be parsed
                        continue
        
        return results
    
    @classmethod
    def _read_entity_data(cls, file_path: str) -> Dict[str, Any]:
        """
        Read entity data from file for commit message generation.
        
        Args:
            file_path: Path to the entity YAML file
            
        Returns:
            Dictionary with entity data, or minimal dict if file cannot be read
        """
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    return data
        except Exception:
            pass
        
        # Return minimal data if file cannot be read
        return {
            'title': os.path.basename(file_path),
            'type': 'entity',
        }
    
    @classmethod
    def _get_entity_name(cls, file_path: str) -> str:
        """
        Get entity name from file for confirmation message
        
        This is a simple implementation that extracts the title field from the YAML file.
        """
        data = cls._read_entity_data(file_path)
        return data.get('title', os.path.basename(file_path))