```markdown
# HoxCore CLI Command Reference

This document provides a comprehensive reference for all HoxCore CLI commands. It is designed for developers and AI coding agents who need to interact with HoxCore registries via the command line.

## Table of Contents

- [Overview](#overview)
- [Global Options](#global-options)
- [Commands](#commands)
  - [init](#init)
  - [create](#create)
  - [list](#list)
  - [show](#show)
  - [get](#get)
  - [edit](#edit)
  - [delete](#delete)
  - [validate](#validate)
  - [registry](#registry)
- [Output Formats](#output-formats)
- [Exit Codes](#exit-codes)
- [Environment Variables](#environment-variables)
- [Common Patterns](#common-patterns)

---

## Overview

HoxCore CLI (`hxc`) is the primary interface for managing HoxCore registries. All commands follow a consistent pattern:

```bash
hxc <command> [arguments] [options]
```

### Getting Help

```bash
# General help
hxc --help

# Command-specific help
hxc <command> --help

# Version information
hxc --version
```

### Command Categories

| Category | Commands | Description |
|----------|----------|-------------|
| **Registry** | `init`, `registry`, `validate` | Registry management and validation |
| **Entity CRUD** | `create`, `show`, `get`, `edit`, `delete` | Entity operations |
| **Query** | `list` | Filtering and searching entities |

---

## Global Options

These options are available for all commands:

| Option | Description |
|--------|-------------|
| `--help`, `-h` | Show help message and exit |
| `--version` | Show version information |

---

## Commands

### init

Initialize a new HoxCore registry with the required directory structure.

#### Syntax

```bash
hxc init [PATH] [OPTIONS]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `PATH` | No | Directory path for the registry (default: current directory) |

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--no-git` | flag | `False` | Skip git repository initialization |
| `--no-commit` | flag | `False` | Skip initial commit (requires git) |
| `--remote URL` | string | None | Git remote URL to configure as 'origin' |
| `--no-set-default` | flag | `False` | Don't set as default registry in config |

#### Created Structure

```
<PATH>/
├── .hxc/                   # Registry marker directory
│   └── index.db            # Query index (gitignored)
├── config.yml              # Registry configuration
├── programs/               # Program entity files
├── projects/               # Project entity files
├── missions/               # Mission entity files
├── actions/                # Action entity files
└── .gitignore              # Git ignore rules
```

#### Examples

```bash
# Initialize in current directory
hxc init

# Initialize at specific path
hxc init /path/to/my-registry

# Initialize without git
hxc init --no-git

# Initialize with remote repository
hxc init --remote https://github.com/user/registry.git

# Initialize without setting as default
hxc init /path/to/secondary-registry --no-set-default
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Directory not empty or already initialized |
| `1` | Git operation failed |
| `1` | Permission denied |

#### Notes

- The directory must be empty or non-existent
- Git initialization is enabled by default
- The registry is automatically set as default unless `--no-set-default` is specified

---

### create

Create a new entity (program, project, mission, or action) in the registry.

#### Syntax

```bash
hxc create <TYPE> <TITLE> [OPTIONS]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `TYPE` | Yes | Entity type: `program`, `project`, `mission`, `action` |
| `TITLE` | Yes | Human-readable title for the entity |

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--id ID` | string | None | Custom human-readable ID (must be unique within type) |
| `--description TEXT` | string | None | Entity description |
| `--status STATUS` | string | `active` | Initial status: `active`, `completed`, `on-hold`, `cancelled`, `planned` |
| `--category CAT` | string | None | Category path (e.g., `software.dev/cli-tool`) |
| `--tags TAG1,TAG2` | string | None | Comma-separated list of tags |
| `--parent ID` | string | None | Parent entity UID or ID |
| `--start-date DATE` | string | today | Start date in YYYY-MM-DD format |
| `--due-date DATE` | string | None | Due date in YYYY-MM-DD format |
| `--no-git` | flag | `False` | Skip git commit |
| `--format FMT` | string | `pretty` | Output format: `pretty`, `yaml`, `json`, `id` |

#### Entity Types

| Type | Prefix | Description |
|------|--------|-------------|
| `program` | `prog-` | Abstract container for related initiatives |
| `project` | `proj-` | Concrete effort with deliverables |
| `mission` | `miss-` | Event-like effort with culmination |
| `action` | `act-` | Ongoing or recurring activity |

#### Examples

