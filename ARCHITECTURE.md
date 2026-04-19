```markdown
# HoxCore Architecture

This document describes the architecture and design of HoxCore, a universal, declarative, version-controlled project registry system. It is intended for AI coding agents and developers who need to understand the system's structure and patterns.

## System Overview

HoxCore is a CLI-first application that manages a Git-backed registry of organizational entities (programs, projects, missions, actions). The system follows a layered architecture with clear separation of concerns.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Entry Points                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   CLI (hxc) │  │ MCP Server  │  │   Python API (future)   │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Command Layer                               │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │ create │ │  list  │ │  show  │ │  edit  │ │ delete │  ...   │
│  └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘        │
└───────┼──────────┼──────────┼──────────┼──────────┼─────────────┘
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Operations Layer                             │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │ CreateOperation │ │  ListOperation  │ │  EditOperation  │    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │  ShowOperation  │ │ DeleteOperation │ │ValidateOperation│    │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
        │                                            │
        ▼                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Core Layer                                 │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────────────┐   │
│  │   Enums    │  │   Config   │  │     Path Security        │   │
│  └────────────┘  └────────────┘  └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
        │                                            │
        ▼                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Storage Layer                                 │
│  ┌────────────────────────┐  ┌────────────────────────────┐     │
│  │   YAML Entity Files    │  │       Git Repository       │     │
│  └────────────────────────┘  └────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
hoxcore/
├── src/hxc/                    # Main package
│   ├── __init__.py             # Package metadata (__version__)
│   ├── cli.py                  # CLI entry point (main function)
│   │
│   ├── commands/               # CLI command implementations
│   │   ├── __init__.py         # Command discovery and loading
│   │   ├── base.py             # BaseCommand abstract class
│   │   ├── create.py           # CreateCommand
│   │   ├── delete.py           # DeleteCommand
│   │   ├── edit.py             # EditCommand
│   │   ├── get.py              # GetCommand
│   │   ├── init.py             # InitCommand
│   │   ├── list.py             # ListCommand
│   │   ├── registry.py         # RegistryCommand
│   │   ├── show.py             # ShowCommand
│   │   └── validate.py         # ValidateCommand
│   │
│   ├── core/                   # Core business logic
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── enums.py            # EntityType, EntityStatus, etc.
│   │   │
│   │   └── operations/         # Business logic operations
│   │       ├── __init__.py
│   │       ├── create.py       # CreateOperation
│   │       ├── delete.py       # DeleteOperation
│   │       ├── edit.py         # EditOperation
│   │       ├── get.py          # GetPropertyOperation
│   │       ├── init.py         # InitOperation
│   │       ├── list.py         # ListOperation
│   │       ├── registry.py     # RegistryOperation
│   │       ├── show.py         # ShowOperation
│   │       └── validate.py     # ValidateOperation
│   │
│   ├── mcp/                    # MCP server implementation
│   │   ├── __init__.py
│   │   ├── server.py           # MCPServer class
│   │   ├── tools.py            # MCP tool implementations
│   │   ├── resources.py        # MCP resource implementations
│   │   └── prompts.py          # MCP prompt templates
│   │
│   └── utils/                  # Utility modules
│       ├── __init__.py
│       ├── helpers.py          # General helpers
│       └── path_security.py    # Path traversal protection
│
├── tests/                      # Test suite
│   ├── conftest.py             # Pytest fixtures
│   └── test_*.py               # Test modules
│
├── docs/                       # Documentation
│   ├── API.md                  # Python API reference
│   ├── COMMANDS.md             # CLI command reference
│   ├── ENTITY_MODEL.md         # Entity specification
│   └── MCP_INTEGRATION.md      # MCP documentation
│
└── standards/                  # Reference examples
    └── model_definition_example.yml
```

## Core Concepts

### Entity Types

All managed items are **entities** with one of four types:

| Type | Prefix | Folder | Description |
|------|--------|--------|-------------|
| `program` | `prog-` | `programs/` | Abstract container for related initiatives |
| `project` | `proj-` | `projects/` | Concrete effort with deliverables |
| `mission` | `miss-` | `missions/` | Event-like effort with culmination |
| `action` | `act-` | `actions/` | Ongoing/recurring activity |

### Identifier System

Each entity has two identifiers:

1. **UID** (Unique Identifier): Auto-generated, immutable, system-controlled
   - Format: `{prefix}-{8-char-hex}` (e.g., `proj-a1b2c3d4`)
   - Used internally and for file naming

2. **ID** (Human Identifier): Optional, user-defined, editable
   - Format: User-controlled (e.g., `P-001`, `MY-PROJECT`)
   - Must be unique within entity type

### Registry Structure

A HoxCore registry is a directory with:

