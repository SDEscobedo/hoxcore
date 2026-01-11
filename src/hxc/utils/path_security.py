# src/hxc/utils/path_security.py
"""
Path security utilities for HoxCore registry operations.
Ensures all file operations stay within the registry boundaries.
"""
import os
from pathlib import Path
from typing import Union


class PathSecurityError(Exception):
    """Raised when a path operation attempts to escape the registry"""
    pass


def resolve_safe_path(registry_root: Union[str, Path], target_path: Union[str, Path]) -> Path:
    """
    Resolve a path safely within the registry root.
    
    Args:
        registry_root: Root directory of the registry
        target_path: Path to resolve (can be relative or absolute)
        
    Returns:
        Resolved absolute path within the registry
        
    Raises:
        PathSecurityError: If the resolved path is outside the registry root
    """
    # Convert to Path objects and resolve to absolute paths
    registry_root = Path(registry_root).resolve()
    
    # If target_path is absolute, check if it's within registry
    # If relative, join with registry_root
    if Path(target_path).is_absolute():
        resolved_path = Path(target_path).resolve()
    else:
        resolved_path = (registry_root / target_path).resolve()
    
    # Check if the resolved path is within the registry root
    try:
        resolved_path.relative_to(registry_root)
    except ValueError:
        raise PathSecurityError(
            f"Path '{target_path}' resolves to '{resolved_path}' which is outside "
            f"the registry root '{registry_root}'"
        )
    
    return resolved_path


def validate_registry_path(registry_root: Union[str, Path], target_path: Union[str, Path]) -> bool:
    """
    Validate that a path is within the registry root without raising an exception.
    
    Args:
        registry_root: Root directory of the registry
        target_path: Path to validate
        
    Returns:
        True if path is within registry, False otherwise
    """
    try:
        resolve_safe_path(registry_root, target_path)
        return True
    except PathSecurityError:
        return False


def get_safe_entity_path(
    registry_root: Union[str, Path],
    entity_type: str,
    filename: str
) -> Path:
    """
    Get a safe path for an entity file within the registry.
    
    Args:
        registry_root: Root directory of the registry
        entity_type: Type of entity (program, project, mission, action)
        filename: Name of the entity file
        
    Returns:
        Safe resolved path for the entity file
        
    Raises:
        PathSecurityError: If the path would be outside the registry
        ValueError: If entity_type is invalid
    """
    valid_types = ["program", "project", "mission", "action"]
    if entity_type not in valid_types:
        raise ValueError(f"Invalid entity type '{entity_type}'. Must be one of: {valid_types}")
    
    # Map entity type to folder name
    folder_map = {
        "program": "programs",
        "project": "projects",
        "mission": "missions",
        "action": "actions"
    }
    
    folder_name = folder_map[entity_type]
    relative_path = Path(folder_name) / filename
    
    return resolve_safe_path(registry_root, relative_path)


def ensure_within_registry(registry_root: Union[str, Path], *paths: Union[str, Path]) -> None:
    """
    Ensure all provided paths are within the registry root.
    
    Args:
        registry_root: Root directory of the registry
        *paths: Variable number of paths to check
        
    Raises:
        PathSecurityError: If any path is outside the registry root
    """
    for path in paths:
        resolve_safe_path(registry_root, path)