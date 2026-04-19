```markdown
# HoxCore Python API Reference

This document provides a comprehensive reference for the HoxCore Python API. It is designed for developers and AI coding agents who need to integrate with or extend HoxCore programmatically.

## Table of Contents

- [Overview](#overview)
- [Core Enums](#core-enums)
- [Configuration](#configuration)
- [Operations](#operations)
  - [InitOperation](#initoperation)
  - [CreateOperation](#createoperation)
  - [ListOperation](#listoperation)
  - [ShowOperation](#showoperation)
  - [GetPropertyOperation](#getpropertyoperation)
  - [EditOperation](#editoperation)
  - [DeleteOperation](#deleteoperation)
  - [ValidateOperation](#validateoperation)
  - [RegistryOperation](#registryoperation)
- [Utilities](#utilities)
- [MCP Server API](#mcp-server-api)
- [Error Handling](#error-handling)
- [Usage Examples](#usage-examples)

---

## Overview

HoxCore follows a layered architecture where **Operations** contain the core business logic. Operations are interface-agnostic and can be used directly in Python code, through the CLI, or via MCP tools.

### Import Structure

```python
# Core enums
from hxc.core.enums import EntityType, EntityStatus, OutputFormat, SortField

# Configuration
from hxc.core.config import Config

# Operations
from hxc.core.operations.init import InitOperation
from hxc.core.operations.create import CreateOperation
from hxc.core.operations.list import ListOperation
from hxc.core.operations.show import ShowOperation
from hxc.core.operations.get import GetPropertyOperation
from hxc.core.operations.edit import EditOperation
from hxc.core.operations.delete import DeleteOperation
from hxc.core.operations.validate import ValidateOperation
from hxc.core.operations.registry import RegistryOperation

# Utilities
from hxc.utils.helpers import get_project_root, is_valid_registry
from hxc.utils.path_security import resolve_safe_path, get_safe_entity_path

# MCP Server
from hxc.mcp.server import MCPServer, create_server
```

---

## Core Enums

### EntityType

Enumeration of valid entity types in the registry.

```python
from hxc.core.enums import EntityType

class EntityType(Enum):
    PROGRAM = "program"
    PROJECT = "project"
    MISSION = "mission"
    ACTION = "action"
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `values()` | `@classmethod -> List[str]` | Returns list of all valid type values |
| `from_string()` | `@classmethod (value: str) -> EntityType` | Parse string to enum, raises `ValueError` if invalid |
| `get_folder_name()` | `() -> str` | Returns folder name for this type (e.g., `"projects"`) |
| `get_file_prefix()` | `() -> str` | Returns file prefix for this type (e.g., `"proj"`) |

#### Entity Type Mapping

| Type | Value | Folder | File Prefix |
|------|-------|--------|-------------|
| `PROGRAM` | `"program"` | `programs/` | `prog-` |
| `PROJECT` | `"project"` | `projects/` | `proj-` |
| `MISSION` | `"mission"` | `missions/` | `miss-` |
| `ACTION` | `"action"` | `actions/` | `act-` |

#### Usage

```python
from hxc.core.enums import EntityType

# Parse from string
entity_type = EntityType.from_string("project")

# Get folder name
folder = entity_type.get_folder_name()  # "projects"

# Get file prefix
prefix = entity_type.get_file_prefix()  # "proj"

# List all valid values
valid_types = EntityType.values()  # ["program", "project", "mission", "action"]
```

### EntityStatus

Enumeration of valid status values for entities.

```python
from hxc.core.enums import EntityStatus

class EntityStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on-hold"
    CANCELLED = "cancelled"
    PLANNED = "planned"
```

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `values()` | `@classmethod -> List[str]` | Returns list of all valid status values |
| `from_string()` | `@classmethod (value: str) -> EntityStatus` | Parse string to enum, raises `ValueError` if invalid |

### OutputFormat

Enumeration of valid output formats for display commands.

```python
from hxc.core.enums import OutputFormat

class OutputFormat(Enum):
    TABLE = "table"
    YAML = "yaml"
    JSON = "json"
    ID = "id"
    PRETTY = "pretty"
```

