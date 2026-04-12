"""
Edit Operation for HoxCore Registry.

This module provides the shared edit operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Entity discovery by ID or UID
- Entity loading and validation
- ID uniqueness validation
- Edit application for scalar and list fields
- Change tracking
- File writing with path security
- Git integration with structured commit messages
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from hxc.core.enums import EntityStatus, EntityType
from hxc.utils.git import commit_entity_change
from hxc.utils.path_security import PathSecurityError, resolve_safe_path


class EditOperationError(Exception):
    """Base exception for edit operation errors"""

    pass


class EntityNotFoundError(EditOperationError):
    """Raised when the entity to edit cannot be found"""

    pass


class DuplicateIdError(EditOperationError):
    """Raised when attempting to set an ID that already exists"""

    pass


class InvalidValueError(EditOperationError):
    """Raised when an invalid value is provided for a field"""

    pass


class NoChangesError(EditOperationError):
    """Raised when no changes are specified"""

    pass


class EditOperation:
    """
    Shared edit operation for CLI and MCP interfaces.

    This class provides the core entity editing logic including:
    - Entity discovery by ID or UID
    - Entity loading and validation
    - ID uniqueness validation
    - Edit application for all field types
    - Change tracking
    - File writing with path security
    - Optional git integration
    """

    def __init__(self, registry_path: str):
        """
        Initialize the edit operation.

        Args:
            registry_path: Path to the registry root directory
        """
        self.registry_path = registry_path

    def find_entity_file(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[Tuple[Path, EntityType]]:
        """
        Find an entity file by ID or UID.

        Uses a two-phase search:
        1. Fast path: Direct filename match for UID
        2. Slow path: Parse YAML files to find matching ID field

        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type to filter search

        Returns:
            Tuple of (file_path, entity_type) if found, None otherwise

        Raises:
            PathSecurityError: If path validation fails
        """
        types_to_search = [entity_type] if entity_type else list(EntityType)

        for ent_type in types_to_search:
            folder_name = ent_type.get_folder_name()
            file_prefix = ent_type.get_file_prefix()

            try:
                type_dir = resolve_safe_path(self.registry_path, folder_name)
            except PathSecurityError:
                continue

            if not type_dir.exists():
                continue

            # Fast path: check for UID match in filename
            uid_pattern = f"{file_prefix}-{identifier}.yml"
            for file_path in type_dir.glob(uid_pattern):
                try:
                    secure_file_path = resolve_safe_path(self.registry_path, file_path)
                    return (secure_file_path, ent_type)
                except PathSecurityError:
                    continue

            # Slow path: search inside files for ID field match
            for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
                try:
                    secure_file_path = resolve_safe_path(self.registry_path, file_path)
                    with open(secure_file_path, "r") as f:
                        data = yaml.safe_load(f)
                        if data and isinstance(data, dict):
                            if (
                                data.get("id") == identifier
                                or data.get("uid") == identifier
                            ):
                                return (secure_file_path, ent_type)
                except PathSecurityError:
                    continue
                except Exception:
                    continue

        return None

    def load_entity(self, file_path: Path) -> Dict[str, Any]:
        """
        Load entity data from a YAML file.

        Args:
            file_path: Path to the entity file

        Returns:
            Entity data dictionary

        Raises:
            PathSecurityError: If path validation fails
            EditOperationError: If entity data is invalid
        """
        secure_file_path = resolve_safe_path(self.registry_path, file_path)

        with open(secure_file_path, "r") as f:
            data = yaml.safe_load(f)

        if not data or not isinstance(data, dict):
            raise EditOperationError(f"Invalid entity data in {file_path}")

        return data

    def load_existing_ids(self, entity_type: EntityType) -> Set[str]:
        """
        Load all ID fields for existing entities of a given type.

        Args:
            entity_type: The entity type to load IDs for

        Returns:
            Set of existing IDs
        """
        ids: Set[str] = set()

        try:
            type_dir = resolve_safe_path(
                self.registry_path, entity_type.get_folder_name()
            )
        except PathSecurityError:
            return ids

        if not type_dir.exists():
            return ids

        file_prefix = entity_type.get_file_prefix()
        for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
            try:
                secure_file_path = resolve_safe_path(self.registry_path, file_path)
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

    def validate_id_uniqueness(
        self,
        entity_data: Dict[str, Any],
        new_id: str,
    ) -> None:
        """
        Validate that a new ID is unique within the entity's type.

        ID uniqueness is scoped per entity type. The same ID can exist
        in different entity types (e.g., a project and a program can
        both have ID "P-001").

        Args:
            entity_data: The current entity data
            new_id: The new ID to set

        Raises:
            DuplicateIdError: If the ID already exists for this entity type
        """
        entity_type_value = entity_data.get("type")
        if not entity_type_value:
            return  # Can't validate without knowing the type

        try:
            entity_type = EntityType.from_string(entity_type_value)
        except ValueError:
            return  # Invalid entity type in file, skip check

        current_id = entity_data.get("id")

        # Setting to the same ID is a no-op
        if current_id == new_id:
            return

        existing_ids = self.load_existing_ids(entity_type)

        if new_id in existing_ids:
            raise DuplicateIdError(
                f"{entity_type.value} with id '{new_id}' already exists in this registry"
            )

    def apply_scalar_edits(
        self,
        entity_data: Dict[str, Any],
        *,
        set_title: Optional[str] = None,
        set_description: Optional[str] = None,
        set_status: Optional[str] = None,
        set_id: Optional[str] = None,
        set_start_date: Optional[str] = None,
        set_due_date: Optional[str] = None,
        set_completion_date: Optional[str] = None,
        set_duration_estimate: Optional[str] = None,
        set_category: Optional[str] = None,
        set_parent: Optional[str] = None,
        set_template: Optional[str] = None,
    ) -> List[str]:
        """
        Apply scalar field edits to entity data.

        This method validates inputs before applying changes:
        - ID uniqueness is checked if set_id is provided
        - Status value is validated against EntityStatus enum

        Changes are only recorded when the new value differs from
        the current value (setting same value is a no-op).

        Args:
            entity_data: The entity data dictionary to modify (modified in place)
            set_*: Optional new values for each field

        Returns:
            List of change descriptions

        Raises:
            InvalidValueError: If an invalid status value is provided
            DuplicateIdError: If set_id conflicts with an existing ID
        """
        changes: List[str] = []

        # Validate ID uniqueness before applying any changes
        if set_id is not None:
            self.validate_id_uniqueness(entity_data, set_id)

        # Validate and normalize status if provided
        if set_status is not None:
            try:
                set_status = EntityStatus.from_string(set_status).value
            except ValueError as e:
                raise InvalidValueError(str(e))

        scalar_mappings = {
            "title": set_title,
            "description": set_description,
            "status": set_status,
            "id": set_id,
            "start_date": set_start_date,
            "due_date": set_due_date,
            "completion_date": set_completion_date,
            "duration_estimate": set_duration_estimate,
            "category": set_category,
            "parent": set_parent,
            "template": set_template,
        }

        for field, value in scalar_mappings.items():
            if value is not None:
                old_value = entity_data.get(field, "(not set)")
                # Skip if setting same value (no change recorded)
                if old_value == value:
                    continue
                entity_data[field] = value
                changes.append(f"Set {field}: '{old_value}' → '{value}'")

        return changes

    def apply_list_edits(
        self,
        entity_data: Dict[str, Any],
        *,
        set_tags: Optional[List[str]] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
        set_children: Optional[List[str]] = None,
        add_children: Optional[List[str]] = None,
        remove_children: Optional[List[str]] = None,
        set_related: Optional[List[str]] = None,
        add_related: Optional[List[str]] = None,
        remove_related: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Apply list field edits to entity data.

        Supports three modes for each list field:
        - set_*: Replace the entire list
        - add_*: Add items (idempotent - duplicates ignored)
        - remove_*: Remove items (silently ignores missing items)

        When set_* is provided, add_* and remove_* for that field are ignored.

        Args:
            entity_data: The entity data dictionary to modify (modified in place)
            set_*: Optional replacement values for lists
            add_*: Optional values to add to lists
            remove_*: Optional values to remove from lists

        Returns:
            List of change descriptions
        """
        changes: List[str] = []

        # Tags operations
        if set_tags is not None:
            old_tags = entity_data.get("tags", [])
            entity_data["tags"] = set_tags
            changes.append(f"Set tags: {old_tags} → {set_tags}")
        else:
            if add_tags:
                tags = entity_data.get("tags") or []
                for tag in add_tags:
                    if tag not in tags:
                        tags.append(tag)
                        changes.append(f"Added tag: '{tag}'")
                entity_data["tags"] = tags

            if remove_tags:
                tags = entity_data.get("tags") or []
                for tag in remove_tags:
                    if tag in tags:
                        tags.remove(tag)
                        changes.append(f"Removed tag: '{tag}'")
                entity_data["tags"] = tags

        # Children operations
        if set_children is not None:
            old_children = entity_data.get("children", [])
            entity_data["children"] = set_children
            changes.append(f"Set children: {old_children} → {set_children}")
        else:
            if add_children:
                children = entity_data.get("children") or []
                for child in add_children:
                    if child not in children:
                        children.append(child)
                        changes.append(f"Added child: '{child}'")
                entity_data["children"] = children

            if remove_children:
                children = entity_data.get("children") or []
                for child in remove_children:
                    if child in children:
                        children.remove(child)
                        changes.append(f"Removed child: '{child}'")
                entity_data["children"] = children

        # Related operations
        if set_related is not None:
            old_related = entity_data.get("related", [])
            entity_data["related"] = set_related
            changes.append(f"Set related: {old_related} → {set_related}")
        else:
            if add_related:
                related = entity_data.get("related") or []
                for rel in add_related:
                    if rel not in related:
                        related.append(rel)
                        changes.append(f"Added related: '{rel}'")
                entity_data["related"] = related

            if remove_related:
                related = entity_data.get("related") or []
                for rel in remove_related:
                    if rel in related:
                        related.remove(rel)
                        changes.append(f"Removed related: '{rel}'")
                entity_data["related"] = related

        return changes

    def write_entity_file(
        self,
        file_path: Path,
        entity_data: Dict[str, Any],
    ) -> None:
        """
        Write entity data to a YAML file.

        Args:
            file_path: Path to the entity file
            entity_data: Entity data dictionary

        Raises:
            PathSecurityError: If path validation fails
            IOError: If file writing fails
        """
        secure_file_path = resolve_safe_path(self.registry_path, file_path)

        with open(secure_file_path, "w") as f:
            yaml.dump(entity_data, f, default_flow_style=False, sort_keys=False)

    def edit_entity(
        self,
        identifier: str,
        *,
        entity_type: Optional[EntityType] = None,
        # Scalar fields
        set_title: Optional[str] = None,
        set_description: Optional[str] = None,
        set_status: Optional[str] = None,
        set_id: Optional[str] = None,
        set_start_date: Optional[str] = None,
        set_due_date: Optional[str] = None,
        set_completion_date: Optional[str] = None,
        set_duration_estimate: Optional[str] = None,
        set_category: Optional[str] = None,
        set_parent: Optional[str] = None,
        set_template: Optional[str] = None,
        # List fields
        set_tags: Optional[List[str]] = None,
        add_tags: Optional[List[str]] = None,
        remove_tags: Optional[List[str]] = None,
        set_children: Optional[List[str]] = None,
        add_children: Optional[List[str]] = None,
        remove_children: Optional[List[str]] = None,
        set_related: Optional[List[str]] = None,
        add_related: Optional[List[str]] = None,
        remove_related: Optional[List[str]] = None,
        # Options
        use_git: bool = True,
    ) -> Dict[str, Any]:
        """
        Edit an entity in the registry.

        This is the main entry point for entity editing, handling:
        - Entity discovery by ID or UID
        - Entity loading and validation
        - ID uniqueness validation
        - Edit application for scalar and list fields
        - File writing with path security
        - Optional git integration with structured commit messages

        The operation is atomic from the perspective of git: if git
        integration is enabled and changes are made, they are staged
        and committed in a single operation.

        Args:
            identifier: ID or UID of the entity to edit
            entity_type: Optional entity type filter to disambiguate
            set_*: Scalar field values to set
            add_*, remove_*, set_* (lists): List field modifications
            use_git: Whether to commit changes to git (default: True)

        Returns:
            Dictionary containing:
            - success: bool
            - identifier: str
            - changes: List[str] (list of change descriptions)
            - entity: dict (updated entity data)
            - file_path: str (path to entity file)
            - git_committed: bool (True if changes were committed)

        Raises:
            EntityNotFoundError: If entity cannot be found
            EditOperationError: If entity data is invalid
            DuplicateIdError: If set_id conflicts with existing ID
            InvalidValueError: If invalid values are provided
            NoChangesError: If no changes are specified
            PathSecurityError: If path validation fails
        """
        # Find the entity file
        result = self.find_entity_file(identifier, entity_type)
        if result is None:
            raise EntityNotFoundError(f"Entity not found: {identifier}")

        file_path, found_entity_type = result

        # Load entity data
        entity_data = self.load_entity(file_path)

        # Check if any changes are specified
        anything_specified = any(
            [
                set_title is not None,
                set_description is not None,
                set_status is not None,
                set_id is not None,
                set_start_date is not None,
                set_due_date is not None,
                set_completion_date is not None,
                set_duration_estimate is not None,
                set_category is not None,
                set_parent is not None,
                set_template is not None,
                set_tags is not None,
                add_tags,
                remove_tags,
                set_children is not None,
                add_children,
                remove_children,
                set_related is not None,
                add_related,
                remove_related,
            ]
        )

        if not anything_specified:
            raise NoChangesError("No changes specified")

        # Apply scalar edits
        changes = self.apply_scalar_edits(
            entity_data,
            set_title=set_title,
            set_description=set_description,
            set_status=set_status,
            set_id=set_id,
            set_start_date=set_start_date,
            set_due_date=set_due_date,
            set_completion_date=set_completion_date,
            set_duration_estimate=set_duration_estimate,
            set_category=set_category,
            set_parent=set_parent,
            set_template=set_template,
        )

        # Apply list edits
        changes.extend(
            self.apply_list_edits(
                entity_data,
                set_tags=set_tags,
                add_tags=add_tags,
                remove_tags=remove_tags,
                set_children=set_children,
                add_children=add_children,
                remove_children=remove_children,
                set_related=set_related,
                add_related=add_related,
                remove_related=remove_related,
            )
        )

        # Write updated entity to file
        self.write_entity_file(file_path, entity_data)

        # Git commit if requested and there are changes
        git_committed = False
        if use_git and changes:
            git_committed = commit_entity_change(
                registry_path=self.registry_path,
                file_path=file_path,
                action="Edit",
                entity_data=entity_data,
                changes=changes,
            )

        return {
            "success": True,
            "identifier": identifier,
            "changes": changes,
            "entity": entity_data,
            "file_path": str(file_path),
            "git_committed": git_committed,
        }
