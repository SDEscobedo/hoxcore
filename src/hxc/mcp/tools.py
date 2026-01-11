"""
MCP Tools for HoxCore Registry Access.

This module provides tool implementations that allow LLMs to interact with
HoxCore registries through the MCP protocol.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml

from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError
from hxc.core.enums import EntityType, EntityStatus, SortField


def list_entities_tool(
    entity_type: str = "all",
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parent: Optional[str] = None,
    max_items: int = 0,
    sort_by: str = "title",
    descending: bool = False,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    List entities from the HoxCore registry with optional filtering and sorting.
    
    Args:
        entity_type: Type of entities to list (program, project, mission, action, all)
        status: Optional status filter (active, completed, on-hold, cancelled, planned, any)
        tags: Optional list of tags to filter by
        category: Optional category filter
        parent: Optional parent ID filter
        max_items: Maximum number of items to return (0 for all)
        sort_by: Sort field (title, id, due_date, status, created, modified)
        descending: Sort in descending order
        registry_path: Optional registry path (uses default if not provided)
        
    Returns:
        Dictionary containing list of entities and metadata
        
    Raises:
        ValueError: If invalid parameters provided
        PathSecurityError: If path security validation fails
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            raise ValueError("No registry found")
        
        if entity_type == "all":
            types_to_search = list(EntityType)
        else:
            types_to_search = [EntityType.from_string(entity_type)]
        
        status_filter = None if status == "any" or status is None else EntityStatus.from_string(status)
        sort_field = SortField.from_string(sort_by)
        
        all_entities = []
        for entity_type_enum in types_to_search:
            entities = _get_entities_of_type(reg_path, entity_type_enum)
            filtered = _filter_entities(
                entities,
                status=status_filter,
                tags=tags,
                category=category,
                parent=parent
            )
            all_entities.extend(filtered)
        
        all_entities = _sort_entities(all_entities, sort_field, descending)
        
        if max_items > 0:
            all_entities = all_entities[:max_items]
        
        return {
            "success": True,
            "entities": all_entities,
            "count": len(all_entities),
            "filters": {
                "type": entity_type,
                "status": status,
                "tags": tags,
                "category": category,
                "parent": parent
            },
            "sort": {
                "field": sort_by,
                "descending": descending
            }
        }
    
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "entities": [],
            "count": 0
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "entities": [],
            "count": 0
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "entities": [],
            "count": 0
        }


def get_entity_tool(
    identifier: str,
    entity_type: Optional[str] = None,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get detailed information about a specific entity.
    
    Args:
        identifier: ID or UID of the entity
        entity_type: Optional entity type to filter (program, project, mission, action)
        registry_path: Optional registry path (uses default if not provided)
        
    Returns:
        Dictionary containing entity data and metadata
        
    Raises:
        ValueError: If entity not found or invalid parameters
        PathSecurityError: If path security validation fails
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            raise ValueError("No registry found")
        
        entity_type_enum = None
        if entity_type:
            entity_type_enum = EntityType.from_string(entity_type)
        
        file_path = _find_entity_file(reg_path, identifier, entity_type_enum)
        if not file_path:
            raise ValueError(f"Entity not found: {identifier}")
        
        secure_file_path = resolve_safe_path(reg_path, file_path)
        with open(secure_file_path, 'r') as f:
            entity_data = yaml.safe_load(f)
        
        if not entity_data or not isinstance(entity_data, dict):
            raise ValueError(f"Invalid entity data for {identifier}")
        
        return {
            "success": True,
            "entity": entity_data,
            "file_path": str(secure_file_path),
            "identifier": identifier
        }
    
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "entity": None,
            "identifier": identifier
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "entity": None,
            "identifier": identifier
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "entity": None,
            "identifier": identifier
        }


def search_entities_tool(
    query: str,
    entity_type: str = "all",
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    max_items: int = 0,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Search for entities in the HoxCore registry.
    
    Args:
        query: Search query for title and description
        entity_type: Type of entities to search (program, project, mission, action, all)
        status: Optional status filter
        tags: Optional list of tags to filter by
        category: Optional category filter
        max_items: Maximum number of items to return (0 for all)
        registry_path: Optional registry path (uses default if not provided)
        
    Returns:
        Dictionary containing search results and metadata
        
    Raises:
        ValueError: If invalid parameters provided
        PathSecurityError: If path security validation fails
    """
    try:
        list_result = list_entities_tool(
            entity_type=entity_type,
            status=status,
            tags=tags,
            category=category,
            max_items=0,
            registry_path=registry_path
        )
        
        if not list_result.get("success"):
            return list_result
        
        all_entities = list_result.get("entities", [])
        query_lower = query.lower()
        matching_entities = []
        
        for entity in all_entities:
            title = entity.get("title", "").lower()
            description = entity.get("description", "").lower()
            
            if query_lower in title or query_lower in description:
                matching_entities.append(entity)
        
        if max_items > 0:
            matching_entities = matching_entities[:max_items]
        
        return {
            "success": True,
            "entities": matching_entities,
            "count": len(matching_entities),
            "query": query,
            "filters": {
                "type": entity_type,
                "status": status,
                "tags": tags,
                "category": category
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Search error: {e}",
            "entities": [],
            "count": 0,
            "query": query
        }


def get_entity_property_tool(
    identifier: str,
    property_name: str,
    entity_type: Optional[str] = None,
    index: Optional[int] = None,
    key: Optional[str] = None,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a specific property value from an entity.
    
    Args:
        identifier: ID or UID of the entity
        property_name: Name of the property to retrieve
        entity_type: Optional entity type to filter
        index: Optional index for list properties
        key: Optional key:value filter for complex properties
        registry_path: Optional registry path (uses default if not provided)
        
    Returns:
        Dictionary containing property value and metadata
        
    Raises:
        ValueError: If entity or property not found
        PathSecurityError: If path security validation fails
    """
    try:
        entity_result = get_entity_tool(identifier, entity_type, registry_path)
        
        if not entity_result.get("success"):
            return entity_result
        
        entity_data = entity_result.get("entity", {})
        
        if property_name == "all":
            return {
                "success": True,
                "property": property_name,
                "value": entity_data,
                "identifier": identifier
            }
        
        if property_name == "path":
            return {
                "success": True,
                "property": property_name,
                "value": entity_result.get("file_path"),
                "identifier": identifier
            }
        
        value = entity_data.get(property_name)
        
        if value is None:
            return {
                "success": False,
                "error": f"Property '{property_name}' not found or not set",
                "property": property_name,
                "value": None,
                "identifier": identifier
            }
        
        if isinstance(value, list) and index is not None:
            if 0 <= index < len(value):
                value = value[index]
            else:
                return {
                    "success": False,
                    "error": f"Index {index} out of range (list has {len(value)} items)",
                    "property": property_name,
                    "value": None,
                    "identifier": identifier
                }
        
        if isinstance(value, list) and key:
            if ':' not in key:
                return {
                    "success": False,
                    "error": "Invalid key filter format. Use key:value (e.g., name:github)",
                    "property": property_name,
                    "value": None,
                    "identifier": identifier
                }
            
            filter_key, filter_value = key.split(':', 1)
            filtered = [
                item for item in value
                if isinstance(item, dict) and item.get(filter_key) == filter_value
            ]
            
            if not filtered:
                return {
                    "success": False,
                    "error": f"No items found with {filter_key}='{filter_value}'",
                    "property": property_name,
                    "value": None,
                    "identifier": identifier
                }
            
            value = filtered[0] if len(filtered) == 1 else filtered
        
        return {
            "success": True,
            "property": property_name,
            "value": value,
            "identifier": identifier
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving property: {e}",
            "property": property_name,
            "value": None,
            "identifier": identifier
        }


def get_entity_hierarchy_tool(
    identifier: str,
    entity_type: Optional[str] = None,
    include_children: bool = True,
    include_related: bool = True,
    recursive: bool = False,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get entity hierarchy including parent, children, and related entities.
    
    Args:
        identifier: ID or UID of the root entity
        entity_type: Optional entity type to filter
        include_children: Include child entities
        include_related: Include related entities
        recursive: Include hierarchy recursively
        registry_path: Optional registry path
        
    Returns:
        Dictionary containing hierarchy data
    """
    try:
        root_result = get_entity_tool(identifier, entity_type, registry_path)
        
        if not root_result.get("success"):
            return root_result
        
        root_entity = root_result.get("entity", {})
        reg_path = _get_registry_path(registry_path)
        
        hierarchy = {
            "root": root_entity,
            "children": [],
            "related": [],
            "parent": None
        }
        
        parent_id = root_entity.get("parent")
        if parent_id:
            parent_result = get_entity_tool(parent_id, registry_path=registry_path)
            if parent_result.get("success"):
                hierarchy["parent"] = parent_result.get("entity")
        
        if include_children:
            children_ids = root_entity.get("children", [])
            hierarchy["children"] = _get_entities_by_ids(
                reg_path, children_ids, recursive
            )
        
        if include_related:
            related_ids = root_entity.get("related", [])
            hierarchy["related"] = _get_entities_by_ids(
                reg_path, related_ids, False
            )
        
        return {
            "success": True,
            "hierarchy": hierarchy,
            "identifier": identifier,
            "options": {
                "include_children": include_children,
                "include_related": include_related,
                "recursive": recursive
            }
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving hierarchy: {e}",
            "hierarchy": None,
            "identifier": identifier
        }


def get_registry_stats_tool(
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get statistics about the registry.
    
    Args:
        registry_path: Optional registry path
        
    Returns:
        Dictionary containing registry statistics
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            raise ValueError("No registry found")
        
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
            
            for entity in entities:
                status = entity.get("status", "unknown")
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
                
                category = entity.get("category", "uncategorized")
                stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
                
                for tag in entity.get("tags", []):
                    stats["tags"][tag] = stats["tags"].get(tag, 0) + 1
        
        return {
            "success": True,
            "stats": stats,
            "registry_path": reg_path
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving stats: {e}",
            "stats": None
        }


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
    status: Optional[EntityStatus] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parent: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter entities based on criteria"""
    filtered = []
    
    for entity in entities:
        if status is not None:
            entity_status = entity.get("status")
            if entity_status != status.value:
                continue
        
        if tags:
            entity_tags = entity.get("tags", [])
            if not all(tag in entity_tags for tag in tags):
                continue
        
        if category and entity.get("category") != category:
            continue
        
        if parent and entity.get("parent") != parent:
            continue
        
        filtered.append(entity)
    
    return filtered


def _sort_entities(
    entities: List[Dict[str, Any]],
    sort_field: SortField,
    descending: bool
) -> List[Dict[str, Any]]:
    """Sort entities by specified field"""
    if sort_field == SortField.CREATED:
        entities = sorted(
            entities,
            key=lambda x: x.get("_file", {}).get("created", ""),
            reverse=descending
        )
    elif sort_field == SortField.MODIFIED:
        entities = sorted(
            entities,
            key=lambda x: x.get("_file", {}).get("modified", ""),
            reverse=descending
        )
    else:
        entities = sorted(
            entities,
            key=lambda x: x.get(sort_field.value, ""),
            reverse=descending
        )
    
    return entities


def _get_entities_by_ids(
    registry_path: str,
    identifiers: List[str],
    recursive: bool = False
) -> List[Dict[str, Any]]:
    """Get entities by their IDs or UIDs"""
    entities = []
    
    for identifier in identifiers:
        try:
            result = get_entity_tool(identifier, registry_path=registry_path)
            if result.get("success"):
                entity = result.get("entity")
                entities.append(entity)
                
                if recursive:
                    children_ids = entity.get("children", [])
                    if children_ids:
                        children = _get_entities_by_ids(registry_path, children_ids, True)
                        entities.extend(children)
        except Exception:
            continue
    
    return entities