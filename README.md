# HoxCore

[![PyPI version](https://badge.fury.io/py/hoxcore.svg)](https://badge.fury.io/py/hoxcore)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A universal, declarative, version-controlled project registry system.**

HoxCore is a foundational, Git-inspired project registry and initialization system designed to manage *any kind of human endeavor*, not only software projects. It provides a **single, authoritative source of truth** for projects and related activities, expressed through immutable, version-controlled metadata and declarative automation.

## Overview

HoxCore manages four fundamental entity types:

| Entity Type | Description | Example |
|-------------|-------------|---------|
| **Program** | Abstract container grouping related initiatives | "Q1 2024 Initiatives" |
| **Project** | Object-like effort with concrete outputs | "Website Redesign" |
| **Mission** | Event-like effort with a clear culmination | "Product Launch Event" |
| **Action** | Ongoing or recurring activity without defined end | "Weekly Code Reviews" |

All entities share a **unified YAML definition**, differing only by metadata fields such as `type`, `category`, and relationships.

## Installation

### From PyPI

```bash
pip install hoxcore
```

### From Source

```bash
git clone https://github.com/SDEscobedo/hoxcore.git
cd hoxcore
pip install -e .
```

### With MCP Support

```bash
pip install hoxcore[mcp]
```

### Development Installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize a Registry

```bash
# Create a new registry in the current directory
hxc init

# Create a registry at a specific path
hxc init /path/to/registry

# Initialize without git
hxc init --no-git
```

### 2. Create Entities

```bash
# Create a project
hxc create project "My New Project" --category software.dev/cli-tool

# Create a mission with a due date
hxc create mission "Product Launch" --due-date 2024-06-01

# Create an action with tags
hxc create action "Weekly Standup" --tags recurring,team,meeting

# Create a program to group related projects
hxc create program "Q1 Initiatives" --description "All Q1 2024 projects"
```

### 3. List and Query Entities

```bash
# List all entities
hxc list

# List only projects
hxc list --type project

# Filter by status
hxc list --status active

# Filter by tags
hxc list --tags cli,tools

# Search by text
hxc list --query "website"

# Filter by due date
hxc list --due-before 2024-06-01
```

### 4. View Entity Details

```bash
# Show entity by ID or UID
hxc show P-001
hxc show proj-12345678

# Get specific property
hxc get P-001 status
hxc get P-001 tags
hxc get P-001 repositories
```

### 5. Edit Entities

```bash
# Update title
hxc edit P-001 --set-title "Updated Project Name"

# Change status
hxc edit P-001 --set-status completed

# Add tags
hxc edit P-001 --add-tags important,urgent

# Set parent relationship
hxc edit P-001 --set-parent PROG-001
```

### 6. Delete Entities

```bash
# Delete with confirmation prompt
hxc delete P-001

# Force delete without confirmation
hxc delete P-001 --force
```

## Entity Model

Entities are stored as YAML files with the following structure:

```yaml
type: project
uid: proj-12345678          # Auto-generated, immutable
id: P-001                   # Optional, human-defined, editable
title: "Example Project"
description: "Project description"
status: active              # active, completed, on-hold, cancelled, planned
start_date: 2024-01-01
due_date: 2024-04-01
category: software.dev/cli-tool
tags: [cli, python, tools]
parent: prog-00000001       # Parent entity UID
children: []                # Child entity UIDs
related: []                 # Related entity UIDs

# Integrations
repositories:
  - name: github
    url: https://github.com/user/repo

storage:
  - name: gdrive
    provider: google-drive
    url: https://drive.google.com/...

tools:
  - name: github-projects
    provider: github
    url: https://github.com/user/repo/projects/1
```

See [docs/ENTITY_MODEL.md](docs/ENTITY_MODEL.md) for the complete specification.

## Registry Structure

```
my-registry/
├── .hxc/                   # Registry marker directory
│   └── index.db            # Query index (gitignored)
├── config.yml              # Registry configuration
├── programs/               # Program entities
│   └── prog-*.yml
├── projects/               # Project entities
│   └── proj-*.yml
├── missions/               # Mission entities
│   └── miss-*.yml
├── actions/                # Action entities
│   └── act-*.yml
└── .gitignore
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `hxc init` | Initialize a new registry |
| `hxc create` | Create a new entity |
| `hxc list` | List entities with filters |
| `hxc show` | Display entity details |
| `hxc get` | Get specific property value |
| `hxc edit` | Modify entity properties |
| `hxc delete` | Remove an entity |
| `hxc validate` | Validate registry integrity |
| `hxc registry` | Manage registry configuration |

See [docs/COMMANDS.md](docs/COMMANDS.md) for complete command reference.

## MCP Integration

HoxCore provides a Model Context Protocol (MCP) server for AI agent integration:

```bash
# Start MCP server
hxc-mcp

# Start in read-only mode
hxc-mcp --read-only

# Specify registry path
hxc-mcp --registry /path/to/registry
```

### Available MCP Tools

**Read Operations:**
- `list_entities` - List and filter entities
- `get_entity` - Get entity by ID/UID
- `search_entities` - Search entities
- `get_entity_property` - Get specific property
- `validate_registry` - Validate registry integrity
- `validate_entity` - Validate entity data

**Write Operations:**
- `init_registry` - Initialize new registry
- `create_entity` - Create new entity
- `edit_entity` - Modify entity
- `delete_entity` - Remove entity

See [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) for complete MCP documentation.

## Configuration

### Global Configuration

Located at `~/.hxc/config.json`:

```json
{
  "registry_path": "/path/to/default/registry"
}
```

### Registry Configuration

Located at `<registry>/config.yml`:

```yaml
version: "1.0"
name: "My Registry"
created: 2024-01-01
```

## Design Principles

- **Git-like**: Immutable UIDs, version history, minimal magic
- **Declarative**: No scripts in templates, no hidden behavior
- **Universal**: Applicable beyond software development
- **Composable**: Integrates with external tools instead of duplicating them
- **Scalable**: Designed for thousands of entities with fast queries
- **LLM-native**: Structured for both human and machine understanding

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design |
| [CONVENTIONS.md](CONVENTIONS.md) | Code conventions and standards |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines |
| [docs/API.md](docs/API.md) | Python API reference |
| [docs/COMMANDS.md](docs/COMMANDS.md) | CLI command reference |
| [docs/ENTITY_MODEL.md](docs/ENTITY_MODEL.md) | Entity model specification |
| [docs/MCP_INTEGRATION.md](docs/MCP_INTEGRATION.md) | MCP server documentation |

## For AI Agents

If you're an AI coding agent working with this codebase:

1. **Start with**: [CLAUDE.md](CLAUDE.md) for AI-specific guidance
2. **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. **Conventions**: [CONVENTIONS.md](CONVENTIONS.md) for coding standards
4. **API Reference**: [docs/API.md](docs/API.md) for implementation details

Key patterns:
- Operations are in `src/hxc/core/operations/`
- Commands are in `src/hxc/commands/`
- MCP tools wrap operations in `src/hxc/mcp/tools.py`
- All entity I/O uses path security validation

## Development

### Running Tests

```bash
pytest
pytest --cov=src/hxc
```

### Code Quality

```bash
black src tests
isort src tests
flake8 src tests
mypy src
```

### Building

```bash
python -m build
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Salvador D. Escobedo ([@SDEscobedo](https://github.com/SDEscobedo))

## Links

- **Repository**: https://github.com/SDEscobedo/hoxcore
- **PyPI**: https://pypi.org/project/hoxcore/
- **Issues**: https://github.com/SDEscobedo/hoxcore/issues
