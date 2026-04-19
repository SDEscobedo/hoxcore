```markdown
# Contributing to HoxCore

Thank you for your interest in contributing to HoxCore! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Contribution Workflow](#contribution-workflow)
- [Adding New Features](#adding-new-features)
- [Testing Guidelines](#testing-guidelines)
- [Code Quality Standards](#code-quality-standards)
- [Documentation Requirements](#documentation-requirements)
- [Pull Request Process](#pull-request-process)
- [For AI Agents](#for-ai-agents)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of YAML and CLI development

### Quick Setup

```bash
# Clone the repository
git clone https://github.com/SDEscobedo/hoxcore.git
cd hoxcore

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
hxc --version
pytest --collect-only
```

## Development Setup

### Full Development Installation

```bash
# Install all optional dependencies
pip install -e ".[dev,mcp]"
```

### IDE Configuration

For VS Code, recommended settings:

```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true
}
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `HXC_REGISTRY_PATH` | Override default registry path | `~/.hxc` config |
| `HXC_DEBUG` | Enable debug logging | `false` |

## Project Structure

```
hoxcore/
├── src/hxc/                    # Main package
│   ├── cli.py                  # CLI entry point
│   ├── commands/               # CLI command implementations
│   │   ├── base.py             # BaseCommand abstract class
│   │   └── *.py                # Individual commands
│   ├── core/                   # Core business logic
│   │   ├── config.py           # Configuration management
│   │   ├── enums.py            # Type enumerations
│   │   └── operations/         # Business logic operations
│   ├── mcp/                    # MCP server implementation
│   │   ├── server.py           # MCPServer class
│   │   ├── tools.py            # MCP tool implementations
│   │   ├── resources.py        # MCP resources
│   │   └── prompts.py          # MCP prompts
│   └── utils/                  # Utility modules
│       ├── helpers.py          # General utilities
│       └── path_security.py    # Path traversal protection
├── tests/                      # Test suite
├── docs/                       # Documentation
└── standards/                  # Reference examples
```

### Architectural Layers

1. **Entry Points**: `cli.py`, `mcp/server.py`
2. **Commands**: Parse CLI arguments, call operations
3. **Operations**: Core business logic (interface-agnostic)
4. **Core**: Enums, config, utilities
5. **Storage**: YAML files in Git-tracked registry

**Key Principle**: Operations contain business logic and are independent of CLI or MCP. Commands and MCP tools are thin wrappers.

## Contribution Workflow

### 1. Find or Create an Issue

