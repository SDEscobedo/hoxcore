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
from hxc.utils.path_security import get_safe_entity_path, resolve_safe_path, PathSecurityError
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


# ─── WRITE TOOLS ────────────────────────────────────────────────────────────
 
def create_entity_tool(
    type: str,
    title: str,
    description: Optional[str] = None,
    status: str = "active",
    id: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    parent: Optional[str] = None,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new entity (program, project, mission, or action) in the registry.
 
    Args:
        type: Entity type — one of program | project | mission | action
        title: Human-readable title for the entity
        description: Optional description
        status: Initial status (default: active)
        id: Optional custom human-readable ID (e.g. P-042)
        category: Optional category path (e.g. software.dev/cli-tool)
        tags: Optional list of tags
        parent: Optional parent entity UID or ID
        start_date: Optional start date in YYYY-MM-DD format (default: today)
        due_date: Optional due date in YYYY-MM-DD format
        registry_path: Optional registry path (uses default if not provided)
 
    Returns:
        Dictionary with uid, id, and file_path on success; error message on failure.
    """
    import uuid
    import datetime
    from hxc.utils.path_security import get_safe_entity_path
 
    try:
        entity_type = EntityType.from_string(type)
        entity_status = EntityStatus.from_string(status)
    except ValueError as e:
        return {"success": False, "error": str(e)}
 
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {"success": False, "error": "No registry found"}
 
        uid = str(uuid.uuid4())[:8]
        today = datetime.date.today().isoformat()
 
        entity_data: Dict[str, Any] = {
            "type": entity_type.value,
            "uid": uid,
            "title": title,
            "status": entity_status.value,
            "start_date": start_date or today,
        }
 
        if id is not None:
            entity_data["id"] = id
        if description is not None:
            entity_data["description"] = description
        if category is not None:
            entity_data["category"] = category
        if tags:
            entity_data["tags"] = tags
        if parent is not None:
            entity_data["parent"] = parent
        if due_date is not None:
            entity_data["due_date"] = due_date
 
        file_prefix = entity_type.get_file_prefix()
        file_name = f"{file_prefix}-{uid}.yml"
 
        try:
            file_path = get_safe_entity_path(reg_path, entity_type.value, file_name)
        except PathSecurityError as e:
            return {"success": False, "error": f"Security error: {e}"}
        except ValueError as e:
            return {"success": False, "error": f"Invalid entity type: {e}"}
 
        file_path.parent.mkdir(parents=True, exist_ok=True)
 
        with open(file_path, "w") as f:
            yaml.dump(entity_data, f, default_flow_style=False, sort_keys=False)
 
        return {
            "success": True,
            "uid": uid,
            "id": entity_data.get("id"),
            "file_path": str(file_path),
            "entity": entity_data,
        }
 
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}
 
 
def edit_entity_tool(
    identifier: str,
    set_title: Optional[str] = None,
    set_description: Optional[str] = None,
    set_status: Optional[str] = None,
    set_id: Optional[str] = None,
    set_category: Optional[str] = None,
    set_parent: Optional[str] = None,
    set_start_date: Optional[str] = None,
    set_due_date: Optional[str] = None,
    set_completion_date: Optional[str] = None,
    add_tags: Optional[List[str]] = None,
    remove_tags: Optional[List[str]] = None,
    add_children: Optional[List[str]] = None,
    remove_children: Optional[List[str]] = None,
    add_related: Optional[List[str]] = None,
    remove_related: Optional[List[str]] = None,
    entity_type: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Edit properties of an existing registry entity.

    Args:
        identifier: UID or human-readable ID of the entity to edit
        set_title: New title value
        set_description: New description value
        set_status: New status value
        set_id: New human-readable ID
        set_category: New category path
        set_parent: New parent UID or ID
        set_start_date: New start date (YYYY-MM-DD)
        set_due_date: New due date (YYYY-MM-DD)
        set_completion_date: New completion date (YYYY-MM-DD)
        add_tags: Tags to add
        remove_tags: Tags to remove
        add_children: Child entity UIDs/IDs to add
        remove_children: Child entity UIDs/IDs to remove
        add_related: Related entity UIDs/IDs to add
        remove_related: Related entity UIDs/IDs to remove
        entity_type: Optional type filter to disambiguate the identifier
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary with updated entity on success; error message on failure.
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {"success": False, "error": "No registry found", "identifier": identifier}
 
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = EntityType.from_string(entity_type)
            except ValueError as e:
                return {"success": False, "error": str(e), "identifier": identifier}
 
        file_path = _find_entity_file(reg_path, identifier, entity_type_enum)
        if not file_path:
            return {
                "success": False,
                "error": f"Entity not found: {identifier}",
                "identifier": identifier,
            }
 
        try:
            secure_file_path = resolve_safe_path(reg_path, file_path)
            with open(secure_file_path, "r") as f:
                entity_data = yaml.safe_load(f)
        except PathSecurityError as e:
            return {"success": False, "error": f"Security error: {e}", "identifier": identifier}
 
        if not entity_data or not isinstance(entity_data, dict):
            return {
                "success": False,
                "error": f"Invalid entity data for {identifier}",
                "identifier": identifier,
            }
 
        # Check ID uniqueness if set_id is provided
        if set_id is not None:
            id_check_error = _check_id_uniqueness(reg_path, entity_data, set_id)
            if id_check_error is not None:
                return {
                    "success": False,
                    "error": id_check_error,
                    "identifier": identifier,
                }
 
        changes: List[str] = []
        # Track whether the caller specified any arguments at all (even no-ops)
        anything_specified = False
 
        # Scalar fields
        scalar_mappings = {
            "title": set_title,
            "description": set_description,
            "status": set_status,
            "id": set_id,
            "category": set_category,
            "parent": set_parent,
            "start_date": set_start_date,
            "due_date": set_due_date,
            "completion_date": set_completion_date,
        }
        for field, value in scalar_mappings.items():
            if value is not None:
                anything_specified = True
                if field == "status":
                    try:
                        value = EntityStatus.from_string(value).value
                    except ValueError as e:
                        return {"success": False, "error": str(e), "identifier": identifier}
                old = entity_data.get(field)
                # Skip if setting the same value (no-op)
                if old == value:
                    continue
                entity_data[field] = value
                changes.append(f"Set {field}: {old!r} → {value!r}")
 
        # Tag operations
        if add_tags:
            anything_specified = True
            tags = entity_data.get("tags") or []
            for tag in add_tags:
                if tag not in tags:
                    tags.append(tag)
                    changes.append(f"Added tag: {tag!r}")
            entity_data["tags"] = tags
 
        if remove_tags:
            anything_specified = True
            tags = entity_data.get("tags") or []
            for tag in remove_tags:
                if tag in tags:
                    tags.remove(tag)
                    changes.append(f"Removed tag: {tag!r}")
            entity_data["tags"] = tags

        # Children operations
        if add_children:
            anything_specified = True
            children = entity_data.get("children") or []
            for child in add_children:
                if child not in children:
                    children.append(child)
                    changes.append(f"Added child: {child!r}")
            entity_data["children"] = children

        if remove_children:
            anything_specified = True
            children = entity_data.get("children") or []
            for child in remove_children:
                if child in children:
                    children.remove(child)
                    changes.append(f"Removed child: {child!r}")
            entity_data["children"] = children

        # Related operations
        if add_related:
            anything_specified = True
            related = entity_data.get("related") or []
            for rel in add_related:
                if rel not in related:
                    related.append(rel)
                    changes.append(f"Added related: {rel!r}")
            entity_data["related"] = related

        if remove_related:
            anything_specified = True
            related = entity_data.get("related") or []
            for rel in remove_related:
                if rel in related:
                    related.remove(rel)
                    changes.append(f"Removed related: {rel!r}")
            entity_data["related"] = related

        if not anything_specified:
            return {
                "success": False,
                "error": "No changes specified",
                "identifier": identifier,
            }
 
        try:
            with open(secure_file_path, "w") as f:
                yaml.dump(entity_data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            return {"success": False, "error": f"Error writing changes: {e}", "identifier": identifier}
 
        return {
            "success": True,
            "identifier": identifier,
            "changes": changes,
            "entity": entity_data,
            "file_path": str(secure_file_path),
        }
 
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}", "identifier": identifier}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "identifier": identifier}
 
 
def delete_entity_tool(
    identifier: str,
    force: bool = False,
    entity_type: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delete an entity from the registry.
 
    When force is False (the default), returns a confirmation prompt and takes no
    action. Call again with force=True to proceed with deletion.
 
    Args:
        identifier: UID or human-readable ID of the entity to delete
        force: If False, returns a confirmation prompt without deleting.
               Set True to confirm deletion.
        entity_type: Optional type filter to disambiguate the identifier
        registry_path: Optional registry path (uses default if not provided)
 
    Returns:
        Dictionary indicating success, or a confirmation_required flag when force is False.
    """
    import os
 
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {"success": False, "error": "No registry found", "identifier": identifier}
 
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = EntityType.from_string(entity_type)
            except ValueError as e:
                return {"success": False, "error": str(e), "identifier": identifier}
 
        file_path = _find_entity_file(reg_path, identifier, entity_type_enum)
        if not file_path:
            return {
                "success": False,
                "error": f"Entity not found: {identifier}",
                "identifier": identifier,
            }
 
        try:
            secure_file_path = resolve_safe_path(reg_path, file_path)
            with open(secure_file_path, "r") as f:
                entity_data = yaml.safe_load(f) or {}
        except PathSecurityError as e:
            return {"success": False, "error": f"Security error: {e}", "identifier": identifier}
 
        entity_title = entity_data.get("title", identifier)
        entity_type_value = entity_data.get("type", "entity")
 
        if not force:
            return {
                "success": False,
                "confirmation_required": True,
                "identifier": identifier,
                "entity_title": entity_title,
                "entity_type": entity_type_value,
                "file_path": str(secure_file_path),
                "message": (
                    f"Confirmation required: about to permanently delete {entity_type_value} "
                    f"'{entity_title}' at {secure_file_path}. "
                    "Call delete_entity_tool again with force=True to proceed."
                ),
            }
 
        try:
            os.remove(str(secure_file_path))
        except Exception as e:
            return {"success": False, "error": f"Error deleting entity: {e}", "identifier": identifier}
 
        return {
            "success": True,
            "identifier": identifier,
            "deleted_title": entity_title,
            "deleted_type": entity_type_value,
            "file_path": str(secure_file_path),
        }
 
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}", "identifier": identifier}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}", "identifier": identifier}


