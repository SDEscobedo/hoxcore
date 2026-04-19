```markdown
# HoxCore MCP Integration Guide

This document provides comprehensive documentation for the HoxCore Model Context Protocol (MCP) server. It is designed for developers and AI coding agents who need to interact with HoxCore registries through the MCP protocol.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Server Configuration](#server-configuration)
- [Tools Reference](#tools-reference)
  - [Read-Only Tools](#read-only-tools)
  - [Write Tools](#write-tools)
  - [Registry Management Tools](#registry-management-tools)
  - [Validation Tools](#validation-tools)
- [Resources Reference](#resources-reference)
- [Prompts Reference](#prompts-reference)
- [AI Agent Configuration](#ai-agent-configuration)
- [Error Handling](#error-handling)
- [Best Practices for AI Agents](#best-practices-for-ai-agents)
- [Advanced Usage](#advanced-usage)

---

## Overview

HoxCore provides a Model Context Protocol (MCP) server that enables AI agents to interact with HoxCore registries through a standardized JSON-RPC interface. The MCP server exposes:

- **Tools**: Functions that AI agents can call to perform operations
- **Resources**: Data endpoints for retrieving registry information
- **Prompts**: Pre-defined prompt templates for common operations

### Key Features

| Feature | Description |
|---------|-------------|
| **Read-Only Mode** | Configurable read-only mode for safe exploration |
| **Git Integration** | Automatic git commits for write operations |
| **Path Security** | Built-in protection against directory traversal |
| **Structured Responses** | Consistent JSON response format |
| **Auto-Discovery** | Automatic registry detection |

### Protocol Version

HoxCore MCP server implements protocol version `2024-11-05`.

---

## Quick Start

### Starting the MCP Server

```bash
# Start with stdio transport (default)
hxc-mcp

# Start in read-only mode
hxc-mcp --read-only

# Specify registry path
hxc-mcp --registry /path/to/registry

# Combined options
hxc-mcp --registry /path/to/registry --read-only
```

### Basic JSON-RPC Request

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "list_entities",
    "arguments": {
      "entity_type": "project",
      "status": "active"
    }
  }
}
```

### Basic JSON-RPC Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"success\": true, \"entities\": [...], \"count\": 5}"
      }
    ]
  }
}
```

---

## Server Configuration

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--registry PATH` | Path to the HoxCore registry | Auto-detect |
| `--transport TYPE` | Transport protocol (`stdio`) | `stdio` |
| `--read-only` | Start in read-only mode (omit write tools) | `False` |

### Read-Only Mode

When started with `--read-only`, the following tools are **not available**:

- `init_registry`
- `create_entity`
- `edit_entity`
- `delete_entity`
- `set_registry_path`
- `clear_registry_path`

This mode is recommended for:
- Exploration and analysis
- AI agents with restricted permissions
- Shared or production registries

### Environment Variables

| Variable | Description |
|----------|-------------|
| `HXC_REGISTRY_PATH` | Override default registry path |
| `HXC_DEBUG` | Enable debug logging |

### Programmatic Initialization

```python
from hxc.mcp.server import create_server, MCPServer

# Create server with defaults
server = create_server()

# Create server with options
server = create_server(
    registry_path="/path/to/registry",
    read_only=True,
)

# Run with stdio transport
server.run_stdio()

# Or handle requests manually
response = server.handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
})
```

---

## Tools Reference

### Tool Response Format

All tools return a consistent response structure:

**Success Response:**
```json
{
  "success": true,
  "data": "...",
  "additional_fields": "..."
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Human-readable error message",
  "context_fields": "..."
}
```

---

### Read-Only Tools

These tools are always available, regardless of read-only mode.

#### list_entities