### SortField

Enumeration of valid sort fields for list operations.

```python
from hxc.core.enums import SortField

class SortField(Enum):
    TITLE = "title"
    ID = "id"
    DUE_DATE = "due_date"
    STATUS = "status"
    CREATED = "created"
    MODIFIED = "modified"
```

---

## Configuration

### Config

Manages global HoxCore configuration stored at `~/.hxc/config.json`.

```python
from hxc.core.config import Config

class Config:
    DEFAULT_CONFIG_DIR = "~/.hxc"
    DEFAULT_CONFIG_FILE = "config.json"
```

#### Constructor

```python
Config(config_dir: Optional[str] = None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_dir` | `Optional[str]` | `~/.hxc` | Configuration directory path |

#### Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `ensure_config_dir()` | `() -> None` | Create config directory if it doesn't exist |
| `load()` | `() -> Dict[str, Any]` | Load configuration from file |
| `save()` | `(config: Dict[str, Any]) -> None` | Save configuration to file |
| `get()` | `(key: str, default: Any = None) -> Any` | Get configuration value |
| `set()` | `(key: str, value: Any) -> None` | Set configuration value |

#### Usage

```python
from hxc.core.config import Config

config = Config()

# Get registry path
registry_path = config.get("registry_path")

# Set registry path
config.set("registry_path", "/path/to/registry")

# Load all configuration
all_config = config.load()
```

---

## Operations

Operations are the core business logic layer. Each operation class handles a specific category of functionality.

### InitOperation

Initializes a new HoxCore registry with the required directory structure.

**Location**: `hxc.core.operations.init`

#### Constructor

```python
InitOperation(path: str)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` | Path where to initialize the registry |

#### Methods

##### initialize_registry

```python
def initialize_registry(
    self,
    use_git: bool = True,
    commit: bool = True,
    remote_url: Optional[str] = None,
    force_empty_check: bool = True,
) -> Dict[str, Any]
```

Creates a complete registry structure.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `use_git` | `bool` | `True` | Initialize git repository |
| `commit` | `bool` | `True` | Create initial commit (requires `use_git`) |
| `remote_url` | `Optional[str]` | `None` | Git remote URL to configure |
| `force_empty_check` | `bool` | `True` | Require empty directory |

**Returns:**

```python
{
    "registry_path": str,      # Absolute path to registry
    "git_initialized": bool,   # Whether git was initialized
    "committed": bool,         # Whether initial commit was made
    "pushed": bool,            # Whether pushed to remote
    "remote_added": bool,      # Whether remote was configured
}
```

**Raises:**

| Exception | Description |
|-----------|-------------|
| `DirectoryNotEmptyError` | Directory is not empty |
| `GitOperationError` | Git operation failed |
| `InitOperationError` | General initialization failure |

**Created Structure:**

```
<path>/
├── .hxc/
│   └── index.db
├── config.yml
├── programs/
├── projects/
├── missions/
├── actions/
└── .gitignore
```

#### Usage

```python
from hxc.core.operations.init import InitOperation

operation = InitOperation("/path/to/new/registry")
result = operation.initialize_registry(
    use_git=True,
    commit=True,
    remote_url="https://github.com/user/registry.git"
)

print(f"Created registry at: {result['registry_path']}")
```

---

### CreateOperation

Creates new entities in the registry.

**Location**: `hxc.core.operations.create`

#### Constructor

```python
CreateOperation(registry_path: str)
```

#### Methods

##### create_entity

```python
def create_entity(
    self,
    entity_type: EntityType,
    title: str,
    entity_id: Optional[str] = None,
    description: Optional[str] = None,
    status: EntityStatus = EntityStatus.ACTIVE,
    start_date: Optional[str] = None,
    due_date: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    parent: Optional[str] = None,
    use_git: bool = True,
) -> Dict[str, Any]
```

