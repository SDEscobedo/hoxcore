```markdown
# HoxCore Entity Model Specification

This document provides a comprehensive specification of the HoxCore entity model. It is designed for developers and AI coding agents who need to understand, create, or manipulate HoxCore entities.

## Table of Contents

- [Overview](#overview)
- [Entity Types](#entity-types)
- [Identifier System](#identifier-system)
- [Field Reference](#field-reference)
  - [Required Fields](#required-fields)
  - [Status and Lifecycle](#status-and-lifecycle)
  - [Classification Fields](#classification-fields)
  - [Relationship Fields](#relationship-fields)
  - [Integration Fields](#integration-fields)
- [Field Categories](#field-categories)
- [Validation Rules](#validation-rules)
- [File Naming and Storage](#file-naming-and-storage)
- [Complete Examples](#complete-examples)
- [Schema Reference](#schema-reference)

---

## Overview

HoxCore entities are the fundamental units managed by the registry system. All entities share a **unified YAML definition**, with semantic differences expressed through the `type` field and associated metadata.

### Core Principles

1. **Immutability of UIDs**: Once generated, a UID never changes
2. **Type-Specific Folders**: Entities are stored in type-specific directories
3. **Git-Native**: Entity files are designed for version control
4. **Human and Machine Readable**: YAML format balances readability with parseability
5. **Declarative**: No executable code in entity definitions

### Entity Definition Structure

```yaml
# --- Identity ---
type: project                    # Required: Entity type
uid: proj-12345678               # Required: System-generated unique identifier
id: P-001                        # Optional: Human-defined identifier

# --- Core Metadata ---
title: "Example Project"         # Required: Human-readable title
description: "..."               # Optional: Detailed description
status: active                   # Optional: Lifecycle status

# --- Temporal Fields ---
start_date: 2024-01-01           # Optional: Start date
due_date: 2024-04-01             # Optional: Target completion date
completion_date: null            # Optional: Actual completion date
duration_estimate: 90d           # Optional: Estimated duration

# --- Classification ---
category: software.dev/cli-tool  # Optional: Hierarchical category
tags: [cli, python, tools]       # Optional: Searchable keywords
template: software.dev/cli-tool  # Optional: Template reference

# --- Relationships ---
parent: prog-00000001            # Optional: Parent entity reference
children: []                     # Optional: Child entity references
related: []                      # Optional: Related entity references

# --- Integrations ---
repositories: []                 # Optional: Version control integrations
storage: []                      # Optional: Storage integrations
databases: []                    # Optional: Database connections
tools: []                        # Optional: Project management tools
models: []                       # Optional: LLM model references
knowledge_bases: []              # Optional: Knowledge base references
```

---

## Entity Types

HoxCore manages four fundamental entity types, each with distinct semantic meaning:

### Program

**Purpose**: Abstract container grouping related initiatives

**Characteristics**:
- Highest-level organizational unit
- Typically has no parent (or another program as parent)
- Contains projects, missions, or actions as children
- Long-lived, spanning multiple quarters or years

**File Prefix**: `prog-`  
**Storage Folder**: `programs/`

**Example Use Cases**:
- "Q1 2024 Strategic Initiatives"
- "Digital Transformation Program"
- "Research & Development Portfolio"

```yaml
type: program
uid: prog-a1b2c3d4
id: PROG-Q1-2024
title: "Q1 2024 Initiatives"
description: "Strategic initiatives for Q1 2024"
status: active
start_date: 2024-01-01
due_date: 2024-03-31
children:
  - proj-11111111
  - proj-22222222
  - miss-33333333
```

### Project

**Purpose**: Object-like effort with concrete outputs/deliverables

**Characteristics**:
- Has defined scope and deliverables
- Clear start and end points
- May have subtasks or child entities
- Most common entity type for software work

**File Prefix**: `proj-`  
**Storage Folder**: `projects/`

**Example Use Cases**:
- "Website Redesign"
- "API Development"
- "Mobile App v2.0"
- "Documentation Overhaul"

```yaml
type: project
uid: proj-e5f6g7h8
id: P-001
title: "Website Redesign"
description: "Complete redesign of company website with modern UI/UX"
status: active
category: software.dev/frontend
tags: [web, frontend, design, priority]
start_date: 2024-01-15
due_date: 2024-06-01
parent: prog-a1b2c3d4
repositories:
  - name: github
    url: https://github.com/company/website