List entities from the HoxCore registry with optional filtering and sorting.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "entity_type": {
      "type": "string",
      "description": "Type of entity (program, project, mission, action, all)",
      "default": "all"
    },
    "status": {
      "type": "string",
      "description": "Filter by status (active, completed, on-hold, cancelled, planned, any)"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Filter by tags (AND logic - entity must have ALL specified tags)"
    },
    "category": {
      "type": "string",
      "description": "Filter by category (exact match)"
    },
    "parent": {
      "type": "string",
      "description": "Filter by parent ID (exact match)"
    },
    "identifier": {
      "type": "string",
      "description": "Filter by ID or UID (exact match)"
    },
    "query": {
      "type": "string",
      "description": "Text search in title and description (case-insensitive)"
    },
    "due_before": {
      "type": "string",
      "description": "Filter by due date before YYYY-MM-DD (inclusive)"
    },
    "due_after": {
      "type": "string",
      "description": "Filter by due date after YYYY-MM-DD (inclusive)"
    },
    "max_items": {
      "type": "integer",
      "description": "Maximum items to return (0 = all)",
      "default": 0
    },
    "sort_by": {
      "type": "string",
      "description": "Sort field (title, id, due_date, status, created, modified)",
      "default": "title"
    },
    "descending": {
      "type": "boolean",
      "description": "Sort in descending order",
      "default": false
    },
    "include_file_metadata": {
      "type": "boolean",
      "description": "Include file metadata (_file field with path, created, modified)",
      "default": false
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "entities": [
    {
      "type": "project",
      "uid": "proj-12345678",
      "id": "P-001",
      "title": "Website Redesign",
      "status": "active",
      "tags": ["web", "frontend"]
    }
  ],
  "count": 1,
  "filters": {
    "type": "project",
    "status": "active"
  },
  "sort": {
    "field": "title",
    "descending": false
  }
}
```

#### get_entity

Get detailed information about a specific entity.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "identifier": {
      "type": "string",
      "description": "ID or UID of the entity to retrieve"
    },
    "entity_type": {
      "type": "string",
      "description": "Optional entity type filter (program, project, mission, action)"
    },
    "include_raw": {
      "type": "boolean",
      "description": "Include raw YAML file content in response",
      "default": false
    }
  },
  "required": ["identifier"]
}
```

**Response:**
```json
{
  "success": true,
  "entity": {
    "type": "project",
    "uid": "proj-12345678",
    "id": "P-001",
    "title": "Website Redesign",
    "description": "Complete website overhaul",
    "status": "active",
    "tags": ["web", "frontend"],
    "repositories": [
      {"name": "github", "url": "https://github.com/company/website"}
    ]
  },
  "file_path": "/path/to/registry/projects/proj-12345678.yml",
  "identifier": "P-001"
}
```

#### search_entities

Search for entities using text queries. (Wrapper around `list_entities` with query parameter.)

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query for title and description"
    },
    "entity_type": {
      "type": "string",
      "description": "Optional type filter"
    },
    "status": {
      "type": "string",
      "description": "Optional status filter"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"}
    },
    "max_items": {
      "type": "integer"
    }
  },
  "required": ["query"]
}
```

#### get_entity_property

Get a specific property value from an entity.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "identifier": {
      "type": "string",
      "description": "ID or UID of the entity"
    },
    "property": {
      "type": "string",
      "description": "Property name to retrieve. SCALAR: type, uid, id, title, description, status, start_date, due_date, completion_date, duration_estimate, category, parent, template. LIST: tags, children, related. COMPLEX: repositories, storage, databases, tools, models, knowledge_bases. SPECIAL: all (returns all properties), path (returns file path)."
    },
    "entity_type": {
      "type": "string",
      "description": "Optional entity type filter"
    },
    "index": {
      "type": "integer",
      "description": "For list/complex properties, get item at specific index (0-based)"
    },
    "key": {
      "type": "string",
      "description": "For complex properties, filter by key:value pattern (e.g., 'name:github')"
    }
  },
  "required": ["identifier", "property"]
}
```

**Response:**
```json
{
  "success": true,
  "property": "tags",
  "property_type": "list",
  "value": ["web", "frontend", "design"],
  "identifier": "P-001"
}
```

---

### Write Tools

These tools are only available when the server is NOT started with `--read-only`.

#### init_registry