Creates a new entity with the specified properties.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity_type` | `EntityType` | Required | Type of entity to create |
| `title` | `str` | Required | Human-readable title |
| `entity_id` | `Optional[str]` | `None` | Custom ID (must be unique within type) |
| `description` | `Optional[str]` | `None` | Entity description |
| `status` | `EntityStatus` | `ACTIVE` | Initial status |
| `start_date` | `Optional[str]` | `None` | Start date (YYYY-MM-DD) |
| `due_date` | `Optional[str]` | `None` | Due date (YYYY-MM-DD) |
| `category` | `Optional[str]` | `None` | Category path |
| `tags` | `Optional[List[str]]` | `None` | List of tags |
| `parent` | `Optional[str]` | `None` | Parent entity UID or ID |
| `use_git` | `bool` | `True` | Commit changes to git |

**Returns:**

```python
{
    "uid": str,            # Generated unique identifier
    "id": Optional[str],   # Custom ID if provided
    "file_path": str,      # Path to created file
    "entity": Dict,        # Complete entity data
    "git_committed": bool, # Whether committed to git
}
```

**Raises:**

| Exception | Description |
|-----------|-------------|
| `DuplicateIdError` | Custom ID already exists |
| `CreateOperationError` | Creation failed |
| `PathSecurityError` | Path security violation |

#### Usage

```python
from hxc.core.operations.create import CreateOperation
from hxc.core.enums import EntityType, EntityStatus

operation = CreateOperation("/path/to/registry")
result = operation.create_entity(
    entity_type=EntityType.PROJECT,
    title="My New Project",
    entity_id="P-001",
    description="Project description",
    status=EntityStatus.ACTIVE,
    tags=["python", "cli"],
    use_git=True,
)

print(f"Created entity with UID: {result['uid']}")
```

---

### ListOperation

Lists and filters entities from the registry.

**Location**: `hxc.core.operations.list`

#### Constructor

```python
ListOperation(registry_path: str)
```

#### Methods

##### list_entities

```python
def list_entities(
    self,
    entity_types: Optional[List[EntityType]] = None,
    status: Optional[EntityStatus] = None,
    tags: Optional[List[str]] = None,
    category: Optional[str] = None,
    parent: Optional[str] = None,
    identifier: Optional[str] = None,
    query: Optional[str] = None,
    due_before: Optional[str] = None,
    due_after: Optional[str] = None,
    sort_field: SortField = SortField.TITLE,
    descending: bool = False,
    max_items: int = 0,
    include_file_metadata: bool = False,
) -> Dict[str, Any]
```

Lists entities with optional filtering and sorting.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity_types` | `Optional[List[EntityType]]` | `None` | Types to include (all if None) |
| `status` | `Optional[EntityStatus]` | `None` | Filter by status |
| `tags` | `Optional[List[str]]` | `None` | Filter by tags (AND logic) |
| `category` | `Optional[str]` | `None` | Filter by category (exact match) |
| `parent` | `Optional[str]` | `None` | Filter by parent ID |
| `identifier` | `Optional[str]` | `None` | Filter by ID or UID |
| `query` | `Optional[str]` | `None` | Text search in title/description |
| `due_before` | `Optional[str]` | `None` | Due date before YYYY-MM-DD |
| `due_after` | `Optional[str]` | `None` | Due date after YYYY-MM-DD |
| `sort_field` | `SortField` | `TITLE` | Sort field |
| `descending` | `bool` | `False` | Sort descending |
| `max_items` | `int` | `0` | Max items (0 = all) |
| `include_file_metadata` | `bool` | `False` | Include `_file` field |

**Returns:**

```python
{
    "entities": List[Dict],  # List of entity dictionaries
    "count": int,            # Number of entities returned
}
```

##### load_entities

```python
def load_entities(
    self,
    entity_type: EntityType,
    include_file_metadata: bool = False,
) -> List[Dict[str, Any]]
```

Load all entities of a specific type.

##### clean_entities_for_output (static)

```python
@staticmethod
def clean_entities_for_output(
    entities: List[Dict[str, Any]],
    remove_file_metadata: bool = True,
) -> List[Dict[str, Any]]
```

Remove internal metadata fields from entities for output.

#### Usage

