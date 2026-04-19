```markdown
# HoxCore Code Conventions

This document defines the coding standards, patterns, and conventions for the HoxCore project. It is designed for AI coding agents and developers to ensure consistent, maintainable code.

## Table of Contents

- [Code Style](#code-style)
- [Naming Conventions](#naming-conventions)
- [File Organization](#file-organization)
- [Type Hints](#type-hints)
- [Documentation](#documentation)
- [Error Handling](#error-handling)
- [Security Patterns](#security-patterns)
- [Testing Conventions](#testing-conventions)
- [Git Conventions](#git-conventions)
- [Import Organization](#import-organization)
- [Design Patterns](#design-patterns)

---

## Code Style

### Formatting Tools

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **Black** | Code formatting | Line length: 88, Python 3.8+ |
| **isort** | Import sorting | Black-compatible profile |
| **Flake8** | Linting | Standard rules |
| **mypy** | Type checking | Strict mode |

### Line Length

- **Maximum**: 88 characters (Black default)
- **Docstrings**: Can extend to 88, but prefer wrapping at ~72 for readability

### String Quotes

- **Prefer double quotes** for strings: `"string"`
- **Single quotes** acceptable for strings containing double quotes
- **Triple double quotes** for docstrings: `"""Docstring"""`

### Trailing Commas

Use trailing commas in multi-line structures:

```python
# Good
result = {
    "success": True,
    "data": value,
    "count": 10,
}

# Also good for function calls
operation.create_entity(
    entity_type=EntityType.PROJECT,
    title="Title",
    use_git=False,
)
```

### Blank Lines

- **Two blank lines** before top-level class/function definitions
- **One blank line** between method definitions in a class
- **One blank line** to separate logical sections within a function

---

## Naming Conventions

### General Rules

| Element | Convention | Example |
|---------|------------|---------|
| Modules | `snake_case` | `path_security.py` |
| Classes | `PascalCase` | `CreateOperation` |
| Functions/Methods | `snake_case` | `create_entity` |
| Variables | `snake_case` | `entity_type` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_CONFIG_DIR` |
| Private | `_leading_underscore` | `_internal_method` |
| Type Variables | `PascalCase` | `EntityType` |

### Specific Patterns

#### Operations

```python
class {Action}Operation:           # CreateOperation, ListOperation
class {Action}OperationError:      # CreateOperationError (base exception)
class {Specific}Error:             # DuplicateIdError (specific exception)
```

#### Commands

```python
class {Action}Command(BaseCommand):  # CreateCommand, ListCommand
    name = "{action}"                # "create", "list"
```

#### MCP Tools

```python
def {action}_entity_tool():         # create_entity_tool, list_entities_tool
def {action}_{noun}_tool():         # get_registry_path_tool
```

#### Entity-Related

```python
entity_type: EntityType             # Not 'type' (reserved keyword)
entity_id: str                      # Human-readable ID (not 'id' for clarity)
uid: str                            # System-generated unique identifier
identifier: str                     # When accepting either ID or UID
```

### Abbreviations

- **Avoid abbreviations** in public APIs
- **Acceptable abbreviations**: `id`, `uid`, `config`, `dir`, `path`, `args`
- **Spell out** in documentation: "identifier" not "id"

---

## File Organization

### Module Structure

```python
"""
Module docstring describing purpose.
"""

# Standard library imports
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
import yaml

# Local imports
from hxc.core.enums import EntityType
from hxc.utils.path_security import resolve_safe_path


# Constants
DEFAULT_VALUE = "default"


# Exceptions (if module-specific)
class ModuleError(Exception):
    """Base exception for this module."""
    pass


# Main classes/functions
class MainClass:
    """Class docstring."""
    pass


# Helper functions (private)
def _helper_function():
    """Helper docstring."""
    pass
```

### Class Structure

