# HoxCore

<p align="center">
    <img src="https://raw.githubusercontent.com/SDEscobedo/hoxcore/refs/heads/master/images/hoxcore_logo.jpg" alt="Hoxcore" width="400">
</p>


## What is HoxCore?

HoxCore is a **meta-manager** — a low-level tool that centralizes the core metadata of organizational objects into a single, unified registry. Rather than managing execution or visualization directly, HoxCore acts as the foundational layer that independent software can build upon.

### Organizational Object Types

HoxCore handles four categories of objects:

| Type | Orientation | Description |
|---|---|---|
| **Projects** | Goal-oriented | Has a defined finalization point; decoupled from execution |
| **Missions** | Event-oriented | Linked to execution; tied to a specific occurrence or execution window |
| **Activities** | Action-oriented | No definite end; represents indefinite, ongoing progression |
| **Programs** | Container | Groups and organizes Projects, Missions, and/or Activities |

### Design Philosophy

HoxCore is intentionally minimal and low-level. It owns the metadata — everything else is up to you. Independent tools can be built on top of HoxCore for visualization, reporting, dashboards, or richer management interfaces, all reading from the same single source of truth.

## Installation

### From PyPI

```bash
pip install hoxcore
```

### For Development

```bash
# Clone the repository
git clone https://github.com/SDEscobedo/hoxcore
cd hoxcore

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Usage

HoxCore manages your projects using a simple file-based system. It operates on a **Registry** (a directory on your disk) that holds various **Entities** (Programs, Projects, Missions, or Actions) stored as individual files. This mental model allows you to maintain full control over your data while using simple CLI commands to organize your workflow.

### Available Commands

| Command | Description |
| :--- | :--- |
| `init` | Initialize a new registry |
| `create` | Create a new entity (project, program, mission, action) |
| `list` | List entities with optional filters |
| `show` | Show full details of a specific entity |
| `get` | Get a specific property from an entity |
| `edit` | Edit properties of an entity |
| `delete` | Delete an entity from the registry |
| `validate` | Validate registry integrity |
| `registry` | Manage registry location |
| `mcp` | Start the MCP server for LLM access |

### Quick Start Guide

#### 1. Initialize a Registry

Set up your first registry to start storing entities.

```bash
# Initialize a registry in the current directory
hxc init

# Initialize in a specific directory
hxc init ~/my-registry

# Initialize without git integration
hxc init --no-git
```

#### 2. Create Entities
   
Add projects, programs, missions, or actions to your registry.

```bash
# Create a basic project
hxc create project "My First Project"

# Create a project with a description, tags, and due date
hxc create project "API Redesign" --description "Redesign the public API" --tags backend api --due-date 2025-06-01

# Create a program (container for projects)
hxc create program "Q2 Initiatives"

# Create a mission (execution-oriented, time-bound)
hxc create mission "Deploy v2.0"

# Create an action (ongoing, no end date)
hxc create action "Monitor system health"
```
#### 3.  List and Inspect
   
View your registry content and drill down into details.

```bash
# List all projects
hxc list project

# List all entities in the registry
hxc list all

# Filter by status or tag
hxc list project --status active
hxc list project --tag backend

# Show full details of a specific entity
hxc show <uid>

# Get a specific property
hxc get <uid> status
```

#### 4. Edit and Delete
   
Update or remove entities as your tasks progress.

```bash
# Change status or add a tag
hxc edit <uid> --set-status completed
hxc edit <uid> --add-tag backend

# Set a new due date
hxc edit <uid> --set-due-date 2025-06-01

# Delete an entity (prompts for confirmation)
hxc delete <uid>

# Delete immediately without prompt
hxc delete <uid> --force
```

**Getting Help**

If you need more information about a specific command or general flags:

```bash
# General help
hxc --help

# Command-specific help
hxc create --help
hxc list --help
```

---

## MCP Server (Model Context Protocol)

HoxCore includes a built-in MCP server that exposes registry functionality to LLMs through a standardized interface. This allows AI assistants (like Claude) to interact with your HoxCore registries directly.

### Starting the Server

```bash
# Start with the default or configured registry
hxc-mcp