```
registry/
├── .hxc/               # Marker directory (indicates valid registry)
│   └── index.db        # Query index (gitignored)
├── config.yml          # Registry configuration
├── programs/           # Program entities (prog-*.yml)
├── projects/           # Project entities (proj-*.yml)
├── missions/           # Mission entities (miss-*.yml)
├── actions/            # Action entities (act-*.yml)
└── .gitignore          # Git ignore rules
```

## Architectural Layers

### 1. Entry Points

#### CLI (`src/hxc/cli.py`)

The main CLI entry point. Uses argparse for argument parsing and dispatches to command classes.

```python
# Entry point registered in pyproject.toml
# hxc = "hxc.cli:main"

def main(args: Optional[List[str]] = None) -> int:
    # Parse arguments
    # Load and execute appropriate command
    # Return exit code
```

#### MCP Server (`src/hxc/mcp/server.py`)

Model Context Protocol server for AI agent integration.

```python
class MCPServer:
    def __init__(self, registry_path: Optional[str], read_only: bool = False):
        # Initialize tools, resources, prompts
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        # JSON-RPC request handling
    
    def run_stdio(self) -> None:
        # stdio transport for MCP
```

### 2. Command Layer (`src/hxc/commands/`)

Commands are the interface between entry points and operations.

#### Base Command Pattern

```python
class BaseCommand(abc.ABC):
    name = ""       # Command name for CLI
    help = ""       # Help text
    
    @classmethod
    @abc.abstractmethod
    def register_subparser(cls, subparsers) -> argparse.ArgumentParser:
        # Register command-specific arguments
        pass
    
    @classmethod
    @abc.abstractmethod
    def execute(cls, args: argparse.Namespace) -> int:
        # Execute command, return exit code
        pass
```

#### Command Responsibilities

- Parse and validate CLI arguments
- Convert arguments to operation parameters
- Call appropriate operation(s)
- Format and display output
- Handle errors and return exit codes

### 3. Operations Layer (`src/hxc/core/operations/`)

Operations contain the core business logic, independent of CLI or MCP interface.

#### Operation Pattern

```python
class SomeOperation:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
    
    def some_method(self, **params) -> Dict[str, Any]:
        # Validate inputs
        # Perform business logic
        # Return structured result
```

#### Key Operations

| Operation | Purpose |
|-----------|---------|
| `InitOperation` | Initialize new registry with directory structure |
| `CreateOperation` | Create new entity with validation |
| `ListOperation` | Load and filter entities with sorting |
| `ShowOperation` | Retrieve single entity by identifier |
| `GetPropertyOperation` | Get specific property from entity |
| `EditOperation` | Modify entity properties |
| `DeleteOperation` | Remove entity from registry |
| `ValidateOperation` | Validate registry integrity |
| `RegistryOperation` | Manage registry configuration |

#### Error Handling

Each operation defines specific exceptions:

```python
class SomeOperationError(Exception):
    """Base exception for SomeOperation"""
    pass

class SpecificError(SomeOperationError):
    """Specific error condition"""
    pass
```

### 4. Core Layer (`src/hxc/core/`)

#### Enums (`src/hxc/core/enums.py`)

Type-safe enumerations for constrained values:

```python
class EntityType(Enum):
    PROGRAM = "program"
    PROJECT = "project"
    MISSION = "mission"
    ACTION = "action"
    
    @classmethod
    def from_string(cls, value: str) -> "EntityType":
        # Parse string to enum with validation

class EntityStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on-hold"
    CANCELLED = "cancelled"
    PLANNED = "planned"

class OutputFormat(Enum):
    TABLE = "table"
    YAML = "yaml"
    JSON = "json"
    ID = "id"
    PRETTY = "pretty"

class SortField(Enum):
    TITLE = "title"
    ID = "id"
    DUE_DATE = "due_date"
    STATUS = "status"
    CREATED = "created"
    MODIFIED = "modified"
```

#### Configuration (`src/hxc/core/config.py`)

Global user configuration management:

```python
class Config:
    DEFAULT_CONFIG_DIR = "~/.hxc"
    DEFAULT_CONFIG_FILE = "config.json"
    
    def load(self) -> Dict[str, Any]: ...
    def save(self, config: Dict[str, Any]) -> None: ...
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
```

### 5. Utilities (`src/hxc/utils/`)

#### Path Security (`src/hxc/utils/path_security.py`)

**Critical**: All file I/O must use path security utilities to prevent directory traversal attacks.

```python
def resolve_safe_path(base_dir: str, relative_path: str) -> Path:
    """Resolve path and verify it's within base directory"""
    # Raises PathSecurityError if path escapes base_dir

def get_safe_entity_path(registry_path: str, entity_type: EntityType, filename: str) -> Path:
    """Get safe path for entity file"""
    # Validates entity type folder and filename

class PathSecurityError(Exception):
    """Raised when path security validation fails"""
```