```python
class SomeOperation:
    """
    Class docstring with description.
    
    Attributes:
        registry_path: Path to the HoxCore registry
    """

    # Class constants
    DEFAULT_VALUE = "default"

    def __init__(self, registry_path: str):
        """Initialize with registry path."""
        self.registry_path = Path(registry_path)

    # Public methods (alphabetical or logical grouping)
    def public_method(self) -> Dict[str, Any]:
        """Public method docstring."""
        pass

    # Private methods
    def _private_method(self) -> None:
        """Private helper method."""
        pass

    # Static/class methods at the end
    @staticmethod
    def static_method() -> str:
        """Static method docstring."""
        pass
```

### One Class Per File

- Each file should contain **one primary class** or a cohesive set of related functions
- Exception classes can be in the same file as the operation they relate to
- Utility functions that support a single class go in the same file

---

## Type Hints

### Required Locations

- **All public function parameters**
- **All public function return types**
- **Class attributes in `__init__`**
- **Module-level variables** when type is not obvious

### Type Hint Style

```python
from typing import Any, Dict, List, Optional, Union

# Function signatures
def get_entity(
    self,
    identifier: str,
    entity_type: Optional[EntityType] = None,
) -> Dict[str, Any]:
    ...

# Optional parameters
def method(
    required: str,
    optional: Optional[str] = None,
    with_default: str = "default",
) -> bool:
    ...

# Complex types
def process(
    items: List[Dict[str, Any]],
    callback: Optional[Callable[[str], bool]] = None,
) -> Union[Dict[str, Any], None]:
    ...
```

### Return Type Patterns

| Return Scenario | Type Hint |
|-----------------|-----------|
| Dictionary result | `Dict[str, Any]` |
| Optional value | `Optional[str]` |
| Success or None | `Optional[Dict[str, Any]]` |
| Boolean check | `bool` |
| No return value | `None` |
| Exit code | `int` |

### Avoid `Any` When Possible

```python
# Prefer specific types
entities: List[Dict[str, Any]]  # OK - entity structure is dynamic

# Avoid
data: Any  # Too vague - specify structure if known
```

---

## Documentation

### Docstring Format

Use **Google-style docstrings**:

```python
def create_entity(
    self,
    entity_type: EntityType,
    title: str,
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a new entity in the registry.
    
    This method generates a unique UID, validates the optional ID for
    uniqueness within the entity type, and writes the entity YAML file.
    
    Args:
        entity_type: Type of entity to create (program, project, mission, action)
        title: Human-readable title for the entity
        entity_id: Optional custom ID. Must be unique within entity type.
                   If not provided, only UID is used for identification.
    
    Returns:
        Dictionary containing:
        - uid: str - Generated unique identifier
        - id: Optional[str] - Custom ID if provided
        - file_path: str - Path to created YAML file
        - entity: Dict - Complete entity data
        - git_committed: bool - Whether changes were committed
    
    Raises:
        DuplicateIdError: If entity_id already exists for this type
        CreateOperationError: If entity creation fails
        PathSecurityError: If path validation fails
    
    Example:
        >>> operation = CreateOperation("/path/to/registry")
        >>> result = operation.create_entity(
        ...     entity_type=EntityType.PROJECT,
        ...     title="My Project",
        ...     entity_id="P-001",
        ... )
        >>> print(result["uid"])
        'proj-a1b2c3d4'
    """
```

### Docstring Requirements

| Element | Required | Notes |
|---------|----------|-------|
| One-line summary | Yes | First line, imperative mood |
| Extended description | If complex | Explain behavior, not implementation |
| Args | If any parameters | All parameters documented |
| Returns | If returns value | Describe structure for dicts |
| Raises | If raises exceptions | All custom exceptions |
| Example | For public APIs | Show typical usage |

### Comment Guidelines

```python
# Good: Explain WHY, not WHAT
# Use fast path first since entity files are named by UID
for entity_type in EntityType:
    file_path = self._get_entity_path(entity_type, identifier)

# Bad: Restates the code
# Loop through entity types
for entity_type in EntityType:

# Good: Explain non-obvious behavior
# Git marks files as read-only; clear flag before deletion
os.chmod(path, stat.S_IWRITE)

# Section headers for long functions
# --- Validation ---
if not title:
    raise ValueError("Title is required")

# --- Entity Generation ---
uid = self._generate_uid(entity_type)
```