Initialize a new HoxCore registry at the specified path.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Path where to initialize the registry. Must be empty or non-existent."
    },
    "use_git": {
      "type": "boolean",
      "description": "Whether to initialize a git repository",
      "default": true
    },
    "commit": {
      "type": "boolean",
      "description": "Whether to create initial commit (requires use_git)",
      "default": true
    },
    "remote_url": {
      "type": "string",
      "description": "Optional git remote URL to configure as 'origin'"
    },
    "set_default": {
      "type": "boolean",
      "description": "Whether to set this registry as the default in config",
      "default": true
    }
  },
  "required": ["path"]
}
```

**Response:**
```json
{
  "success": true,
  "registry_path": "/path/to/registry",
  "git_initialized": true,
  "committed": true,
  "pushed": false,
  "remote_added": false,
  "set_as_default": true
}
```

#### create_entity

Create a new entity (program, project, mission, or action) in the registry.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "type": {
      "type": "string",
      "description": "Entity type: program | project | mission | action"
    },
    "title": {
      "type": "string",
      "description": "Human-readable title"
    },
    "description": {
      "type": "string"
    },
    "status": {
      "type": "string",
      "description": "Initial status",
      "default": "active"
    },
    "id": {
      "type": "string",
      "description": "Optional custom human-readable ID (e.g., P-042). Must be unique within entity type."
    },
    "category": {
      "type": "string"
    },
    "tags": {
      "type": "array",
      "items": {"type": "string"}
    },
    "parent": {
      "type": "string",
      "description": "Parent entity UID or ID"
    },
    "start_date": {
      "type": "string",
      "description": "YYYY-MM-DD (default: today)"
    },
    "due_date": {
      "type": "string",
      "description": "YYYY-MM-DD"
    },
    "use_git": {
      "type": "boolean",
      "description": "Whether to commit the change to git",
      "default": true
    }
  },
  "required": ["type", "title"]
}
```

**Response:**
```json
{
  "success": true,
  "uid": "proj-a1b2c3d4",
  "id": "P-001",
  "file_path": "/path/to/registry/projects/proj-a1b2c3d4.yml",
  "entity": {
    "type": "project",
    "uid": "proj-a1b2c3d4",
    "id": "P-001",
    "title": "New Project",
    "status": "active"
  },
  "git_committed": true
}
```

#### edit_entity

Edit properties of an existing registry entity.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "identifier": {
      "type": "string",
      "description": "UID or human-readable ID of the entity to edit"
    },
    "set_title": {"type": "string", "description": "New title value"},
    "set_description": {"type": "string", "description": "New description value"},
    "set_status": {"type": "string", "description": "New status (active, completed, on-hold, cancelled, planned)"},
    "set_id": {"type": "string", "description": "New human-readable ID. Must be unique."},
    "set_category": {"type": "string", "description": "New category path"},
    "set_parent": {"type": "string", "description": "New parent UID or ID"},
    "set_start_date": {"type": "string", "description": "New start date (YYYY-MM-DD)"},
    "set_due_date": {"type": "string", "description": "New due date (YYYY-MM-DD)"},
    "set_completion_date": {"type": "string", "description": "New completion date (YYYY-MM-DD)"},
    "add_tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to add (idempotent)"},
    "remove_tags": {"type": "array", "items": {"type": "string"}, "description": "Tags to remove"},
    "add_children": {"type": "array", "items": {"type": "string"}, "description": "Child entity UIDs/IDs to add"},
    "remove_children": {"type": "array", "items": {"type": "string"}, "description": "Child entity UIDs/IDs to remove"},
    "add_related": {"type": "array", "items": {"type": "string"}, "description": "Related entity UIDs/IDs to add"},
    "remove_related": {"type": "array", "items": {"type": "string"}, "description": "Related entity UIDs/IDs to remove"},
    "entity_type": {"type": "string", "description": "Optional type filter to disambiguate"},
    "use_git": {"type": "boolean", "description": "Whether to commit the change", "default": true}
  },
  "required": ["identifier"]
}
```

**Response:**
```json
{
  "success": true,
  "identifier": "P-001",
  "changes": [
    "title: Old Title → New Title",
    "status: active → completed",
    "Added tags: urgent"
  ],
  "entity": {...},
  "file_path": "/path/to/registry/projects/proj-12345678.yml",
  "git_committed": true
}
```

#### delete_entity

Delete an entity from the registry.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "identifier": {
      "type": "string",
      "description": "UID or human-readable ID"
    },
    "force": {
      "type": "boolean",
      "description": "Set True to confirm deletion (default: False returns confirmation prompt)",
      "default": false
    },
    "entity_type": {
      "type": "string"
    },
    "use_git": {
      "type": "boolean",
      "description": "Whether to commit the deletion",
      "default": true
    }
  },
  "required": ["identifier"]
}
```

**Response (force=false):**
```json
{
  "success": false,
  "confirmation_required": true,
  "identifier": "P-001",
  "entity_title": "Website Redesign",
  "entity_type": "project",
  "file_path": "/path/to/registry/projects/proj-12345678.yml",
  "message": "Confirmation required: about to permanently delete project 'Website Redesign'..."
}
```