```

### Mission

**Purpose**: Event-like or execution-oriented effort with clear culmination

**Characteristics**:
- Has a specific target date or event
- Success is often binary (achieved or not)
- Time-bound with urgency
- Culminates in a specific moment or deliverable

**File Prefix**: `miss-`  
**Storage Folder**: `missions/`

**Example Use Cases**:
- "Product Launch Event"
- "Conference Presentation"
- "System Migration Cutover"
- "Certification Audit"

```yaml
type: mission
uid: miss-i9j0k1l2
id: M-001
title: "Product Launch"
description: "Launch new product at industry conference"
status: planned
category: marketing/launch
tags: [launch, conference, high-priority]
start_date: 2024-05-01
due_date: 2024-06-15
parent: prog-a1b2c3d4
related:
  - proj-e5f6g7h8
```

### Action

**Purpose**: Ongoing or recurring activity without a defined end

**Characteristics**:
- No fixed completion date
- Recurring or continuous nature
- Maintenance or operational activities
- May have periodic reviews

**File Prefix**: `act-`  
**Storage Folder**: `actions/`

**Example Use Cases**:
- "Weekly Team Standup"
- "Quarterly Security Reviews"
- "Continuous Documentation Updates"
- "Customer Support Rotation"

```yaml
type: action
uid: act-m3n4o5p6
id: A-001
title: "Weekly Code Review"
description: "Team code review sessions every Friday"
status: active
category: process/engineering
tags: [recurring, team, code-quality]
start_date: 2024-01-01
# Note: No due_date for ongoing actions
```

### Type Selection Guidelines

| Criterion | Program | Project | Mission | Action |
|-----------|---------|---------|---------|--------|
| Has concrete deliverables | Rarely | Yes | Sometimes | Rarely |
| Has end date | Flexible | Yes | Yes | No |
| Contains other entities | Yes | Sometimes | Rarely | Rarely |
| Recurring/continuous | No | No | No | Yes |
| Time-critical event | No | Sometimes | Yes | No |

---

## Identifier System

Each entity has two identifier fields:

### UID (Unique Identifier)

**Field**: `uid`  
**Type**: String  
**Format**: `{prefix}-{8-char-hex}`  
**Required**: Yes (system-generated)  
**Mutable**: No (immutable after creation)

The UID is the **primary identifier** for an entity:

- Auto-generated by HoxCore during creation
- Based on entity type prefix + random hex string
- Used for internal references and file naming
- Never changes throughout entity lifecycle

**Examples**:
```
prog-a1b2c3d4
proj-e5f6g7h8
miss-i9j0k1l2
act-m3n4o5p6
```

**UID Prefixes by Type**:

| Entity Type | Prefix | Example UID |
|-------------|--------|-------------|
| Program | `prog-` | `prog-a1b2c3d4` |
| Project | `proj-` | `proj-e5f6g7h8` |
| Mission | `miss-` | `miss-i9j0k1l2` |
| Action | `act-` | `act-m3n4o5p6` |

### ID (Human Identifier)

**Field**: `id`  
**Type**: String  
**Format**: User-defined  
**Required**: No  
**Mutable**: Yes (can be changed)

The ID is an **optional human-friendly identifier**:

- User-defined during or after creation
- Must be unique within entity type
- Can be changed via `edit` command
- Useful for external system references

**Example Patterns**:
```
P-001          # Simple sequential
PROJ-ALPHA     # Descriptive
2024-Q1-001    # Date-based
WEB-REDESIGN   # Name-based
```

### Identifier Resolution

When looking up entities, both UID and ID can be used:

1. **Fast path**: System checks if identifier matches UID pattern
2. **Slow path**: System searches file contents for ID match

```bash
# Both work:
hxc show proj-e5f6g7h8    # By UID
hxc show P-001            # By ID
```

---

## Field Reference

### Required Fields

These fields must be present in every entity:

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Entity type: `program`, `project`, `mission`, `action` |
| `uid` | string | System-generated unique identifier |
| `title` | string | Human-readable title (non-empty) |

### Status and Lifecycle

#### status

**Type**: String (enum)  
**Default**: `active`  
**Valid Values**:

| Status | Description | Use Case |
|--------|-------------|----------|
| `active` | Currently in progress | Default for new entities |
| `completed` | Successfully finished | Set when done |
| `on-hold` | Temporarily paused | Waiting for dependencies |
| `cancelled` | Abandoned or stopped | No longer relevant |
| `planned` | Not yet started | Future work |

```yaml
status: active
```

#### start_date

**Type**: String (date)  
**Format**: `YYYY-MM-DD`  
**Default**: Date of creation

```yaml
start_date: 2024-01-15
```

#### due_date

**Type**: String (date)  
**Format**: `YYYY-MM-DD`  
**Required**: No (but recommended for time-bound entities)

```yaml
due_date: 2024-06-01
```

#### completion_date

**Type**: String (date)  
**Format**: `YYYY-MM-DD`  
**Usage**: Set when status becomes `completed`

```yaml
completion_date: 2024-05-28
```

#### duration_estimate

**Type**: String  
**Format**: `{number}{unit}` where unit is `d` (days), `w` (weeks), `m` (months)

```yaml
duration_estimate: 90d
duration_estimate: 3w
duration_estimate: 6m
```

### Classification Fields

#### description

**Type**: String  
**Purpose**: Detailed explanation for humans and LLMs

```yaml
description: >
  This project builds an AI-integrated CLI for managing modular registries.
  It includes support for MCP protocol and declarative templates.