```bash
# Create a basic project
hxc create project "My New Project"

# Create with custom ID and tags
hxc create project "Website Redesign" --id P-001 --tags web,frontend,design

# Create a mission with due date
hxc create mission "Product Launch" --due-date 2024-06-01 --status planned

# Create action with description
hxc create action "Weekly Standup" --description "Team sync every Monday at 9am"

# Create project under a program
hxc create project "API Development" --parent PROG-Q1-2024

# Create with full options
hxc create project "Complete Project" \
  --id P-100 \
  --description "A fully configured project" \
  --status active \
  --category software.dev/backend \
  --tags api,python,microservices \
  --parent PROG-001 \
  --start-date 2024-01-15 \
  --due-date 2024-06-30

# Output only the UID (useful for scripting)
hxc create project "Script Project" --format id
```

#### Output Formats

**Pretty (default):**
```
Created project 'My New Project'
  UID: proj-12345678
  ID:  P-001
  File: /path/to/registry/projects/proj-12345678.yml
```

**YAML:**
```yaml
type: project
uid: proj-12345678
id: P-001
title: My New Project
status: active
...
```

**JSON:**
```json
{
  "type": "project",
  "uid": "proj-12345678",
  "id": "P-001",
  "title": "My New Project",
  "status": "active"
}
```