**Response (force=true):**
```json
{
  "success": true,
  "identifier": "P-001",
  "deleted_title": "Website Redesign",
  "deleted_type": "project",
  "file_path": "/path/to/registry/projects/proj-12345678.yml",
  "git_committed": true
}
```

---

### Registry Management Tools

#### get_registry_path

Get the currently configured registry path.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "include_discovery": {
      "type": "boolean",
      "description": "Whether to attempt auto-discovery if not configured",
      "default": true
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "path": "/path/to/registry",
  "is_valid": true,
  "source": "config",
  "discovered_path": null,
  "validation_errors": []
}
```

#### validate_registry_path

Validate if a path is a valid HoxCore registry.

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Path to validate"
    }
  },
  "required": ["path"]
}
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "path": "/path/to/registry",
  "missing": []
}
```

#### list_registries

List all known registries.

**Response:**
```json
{
  "success": true,
  "registries": [
    {
      "path": "/path/to/registry",
      "is_current": true,
      "is_valid": true,
      "name": "default",
      "source": "config"
    }
  ],
  "count": 1
}
```

#### discover_registry

Attempt to discover a registry in the current directory tree.

**Response:**
```json
{
  "success": true,
  "path": "/path/to/discovered/registry",
  "is_valid": true
}
```

#### set_registry_path

Set the default registry path in configuration. (Write mode only)

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Path to set as the default registry"
    },
    "validate": {
      "type": "boolean",
      "description": "Whether to validate the path before setting",
      "default": true
    }
  },
  "required": ["path"]
}
```

#### clear_registry_path

Clear the configured registry path. (Write mode only)

**Response:**
```json
{
  "success": true,
  "previous_path": "/path/to/registry"
}
```

---

### Validation Tools

These tools are available in both read-only and read-write modes.

#### validate_registry

Validate the integrity and consistency of a HoxCore registry.

**Checks Performed:**
- Required fields (type, uid, title)
- UID uniqueness across all entities
- ID uniqueness within each entity type
- Parent link validation (errors for broken links)
- Child link validation (errors for broken links)
- Related link validation (warnings for broken links)
- Status value validation
- Entity type validation
- Empty file detection
- Invalid YAML detection

**Response:**
```json
{
  "success": true,
  "valid": true,
  "errors": [],
  "warnings": [
    "projects/proj-12345678.yml: Related entity 'proj-99999999' not found"
  ],
  "error_count": 0,
  "warning_count": 1,
  "entities_checked": 15,
  "entities_by_type": {
    "program": 2,
    "project": 10,
    "mission": 2,
    "action": 1
  }
}
```

#### validate_entity

Validate a single entity's data structure (pre-flight validation).

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "entity_data": {
      "type": "object",
      "description": "Entity data dictionary to validate. Should contain: type, uid, title."
    },
    "check_relationships": {
      "type": "boolean",
      "description": "Whether to verify that parent/children/related references exist",
      "default": true
    }
  },
  "required": ["entity_data"]
}
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "errors": [],
  "warnings": [],
  "error_count": 0,
  "warning_count": 0
}
```

---

## Resources Reference

MCP resources provide read-only data access through URI-based endpoints.

### Available Resources

| Resource | URI Pattern | Description |
|----------|-------------|-------------|
| Entity | `hxc://entity/{identifier}` | Single entity by ID or UID |
| Entities | `hxc://entities/{type}` | All entities of a type |
| Hierarchy | `hxc://hierarchy/{identifier}` | Entity with relationships |
| Stats | `hxc://registry/stats` | Registry statistics |
| Search | `hxc://search?q={query}` | Search results |

### Accessing Resources

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "resources/read",
  "params": {
    "uri": "hxc://entity/P-001"
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "contents": [
      {
        "uri": "hxc://entity/P-001",
        "mimeType": "application/json",
        "text": "{\"type\": \"project\", \"uid\": \"proj-12345678\", ...}"
      }
    ]
  }
}
```

### Resource Details

#### Entity Resource

**URI**: `hxc://entity/{identifier}`

Returns complete entity data for a single entity.

#### Entities Resource

**URI**: `hxc://entities/{type}`

Returns all entities of the specified type. Valid types: `program`, `project`, `mission`, `action`, `all`.

#### Hierarchy Resource

**URI**: `hxc://hierarchy/{identifier}`

