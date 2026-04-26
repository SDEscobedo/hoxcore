"""
MCP Tools for HoxCore Registry Access.

This module provides tool implementations that allow LLMs to interact with
HoxCore registries through the MCP protocol.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from hxc.commands.registry import RegistryCommand
from hxc.core.config import Config
from hxc.core.enums import EntityStatus, EntityType, SortField
from hxc.core.operations.create import (
    CreateOperation,
    CreateOperationError,
    DuplicateIdError,
)
from hxc.core.operations.delete import (
    AmbiguousEntityError,
    DeleteOperation,
    DeleteOperationError,
    EntityNotFoundError,
)
from hxc.core.operations.edit import DuplicateIdError as EditDuplicateIdError
from hxc.core.operations.edit import (
    EditOperation,
    EditOperationError,
)
from hxc.core.operations.edit import EntityNotFoundError as EditEntityNotFoundError
from hxc.core.operations.edit import (
    InvalidValueError,
    NoChangesError,
)
from hxc.core.operations.get import (
    GetPropertyOperation,
    GetPropertyOperationError,
)
from hxc.core.operations.init import (
    DirectoryNotEmptyError,
    GitOperationError,
    InitOperation,
    InitOperationError,
)
from hxc.core.operations.list import (
    ListOperation,
    ListOperationError,
)
from hxc.core.operations.registry import (
    InvalidRegistryPathError,
    RegistryOperation,
    RegistryOperationError,
)
from hxc.core.operations.scaffold import (
    PromptRequiredError,
    ScaffoldExecutionError,
    ScaffoldOperation,
    ScaffoldOperationError,
    ScaffoldSecurityError,
    TemplateNotFoundOperationError,
    TemplateValidationError,
)
from hxc.core.operations.show import (
    InvalidEntityError,
    ShowOperation,
    ShowOperationError,
)
from hxc.core.operations.validate import (
    ValidateOperation,
    ValidateOperationError,
)
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import (
    PathSecurityError,
    get_safe_entity_path,
    resolve_safe_path,
)


def init_registry_tool(
    path: str,
    use_git: bool = True,
    commit: bool = True,
    remote_url: Optional[str] = None,
    set_default: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initialize a new HoxCore registry at the specified path.

    This tool creates a complete registry structure including:
    - Entity folders (programs, projects, missions, actions)
    - Configuration file (config.yml)
    - Registry marker directory (.hxc)
    - Index database (index.db)
    - Gitignore file (.gitignore)
    - Optional git repository initialization

    The tool performs git-aware initialization by default, creating an initial
    commit with all registry files. Path security is enforced to prevent
    directory traversal attacks.

    Args:
        path: Path where to initialize the registry. Must be an empty directory
              or a path that doesn't exist yet.
        use_git: Whether to initialize a git repository (default: True)
        commit: Whether to create initial commit (default: True, requires use_git)
        remote_url: Optional git remote URL to configure as 'origin'
        set_default: Whether to set this registry as the default in config (default: True)
        registry_path: Ignored for init_registry_tool (included for API consistency)

    Returns:
        Dictionary containing:
        - success: bool
        - registry_path: str (absolute path on success)
        - git_initialized: bool
        - committed: bool
        - pushed: bool (if remote_url was provided)
        - remote_added: bool (if remote_url was provided)
        - set_as_default: bool

    Raises:
        DirectoryNotEmptyError: If the directory is not empty
        PathSecurityError: If path validation fails
        InitOperationError: If initialization fails
    """
    try:
        # Validate path
        if not path:
            return {
                "success": False,
                "error": "Path is required",
                "path": path,
            }

        # Create and execute the init operation
        operation = InitOperation(path)

        result = operation.initialize_registry(
            use_git=use_git,
            commit=commit,
            remote_url=remote_url,
            force_empty_check=True,
        )

        registry_path_str = result["registry_path"]

        # Set as default registry if requested
        set_as_default = False
        if set_default and registry_path_str:
            try:
                config = Config()
                config.set("registry_path", registry_path_str)
                set_as_default = True
            except Exception:
                # Config setting failure is not critical
                pass

        return {
            "success": True,
            "registry_path": registry_path_str,
            "git_initialized": result.get("git_initialized", False),
            "committed": result.get("committed", False),
            "pushed": result.get("pushed", False),
            "remote_added": result.get("remote_added", False),
            "set_as_default": set_as_default,
        }

    except DirectoryNotEmptyError as e:
        return {
            "success": False,
            "error": str(e),
            "path": path,
        }
    except GitOperationError as e:
        return {
            "success": False,
            "error": f"Git operation failed: {e}",
            "path": path,
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "path": path,
        }
    except InitOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "path": path,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "path": path,
        }


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
    registry_path: Optional[str] = None,
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
                "count": 0,
            }

        # Convert entity type
        if entity_type == "all":
            entity_types = list(EntityType)
        else:
            try:
                entity_types = [EntityType.from_string(entity_type)]
            except ValueError as e:
                return {"success": False, "error": str(e), "entities": [], "count": 0}

        # Convert status filter
        status_filter = None
        if status and status != "any":
            try:
                status_filter = EntityStatus.from_string(status)
            except ValueError as e:
                return {"success": False, "error": str(e), "entities": [], "count": 0}

        # Convert sort field
        try:
            sort_field = SortField.from_string(sort_by)
        except ValueError as e:
            return {"success": False, "error": str(e), "entities": [], "count": 0}

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
            entities = ListOperation.clean_entities_for_output(
                entities, remove_file_metadata=True
            )

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
            "sort": {"field": sort_by, "descending": descending},
        }

    except ListOperationError as e:
        return {"success": False, "error": str(e), "entities": [], "count": 0}
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "entities": [],
            "count": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "entities": [],
            "count": 0,
        }


