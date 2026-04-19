```markdown
# CLAUDE.md - HoxCore AI Agent Context

This document provides essential context for Claude (Anthropic) when working with the HoxCore codebase. It is optimized for Claude Opus and Sonnet models used in AI coding agents.

## Project Identity

**HoxCore** is a CLI-first, Git-backed registry system for managing organizational entities (programs, projects, missions, actions). It follows a layered architecture with MCP (Model Context Protocol) integration for AI agents.

- **Language**: Python 3.8+
- **Package**: `hxc` (installed via `pip install hoxcore`)
- **Entry Points**: `hxc` (CLI), `hxc-mcp` (MCP server)

## Critical Rules

### 1. Path Security (MANDATORY)

**All file I/O MUST use path security utilities.** This is non-negotiable.

```python
# CORRECT - Always use these
from hxc.utils.path_security import resolve_safe_path, get_safe_entity_path

file_path = get_safe_entity_path(registry_path, entity_type, filename)

# NEVER DO THIS - Path injection vulnerability
file_path = Path(registry_path) / user_input / "file.yml"
```

### 2. Use Enums, Not Strings

```python
from hxc.core.enums import EntityType, EntityStatus

# CORRECT
entity_type = EntityType.from_string("project")  # Validates and returns enum

# INCORRECT
entity_type = "project"  # No validation
```

### 3. Operations Are Interface-Agnostic

Operations contain business logic and must NOT depend on CLI arguments or MCP structures:

```python
# CORRECT - Operation returns structured dict
result = operation.create_entity(entity_type=EntityType.PROJECT, title="Title")

# INCORRECT - Operation receives CLI args
result = operation.create_entity(args)  # args is argparse.Namespace
```

## Architecture Overview

```
Entry Points (CLI, MCP)
        ↓
Commands (src/hxc/commands/)     ← Parse args, format output
        ↓
Operations (src/hxc/core/operations/)  ← Business logic (THIS IS WHERE LOGIC LIVES)
        ↓
Core (enums, config, utilities)
        ↓
Storage (YAML files in Git repository)
```

## Directory Structure

```
src/hxc/
├── cli.py                      # CLI entry point
├── commands/                   # CLI command implementations
│   ├── base.py                 # BaseCommand abstract class
│   ├── create.py, list.py, show.py, edit.py, delete.py
│   ├── get.py, init.py, validate.py, registry.py
│   └── __init__.py             # Command discovery
├── core/
│   ├── config.py               # Configuration (~/.hxc/config.json)
│   ├── enums.py                # EntityType, EntityStatus, OutputFormat, SortField
│   └── operations/             # Business logic layer
│       ├── create.py, list.py, show.py, edit.py, delete.py
│       ├── get.py, init.py, validate.py, registry.py
│       └── __init__.py
├── mcp/
│   ├── server.py               # MCPServer class
│   ├── tools.py                # MCP tool implementations (wrap operations)
│   ├── resources.py            # MCP resources
│   └── prompts.py              # MCP prompts
└── utils/
    ├── helpers.py              # get_project_root, is_valid_registry
    └── path_security.py        # CRITICAL: Path traversal protection
```

## Entity Types

| Type | Prefix | Folder | Purpose |
|------|--------|--------|---------|
| `program` | `prog-` | `programs/` | Container for related initiatives |
| `project` | `proj-` | `projects/` | Effort with deliverables |
| `mission` | `miss-` | `missions/` | Event with culmination |
| `action` | `act-` | `actions/` | Ongoing/recurring activity |

## Identifier System

- **UID**: `{prefix}-{8-hex}` — Auto-generated, immutable (e.g., `proj-a1b2c3d4`)
- **ID**: User-defined, editable, unique within type (e.g., `P-001`)

## Key Patterns

### Operation Pattern

```python
class SomeOperation:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)

    def perform_action(self, param: str) -> Dict[str, Any]:
        # 1. Validate inputs
        # 2. Execute logic
        # 3. Return structured result
        return {"success": True, "data": result}
