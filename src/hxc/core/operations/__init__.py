"""
HoxCore Core Operations Module.

This module provides shared operation implementations that ensure behavioral
consistency between the CLI commands and MCP tools. Operations handle the
core business logic including:

- Entity creation with git integration
- Entity editing with git integration
- Entity deletion with git integration
- Entity listing with filtering and sorting
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
from hxc.core.operations.list import (
    ListOperation,
    ListOperationError,
)

__all__ = [
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
    # List operation
    "ListOperation",
    "ListOperationError",
]