#### Helpers (`src/hxc/utils/helpers.py`)

```python
def get_project_root(start_dir: Optional[str] = None) -> Optional[str]:
    """Find registry root by walking up directory tree"""

def is_valid_registry(path: str) -> bool:
    """Check if path contains valid registry structure"""
```

## MCP Architecture

### Server Structure

```python
class MCPServer:
    _tools: Dict[str, Callable]      # Tool implementations
    _resources: Dict[str, Callable]  # Resource implementations
    _prompts: Dict[str, Dict]        # Prompt templates
    
    def __init__(self, registry_path: str, read_only: bool = False):
        # In read_only mode, write tools are not registered
```

### Tool Categories

**Read-Only Tools** (always available):
- `list_entities`, `get_entity`, `search_entities`, `get_entity_property`
- `get_registry_path`, `validate_registry_path`, `list_registries`
- `validate_registry`, `validate_entity`

**Write Tools** (read-write mode only):
- `init_registry`, `create_entity`, `edit_entity`, `delete_entity`
- `set_registry_path`, `clear_registry_path`

### Tool Implementation Pattern

MCP tools in `src/hxc/mcp/tools.py` wrap operations:

```python
def some_tool(
    param1: str,
    param2: Optional[str] = None,
    registry_path: Optional[str] = None,  # Always included
) -> Dict[str, Any]:
    """
    Tool description for LLM.
    
    Args:
        param1: Description
        param2: Description
        registry_path: Registry path (uses default if not provided)
    
    Returns:
        Dictionary with success, result data, or error
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {"success": False, "error": "No registry found"}
        
        operation = SomeOperation(reg_path)
        result = operation.some_method(param1=param1, param2=param2)
        
        return {"success": True, **result}
    
    except SomeOperationError as e:
        return {"success": False, "error": str(e)}
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}
```

## Data Flow Examples

### Creating an Entity

```
CLI Input: hxc create project "My Project" --tags cli,tools
    │
    ▼
CreateCommand.execute()
    │ Parse arguments
    │ Validate entity type, status
    ▼
CreateOperation.create_entity()
    │ Generate UID
    │ Build entity data structure
    │ Validate uniqueness (ID if provided)
    │ Write YAML file (with path security)
    │ Git commit if enabled
    ▼
Return: {uid, id, file_path, entity, git_committed}
    │
    ▼
CLI Output: Created project 'My Project' (proj-a1b2c3d4)
```

### Listing Entities

```
CLI Input: hxc list --type project --status active --tags cli
    │
    ▼
ListCommand.execute()
    │ Parse filters
    │ Convert strings to enums
    ▼
ListOperation.list_entities()
    │ For each entity type folder:
    │   Load all YAML files
    │   Apply filters (status, tags, query, etc.)
    │   Sort results
    │   Apply max_items limit
    ▼
Return: {entities: [...], count: N}
    │
    ▼
CLI Output: Table/YAML/JSON formatted list
```

### MCP Tool Call

```
MCP Request: {"method": "tools/call", "params": {"name": "get_entity", "arguments": {"identifier": "P-001"}}}
    │
    ▼
MCPServer.handle_request()
    │ Route to _handle_call_tool()
    ▼
get_entity_tool(identifier="P-001")
    │ Get registry path
    │ Convert entity_type if provided
    ▼
ShowOperation.get_entity()
    │ Search by UID (fast path)
    │ Search by ID (slow path)
    │ Load and return entity
    ▼
MCP Response: {"result": {"content": [{"type": "text", "text": "{...}"}]}}
```

## Key Design Patterns

### 1. Operation Isolation

Operations are self-contained and don't depend on CLI or MCP specifics:

```python
# Good: Operation returns structured data
result = operation.create_entity(type=..., title=...)
# result = {"uid": "...", "id": "...", "entity": {...}}

# Bad: Operation knows about CLI
result = operation.create_entity(args)  # args is argparse.Namespace
```

### 2. Consistent Error Handling

All operations raise specific exceptions that are caught at the interface layer:

```python
# In operation
class EntityNotFoundError(ShowOperationError):
    pass

def get_entity(self, identifier: str) -> Dict[str, Any]:
    ...
    if not found:
        raise EntityNotFoundError(f"Entity not found: {identifier}")

# In CLI command
try:
    result = operation.get_entity(identifier)
except EntityNotFoundError as e:
    print(f"Error: {e}", file=sys.stderr)
    return 1

# In MCP tool
try:
    result = operation.get_entity(identifier)
except EntityNotFoundError as e:
    return {"success": False, "error": str(e)}
```

### 3. Git-Aware Operations

Write operations support optional git integration:

