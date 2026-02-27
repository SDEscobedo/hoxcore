"""
MCP Server implementation for HoxCore Registry Access.

This module provides a Model Context Protocol (MCP) server that allows LLMs
to interact with HoxCore registries through standardized protocol interfaces.
"""
import json
import sys
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError
from hxc.mcp.tools import (
    list_entities_tool,
    get_entity_tool,
    search_entities_tool,
    get_entity_property_tool,
)
from hxc.mcp.resources import (
    get_entity_resource,
    list_entities_resource,
    get_entity_hierarchy_resource,
    get_registry_stats_resource,
    search_entities_resource,
)
from hxc.mcp.prompts import (
    get_all_prompts,
    get_prompt_by_name,
)





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
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize the MCP server.
        
        Args:
            registry_path: Optional path to the registry (uses default if not provided)
        """
        self.registry_path = self._get_registry_path(registry_path)
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
        """Register all available tools"""
        self._tools = {
            "list_entities": list_entities_tool,
            "get_entity": get_entity_tool,
            "search_entities": search_entities_tool,
            "get_entity_property": get_entity_property_tool,
        }
    
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
            self._prompts[prompt['name']] = prompt
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP request.
        
        Args:
            request: MCP request dictionary
            
        Returns:
            MCP response dictionary
        """
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        try:
            if method == 'tools/list':
                result = self._handle_list_tools()
            elif method == 'tools/call':
                result = self._handle_call_tool(params)
            elif method == 'resources/list':
                result = self._handle_list_resources()
            elif method == 'resources/read':
                result = self._handle_read_resource(params)
            elif method == 'prompts/list':
                result = self._handle_list_prompts()
            elif method == 'prompts/get':
                result = self._handle_get_prompt(params)
            elif method == 'initialize':
                result = self._handle_initialize(params)
            else:
                return self._error_response(
                    request_id,
                    -32601,
                    f"Method not found: {method}"
                )
            
            return self._success_response(request_id, result)
        
        except Exception as e:
            return self._error_response(
                request_id,
                -32603,
                f"Internal error: {str(e)}"
            )
    
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialization request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {
                    "listChanged": False
                },
                "resources": {
                    "subscribe": False,
                    "listChanged": False
                },
                "prompts": {
                    "listChanged": False
                }
            },
            "serverInfo": {
                "name": "hoxcore-mcp-server",
                "version": "0.1.0"
            }
        }
    
    def _handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        tools = []
        
        for tool_name, tool_func in self._tools.items():
            tool_info = {
                "name": tool_name,
                "description": tool_func.__doc__ or f"Execute {tool_name}",
                "inputSchema": self._get_tool_schema(tool_name)
            }
            tools.append(tool_info)
        
        return {"tools": tools}
    
    def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        tool_name = params.get('name')
        arguments = params.get('arguments', {})

        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Add registry path to arguments if not provided
        if 'registry_path' not in arguments:
            arguments['registry_path'] = self.registry_path

        # Remap 'property' (reserved Python keyword) to 'property_name'
        if tool_name == 'get_entity_property' and 'property' in arguments:
            arguments['property_name'] = arguments.pop('property')

        tool_func = self._tools[tool_name]
        result = tool_func(**arguments)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o))
                }
            ]
        }
    
    def _handle_list_resources(self) -> Dict[str, Any]:
        """Handle resources/list request"""
        resources = []
        
        # Add static resource templates
        resource_templates = [
            {
                "uri": "hxc://entity/{identifier}",
                "name": "Entity Resource",
                "description": "Access a specific entity by ID or UID",
                "mimeType": "application/x-yaml"
            },
            {
                "uri": "hxc://entities/{type}",
                "name": "Entity List Resource",
                "description": "List entities of a specific type",
                "mimeType": "application/json"
            },
            {
                "uri": "hxc://hierarchy/{identifier}",
                "name": "Entity Hierarchy Resource",
                "description": "Access entity hierarchy and relationships",
                "mimeType": "application/json"
            },
            {
                "uri": "hxc://registry/stats",
                "name": "Registry Statistics Resource",
                "description": "Access registry statistics and overview",
                "mimeType": "application/json"
            },
            {
                "uri": "hxc://search?q={query}",
                "name": "Search Resource",
                "description": "Search entities by query",
                "mimeType": "application/json"
            }
        ]
        
        resources.extend(resource_templates)
        
        return {"resources": resources}
    
    def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request"""
        uri = params.get('uri')

        if not uri or not uri.startswith('hxc://'):
            raise ValueError(f"Invalid resource URI: {uri}")

        # Strip scheme and split path from query string first
        uri_without_scheme = uri.replace('hxc://', '')
        path_part, _, query_string = uri_without_scheme.partition('?')
        uri_parts = path_part.split('/') if path_part else []
        resource_type = uri_parts[0] if uri_parts else None

        if resource_type == 'entity':
            identifier = uri_parts[1] if len(uri_parts) > 1 else None
            if not identifier:
                raise ValueError("Entity identifier required")
            resource = get_entity_resource(identifier, registry_path=self.registry_path)

        elif resource_type == 'entities':
            entity_type = uri_parts[1] if len(uri_parts) > 1 else 'all'
            resource = list_entities_resource(
                entity_type=entity_type,
                registry_path=self.registry_path
            )

        elif resource_type == 'hierarchy':
            identifier = uri_parts[1] if len(uri_parts) > 1 else None
            if not identifier:
                raise ValueError("Entity identifier required")
            resource = get_entity_hierarchy_resource(
                identifier,
                registry_path=self.registry_path
            )

        elif resource_type == 'registry' and len(uri_parts) > 1 and uri_parts[1] == 'stats':
            resource = get_registry_stats_resource(registry_path=self.registry_path)

        elif resource_type == 'search':
            query_part = ''
            for param in query_string.split('&'):
                if param.startswith('q='):
                    query_part = param[2:]
                    break
            if not query_part:
                raise ValueError("Search query required")
            resource = search_entities_resource(
                query=query_part,
                registry_path=self.registry_path
            )

        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

        content_text = json.dumps(resource['content'], indent=2, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o))

        return {
            "contents": [
                {
                    "uri": uri,
                    "mimeType": resource.get('mimeType', 'application/json'),
                    "text": content_text
                }
            ]
        }
    
    def _handle_list_prompts(self) -> Dict[str, Any]:
        """Handle prompts/list request"""
        prompts = []
        
        for prompt_name, prompt_data in self._prompts.items():
            prompt_info = {
                "name": prompt_name,
                "description": prompt_data.get('description', ''),
                "arguments": prompt_data.get('arguments', [])
            }
            prompts.append(prompt_info)
        
        return {"prompts": prompts}
    
    def _handle_get_prompt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle prompts/get request"""
        prompt_name = params.get('name')
        arguments = params.get('arguments', {})
        
        if prompt_name not in self._prompts:
            raise ValueError(f"Unknown prompt: {prompt_name}")
        
        prompt_data = self._prompts[prompt_name]
        
        # Build prompt message
        messages = [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": self._format_prompt_message(prompt_data, arguments)
                }
            }
        ]
        
        return {
            "description": prompt_data.get('description', ''),
            "messages": messages
        }
    
    def _format_prompt_message(
        self,
        prompt_data: Dict[str, Any],
        arguments: Dict[str, Any]
    ) -> str:
        """Format a prompt message with arguments"""
        lines = [prompt_data.get('description', '')]
        
        if arguments:
            lines.append("\nArguments:")
            for key, value in arguments.items():
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    def _get_tool_schema(self, tool_name: str) -> Dict[str, Any]:
        """Get JSON schema for a tool's input parameters"""
        schemas = {
            "list_entities": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["program", "project", "mission", "action", "all"],
                        "default": "all",
                        "description": "Type of entities to list"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "completed", "on-hold", "cancelled", "planned", "any"],
                        "description": "Filter by status"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    },
                    "parent": {
                        "type": "string",
                        "description": "Filter by parent ID"
                    },
                    "max_items": {
                        "type": "integer",
                        "default": 0,
                        "description": "Maximum number of items (0 for all)"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["title", "id", "due_date", "status", "created", "modified"],
                        "default": "title",
                        "description": "Sort field"
                    },
                    "descending": {
                        "type": "boolean",
                        "default": False,
                        "description": "Sort in descending order"
                    }
                }
            },
            "get_entity": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "ID or UID of the entity"
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["program", "project", "mission", "action"],
                        "description": "Entity type (optional if identifier is unique)"
                    }
                },
                "required": ["identifier"]
            },
            "search_entities": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for title and description"
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["program", "project", "mission", "action", "all"],
                        "default": "all",
                        "description": "Type of entities to search"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["active", "completed", "on-hold", "cancelled", "planned", "any"],
                        "description": "Filter by status"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags"
                    },
                    "category": {
                        "type": "string",
                        "description": "Filter by category"
                    },
                    "max_items": {
                        "type": "integer",
                        "default": 0,
                        "description": "Maximum number of items (0 for all)"
                    }
                },
                "required": ["query"]
            },
            "get_entity_property": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "description": "ID or UID of the entity"
                    },
                    "property": {
                        "type": "string",
                        "description": "Property name to retrieve"
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": ["program", "project", "mission", "action"],
                        "description": "Entity type (optional if identifier is unique)"
                    },
                    "index": {
                        "type": "integer",
                        "description": "For list properties, get item at specific index"
                    },
                    "key": {
                        "type": "string",
                        "description": "For complex properties, filter by key:value"
                    }
                },
                "required": ["identifier", "property"]
            }
        }
        
        return schemas.get(tool_name, {"type": "object"})
    
    def _success_response(self, request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a successful JSON-RPC response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        """Create an error JSON-RPC response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    def run_stdio(self) -> None:
        """
        Run the MCP server using stdio transport.

        This method reads JSON-RPC requests from stdin and writes responses to stdout.
        """
        def _json_dumps(obj):
            return json.dumps(obj, default=lambda o: o.isoformat() if hasattr(o, 'isoformat') else str(o))

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
                        None,
                        -32700,
                        f"Parse error: {str(e)}"
                    )
                    print(_json_dumps(error_response), flush=True)
                except Exception as e:
                    error_response = self._error_response(
                        None,
                        -32603,
                        f"Internal error: {str(e)}"
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
            "registry_path": self.registry_path
        }
    
    def register_tool(self, name: str, func: Callable) -> None:
        """
        Register a custom tool.
        
        Args:
            name: Tool name
            func: Tool function
        """
        self._tools[name] = func
    
    def register_resource(self, name: str, func: Callable) -> None:
        """
        Register a custom resource.
        
        Args:
            name: Resource name
            func: Resource function
        """
        self._resources[name] = func
    
    def register_prompt(self, prompt_data: Dict[str, Any]) -> None:
        """
        Register a custom prompt.
        
        Args:
            prompt_data: Prompt definition dictionary
        """
        name = prompt_data.get('name')
        if not name:
            raise ValueError("Prompt must have a name")
        self._prompts[name] = prompt_data


def create_server(registry_path: Optional[str] = None) -> MCPServer:
    """
    Create and configure an MCP server instance.
    
    Args:
        registry_path: Optional path to the registry
        
    Returns:
        Configured MCPServer instance
    """
    return MCPServer(registry_path=registry_path)


def main() -> int:
    """
    Main entry point for running the MCP server.
    
    Returns:
        Exit code
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='HoxCore MCP Server'
    )
    parser.add_argument(
        '--registry',
        help='Path to the registry (defaults to current or configured registry)'
    )
    parser.add_argument(
        '--transport',
        choices=['stdio'],
        default='stdio',
        help='Transport protocol (default: stdio)'
    )
    
    args = parser.parse_args()
    
    try:
        server = create_server(registry_path=args.registry)
        
        if not server.registry_path:
            print("Error: No registry found. Please specify with --registry or initialize one.", file=sys.stderr)
            return 1
        
        if args.transport == 'stdio':
            server.run_stdio()
        
        return 0
    
    except Exception as e:
        print(f"Error starting MCP server: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())