```

### MCP Tool Pattern

```python
def some_tool(
    param: str,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool description for LLM."""
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {"success": False, "error": "No registry found"}

        operation = SomeOperation(reg_path)
        return {"success": True, **operation.method(param)}
    except SpecificError as e:
        return {"success": False, "error": str(e)}
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}"}
```

### Command Pattern

```python
class SomeCommand(BaseCommand):
    name = "cmdname"
    help = "Description"

    @classmethod
    def register_subparser(cls, subparsers) -> argparse.ArgumentParser:
        parser = subparsers.add_parser(cls.name, help=cls.help)
        # Add arguments
        return parser

    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        # Return 0 for success, non-zero for error
        return 0
```

### Exception Pattern

```python
class SomeOperationError(Exception):
    """Base exception for SomeOperation."""
    pass

class SpecificError(SomeOperationError):
    """Raised when specific condition occurs."""
    pass
```

## Common Tasks

### Adding a New CLI Command

1. Create `src/hxc/commands/newcmd.py`:
   ```python
   from hxc.commands.base import BaseCommand
   
   class NewCommand(BaseCommand):
       name = "newcmd"
       help = "Command description"
       # ... implement register_subparser and execute
   ```

2. Add to `AVAILABLE_COMMANDS` in `src/hxc/commands/__init__.py`

3. Create corresponding operation if needed

4. Add tests in `tests/test_commands/test_newcmd.py`

### Adding a New MCP Tool

1. Add function to `src/hxc/mcp/tools.py`
2. Register in `MCPServer._register_tools()` (in `server.py`)
3. Add schema in `MCPServer._get_tool_schema()` (in `server.py`)
4. Add tests in `tests/test_mcp/`

### Adding a New Operation

1. Create `src/hxc/core/operations/newop.py`:
   - Define exception classes
   - Implement operation class with methods returning `Dict[str, Any]`

2. Add tests in `tests/test_operations/test_newop.py`

## Type Hints and Docstrings

All public functions require type hints and Google-style docstrings:

```python
def method(
    self,
    required: str,
    optional: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Brief description.

    Args:
        required: Description of required parameter
        optional: Description of optional parameter

    Returns:
        Dictionary containing:
        - success: bool
        - data: Result data

    Raises:
        SpecificError: When condition occurs
    """
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/hxc

# Run specific test
pytest tests/test_operations/test_create.py -v

# Run by marker
pytest -m unit
pytest -m mcp
```

### Test Fixture

```python
@pytest.fixture
def temp_registry(tmp_path):
    """Create initialized registry for testing."""
    operation = InitOperation(str(tmp_path))
    operation.initialize_registry(use_git=False)
    return tmp_path
```

## Code Quality

```bash
black src tests          # Format
isort src tests          # Sort imports
flake8 src tests         # Lint
mypy src                 # Type check
```

## Git Commit Messages

Format: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Examples:
- `feat(create): add support for custom entity IDs`
- `fix(list): handle empty registry gracefully`

## Key Files Quick Reference

| File | Purpose |
|------|---------|
| `src/hxc/core/enums.py` | EntityType, EntityStatus — **use these** |
| `src/hxc/utils/path_security.py` | Path validation — **mandatory for file I/O** |
| `src/hxc/commands/base.py` | BaseCommand pattern |
| `src/hxc/mcp/tools.py` | MCP tool implementations |
| `src/hxc/mcp/server.py` | MCP server and tool registration |
| `standards/model_definition_example.yml` | Complete entity YAML example |

## Entity YAML Structure

```yaml
type: project
uid: proj-12345678        # Auto-generated
id: P-001                 # Optional, user-defined
title: "Project Title"
description: "Description"
status: active            # active|completed|on-hold|cancelled|planned
start_date: 2024-01-01
due_date: 2024-04-01
category: software.dev/cli-tool
tags: [cli, python]
parent: prog-00000001     # Parent UID or ID
children: []
related: []
repositories:
  - name: github
    url: https://github.com/user/repo
```

## Error Handling Guidelines

1. **Define specific exceptions** per operation
2. **Never use bare `except:`** — catch specific exceptions
3. **Return structured error responses** in MCP tools
4. **Include context** in error messages

```python
# Good
except EntityNotFoundError as e:
    return {"success": False, "error": str(e), "identifier": identifier}

# Bad
except:
    return {"success": False, "error": "Something went wrong"}
```

## Two-Phase Entity Lookup

Entity retrieval uses optimized search:

1. **Fast path**: Check if identifier matches filename (`{prefix}-{uid}.yml`)
2. **Slow path**: Search file contents for ID match

## Read-Only vs Read-Write MCP Mode

The MCP server supports `--read-only` mode where write tools are omitted:

**Always available**: `list_entities`, `get_entity`, `search_entities`, `get_entity_property`, `validate_registry`, `validate_entity`

**Write mode only**: `init_registry`, `create_entity`, `edit_entity`, `delete_entity`

## Additional Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — Full system architecture
- [CONVENTIONS.md](CONVENTIONS.md) — Detailed coding standards
- [CONTRIBUTING.md](CONTRIBUTING.md) — Contribution workflow
- [docs/API.md](docs/API.md) — Python API reference
- [docs/COMMANDS.md](docs/COMMANDS.md) — CLI reference
- [docs/ENTITY_MODEL.md](docs/ENTITY_MODEL.md) — Entity specification
- [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) — MCP documentation

## Quick Checklist Before Committing

- [ ] Type hints on all public functions
- [ ] Docstrings with Args, Returns, Raises
- [ ] Path security for ALL file I/O
- [ ] Specific exception handling (no bare except)
- [ ] Tests written and passing
- [ ] Code formatted with `black` and `isort`
- [ ] Linting passes with `flake8`
- [ ] Type checking passes with `mypy`
```