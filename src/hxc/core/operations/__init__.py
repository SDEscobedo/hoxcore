"""
HoxCore Core Operations Module.

This module provides shared operation implementations that ensure behavioral
consistency between the CLI commands and MCP tools. Operations handle the
core business logic including:

- Entity creation with git integration
- ID uniqueness validation
- Path security enforcement
- Structured commit message generation

All operations are designed to be used by both CLI and MCP interfaces,
ensuring identical behavior regardless of the entry point.
"""

from hxc.core.operations.create import CreateOperation


__all__ = [
    "CreateOperation",
]