Returns entity with parent, children, and related entities resolved.

```json
{
  "root": {...},
  "parent": {...},
  "children": [...],
  "related": [...]
}
```

#### Stats Resource

**URI**: `hxc://registry/stats`

Returns registry statistics:

```json
{
  "total_entities": 22,
  "by_type": {
    "program": 2,
    "project": 15,
    "mission": 3,
    "action": 2
  },
  "by_status": {
    "active": 18,
    "completed": 3,
    "on-hold": 1
  },
  "by_category": {...},
  "tags": {...}
}
```

#### Search Resource

**URI**: `hxc://search?q={query}`

Returns entities matching the search query.

---

## Prompts Reference

MCP prompts provide pre-defined templates for common operations.

### Available Prompts

| Prompt | Description |
|--------|-------------|
| `get_entity` | Retrieve entity information |
| `search_entities` | Search with filters |
| `list_entities` | List entities with options |
| `get_entity_property` | Get specific property |
| `analyze_registry` | Analyze registry structure |
| `get_related_entities` | Find related entities |
| `query_by_date` | Date-based queries |

### Using Prompts

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "prompts/get",
  "params": {
    "name": "get_entity",
    "arguments": {
      "identifier": "P-001"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "description": "Retrieve detailed information about a specific entity",
    "messages": [
      {
        "role": "user",
        "content": {
          "type": "text",
          "text": "Retrieve detailed information about a specific entity\n\nArguments:\n- identifier: P-001"
        }
      }
    ]
  }
}
```

---

## AI Agent Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hoxcore": {
      "command": "hxc-mcp",
      "args": ["--registry", "/path/to/registry"],
      "env": {}
    }
  }
}
```

For read-only mode:

```json
{
  "mcpServers": {
    "hoxcore": {
      "command": "hxc-mcp",
      "args": ["--registry", "/path/to/registry", "--read-only"],
      "env": {}
    }
  }
}
```

### Cursor

Add to Cursor settings or `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "hoxcore": {
      "command": "python",
      "args": ["-m", "hxc.mcp.server", "--registry", "/path/to/registry"],
      "cwd": "/path/to/hoxcore"
    }
  }
}
```

### Windsurf

Add to Windsurf MCP configuration:

```json
{
  "servers": {
    "hoxcore": {
      "command": "hxc-mcp",
      "args": ["--registry", "/path/to/registry"]
    }
  }
}
```

### Custom Integration

```python
import json
import subprocess
import sys

def call_hoxcore_mcp(method: str, params: dict) -> dict:
    """Call HoxCore MCP server with a request."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    proc = subprocess.Popen(
        ["hxc-mcp", "--registry", "/path/to/registry"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    
    stdout, _ = proc.communicate(json.dumps(request) + "\n")
    return json.loads(stdout)

# Example usage
result = call_hoxcore_mcp("tools/call", {
    "name": "list_entities",
    "arguments": {"entity_type": "project"}
})
```

---

## Error Handling

### Error Response Format

All errors follow a consistent format:

```json
{
  "success": false,
  "error": "Human-readable error description",
  "context_field": "value for debugging"
}
```

### Common Error Types

| Error | Cause | Resolution |
|-------|-------|------------|
| `No registry found` | Registry path not configured or invalid | Set registry path or run in registry directory |
| `Entity not found: {id}` | Entity with given identifier doesn't exist | Verify identifier is correct |
| `Duplicate ID error` | Custom ID already exists | Use a different ID |
| `Invalid entity type` | Type not one of: program, project, mission, action | Use valid type |
| `Invalid status` | Status not one of: active, completed, on-hold, cancelled, planned | Use valid status |
| `Security error` | Path traversal or security violation | Use valid paths within registry |
| `Directory not empty` | Init on non-empty directory | Use empty directory for init |

### JSON-RPC Error Codes

| Code | Meaning |
|------|---------|
| `-32700` | Parse error (invalid JSON) |
| `-32601` | Method not found |
| `-32603` | Internal error |

### Error Handling Best Practices

```python
# Python example
result = tool_function(...)
if not result.get("success"):
    error = result.get("error", "Unknown error")
    # Handle error appropriately
    if "not found" in error.lower():
        # Handle missing entity
        pass
    elif "duplicate" in error.lower():
        # Handle duplicate ID
        pass
    else:
        # General error handling
        pass
```

---

