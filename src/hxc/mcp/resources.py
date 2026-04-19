"""
MCP Resources for HoxCore Registry Access.

This module provides resource definitions that expose HoxCore registry entities
as accessible resources through the MCP protocol. It delegates core listing and
filtering logic to the shared ListOperation class to ensure behavioral parity
with CLI commands.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityStatus, EntityType, SortField
from hxc.core.operations.list import ListOperation
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError, resolve_safe_path


def get_entity_resource(
    identifier: str,
    entity_type: Optional[str] = None,
    registry_path: Optional[str] = None,
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
    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")

    entity_type_enum = None
    if entity_type:
        try:
            entity_type_enum = EntityType.from_string(entity_type)
        except ValueError as e:
            raise ValueError(f"Invalid entity type: {e}")

    operation = ListOperation(reg_path)
    entity_data = operation.get_entity_by_identifier(
        identifier=identifier,
        entity_type=entity_type_enum,
        include_file_metadata=True,
    )

    if not entity_data:
        raise ValueError(f"Entity not found: {identifier}")

    file_path = entity_data.get("_file", {}).get("path", "")

    clean_entity = {k: v for k, v in entity_data.items() if not k.startswith("_")}

    resource = {
        "uri": f"hxc://entity/{clean_entity.get('uid', identifier)}",
        "name": clean_entity.get("title", identifier),
        "description": clean_entity.get("description", ""),
        "mimeType": "application/x-yaml",
        "metadata": {
            "type": clean_entity.get("type"),
            "id": clean_entity.get("id"),
            "uid": clean_entity.get("uid"),
            "status": clean_entity.get("status"),
            "category": clean_entity.get("category"),
            "tags": clean_entity.get("tags", []),
            "file_path": file_path,
        },
        "content": clean_entity,
    }

    return resource


def list_entities_resource(
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
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List entities as an MCP resource collection.

    This function provides full filtering capabilities identical to the CLI
    `hxc list` command, including text search and date range filters.

    Args:
        entity_type: Type of entities to list (program, project, mission, action, all)
        status: Optional status filter (active, completed, on-hold, cancelled, planned)
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
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        MCP resource definition with list of entities

    Raises:
        ValueError: If invalid parameters
        PathSecurityError: If path security validation fails
    """
    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")

    if entity_type == "all":
        entity_types = list(EntityType)
    else:
        try:
            entity_types = [EntityType.from_string(entity_type)]
        except ValueError as e:
            raise ValueError(f"Invalid entity type: {e}")

    status_filter = None
    if status:
        try:
            status_filter = EntityStatus.from_string(status)
        except ValueError as e:
            raise ValueError(f"Invalid status: {e}")

    try:
        sort_field = SortField.from_string(sort_by)
    except ValueError as e:
        raise ValueError(f"Invalid sort field: {e}")

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
        include_file_metadata=False,
    )

    entities = result["entities"]

    resource = {
        "uri": f"hxc://entities/{entity_type}",
        "name": f"HoxCore {entity_type.title()} Entities",
        "description": f"Collection of {entity_type} entities from the registry",
        "mimeType": "application/json",
        "metadata": {
            "count": len(entities),
            "type": entity_type,
            "filters": {
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
                "descending": descending,
            },
        },
        "content": {"entities": entities, "total": len(entities)},
    }

    return resource


def get_entity_hierarchy_resource(
    identifier: str,
    entity_type: Optional[str] = None,
    include_children: bool = True,
    include_related: bool = True,
    recursive: bool = False,
    registry_path: Optional[str] = None,
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
    root_entity = get_entity_resource(identifier, entity_type, registry_path)

    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")

    hierarchy = {
        "root": root_entity["content"],
        "children": [],
        "related": [],
        "parent": None,
    }

    parent_id = root_entity["content"].get("parent")
    if parent_id:
        try:
            parent_resource = get_entity_resource(
                parent_id, registry_path=registry_path
            )
            hierarchy["parent"] = parent_resource["content"]
        except (ValueError, PathSecurityError):
            pass

    if include_children:
        children_ids = root_entity["content"].get("children", [])
        hierarchy["children"] = _get_entities_by_ids(reg_path, children_ids, recursive)

    if include_related:
        related_ids = root_entity["content"].get("related", [])
        hierarchy["related"] = _get_entities_by_ids(reg_path, related_ids, False)

    resource = {
        "uri": f"hxc://hierarchy/{root_entity['content'].get('uid', identifier)}",
        "name": f"Hierarchy: {root_entity['name']}",
        "description": f"Hierarchical view of {root_entity['name']} and related entities",
        "mimeType": "application/json",
        "metadata": {
            "root_id": root_entity["content"].get("uid"),
            "include_children": include_children,
            "include_related": include_related,
            "recursive": recursive,
        },
        "content": hierarchy,
    }

    return resource


def get_registry_stats_resource(registry_path: Optional[str] = None) -> Dict[str, Any]:
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
    reg_path = _get_registry_path(registry_path)
    if not reg_path:
        raise ValueError("No registry found")

    operation = ListOperation(reg_path)

    stats = {
        "total_entities": 0,
        "by_type": {},
        "by_status": {},
        "by_category": {},
        "tags": {},
    }

    for entity_type_enum in EntityType:
        entities = operation.load_entities(
            entity_type_enum, include_file_metadata=False
        )
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

    resource = {
        "uri": "hxc://registry/stats",
        "name": "Registry Statistics",
        "description": "Statistical overview of the HoxCore registry",
        "mimeType": "application/json",
        "metadata": {"registry_path": reg_path},
        "content": stats,
    }

    return resource


def search_entities_resource(
    query: str,
    entity_type: str = "all",
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    max_items: int = 0,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Search entities and return as an MCP resource.

    Note: This function is provided for backwards compatibility. Consider using
    `list_entities_resource` with the `query` parameter for new implementations,
    which provides additional filtering capabilities.

    Args:
        query: Search query for title and description (case-insensitive)
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
    entities_resource = list_entities_resource(
        entity_type=entity_type,
        status=status,
        tags=tags,
        category=category,
        query=query,
        max_items=max_items,
        registry_path=registry_path,
    )

    matching_entities = entities_resource["content"]["entities"]

    resource = {
        "uri": f"hxc://search?q={query}",
        "name": f"Search Results: {query}",
        "description": f"Entities matching search query: {query}",
        "mimeType": "application/json",
        "metadata": {
            "query": query,
            "count": len(matching_entities),
            "type": entity_type,
            "filters": {"status": status, "tags": tags, "category": category},
        },
        "content": {
            "query": query,
            "entities": matching_entities,
            "total": len(matching_entities),
        },
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


def _get_entities_by_ids(
    registry_path: str, identifiers: List[str], recursive: bool = False
) -> List[Dict[str, Any]]:
    """Get entities by their IDs or UIDs"""
    entities = []
    operation = ListOperation(registry_path)

    for identifier in identifiers:
        try:
            entity_data = operation.get_entity_by_identifier(
                identifier=identifier,
                include_file_metadata=False,
            )

            if entity_data:
                entities.append(entity_data)

                if recursive:
                    children_ids = entity_data.get("children", [])
                    if children_ids:
                        children = _get_entities_by_ids(
                            registry_path, children_ids, True
                        )
                        entities.extend(children)
        except (ValueError, PathSecurityError):
            continue

    return entities