# Start with a specific registry path
hxc-mcp --registry /path/to/your/registry

# Specify transport (currently only stdio is supported)
hxc-mcp --transport stdio
```

You can also start the server programmatically:

```python
from hxc.mcp.server import create_server

server = create_server(registry_path="/path/to/registry")
server.run_stdio()
```

### Connecting to Claude (or other MCP-compatible clients)

Add HoxCore to your MCP client configuration. For Claude Desktop, update your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "hoxcore": {
      "command": "hxc-mcp",
      "args": ["--registry", "/path/to/your/registry"]
    }
  }
}
```

### Available Tools

The MCP server exposes four tools that an LLM can call:

| Tool | Description |
|---|---|
| `list_entities` | List entities in the registry, with optional filters for type, status, tags, category, and parent |
| `get_entity` | Retrieve a specific entity by its ID or UID |
| `search_entities` | Full-text search across entity titles and descriptions |
| `get_entity_property` | Fetch a specific property from an entity, with support for list indexing and key filtering |

### Available Resources

Resources are accessible via `hxc://` URIs:

| URI | Description |
|---|---|
| `hxc://entity/{identifier}` | A specific entity by ID or UID (YAML) |
| `hxc://entities/{type}` | All entities of a given type (JSON) |
| `hxc://hierarchy/{identifier}` | Entity hierarchy and relationships (JSON) |
| `hxc://registry/stats` | Registry statistics and overview (JSON) |
| `hxc://search?q={query}` | Search results for a query (JSON) |

### Extending the Server

You can register custom tools, resources, and prompts at runtime:

```python
from hxc.mcp.server import create_server

server = create_server()

# Register a custom tool
def my_tool(registry_path=None, **kwargs):
    """My custom tool description."""
    return {"result": "..."}

server.register_tool("my_tool", my_tool)

# Register a custom prompt
server.register_prompt({
    "name": "my_prompt",
    "description": "A helpful prompt template",
    "arguments": [
        {"name": "context", "description": "Context for the prompt", "required": True}
    ]
})

server.run_stdio()
```

---

## Development

### Project Structure

```
project/
├── LICENSE
├── README.md
├── pyproject.toml
├── setup.py
├── src/
│   └── hxc/
│       ├── __init__.py
│       ├── cli.py
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── command1.py
│       │   └── command2.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── config.py
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── server.py
│       │   ├── tools.py
│       │   ├── resources.py
│       │   └── prompts.py
│       └── utils/
│           ├── __init__.py
│           └── helpers.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_cli.py
    └── commands/
        ├── __init__.py
        ├── test_command1.py
        └── test_command2.py
```

### Adding New Commands

To add a new command to the CLI:

1. Create a new file in `src/hxc/commands/` (e.g., `mycommand.py`)
2. Define a class that inherits from `BaseCommand`
3. Use the `@register_command` decorator to register it
4. Implement `register_subparser` and `execute` methods

Example:

```python
from hxc.commands import register_command
from hxc.commands.base import BaseCommand

@register_command
class MyCommand(BaseCommand):
    name = "mycommand"
    help = "My custom command"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        parser.add_argument('--myflag', help='My flag')
        return parser
    
    @classmethod
    def execute(cls, args):
        # Implement command logic here
        return 0
```

### Running Tests

Make sure you have development dependencies installed:

```bash
pip install -e ".[dev]"
```

Run the tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hxc

# Run specific tests
pytest tests/test_cli.py
```

### Important Test Setup

The project uses a `src/` layout for better package organization. Make sure you have a `conftest.py` file in your tests directory with the following content to ensure tests can import the package correctly:

```python
# tests/conftest.py
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
```

## Distribution

### Building the package

```bash
python -m build
```

### Publishing to PyPI

```bash
python -m twine upload dist/*
```

## License

MIT
