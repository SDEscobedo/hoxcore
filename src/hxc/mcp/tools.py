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
from hxc.core.operations.create import (
    CreateOperation,
    CreateOperationError,
    DuplicateIdError,
)
from hxc.core.operations.delete import (
    DeleteOperation,
    DeleteOperationError,
    EntityNotFoundError,
    AmbiguousEntityError,
)
from hxc.core.operations.list import (
    ListOperation,
    ListOperationError,
)


def list_entities_tool(
    entity_type: str = "all",
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parent: Optional[str] = None,
    identifier: Optional[str] = None,
    query: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    max_items: int = 0,
    sort_by: str = "title",
    descending: bool = False,
    include_file_metadata: bool = False,
    registry_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    List entities from the HoxCore registry with optional filtering and sorting.
    
    This tool provides comprehensive filtering capabilities identical to the CLI
    `hxc list` command, including text search, date range filters, and ID lookup.
    
    Args:
        entity_type: Type of entities to list (program, project, mission, action, all)
        status: Optional status filter (active, completed, on-hold, cancelled, planned, any)
        tags: Optional list of tags to filter by (AND logic - entity must have ALL tags)
        category: Optional category filter (exact match)
        parent: Optional parent ID filter (exact match)
        identifier: Optional ID or UID filter (exact match)
        query: Optional text search in title and description (case-insensitive)
        due_before: Optional due date filter - show entities due before YYYY-MM-DD (inclusive)
        due_after: Optional due date filter - show entities due after YYYY-MM-DD (inclusive)
        max_items: Maximum number of items to return (0 for all)
        sort_by: Sort field (title, id, due_date, status, created, modified)
        descending: Sort in descending order
        include_file_metadata: Include file metadata (_file field with path, created, modified)
        registry_path: Optional registry path (uses default if not provided)
        
    Returns:
        Dictionary containing:
        - success: bool
        - entities: list of entity dictionaries
        - count: number of entities returned
        - filters: applied filter values
        - sort: sort configuration
        
    Raises:
        ValueError: If invalid parameters provided
        PathSecurityError: If path security validation fails
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {
                "success": False,
                "error": "No registry found",
                "entities": [],
                "count": 0
            }
        
        # Convert entity type
        if entity_type == "all":
            entity_types = list(EntityType)
        else:
            try:
                entity_types = [EntityType.from_string(entity_type)]
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "entities": [],
                    "count": 0
                }
        
        # Convert status filter
        status_filter = None
        if status and status != "any":
            try:
                status_filter = EntityStatus.from_string(status)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "entities": [],
                    "count": 0
                }
        
        # Convert sort field
        try:
            sort_field = SortField.from_string(sort_by)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "entities": [],
                "count": 0
            }
        
        # Use shared ListOperation
        operation = ListOperation(reg_path)
        
        result = operation.list_entities(
            entity_types=entity_types,
            status=status_filter,
            tags=tags,
            category=category,
            parent=parent,
            identifier=identifier,
            query=query,
            due_before=due_before,
            due_after=due_after,
            sort_field=sort_field,
            descending=descending,
            max_items=max_items,
            include_file_metadata=include_file_metadata,
        )
        
        # Clean entities for output if file metadata not requested
        entities = result["entities"]
        if not include_file_metadata:
            entities = ListOperation.clean_entities_for_output(entities, remove_file_metadata=True)
        
        return {
            "success": True,
            "entities": entities,
            "count": len(entities),
            "filters": {
                "type": entity_type,
                "status": status,
                "tags": tags,
                "category": category,
                "parent": parent,
                "identifier": identifier,
                "query": query,
                "due_before": due_before,
                "due_after": due_after,
            },
            "sort": {
                "field": sort_by,
                "descending": descending
            }
        }
    
    except ListOperationError as e:
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
        
        # Use ListOperation to get entity with file metadata
        operation = ListOperation(reg_path)
        entity_data = operation.get_entity_by_identifier(
            identifier=identifier,
            entity_type=entity_type_enum,
            include_file_metadata=True,
        )
        
        if not entity_data:
            raise ValueError(f"Entity not found: {identifier}")
        
        # Extract file path from metadata
        file_path = entity_data.get("_file", {}).get("path", "")
        
        # Clean entity for output
        clean_entity = {k: v for k, v in entity_data.items() if not k.startswith('_')}
        
        return {
            "success": True,
            "entity": clean_entity,
            "file_path": file_path,
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
    
    Note: This tool is provided for backwards compatibility. Consider using
    `list_entities_tool` with the `query` parameter for new implementations,
    which provides additional filtering capabilities.
    
    Args:
        query: Search query for title and description (case-insensitive)
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
    # Delegate to list_entities_tool with query parameter
    result = list_entities_tool(
        entity_type=entity_type,
        status=status,
        tags=tags,
        category=category,
        query=query,
        max_items=max_items,
        registry_path=registry_path
    )
    
    # Transform response to match expected search format
    if result.get("success"):
        return {
            "success": True,
            "entities": result["entities"],
            "count": result["count"],
            "query": query,
            "filters": {
                "type": entity_type,
                "status": status,
                "tags": tags,
                "category": category
            }
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Search error"),
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
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            raise ValueError("No registry found")
        
        entity_type_enum = None
        if entity_type:
            entity_type_enum = EntityType.from_string(entity_type)
        
        # Use ListOperation to get entity with file metadata
        operation = ListOperation(reg_path)
        entity_data = operation.get_entity_by_identifier(
            identifier=identifier,
            entity_type=entity_type_enum,
            include_file_metadata=True,
        )
        
        if not entity_data:
            return {
                "success": False,
                "error": f"Entity not found: {identifier}",
                "property": property_name,
                "value": None,
                "identifier": identifier
            }
        
        if property_name == "all":
            # Return all properties except internal metadata
            clean_entity = {k: v for k, v in entity_data.items() if not k.startswith('_')}
            return {
                "success": True,
                "property": property_name,
                "value": clean_entity,
                "identifier": identifier
            }
        
        if property_name == "path":
            return {
                "success": True,
                "property": property_name,
                "value": entity_data.get("_file", {}).get("path", ""),
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
    
    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "property": property_name,
            "value": None,
            "identifier": identifier
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "property": property_name,
            "value": None,
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
        
        # Use ListOperation to get entities
        operation = ListOperation(reg_path)
        
        stats = {
            "total_entities": 0,
            "by_type": {},
            "by_status": {},
            "by_category": {},
            "tags": {}
        }
        
        for entity_type_enum in EntityType:
            entities = operation.load_entities(entity_type_enum, include_file_metadata=False)
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
    use_git: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new entity (program, project, mission, or action) in the registry.

    This tool performs git-aware creation by default, staging and committing the
    new entity file with a structured commit message. ID uniqueness is validated
    before creation to ensure data integrity.

    Args:
        type: Entity type — one of program | project | mission | action
        title: Human-readable title for the entity
        description: Optional description
        status: Initial status (default: active)
        id: Optional custom human-readable ID (e.g. P-042). Must be unique within entity type.
        category: Optional category path (e.g. software.dev/cli-tool)
        tags: Optional list of tags
        parent: Optional parent entity UID or ID
        start_date: Optional start date in YYYY-MM-DD format (default: today)
        due_date: Optional due date in YYYY-MM-DD format
        use_git: Whether to commit the change to git (default: True)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary with uid, id, file_path, entity, and git_committed on success;
        error message on failure.
    """
    try:
        entity_type = EntityType.from_string(type)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    try:
        entity_status = EntityStatus.from_string(status)
    except ValueError as e:
        return {"success": False, "error": str(e)}

    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        return {"success": False, "error": "No registry found"}

    operation = CreateOperation(reg_path)

    try:
        result = operation.create_entity(
            entity_type=entity_type,
            title=title,
            entity_id=id,
            description=description,
            status=entity_status,
            start_date=start_date,
            due_date=due_date,
            category=category,
            tags=tags,
            parent=parent,
            use_git=use_git,
        )

        return {
            "success": True,
            "uid": result["uid"],
            "id": result["id"],
            "file_path": result["file_path"],
            "entity": result["entity"],
            "git_committed": result.get("git_committed", False),
        }

    except DuplicateIdError as e:
        return {"success": False, "error": str(e)}
    except CreateOperationError as e:
        return {"success": False, "error": str(e)}
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}"}
    except ValueError as e:
        return {"success": False, "error": f"Invalid entity type: {e}"}
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
    use_git: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Delete an entity from the registry.

    This tool performs git-aware deletion by default, using `git rm` and creating
    a structured commit message with entity metadata. When force is False (the
    default), returns a confirmation prompt and takes no action. Call again with
    force=True to proceed with deletion.

    Args:
        identifier: UID or human-readable ID of the entity to delete
        force: If False, returns a confirmation prompt without deleting.
               Set True to confirm deletion.
        entity_type: Optional type filter to disambiguate the identifier
        use_git: Whether to commit the deletion to git (default: True)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary indicating success with deleted_title, deleted_type, file_path,
        and git_committed; or a confirmation_required flag when force is False;
        or an error message on failure.
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

        operation = DeleteOperation(reg_path)

        # Get entity info for confirmation or deletion
        try:
            info = operation.get_entity_info(identifier, entity_type_enum)
        except EntityNotFoundError:
            return {
                "success": False,
                "error": f"Entity not found: {identifier}",
                "identifier": identifier,
            }
        except AmbiguousEntityError as e:
            return {
                "success": False,
                "error": str(e),
                "identifier": identifier,
            }
        except DeleteOperationError as e:
            return {
                "success": False,
                "error": str(e),
                "identifier": identifier,
            }

        entity_title = info["entity_title"]
        entity_type_value = info["entity_type"]
        file_path = info["file_path"]

        if not force:
            return {
                "success": False,
                "confirmation_required": True,
                "identifier": identifier,
                "entity_title": entity_title,
                "entity_type": entity_type_value,
                "file_path": file_path,
                "message": (
                    f"Confirmation required: about to permanently delete {entity_type_value} "
                    f"'{entity_title}' at {file_path}. "
                    "Call delete_entity_tool again with force=True to proceed."
                ),
            }

        # Perform the deletion
        try:
            result = operation.delete_entity(
                identifier=identifier,
                entity_type=entity_type_enum,
                use_git=use_git,
            )
        except EntityNotFoundError as e:
            return {
                "success": False,
                "error": str(e),
                "identifier": identifier,
            }
        except AmbiguousEntityError as e:
            return {
                "success": False,
                "error": str(e),
                "identifier": identifier,
            }
        except DeleteOperationError as e:
            return {
                "success": False,
                "error": f"Error deleting entity: {e}",
                "identifier": identifier,
            }

        return {
            "success": True,
            "identifier": identifier,
            "deleted_title": result["deleted_title"],
            "deleted_type": result["deleted_type"],
            "file_path": result["file_path"],
            "git_committed": result.get("git_committed", False),
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
    operation = ListOperation(registry_path)
    entities = operation.load_entities(entity_type, include_file_metadata=False)
    
    ids = set()
    for entity in entities:
        existing_id = entity.get("id")
        if isinstance(existing_id, str):
            ids.add(existing_id)
    
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