- Check [existing issues](https://github.com/SDEscobedo/hoxcore/issues)
- For new features, create an issue first to discuss
- For bugs, include reproduction steps

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation only
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 3. Make Changes

- Follow [code conventions](CONVENTIONS.md)
- Write tests for new functionality
- Update documentation as needed

### 4. Run Quality Checks

```bash
# Format code
black src tests
isort src tests

# Lint
flake8 src tests

# Type check
mypy src

# Run tests
pytest
```

### 5. Submit Pull Request

- Use descriptive title and description
- Reference related issues
- Ensure all checks pass

## Adding New Features

### Adding a New CLI Command

1. **Create command file** (`src/hxc/commands/newcmd.py`):

```python
"""
NewCmd command implementation
"""
import argparse
from typing import Any

from hxc.commands.base import BaseCommand
from hxc.core.operations.newop import NewOperation


class NewCommand(BaseCommand):
    """Command description."""
    
    name = "newcmd"
    help = "Brief help text for the command"

    @classmethod
    def register_subparser(
        cls, subparsers: argparse._SubParsersAction
    ) -> argparse.ArgumentParser:
        parser = subparsers.add_parser(cls.name, help=cls.help)
        parser.add_argument("required_arg", help="Required argument")
        parser.add_argument("--optional", help="Optional argument")
        return parser

    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        try:
            operation = NewOperation(registry_path)
            result = operation.perform_action(
                required_arg=args.required_arg,
                optional=args.optional,
            )
            print(f"Success: {result}")
            return 0
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
```

2. **Register in `__init__.py`**: Add to `AVAILABLE_COMMANDS` list

3. **Create operation** (see below)

4. **Add tests** in `tests/test_commands/test_newcmd.py`

5. **Document** in `docs/COMMANDS.md`

### Adding a New Operation

1. **Create operation file** (`src/hxc/core/operations/newop.py`):

```python
"""
NewOp operation implementation
"""
from pathlib import Path
from typing import Any, Dict, Optional

from hxc.utils.path_security import resolve_safe_path


class NewOperationError(Exception):
    """Base exception for NewOperation."""
    pass


class SpecificError(NewOperationError):
    """Specific error condition."""
    pass


class NewOperation:
    """
    Performs new operation on registry entities.
    
    This operation does X, Y, Z.
    """

    def __init__(self, registry_path: str):
        """
        Initialize the operation.
        
        Args:
            registry_path: Path to the HoxCore registry
        """
        self.registry_path = Path(registry_path)

    def perform_action(
        self,
        required_param: str,
        optional_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform the action.
        
        Args:
            required_param: Description of required parameter
            optional_param: Description of optional parameter
            
        Returns:
            Dictionary containing:
            - success: bool
            - result_data: Any relevant data
            
        Raises:
            SpecificError: When specific condition occurs
            NewOperationError: For general operation failures
        """
        # Validate inputs
        if not required_param:
            raise SpecificError("required_param cannot be empty")
        
        # Use path security for any file operations
        safe_path = resolve_safe_path(
            str(self.registry_path), 
            "some/relative/path"
        )
        
        # Perform operation logic
        result = self._internal_method(required_param)
        
        return {
            "success": True,
            "data": result,
        }

    def _internal_method(self, param: str) -> Any:
        """Internal helper method."""
        pass
```

2. **Add tests** in `tests/test_operations/test_newop.py`

### Adding an MCP Tool

1. **Add tool function** to `src/hxc/mcp/tools.py`:

```python
def new_tool(
    required_param: str,
    optional_param: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool description for LLM consumption.
    
    This tool performs X operation on Y entities.
    
    Args:
        required_param: Description
        optional_param: Description (default: None)
        registry_path: Optional registry path (uses default if not provided)
    
    Returns:
        Dictionary containing:
        - success: bool
        - data: Result data on success
        - error: Error message on failure
    
    Example:
        >>> new_tool("value")
        {"success": True, "data": {...}}
    """
    try:
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {"success": False, "error": "No registry found"}
        
        operation = NewOperation(reg_path)
        result = operation.perform_action(
            required_param=required_param,
            optional_param=optional_param,
        )
        
        return {"success": True, **result}
    
    except SpecificError as e:
        return {"success": False, "error": str(e)}
    except NewOperationError as e:
        return {"success": False, "error": str(e)}
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}
```

2. **Register tool** in `MCPServer._register_tools()`:

```python
def _register_tools(self) -> None:
    self._tools = {
        # ... existing tools
        "new_tool": new_tool,
    }
```

3. **Add schema** in `MCPServer._get_tool_schema()`:

```python
"new_tool": {
    "type": "object",
    "properties": {
        "required_param": {
            "type": "string",
            "description": "Description of required parameter",
        },
        "optional_param": {
            "type": "string",
            "description": "Description of optional parameter",
        },
    },
    "required": ["required_param"],
},
```

4. **Add tests** in `tests/test_mcp/test_tools.py`

5. **Document** in `docs/MCP_INTEGRATION.md`

## Testing Guidelines

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_cli.py              # CLI integration tests
├── test_commands/           # Command tests
│   └── test_create.py
├── test_operations/         # Operation unit tests
│   └── test_create.py
├── test_mcp/                # MCP tests
│   └── test_tools.py
└── test_utils/              # Utility tests
```

### Writing Tests

```python
import pytest
from pathlib import Path

from hxc.core.operations.create import CreateOperation
from hxc.core.enums import EntityType


class TestCreateOperation:
    """Tests for CreateOperation."""

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
        assert result["entity"]["title"] == "Test Project"

    def test_create_with_duplicate_id_fails(self, temp_registry):
        """Test that duplicate IDs are rejected."""
        operation = CreateOperation(str(temp_registry))
        
        # Create first entity
        operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="First",
            entity_id="P-001",
            use_git=False,
        )
        
        # Attempt duplicate
        with pytest.raises(DuplicateIdError):
            operation.create_entity(
                entity_type=EntityType.PROJECT,
                title="Second",
                entity_id="P-001",
                use_git=False,
            )