**ID:**
```
proj-12345678
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Invalid entity type |
| `1` | Duplicate ID error |
| `1` | Invalid date format |
| `1` | Parent entity not found |
| `1` | No registry found |

---

### list

List entities from the registry with optional filtering and sorting.

#### Syntax

```bash
hxc list [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--type TYPE` | string | `all` | Entity type: `program`, `project`, `mission`, `action`, `all` |
| `--status STATUS` | string | `any` | Filter by status: `active`, `completed`, `on-hold`, `cancelled`, `planned`, `any` |
| `--tags TAG1,TAG2` | string | None | Filter by tags (AND logic - must have ALL tags) |
| `--category CAT` | string | None | Filter by category (exact match) |
| `--parent ID` | string | None | Filter by parent ID or UID |
| `--id ID` | string | None | Filter by specific ID or UID |
| `--query TEXT` | string | None | Text search in title and description |
| `--due-before DATE` | string | None | Filter by due date before YYYY-MM-DD (inclusive) |
| `--due-after DATE` | string | None | Filter by due date after YYYY-MM-DD (inclusive) |
| `--sort FIELD` | string | `title` | Sort by: `title`, `id`, `due_date`, `status`, `created`, `modified` |
| `--desc` | flag | `False` | Sort in descending order |
| `--max N` | int | `0` | Maximum items to return (0 = all) |
| `--format FMT` | string | `table` | Output format: `table`, `yaml`, `json`, `id` |

#### Filter Logic

- **Tags**: AND logic - entity must have ALL specified tags
- **Status**: Exact match (use `any` for no filtering)
- **Category**: Exact match
- **Query**: Case-insensitive substring match in title and description
- **Date filters**: Inclusive bounds

#### Examples

```bash
# List all entities
hxc list

# List only projects
hxc list --type project

# List active projects
hxc list --type project --status active

# Filter by multiple tags (must have ALL)
hxc list --tags python,cli,tools

# Search by text
hxc list --query "website"

# Filter by due date range
hxc list --due-after 2024-01-01 --due-before 2024-06-30

# Sort by due date descending
hxc list --sort due_date --desc

# Limit results
hxc list --max 10

# Get only IDs (for scripting)
hxc list --type project --status active --format id

# Complex filter
hxc list \
  --type project \
  --status active \
  --tags priority \
  --due-before 2024-06-01 \
  --sort due_date \
  --format yaml
```

#### Output Formats

**Table (default):**
```
TYPE     UID              ID      TITLE              STATUS    DUE DATE
project  proj-12345678    P-001   Website Redesign   active    2024-06-01
project  proj-87654321    P-002   API Development    active    2024-04-15
mission  miss-11111111    M-001   Product Launch     planned   2024-07-01
```

**YAML:**
```yaml
- type: project
  uid: proj-12345678
  id: P-001
  title: Website Redesign
  status: active
  due_date: 2024-06-01
- type: project
  uid: proj-87654321
  id: P-002
  title: API Development
  status: active
  due_date: 2024-04-15
```

**JSON:**
```json
[
  {
    "type": "project",
    "uid": "proj-12345678",
    "id": "P-001",
    "title": "Website Redesign",
    "status": "active",
    "due_date": "2024-06-01"
  }
]
```

**ID:**
```
proj-12345678
proj-87654321
miss-11111111
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success (even if no results) |
| `1` | Invalid filter parameters |
| `1` | No registry found |

---

### show

Display detailed information about a specific entity.

#### Syntax

```bash
hxc show <IDENTIFIER> [OPTIONS]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `IDENTIFIER` | Yes | Entity ID or UID to display |

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--type TYPE` | string | None | Entity type filter for disambiguation |
| `--format FMT` | string | `pretty` | Output format: `pretty`, `yaml`, `json` |
| `--raw` | flag | `False` | Include raw YAML file content |

#### Lookup Strategy

The command uses a two-phase search:
1. **Fast path**: Match identifier against filename pattern (`{prefix}-{uid}.yml`)
2. **Slow path**: Search file contents for ID match

#### Examples

```bash
# Show by UID
hxc show proj-12345678

# Show by custom ID
hxc show P-001

# Show with type filter (for disambiguation)
hxc show P-001 --type project

# Output as YAML
hxc show P-001 --format yaml

# Output as JSON
hxc show P-001 --format json

# Include raw file content
hxc show P-001 --raw
```

#### Output Formats

**Pretty (default):**
```
═══════════════════════════════════════════════════════════════════
PROJECT: Website Redesign
═══════════════════════════════════════════════════════════════════

  UID:         proj-12345678
  ID:          P-001
  Status:      active
  Category:    software.dev/frontend

  Description:
    Redesign the company website with modern UI/UX

  Dates:
    Start:     2024-01-15
    Due:       2024-06-01

  Tags:        web, frontend, design, priority

  Relationships:
    Parent:    prog-00000001 (Q1 Initiatives)
    Children:  (none)
    Related:   proj-87654321

  Repositories:
    • github: https://github.com/company/website

  File: /path/to/registry/projects/proj-12345678.yml
═══════════════════════════════════════════════════════════════════
```

**YAML:**
```yaml
type: project
uid: proj-12345678
id: P-001
title: Website Redesign
description: Redesign the company website with modern UI/UX
status: active
category: software.dev/frontend
tags:
  - web
  - frontend
  - design
  - priority
start_date: 2024-01-15
due_date: 2024-06-01
parent: prog-00000001
repositories:
  - name: github
    url: https://github.com/company/website
```

**JSON:**
```json
{
  "type": "project",
  "uid": "proj-12345678",
  "id": "P-001",
  "title": "Website Redesign",
  "description": "Redesign the company website with modern UI/UX",
  "status": "active",
  "category": "software.dev/frontend",
  "tags": ["web", "frontend", "design", "priority"],
  "start_date": "2024-01-15",
  "due_date": "2024-06-01",
  "parent": "prog-00000001",
  "repositories": [
    {"name": "github", "url": "https://github.com/company/website"}
  ]
}
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Entity not found |
| `1` | Ambiguous identifier (multiple matches) |
| `1` | Invalid entity file |

---

### get

Retrieve a specific property value from an entity.

#### Syntax

```bash
hxc get <IDENTIFIER> <PROPERTY> [OPTIONS]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `IDENTIFIER` | Yes | Entity ID or UID |
| `PROPERTY` | Yes | Property name to retrieve |

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--type TYPE` | string | None | Entity type filter for disambiguation |
| `--index N` | int | None | For list/complex properties, get item at index (0-based) |
| `--key FILTER` | string | None | For complex properties, filter by `key:value` pattern |
| `--format FMT` | string | `value` | Output format: `value`, `yaml`, `json` |

#### Available Properties

**Scalar Properties:**
| Property | Description |
|----------|-------------|
| `type` | Entity type |
| `uid` | Unique identifier |
| `id` | Human-readable ID |
| `title` | Entity title |
| `description` | Entity description |
| `status` | Current status |
| `start_date` | Start date |
| `due_date` | Due date |
| `completion_date` | Completion date |
| `duration_estimate` | Estimated duration |
| `category` | Category path |
| `parent` | Parent entity reference |
| `template` | Template reference |

**List Properties:**
| Property | Description |
|----------|-------------|
| `tags` | List of tags |
| `children` | List of child entity references |
| `related` | List of related entity references |

**Complex Properties:**
| Property | Description |
|----------|-------------|
| `repositories` | Version control integrations |
| `storage` | Storage integrations |
| `databases` | Database connections |
| `tools` | Project management tools |
| `models` | LLM model references |
| `knowledge_bases` | Knowledge base references |

**Special Properties:**
| Property | Description |
|----------|-------------|
| `all` | Returns all properties |
| `path` | Returns file path |

#### Examples

```bash
# Get scalar property
hxc get P-001 status
hxc get P-001 title
hxc get P-001 due_date

# Get list property
hxc get P-001 tags
hxc get P-001 children

# Get specific tag by index
hxc get P-001 tags --index 0

# Get complex property
hxc get P-001 repositories

# Filter complex property
hxc get P-001 repositories --key name:github

# Get all properties
hxc get P-001 all

# Get file path
hxc get P-001 path

# Output as JSON
hxc get P-001 tags --format json

# Output as YAML
hxc get P-001 repositories --format yaml
```

#### Output Formats

**Value (default):**
```
active
```

For lists:
```
web
frontend
design
priority
```

**YAML:**
```yaml
- web
- frontend
- design
- priority
```

**JSON:**
```json
["web", "frontend", "design", "priority"]
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Entity not found |
| `1` | Property not found |
| `1` | Invalid index |
| `1` | Invalid key filter |

---

### edit

Modify properties of an existing entity.

#### Syntax

```bash
hxc edit <IDENTIFIER> [OPTIONS]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `IDENTIFIER` | Yes | Entity ID or UID to edit |

#### Options

**Scalar Field Updates:**
| Option | Type | Description |
|--------|------|-------------|
| `--set-title TEXT` | string | New title |
| `--set-description TEXT` | string | New description |
| `--set-status STATUS` | string | New status |
| `--set-id ID` | string | New custom ID (must be unique) |
| `--set-category CAT` | string | New category |
| `--set-parent ID` | string | New parent reference |
| `--set-start-date DATE` | string | New start date (YYYY-MM-DD) |
| `--set-due-date DATE` | string | New due date (YYYY-MM-DD) |
| `--set-completion-date DATE` | string | New completion date (YYYY-MM-DD) |

**List Field Operations:**
| Option | Type | Description |
|--------|------|-------------|
| `--add-tags TAG1,TAG2` | string | Tags to add (idempotent) |
| `--remove-tags TAG1,TAG2` | string | Tags to remove (silent if missing) |
| `--add-children ID1,ID2` | string | Child references to add |
| `--remove-children ID1,ID2` | string | Child references to remove |
| `--add-related ID1,ID2` | string | Related references to add |
| `--remove-related ID1,ID2` | string | Related references to remove |

**General Options:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--type TYPE` | string | None | Entity type filter for disambiguation |
| `--no-git` | flag | `False` | Skip git commit |
| `--format FMT` | string | `pretty` | Output format: `pretty`, `yaml`, `json` |

#### Examples

```bash
# Update title
hxc edit P-001 --set-title "Updated Project Name"

# Change status
hxc edit P-001 --set-status completed

# Add and remove tags
hxc edit P-001 --add-tags urgent,priority --remove-tags draft

# Update multiple fields
hxc edit P-001 \
  --set-title "Final Project Name" \
  --set-status completed \
  --set-completion-date 2024-03-15

# Change parent
hxc edit P-001 --set-parent PROG-002

# Add children
hxc edit PROG-001 --add-children P-001,P-002,P-003

# Add related projects
hxc edit P-001 --add-related P-002,M-001

# Change custom ID
hxc edit P-001 --set-id PROJECT-ALPHA

# Edit without git commit
hxc edit P-001 --set-status on-hold --no-git
```

#### Output Formats

**Pretty (default):**
```
Updated project 'Updated Project Name' (proj-12345678)
  Changes:
    • title: "Old Title" → "Updated Project Name"
    • status: active → completed
    • Added tags: urgent, priority
    • Removed tags: draft
```

**YAML:**
```yaml
identifier: P-001
changes:
  - field: title
    old: Old Title
    new: Updated Project Name
  - field: status
    old: active
    new: completed
entity:
  type: project
  uid: proj-12345678
  ...
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Entity not found |
| `1` | Duplicate ID error |
| `1` | Invalid status value |
| `1` | Invalid date format |
| `1` | No changes specified |

---

### delete

Remove an entity from the registry.

#### Syntax

```bash
hxc delete <IDENTIFIER> [OPTIONS]
```

#### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `IDENTIFIER` | Yes | Entity ID or UID to delete |

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force`, `-f` | flag | `False` | Skip confirmation prompt |
| `--type TYPE` | string | None | Entity type filter for disambiguation |
| `--no-git` | flag | `False` | Skip git commit |

#### Examples

```bash
# Delete with confirmation prompt
hxc delete P-001

# Force delete without confirmation
hxc delete P-001 --force

# Delete with type filter
hxc delete P-001 --type project --force

# Delete without git commit
hxc delete P-001 --force --no-git
```

#### Confirmation Prompt

Without `--force`:
```
About to delete project 'Website Redesign' (proj-12345678)
File: /path/to/registry/projects/proj-12345678.yml

Are you sure? [y/N]: 
```

#### Output

```
Deleted project 'Website Redesign' (proj-12345678)
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `0` | Cancelled by user |
| `1` | Entity not found |
| `1` | Ambiguous identifier |

#### Notes

- Deletion is permanent (though recoverable via git if enabled)
- By default, uses `git rm` for proper version control
- Does not cascade delete children or update parent references

---

### validate

Validate the integrity and consistency of a HoxCore registry.

#### Syntax

```bash
hxc validate [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--format FMT` | string | `pretty` | Output format: `pretty`, `yaml`, `json` |
| `--quiet`, `-q` | flag | `False` | Only output errors (suppress warnings) |

#### Validation Checks

| Check | Severity | Description |
|-------|----------|-------------|
| Required fields | Error | `type`, `uid`, `title` must be present |
| UID uniqueness | Error | UIDs must be unique across all entities |
| ID uniqueness | Error | IDs must be unique within entity type |
| Parent links | Error | Parent references must exist |
| Child links | Error | Child references must exist |
| Related links | Warning | Related references should exist |
| Status values | Error | Status must be valid enum value |
| Type validation | Error | Type must match directory location |
| Empty files | Error | Entity files cannot be empty |
| YAML validity | Error | Files must be valid YAML |

#### Examples

```bash
# Validate registry
hxc validate

# Validate with JSON output
hxc validate --format json

# Quiet mode (errors only)
hxc validate --quiet
```

#### Output Formats

**Pretty (default):**
```
Validating registry: /path/to/registry

Checking entities...
  programs: 3
  projects: 12
  missions: 2
  actions: 5

✓ No errors found
⚠ 2 warnings

Warnings:
  • projects/proj-12345678.yml: Related entity 'proj-99999999' not found
  • missions/miss-11111111.yml: Related entity 'proj-88888888' not found

Summary:
  Entities checked: 22
  Errors: 0
  Warnings: 2
```

With errors:
```
Validating registry: /path/to/registry

✗ 3 errors found

Errors:
  • projects/proj-12345678.yml: Missing required field 'title'
  • projects/proj-87654321.yml: Duplicate ID 'P-001' (also in proj-11111111.yml)
  • missions/miss-11111111.yml: Parent entity 'prog-99999999' not found

Summary:
  Entities checked: 22
  Errors: 3
  Warnings: 0
```

**JSON:**
```json
{
  "valid": false,
  "errors": [
    "projects/proj-12345678.yml: Missing required field 'title'",
    "projects/proj-87654321.yml: Duplicate ID 'P-001'"
  ],
  "warnings": [
    "missions/miss-11111111.yml: Related entity 'proj-99999999' not found"
  ],
  "error_count": 2,
  "warning_count": 1,
  "entities_checked": 22,
  "entities_by_type": {
    "program": 3,
    "project": 12,
    "mission": 2,
    "action": 5
  }
}
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Valid (no errors, warnings allowed) |
| `1` | Invalid (one or more errors) |
| `1` | No registry found |

---

### registry

Manage registry configuration and discovery.

#### Syntax

```bash
hxc registry <SUBCOMMAND> [OPTIONS]
```

#### Subcommands

| Subcommand | Description |
|------------|-------------|
| `path` | Show or set the current registry path |
| `list` | List known registries |
| `discover` | Attempt to discover a registry |
| `clear` | Clear the configured registry path |

#### registry path

Show or set the current registry path.

```bash
# Show current path
hxc registry path

# Set new path
hxc registry path /path/to/registry

# Set path without validation
hxc registry path /path/to/registry --no-validate
```

**Options:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--no-validate` | flag | `False` | Skip path validation |

**Output:**
```
Current registry: /path/to/registry
  Status: Valid
  Source: config

Entity counts:
  programs: 3
  projects: 12
  missions: 2
  actions: 5
```

#### registry list

List all known registries.

```bash
hxc registry list
```

**Output:**
```
Known registries:

  * /path/to/registry (current, config)
    Status: Valid
    Entities: 22

  /path/to/other-registry (discovered)
    Status: Valid
    Entities: 8
```

#### registry discover

Attempt to discover a registry in the current directory tree.

```bash
hxc registry discover
```

**Output:**
```
Discovered registry: /path/to/registry
  Status: Valid
  
Set as default? [y/N]: 
```

#### registry clear

Clear the configured registry path.

```bash
hxc registry clear
```

**Output:**
```
Cleared registry path: /path/to/registry
```

#### Exit Codes

| Code | Description |
|------|-------------|
| `0` | Success |
| `1` | Invalid registry path |
| `1` | No registry discovered |

---

## Output Formats

Most commands support multiple output formats via `--format`:

| Format | Description | Use Case |
|--------|-------------|----------|
| `table` | Tabular format | Human reading |
| `pretty` | Formatted display | Human reading |
| `yaml` | YAML format | Interoperability |
| `json` | JSON format | Scripting, APIs |
| `id` | Only identifiers | Scripting, piping |
| `value` | Raw value only | Property extraction |

### Format Selection Guidelines

```bash
# For human consumption
hxc list --format table
hxc show P-001 --format pretty

# For scripting
PROJECT_ID=$(hxc create project "New" --format id)
hxc list --format id | xargs -I {} hxc show {}

# For data interchange
hxc list --format json | jq '.[] | select(.status == "active")'
hxc show P-001 --format yaml > entity-backup.yml

# For property extraction
STATUS=$(hxc get P-001 status --format value)
```

---

## Exit Codes

HoxCore CLI uses standard exit codes:

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Operation completed successfully |
| `1` | Error | Operation failed |
| `130` | Interrupted | User interrupted (Ctrl+C) |

### Error Handling in Scripts

```bash
#!/bin/bash
set -e

# Will exit if any command fails
hxc create project "Test Project"

# Or handle errors explicitly
if ! hxc show P-001 > /dev/null 2>&1; then
    echo "Entity P-001 not found"
    exit 1
fi
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HXC_REGISTRY_PATH` | Override default registry path | Config value |
| `HXC_DEBUG` | Enable debug logging | `false` |
| `NO_COLOR` | Disable colored output | Not set |

### Usage

```bash
# Temporary registry override
HXC_REGISTRY_PATH=/path/to/registry hxc list

# Debug mode
HXC_DEBUG=1 hxc create project "Test"

# Disable colors (for logging)
NO_COLOR=1 hxc list
```

---

## Common Patterns

### Scripting Patterns

```bash
# Create project and capture UID
PROJECT_UID=$(hxc create project "My Project" --format id)
echo "Created: $PROJECT_UID"

# Process all active projects
hxc list --type project --status active --format id | while read uid; do
    echo "Processing: $uid"
    hxc show "$uid" --format json | jq '.title'
done

# Bulk tag update
for uid in $(hxc list --tags legacy --format id); do
    hxc edit "$uid" --add-tags migration-target
done

# Export all entities
hxc list --format json > registry-backup.json

# Find overdue items
TODAY=$(date +%Y-%m-%d)
hxc list --status active --due-before "$TODAY" --format table
```

### Pipeline Integration

```bash
# Find projects without tags
hxc list --type project --format json | \
    jq '.[] | select(.tags == null or .tags == []) | .uid'

# Count entities by status
hxc list --format json | \
    jq 'group_by(.status) | map({status: .[0].status, count: length})'

# Generate markdown list
hxc list --type project --status active --format json | \
    jq -r '.[] | "- [ ] \(.title) (\(.id // .uid))"'
```

### Git Integration

```bash
# Create entity on feature branch
git checkout -b feature/new-project
hxc create project "Feature Project"
git push -u origin feature/new-project

# Review changes before commit
hxc edit P-001 --set-status completed --no-git
git diff
git add -A && git commit -m "Complete P-001"
```

---

## See Also

- [API.md](API.md) - Python API reference
- [ENTITY_MODEL.md](ENTITY_MODEL.md) - Entity specification
- [MCP_INTEGRATION.md](MCP_INTEGRATION.md) - MCP server documentation
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System architecture
```