```python
from hxc.core.operations.list import ListOperation
from hxc.core.enums import EntityType, EntityStatus, SortField

operation = ListOperation("/path/to/registry")

# List all active projects
result = operation.list_entities(
    entity_types=[EntityType.PROJECT],
    status=EntityStatus.ACTIVE,
    sort_field=SortField.DUE_DATE,
)

for entity in result["entities"]:
    print(f"{entity['title']} - Due: {entity.get('due_date')}")
```

---

### ShowOperation

Retrieves a single entity by identifier.

**Location**: `hxc.core.operations.show`

#### Constructor

```python
ShowOperation(registry_path: str)
```

#### Methods

##### get_entity

```python
def get_entity(
    self,
    identifier: str,
    entity_type: Optional[EntityType] = None,
    include_raw: bool = False,
) -> Dict[str, Any]
```

Retrieve an entity using a two-phase search strategy.

**Search Strategy:**
1. **Fast path**: Check if identifier matches filename pattern (`{prefix}-{uid}.yml`)
2. **Slow path**: Search file contents for ID match

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `identifier` | `str` | Required | ID or UID of the entity |
| `entity_type` | `Optional[EntityType]` | `None` | Type filter (searches all if None) |
| `include_raw` | `bool` | `False` | Include raw YAML content |

**Returns:**

```python
{
    "success": bool,
    "entity": Dict,           # Entity data
    "file_path": str,         # Path to entity file
    "raw_content": str,       # Only if include_raw=True
}
```

**Raises:**

| Exception | Description |
|-----------|-------------|
| `EntityNotFoundError` | Entity does not exist |
| `AmbiguousEntityError` | Multiple entities match |
| `InvalidEntityError` | Entity file is invalid |
| `ShowOperationError` | General retrieval failure |

#### Usage

```python
from hxc.core.operations.show import ShowOperation

operation = ShowOperation("/path/to/registry")

# Get by UID
result = operation.get_entity("proj-12345678")

# Get by custom ID with type filter
result = operation.get_entity("P-001", entity_type=EntityType.PROJECT)

print(f"Title: {result['entity']['title']}")
```

---

### GetPropertyOperation

Retrieves specific properties from an entity.

**Location**: `hxc.core.operations.get`

#### Constructor

```python
GetPropertyOperation(registry_path: str)
```

#### Methods

##### get_property

```python
def get_property(
    self,
    identifier: str,
    property_name: str,
    entity_type: Optional[EntityType] = None,
    index: Optional[int] = None,
    key_filter: Optional[str] = None,
) -> Dict[str, Any]
```

Get a specific property value from an entity.

**Property Categories:**

| Category | Properties |
|----------|------------|
| **SCALAR** | `type`, `uid`, `id`, `title`, `description`, `status`, `start_date`, `due_date`, `completion_date`, `duration_estimate`, `category`, `parent`, `template` |
| **LIST** | `tags`, `children`, `related` |
| **COMPLEX** | `repositories`, `storage`, `databases`, `tools`, `models`, `knowledge_bases` |
| **SPECIAL** | `all` (returns all properties), `path` (returns file path) |

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `identifier` | `str` | Required | Entity ID or UID |
| `property_name` | `str` | Required | Property to retrieve |
| `entity_type` | `Optional[EntityType]` | `None` | Type filter |
| `index` | `Optional[int]` | `None` | Index for list/complex properties |
| `key_filter` | `Optional[str]` | `None` | Filter for complex properties (`key:value`) |

**Returns:**

```python
{
    "success": bool,
    "property": str,          # Normalized property name
    "property_type": str,     # "scalar", "list", "complex", "special"
    "value": Any,             # Property value
    "identifier": str,
}
```

#### Usage

```python
from hxc.core.operations.get import GetPropertyOperation

operation = GetPropertyOperation("/path/to/registry")

# Get scalar property
result = operation.get_property("P-001", "status")
print(f"Status: {result['value']}")

# Get list property
result = operation.get_property("P-001", "tags")
print(f"Tags: {result['value']}")

# Get complex property with filter
result = operation.get_property("P-001", "repositories", key_filter="name:github")
print(f"GitHub repo: {result['value']}")

# Get all properties
result = operation.get_property("P-001", "all")
```