# ─── HELPER FUNCTIONS ──────────────────────────────────────────────────────


def _get_registry_path(specified_path: Optional[str] = None) -> Optional[str]:
    """Get registry path from specified path or config"""
    if specified_path:
        path = Path(specified_path)
        if not path.exists() or not path.is_dir():
            return None
        return specified_path

    registry_path = RegistryCommand.get_registry_path()
    if registry_path:
        return registry_path

    return None


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


def _load_existing_ids(registry_path: str, entity_type: EntityType) -> set:
    """
    Load all `id` fields for existing entities of this type into a set.

    Args:
        registry_path: Path to the registry
        entity_type: The entity type to load IDs for
        
    Returns:
        Set of existing IDs (strings). Missing/invalid ids are ignored.
    """
    ids = set()
    try:
        type_dir = resolve_safe_path(registry_path, entity_type.get_folder_name())
    except PathSecurityError:
        return ids
        
    if not type_dir.exists():
        return ids

    file_prefix = entity_type.get_file_prefix()
    for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
        try:
            secure_file_path = resolve_safe_path(registry_path, file_path)
            with open(secure_file_path, "r") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                existing_id = data.get("id")
                if isinstance(existing_id, str):
                    ids.add(existing_id)
        except PathSecurityError:
            continue
        except Exception:
            continue

    return ids


def _check_id_uniqueness(
    registry_path: str,
    entity_data: Dict[str, Any],
    new_id: str
) -> Optional[str]:
    """
    Check if the new ID is unique within the entity's type.
    
    Args:
        registry_path: Path to the registry
        entity_data: The current entity data
        new_id: The new ID to set
        
    Returns:
        None if the ID is valid/unique, or an error message string if not.
    """
    # Get the entity type from the loaded data
    entity_type_value = entity_data.get('type')
    if not entity_type_value:
        return None  # Can't validate without knowing the type
    
    try:
        actual_entity_type = EntityType.from_string(entity_type_value)
    except ValueError:
        return None  # Invalid entity type in file, skip check
    
    # Get current entity's ID
    current_id = entity_data.get('id')
    
    # If setting to the same ID, it's a no-op - allow it
    if current_id == new_id:
        return None
    
    # Load all existing IDs for this entity type
    existing_ids = _load_existing_ids(registry_path, actual_entity_type)
    
    # Check if new ID already exists
    if new_id in existing_ids:
        return f"{actual_entity_type.value} with id '{new_id}' already exists in this registry"
    
    return None