def get_entity_tool(
    identifier: str,
    entity_type: Optional[str] = None,
    include_raw: bool = False,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a specific entity.

    This tool uses a two-phase search strategy for entity lookup:
    1. Fast path: Try to match identifier in filename pattern ({prefix}-{identifier}.yml)
    2. Slow path: Search file contents for ID or UID match

    The fast path optimizes for UID lookups since entity files are named
    using the UID (e.g., proj-12345678.yml).

    Args:
        identifier: ID or UID of the entity
        entity_type: Optional entity type to filter (program, project, mission, action)
        include_raw: Whether to include raw YAML file content in response (default: False)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - entity: dict (entity data) or None
        - file_path: str (path to entity file) or None
        - identifier: str (the search identifier)
        - raw_content: str (only if include_raw=True and entity found)
        - error: str (only if success=False)

    Raises:
        ValueError: If entity not found or invalid parameters
        PathSecurityError: If path security validation fails
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {
                "success": False,
                "error": "No registry found",
                "entity": None,
                "file_path": None,
                "identifier": identifier,
            }

        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = EntityType.from_string(entity_type)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "entity": None,
                    "file_path": None,
                    "identifier": identifier,
                }

        # Use shared ShowOperation for entity retrieval
        operation = ShowOperation(reg_path)
        result = operation.get_entity(
            identifier=identifier,
            entity_type=entity_type_enum,
            include_raw=include_raw,
        )

        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", f"Entity not found: {identifier}"),
                "entity": None,
                "file_path": None,
                "identifier": identifier,
            }

        response: Dict[str, Any] = {
            "success": True,
            "entity": result["entity"],
            "file_path": result["file_path"],
            "identifier": identifier,
        }

        if include_raw and "raw_content" in result:
            response["raw_content"] = result["raw_content"]

        return response

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "entity": None,
            "file_path": None,
            "identifier": identifier,
        }
    except InvalidEntityError as e:
        return {
            "success": False,
            "error": str(e),
            "entity": None,
            "file_path": None,
            "identifier": identifier,
        }
    except ShowOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "entity": None,
            "file_path": None,
            "identifier": identifier,
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "entity": None,
            "file_path": None,
            "identifier": identifier,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "entity": None,
            "file_path": None,
            "identifier": identifier,
        }


def search_entities_tool(
    query: str,
    entity_type: str = "all",
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    max_items: int = 0,
    registry_path: Optional[str] = None,
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
        registry_path=registry_path,
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
                "category": category,
            },
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Search error"),
            "entities": [],
            "count": 0,
            "query": query,
        }


def get_entity_property_tool(
    identifier: str,
    property_name: str,
    entity_type: Optional[str] = None,
    index: Optional[int] = None,
    key: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a specific property value from an entity.

    This tool uses the shared GetPropertyOperation to ensure behavioral
    consistency with the CLI `hxc get` command. Property names are validated
    against a canonical set before retrieval.

    Property Categories:
    - SCALAR: type, uid, id, title, description, status, start_date, due_date,
              completion_date, duration_estimate, category, parent, template
    - LIST: tags, children, related
    - COMPLEX: repositories, storage, databases, tools, models, knowledge_bases
    - SPECIAL: all (returns all properties), path (returns file path)

    Args:
        identifier: ID or UID of the entity
        property_name: Name of the property to retrieve (case-insensitive)
        entity_type: Optional entity type to filter (program, project, mission, action)
        index: Optional index for list/complex properties (0-based)
        key: Optional key:value filter for complex properties (e.g., "name:github")
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - property: str (normalized property name)
        - property_type: str (scalar, list, complex, special) - only on success
        - value: Any (property value) - only on success
        - identifier: str
        - error: str (only if success=False)
        - available_properties: list (only if unknown property error)

    Raises:
        ValueError: If entity or property not found
        PathSecurityError: If path security validation fails
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {
                "success": False,
                "error": "No registry found",
                "property": property_name,
                "value": None,
                "identifier": identifier,
            }

        # Convert entity type if provided
        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = EntityType.from_string(entity_type)
            except ValueError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "property": property_name,
                    "value": None,
                    "identifier": identifier,
                }

        # Use shared GetPropertyOperation for consistent behavior with CLI
        operation = GetPropertyOperation(reg_path)

        result = operation.get_property(
            identifier=identifier,
            property_name=property_name,
            entity_type=entity_type_enum,
            index=index,
            key_filter=key,
        )

        # Return the result from the operation
        # The operation already provides all the required fields
        return result

    except GetPropertyOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "property": property_name,
            "value": None,
            "identifier": identifier,
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "property": property_name,
            "value": None,
            "identifier": identifier,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving property: {e}",
            "property": property_name,
            "value": None,
            "identifier": identifier,
        }


