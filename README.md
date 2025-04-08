# HoxCore

**Universal Project Registry Manager**

A simple, scalable, Git-like system for managing project metadata across programs, projects, missions, and actions. Designed to work with any kind of project — from software development to event planning and personal goals.

## 🚀 Features

- Git-based registry for metadata (not source code)
- YAML files for each item with a flat, tag-rich structure
- Queryable index (SQLite) for fast searches
- Integration-ready with GitHub, Azure DevOps, Gitea, Overleaf, and more
- Designed to be extensible, including AI support

## 📁 Registry Structure

    project-registry/ 
    ├── .git/ 
    ├── index.db 
    ├── config.yml 
    ├── programs/ 
    ├── projects/ 
    ├── missions/ 
    ├── actions/

## 🛠️ Usage (planned)

- `init`: Initialize a new registry at a given path
- `create`: Create a new program/project/mission/action
- `edit`: Edit existing items
- `index`: Build and query the index
- `commit`: Save changes via Git
- `export`: Export data for LLM use

## 🔧 Tech Stack

- Python 3.10+
- Poetry for dependency management
- Typer for CLI
- SQLite for indexing
- YAML for metadata

---

## 📌 License

MIT License. Free to use, modify, and extend.
