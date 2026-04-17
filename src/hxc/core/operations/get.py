"""
Get Property Operation for HoxCore Registry.

This module provides the shared get property operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Property name validation against canonical property sets
- Property classification (scalar, list, complex, special)
- Type-aware property retrieval
- Index and key filter operations for list/complex properties
- Entity lookup via ShowOperation
- Path security enforcement
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from hxc.core.enums import EntityType
from hxc.core.operations.show import ShowOperation, ShowOperationError
from hxc.utils.path_security import PathSecurityError


class GetPropertyOperationError(Exception):
    """Base exception for get property operation errors"""

    pass


class UnknownPropertyError(GetPropertyOperationError):
    """Raised when property name is not in the known property set"""

    def __init__(self, property_name: str, available_properties: List[str]):
        self.property_name = property_name
        self.available_properties = available_properties
        super().__init__(
            f"Unknown property '{property_name}'. "
            f"Available properties: {', '.join(sorted(available_properties))}"
        )


class PropertyNotSetError(GetPropertyOperationError):
    """Raised when a valid property is not set (None or missing)"""

    def __init__(self, property_name: str):
        self.property_name = property_name
        super().__init__(f"Property '{property_name}' is not set")


class IndexOutOfRangeError(GetPropertyOperationError):
    """Raised when index is out of range for a list property"""

    def __init__(self, index: int, list_length: int):
        self.index = index
        self.list_length = list_length
        super().__init__(
            f"Index {index} out of range (list has {list_length} items)"
        )


class InvalidKeyFilterError(GetPropertyOperationError):
    """Raised when key filter format is invalid"""

    def __init__(self, key_filter: str):
        self.key_filter = key_filter
        super().__init__(
            f"Invalid key filter format '{key_filter}'. Use key:value (e.g., name:github)"
        )


class KeyFilterNoMatchError(GetPropertyOperationError):
    """Raised when key filter matches no items"""

    def __init__(self, filter_key: str, filter_value: str):
        self.filter_key = filter_key
        self.filter_value = filter_value
        super().__init__(f"No items found with {filter_key}='{filter_value}'")


class PropertyType:
    """Property type constants"""

    SCALAR = "scalar"
    LIST = "list"
    COMPLEX = "complex"
    SPECIAL = "special"


class GetPropertyOperation:
    """
    Shared get property operation for CLI and MCP interfaces.

    This class provides the core property retrieval logic including:
    - Property name validation against canonical property sets
    - Property classification (scalar, list, complex, special)
    - Type-aware property retrieval
    - Index and key filter operations
    - Entity lookup delegation to ShowOperation
    - Path security enforcement

    Property Categories:
    - SCALAR: Simple single-value properties (type, uid, id, title, etc.)
    - LIST: Simple list properties (tags, children, related)
    - COMPLEX: List of dictionaries (repositories, storage, databases, etc.)
    - SPECIAL: Computed/meta properties (all, path)
    """

    # Define all accessible properties with explicit classification
    SCALAR_PROPERTIES: Set[str] = {
        "type",
        "uid",
        "id",
        "title",
        "description",
        "status",
        "start_date",
        "due_date",
        "completion_date",
        "duration_estimate",
        "category",
        "parent",
        "template",
    }

    LIST_PROPERTIES: Set[str] = {"tags", "children", "related"}

    COMPLEX_PROPERTIES: Set[str] = {
        "repositories",
        "storage",
        "databases",
        "tools",
        "models",
        "knowledge_bases",
    }

    SPECIAL_PROPERTIES: Set[str] = {
        "all",  # Get all properties
        "path",  # Get file path
    }

    ALL_PROPERTIES: Set[str] = (
        SCALAR_PROPERTIES | LIST_PROPERTIES | COMPLEX_PROPERTIES | SPECIAL_PROPERTIES
    )

    def __init__(self, registry_path: str):
        """
        Initialize the get property operation.

        Args:
            registry_path: Path to the registry root directory
        """
        self.registry_path = registry_path
        self._show_operation = ShowOperation(registry_path)

    @classmethod
    def get_property_type(cls, property_name: str) -> Optional[str]:
        """
        Get the type classification for a property name.

        Args:
            property_name: Name of the property

        Returns:
            Property type constant (SCALAR, LIST, COMPLEX, SPECIAL) or None if unknown
        """
        property_lower = property_name.lower()

        if property_lower in cls.SCALAR_PROPERTIES:
            return PropertyType.SCALAR
        elif property_lower in cls.LIST_PROPERTIES:
            return PropertyType.LIST
        elif property_lower in cls.COMPLEX_PROPERTIES:
            return PropertyType.COMPLEX
        elif property_lower in cls.SPECIAL_PROPERTIES:
            return PropertyType.SPECIAL
        else:
            return None

    @classmethod
    def validate_property_name(cls, property_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that a property name is known.

        Args:
            property_name: Name of the property to validate

        Returns:
            Tuple of (is_valid, normalized_property_name)
            If invalid, normalized_property_name is None
        """
        property_lower = property_name.lower()

        if property_lower in cls.ALL_PROPERTIES:
            return True, property_lower

        return False, None

    @classmethod
    def get_available_properties(cls) -> List[str]:
        """
        Get list of all available property names.

        Returns:
            Sorted list of all valid property names
        """
        return sorted(cls.ALL_PROPERTIES)

    @classmethod
    def get_properties_by_type(cls) -> Dict[str, List[str]]:
        """
        Get properties grouped by their type classification.

        Returns:
            Dictionary with property types as keys and lists of property names as values
        """
        return {
            PropertyType.SCALAR: sorted(cls.SCALAR_PROPERTIES),
            PropertyType.LIST: sorted(cls.LIST_PROPERTIES),
            PropertyType.COMPLEX: sorted(cls.COMPLEX_PROPERTIES),
            PropertyType.SPECIAL: sorted(cls.SPECIAL_PROPERTIES),
        }

    def get_entity(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Dict[str, Any]:
        """
        Get an entity by ID or UID using ShowOperation.

        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type to filter search

        Returns:
            Dictionary containing entity data and metadata from ShowOperation
        """
        return self._show_operation.get_entity(
            identifier=identifier,
            entity_type=entity_type,
            include_raw=False,
        )

    def get_property(
        self,
        identifier: str,
        property_name: str,
        entity_type: Optional[EntityType] = None,
        index: Optional[int] = None,
        key_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific property value from an entity.

        This is the main entry point for property retrieval, handling:
        - Property name validation
        - Entity lookup
        - Property type-aware value retrieval
        - Index and key filter operations

        Args:
            identifier: ID or UID of the entity
            property_name: Name of the property to retrieve
            entity_type: Optional entity type to filter search
            index: Optional index for list/complex properties
            key_filter: Optional key:value filter for complex properties

        Returns:
            Dictionary containing:
            - success: bool
            - value: Any (property value)
            - property: str (normalized property name)
            - property_type: str (scalar, list, complex, special)
            - identifier: str
            - file_path: str (only for 'path' property or included in entity lookup)
            - error: str (only if success=False)
            - available_properties: list (only if unknown property error)

        Raises:
            UnknownPropertyError: If property name is not recognized
            PropertyNotSetError: If property exists but is not set
            IndexOutOfRangeError: If index is out of range
            InvalidKeyFilterError: If key filter format is invalid
            KeyFilterNoMatchError: If key filter matches no items
        """
        # Normalize property name
        property_lower = property_name.lower()

        # Validate property name
        is_valid, normalized_name = self.validate_property_name(property_lower)
        if not is_valid:
            return {
                "success": False,
                "error": f"Unknown property '{property_name}'. "
                f"Available properties: {', '.join(sorted(self.ALL_PROPERTIES))}",
                "property": property_name,
                "property_type": None,
                "value": None,
                "identifier": identifier,
                "available_properties": self.get_available_properties(),
            }

        property_type = self.get_property_type(normalized_name)

        # Get entity data
        entity_result = self.get_entity(identifier, entity_type)

        if not entity_result["success"]:
            return {
                "success": False,
                "error": entity_result.get("error", f"Entity not found: {identifier}"),
                "property": normalized_name,
                "property_type": property_type,
                "value": None,
                "identifier": identifier,
            }

        entity_data = entity_result["entity"]
        file_path = entity_result["file_path"]

        # Handle special properties
        if normalized_name == "path":
            return {
                "success": True,
                "property": normalized_name,
                "property_type": PropertyType.SPECIAL,
                "value": file_path,
                "identifier": identifier,
            }

        if normalized_name == "all":
            return {
                "success": True,
                "property": normalized_name,
                "property_type": PropertyType.SPECIAL,
                "value": entity_data,
                "identifier": identifier,
            }

        # Get property value
        value = entity_data.get(normalized_name)

        # Check if property is set
        if value is None:
            return {
                "success": False,
                "error": f"Property '{normalized_name}' is not set",
                "property": normalized_name,
                "property_type": property_type,
                "value": None,
                "identifier": identifier,
            }

        # Handle list properties with index
        if property_type == PropertyType.LIST and isinstance(value, list):
            value, error = self._apply_index_filter(value, index, normalized_name)
            if error:
                return {
                    "success": False,
                    "error": error,
                    "property": normalized_name,
                    "property_type": property_type,
                    "value": None,
                    "identifier": identifier,
                }

        # Handle complex properties with index and key filter
        if property_type == PropertyType.COMPLEX and isinstance(value, list):
            # Apply key filter first if provided
            if key_filter:
                value, error = self._apply_key_filter(value, key_filter, normalized_name)
                if error:
                    return {
                        "success": False,
                        "error": error,
                        "property": normalized_name,
                        "property_type": property_type,
                        "value": None,
                        "identifier": identifier,
                    }
            # Then apply index if provided (and key filter wasn't used or returned list)
            elif index is not None:
                value, error = self._apply_index_filter(value, index, normalized_name)
                if error:
                    return {
                        "success": False,
                        "error": error,
                        "property": normalized_name,
                        "property_type": property_type,
                        "value": None,
                        "identifier": identifier,
                    }

        return {
            "success": True,
            "property": normalized_name,
            "property_type": property_type,
            "value": value,
            "identifier": identifier,
        }

    def _apply_index_filter(
        self,
        value: List[Any],
        index: Optional[int],
        property_name: str,
    ) -> Tuple[Any, Optional[str]]:
        """
        Apply index filter to a list value.

        Args:
            value: List value to filter
            index: Index to retrieve (None to skip)
            property_name: Property name for error messages

        Returns:
            Tuple of (filtered_value, error_message)
            If error_message is not None, filtered_value should be ignored
        """
        if index is None:
            return value, None

        if not isinstance(value, list):
            return value, None

        if 0 <= index < len(value):
            return value[index], None
        else:
            return None, f"Index {index} out of range (list has {len(value)} items)"

    def _apply_key_filter(
        self,
        value: List[Any],
        key_filter: str,
        property_name: str,
    ) -> Tuple[Any, Optional[str]]:
        """
        Apply key:value filter to a list of dictionaries.

        Args:
            value: List of dictionaries to filter
            key_filter: Filter string in format "key:value"
            property_name: Property name for error messages

        Returns:
            Tuple of (filtered_value, error_message)
            If error_message is not None, filtered_value should be ignored
        """
        if not isinstance(value, list):
            return value, None

        # Parse key:value filter
        if ":" not in key_filter:
            return None, f"Invalid key filter format '{key_filter}'. Use key:value (e.g., name:github)"

        filter_key, filter_value = key_filter.split(":", 1)

        filtered = [
            item
            for item in value
            if isinstance(item, dict) and item.get(filter_key) == filter_value
        ]

        if not filtered:
            return None, f"No items found with {filter_key}='{filter_value}'"

        # If only one item matches, return it directly
        if len(filtered) == 1:
            return filtered[0], None

        return filtered, None

    def get_entity_file_path(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> Optional[str]:
        """
        Get the file path for an entity without loading all properties.

        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type to filter search

        Returns:
            File path as string if found, None otherwise
        """
        return self._show_operation.get_entity_file_path(identifier, entity_type)

    def entity_exists(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
    ) -> bool:
        """
        Check if an entity exists.

        Args:
            identifier: ID or UID of the entity
            entity_type: Optional entity type to filter search

        Returns:
            True if entity exists, False otherwise
        """
        return self._show_operation.entity_exists(identifier, entity_type)