---

### EditOperation

Modifies existing entities.

**Location**: `hxc.core.operations.edit`

#### Constructor

```python
EditOperation(registry_path: str)
```

#### Methods

##### edit_entity

```python
def edit_entity(
    self,
    identifier: str,
    entity_type: Optional[EntityType] = None,
    # Scalar fields
    set_title: Optional[str] = None,
    set_description: Optional[str] = None,
    set_status: Optional[str] = None,
    set_id: Optional[str] = None,
    set_start_date: Optional[str] = None,
    set_due_date: Optional[str] = None,
    set_completion_date: Optional[str] = None,
    set_category: Optional[str] = None,
    set_parent: Optional[str] = None,
    # List operations
    add_tags: Optional[List[str]] = None,
    remove_tags: Optional[List[str]] = None,
    add_children: Optional[List[str]] = None,
    remove_children: Optional[List[str]] = None,
    add_related: Optional[List[str]] = None,
    remove_related: Optional[List[str]] = None,
    # Options
    use_git: bool = True,
) -> Dict[str, Any]
```

Modify entity properties.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `identifier` | `str` | Entity ID or UID |
| `entity_type` | `Optional[EntityType]` | Type filter for disambiguation |
| `set_*` | `Optional[str]` | Set scalar field value |
| `add_tags` | `Optional[List[str]]` | Tags to add (idempotent) |
| `remove_tags` | `Optional[List[str]]` | Tags to remove |
| `add_children` | `Optional[List[str]]` | Children to add |
| `remove_children` | `Optional[List[str]]` | Children to remove |
| `add_related` | `Optional[List[str]]` | Related entities to add |
| `remove_related` | `Optional[List[str]]` | Related entities to remove |
| `use_git` | `bool` | Commit changes to git |

**Returns:**

```python
{
    "changes": List[str],     # List of applied changes
    "entity": Dict,           # Updated entity data
    "file_path": str,         # Path to entity file
    "git_committed": bool,    # Whether committed
}
```

**Raises:**

| Exception | Description |
|-----------|-------------|
| `EntityNotFoundError` | Entity does not exist |
| `DuplicateIdError` | New ID already exists |
| `InvalidValueError` | Invalid field value |
| `NoChangesError` | No changes requested |
| `EditOperationError` | Edit failed |

#### Usage

```python
from hxc.core.operations.edit import EditOperation

operation = EditOperation("/path/to/registry")

result = operation.edit_entity(
    identifier="P-001",
    set_title="Updated Title",
    set_status="completed",
    add_tags=["important", "urgent"],
    remove_tags=["draft"],
    use_git=True,
)

print(f"Applied changes: {result['changes']}")
```

---

### DeleteOperation

Removes entities from the registry.

**Location**: `hxc.core.operations.delete`

#### Constructor

```python
DeleteOperation(registry_path: str)
```

#### Methods

##### get_entity_info

```python
def get_entity_info(
    self,
    identifier: str,
    entity_type: Optional[EntityType] = None,
) -> Dict[str, Any]
```

Get entity information before deletion.

**Returns:**

```python
{
    "entity_title": str,
    "entity_type": str,
    "file_path": str,
}
```

##### delete_entity

```python
def delete_entity(
    self,
    identifier: str,
    entity_type: Optional[EntityType] = None,
    use_git: bool = True,
) -> Dict[str, Any]
```

Delete an entity from the registry.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `identifier` | `str` | Required | Entity ID or UID |
| `entity_type` | `Optional[EntityType]` | `None` | Type filter |
| `use_git` | `bool` | `True` | Commit deletion to git |

**Returns:**

```python
{
    "deleted_title": str,     # Title of deleted entity
    "deleted_type": str,      # Type of deleted entity
    "file_path": str,         # Path to deleted file
    "git_committed": bool,    # Whether committed
}
```

**Raises:**

