"""
MCP Resources for HoxCore Registry Access.

This module provides resource definitions that expose HoxCore registry entities
as accessible resources through the MCP protocol.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError
from hxc.core.enums import EntityType


def get_entity_resource(
    identifier: str,
    entity_type: Optional[str] = None,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a specific entity as an MCP resource.
    
    Args:
        identifier: ID or UID of the entity
        entity_type: Optional entity type to filter
        registry_path: Optional registry path (uses default if not provided)
        
    Returns:
        MCP resource definition with entity data
        
    Raises:
        ValueError: If entity not found or invalid parameters
        PathSecurityError: If path security validation fails
    """
    # Get registry path
    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")
    
    # Convert entity type if provided
    entity_type_enum = None
    if entity_type:
        try:
            entity_type_enum = EntityType.from_string(entity_type)
        except ValueError as e:
            raise ValueError(f"Invalid entity type: {e}")
    
    # Find the entity file
    file_path = _find_entity_file(reg_path, identifier, entity_type_enum)
    if not file_path:
        raise ValueError(f"Entity not found: {identifier}")
    
    # Load entity data
    try:
        secure_file_path = resolve_safe_path(reg_path, file_path)
        with open(secure_file_path, 'r') as f:
            entity_data = yaml.safe_load(f)
    except PathSecurityError as e:
        raise PathSecurityError(f"Security error accessing entity: {e}")
    except Exception as e:
        raise ValueError(f"Error loading entity: {e}")
    
    if not entity_data or not isinstance(entity_data, dict):
        raise ValueError(f"Invalid entity data for {identifier}")
    
    # Build resource definition
    resource = {
        "uri": f"hxc://entity/{entity_data.get('uid', identifier)}",
        "name": entity_data.get('title', identifier),
        "description": entity_data.get('description', ''),
        "mimeType": "application/x-yaml",
        "metadata": {
            "type": entity_data.get('type'),
            "id": entity_data.get('id'),
            "uid": entity_data.get('uid'),
            "status": entity_data.get('status'),
            "category": entity_data.get('category'),
            "tags": entity_data.get('tags', []),
            "file_path": str(secure_file_path)
        },
        "content": entity_data
    }
    
    return resource


