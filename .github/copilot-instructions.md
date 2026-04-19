```markdown
# HoxCore - GitHub Copilot Instructions

This document provides context for GitHub Copilot to assist with HoxCore development. HoxCore is a universal, declarative, version-controlled project registry system.

## Project Overview

HoxCore is a CLI-first application that manages a Git-backed registry of organizational entities (programs, projects, missions, actions). It follows a layered architecture with clear separation of concerns and provides MCP (Model Context Protocol) integration for AI agents.

### Core Entity Types

| Type | Prefix | Folder | Description |
|------|--------|--------|-------------|
| `program` | `prog-` | `programs/` | Abstract container for related initiatives |
| `project` | `proj-` | `projects/` | Concrete effort with deliverables |
| `mission` | `miss-` | `missions/` | Event-like effort with culmination |
| `action` | `act-` | `actions/` | Ongoing/recurring activity |

### Identifier System

- **UID**: Auto-generated, immutable (e.g., `proj-a1b2c3d4`)
- **ID**: Optional, user-defined, editable (e.g., `P-001`)

## Architecture

```
Entry Points (CLI, MCP Server)
        ↓
Command Layer (src/hxc/commands/)
        ↓
Operations Layer (src/hxc/core/operations/)
        ↓
Core Layer (enums, config, utilities)
        ↓
Storage Layer (YAML files, Git repository)
```

## Key Directories

```
src/hxc/
├── cli.py                  # CLI entry point
├── commands/               # CLI command implementations
│   ├── base.py             # BaseCommand abstract class
│   └── *.py                # Individual commands
├── core/
│   ├── config.py           # Configuration management
│   ├── enums.py            # EntityType, EntityStatus, etc.
│   └── operations/         # Business logic operations
├── mcp/                    # MCP server implementation
│   ├── server.py           # MCPServer class
│   ├── tools.py            # MCP tool implementations
│   ├── resources.py        # MCP resources
│   └── prompts.py          # MCP prompts
└── utils/
    ├── helpers.py          # General utilities
    └── path_security.py    # Path traversal protection (CRITICAL)
```

## Coding Conventions

### Type Hints

All public functions require type hints:

```python
def create_entity(
    self,
    entity_type: EntityType,
    title: str,
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
```

### Docstrings

Use Google-style docstrings:

```python
def method(self, param: str) -> Dict[str, Any]:
    """
    Brief description.
    
    Args:
        param: Parameter description
        
    Returns:
        Dictionary containing result data
        
    Raises:
        SpecificError: When condition occurs
    """
```

### Error Handling

Define specific exceptions per operation:

```python
class CreateOperationError(Exception):
    """Base exception for CreateOperation."""
    pass

class DuplicateIdError(CreateOperationError):
    """Raised when entity ID already exists."""
    pass
```

## Critical Patterns

### Path Security (MANDATORY)

All file I/O MUST use path security utilities:

```python
from hxc.utils.path_security import resolve_safe_path, get_safe_entity_path

# Correct
file_path = get_safe_entity_path(registry_path, entity_type, filename)

# NEVER do this
file_path = Path(registry_path) / user_input / "file.yml"  # DANGEROUS
```

### Operation Pattern

Operations contain business logic, independent of CLI/MCP:

```python
class SomeOperation:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
    
    def perform_action(self, **params) -> Dict[str, Any]:
        # Validate → Execute → Return structured result
        return {"success": True, "data": result}
```

### MCP Tool Pattern

MCP tools wrap operations with consistent error handling:

```python
def some_tool(
    param: str,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
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

Commands handle CLI arguments and output formatting:

```python
class SomeCommand(BaseCommand):
    name = "cmdname"
    help = "Description"
    
    @classmethod
    def register_subparser(cls, subparsers): ...
    
    @classmethod
    def execute(cls, args) -> int:
        # Return 0 for success, non-zero for error
```

## Enums (Always Use)

```python
from hxc.core.enums import EntityType, EntityStatus, OutputFormat, SortField

# Validate entity type
entity_type = EntityType.from_string("project")  # Raises ValueError if invalid

# Validate status
status = EntityStatus.from_string("active")  # Raises ValueError if invalid
```

## Import Organization

1. Standard library
2. Third-party packages
3. Local imports

```python
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from hxc.core.enums import EntityType
from hxc.utils.path_security import resolve_safe_path
```

## Testing

```python
@pytest.fixture
def temp_registry(tmp_path):
    """Create initialized registry for testing."""
    operation = InitOperation(str(tmp_path))
    operation.initialize_registry(use_git=False)
    return tmp_path

def test_create_project_success(self, temp_registry):
    """Test successful project creation."""
    operation = CreateOperation(str(temp_registry))
    result = operation.create_entity(
        entity_type=EntityType.PROJECT,
        title="Test Project",
        use_git=False,
    )
    assert result["success"] is True
    assert result["uid"].startswith("proj-")
```

## Common Tasks

### Adding a New Command

1. Create `src/hxc/commands/newcmd.py` with `BaseCommand` subclass
2. Add to `AVAILABLE_COMMANDS` in `src/hxc/commands/__init__.py`
3. Create operation if needed in `src/hxc/core/operations/`
4. Add tests in `tests/test_commands/`
5. Document in `docs/COMMANDS.md`

### Adding a New MCP Tool

1. Add tool function to `src/hxc/mcp/tools.py`
2. Register in `MCPServer._register_tools()`
3. Add schema in `MCPServer._get_tool_schema()`
4. Add tests in `tests/test_mcp/`
5. Document in `docs/MCP_INTEGRATION.md`

### Adding a New Operation

1. Create `src/hxc/core/operations/newop.py`
2. Define exception classes
3. Implement operation class
4. Add tests in `tests/test_operations/`
5. Document in `docs/API.md`

## Quality Checks

Before committing:

```bash
black src tests
isort src tests
flake8 src tests
mypy src
pytest
```

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/hxc/core/enums.py` | EntityType, EntityStatus enums |
| `src/hxc/utils/path_security.py` | Path validation (use for ALL file I/O) |
| `src/hxc/commands/base.py` | BaseCommand pattern |
| `src/hxc/mcp/tools.py` | MCP tool implementations |
| `pyproject.toml` | Project configuration |
| `standards/model_definition_example.yml` | Entity YAML reference |

## Entity YAML Structure

```yaml
type: project
uid: proj-12345678
id: P-001
title: "Example Project"
description: "Description"
status: active
start_date: 2024-01-01
due_date: 2024-04-01
category: software.dev/cli-tool
tags: [cli, python]
parent: prog-00000001
children: []
related: []
repositories:
  - name: github
    url: https://github.com/user/repo
```

## Git Commit Messages

Format: `<type>(<scope>): <description>`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

Examples:
- `feat(create): add support for custom entity IDs`
- `fix(list): handle empty registry gracefully`
- `docs(readme): update installation instructions`

## Additional Documentation

- `ARCHITECTURE.md` - System architecture
- `CONVENTIONS.md` - Detailed coding standards
- `CONTRIBUTING.md` - Contribution guidelines
- `docs/API.md` - Python API reference
- `docs/COMMANDS.md` - CLI command reference
- `docs/ENTITY_MODEL.md` - Entity specification
- `docs/MCP_INTEGRATION.md` - MCP documentation
```