---

## Error Handling

### Exception Hierarchy

```python
# Base exception for operation
class CreateOperationError(Exception):
    """Base exception for CreateOperation."""
    pass

# Specific exceptions inherit from base
class DuplicateIdError(CreateOperationError):
    """Raised when entity ID already exists."""
    
    def __init__(self, entity_id: str, entity_type: str):
        self.entity_id = entity_id
        self.entity_type = entity_type
        super().__init__(
            f"ID '{entity_id}' already exists for type '{entity_type}'"
        )
```

### Exception Naming

- Base: `{Operation}Error` or `{Module}Error`
- Specific: `{Condition}Error` - e.g., `EntityNotFoundError`, `DuplicateIdError`

### Catching Exceptions

```python
# Good: Specific exceptions, proper handling
try:
    result = operation.create_entity(...)
except DuplicateIdError as e:
    return {"success": False, "error": str(e), "duplicate_id": e.entity_id}
except CreateOperationError as e:
    return {"success": False, "error": str(e)}
except PathSecurityError as e:
    return {"success": False, "error": f"Security error: {e}"}
except Exception as e:
    return {"success": False, "error": f"Unexpected error: {e}"}

# Bad: Bare except or overly broad
try:
    result = operation.create_entity(...)
except:  # Never do this
    return {"success": False, "error": "Something went wrong"}
```

### Return Value Pattern for Operations

Operations return structured dictionaries:

```python
# Success case
return {
    "success": True,
    "uid": uid,
    "entity": entity_data,
    "file_path": str(file_path),
}

# MCP tool wrapper adds consistent error structure
return {
    "success": False,
    "error": "Human-readable error message",
    "identifier": identifier,  # Context for debugging
}
```

---

## Security Patterns

### Path Traversal Prevention

**CRITICAL**: All file I/O must use path security utilities.

```python
from hxc.utils.path_security import (
    resolve_safe_path,
    get_safe_entity_path,
    PathSecurityError,
)

# Reading files
file_path = get_safe_entity_path(registry_path, entity_type, filename)
with open(file_path, "r") as f:
    data = yaml.safe_load(f)

# Writing files
safe_path = get_safe_entity_path(registry_path, entity_type, f"{uid}.yml")
with open(safe_path, "w") as f:
    yaml.dump(data, f)

# Generic path resolution
resolved = resolve_safe_path(base_dir, user_provided_path)
```

**Never do this:**

```python
# DANGEROUS: Path injection vulnerability
file_path = Path(registry_path) / user_input / "file.yml"

# DANGEROUS: String concatenation with user input
path = f"{registry_path}/{entity_type}/{filename}"
```

### Input Validation

```python
# Validate against enums, not strings
entity_type = EntityType.from_string(user_input)  # Raises ValueError if invalid

# Validate status
status = EntityStatus.from_string(status_input)  # Raises ValueError if invalid

# Date validation
from datetime import datetime
try:
    date = datetime.strptime(date_string, "%Y-%m-%d").date()
except ValueError:
    raise InvalidValueError(f"Invalid date format: {date_string}")
```

### YAML Safety

```python
# Always use safe_load
data = yaml.safe_load(file_content)  # Good

# Never use unsafe load
data = yaml.load(file_content)  # DANGEROUS - allows arbitrary code execution
```

---

## Testing Conventions

### Test File Naming

```
tests/
├── test_cli.py                    # CLI integration tests
├── test_commands/
│   └── test_create.py             # Tests for CreateCommand
├── test_operations/
│   └── test_create.py             # Tests for CreateOperation
└── test_mcp/
    └── test_tools.py              # Tests for MCP tools
```

### Test Class/Function Naming

```python
class TestCreateOperation:
    """Tests for CreateOperation class."""

    def test_create_project_success(self):
        """Test successful project creation."""
        pass

    def test_create_with_duplicate_id_raises_error(self):
        """Test that duplicate IDs raise DuplicateIdError."""
        pass

    def test_create_without_git_skips_commit(self):
        """Test that use_git=False skips git operations."""
        pass
```