def get_entity_hierarchy_tool(
    identifier: str,
    entity_type: Optional[str] = None,
    include_children: bool = True,
    include_related: bool = True,
    recursive: bool = False,
    registry_path: Optional[str] = None,
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
        root_result = get_entity_tool(
            identifier, entity_type, registry_path=registry_path
        )

        if not root_result.get("success"):
            return root_result

        root_entity = root_result.get("entity", {})
        reg_path = _get_registry_path(registry_path)

        hierarchy = {"root": root_entity, "children": [], "related": [], "parent": None}

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
            hierarchy["related"] = _get_entities_by_ids(reg_path, related_ids, False)

        return {
            "success": True,
            "hierarchy": hierarchy,
            "identifier": identifier,
            "options": {
                "include_children": include_children,
                "include_related": include_related,
                "recursive": recursive,
            },
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving hierarchy: {e}",
            "hierarchy": None,
            "identifier": identifier,
        }


def get_registry_stats_tool(registry_path: Optional[str] = None) -> Dict[str, Any]:
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
                stats["by_category"][category] = (
                    stats["by_category"].get(category, 0) + 1
                )

                for tag in entity.get("tags", []):
                    stats["tags"][tag] = stats["tags"].get(tag, 0) + 1

        return {"success": True, "stats": stats, "registry_path": reg_path}

    except Exception as e:
        return {
            "success": False,
            "error": f"Error retrieving stats: {e}",
            "stats": None,
        }


# ─── REGISTRY MANAGEMENT TOOLS ──────────────────────────────────────────────


def get_registry_path_tool(
    include_discovery: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get the currently configured registry path.

    This tool returns information about the current registry configuration,
    including whether the path is valid and where it was discovered from.

    Args:
        include_discovery: Whether to attempt auto-discovery if not configured
                          (default: True)
        registry_path: Ignored for this tool (included for API consistency)

    Returns:
        Dictionary containing:
        - success: bool
        - path: str or None - The registry path
        - is_valid: bool - Whether the path passes validation
        - source: str - Where the path came from ('config', 'discovered', 'none')
        - discovered_path: str or None - Auto-discovered path if different from configured
        - validation_errors: list - Missing components if path is invalid
    """
    try:
        operation = RegistryOperation()
        result = operation.get_registry_path(include_discovery=include_discovery)

        return {
            "success": result["success"],
            "path": result["path"],
            "is_valid": result["is_valid"],
            "source": result["source"],
            "discovered_path": result.get("discovered_path"),
            "validation_errors": result.get("validation_errors", []),
        }

    except RegistryOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "path": None,
            "is_valid": False,
            "source": "none",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "path": None,
            "is_valid": False,
            "source": "none",
        }


def set_registry_path_tool(
    path: str,
    validate: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Set the default registry path in configuration.

    This tool updates the HoxCore configuration to use the specified path
    as the default registry. By default, the path is validated before setting
    to ensure it's a valid HoxCore registry.

    Note: This tool is only available in read-write mode.

    Args:
        path: Path to set as the default registry
        validate: Whether to validate the path before setting (default: True)
        registry_path: Ignored for this tool (included for API consistency)

    Returns:
        Dictionary containing:
        - success: bool
        - path: str - The newly set path (resolved to absolute)
        - previous_path: str or None - The previous registry path
        - is_valid: bool - Whether the new path is valid (if validated)

    Raises:
        InvalidRegistryPathError: If validate=True and path is invalid
    """
    try:
        if not path:
            return {
                "success": False,
                "error": "Path is required",
                "path": None,
                "previous_path": None,
                "is_valid": False,
            }

        operation = RegistryOperation()

        try:
            result = operation.set_registry_path(path=path, validate=validate)
        except InvalidRegistryPathError as e:
            return {
                "success": False,
                "error": str(e),
                "path": e.path,
                "previous_path": None,
                "is_valid": False,
                "missing_components": e.missing_components,
            }

        return {
            "success": True,
            "path": result["path"],
            "previous_path": result["previous_path"],
            "is_valid": result["is_valid"],
        }

    except RegistryOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "path": path,
            "previous_path": None,
            "is_valid": False,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "path": path,
            "previous_path": None,
            "is_valid": False,
        }


def validate_registry_path_tool(
    path: str,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate if a path is a valid HoxCore registry.

    A valid registry must:
    - Exist and be a directory
    - Contain config.yml
    - Contain all entity folders: programs, projects, missions, actions

    Args:
        path: Path to validate
        registry_path: Ignored for this tool (included for API consistency)

    Returns:
        Dictionary containing:
        - success: bool - Always True (validation completed)
        - valid: bool - Whether the path is a valid registry
        - path: str - The validated path (resolved to absolute)
        - missing: list - Missing required components (empty if valid)
    """
    try:
        if not path:
            return {
                "success": True,
                "valid": False,
                "path": "",
                "missing": ["path is required"],
            }

        result = RegistryOperation.validate_registry_path(path)

        return {
            "success": True,
            "valid": result["valid"],
            "path": result["path"],
            "missing": result["missing"],
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "valid": False,
            "path": path,
            "missing": [],
        }


def list_registries_tool(
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all known registries.

    Currently supports a single configured registry plus auto-discovered
    registries. Future versions may support multiple named registries.

    Args:
        registry_path: Ignored for this tool (included for API consistency)

    Returns:
        Dictionary containing:
        - success: bool
        - registries: list of registry objects with:
            - path: str - Registry path
            - is_current: bool - Whether this is the active registry
            - is_valid: bool - Whether the path passes validation
            - name: str - Registry name ('default' or 'discovered')
            - source: str - Where it came from ('config' or 'discovered')
        - count: int - Number of registries found
    """
    try:
        operation = RegistryOperation()
        result = operation.list_registries()

        return {
            "success": True,
            "registries": result["registries"],
            "count": result["count"],
        }

    except RegistryOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "registries": [],
            "count": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "registries": [],
            "count": 0,
        }


def discover_registry_tool(
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Attempt to discover a registry in the current directory tree.

    Walks up from the current working directory looking for a valid
    HoxCore registry structure.

    Args:
        registry_path: Ignored for this tool (included for API consistency)

    Returns:
        Dictionary containing:
        - success: bool - Whether a registry was discovered
        - path: str or None - Discovered registry path
        - is_valid: bool - Whether the discovered path is valid
    """
    try:
        operation = RegistryOperation()
        result = operation.discover_registry()

        return {
            "success": result["success"],
            "path": result["path"],
            "is_valid": result["is_valid"],
        }

    except RegistryOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "path": None,
            "is_valid": False,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "path": None,
            "is_valid": False,
        }


def clear_registry_path_tool(
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Clear the configured registry path.

    Removes the registry path from configuration. After clearing,
    HoxCore will rely on auto-discovery or explicit path specification.

    Note: This tool is only available in read-write mode.

    Args:
        registry_path: Ignored for this tool (included for API consistency)

    Returns:
        Dictionary containing:
        - success: bool
        - previous_path: str or None - The cleared path
    """
    try:
        operation = RegistryOperation()
        result = operation.clear_registry_path()

        return {
            "success": True,
            "previous_path": result["previous_path"],
        }

    except RegistryOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "previous_path": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "previous_path": None,
        }


# ─── VALIDATION TOOLS ───────────────────────────────────────────────────────


def validate_registry_tool(
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate the integrity and consistency of a HoxCore registry.

    This tool performs comprehensive validation checks including:
    - Required fields validation (type, uid, title)
    - UID uniqueness across all entities
    - ID uniqueness within each entity type
    - Parent link validation (errors for broken links)
    - Child link validation (errors for broken links)
    - Related link validation (warnings for broken links)
    - Status value validation against EntityStatus enum
    - Entity type validation (type matches directory location)
    - Empty file detection
    - Invalid YAML detection

    This tool is available in both read-only and read-write modes since
    validation is a non-destructive operation.

    Args:
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool - Whether validation completed successfully
        - valid: bool - Whether the registry passed validation (no errors)
        - errors: list - List of error messages
        - warnings: list - List of warning messages
        - error_count: int - Number of errors found
        - warning_count: int - Number of warnings found
        - entities_checked: int - Total number of entities validated
        - entities_by_type: dict - Count of entities per type

    Examples:
        >>> validate_registry_tool()
        {
            "success": True,
            "valid": True,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
            "entities_checked": 15,
            "entities_by_type": {"project": 10, "program": 3, "mission": 1, "action": 1}
        }
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {
                "success": False,
                "error": "No registry found",
                "valid": False,
                "errors": [],
                "warnings": [],
                "error_count": 0,
                "warning_count": 0,
                "entities_checked": 0,
                "entities_by_type": {},
            }

        operation = ValidateOperation(reg_path)
        result = operation.validate_registry()

        return {
            "success": True,
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "error_count": result.error_count,
            "warning_count": result.warning_count,
            "entities_checked": result.entities_checked,
            "entities_by_type": result.entities_by_type,
        }

    except ValidateOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "valid": False,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
            "entities_checked": 0,
            "entities_by_type": {},
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "valid": False,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
            "entities_checked": 0,
            "entities_by_type": {},
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "valid": False,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
            "entities_checked": 0,
            "entities_by_type": {},
        }


def validate_entity_tool(
    entity_data: Dict[str, Any],
    check_relationships: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate a single entity's data structure (pre-flight validation).

    This tool performs validation on entity data before create or edit
    operations to catch issues early. It validates:
    - Required fields (type, uid, title)
    - Entity type against EntityType enum
    - Status value against EntityStatus enum
    - Children field format (must be a list)
    - Related field format (must be a list)
    - Parent/children/related references exist (if check_relationships=True)

    This is useful for:
    - Pre-flight validation before create/edit operations
    - Validating entity data from external sources
    - Testing entity templates

    This tool is available in both read-only and read-write modes since
    validation is a non-destructive operation.

    Args:
        entity_data: Entity data dictionary to validate. Should contain at minimum:
                    type, uid, and title fields.
        check_relationships: Whether to verify that parent/children/related
                            references exist in the registry (default: True).
                            Set to False for validating entities in isolation.
        registry_path: Optional registry path for relationship checking
                      (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool - Whether validation completed successfully
        - valid: bool - Whether the entity data passed validation
        - errors: list - List of error messages
        - warnings: list - List of warning messages
        - error_count: int - Number of errors found
        - warning_count: int - Number of warnings found

    Examples:
        >>> validate_entity_tool({
        ...     "type": "project",
        ...     "uid": "proj-001",
        ...     "title": "My Project",
        ...     "status": "active"
        ... })
        {
            "success": True,
            "valid": True,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0
        }

        >>> validate_entity_tool({
        ...     "type": "invalid_type",
        ...     "title": "Missing UID"
        ... })
        {
            "success": True,
            "valid": False,
            "errors": [
                "Missing required field 'uid'",
                "Invalid entity type 'invalid_type'. Valid types: program, project, mission, action"
            ],
            "warnings": [],
            "error_count": 2,
            "warning_count": 0
        }
    """
    try:
        if not entity_data:
            return {
                "success": True,
                "valid": False,
                "errors": ["Entity data is required"],
                "warnings": [],
                "error_count": 1,
                "warning_count": 0,
            }

        if not isinstance(entity_data, dict):
            return {
                "success": True,
                "valid": False,
                "errors": ["Entity data must be a dictionary"],
                "warnings": [],
                "error_count": 1,
                "warning_count": 0,
            }

        # Get registry path for relationship checking
        reg_path = _get_registry_path(registry_path)

        # If relationship checking is requested but no registry, skip relationships
        if check_relationships and not reg_path:
            check_relationships = False

        if reg_path:
            operation = ValidateOperation(reg_path)
            result = operation.validate_entity(
                entity_data=entity_data,
                check_relationships=check_relationships,
            )
        else:
            # Perform basic validation without registry
            result = _validate_entity_without_registry(entity_data)

        return {
            "success": True,
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "error_count": len(result.errors),
            "warning_count": len(result.warnings),
        }

    except ValidateOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "valid": False,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "valid": False,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "valid": False,
            "errors": [],
            "warnings": [],
            "error_count": 0,
            "warning_count": 0,
        }


def _validate_entity_without_registry(
    entity_data: Dict[str, Any],
) -> "EntityValidationResult":
    """
    Validate entity data without a registry (basic structural validation).

    This is used when no registry is available for relationship checking.
    """
    from hxc.core.operations.validate import EntityValidationResult

    result = EntityValidationResult(entity_data=entity_data)

    # Required fields
    required_fields = ["type", "uid", "title"]
    for field_name in required_fields:
        if field_name not in entity_data or not entity_data[field_name]:
            result.add_error(f"Missing required field '{field_name}'")

    # Validate entity type
    entity_type = entity_data.get("type")
    if entity_type:
        try:
            EntityType.from_string(entity_type)
        except ValueError:
            valid_types = ", ".join(EntityType.values())
            result.add_error(
                f"Invalid entity type '{entity_type}'. Valid types: {valid_types}"
            )

    # Validate status
    status = entity_data.get("status")
    if status:
        try:
            EntityStatus.from_string(status)
        except ValueError:
            valid_statuses = ", ".join(EntityStatus.values())
            result.add_error(
                f"Invalid status '{status}'. Valid statuses: {valid_statuses}"
            )

    # Validate children format
    children = entity_data.get("children")
    if children is not None and not isinstance(children, list):
        result.add_error("Invalid children format: must be a list")

    # Validate related format
    related = entity_data.get("related")
    if related is not None and not isinstance(related, list):
        result.add_warning("Invalid related format: must be a list")

    return result


# ─── TEMPLATE TOOLS ─────────────────────────────────────────────────────────


def list_templates_tool(
    include_registry: bool = True,
    include_user: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    List all available templates.

    Templates are declarative scaffolding definitions that can be used to create
    folder structures, files, and initialize repositories when creating new entities.
    Templates are searched in two locations:
    - Registry-local: `.hxc/templates/` within the registry
    - User templates: `~/.hxc/templates/`

    Args:
        include_registry: Include registry-local templates (default: True)
        include_user: Include user templates from ~/.hxc/templates/ (default: True)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - templates: list of template info dictionaries with:
            - id: str - Template identifier (path-based)
            - path: str - Full path to template file
            - source: str - 'registry' or 'user'
            - name: str or None - Template name (if parseable)
            - version: str or None - Template version (if parseable)
            - description: str or None - Template description (if parseable)
            - author: str or None - Template author (if parseable)
            - valid: bool - Whether template is valid
        - count: int - Number of templates found

    Examples:
        >>> list_templates_tool()
        {
            "success": True,
            "templates": [
                {
                    "id": "software.dev/cli-tool/default",
                    "path": "~/.hxc/templates/software.dev/cli-tool/default.yml",
                    "source": "user",
                    "name": "cli-tool-default",
                    "version": "1.0",
                    "description": "Standard CLI tool project structure",
                    "valid": True
                }
            ],
            "count": 1
        }
    """
    try:
        reg_path = _get_registry_path(registry_path)

        operation = ScaffoldOperation(registry_path=reg_path)
        templates = operation.list_templates(
            include_registry=include_registry,
            include_user=include_user,
        )

        return {
            "success": True,
            "templates": templates,
            "count": len(templates),
        }

    except ScaffoldOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "templates": [],
            "count": 0,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "templates": [],
            "count": 0,
        }


def show_template_tool(
    template_ref: str,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get detailed information about a template.

    Templates are declarative scaffolding definitions that specify folder
    structures, files to create, and Git initialization options. This tool
    retrieves and parses a template to show its full definition.

    Args:
        template_ref: Template reference (path or identifier).
                     Can be an explicit path, registry-local reference,
                     or user template reference.
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - template: dict with template details (on success):
            - path: str - Resolved template path
            - name: str or None - Template name
            - version: str or None - Template version
            - description: str or None - Template description
            - author: str or None - Template author
            - structure: list - Directories to create
            - files: list - Files to create
            - copy: list - Files to copy
            - git: dict or None - Git configuration
            - variables: list - Variable definitions
            - source: str - Template source ('explicit', 'registry', or 'user')
        - error: str (only if success=False)
        - searched_paths: list (only if template not found)

    Examples:
        >>> show_template_tool("software.dev/cli-tool/default")
        {
            "success": True,
            "template": {
                "path": "~/.hxc/templates/software.dev/cli-tool/default.yml",
                "name": "cli-tool-default",
                "version": "1.0",
                "description": "Standard CLI tool project structure",
                "author": "hoxcore",
                "structure": [
                    {"type": "directory", "path": "src/{{id}}"},
                    {"type": "directory", "path": "tests"}
                ],
                "files": [
                    {"path": "README.md", "content": "# {{title}}\\n..."}
                ],
                "git": {"init": true, "initial_commit": true},
                "variables": [
                    {"name": "title", "source": "entity"}
                ],
                "source": "user"
            }
        }
    """
    try:
        if not template_ref:
            return {
                "success": False,
                "error": "Template reference is required",
                "template": None,
            }

        reg_path = _get_registry_path(registry_path)

        operation = ScaffoldOperation(registry_path=reg_path)

        info = operation.get_template_info(template_ref)

        return {
            "success": True,
            "template": info,
        }

    except TemplateNotFoundOperationError as e:
        return {
            "success": False,
            "error": f"Template not found: {e.template_ref}",
            "template": None,
            "searched_paths": e.searched_paths,
        }
    except TemplateValidationError as e:
        return {
            "success": False,
            "error": f"Invalid template: {e}",
            "template": None,
        }
    except ScaffoldSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "template": None,
        }
    except ScaffoldOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "template": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "template": None,
        }


def validate_template_tool(
    template_ref: str,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate a template file.

    Validates that a template file exists, is valid YAML, and conforms to
    the HoxCore template schema. Templates must be declarative only - no
    script execution or shell commands are allowed.

    Validation checks:
    - File exists and is readable
    - Valid YAML syntax
    - Required fields present (name, version)
    - Valid structure entries (directories only)
    - Valid file entries (must have content or template reference)
    - Valid variable definitions (entity, system, or prompt sources)
    - No path traversal attempts (../)
    - No absolute paths

    Args:
        template_ref: Template reference (path or identifier)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - valid: bool - Whether the template is valid
        - template_ref: str - The template reference
        - template_path: str - Resolved path (on success)
        - name: str or None - Template name (on success)
        - version: str or None - Template version (on success)
        - error: str (only if validation failed)
        - searched_paths: list (only if template not found)

    Examples:
        >>> validate_template_tool("software.dev/cli-tool/default")
        {
            "success": True,
            "valid": True,
            "template_ref": "software.dev/cli-tool/default",
            "template_path": "~/.hxc/templates/software.dev/cli-tool/default.yml",
            "name": "cli-tool-default",
            "version": "1.0"
        }

        >>> validate_template_tool("invalid-template")
        {
            "success": True,
            "valid": False,
            "template_ref": "invalid-template",
            "error": "Template not found: invalid-template",
            "searched_paths": [...]
        }
    """
    try:
        if not template_ref:
            return {
                "success": True,
                "valid": False,
                "template_ref": "",
                "error": "Template reference is required",
            }

        reg_path = _get_registry_path(registry_path)

        operation = ScaffoldOperation(registry_path=reg_path)

        # Resolve and parse template (validation happens during parse)
        template_path = operation.resolve_template(template_ref)
        template_data = operation.parse_template(template_path)

        return {
            "success": True,
            "valid": True,
            "template_ref": template_ref,
            "template_path": str(template_path),
            "name": template_data.get("name"),
            "version": template_data.get("version"),
        }

    except TemplateNotFoundOperationError as e:
        return {
            "success": True,
            "valid": False,
            "template_ref": template_ref,
            "error": f"Template not found: {e.template_ref}",
            "searched_paths": e.searched_paths,
        }
    except TemplateValidationError as e:
        return {
            "success": True,
            "valid": False,
            "template_ref": template_ref,
            "error": f"Template validation failed: {e}",
        }
    except ScaffoldSecurityError as e:
        return {
            "success": True,
            "valid": False,
            "template_ref": template_ref,
            "error": f"Security error: {e}",
        }
    except ScaffoldOperationError as e:
        return {
            "success": False,
            "valid": False,
            "template_ref": template_ref,
            "error": str(e),
        }
    except Exception as e:
        return {
            "success": False,
            "valid": False,
            "template_ref": template_ref,
            "error": f"Unexpected error: {e}",
        }


def preview_scaffold_tool(
    template_ref: str,
    output_path: str,
    entity_data: Optional[Dict[str, Any]] = None,
    prompt_values: Optional[Dict[str, Any]] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Preview scaffolding without making changes (dry-run).

    This tool shows what would be created by scaffolding operation without
    actually creating any files or directories. Useful for verifying template
    behavior before committing to changes.

    Args:
        template_ref: Template reference (path or identifier)
        output_path: Path where scaffolding would be performed
        entity_data: Optional entity data for variable substitution.
                    Typically includes title, id, uid, description, etc.
        prompt_values: Optional user-provided values for prompt variables
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - dry_run: bool - Always True for preview
        - template_name: str or None - Template name
        - template_version: str or None - Template version
        - output_path: str - Resolved output path
        - directories_created: list - Directories that would be created
        - files_created: list - Files that would be created
        - files_copied: list - Files that would be copied
        - git_initialized: bool - Whether Git would be initialized
        - git_committed: bool - Whether initial commit would be created
        - total_items: int - Total items that would be created
        - pending_prompts: list - Prompt variables that need values
        - error: str (only if success=False)
        - searched_paths: list (only if template not found)

    Examples:
        >>> preview_scaffold_tool(
        ...     "software.dev/cli-tool/default",
        ...     "./my-project",
        ...     {"title": "My Project", "id": "my-proj"}
        ... )
        {
            "success": True,
            "dry_run": True,
            "template_name": "cli-tool-default",
            "output_path": "/home/user/my-project",
            "directories_created": ["src/my-proj", "tests", "docs"],
            "files_created": ["README.md", "src/my-proj/__init__.py"],
            "files_copied": ["LICENSE"],
            "git_initialized": True,
            "git_committed": True,
            "total_items": 6,
            "pending_prompts": []
        }
    """
    try:
        if not template_ref:
            return {
                "success": False,
                "error": "Template reference is required",
                "dry_run": True,
            }

        if not output_path:
            return {
                "success": False,
                "error": "Output path is required",
                "dry_run": True,
            }

        reg_path = _get_registry_path(registry_path)

        operation = ScaffoldOperation(registry_path=reg_path)

        result = operation.preview(
            template_ref=template_ref,
            output_path=output_path,
            entity_data=entity_data or {},
            prompt_values=prompt_values,
        )

        return result.to_dict()

    except TemplateNotFoundOperationError as e:
        return {
            "success": False,
            "error": f"Template not found: {e.template_ref}",
            "dry_run": True,
            "searched_paths": e.searched_paths,
        }
    except TemplateValidationError as e:
        return {
            "success": False,
            "error": f"Invalid template: {e}",
            "dry_run": True,
        }
    except ScaffoldSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "dry_run": True,
        }
    except ScaffoldExecutionError as e:
        return {
            "success": False,
            "error": f"Preview failed: {e}",
            "dry_run": True,
        }
    except ScaffoldOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "dry_run": True,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "dry_run": True,
        }


def scaffold_tool(
    template_ref: str,
    output_path: str,
    entity_data: Optional[Dict[str, Any]] = None,
    prompt_values: Optional[Dict[str, Any]] = None,
    allow_non_empty: bool = False,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute scaffolding from a template.

    Creates folder structures, files with content injection, copies template
    assets, and optionally initializes a Git repository based on the template
    definition. This is a write operation that creates files and directories.

    Templates are declarative only with these security restrictions:
    - No shell command execution
    - No script execution
    - No network access
    - No arbitrary file reading
    - No path traversal (../)
    - Only read from designated template directories

    Note: This tool is only available in read-write mode.

    Args:
        template_ref: Template reference (path or identifier)
        output_path: Path where scaffolding should be performed.
                    Must not exist or be empty (unless allow_non_empty=True)
        entity_data: Optional entity data for variable substitution.
                    Typically includes title, id, uid, description, etc.
        prompt_values: Optional user-provided values for prompt variables.
                      Required if template has prompt variables without defaults.
        allow_non_empty: Allow scaffolding in non-empty directories (default: False)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - dry_run: bool - Always False for actual scaffolding
        - template_name: str or None - Template name
        - template_version: str or None - Template version
        - output_path: str - Resolved output path
        - directories_created: list - Directories created
        - files_created: list - Files created
        - files_copied: list - Files copied
        - git_initialized: bool - Whether Git was initialized
        - git_committed: bool - Whether initial commit was created
        - total_items: int - Total items created
        - warnings: list - Any warnings during scaffolding
        - error: str (only if success=False)
        - searched_paths: list (only if template not found)
        - pending_prompts: list (only if prompts required but not provided)

    Examples:
        >>> scaffold_tool(
        ...     "software.dev/cli-tool/default",
        ...     "./my-project",
        ...     {"title": "My Project", "id": "my-proj"}
        ... )
        {
            "success": True,
            "dry_run": False,
            "template_name": "cli-tool-default",
            "output_path": "/home/user/my-project",
            "directories_created": ["src/my-proj", "tests", "docs"],
            "files_created": ["README.md", "src/my-proj/__init__.py"],
            "files_copied": ["LICENSE"],
            "git_initialized": True,
            "git_committed": True,
            "total_items": 6
        }
    """
    try:
        if not template_ref:
            return {
                "success": False,
                "error": "Template reference is required",
                "dry_run": False,
            }

        if not output_path:
            return {
                "success": False,
                "error": "Output path is required",
                "dry_run": False,
            }

        reg_path = _get_registry_path(registry_path)

        operation = ScaffoldOperation(registry_path=reg_path)

        result = operation.scaffold(
            template_ref=template_ref,
            output_path=output_path,
            entity_data=entity_data or {},
            prompt_values=prompt_values,
            dry_run=False,
            allow_non_empty=allow_non_empty,
            require_all_prompts=True,
        )

        return result.to_dict()

    except TemplateNotFoundOperationError as e:
        return {
            "success": False,
            "error": f"Template not found: {e.template_ref}",
            "dry_run": False,
            "searched_paths": e.searched_paths,
        }
    except TemplateValidationError as e:
        return {
            "success": False,
            "error": f"Invalid template: {e}",
            "dry_run": False,
        }
    except ScaffoldSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "dry_run": False,
        }
    except PromptRequiredError as e:
        return {
            "success": False,
            "error": f"Prompt values required: {e}",
            "dry_run": False,
            "pending_prompts": e.required_prompts,
        }
    except ScaffoldExecutionError as e:
        return {
            "success": False,
            "error": f"Scaffolding failed: {e}",
            "dry_run": False,
        }
    except ScaffoldOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "dry_run": False,
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "dry_run": False,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "dry_run": False,
        }


def init_template_directories_tool(
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initialize template directories.

    Creates the user templates directory (~/.hxc/templates/) and optionally
    the registry templates directory (.hxc/templates/) if a registry is
    configured.

    Note: This tool is only available in read-write mode.

    Args:
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary containing:
        - success: bool
        - user_path: str or None - Created user templates directory
        - registry_path: str or None - Created registry templates directory
        - error: str (only if success=False)

    Examples:
        >>> init_template_directories_tool()
        {
            "success": True,
            "user_path": "/home/user/.hxc/templates",
            "registry_path": "/path/to/registry/.hxc/templates"
        }
    """
    try:
        reg_path = _get_registry_path(registry_path)

        operation = ScaffoldOperation(registry_path=reg_path)
        result = operation.ensure_template_directories()

        return {
            "success": True,
            "user_path": str(result["user"]) if result.get("user") else None,
            "registry_path": str(result["registry"]) if result.get("registry") else None,
        }

    except ScaffoldOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "user_path": None,
            "registry_path": None,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "user_path": None,
            "registry_path": None,
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
    template: Optional[str] = None,
    scaffold: bool = False,
    scaffold_output: Optional[str] = None,
    use_git: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new entity (program, project, mission, or action) in the registry.

    This tool performs git-aware creation by default, staging and committing the
    new entity file with a structured commit message. ID uniqueness is validated
    before creation to ensure data integrity.

    Optionally, can scaffold a project structure from a template when creating
    the entity. Use the scaffold parameter to trigger scaffolding.

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
        template: Optional template reference to store in entity and/or use for scaffolding
        scaffold: If True and template is provided, scaffold project structure (default: False)
        scaffold_output: Output directory for scaffolding (default: current directory with entity ID)
        use_git: Whether to commit the change to git (default: True)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary with uid, id, file_path, entity, and git_committed on success.
        If scaffold=True, also includes scaffold_result with scaffolding details.
        error message on failure.

    Examples:
        >>> create_entity_tool("project", "My CLI Tool", template="software.dev/cli-tool/default")
        {
            "success": True,
            "uid": "abc12345",
            "id": "my_cli_tool",
            "file_path": "/registry/projects/proj-abc12345.yml",
            "entity": {...},
            "git_committed": True
        }

        >>> create_entity_tool(
        ...     "project",
        ...     "My CLI Tool",
        ...     template="software.dev/cli-tool/default",
        ...     scaffold=True,
        ...     scaffold_output="./my-cli-tool"
        ... )
        {
            "success": True,
            "uid": "abc12345",
            "id": "my_cli_tool",
            "file_path": "/registry/projects/proj-abc12345.yml",
            "entity": {...},
            "git_committed": True,
            "scaffold_result": {
                "success": True,
                "directories_created": ["src/my_cli_tool", "tests"],
                "files_created": ["README.md"],
                ...
            }
        }
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

    # Validate scaffolding options
    if scaffold and not template:
        # Check if category has a variant that can be used as template
        if category:
            try:
                scaffold_op = ScaffoldOperation(registry_path=reg_path)
                parsed = scaffold_op.parse_category_variant(category)
                if parsed.has_variant:
                    template = parsed.template_path
            except Exception:
                pass

        if not template:
            return {
                "success": False,
                "error": "scaffold=True requires a template or a category with variant notation",
            }

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
            template=template,
            use_git=use_git,
        )

        response = {
            "success": True,
            "uid": result["uid"],
            "id": result["id"],
            "file_path": result["file_path"],
            "entity": result["entity"],
            "git_committed": result.get("git_committed", False),
        }

        # Execute scaffolding if requested
        if scaffold and template:
            scaffold_result = _execute_scaffolding_for_create(
                template_ref=template,
                entity_data=result["entity"],
                output_path=scaffold_output,
                registry_path=reg_path,
            )
            response["scaffold_result"] = scaffold_result

            # If scaffolding failed, note it but don't fail the whole operation
            if not scaffold_result.get("success"):
                response["scaffold_warning"] = (
                    f"Entity created but scaffolding failed: {scaffold_result.get('error')}"
                )

        return response

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


def _execute_scaffolding_for_create(
    template_ref: str,
    entity_data: Dict[str, Any],
    output_path: Optional[str],
    registry_path: str,
) -> Dict[str, Any]:
    """
    Execute scaffolding as part of entity creation.

    Args:
        template_ref: Template reference (path or identifier)
        entity_data: Entity data for variable substitution
        output_path: Output directory (defaults to current directory with entity ID)
        registry_path: Registry path for template resolution

    Returns:
        Dictionary with scaffolding result
    """
    # Determine output path
    if output_path:
        scaffold_path = Path(output_path).resolve()
    else:
        # Default to current directory with entity ID as subdirectory
        entity_id = entity_data.get("id", entity_data.get("uid", "project"))
        scaffold_path = Path.cwd() / entity_id

    try:
        operation = ScaffoldOperation(registry_path=registry_path)

        result = operation.scaffold(
            template_ref=template_ref,
            output_path=scaffold_path,
            entity_data=entity_data,
            dry_run=False,
            allow_non_empty=False,
            require_all_prompts=False,
        )

        return result.to_dict()

    except TemplateNotFoundOperationError as e:
        return {
            "success": False,
            "error": f"Template not found: {e.template_ref}",
            "searched_paths": e.searched_paths,
        }
    except TemplateValidationError as e:
        return {
            "success": False,
            "error": f"Invalid template: {e}",
        }
    except ScaffoldSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
        }
    except PromptRequiredError as e:
        return {
            "success": False,
            "error": f"Prompt values required for scaffolding",
            "pending_prompts": e.required_prompts,
        }
    except ScaffoldExecutionError as e:
        return {
            "success": False,
            "error": f"Scaffolding failed: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Scaffolding error: {e}",
        }


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
    use_git: bool = True,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Edit properties of an existing registry entity.

    This tool performs git-aware editing by default, staging and committing the
    modified entity file with a structured commit message. ID uniqueness is
    validated when changing the ID field to ensure data integrity.

    Args:
        identifier: UID or human-readable ID of the entity to edit
        set_title: New title value
        set_description: New description value
        set_status: New status value
        set_id: New human-readable ID. Must be unique within entity type.
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
        use_git: Whether to commit the change to git (default: True)
        registry_path: Optional registry path (uses default if not provided)

    Returns:
        Dictionary with identifier, changes, entity, file_path, and git_committed
        on success; error message on failure.
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {
                "success": False,
                "error": "No registry found",
                "identifier": identifier,
            }

        entity_type_enum = None
        if entity_type:
            try:
                entity_type_enum = EntityType.from_string(entity_type)
            except ValueError as e:
                return {"success": False, "error": str(e), "identifier": identifier}

        # Use shared EditOperation
        operation = EditOperation(reg_path)

        result = operation.edit_entity(
            identifier=identifier,
            entity_type=entity_type_enum,
            # Scalar fields
            set_title=set_title,
            set_description=set_description,
            set_status=set_status,
            set_id=set_id,
            set_start_date=set_start_date,
            set_due_date=set_due_date,
            set_completion_date=set_completion_date,
            set_category=set_category,
            set_parent=set_parent,
            # List fields
            add_tags=add_tags,
            remove_tags=remove_tags,
            add_children=add_children,
            remove_children=remove_children,
            add_related=add_related,
            remove_related=remove_related,
            # Options
            use_git=use_git,
        )

        return {
            "success": True,
            "identifier": identifier,
            "changes": result["changes"],
            "entity": result["entity"],
            "file_path": result["file_path"],
            "git_committed": result.get("git_committed", False),
        }

    except EditEntityNotFoundError as e:
        return {
            "success": False,
            "error": str(e),
            "identifier": identifier,
        }
    except EditDuplicateIdError as e:
        return {
            "success": False,
            "error": str(e),
            "identifier": identifier,
        }
    except InvalidValueError as e:
        return {
            "success": False,
            "error": str(e),
            "identifier": identifier,
        }
    except NoChangesError as e:
        return {
            "success": False,
            "error": str(e),
            "identifier": identifier,
        }
    except EditOperationError as e:
        return {
            "success": False,
            "error": str(e),
            "identifier": identifier,
        }
    except PathSecurityError as e:
        return {
            "success": False,
            "error": f"Security error: {e}",
            "identifier": identifier,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "identifier": identifier,
        }


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
            return {
                "success": False,
                "error": "No registry found",
                "identifier": identifier,
            }

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
        return {
            "success": False,
            "error": f"Security error: {e}",
            "identifier": identifier,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {e}",
            "identifier": identifier,
        }


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


def _get_entities_by_ids(
    registry_path: str, identifiers: List[str], recursive: bool = False
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
                        children = _get_entities_by_ids(
                            registry_path, children_ids, True
                        )
                        entities.extend(children)
        except Exception:
            continue

    return entities