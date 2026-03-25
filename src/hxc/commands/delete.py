"""
Delete command implementation for removing projects, programs, actions, or missions.
"""
import os
import yaml
import argparse
import subprocess
import re
from pathlib import Path
from typing import Optional, List, Tuple

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError
from hxc.commands.edit import EditCommand


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
            
            # Ask for confirmation unless --force is used
            if not args.force:
                entity_name = cls._get_entity_name(str(secure_file_path))
                print(f"⚠️  Warning: About to delete {entity_type} '{entity_name}' at {secure_file_path}")
                confirmation = input("Are you sure? (y/N): ")
                if confirmation.lower() != 'y':
                    print("❌ Deletion cancelled")
                    return 1
            
            # Read entity data before deleting the file
            try:
                with open(secure_file_path, 'r') as f:
                    entity_data = yaml.safe_load(f) or {}
            except FileNotFoundError:
                print(f"❌ File not found at {secure_file_path}. Cannot proceed.")
                return 1
            except Exception as e:
                print(f"❌ Error reading entity file: {e}")
                return 1

            if args.no_commit:
                # Simple file deletion
                os.remove(str(secure_file_path))
                print(f"✅ Deleted {entity_type} at {secure_file_path}")
                print("⚠️  Changes not committed (--no-commit flag used)")
            else:
                # Git-aware deletion
                return cls._git_delete_entity(registry_path, secure_file_path, entity_type, entity_data)

            return 0
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ An unexpected error occurred: {e}")
            return 1

    @classmethod
    def _confirm_deletion(cls, secure_file_path: Path, entity_type: str) -> bool:
        """Get user confirmation to delete an entity."""
        entity_name = cls._get_entity_name(str(secure_file_path))
        print(f"⚠️  Warning: About to delete {entity_type} '{entity_name}' at {secure_file_path}")
        confirmation = input("Are you sure? (y/N): ")
        if confirmation.lower() != 'y':
            print("❌ Deletion cancelled")
            return False
        return True

    @classmethod
    def _git_delete_entity(cls, registry_path: str, secure_file_path: Path, entity_type: str, entity_data: dict) -> int:
        """
        Handles the deletion of an entity using Git.
        It stages the deletion and commits it with a formatted message.
        If the file is not tracked by Git, it just deletes the file from the filesystem.
        """
        git_root = EditCommand._find_git_root(registry_path)
        if not git_root:
            print("⚠️  No git repository found. Deleting file from disk only.")
            os.remove(str(secure_file_path))
            print(f"✅ Deleted {entity_type} at {secure_file_path}")
            return 0
        
        if not EditCommand._git_available():
            print("⚠️ Git is not installed.")
            os.remove(str(secure_file_path))
            print(f"✅ Deleted {entity_type} at {secure_file_path}")
            return 0
        
        rel_path = secure_file_path.relative_to(Path(git_root)).as_posix()
        
        # Check if there are uncommitted changes
        status_result = subprocess.run(["git", "status", "--porcelain"], cwd=git_root, capture_output=True, text=True)
        if status_result.stdout:
            print("Uncommitted changes exist. Staging only the deleted file.")

        rm_result = subprocess.run(["git", "rm", rel_path], cwd=git_root, capture_output=True, text=True)

        if rm_result.returncode != 0:
            print(f"⚠️  File not tracked by Git. Deleting from disk only.")
            os.remove(str(secure_file_path))
            print(f"✅ Deleted untracked file: {secure_file_path}")
            return 0

        prefix = cls.FILE_PREFIXES.get(entity_type, "ent")
        uid = entity_data.get('uid', "Unknown")
        title = entity_data.get('title', os.path.basename(str(secure_file_path)))
        entity_id = entity_data.get('id', "Unknown")

        commit_message = (
            f"Delete {prefix}-{uid}: {title}\n\n"
            f"Entity type: {entity_type}\n"
            f"Entity ID: {entity_id}\n"
            f"Entity UID: {uid}"
        )

        try:
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=git_root,
                capture_output=True,
                text=True
            )

            if commit_result.returncode != 0:
                print(f"❌ git commit failed: {commit_result.stderr.strip()}")
                print("     Delete operation succeded, but commit was skipped.")
                return 0
        
        except Exception as e:
            print(f"❌ git commit failed: {e}")
            print("     Delete operation succeded, but commit was skipped.")
            return 0

        commit_hash = EditCommand._parse_commit_hash(commit_result.stdout)
        hash_display = f"({commit_hash})" if commit_hash else "(empty commit)"
        
        print(f"✅ Deleted {entity_type} at {secure_file_path}")
        print(f"📦 Changes committed to git {hash_display}")
        return 0
    
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
        entity_types = [entity_type] if entity_type else cls.ENTITY_FOLDERS.keys()
        
        for ent_type in entity_types:
            folder = cls.ENTITY_FOLDERS[ent_type]
            prefix = cls.FILE_PREFIXES[ent_type]
            
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
                    results.append((str(secure_file_path), ent_type))
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
                                    results.append((str(secure_file_path), ent_type))
                    except PathSecurityError:
                        # Skip files that are outside the registry
                        continue
                    except Exception:
                        # Skip files that can't be parsed
                        continue
        
        return results
    
    @classmethod
    def _get_entity_name(cls, file_path: str) -> str:
        """
        Get entity name from file for confirmation message
        
        This is a simple implementation that extracts the title field from the YAML file.
        """
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
                return data.get('title', os.path.basename(file_path))
        except Exception:
            # If we can't extract the title, just return the filename
            return os.path.basename(file_path)