### Test Structure (Arrange-Act-Assert)

```python
def test_create_project_success(self, temp_registry):
    """Test successful project creation."""
    # Arrange
    operation = CreateOperation(str(temp_registry))
    
    # Act
    result = operation.create_entity(
        entity_type=EntityType.PROJECT,
        title="Test Project",
        use_git=False,
    )
    
    # Assert
    assert result["success"] is True
    assert result["uid"].startswith("proj-")
    assert result["entity"]["title"] == "Test Project"
    assert (temp_registry / "projects" / f"{result['uid']}.yml").exists()
```

### Fixtures

```python
@pytest.fixture
def temp_registry(tmp_path):
    """Create initialized registry for testing."""
    operation = InitOperation(str(tmp_path))
    operation.initialize_registry(use_git=False)
    return tmp_path

@pytest.fixture
def sample_project(temp_registry):
    """Create sample project entity."""
    operation = CreateOperation(str(temp_registry))
    return operation.create_entity(
        entity_type=EntityType.PROJECT,
        title="Sample Project",
        use_git=False,
    )
```

### Test Markers

```python
@pytest.mark.unit           # Fast, isolated tests
@pytest.mark.integration    # Filesystem/external resource tests
@pytest.mark.mcp            # MCP-specific tests
```

---

## Git Conventions

### Commit Messages

Format: `<type>(<scope>): <description>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code change that neither fixes bug nor adds feature
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(create): add support for custom entity IDs
fix(list): handle empty registry gracefully
docs(readme): update installation instructions
refactor(operations): extract common validation logic
test(mcp): add tests for create_entity_tool
chore(deps): update PyYAML to 6.0.1
```

### Branch Names

```
feature/add-custom-ids
fix/list-empty-registry
docs/update-api-reference
refactor/extract-validation
```

### Entity Git Messages (Auto-generated)

Operations generate structured commit messages:

```python
# Create
f"Create {entity_type}: {title}"

# Edit
f"Edit {entity_type} {identifier}: {', '.join(changed_fields)}"

# Delete
f"Delete {entity_type}: {title} ({uid})"
```

---

## Import Organization

### Import Order

1. **Standard library** (os, sys, pathlib, typing, etc.)
2. **Third-party packages** (yaml, pytest, etc.)
3. **Local imports** (hxc.*)

```python
# Standard library
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party
import yaml

# Local - absolute imports preferred
from hxc.commands.base import BaseCommand
from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.create import CreateOperation
from hxc.utils.path_security import PathSecurityError, resolve_safe_path
```

### Import Style

```python
# Good: Explicit imports
from hxc.core.enums import EntityType, EntityStatus

# Good: Module import for many items
from hxc.core import enums
entity_type = enums.EntityType.PROJECT

# Avoid: Star imports
from hxc.core.enums import *  # Don't do this
```

---

## Design Patterns

### Operation Pattern

Operations are the core business logic layer:

```python
class SomeOperation:
    """
    Performs some action on registry entities.
    
    Operations are interface-agnostic and should not depend on
    CLI arguments or MCP request structures.
    """

    def __init__(self, registry_path: str):
        """Initialize with registry path."""
        self.registry_path = Path(registry_path)

    def perform_action(
        self,
        required_param: str,
        optional_param: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform the action.
        
        Args:
            required_param: Description
            optional_param: Description
            
        Returns:
            Structured result dictionary
            
        Raises:
            SomeOperationError: On failure
        """
        # Validate inputs
        self._validate_inputs(required_param)
        
        # Perform operation
        result = self._internal_logic(required_param)
        
        # Return structured result
        return {
            "success": True,
            "data": result,
        }

    def _validate_inputs(self, param: str) -> None:
        """Validate input parameters."""
        if not param:
            raise SomeOperationError("Parameter is required")

    def _internal_logic(self, param: str) -> Any:
        """Internal implementation detail."""
        pass
```

### MCP Tool Pattern

MCP tools wrap operations with consistent error handling:

