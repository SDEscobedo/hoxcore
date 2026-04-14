"""
Show Operation for HoxCore Registry.

This module provides the shared show operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Entity lookup by ID or UID (two-phase search)
- Entity data loading and validation
- Raw content retrieval
- Path security enforcement
"""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from hxc.core.enums import EntityType
from hxc.utils.path_security import PathSecurityError, resolve_safe_path


class ShowOperationError(Exception):
    """Base exception for show operation errors"""

    pass


class EntityNotFoundError(ShowOperationError):
    """Raised when an entity cannot be found"""

    def __init__(self, identifier: str, entity_type: Optional[EntityType] = None):
        self.identifier = identifier
        self.entity_type = entity_type
        type_msg = f" (type: {entity_type.value})" if entity_type else ""
        super().__init__(f"Entity not found: {identifier}{type_msg}")


class InvalidEntityError(ShowOperationError):
    """Raised when an entity file contains invalid data"""

    def __init__(self, file_path: str, reason: str):
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Invalid entity in {file_path}: {reason}")


class ShowOperation:
    """
    Shared show operation for CLI and MCP interfaces.

    This class provides the core entity retrieval logic including:
    - Two-phase entity lookup (filename optimization, then content search)
    - Entity data loading and validation
    - Raw content retrieval
    - Path security enforcement

    The two-phase search strategy ensures:
    1. Fast lookup when identifier matches UID in filename
    2. Complete search by scanning file contents for ID/UID match
    """

    def __init__(self, registry_path: str):
        """
        Initialize the show operation.

        Args:
            registry_path: Path to the registry root directory
        """
        self.registry_path = registry_path

    def find_entity_file(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[Path]:
        """
        Find an entity file by ID or UID.

        Uses a two-phase search strategy for each entity type:
        1. Fast path: Try to match identifier in filename pattern ({prefix}-{identifier}.yml)
        2. Slow path: Search file contents for ID or UID match

        The fast path optimizes for UID lookups since entity files are named
        using the UID (e.g., proj-12345678.yml).

        Args:
            identifier: ID or UID of the entity to find
            entity_type: Optional entity type to filter search. If None, searches all types.

        Returns:
            Path to the entity file if found, None otherwise

        Raises:
            PathSecurityError: If path validation fails
        """
        types_to_search = [entity_type] if entity_type else list(EntityType)

        for et in types_to_search:
            result = self._search_entity_type(identifier, et)
            if result:
                return result

        return None

    def _search_entity_type(
        self,
        identifier: str,
        entity_type: EntityType,
    ) -> Optional[Path]:
        """
        Search for an entity within a specific entity type folder.

        Args:
            identifier: ID or UID to search for
            entity_type: The entity type to search

        Returns:
            Path to the entity file if found, None otherwise

        Raises:
            PathSecurityError: If path validation fails
        """
        folder_name = entity_type.get_folder_name()
        file_prefix = entity_type.get_file_prefix()

        type_dir = resolve_safe_path(self.registry_path, folder_name)

        if not type_dir.exists():
            return None

        # Phase 1: Fast path - try direct filename match
        # Files are named {prefix}-{uid}.yml, so if identifier is a UID,
        # we can find it directly without scanning all files
        candidate_file = type_dir / f"{file_prefix}-{identifier}.yml"
        if candidate_file.exists():
            try:
                secure_path = resolve_safe_path(self.registry_path, candidate_file)
                if self._verify_entity_identifier(secure_path, identifier):
                    return secure_path
            except (yaml.YAMLError, IOError):
                pass

        # Phase 2: Slow path - search all files for ID/UID match in content
        for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
            # Skip the candidate we already checked
            if candidate_file.exists() and file_path.resolve() == candidate_file.resolve():
                continue

            try:
                secure_path = resolve_safe_path(self.registry_path, file_path)
                if self._verify_entity_identifier(secure_path, identifier):
                    return secure_path
            except (yaml.YAMLError, IOError):
                continue

        return None

    def _verify_entity_identifier(self, file_path: Path, identifier: str) -> bool:
        """
        Verify that a file contains an entity with the given identifier.

        Args:
            file_path: Path to the entity file
            identifier: ID or UID to match

        Returns:
            True if the file contains an entity matching the identifier,
            False otherwise (including for invalid YAML or empty files)
        """
        try:
            with open(file_path, "r") as f:
                content = yaml.safe_load(f)
        except (yaml.YAMLError, IOError):
            return False

        if not content or not isinstance(content, dict):
            return False

        return content.get("id") == identifier or content.get("uid") == identifier

    def load_entity(self, file_path: Path) -> Dict[str, Any]:
        """
        Load and validate entity data from a YAML file.

        Args:
            file_path: Path to the entity file

        Returns:
            Dictionary containing entity data

        Raises:
            InvalidEntityError: If the file contains invalid data
            PathSecurityError: If path validation fails
        """
        secure_path = resolve_safe_path(self.registry_path, file_path)

        try:
            with open(secure_path, "r") as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise InvalidEntityError(str(file_path), f"Invalid YAML: {e}")

        if not content:
            raise InvalidEntityError(str(file_path), "Empty file")

        if not isinstance(content, dict):
            raise InvalidEntityError(str(file_path), "Content is not a dictionary")

        # Validate required fields
        if "type" not in content:
            raise InvalidEntityError(str(file_path), "Missing 'type' field")

        if "uid" not in content:
            raise InvalidEntityError(str(file_path), "Missing 'uid' field")

        return content

    def load_raw_content(self, file_path: Path) -> str:
        """
        Load raw file content without parsing.

        Args:
            file_path: Path to the entity file

        Returns:
            Raw file content as string

        Raises:
            PathSecurityError: If path validation fails
            IOError: If file cannot be read
        """
        secure_path = resolve_safe_path(self.registry_path, file_path)

        with open(secure_path, "r") as f:
            return f.read()

    def get_entity(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
        include_raw: bool = False,
    ) -> Dict[str, Any]:
        """
        Get an entity by ID or UID.

        This is the main entry point for entity retrieval, combining
        lookup, loading, and optional raw content retrieval.

        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type to filter search
            include_raw: Whether to include raw file content in response

        Returns:
            Dictionary containing:
            - success: bool
            - entity: dict (entity data) or None
            - file_path: str (path to entity file) or None
            - identifier: str (the search identifier)
            - raw_content: str (only if include_raw=True and entity found)
            - error: str (only if success=False)
        """
        try:
            file_path = self.find_entity_file(identifier, entity_type)

            if not file_path:
                type_msg = f" (type: {entity_type.value})" if entity_type else ""
                return {
                    "success": False,
                    "error": f"Entity not found: {identifier}{type_msg}",
                    "entity": None,
                    "file_path": None,
                    "identifier": identifier,
                }

            entity_data = self.load_entity(file_path)

            result: Dict[str, Any] = {
                "success": True,
                "entity": entity_data,
                "file_path": str(file_path),
                "identifier": identifier,
            }

            if include_raw:
                result["raw_content"] = self.load_raw_content(file_path)

            return result

        except InvalidEntityError as e:
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

    def entity_exists(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> bool:
        """
        Check if an entity exists without loading its full content.

        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type to filter search

        Returns:
            True if entity exists, False otherwise
        """
        try:
            return self.find_entity_file(identifier, entity_type) is not None
        except PathSecurityError:
            return False

    def get_entity_file_path(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[str]:
        """
        Get the file path for an entity without loading its content.

        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type to filter search

        Returns:
            File path as string if found, None otherwise
        """
        try:
            file_path = self.find_entity_file(identifier, entity_type)
            return str(file_path) if file_path else None
        except PathSecurityError:
            return None