"""
HoxCore Core Operations Module.

This module provides shared operation implementations that ensure behavioral
consistency between the CLI commands and MCP tools. Operations handle the
core business logic including:

- Registry initialization with git integration
- Entity creation with git integration
- Entity editing with git integration
- Entity deletion with git integration
- Entity listing with filtering and sorting
- Entity retrieval with unified lookup logic
- Property retrieval with validation and type-aware handling
- Registry validation and integrity checking
- ID uniqueness validation
- Path security enforcement
- Structured commit message generation

All operations are designed to be used by both CLI and MCP interfaces,
ensuring identical behavior regardless of the entry point.
"""

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
from hxc.core.operations.edit import (
    EditOperation,
    EditOperationError,
    InvalidValueError,
    NoChangesError,
)
from hxc.core.operations.get import (
    GetPropertyOperation,
    GetPropertyOperationError,
    IndexOutOfRangeError,
    InvalidKeyFilterError,
    KeyFilterNoMatchError,
    PropertyNotSetError,
    PropertyType,
    UnknownPropertyError,
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
from hxc.core.operations.show import EntityNotFoundError as ShowEntityNotFoundError
from hxc.core.operations.show import (
    InvalidEntityError,
    ShowOperation,
    ShowOperationError,
)
from hxc.core.operations.validate import (
    EntityValidationResult,
    ValidateOperation,
    ValidateOperationError,
    ValidationResult,
)

__all__ = [
    # Init operation
    "InitOperation",
    "InitOperationError",
    "DirectoryNotEmptyError",
    "GitOperationError",
    # Create operation
    "CreateOperation",
    "CreateOperationError",
    "DuplicateIdError",
    # Delete operation
    "DeleteOperation",
    "DeleteOperationError",
    "EntityNotFoundError",
    "AmbiguousEntityError",
    # Edit operation
    "EditOperation",
    "EditOperationError",
    "InvalidValueError",
    "NoChangesError",
    # Get property operation
    "GetPropertyOperation",
    "GetPropertyOperationError",
    "UnknownPropertyError",
    "PropertyNotSetError",
    "IndexOutOfRangeError",
    "InvalidKeyFilterError",
    "KeyFilterNoMatchError",
    "PropertyType",
    # List operation
    "ListOperation",
    "ListOperationError",
    # Show operation
    "ShowOperation",
    "ShowOperationError",
    "ShowEntityNotFoundError",
    "InvalidEntityError",
    # Validate operation
    "ValidateOperation",
    "ValidateOperationError",
    "ValidationResult",
    "EntityValidationResult",
]
