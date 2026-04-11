"""
MCP (Model Context Protocol) integration for HoxCore registry access.

This module provides MCP server capabilities to allow LLMs to interact with
HoxCore registries through standardized protocol interfaces.
"""

from hxc.mcp.prompts import (
    get_entity_prompt,
    search_entities_prompt,
)
from hxc.mcp.resources import (
    get_entity_resource,
    list_entities_resource,
)
from hxc.mcp.server import MCPServer
from hxc.mcp.tools import (
    create_entity_tool,
    delete_entity_tool,
    edit_entity_tool,
    get_entity_property_tool,
    get_entity_tool,
    list_entities_tool,
    search_entities_tool,
)

__all__ = [
    "MCPServer",
    # Read tools
    "list_entities_tool",
    "get_entity_tool",
    "search_entities_tool",
    "get_entity_property_tool",
    # Write tools
    "create_entity_tool",
    "edit_entity_tool",
    "delete_entity_tool",
    # Resources
    "get_entity_resource",
    "list_entities_resource",
    # Prompts
    "get_entity_prompt",
    "search_entities_prompt",
]