| Exception | Description |
|-----------|-------------|
| `EntityNotFoundError` | Entity does not exist |
| `AmbiguousEntityError` | Multiple entities match |
| `DeleteOperationError` | Deletion failed |

#### Usage

```python
from hxc.core.operations.delete import DeleteOperation

operation = DeleteOperation("/path/to/registry")

# Get info first (for confirmation)
info = operation.get_entity_info("P-001")
print(f"About to delete: {info['entity_title']}")

# Perform deletion
result = operation.delete_entity("P-001", use_git=True)
print(f"Deleted: {result['deleted_title']}")
```

---

### ValidateOperation

Validates registry integrity and entity data.

**Location**: `hxc.core.operations.validate`

#### Constructor

```python
ValidateOperation(registry_path: str)
```

#### Methods

##### validate_registry

```python
def validate_registry(self) -> ValidationResult
```

Validate the entire registry.

**Checks performed:**
- Required fields (type, uid, title)
- UID uniqueness across all entities
- ID uniqueness within each entity type
- Parent link validation (error for broken links)
- Child link validation (error for broken links)
- Related link validation (warning for broken links)
- Status value validation
- Entity type validation
- Empty file detection
- Invalid YAML detection

**Returns:** `ValidationResult` object with:

```python
class ValidationResult:
    valid: bool                    # No errors found
    errors: List[str]              # Error messages
    warnings: List[str]            # Warning messages
    error_count: int
    warning_count: int
    entities_checked: int
    entities_by_type: Dict[str, int]
```

##### validate_entity

```python
def validate_entity(
    self,
    entity_data: Dict[str, Any],
    check_relationships: bool = True,
) -> EntityValidationResult
```

Validate a single entity's data structure.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity_data` | `Dict[str, Any]` | Required | Entity data to validate |
| `check_relationships` | `bool` | `True` | Verify relationships exist |

**Returns:** `EntityValidationResult` object with:

```python
class EntityValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]
```

#### Usage

```python
from hxc.core.operations.validate import ValidateOperation

operation = ValidateOperation("/path/to/registry")

# Validate entire registry
result = operation.validate_registry()
if result.valid:
    print(f"Registry valid! Checked {result.entities_checked} entities.")
else:
    print(f"Found {result.error_count} errors:")
    for error in result.errors:
        print(f"  - {error}")

# Validate entity data before creation
entity_data = {
    "type": "project",
    "uid": "proj-12345678",
    "title": "Test Project",
    "status": "active",
}
result = operation.validate_entity(entity_data)
```

---

### RegistryOperation

Manages registry configuration and discovery.

**Location**: `hxc.core.operations.registry`

#### Class Methods (Static)

##### validate_registry_path

```python
@staticmethod
def validate_registry_path(path: str) -> Dict[str, Any]
```

Validate if a path is a valid HoxCore registry.

**Returns:**

```python
{
    "valid": bool,
    "path": str,          # Resolved absolute path
    "missing": List[str], # Missing required components
}
```

#### Instance Methods

##### get_registry_path

```python
def get_registry_path(
    self,
    include_discovery: bool = True,
) -> Dict[str, Any]
```

Get the currently configured registry path.

**Returns:**

```python
{
    "success": bool,
    "path": Optional[str],
    "is_valid": bool,
    "source": str,            # "config", "discovered", "none"
    "discovered_path": Optional[str],
    "validation_errors": List[str],
}
```

##### set_registry_path

```python
def set_registry_path(
    self,
    path: str,
    validate: bool = True,
) -> Dict[str, Any]
```

Set the default registry path in configuration.

##### clear_registry_path

```python
def clear_registry_path(self) -> Dict[str, Any]
```

Clear the configured registry path.

##### list_registries

```python
def list_registries(self) -> Dict[str, Any]
```

List all known registries.

##### discover_registry

```python
def discover_registry(self) -> Dict[str, Any]
```

Attempt to discover a registry in the current directory tree.

---

## Utilities

### Path Security

**Location**: `hxc.utils.path_security`

**CRITICAL**: All file I/O must use these utilities to prevent path traversal attacks.

