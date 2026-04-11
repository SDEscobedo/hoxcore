"""
Delete Operation for HoxCore Registry.

This module provides the shared delete operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Entity discovery by ID or UID
- Git-aware deletion with automatic commits
- Path security enforcement
- Structured commit message generation
- Graceful fallback for non-git registries
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import yaml

from hxc.core.enums import EntityType
from hxc.utils.path_security import resolve_safe_path, PathSecurityError
from hxc.utils.git import find_git_root, git_available, commit_entity_change


class DeleteOperationError(Exception):
    """Base exception for delete operation errors"""
    pass


class EntityNotFoundError(DeleteOperationError):
    """Raised when the entity to delete cannot be found"""
    pass


class AmbiguousEntityError(DeleteOperationError):
    """Raised when multiple entities match the identifier"""
    pass


class DeleteOperation:
    """
    Shared delete operation for CLI and MCP interfaces.
    
    This class provides the core entity deletion logic including:
    - Entity discovery by ID or UID
    - Entity data loading for commit messages
    - Git-aware deletion with automatic commits
    - Fallback deletion for non-git scenarios
    - Path security enforcement
    """
    
    # Mapping of entity types to folder names
    ENTITY_FOLDERS = {
        "program": "programs",
        "project": "projects",
        "mission": "missions",
        "action": "actions",
    }
    
    # Mapping of entity types to file prefixes
    FILE_PREFIXES = {
        "program": "prog",
        "project": "proj",
        "mission": "miss",
        "action": "act",
    }
    
    def __init__(self, registry_path: str):
        """
        Initialize the delete operation.
        
        Args:
            registry_path: Path to the registry root directory
        """
        self.registry_path = registry_path
    
    def find_entity_files(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None
    ) -> List[Tuple[Path, str]]:
        """
        Find entity files matching the identifier.
        
        Args:
            identifier: ID or UID to search for
            entity_type: Optional entity type to filter by
            
        Returns:
            List of tuples (file_path, entity_type_string)
            
        Raises:
            PathSecurityError: If any path operation attempts to escape the registry
        """
        results: List[Tuple[Path, str]] = []
        
        # Determine which entity types to search
        if entity_type:
            entity_types = [entity_type.value]
        else:
            entity_types = list(self.ENTITY_FOLDERS.keys())
        
        for ent_type in entity_types:
            folder = self.ENTITY_FOLDERS[ent_type]
            prefix = self.FILE_PREFIXES[ent_type]
            
            # Securely resolve the folder path
            try:
                folder_path = resolve_safe_path(self.registry_path, folder)
            except PathSecurityError:
                continue
            
            if not folder_path.exists():
                continue
            
            # Look for files with matching UID in filename
            uid_pattern = f"{prefix}-{identifier}.yml"
            for file_path in folder_path.glob(uid_pattern):
                try:
                    secure_file_path = resolve_safe_path(self.registry_path, file_path)
                    results.append((secure_file_path, ent_type))
                except PathSecurityError:
                    continue
            
            # If no direct matches, search inside files for ID field
            if not results:
                for file_path in folder_path.glob(f"{prefix}-*.yml"):
                    try:
                        secure_file_path = resolve_safe_path(self.registry_path, file_path)
                        
                        with open(secure_file_path, 'r') as f:
                            data = yaml.safe_load(f)
                            if data and isinstance(data, dict):
                                if data.get('id') == identifier or data.get('uid') == identifier:
                                    results.append((secure_file_path, ent_type))
                    except PathSecurityError:
                        continue
                    except Exception:
                        continue
        
        return results
    
    def load_entity_data(self, file_path: Path) -> Dict[str, Any]:
        """
        Load entity data from a YAML file.
        
        Args:
            file_path: Path to the entity file
            
        Returns:
            Entity data dictionary
            
        Raises:
            PathSecurityError: If path validation fails
            FileNotFoundError: If file does not exist
            ValueError: If file contains invalid data
        """
        secure_file_path = resolve_safe_path(self.registry_path, file_path)
        
        with open(secure_file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        if not data or not isinstance(data, dict):
            raise ValueError(f"Invalid entity data in {file_path}")
        
        return data
    
    def get_entity_title(self, file_path: Path) -> str:
        """
        Get entity title from file for display purposes.
        
        Args:
            file_path: Path to the entity file
            
        Returns:
            Entity title or filename as fallback
        """
        try:
            data = self.load_entity_data(file_path)
            return data.get('title', file_path.name)
        except Exception:
            return file_path.name
    
    def delete_file(self, file_path: Path) -> None:
        """
        Delete an entity file from the filesystem.
        
        Args:
            file_path: Path to the entity file
            
        Raises:
            PathSecurityError: If path validation fails
            OSError: If file deletion fails
        """
        secure_file_path = resolve_safe_path(self.registry_path, file_path)
        os.remove(str(secure_file_path))
    
    def delete_with_git(
        self,
        file_path: Path,
        entity_data: Dict[str, Any],
        entity_type: str
    ) -> bool:
        """
        Delete an entity file using git operations.
        
        Stages the deletion with `git rm` and commits with a structured message.
        Falls back to simple file deletion if git operations fail.
        
        Args:
            file_path: Path to the entity file
            entity_data: Entity data dictionary
            entity_type: Entity type string
            
        Returns:
            True if git commit was successful, False otherwise
        """
        import subprocess
        
        git_root = find_git_root(self.registry_path)
        if git_root is None:
            # Not a git repository, fall back to simple deletion
            self.delete_file(file_path)
            return False
        
        if not git_available():
            # Git not installed, fall back to simple deletion
            self.delete_file(file_path)
            return False
        
        secure_file_path = resolve_safe_path(self.registry_path, file_path)
        rel_path = secure_file_path.relative_to(Path(git_root)).as_posix()
        
        # Attempt git rm
        rm_result = subprocess.run(
            ["git", "rm", rel_path],
            cwd=git_root,
            capture_output=True,
            text=True
        )
        
        if rm_result.returncode != 0:
            # File not tracked by git, fall back to simple deletion
            self.delete_file(file_path)
            return False
        
        # Build commit message
        prefix = self.FILE_PREFIXES.get(entity_type, "ent")
        uid = entity_data.get('uid', "unknown")
        title = entity_data.get('title', file_path.name)
        entity_id = entity_data.get('id', "unknown")
        
        commit_message = (
            f"Delete {prefix}-{uid}: {title}\n\n"
            f"Entity type: {entity_type}\n"
            f"Entity ID: {entity_id}\n"
            f"Entity UID: {uid}"
        )
        
        # Commit the deletion
        try:
            commit_result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=git_root,
                capture_output=True,
                text=True
            )
            
            if commit_result.returncode != 0:
                # Commit failed but file was removed from index
                return False
            
            return True
            
        except Exception:
            return False
    
    def delete_entity(
        self,
        identifier: str,
        *,
        entity_type: Optional[EntityType] = None,
        use_git: bool = True,
    ) -> Dict[str, Any]:
        """
        Delete an entity from the registry.
        
        This is the main entry point for entity deletion, handling:
        - Entity discovery by ID or UID
        - Ambiguous match detection
        - Git-aware deletion with automatic commits
        - Fallback deletion for non-git scenarios
        
        Args:
            identifier: ID or UID of the entity to delete
            entity_type: Optional entity type filter
            use_git: Whether to use git for deletion (default: True)
            
        Returns:
            Dictionary containing:
            - success: bool
            - identifier: str
            - deleted_title: str (on success)
            - deleted_type: str (on success)
            - file_path: str (on success)
            - git_committed: bool (on success, if use_git=True)
            
        Raises:
            EntityNotFoundError: If no entity matches the identifier
            AmbiguousEntityError: If multiple entities match
            PathSecurityError: If path validation fails
        """
        # Find matching entity files
        files = self.find_entity_files(identifier, entity_type)
        
        if not files:
            raise EntityNotFoundError(f"Entity not found: {identifier}")
        
        if len(files) > 1:
            type_list = [f"{ent_type}: {str(path)}" for path, ent_type in files]
            raise AmbiguousEntityError(
                f"Multiple entities found with identifier '{identifier}': {', '.join(type_list)}. "
                "Please specify the entity type."
            )
        
        file_path, entity_type_str = files[0]
        
        # Load entity data before deletion
        try:
            entity_data = self.load_entity_data(file_path)
        except FileNotFoundError:
            raise EntityNotFoundError(f"Entity file not found: {file_path}")
        except Exception as e:
            raise DeleteOperationError(f"Error loading entity data: {e}")
        
        entity_title = entity_data.get('title', identifier)
        
        # Perform deletion
        git_committed = False
        
        if use_git:
            git_committed = self.delete_with_git(file_path, entity_data, entity_type_str)
        else:
            self.delete_file(file_path)
        
        return {
            "success": True,
            "identifier": identifier,
            "deleted_title": entity_title,
            "deleted_type": entity_type_str,
            "file_path": str(file_path),
            "entity": entity_data,
            "git_committed": git_committed,
        }
    
    def get_entity_info(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Dict[str, Any]:
        """
        Get information about an entity without deleting it.
        
        Useful for confirmation prompts and pre-deletion checks.
        
        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type filter
            
        Returns:
            Dictionary containing:
            - success: bool
            - identifier: str
            - entity_title: str (on success)
            - entity_type: str (on success)
            - file_path: str (on success)
            - entity: dict (on success)
            
        Raises:
            EntityNotFoundError: If no entity matches
            AmbiguousEntityError: If multiple entities match
        """
        files = self.find_entity_files(identifier, entity_type)
        
        if not files:
            raise EntityNotFoundError(f"Entity not found: {identifier}")
        
        if len(files) > 1:
            type_list = [f"{ent_type}: {str(path)}" for path, ent_type in files]
            raise AmbiguousEntityError(
                f"Multiple entities found with identifier '{identifier}': {', '.join(type_list)}. "
                "Please specify the entity type."
            )
        
        file_path, entity_type_str = files[0]
        
        try:
            entity_data = self.load_entity_data(file_path)
        except Exception as e:
            raise DeleteOperationError(f"Error loading entity data: {e}")
        
        return {
            "success": True,
            "identifier": identifier,
            "entity_title": entity_data.get('title', identifier),
            "entity_type": entity_type_str,
            "file_path": str(file_path),
            "entity": entity_data,
        }