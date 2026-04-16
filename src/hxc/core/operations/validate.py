"""
Validate Operation for HoxCore Registry.

This module provides the shared validate operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Registry-wide integrity validation
- Entity-level validation (pre-flight checks)
- Required field validation
- UID uniqueness validation
- ID uniqueness validation (per entity type)
- Relationship validation (parent, children, related)
- Status and type validation
- Path security enforcement
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from hxc.core.enums import EntityStatus, EntityType
from hxc.utils.path_security import PathSecurityError, resolve_safe_path


class ValidateOperationError(Exception):
    """Base exception for validate operation errors"""

    pass


@dataclass
class ValidationResult:
    """
    Container for validation results.

    This class holds all validation errors, warnings, and metadata,
    providing a consistent structure for both CLI and MCP interfaces.
    """

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    entities_checked: int = 0
    entities_by_type: Dict[str, int] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        """Registry is valid if there are no errors"""
        return len(self.errors) == 0

    @property
    def error_count(self) -> int:
        """Number of errors"""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Number of warnings"""
        return len(self.warnings)

    def add_error(self, message: str) -> None:
        """Add an error message"""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another ValidationResult into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for MCP serialization.

        Returns:
            Dictionary containing all validation results
        """
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "entities_checked": self.entities_checked,
            "entities_by_type": self.entities_by_type,
        }


@dataclass
class EntityValidationResult:
    """
    Container for single entity validation results.

    Used for pre-flight validation before create/edit operations.
    """

    valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    entity_data: Optional[Dict[str, Any]] = None

    def add_error(self, message: str) -> None:
        """Add an error message and mark as invalid"""
        self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message"""
        self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for MCP serialization.

        Returns:
            Dictionary containing entity validation results
        """
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class ValidateOperation:
    """
    Shared validate operation for CLI and MCP interfaces.

    This class provides the core validation logic including:
    - Required field validation
    - UID uniqueness validation
    - ID uniqueness validation (per entity type)
    - Parent/child/related relationship validation
    - Status and type validation
    - File integrity validation
    - Path security enforcement
    """

    # Required fields for all entities
    REQUIRED_FIELDS = ["type", "uid", "title"]

    def __init__(self, registry_path: str):
        """
        Initialize the validate operation.

        Args:
            registry_path: Path to the registry root directory
        """
        self.registry_path = registry_path

    def _normalize_path(self, path: Optional[str]) -> Optional[Path]:
        """
        Normalize a path string to a resolved Path object for cross-platform comparison.

        Args:
            path: Path string to normalize, or None

        Returns:
            Resolved Path object, or None if input was None
        """
        if path is None:
            return None
        return Path(path).resolve()

    def validate_registry(self, verbose: bool = False) -> ValidationResult:
        """
        Validate the entire registry for integrity and consistency.

        This is the main entry point for full registry validation,
        performing all checks and returning a comprehensive result.

        Args:
            verbose: Whether to include detailed progress (used by CLI)

        Returns:
            ValidationResult containing all errors, warnings, and metadata
        """
        result = ValidationResult()

        # Load all entities
        entities, load_errors = self._load_all_entities()

        # Add load errors
        result.errors.extend(load_errors)

        # Count entities by type
        for entity in entities:
            entity_type = entity.get("type", "unknown")
            result.entities_by_type[entity_type] = (
                result.entities_by_type.get(entity_type, 0) + 1
            )
        result.entities_checked = len(entities)

        # Validate required fields
        field_errors = self._validate_required_fields(entities)
        result.errors.extend(field_errors)

        # Validate UIDs
        uid_errors = self._validate_uids(entities)
        result.errors.extend(uid_errors)

        # Validate IDs (per entity type)
        id_errors = self._validate_ids(entities)
        result.errors.extend(id_errors)

        # Validate parent/child/related relationships
        relationship_errors, relationship_warnings = self._validate_relationships(
            entities
        )
        result.errors.extend(relationship_errors)
        result.warnings.extend(relationship_warnings)

        # Validate status values
        status_errors = self._validate_status(entities)
        result.errors.extend(status_errors)

        # Validate entity types
        type_errors = self._validate_types(entities)
        result.errors.extend(type_errors)

        return result

    def validate_entity(
        self,
        entity_data: Dict[str, Any],
        check_relationships: bool = True,
    ) -> EntityValidationResult:
        """
        Validate a single entity (pre-flight validation).

        This method is useful for validating entity data before create/edit
        operations to catch issues early.

        Args:
            entity_data: Entity data dictionary to validate
            check_relationships: Whether to verify parent/child/related exist

        Returns:
            EntityValidationResult containing validation status and messages
        """
        result = EntityValidationResult(entity_data=entity_data)

        # Validate required fields
        for field_name in self.REQUIRED_FIELDS:
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

        # Validate relationships if requested
        if check_relationships:
            relationship_result = self._validate_entity_relationships(entity_data)
            result.errors.extend(relationship_result.errors)
            result.warnings.extend(relationship_result.warnings)
            if relationship_result.errors:
                result.valid = False

        return result

    def check_uid_unique(
        self,
        uid: str,
        exclude_file: Optional[str] = None,
    ) -> bool:
        """
        Check if a UID is unique across all entities.

        Args:
            uid: UID to check
            exclude_file: Optional file path to exclude from check (for edits)

        Returns:
            True if UID is unique, False otherwise
        """
        # Normalize exclude_file path for cross-platform comparison
        normalized_exclude = self._normalize_path(exclude_file)

        for entity_type in EntityType:
            folder_name = entity_type.get_folder_name()

            try:
                type_dir = resolve_safe_path(self.registry_path, folder_name)
            except PathSecurityError:
                continue

            if not type_dir.exists():
                continue

            for file_path in type_dir.glob("*.yml"):
                # Normalize current file path for comparison
                normalized_file_path = file_path.resolve()

                if normalized_exclude and normalized_file_path == normalized_exclude:
                    continue

                try:
                    secure_file_path = resolve_safe_path(self.registry_path, file_path)
                    with open(secure_file_path, "r") as f:
                        entity_data = yaml.safe_load(f)

                    if entity_data and entity_data.get("uid") == uid:
                        return False

                except (yaml.YAMLError, IOError, PathSecurityError):
                    continue

        return True

    def check_id_unique(
        self,
        entity_id: str,
        entity_type: EntityType,
        exclude_file: Optional[str] = None,
    ) -> bool:
        """
        Check if an ID is unique within an entity type.

        Args:
            entity_id: ID to check
            entity_type: Entity type to check within
            exclude_file: Optional file path to exclude from check (for edits)

        Returns:
            True if ID is unique within the entity type, False otherwise
        """
        folder_name = entity_type.get_folder_name()

        # Normalize exclude_file path for cross-platform comparison
        normalized_exclude = self._normalize_path(exclude_file)

        try:
            type_dir = resolve_safe_path(self.registry_path, folder_name)
        except PathSecurityError:
            return True

        if not type_dir.exists():
            return True

        for file_path in type_dir.glob("*.yml"):
            # Normalize current file path for comparison
            normalized_file_path = file_path.resolve()

            if normalized_exclude and normalized_file_path == normalized_exclude:
                continue

            try:
                secure_file_path = resolve_safe_path(self.registry_path, file_path)
                with open(secure_file_path, "r") as f:
                    entity_data = yaml.safe_load(f)

                if entity_data and entity_data.get("id") == entity_id:
                    return False

            except (yaml.YAMLError, IOError, PathSecurityError):
                continue

        return True

    def get_all_uids(self) -> Set[str]:
        """
        Get all UIDs in the registry.

        Returns:
            Set of all UIDs
        """
        uids: Set[str] = set()

        for entity_type in EntityType:
            folder_name = entity_type.get_folder_name()

            try:
                type_dir = resolve_safe_path(self.registry_path, folder_name)
            except PathSecurityError:
                continue

            if not type_dir.exists():
                continue

            for file_path in type_dir.glob("*.yml"):
                try:
                    secure_file_path = resolve_safe_path(self.registry_path, file_path)
                    with open(secure_file_path, "r") as f:
                        entity_data = yaml.safe_load(f)

                    if entity_data:
                        uid = entity_data.get("uid")
                        if uid:
                            uids.add(uid)

                except (yaml.YAMLError, IOError, PathSecurityError):
                    continue

        return uids

    def _load_all_entities(self) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Load all entities from the registry.

        Returns:
            Tuple of (entities list, load errors list)
        """
        entities: List[Dict[str, Any]] = []
        errors: List[str] = []

        for entity_type in EntityType:
            folder_name = entity_type.get_folder_name()

            try:
                type_dir = resolve_safe_path(self.registry_path, folder_name)
            except PathSecurityError as e:
                errors.append(f"Security error accessing {folder_name}: {e}")
                continue

            if not type_dir.exists():
                continue

            # Load all YAML files in the directory
            for file_path in type_dir.glob("*.yml"):
                try:
                    secure_file_path = resolve_safe_path(self.registry_path, file_path)

                    with open(secure_file_path, "r") as f:
                        entity_data = yaml.safe_load(f)

                    if entity_data is None:
                        errors.append(f"Empty file: {file_path.name}")
                        continue

                    if not isinstance(entity_data, dict):
                        errors.append(f"Invalid YAML structure in {file_path.name}")
                        continue

                    # Add file metadata
                    entity_data["_file"] = {
                        "path": str(secure_file_path),
                        "name": secure_file_path.name,
                        "type": entity_type.value,
                    }

                    entities.append(entity_data)

                except PathSecurityError as e:
                    errors.append(f"Security error with {file_path.name}: {e}")
                except yaml.YAMLError as e:
                    errors.append(f"YAML parse error in {file_path.name}: {e}")
                except Exception as e:
                    errors.append(f"Error loading {file_path.name}: {e}")

        return entities, errors

    def _validate_required_fields(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Validate that all entities have required fields"""
        errors: List[str] = []

        for entity in entities:
            file_name = entity.get("_file", {}).get("name", "unknown")

            for field_name in self.REQUIRED_FIELDS:
                if field_name not in entity or not entity[field_name]:
                    errors.append(
                        f"Missing required field '{field_name}' in {file_name}"
                    )

        return errors

    def _validate_uids(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Validate that all UIDs are unique"""
        errors: List[str] = []
        uid_map: Dict[str, List[str]] = defaultdict(list)

        # Build UID map
        for entity in entities:
            uid = entity.get("uid")
            if uid:
                file_name = entity.get("_file", {}).get("name", "unknown")
                uid_map[uid].append(file_name)

        # Check for duplicates
        for uid, files in uid_map.items():
            if len(files) > 1:
                errors.append(
                    f"Duplicate UID '{uid}' found in files: {', '.join(files)}"
                )

        return errors

    def _validate_ids(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Validate that all IDs are unique within each entity type"""
        errors: List[str] = []

        # Group entities by type
        entities_by_type: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entity in entities:
            entity_type = entity.get("type")
            if entity_type:
                entities_by_type[entity_type].append(entity)

        # Check ID uniqueness within each type
        for entity_type, type_entities in entities_by_type.items():
            id_map: Dict[str, List[str]] = defaultdict(list)

            for entity in type_entities:
                entity_id = entity.get("id")
                if entity_id:
                    file_name = entity.get("_file", {}).get("name", "unknown")
                    id_map[entity_id].append(file_name)

            # Check for duplicates within this type
            for entity_id, files in id_map.items():
                if len(files) > 1:
                    errors.append(
                        f"Duplicate ID '{entity_id}' in {entity_type} entities: {', '.join(files)}"
                    )

        return errors

    def _validate_relationships(
        self, entities: List[Dict[str, Any]]
    ) -> Tuple[List[str], List[str]]:
        """Validate parent/child and related relationships"""
        errors: List[str] = []
        warnings: List[str] = []

        # Build UID set for quick lookup
        valid_uids = {entity.get("uid") for entity in entities if entity.get("uid")}

        for entity in entities:
            file_name = entity.get("_file", {}).get("name", "unknown")

            # Check parent
            parent = entity.get("parent")
            if parent:
                if parent not in valid_uids:
                    errors.append(
                        f"Broken parent link in {file_name}: parent '{parent}' not found"
                    )

            # Check children
            children = entity.get("children", [])
            if children:
                if not isinstance(children, list):
                    errors.append(
                        f"Invalid children format in {file_name}: must be a list"
                    )
                else:
                    for child_uid in children:
                        if child_uid not in valid_uids:
                            errors.append(
                                f"Broken child link in {file_name}: child '{child_uid}' not found"
                            )

            # Check related (warnings only)
            related = entity.get("related", [])
            if related:
                if not isinstance(related, list):
                    warnings.append(
                        f"Invalid related format in {file_name}: must be a list"
                    )
                else:
                    for related_uid in related:
                        if related_uid not in valid_uids:
                            warnings.append(
                                f"Broken related link in {file_name}: related '{related_uid}' not found"
                            )

        return errors, warnings

    def _validate_entity_relationships(
        self, entity_data: Dict[str, Any]
    ) -> EntityValidationResult:
        """
        Validate relationships for a single entity against registry.

        Args:
            entity_data: Entity data to validate

        Returns:
            EntityValidationResult with relationship validation results
        """
        result = EntityValidationResult()
        valid_uids = self.get_all_uids()

        # Check parent
        parent = entity_data.get("parent")
        if parent and parent not in valid_uids:
            result.add_error(f"Parent '{parent}' not found in registry")

        # Check children
        children = entity_data.get("children", [])
        if isinstance(children, list):
            for child_uid in children:
                if child_uid not in valid_uids:
                    result.add_error(f"Child '{child_uid}' not found in registry")

        # Check related (warnings)
        related = entity_data.get("related", [])
        if isinstance(related, list):
            for related_uid in related:
                if related_uid not in valid_uids:
                    result.add_warning(f"Related '{related_uid}' not found in registry")

        return result

    def _validate_status(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Validate status values using EntityStatus enum"""
        errors: List[str] = []
        valid_statuses = EntityStatus.values()

        for entity in entities:
            status = entity.get("status")
            if status and status not in valid_statuses:
                file_name = entity.get("_file", {}).get("name", "unknown")
                errors.append(
                    f"Invalid status '{status}' in {file_name}. "
                    f"Valid values: {', '.join(valid_statuses)}"
                )

        return errors

    def _validate_types(self, entities: List[Dict[str, Any]]) -> List[str]:
        """Validate entity types match their directory using EntityType enum"""
        errors: List[str] = []
        valid_types = EntityType.values()

        for entity in entities:
            declared_type = entity.get("type")
            file_type = entity.get("_file", {}).get("type")
            file_name = entity.get("_file", {}).get("name", "unknown")

            # Check if declared type is valid
            if declared_type and declared_type not in valid_types:
                errors.append(
                    f"Invalid entity type '{declared_type}' in {file_name}. "
                    f"Valid types: {', '.join(valid_types)}"
                )

            # Check if type matches directory
            if declared_type and file_type and declared_type != file_type:
                errors.append(
                    f"Type mismatch in {file_name}: declared as '{declared_type}' "
                    f"but in '{file_type}' directory"
                )

        return errors