#### resolve_safe_path

```python
def resolve_safe_path(base_dir: str, relative_path: str) -> Path
```

Resolve a path and verify it stays within the base directory.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `base_dir` | `str` | Base directory (must not be escaped) |
| `relative_path` | `str` | Path to resolve |

**Raises:** `PathSecurityError` if path escapes base directory.

#### get_safe_entity_path

```python
def get_safe_entity_path(
    registry_path: str,
    entity_type: EntityType,
    filename: str,
) -> Path
```

Get a safe path for an entity file.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `registry_path` | `str` | Registry root path |
| `entity_type` | `EntityType` | Entity type |
| `filename` | `str` | Entity filename |

**Raises:** `PathSecurityError` if path validation fails.

#### Usage

```python
from hxc.utils.path_security import (
    resolve_safe_path,
    get_safe_entity_path,
    PathSecurityError,
)
from hxc.core.enums import EntityType

# Safe path resolution
try:
    safe_path = resolve_safe_path("/registry", "projects/../../../etc/passwd")
except PathSecurityError as e:
    print(f"Blocked: {e}")

# Entity path
entity_path = get_safe_entity_path(
    "/registry",
    EntityType.PROJECT,
    "proj-12345678.yml"
)
```

### Helpers

**Location**: `hxc.utils.helpers`

#### get_project_root

```python
def get_project_root(start_dir: Optional[str] = None) -> Optional[str]
```

Find registry root by walking up directory tree looking for `.hxc/` marker or registry structure.

#### is_valid_registry

```python
def is_valid_registry(path: str) -> bool
```

Check if path contains a valid HoxCore registry structure.

---

## MCP Server API

### MCPServer

**Location**: `hxc.mcp.server`

#### Constructor

```python
MCPServer(
    registry_path: Optional[str] = None,
    read_only: bool = False,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `registry_path` | `Optional[str]` | Auto-detect | Path to registry |
| `read_only` | `bool` | `False` | Omit write tools |

#### Methods

##### handle_request

```python
def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]
```

Handle a JSON-RPC MCP request.

##### run_stdio

```python
def run_stdio(self) -> None
```

Run server using stdio transport.

##### get_capabilities

```python
def get_capabilities(self) -> Dict[str, Any]
```

Get server capabilities.

##### register_tool

```python
def register_tool(self, name: str, func: Callable) -> None
```

Register a custom tool.

##### register_resource

```python
def register_resource(self, name: str, func: Callable) -> None
```

Register a custom resource.

##### register_prompt

```python
def register_prompt(self, prompt_data: Dict[str, Any]) -> None
```

Register a custom prompt.

### create_server

```python
def create_server(
    registry_path: Optional[str] = None,
    read_only: bool = False,
) -> MCPServer
```

Factory function to create a configured MCP server instance.

#### Usage

```python
from hxc.mcp.server import create_server

# Create server
server = create_server(
    registry_path="/path/to/registry",
    read_only=True,
)

# Get capabilities
caps = server.get_capabilities()
print(f"Available tools: {caps['tools']}")