def list_entities_resource(
    entity_type: str = "all",
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parent: Optional[str] = None,
    max_items: int = 0,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    List entities as an MCP resource collection.
    
    Args:
        entity_type: Type of entities to list (program, project, mission, action, all)
        status: Optional status filter
        tags: Optional list of tags to filter by
        category: Optional category filter
        parent: Optional parent ID filter
        max_items: Maximum number of items to return (0 for all)
        registry_path: Optional registry path (uses default if not provided)
        
    Returns:
        MCP resource definition with list of entities
        
    Raises:
        ValueError: If invalid parameters
        PathSecurityError: If path security validation fails
    """
    # Get registry path
    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")
    
    # Determine entity types to search
    if entity_type == "all":
        types_to_search = list(EntityType)
    else:
        try:
            types_to_search = [EntityType.from_string(entity_type)]
        except ValueError as e:
            raise ValueError(f"Invalid entity type: {e}")
    
    # Collect entities
    all_entities = []
    for entity_type_enum in types_to_search:
        entities = _get_entities_of_type(reg_path, entity_type_enum)
        filtered = _filter_entities(
            entities,
            status=status,
            tags=tags,
            category=category,
            parent=parent
        )
        all_entities.extend(filtered)
    
    # Sort by title
    all_entities.sort(key=lambda x: x.get('title', ''))
    
    # Apply max limit
    if max_items > 0:
        all_entities = all_entities[:max_items]
    
    # Build resource collection
    resource = {
        "uri": f"hxc://entities/{entity_type}",
        "name": f"HoxCore {entity_type.title()} Entities",
        "description": f"Collection of {entity_type} entities from the registry",
        "mimeType": "application/json",
        "metadata": {
            "count": len(all_entities),
            "type": entity_type,
            "filters": {
                "status": status,
                "tags": tags,
                "category": category,
                "parent": parent
            }
        },
        "content": {
            "entities": all_entities,
            "total": len(all_entities)
        }
    }
    
    return resource


def get_entity_hierarchy_resource(
    identifier: str,
    entity_type: Optional[str] = None,
    include_children: bool = True,
    include_related: bool = True,
    recursive: bool = False,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get entity hierarchy as an MCP resource.
    
    Args:
        identifier: ID or UID of the root entity
        entity_type: Optional entity type to filter
        include_children: Include child entities
        include_related: Include related entities
        recursive: Include hierarchy recursively
        registry_path: Optional registry path
        
    Returns:
        MCP resource definition with hierarchy data
        
    Raises:
        ValueError: If entity not found or invalid parameters
        PathSecurityError: If path security validation fails
    """
    # Get the root entity
    root_entity = get_entity_resource(identifier, entity_type, registry_path)
    
    # Get registry path
    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")
    
    # Build hierarchy
    hierarchy = {
        "root": root_entity['content'],
        "children": [],
        "related": []
    }
    
    if include_children:
        children_ids = root_entity['content'].get('children', [])
        hierarchy['children'] = _get_entities_by_ids(
            reg_path, children_ids, recursive
        )
    
    if include_related:
        related_ids = root_entity['content'].get('related', [])
        hierarchy['related'] = _get_entities_by_ids(
            reg_path, related_ids, False
        )
    
    # Build resource
    resource = {
        "uri": f"hxc://hierarchy/{root_entity['content'].get('uid', identifier)}",
        "name": f"Hierarchy: {root_entity['name']}",
        "description": f"Hierarchical view of {root_entity['name']} and related entities",
        "mimeType": "application/json",
        "metadata": {
            "root_id": root_entity['content'].get('uid'),
            "include_children": include_children,
            "include_related": include_related,
            "recursive": recursive
        },
        "content": hierarchy
    }
    
    return resource


def get_registry_stats_resource(
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get registry statistics as an MCP resource.
    
    Args:
        registry_path: Optional registry path
        
    Returns:
        MCP resource definition with registry statistics
        
    Raises:
        ValueError: If registry not found
        PathSecurityError: If path security validation fails
    """
    # Get registry path
    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")
    
    # Collect statistics
    stats = {
        "total_entities": 0,
        "by_type": {},
        "by_status": {},
        "by_category": {},
        "tags": {}
    }
    
    for entity_type_enum in EntityType:
        entities = _get_entities_of_type(reg_path, entity_type_enum)
        type_name = entity_type_enum.value
        stats["by_type"][type_name] = len(entities)
        stats["total_entities"] += len(entities)
        
        # Count by status
        for entity in entities:
            status = entity.get('status', 'unknown')
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Count by category
            category = entity.get('category', 'uncategorized')
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            
            # Count tags
            for tag in entity.get('tags', []):
                stats["tags"][tag] = stats["tags"].get(tag, 0) + 1
    
    # Build resource
    resource = {
        "uri": "hxc://registry/stats",
        "name": "Registry Statistics",
        "description": "Statistical overview of the HoxCore registry",
        "mimeType": "application/json",
        "metadata": {
            "registry_path": reg_path
        },
        "content": stats
    }
    
    return resource


def search_entities_resource(
    query: str,
    entity_type: str = "all",
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    max_items: int = 0,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search entities and return as an MCP resource.
    
    Args:
        query: Search query for title and description
        entity_type: Type of entities to search
        status: Optional status filter
        tags: Optional list of tags to filter by
        category: Optional category filter
        max_items: Maximum number of items to return (0 for all)
        registry_path: Optional registry path
        
    Returns:
        MCP resource definition with search results
        
    Raises:
        ValueError: If invalid parameters
        PathSecurityError: If path security validation fails
    """
    # Get all entities matching filters
    entities_resource = list_entities_resource(
        entity_type=entity_type,
        status=status,
        tags=tags,
        category=category,
        max_items=0,
        registry_path=registry_path
    )
    
    all_entities = entities_resource['content']['entities']
    
    # Filter by query
    query_lower = query.lower()
    matching_entities = []
    
    for entity in all_entities:
        title = entity.get('title', '').lower()
        description = entity.get('description', '').lower()
        
        if query_lower in title or query_lower in description:
            matching_entities.append(entity)
    
    # Apply max limit
    if max_items > 0:
        matching_entities = matching_entities[:max_items]
    
    # Build resource
    resource = {
        "uri": f"hxc://search?q={query}",
        "name": f"Search Results: {query}",
        "description": f"Entities matching search query: {query}",
        "mimeType": "application/json",
        "metadata": {
            "query": query,
            "count": len(matching_entities),
            "type": entity_type,
            "filters": {
                "status": status,
                "tags": tags,
                "category": category
            }
        },
        "content": {
            "query": query,
            "entities": matching_entities,
            "total": len(matching_entities)
        }
    }
    
    return resource


def _get_registry_path(specified_path: Optional[str] = None) -> Optional[str]:
    """Get registry path from specified path, config, or current directory"""
    if specified_path:
        return specified_path
    
    registry_path = RegistryCommand.get_registry_path()
    if registry_path:
        return registry_path
    
    return get_project_root()


def _find_entity_file(
    registry_path: str,
    identifier: str,
    entity_type: Optional[EntityType] = None
) -> Optional[Path]:
    """Find an entity file by ID or UID"""
    types_to_search = [entity_type] if entity_type else list(EntityType)
    
    for entity_type_enum in types_to_search:
        folder_name = entity_type_enum.get_folder_name()
        file_prefix = entity_type_enum.get_file_prefix()
        
        try:
            type_dir = resolve_safe_path(registry_path, folder_name)
        except PathSecurityError:
            continue
        
        if not type_dir.exists():
            continue
        
        uid_pattern = f"{file_prefix}-{identifier}.yml"
        for file_path in type_dir.glob(uid_pattern):
            try:
                secure_file_path = resolve_safe_path(registry_path, file_path)
                return secure_file_path
            except PathSecurityError:
                continue
        
        for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
            try:
                secure_file_path = resolve_safe_path(registry_path, file_path)
                with open(secure_file_path, 'r') as f:
                    data = yaml.safe_load(f)
                    if data and isinstance(data, dict):
                        if data.get('id') == identifier or data.get('uid') == identifier:
                            return secure_file_path
            except (PathSecurityError, Exception):
                continue
    
    return None


def _get_entities_of_type(
    registry_path: str,
    entity_type: EntityType
) -> List[Dict[str, Any]]:
    """Get all entities of a specific type"""
    entities = []
    
    folder_name = entity_type.get_folder_name()
    file_prefix = entity_type.get_file_prefix() + "-"
    
    try:
        type_dir = resolve_safe_path(registry_path, folder_name)
    except PathSecurityError:
        return []
    
    if not type_dir.exists():
        return []
    
    for file_path in type_dir.glob(f"{file_prefix}*.yml"):
        try:
            secure_file_path = resolve_safe_path(registry_path, file_path)
            with open(secure_file_path, 'r') as f:
                entity_data = yaml.safe_load(f)
                if entity_data and isinstance(entity_data, dict):
                    entities.append(entity_data)
        except (PathSecurityError, Exception):
            continue
    
    return entities


def _filter_entities(
    entities: List[Dict[str, Any]],
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parent: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter entities based on criteria"""
    filtered = []
    
    for entity in entities:
        if status and entity.get('status') != status:
            continue
        
        if tags:
            entity_tags = entity.get('tags', [])
            if not all(tag in entity_tags for tag in tags):
                continue
        
        if category and entity.get('category') != category:
            continue
        
        if parent and entity.get('parent') != parent:
            continue
        
        filtered.append(entity)
    
    return filtered


def _get_entities_by_ids(
    registry_path: str,
    identifiers: List[str],
    recursive: bool = False
) -> List[Dict[str, Any]]:
    """Get entities by their IDs or UIDs"""
    entities = []
    
    for identifier in identifiers:
        try:
            resource = get_entity_resource(identifier, registry_path=registry_path)
            entity = resource['content']
            entities.append(entity)
            
            if recursive:
                children_ids = entity.get('children', [])
                if children_ids:
                    children = _get_entities_by_ids(registry_path, children_ids, True)
                    entities.extend(children)
        except (ValueError, PathSecurityError):
            continue
    
    return entities