```

#### category

**Type**: String  
**Format**: Hierarchical path with optional template variant  
**Pattern**: `{domain}.{subdomain}/{type}.{variant}`

Categories provide semantic classification:

```yaml
# Basic category
category: software.dev/cli-tool

# With template variant
category: software.dev/cli-tool.python-v2

# Other examples
category: academic/research-paper
category: aerospace.mission/satellite-deployment
category: business/quarterly-review
```

**Category Components**:
- **Domain**: Top-level area (`software`, `academic`, `business`)
- **Subdomain**: Specialization (`dev`, `research`, `finance`)
- **Type**: Specific kind (`cli-tool`, `research-paper`)
- **Variant**: Template version (after `.`)

#### tags

**Type**: List of strings  
**Purpose**: Searchable keywords for filtering

```yaml
tags:
  - cli
  - python
  - ai
  - registry
  - tools
```

**Tag Guidelines**:
- Use lowercase
- Use hyphens for multi-word tags: `machine-learning`
- Keep tags atomic and specific
- Avoid redundant tags (don't duplicate category info)

#### template

**Type**: String  
**Purpose**: Reference to scaffolding template for initialization

```yaml
template: software.dev/cli-tool.default
```

### Relationship Fields

#### parent

**Type**: String (UID or ID reference)  
**Purpose**: Hierarchical parent relationship

```yaml
parent: prog-a1b2c3d4
# or
parent: PROG-Q1-2024
```

**Relationship Rules**:
- An entity can have at most one parent
- Programs typically have no parent (or another program)
- Projects/missions/actions typically belong to a program or project

#### children

**Type**: List of strings (UID or ID references)  
**Purpose**: Hierarchical child relationships

```yaml
children:
  - proj-11111111
  - proj-22222222
  - miss-33333333
```

**Note**: Children should have corresponding `parent` references for bidirectional linking.

#### related

**Type**: List of strings (UID or ID references)  
**Purpose**: Non-hierarchical relationships between entities

```yaml
related:
  - proj-44444444
  - miss-55555555
```

**Use Cases**:
- Dependencies between projects
- Related documentation
- Cross-references for context

### Integration Fields

All integration fields follow a list-of-objects pattern for extensibility.

#### repositories

**Type**: List of repository objects  
**Purpose**: Version control system integrations

```yaml
repositories:
  - name: github
    url: https://github.com/user/repo
  
  - name: overleaf
    url: https://www.overleaf.com/project/123abc
  
  - name: local-repo
    path: ./repos/example
