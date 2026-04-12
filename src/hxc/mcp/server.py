"""
MCP Server implementation for HoxCore Registry Access.

This module provides a Model Context Protocol (MCP) server that allows LLMs
to interact with HoxCore registries through standardized protocol interfaces.
"""

import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hxc.commands.registry import RegistryCommand
from hxc.mcp.prompts import (
    get_all_prompts,
    get_prompt_by_name,
)
from hxc.mcp.resources import (
    get_entity_hierarchy_resource,
    get_entity_resource,
    get_registry_stats_resource,
    list_entities_resource,
    search_entities_resource,
)
from hxc.mcp.tools import (
    clear_registry_path_tool,
    create_entity_tool,
    delete_entity_tool,
    discover_registry_tool,
    edit_entity_tool,
    get_entity_property_tool,
    get_entity_tool,
    get_registry_path_tool,
    init_registry_tool,
    list_entities_tool,
    list_registries_tool,
    search_entities_tool,
    set_registry_path_tool,
    validate_registry_path_tool,
)
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError


class MCPServer:
    """
    MCP Server for HoxCore Registry Access.

    This server implements the Model Context Protocol to expose HoxCore
    registry functionality to LLMs through a standardized interface.
    """

    class _DateEncoder(json.JSONEncoder):
        def default(self, obj):
            from datetime import date, datetime

            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            return super().default(obj)

    def __init__(self, registry_path: Optional[str] = None, read_only: bool = False):
        """
        Initialize the MCP server.

        Args:
            registry_path: Optional path to the registry (uses default if not provided)
            read_only: If True, only read tools are registered — write tools are omitted.
        """
        self.registry_path = self._get_registry_path(registry_path)
        self.read_only = read_only
        self._tools: Dict[str, Callable] = {}
        self._resources: Dict[str, Callable] = {}
        self._prompts: Dict[str, Dict[str, Any]] = {}

        # Register built-in tools, resources, and prompts
        self._register_tools()
        self._register_resources()
        self._register_prompts()

    def _get_registry_path(self, specified_path: Optional[str] = None) -> Optional[str]:
        """Get registry path from specified path, config, or current directory"""
        if specified_path:
            return specified_path

        registry_path = RegistryCommand.get_registry_path()
        if registry_path:
            return registry_path

        return get_project_root()

    def _register_tools(self) -> None:
        """Register all available tools. Write tools are omitted in read-only mode."""
        # Read-only tools (always available)
        self._tools = {
            "list_entities": list_entities_tool,
            "get_entity": get_entity_tool,
            "search_entities": search_entities_tool,
            "get_entity_property": get_entity_property_tool,
            # Registry management tools (read operations)
            "get_registry_path": get_registry_path_tool,
            "validate_registry_path": validate_registry_path_tool,
            "list_registries": list_registries_tool,
            "discover_registry": discover_registry_tool,
        }
        if not self.read_only:
            self._tools.update(
                {
                    "init_registry": init_registry_tool,
                    "create_entity": create_entity_tool,
                    "edit_entity": edit_entity_tool,
                    "delete_entity": delete_entity_tool,
                    # Registry management tools (write operations)
                    "set_registry_path": set_registry_path_tool,
                    "clear_registry_path": clear_registry_path_tool,
                }
            )

    def _register_resources(self) -> None:
        """Register all available resources"""
        self._resources = {
            "entity": get_entity_resource,
            "entities": list_entities_resource,
            "hierarchy": get_entity_hierarchy_resource,
            "stats": get_registry_stats_resource,
            "search": search_entities_resource,
        }

    def _register_prompts(self) -> None:
        """Register all available prompts"""
        for prompt in get_all_prompts():
            self._prompts[prompt["name"]] = prompt

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.

        Args:
            request: MCP request dictionary

        Returns:
            MCP response dictionary
        """
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "tools/list":
                result = self._handle_list_tools()
            elif method == "tools/call":
                result = self._handle_call_tool(params)
            elif method == "resources/list":
                result = self._handle_list_resources()
            elif method == "resources/read":
                result = self._handle_read_resource(params)
            elif method == "prompts/list":
                result = self._handle_list_prompts()
            elif method == "prompts/get":
                result = self._handle_get_prompt(params)
            elif method == "initialize":
                result = self._handle_initialize(params)
            else:
                return self._error_response(
                    request_id, -32601, f"Method not found: {method}"
                )

            return self._success_response(request_id, result)

        except Exception as e:
            return self._error_response(request_id, -32603, f"Internal error: {str(e)}")

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False, "listChanged": False},
                "prompts": {"listChanged": False},
            },
            "serverInfo": {"name": "hoxcore-mcp-server", "version": "0.1.0"},
        }

    def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = []

        for tool_name, tool_func in self._tools.items():
            tool_info = {
                "name": tool_name,
                "description": tool_func.__doc__ or f"Execute {tool_name}",
                "inputSchema": self._get_tool_schema(tool_name),
            }
            tools.append(tool_info)

        return {"tools": tools}

    def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Add registry path to arguments if not provided
        if "registry_path" not in arguments:
            arguments["registry_path"] = self.registry_path

        # Remap 'property' (reserved Python keyword) to 'property_name'
        if tool_name == "get_entity_property" and "property" in arguments:
            arguments["property_name"] = arguments.pop("property")

        tool_func = self._tools[tool_name]
        result = tool_func(**arguments)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        result,
                        indent=2,
                        default=lambda o: (
                            o.isoformat() if hasattr(o, "isoformat") else str(o)
                        ),
                    ),
                }
            ]
        }

    def _handle_list_resources(self) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources = []

        resource_definitions = {
            "entity": {
                "uri": "hxc://entity/{identifier}",
                "name": "Entity",
                "description": "A specific entity by ID or UID (YAML)",
                "mimeType": "application/json",
            },
            "entities": {
                "uri": "hxc://entities/{type}",
                "name": "Entities",
                "description": "All entities of a given type (JSON)",
                "mimeType": "application/json",
            },
            "hierarchy": {
                "uri": "hxc://hierarchy/{identifier}",
                "name": "Hierarchy",
                "description": "Entity hierarchy and relationships (JSON)",
                "mimeType": "application/json",
            },
            "stats": {
                "uri": "hxc://registry/stats",
                "name": "Registry Stats",
                "description": "Registry statistics and overview (JSON)",
                "mimeType": "application/json",
            },
            "search": {
                "uri": "hxc://search?q={query}",
                "name": "Search",
                "description": "Search results for a query (JSON)",
                "mimeType": "application/json",
            },
        }

        for resource_name in self._resources:
            if resource_name in resource_definitions:
                resources.append(resource_definitions[resource_name])

        return {"resources": resources}

    def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get("uri", "")

        result = None
        content_uri = uri

        if uri.startswith("hxc://entity/"):
            identifier = uri[len("hxc://entity/") :]
            resource_func = self._resources.get("entity")
            if resource_func:
                result = resource_func(identifier, registry_path=self.registry_path)

        elif uri.startswith("hxc://entities/"):
            entity_type = uri[len("hxc://entities/") :]
            resource_func = self._resources.get("entities")
            if resource_func:
                result = resource_func(entity_type, registry_path=self.registry_path)

        elif uri.startswith("hxc://hierarchy/"):
            identifier = uri[len("hxc://hierarchy/") :]
            resource_func = self._resources.get("hierarchy")
            if resource_func:
                result = resource_func(identifier, registry_path=self.registry_path)

        elif uri == "hxc://registry/stats":
            resource_func = self._resources.get("stats")
            if resource_func:
                result = resource_func(registry_path=self.registry_path)

        elif uri.startswith("hxc://search"):
            query = ""
            if "?q=" in uri:
                query = uri.split("?q=")[1]
            resource_func = self._resources.get("search")
            if resource_func:
                result = resource_func(query, registry_path=self.registry_path)

        if result is None:
            raise ValueError(f"Resource not found: {uri}")

        content_text = json.dumps(
            result["content"],
            indent=2,
            default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o),
        )

        return {
            "contents": [
                {
                    "uri": content_uri,
                    "mimeType": result.get("mimeType", "application/json"),
                    "text": content_text,
                }
            ]
        }

    def _handle_list_prompts(self) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts = []
        for prompt_name, prompt_data in self._prompts.items():
            prompts.append(prompt_data)
        return {"prompts": prompts}

    def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})

        if prompt_name not in self._prompts:
            raise ValueError(f"Unknown prompt: {prompt_name}")

        prompt_data = self._prompts[prompt_name]

        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": self._format_prompt_message(prompt_data, arguments),
                },
            }
        ]

        return {
            "description": prompt_data.get("description", ""),
            "messages": messages,
        }

    def _format_prompt_message(
        self,
        prompt_data: Dict[str, Any],
        arguments: Dict[str, Any],
    ) -> str:
        """Format a prompt message with the supplied arguments."""
        lines = [prompt_data.get("description", "")]

        if arguments:
            lines.append("\nArguments:")
            for key, value in arguments.items():
                lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    def _get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get JSON schema for a tool's input parameters"""
        schemas = {
            "init_registry": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path where to initialize the registry. Must be an empty directory or a path that doesn't exist yet.",
                    },
                    "use_git": {
                        "type": "boolean",
                        "description": "Whether to initialize a git repository (default: true)",
                    },
                    "commit": {
                        "type": "boolean",
                        "description": "Whether to create initial commit (default: true, requires use_git)",
                    },
                    "remote_url": {
                        "type": "string",
                        "description": "Optional git remote URL to configure as 'origin'",
                    },
                    "set_default": {
                        "type": "boolean",
                        "description": "Whether to set this registry as the default in config (default: true)",
                    },
                },
                "required": ["path"],
            },
            "list_entities": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "description": "Type of entity (program, project, mission, action, all)",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by status (active, completed, on-hold, cancelled, planned, any)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags (AND logic - entity must have ALL specified tags)",
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category (exact match)",
                    },
                    "parent": {
                        "type": "string",
                        "description": "Filter by parent ID (exact match)",
                    },
                    "identifier": {
                        "type": "string",
                        "description": "Filter by ID or UID (exact match)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Text search in title and description (case-insensitive)",
                    },
                    "due_before": {
                        "type": "string",
                        "description": "Filter by due date before YYYY-MM-DD (inclusive)",
                    },
                    "due_after": {
                        "type": "string",
                        "description": "Filter by due date after YYYY-MM-DD (inclusive)",
                    },
                    "max_items": {
                        "type": "integer",
                        "description": "Maximum items to return (0 = all)",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort field (title, id, due_date, status, created, modified)",
                    },
                    "descending": {
                        "type": "boolean",
                        "description": "Sort in descending order",
                    },
                    "include_file_metadata": {
                        "type": "boolean",
                        "description": "Include file metadata (_file field with path, created, modified)",
                    },
                },
            },
            "get_entity": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "ID or UID of the entity",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Optional type filter",
                    },
                },
                "required": ["identifier"],
            },
            "search_entities": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "entity_type": {
                        "type": "string",
                        "description": "Optional type filter",
                    },
                    "status": {
                        "type": "string",
                        "description": "Optional status filter",
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "max_items": {"type": "integer"},
                },
                "required": ["query"],
            },
            "get_entity_property": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "ID or UID of the entity",
                    },
                    "property": {
                        "type": "string",
                        "description": "Property name to retrieve",
                    },
                    "entity_type": {"type": "string"},
                    "index": {"type": "integer"},
                    "key": {"type": "string"},
                },
                "required": ["identifier", "property"],
            },
            "create_entity": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "description": "Entity type: program | project | mission | action",
                    },
                    "title": {"type": "string", "description": "Human-readable title"},
                    "description": {"type": "string"},
                    "status": {
                        "type": "string",
                        "description": "Initial status (default: active)",
                    },
                    "id": {
                        "type": "string",
                        "description": "Optional custom human-readable ID (e.g. P-042). Must be unique within entity type.",
                    },
                    "category": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "parent": {
                        "type": "string",
                        "description": "Parent entity UID or ID",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "YYYY-MM-DD (default: today)",
                    },
                    "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "use_git": {
                        "type": "boolean",
                        "description": "Whether to commit the change to git (default: true). Set false to skip git operations.",
                    },
                },
                "required": ["type", "title"],
            },
            "edit_entity": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "UID or human-readable ID of the entity to edit",
                    },
                    "set_title": {
                        "type": "string",
                        "description": "New title value",
                    },
                    "set_description": {
                        "type": "string",
                        "description": "New description value",
                    },
                    "set_status": {
                        "type": "string",
                        "description": "New status value (active, completed, on-hold, cancelled, planned)",
                    },
                    "set_id": {
                        "type": "string",
                        "description": "New human-readable ID. Must be unique within entity type.",
                    },
                    "set_category": {
                        "type": "string",
                        "description": "New category path",
                    },
                    "set_parent": {
                        "type": "string",
                        "description": "New parent UID or ID",
                    },
                    "set_start_date": {
                        "type": "string",
                        "description": "New start date (YYYY-MM-DD)",
                    },
                    "set_due_date": {
                        "type": "string",
                        "description": "New due date (YYYY-MM-DD)",
                    },
                    "set_completion_date": {
                        "type": "string",
                        "description": "New completion date (YYYY-MM-DD)",
                    },
                    "add_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to add (idempotent - duplicates ignored)",
                    },
                    "remove_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags to remove (silently ignores missing)",
                    },
                    "add_children": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Child entity UIDs/IDs to add",
                    },
                    "remove_children": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Child entity UIDs/IDs to remove",
                    },
                    "add_related": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related entity UIDs/IDs to add",
                    },
                    "remove_related": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related entity UIDs/IDs to remove",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Optional type filter to disambiguate the identifier (program, project, mission, action)",
                    },
                    "use_git": {
                        "type": "boolean",
                        "description": "Whether to commit the change to git (default: true). Set false to skip git operations.",
                    },
                },
                "required": ["identifier"],
            },
            "delete_entity": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "UID or human-readable ID",
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Set True to confirm deletion (default: False returns a confirmation prompt)",
                    },
                    "entity_type": {"type": "string"},
                    "use_git": {
                        "type": "boolean",
                        "description": "Whether to commit the deletion to git (default: true). Set false to skip git operations.",
                    },
                },
                "required": ["identifier"],
            },
            # Registry management tools
            "get_registry_path": {
                "type": "object",
                "properties": {
                    "include_discovery": {
                        "type": "boolean",
                        "description": "Whether to attempt auto-discovery if not configured (default: true)",
                    },
                },
            },
            "set_registry_path": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to set as the default registry",
                    },
                    "validate": {
                        "type": "boolean",
                        "description": "Whether to validate the path before setting (default: true)",
                    },
                },
                "required": ["path"],
            },
            "validate_registry_path": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to validate as a HoxCore registry",
                    },
                },
                "required": ["path"],
            },
            "list_registries": {
                "type": "object",
                "properties": {},
            },
            "discover_registry": {
                "type": "object",
                "properties": {},
            },
            "clear_registry_path": {
                "type": "object",
                "properties": {},
            },
        }
        return schemas.get(tool_name, {"type": "object", "properties": {}})

    def _success_response(
        self, request_id: Any, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error_response(
        self, request_id: Any, code: int, message: str
    ) -> Dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }

    def run_stdio(self) -> None:
        """
        Run the MCP server using stdio transport.

        This method reads JSON-RPC requests from stdin and writes responses to stdout.
        """

        def _json_dumps(obj):
            return json.dumps(
                obj,
                default=lambda o: o.isoformat() if hasattr(o, "isoformat") else str(o),
            )

        try:
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    print(_json_dumps(response), flush=True)
                except json.JSONDecodeError as e:
                    error_response = self._error_response(
                        None, -32700, f"Parse error: {str(e)}"
                    )
                    print(_json_dumps(error_response), flush=True)
                except Exception as e:
                    error_response = self._error_response(
                        None, -32603, f"Internal error: {str(e)}"
                    )
                    print(_json_dumps(error_response), flush=True)

        except KeyboardInterrupt:
            pass

    def get_capabilities(self) -> Dict[str, Any]:
        """
        Get server capabilities.

        Returns:
            Dictionary describing server capabilities
        """
        return {
            "tools": list(self._tools.keys()),
            "resources": list(self._resources.keys()),
            "prompts": list(self._prompts.keys()),
            "registry_path": self.registry_path,
            "read_only": self.read_only,
        }

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a custom tool."""
        self._tools[name] = func

    def register_resource(self, name: str, func: Callable) -> None:
        """Register a custom resource."""
        self._resources[name] = func

    def register_prompt(self, prompt_data: Dict[str, Any]) -> None:
        """Register a custom prompt."""
        name = prompt_data.get("name")
        if not name:
            raise ValueError("Prompt must have a name")
        self._prompts[name] = prompt_data


def create_server(
    registry_path: Optional[str] = None, read_only: bool = False
) -> MCPServer:
    """
    Create and configure an MCP server instance.

    Args:
        registry_path: Optional path to the registry
        read_only: If True, only read tools are registered.

    Returns:
        Configured MCPServer instance
    """
    return MCPServer(registry_path=registry_path, read_only=read_only)


def main() -> int:
    """
    Main entry point for running the MCP server.

    Returns:
        Exit code
    """
    import argparse

    parser = argparse.ArgumentParser(description="HoxCore MCP Server")
    parser.add_argument(
        "--registry",
        help="Path to the registry (defaults to current or configured registry)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Start in read-only mode: omit write tools (init_registry, create_entity, edit_entity, delete_entity, set_registry_path, clear_registry_path)",
    )

    args = parser.parse_args()

    try:
        server = create_server(registry_path=args.registry, read_only=args.read_only)

        if not server.registry_path:
            print(
                "Error: No registry found. Please specify with --registry or initialize one.",
                file=sys.stderr,
            )
            return 1

        if args.transport == "stdio":
            server.run_stdio()

        return 0

    except Exception as e:
        print(f"Error starting MCP server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