```python
def some_tool(
    required_param: str,
    optional_param: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tool description for LLM consumption.
    
    Args:
        required_param: Description
        optional_param: Description
        registry_path: Optional registry path (uses default if not provided)
    
    Returns:
        Dictionary with success status and result or error
    """
    try:
        # Get registry path
        reg_path = _get_registry_path(registry_path)
        if not reg_path:
            return {"success": False, "error": "No registry found"}
        
        # Execute operation
        operation = SomeOperation(reg_path)
        result = operation.perform_action(
            required_param=required_param,
            optional_param=optional_param,
        )
        
        return {"success": True, **result}
    
    except SpecificError as e:
        return {"success": False, "error": str(e)}
    except SomeOperationError as e:
        return {"success": False, "error": str(e)}
    except PathSecurityError as e:
        return {"success": False, "error": f"Security error: {e}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}
```

### Command Pattern

Commands handle CLI argument parsing and output formatting:

```python
class SomeCommand(BaseCommand):
    """Command description."""

    name = "cmdname"
    help = "Brief help text"

    @classmethod
    def register_subparser(
        cls, subparsers: argparse._SubParsersAction
    ) -> argparse.ArgumentParser:
        """Register command arguments."""
        parser = subparsers.add_parser(cls.name, help=cls.help)
        parser.add_argument("required", help="Required argument")
        parser.add_argument("--optional", help="Optional argument")
        parser.add_argument(
            "--format",
            choices=["table", "yaml", "json"],
            default="table",
            help="Output format",
        )
        return parser

    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        """Execute the command."""
        try:
            # Get registry
            registry_path = RegistryCommand.get_registry_path()
            if not registry_path:
                print("Error: No registry found", file=sys.stderr)
                return 1
            
            # Execute operation
            operation = SomeOperation(registry_path)
            result = operation.perform_action(
                required_param=args.required,
                optional_param=args.optional,
            )
            
            # Format output
            cls._print_result(result, args.format)
            return 0
            
        except SomeOperationError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

    @classmethod
    def _print_result(cls, result: Dict[str, Any], format: str) -> None:
        """Format and print result."""
        if format == "json":
            print(json.dumps(result, indent=2))
        elif format == "yaml":
            print(yaml.dump(result, default_flow_style=False))
        else:
            # Table format
            print(f"Result: {result['data']}")
```

### Two-Phase Entity Lookup

Entity retrieval uses an optimized search strategy:

```python
def get_entity(self, identifier: str) -> Dict[str, Any]:
    """
    Retrieve entity using two-phase search.
    
    Phase 1 (fast): Check if identifier matches filename pattern
    Phase 2 (slow): Search file contents for ID match
    """
    # Phase 1: Fast path - files are named {prefix}-{uid}.yml
    for entity_type in EntityType:
        file_path = self._build_file_path(entity_type, identifier)
        if file_path.exists():
            return self._load_entity(file_path)
    
    # Phase 2: Slow path - search file contents
    for entity_type in EntityType:
        for file_path in self._list_entity_files(entity_type):
            entity = self._load_entity(file_path)
            if entity.get("id") == identifier:
                return entity
    
    raise EntityNotFoundError(identifier)
```

---

## Quick Reference

### Common Patterns

```python
# Entity type validation
entity_type = EntityType.from_string(type_string)

# Status validation
status = EntityStatus.from_string(status_string)

# Safe file path
path = get_safe_entity_path(registry_path, entity_type, filename)

# YAML operations
data = yaml.safe_load(content)
output = yaml.dump(data, default_flow_style=False)

# Return structure
return {"success": True, "data": result}
return {"success": False, "error": "message"}
```

### Checklist for New Code

- [ ] Type hints on all public functions
- [ ] Docstrings with Args, Returns, Raises
- [ ] Path security for all file I/O
- [ ] Specific exception handling
- [ ] Tests with arrange-act-assert
- [ ] Enum validation for constrained values
- [ ] Consistent return structures

---

## Version

This conventions document applies to HoxCore v0.1.x and will be updated as patterns evolve.
```