```

### Test Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary initialized registry."""
    from hxc.core.operations.init import InitOperation
    
    operation = InitOperation(str(tmp_path))
    operation.initialize_registry(use_git=False)
    return tmp_path


@pytest.fixture
def sample_project(temp_registry):
    """Create a sample project entity."""
    from hxc.core.operations.create import CreateOperation
    from hxc.core.enums import EntityType
    
    operation = CreateOperation(str(temp_registry))
    return operation.create_entity(
        entity_type=EntityType.PROJECT,
        title="Sample Project",
        use_git=False,
    )
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/hxc --cov-report=html

# Run specific test file
pytest tests/test_operations/test_create.py

# Run specific test
pytest tests/test_operations/test_create.py::TestCreateOperation::test_create_project_success

# Run by marker
pytest -m unit
pytest -m integration
pytest -m mcp

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Markers

```python
@pytest.mark.unit           # Fast, isolated unit tests
@pytest.mark.integration    # Tests involving filesystem
@pytest.mark.mcp            # MCP-specific tests
```

## Code Quality Standards

### Formatting

We use **Black** for code formatting:

```bash
black src tests
```

Configuration in `pyproject.toml`:
- Line length: 88
- Target Python: 3.8+

### Import Sorting

We use **isort** with Black-compatible settings:

```bash
isort src tests
```

### Linting

We use **Flake8** for linting:

```bash
flake8 src tests
```

### Type Checking

We use **mypy** for static type analysis:

```bash
mypy src
```

All public functions must have type hints:

```python
def create_entity(
    self,
    entity_type: EntityType,
    title: str,
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
```

### Security Requirements

**Path Traversal Prevention**: All file I/O must use path security utilities:

```python
from hxc.utils.path_security import (
    resolve_safe_path,
    get_safe_entity_path,
    PathSecurityError,
)

# Always use for file operations
safe_path = get_safe_entity_path(registry_path, entity_type, filename)
```

**Never** construct file paths through string concatenation with user input.

### Error Handling

- Define specific exceptions for operations
- Catch specific exceptions, not bare `except:`
- Return structured error responses in MCP tools

```python
# Good
try:
    result = operation.perform()
except EntityNotFoundError as e:
    return {"success": False, "error": str(e)}
except OperationError as e:
    return {"success": False, "error": str(e)}

# Bad
try:
    result = operation.perform()
except:
    return {"success": False, "error": "Something went wrong"}
```

## Documentation Requirements

### Code Documentation

**Docstrings**: All public classes, methods, and functions must have docstrings:

```python
def get_entity(
    self,
    identifier: str,
    entity_type: Optional[EntityType] = None,
) -> Dict[str, Any]:
    """
    Retrieve an entity by its identifier.
    
    Uses a two-phase search strategy:
    1. Fast path: Match identifier in filename pattern
    2. Slow path: Search file contents for ID match
    
    Args:
        identifier: Entity ID or UID to search for
        entity_type: Optional type filter to narrow search
        
    Returns:
        Dictionary containing:
        - success: bool
        - entity: Dict with entity data
        - file_path: Path to entity file
        
    Raises:
        EntityNotFoundError: If entity does not exist
        AmbiguousEntityError: If multiple entities match
        
    Example:
        >>> operation = ShowOperation("/path/to/registry")
        >>> result = operation.get_entity("P-001")
        >>> print(result["entity"]["title"])
        "My Project"
    """
```

### Documentation Files

When adding features, update relevant documentation:

| Feature Type | Update |
|--------------|--------|
| New CLI command | `docs/COMMANDS.md` |
| New MCP tool | `docs/MCP_INTEGRATION.md` |
| New entity field | `docs/ENTITY_MODEL.md` |
| API change | `docs/API.md` |
| Architecture change | `ARCHITECTURE.md` |

### Changelog

For significant changes, add entry to CHANGELOG.md (when created):

```markdown
## [Unreleased]

### Added
- New `newcmd` command for X functionality (#123)

### Changed
- Improved performance of `list` command (#124)

### Fixed
- Fixed path traversal vulnerability (#125)
```

## Pull Request Process

### Before Submitting

1. ✅ All tests pass: `pytest`
2. ✅ Code is formatted: `black src tests && isort src tests`
3. ✅ Linting passes: `flake8 src tests`
4. ✅ Type checks pass: `mypy src`
5. ✅ Documentation updated
6. ✅ Commit messages are clear

### PR Template

```markdown
## Description

Brief description of changes.

## Related Issues

Fixes #123
Related to #124

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

Describe testing performed:
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist

- [ ] Code follows project conventions
- [ ] Self-reviewed my code
- [ ] Added necessary documentation
- [ ] All tests pass
- [ ] No new warnings
```

### Review Process

1. Automated checks must pass
2. At least one maintainer approval required
3. All review comments addressed
4. Squash and merge for clean history

## For AI Agents

If you are an AI coding agent contributing to HoxCore:

### Start Here

1. **Read first**: [CLAUDE.md](CLAUDE.md) - AI-specific guidance
2. **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) - System design
3. **Conventions**: [CONVENTIONS.md](CONVENTIONS.md) - Coding standards

### Key Files to Understand

```
src/hxc/
├── core/enums.py           # EntityType, EntityStatus (use these, don't create strings)
├── core/operations/        # Business logic (add new operations here)
├── commands/base.py        # BaseCommand pattern (follow for new commands)
├── mcp/tools.py            # MCP tool pattern (follow for new tools)
└── utils/path_security.py  # MUST use for all file I/O
```

### Patterns to Follow

**Operation Pattern**:
```python
class SomeOperation:
    def __init__(self, registry_path: str):
        self.registry_path = Path(registry_path)
    
    def method(self, **params) -> Dict[str, Any]:
        # Validate → Execute → Return structured result
```

**MCP Tool Pattern**:
```python
def some_tool(param: str, registry_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        reg_path = _get_registry_path(registry_path)
        operation = SomeOperation(reg_path)
        return {"success": True, **operation.method(param)}
    except SpecificError as e:
        return {"success": False, "error": str(e)}
```

**Command Pattern**:
```python
class SomeCommand(BaseCommand):
    name = "cmdname"
    help = "Description"
    
    @classmethod
    def register_subparser(cls, subparsers): ...
    
    @classmethod
    def execute(cls, args) -> int:
        # 0 = success, non-zero = error
```

### Critical Rules

1. **Always use path security** for file operations
2. **Never use bare `except:`** - catch specific exceptions
3. **Operations are interface-agnostic** - no CLI or MCP specifics
4. **All public functions need type hints** and docstrings
5. **Run quality checks** before considering work complete

### Testing Your Changes

```bash
# Minimum before submitting
pytest tests/ -v
black --check src tests
isort --check src tests
flake8 src tests
mypy src
```

---

## Questions?

- Open an [issue](https://github.com/SDEscobedo/hoxcore/issues)
- Check existing documentation
- Review similar implementations in codebase

Thank you for contributing to HoxCore!
```