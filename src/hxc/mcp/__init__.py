"""
MCP (Model Context Protocol) integration for HoxCore registry access.

This module provides MCP server capabilities to allow LLMs to interact with
HoxCore registries through standardized protocol interfaces.
"""

from hxc.mcp.server import MCPServer
from hxc.mcp.tools import (
    list_entities_tool,
    get_entity_tool,
    search_entities_tool,
    get_entity_property_tool,
)
from hxc.mcp.resources import (
    get_entity_resource,
    list_entities_resource,
)
from hxc.mcp.prompts import (
    get_entity_prompt,
    search_entities_prompt,
)

__all__ = [
    'MCPServer',
    'list_entities_tool',
    'get_entity_tool',
    'search_entities_tool',
    'get_entity_property_tool',
    'get_entity_resource',
    'list_entities_resource',
    'get_entity_prompt',
    'search_entities_prompt',
]