```

**Repository Object Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Identifier for the repository |
| `url` | string | No* | Remote repository URL |
| `path` | string | No* | Local repository path |

*At least one of `url` or `path` should be provided.

#### storage

**Type**: List of storage objects  
**Purpose**: File storage and document management integrations

```yaml
storage:
  - name: gdrive
    provider: google-drive
    url: https://drive.google.com/drive/folders/example
  
  - name: notion
    provider: notion
    url: https://notion.so/workspace/docs
  
  - name: local-docs
    provider: filesystem
    path: ./documentation
```

**Storage Object Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Identifier for the storage |
| `provider` | string | No | Storage provider type |
| `url` | string | No* | Remote storage URL |
| `path` | string | No* | Local storage path |

**Common Providers**: `google-drive`, `dropbox`, `onedrive`, `notion`, `filesystem`

#### databases

**Type**: List of database objects  
**Purpose**: Database connections for the entity

```yaml
databases:
  - name: local-sqlite
    type: sqlite
    path: ./data/example.db
  
  - name: remote-postgres
    type: postgres
    url: postgres://user:pass@host:5432/dbname
```

**Database Object Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Identifier for the database |
| `type` | string | Yes | Database type |
| `url` | string | No* | Connection URL |
| `path` | string | No* | Local database path |

**Common Types**: `sqlite`, `postgres`, `mysql`, `mongodb`, `redis`

#### tools

**Type**: List of tool objects  
**Purpose**: Project management and collaboration tool integrations

```yaml
tools:
  - name: azure-devops
    provider: azure
    url: https://dev.azure.com/org/project
  
  - name: github-projects
    provider: github
    url: https://github.com/user/repo/projects/1
  
  - name: trello
    provider: trello
    url: https://trello.com/b/boardid/project-board
  
  - name: openproject
    provider: openproject
    url: https://openproject.example.com/projects/my-project
```

**Tool Object Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Identifier for the tool |
| `provider` | string | No | Tool provider type |
| `url` | string | Yes | Tool URL |

**Common Providers**: `azure`, `github`, `gitlab`, `jira`, `trello`, `asana`, `openproject`

#### models

**Type**: List of model objects  
**Purpose**: LLM model references for AI integration

```yaml
models:
  - id: assistant
    provider: openwebui
    url: http://openwebui.local/?models=assistant
  
  - id: code-helper
    provider: openai
    model: gpt-4-turbo
  
  - id: local-llm
    provider: ollama
    model: codellama:34b
```

**Model Object Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Identifier for the model |
| `provider` | string | No | Model provider |
| `model` | string | No | Specific model name |
| `url` | string | No | Model access URL |

**Common Providers**: `openai`, `anthropic`, `ollama`, `openwebui`, `azure-openai`

#### knowledge_bases

**Type**: List of knowledge base objects  
**Purpose**: External knowledge sources for AI context

```yaml
knowledge_bases:
  - id: kb-registry-specs
    url: http://openwebui.local/workspace/knowledge/5f0f9cc7...
  
  - id: project-docs
    provider: notion
    url: https://notion.so/workspace/project-knowledge
  
  - id: local-knowledge
    path: ./knowledge/
```

**Knowledge Base Object Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Identifier for the knowledge base |
| `provider` | string | No | Knowledge base provider |
| `url` | string | No* | Remote knowledge base URL |
| `path` | string | No* | Local knowledge base path |

---

## Field Categories

For programmatic access, fields are categorized as follows:

### Scalar Fields

Single-value fields that can be directly get/set:

```python
SCALAR_FIELDS = [
    "type",
    "uid",
    "id",
    "title",
    "description",
    "status",
    "start_date",
    "due_date",
    "completion_date",
    "duration_estimate",
    "category",
    "parent",
    "template",
]
```

### List Fields

Simple list fields (add/remove operations):

```python
LIST_FIELDS = [
    "tags",
    "children",
    "related",
]
```

### Complex Fields

List-of-objects fields (structured sub-items):

```python
COMPLEX_FIELDS = [
    "repositories",
    "storage",
    "databases",
    "tools",
    "models",
    "knowledge_bases",
]
```

### Special Fields

Virtual fields for programmatic access:

| Field | Description |
|-------|-------------|
| `all` | Returns complete entity data |
| `path` | Returns file system path to entity |

---

## Validation Rules

HoxCore enforces the following validation rules:

### Required Field Validation

| Field | Rule |
|-------|------|
| `type` | Must be present and valid enum value |
| `uid` | Must be present and match pattern `{prefix}-{8-hex}` |
| `title` | Must be present and non-empty |

### Type Validation

```python
# Valid types
["program", "project", "mission", "action"]