## Best Practices for AI Agents

### 1. Always Check Response Success

```python
result = list_entities_tool(entity_type="project")
if result["success"]:
    entities = result["entities"]
else:
    handle_error(result["error"])
```

### 2. Use Type Filters for Disambiguation

When an identifier might match multiple entities:

```python
# More specific - faster and unambiguous
get_entity_tool(identifier="P-001", entity_type="project")

# Less specific - may be ambiguous
get_entity_tool(identifier="P-001")
```

### 3. Validate Before Creating

```python
# Pre-flight validation
validation = validate_entity_tool(
    entity_data={
        "type": "project",
        "uid": "proj-temp",  # Placeholder
        "title": "New Project",
        "status": "active"
    },
    check_relationships=False  # Skip relationship check for new entities
)

if validation["valid"]:
    result = create_entity_tool(...)
```

### 4. Use Read-Only Mode for Exploration

When exploring or analyzing a registry:

```bash
hxc-mcp --read-only
```

### 5. Batch Operations Efficiently

Instead of multiple calls:

```python
# Inefficient
for id in ids:
    entity = get_entity_tool(identifier=id)

# Efficient
entities = list_entities_tool(entity_type="project")
# Filter in memory
```

### 6. Handle Confirmation for Deletes

```python
# First call returns confirmation
result = delete_entity_tool(identifier="P-001")
if result.get("confirmation_required"):
    # Show confirmation to user or make decision
    if should_delete:
        result = delete_entity_tool(identifier="P-001", force=True)
```

### 7. Leverage Git Integration

Write operations commit to git by default. Disable when doing batch updates:

```python
# Multiple edits, single commit at end
edit_entity_tool(identifier="P-001", set_status="completed", use_git=False)
edit_entity_tool(identifier="P-002", set_status="completed", use_git=False)
edit_entity_tool(identifier="P-003", set_status="completed", use_git=True)  # Commits all
```

### 8. Use Validation Tools

Before major operations:

```python
# Check registry health
validation = validate_registry_tool()
if not validation["valid"]:
    # Handle errors before proceeding
    for error in validation["errors"]:
        print(f"Error: {error}")
```

---

## Advanced Usage

### Custom Tool Registration

```python
from hxc.mcp.server import MCPServer

def custom_tool(param: str, registry_path: str = None) -> dict:
    """Custom tool description."""
    return {"success": True, "data": "custom result"}

server = MCPServer(registry_path="/path/to/registry")
server.register_tool("custom_tool", custom_tool)
```

### Custom Resource Registration

```python
def custom_resource(identifier: str, registry_path: str = None) -> dict:
    """Custom resource handler."""
    return {
        "content": {"custom": "data"},
        "mimeType": "application/json"
    }

server.register_resource("custom", custom_resource)
```

### Custom Prompt Registration

```python
server.register_prompt({
    "name": "custom_prompt",
    "description": "Custom prompt template",
    "arguments": [
        {
            "name": "param",
            "description": "Parameter description",
            "required": True
        }
    ]
})
```

### Direct Server Capabilities Query

```python
server = MCPServer(registry_path="/path/to/registry")
caps = server.get_capabilities()
print(f"Tools: {caps['tools']}")
print(f"Resources: {caps['resources']}")
print(f"Prompts: {caps['prompts']}")
print(f"Read-only: {caps['read_only']}")
```

---

## Troubleshooting

### Server Won't Start

1. **Check Python path**: Ensure `hxc` package is installed
2. **Check registry path**: Verify path exists and is valid
3. **Check permissions**: Ensure read (and write if not read-only) permissions

### No Registry Found

```bash
# Set registry explicitly
hxc-mcp --registry /path/to/registry

# Or set in config first
hxc registry path /path/to/registry
```

### Tool Returns Empty Results

1. **Check entity type**: Use correct type or `all`
2. **Check filters**: Verify filter values are valid
3. **Check registry content**: Ensure entities exist

### Git Commit Failures

1. **Check git status**: Ensure clean working tree
2. **Check permissions**: Ensure write access
3. **Disable git**: Use `use_git=false` parameter

---

## See Also

- [API.md](API.md) - Python API reference
- [COMMANDS.md](COMMANDS.md) - CLI command reference
- [ENTITY_MODEL.md](ENTITY_MODEL.md) - Entity specification
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [../CLAUDE.md](../CLAUDE.md) - AI agent guidance
```