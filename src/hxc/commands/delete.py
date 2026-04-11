"""
Delete command implementation for removing projects, programs, actions, or missions.
"""
import os
import yaml
import argparse
from pathlib import Path
from typing import Optional, List, Tuple

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError
from hxc.core.enums import EntityType
from hxc.core.operations.delete import (
    DeleteOperation,
    DeleteOperationError,
    EntityNotFoundError,
    AmbiguousEntityError,
)


@register_command
class DeleteCommand(BaseCommand):
    """Command for deleting entities from the registry"""
    
    name = "delete"
    help = "Delete an entity and automatically commit the change"
    
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
        parser.add_argument("--no-commit", action='store_true', help='Do not commit deletion to git')
        
        return parser
    
    @classmethod
    def execute(cls, args):
        try:
            # Get registry path
            registry_path = cls._get_registry_path(args.registry)
            if not registry_path:
                print("❌ No registry found. Please specify with --registry or initialize one with 'hxc init'")
                return 1
            
            # Convert entity type if provided
            entity_type = None
            if args.type:
                try:
                    entity_type = EntityType.from_string(args.type)
                except ValueError as e:
                    print(f"❌ Invalid argument: {e}")
                    return 1
            
            # Create the delete operation
            operation = DeleteOperation(registry_path)
            
            # Get entity info for confirmation
            try:
                info = operation.get_entity_info(args.identifier, entity_type)
            except EntityNotFoundError:
                print(f"❌ No entity found with identifier '{args.identifier}'")
                if args.type:
                    print(f"   Note: Filter was applied for entity type: {args.type}")
                return 1
            except AmbiguousEntityError as e:
                print(f"❌ {e}")
                print("Please specify the entity type with --type")
                return 1
            except DeleteOperationError as e:
                print(f"❌ Error: {e}")
                return 1
            
            entity_title = info["entity_title"]
            entity_type_str = info["entity_type"]
            file_path = info["file_path"]
            
            # Ask for confirmation unless --force is used
            if not args.force:
                print(f"⚠️  Warning: About to delete {entity_type_str} '{entity_title}' at {file_path}")
                confirmation = input("Are you sure? (y/N): ")
                if confirmation.lower() != 'y':
                    print("❌ Deletion cancelled")
                    return 1
            
            # Perform the deletion
            use_git = not args.no_commit
            
            try:
                result = operation.delete_entity(
                    identifier=args.identifier,
                    entity_type=entity_type,
                    use_git=use_git,
                )
            except EntityNotFoundError as e:
                print(f"❌ {e}")
                return 1
            except AmbiguousEntityError as e:
                print(f"❌ {e}")
                return 1
            except DeleteOperationError as e:
                print(f"❌ Error deleting entity: {e}")
                return 1
            
            # Print success message
            print(f"✅ Deleted {result['deleted_type']} at {result['file_path']}")
            
            if args.no_commit:
                print("⚠️  Changes not committed (--no-commit flag used)")
            elif result.get("git_committed"):
                print("📦 Changes committed to git")
            else:
                # Git was requested but not committed (not a git repo, etc.)
                pass
            
            return 0
            
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
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
        Find entity files matching the identifier.
        
        This method is kept for backward compatibility with existing tests.
        It delegates to DeleteOperation.find_entity_files().
        
        Args:
            registry_path: Path to the registry root
            identifier: ID or UID to search for
            entity_type: Optional entity type to filter by
            
        Returns:
            List of tuples (file_path, entity_type)
            
        Raises:
            PathSecurityError: If any path operation attempts to escape the registry
        """
        operation = DeleteOperation(registry_path)
        
        # Convert entity type string to EntityType enum if provided
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = EntityType.from_string(entity_type)
            except ValueError:
                return []
        
        # Get results from the operation
        results = operation.find_entity_files(identifier, entity_type_enum)
        
        # Convert Path objects to strings for backward compatibility
        return [(str(file_path), ent_type) for file_path, ent_type in results]
    
    @classmethod
    def _get_entity_name(cls, file_path: str) -> str:
        """
        Get entity name from file for confirmation message.
        
        This method is kept for backward compatibility with existing tests.
        """
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('title', os.path.basename(file_path))
        except Exception:
            return os.path.basename(file_path)