# Type must match directory location
# proj-* files must be in projects/ folder
```

### Status Validation

```python
# Valid statuses
["active", "completed", "on-hold", "cancelled", "planned"]
```

### Date Validation

```python
# Format: YYYY-MM-DD
# Examples:
"2024-01-15"  # Valid
"01-15-2024"  # Invalid
"2024/01/15"  # Invalid
```

### Uniqueness Validation

| Scope | Field | Rule |
|-------|-------|------|
| Global | `uid` | Must be unique across ALL entities |
| Per-Type | `id` | Must be unique within entity type |

### Relationship Validation

| Relationship | Validation | Severity |
|--------------|------------|----------|
| `parent` | Must exist if specified | Error |
| `children` | Each must exist | Error |
| `related` | Each should exist | Warning |

### List Field Validation

```yaml
# Valid
tags:
  - python
  - cli

# Invalid (not a list)
tags: python, cli

# Valid (empty list)
children: []

# Invalid (wrong type)
children: "proj-12345678"
```

---

## File Naming and Storage

### File Naming Convention

Entity files are named using the UID:

```
{uid}.yml
```

**Examples**:
```
programs/prog-a1b2c3d4.yml
projects/proj-e5f6g7h8.yml
missions/miss-i9j0k1l2.yml
actions/act-m3n4o5p6.yml
```

### Directory Structure

```
registry/
├── .hxc/                       # Registry marker
│   └── index.db                # Query index
├── config.yml                  # Registry configuration
├── programs/                   # Program entities
│   ├── prog-a1b2c3d4.yml
│   └── prog-b2c3d4e5.yml
├── projects/                   # Project entities
│   ├── proj-e5f6g7h8.yml
│   └── proj-f6g7h8i9.yml
├── missions/                   # Mission entities
│   └── miss-i9j0k1l2.yml
├── actions/                    # Action entities
│   └── act-m3n4o5p6.yml
└── .gitignore
```

### YAML Formatting

Entity files use standard YAML with these conventions:

- **Indentation**: 2 spaces
- **Lists**: Hyphenated format
- **Strings**: Quoted when containing special characters
- **Null values**: Represented as `null` or omitted
- **Dates**: ISO 8601 format (`YYYY-MM-DD`)

---

## Complete Examples

### Full Project Entity

```yaml
# Identity
type: project
uid: proj-e5f6g7h8
id: P-001
title: "Website Redesign"
description: >
  Complete redesign of the company website with modern UI/UX.
  Includes responsive design, accessibility improvements, and
  performance optimization.

# Status & Lifecycle
status: active
start_date: 2024-01-15
due_date: 2024-06-01
completion_date: null
duration_estimate: 4m

# Classification
category: software.dev/frontend
tags:
  - web
  - frontend
  - design
  - priority
  - q1-2024

# Relationships
parent: prog-a1b2c3d4
children: []
related:
  - proj-f6g7h8i9
  - miss-i9j0k1l2

# Integrations
repositories:
  - name: github
    url: https://github.com/company/website-redesign
  - name: design-files
    url: https://github.com/company/website-design

storage:
  - name: gdrive
    provider: google-drive
    url: https://drive.google.com/drive/folders/website-assets
  - name: figma
    provider: figma
    url: https://figma.com/file/abc123/website-design

databases:
  - name: analytics
    type: postgres
    url: postgres://analytics.company.com:5432/website_metrics

tools:
  - name: github-projects
    provider: github
    url: https://github.com/orgs/company/projects/5
  - name: slack
    provider: slack
    url: https://company.slack.com/channels/website-redesign