```python
def create_entity(self, ..., use_git: bool = True) -> Dict[str, Any]:
    # Write file
    self._write_entity(file_path, entity_data)
    
    # Git operations if enabled
    git_committed = False
    if use_git and self._is_git_repo():
        self._git_add(file_path)
        self._git_commit(f"Create {entity_type}: {title}")
        git_committed = True
    
    return {..., "git_committed": git_committed}
```

### 4. Two-Phase Entity Lookup

Entity retrieval uses a two-phase search for performance:

```python
def get_entity(self, identifier: str) -> Dict[str, Any]:
    # Phase 1: Fast path - check if identifier matches filename pattern
    # Entity files are named {prefix}-{uid}.yml
    for entity_type in EntityType:
        file_path = self._get_entity_path(entity_type, identifier)
        if file_path.exists():
            return self._load_entity(file_path)
    
    # Phase 2: Slow path - search file contents for ID match
    for entity_type in EntityType:
        for file_path in self._list_entity_files(entity_type):
            entity = self._load_entity(file_path)
            if entity.get("id") == identifier:
                return entity
    
    raise EntityNotFoundError(identifier)
```

## Security Considerations

### Path Traversal Prevention

**All file operations must use path security utilities:**

```python
from hxc.utils.path_security import resolve_safe_path, get_safe_entity_path

# Reading entity file
file_path = get_safe_entity_path(registry_path, entity_type, filename)
with open(file_path) as f:
    data = yaml.safe_load(f)

# Writing entity file  
file_path = get_safe_entity_path(registry_path, entity_type, f"{uid}.yml")
with open(file_path, 'w') as f:
    yaml.dump(data, f)
```

### Input Validation

All user inputs are validated before use:

- Entity types validated against `EntityType` enum
- Status values validated against `EntityStatus` enum
- Dates validated for format (YYYY-MM-DD)
- IDs checked for uniqueness before creation/modification

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py           # Shared fixtures (tmp_path cleanup, etc.)
├── test_cli.py           # CLI integration tests
├── test_commands/        # Command-specific tests
├── test_operations/      # Operation unit tests
├── test_mcp/             # MCP server tests
└── test_utils/           # Utility tests
```

### Key Fixtures

```python
@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
    operation = InitOperation(str(tmp_path))
    operation.initialize_registry(use_git=False)
    return tmp_path

@pytest.fixture
def sample_entity(temp_registry):
    """Create a sample entity"""
    operation = CreateOperation(str(temp_registry))
    result = operation.create_entity(
        entity_type=EntityType.PROJECT,
        title="Test Project",
        use_git=False
    )
    return result
```

### Test Markers

```python
@pytest.mark.unit          # Unit tests (fast, isolated)
@pytest.mark.integration   # Integration tests (may use filesystem)
@pytest.mark.mcp           # MCP-specific tests
```

## Extension Points

### Adding a New Command

1. Create `src/hxc/commands/newcmd.py`:

```python
from hxc.commands.base import BaseCommand

class NewCommand(BaseCommand):
    name = "newcmd"
    help = "Description of new command"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = subparsers.add_parser(cls.name, help=cls.help)
        parser.add_argument("--option", help="Option help")
        return parser
    
    @classmethod
    def execute(cls, args) -> int:
        # Implementation
        return 0
```

2. Add to `src/hxc/commands/__init__.py` command list

### Adding a New Operation

1. Create `src/hxc/core/operations/newop.py`:

```python
class NewOperationError(Exception):
    pass

class NewOperation:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
    
    def perform_action(self, **params) -> Dict[str, Any]:
        # Implementation
        return {"success": True, ...}
```

### Adding an MCP Tool

1. Add tool function to `src/hxc/mcp/tools.py`:

```python
def new_tool(
    param: str,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool description."""
    # Implementation using operations
```

2. Register in `MCPServer._register_tools()`
3. Add schema in `MCPServer._get_tool_schema()`

## Performance Considerations

### Current Implementation

- Entity loading: Direct YAML file reads
- Filtering: In-memory after loading
- Indexing: Planned (`.hxc/index.db`)

### Scaling Strategy

For registries with thousands of entities:

1. **Index-based queries**: Use SQLite index for fast lookups
2. **Lazy loading**: Load entity metadata only, full content on demand
3. **Caching**: Cache frequently accessed entities
4. **Batch operations**: Support bulk create/update

## Future Architecture

### Planned Enhancements

1. **SQLite Index**: Fast queries without loading all YAML files
2. **Template System**: Declarative scaffolding templates
3. **Plugin System**: Extend functionality without core changes
4. **API Server**: HTTP API alongside CLI and MCP
5. **Watch Mode**: Real-time registry synchronization

### Migration Path

The current architecture supports these extensions through:

- Operation layer abstraction (can add caching, indexing)
- Interface layer separation (easy to add new interfaces)
- Configuration system (can add plugin registration)
```