# Handle request
response = server.handle_request({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "list_entities",
        "arguments": {"entity_type": "project"}
    }
})
```

### MCP Tools

**Location**: `hxc.mcp.tools`

All MCP tools follow a consistent pattern:

```python
def tool_name(
    param: str,
    optional_param: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Tool description."""
    # Returns {"success": True, ...} or {"success": False, "error": "..."}
```

See [MCP_INTEGRATION.md](MCP_INTEGRATION.md) for complete tool documentation.

---

## Error Handling

### Exception Hierarchy

```
Exception
├── InitOperationError
│   ├── DirectoryNotEmptyError
│   └── GitOperationError
├── CreateOperationError
│   └── DuplicateIdError
├── ListOperationError
├── ShowOperationError
│   ├── EntityNotFoundError
│   ├── AmbiguousEntityError
│   └── InvalidEntityError
├── GetPropertyOperationError
├── EditOperationError
│   ├── EntityNotFoundError
│   ├── DuplicateIdError
│   ├── InvalidValueError
│   └── NoChangesError
├── DeleteOperationError
│   ├── EntityNotFoundError
│   └── AmbiguousEntityError
├── ValidateOperationError
├── RegistryOperationError
│   └── InvalidRegistryPathError
└── PathSecurityError
```

### Error Handling Pattern

```python
from hxc.core.operations.create import (
    CreateOperation,
    CreateOperationError,
    DuplicateIdError,
)
from hxc.utils.path_security import PathSecurityError

try:
    operation = CreateOperation(registry_path)
    result = operation.create_entity(
        entity_type=EntityType.PROJECT,
        title="My Project",
        entity_id="P-001",
    )
except DuplicateIdError as e:
    print(f"ID already exists: {e.entity_id}")
except CreateOperationError as e:
    print(f"Creation failed: {e}")
except PathSecurityError as e:
    print(f"Security violation: {e}")
```

---

## Usage Examples

### Complete Workflow

```python
from hxc.core.operations.init import InitOperation
from hxc.core.operations.create import CreateOperation
from hxc.core.operations.list import ListOperation
from hxc.core.operations.edit import EditOperation
from hxc.core.operations.validate import ValidateOperation
from hxc.core.enums import EntityType, EntityStatus, SortField

# 1. Initialize registry
init_op = InitOperation("/path/to/registry")
init_op.initialize_registry(use_git=True)

registry_path = "/path/to/registry"

# 2. Create a program
create_op = CreateOperation(registry_path)
program = create_op.create_entity(
    entity_type=EntityType.PROGRAM,
    title="Q1 2024 Initiatives",
    entity_id="PROG-Q1-2024",
)

# 3. Create projects under the program
project1 = create_op.create_entity(
    entity_type=EntityType.PROJECT,
    title="Website Redesign",
    entity_id="P-001",
    parent=program["uid"],
    tags=["web", "design"],
)

project2 = create_op.create_entity(
    entity_type=EntityType.PROJECT,
    title="API Development",
    entity_id="P-002",
    parent=program["uid"],
    tags=["api", "backend"],
)

# 4. List active projects
list_op = ListOperation(registry_path)
result = list_op.list_entities(
    entity_types=[EntityType.PROJECT],
    status=EntityStatus.ACTIVE,
    sort_field=SortField.TITLE,
)
print(f"Found {result['count']} active projects")

# 5. Update a project
edit_op = EditOperation(registry_path)
edit_op.edit_entity(
    identifier="P-001",
    set_status="completed",
    add_tags=["launched"],
)

# 6. Validate registry
validate_op = ValidateOperation(registry_path)
validation = validate_op.validate_registry()
if validation.valid:
    print("Registry is valid!")
else:
    for error in validation.errors:
        print(f"Error: {error}")
```

### Building Custom Tools

```python
from typing import Any, Dict, Optional
from hxc.core.operations.list import ListOperation
from hxc.core.enums import EntityType, EntityStatus

def get_overdue_projects(
    registry_path: str,
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get all projects that are past their due date.
    
    Args:
        registry_path: Path to the registry
        as_of_date: Reference date (YYYY-MM-DD), defaults to today
        
    Returns:
        Dictionary with overdue projects
    """
    from datetime import date
    
    if as_of_date is None:
        as_of_date = date.today().isoformat()
    
    operation = ListOperation(registry_path)
    result = operation.list_entities(
        entity_types=[EntityType.PROJECT],
        status=EntityStatus.ACTIVE,
        due_before=as_of_date,
    )
    
    return {
        "overdue_count": result["count"],
        "projects": result["entities"],
        "as_of": as_of_date,
    }
```

---

## Version Compatibility

| HoxCore Version | Python Version | Notes |
|-----------------|----------------|-------|
| 0.1.x | 3.8+ | Current stable |

---

## See Also

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [CONVENTIONS.md](../CONVENTIONS.md) - Code conventions
- [COMMANDS.md](COMMANDS.md) - CLI reference
- [ENTITY_MODEL.md](ENTITY_MODEL.md) - Entity specification
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md) - MCP documentation
```