models:
  - id: content-assistant
    provider: openai
    model: gpt-4-turbo

knowledge_bases:
  - id: brand-guidelines
    url: https://notion.so/company/brand-guidelines
```

### Full Program Entity

```yaml
type: program
uid: prog-a1b2c3d4
id: PROG-Q1-2024
title: "Q1 2024 Strategic Initiatives"
description: >
  Umbrella program for all strategic initiatives in Q1 2024.
  Focus areas: digital transformation, customer experience, and
  operational efficiency.

status: active
start_date: 2024-01-01
due_date: 2024-03-31

category: business/strategic
tags:
  - q1-2024
  - strategic
  - executive-priority

children:
  - proj-e5f6g7h8
  - proj-f6g7h8i9
  - miss-i9j0k1l2
  - act-m3n4o5p6

storage:
  - name: program-docs
    provider: notion
    url: https://notion.so/company/q1-2024-program

tools:
  - name: azure-devops
    provider: azure
    url: https://dev.azure.com/company/q1-initiatives

knowledge_bases:
  - id: strategy-docs
    url: https://notion.so/company/strategy-2024
```

### Minimal Valid Entity

```yaml
type: project
uid: proj-00000001
title: "Minimal Project"
```

---

## Schema Reference

### Entity Type Schema

```yaml
type:
  type: string
  required: true
  enum:
    - program
    - project
    - mission
    - action
```

### Status Schema

```yaml
status:
  type: string
  required: false
  default: active
  enum:
    - active
    - completed
    - on-hold
    - cancelled
    - planned
```

### Date Schema

```yaml
# All date fields follow this pattern
date_field:
  type: string
  required: false
  pattern: "^\\d{4}-\\d{2}-\\d{2}$"
  format: date
  example: "2024-01-15"
```

### Repository Schema

```yaml
repositories:
  type: array
  items:
    type: object
    properties:
      name:
        type: string
        required: true
      url:
        type: string
        required: false
      path:
        type: string
        required: false
```

### Integration Object Schema (Generic)

```yaml
# Pattern for all integration fields
integration_item:
  type: object
  required:
    - name  # or 'id' for models/knowledge_bases
  properties:
    name:
      type: string
      description: Identifier for the integration
    provider:
      type: string
      description: Service provider type
    url:
      type: string
      description: Remote resource URL
    path:
      type: string
      description: Local file path
```

---

## For AI Agents

### Quick Reference

When working with HoxCore entities:

1. **Always validate `type`** against `EntityType` enum
2. **Always validate `status`** against `EntityStatus` enum
3. **UIDs are immutable** - never attempt to change them
4. **IDs must be unique** within their entity type
5. **Use path security** for all file operations
6. **Dates must be YYYY-MM-DD** format

### Entity Creation Checklist

```yaml
# Minimum required fields
type: project           # Required
uid: auto               # System-generated
title: "Title"          # Required, non-empty

# Recommended fields
status: active          # Defaults to active
start_date: YYYY-MM-DD  # Defaults to today
description: "..."      # For context
tags: []                # For searchability
```

### Common Operations

```python
from hxc.core.enums import EntityType, EntityStatus

# Type validation
entity_type = EntityType.from_string("project")  # Raises ValueError if invalid

# Status validation
status = EntityStatus.from_string("active")  # Raises ValueError if invalid

# Get folder for type
folder = entity_type.get_folder_name()  # "projects"

# Get file prefix
prefix = entity_type.get_file_prefix()  # "proj"
```

### Field Access Patterns

```bash
# Scalar fields
hxc get P-001 title
hxc get P-001 status

# List fields
hxc get P-001 tags
hxc get P-001 tags --index 0

# Complex fields
hxc get P-001 repositories
hxc get P-001 repositories --key name:github

# All fields
hxc get P-001 all
```

---

## See Also

- [API.md](API.md) - Python API reference
- [COMMANDS.md](COMMANDS.md) - CLI command reference
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md) - MCP server documentation
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
- [../standards/model_definition_example.yml](../standards/model_definition_example.yml) - Complete example
```