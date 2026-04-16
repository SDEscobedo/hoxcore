"""
Shared fixtures for MCP (Model Context Protocol) integration tests.

This module provides pytest fixtures that are shared across all MCP test files.
These fixtures create temporary registries, git repositories, and other test
resources needed for testing MCP tools, resources, prompts, and server.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def git_env(monkeypatch):
    """Configure git environment variables for tests.

    This ensures git commands work in CI environments where git
    user.name and user.email are not configured globally.
    """
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test User")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@test.com")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test User")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@test.com")


@pytest.fixture
def temp_registry():
    """Create a temporary test registry with multiple entity types."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)

    # Create test entities
    project1_content = """
type: project
uid: proj-test-001
id: P-001
title: Test Project One
description: A test project for MCP tools testing
status: active
category: software.dev/cli-tool
tags: [test, mcp, cli]
start_date: 2024-01-01
due_date: 2024-12-31
children: []
related: []
repositories:
  - name: github
    url: https://github.com/test/repo
storage:
  - name: gdrive
    provider: google-drive
    url: https://drive.google.com/test
"""
    (registry_path / "projects" / "proj-proj-test-001.yml").write_text(project1_content)

    project2_content = """
type: project
uid: proj-test-002
id: P-002
title: Test Project Two
description: Another test project
status: completed
category: software.dev/web-app
tags: [test, web]
start_date: 2024-01-01
completion_date: 2024-06-30
children: []
related: []
"""
    (registry_path / "projects" / "proj-proj-test-002.yml").write_text(project2_content)

    program_content = """
type: program
uid: prog-test-001
id: PRG-001
title: Test Program
description: A test program
status: active
category: software.dev
tags: [test, program]
children: [proj-test-001, proj-test-002]
related: []
"""
    (registry_path / "programs" / "prog-prog-test-001.yml").write_text(program_content)

    mission_content = """
type: mission
uid: miss-test-001
id: M-001
title: Test Mission
description: A test mission
status: planned
category: research
tags: [test, mission]
parent: prog-test-001
children: []
related: []
"""
    (registry_path / "missions" / "miss-miss-test-001.yml").write_text(mission_content)

    action_content = """
type: action
uid: act-test-001
id: A-001
title: Test Action
description: A test action
status: active
category: maintenance
tags: [test, action]
children: []
related: []
"""
    (registry_path / "actions" / "act-act-test-001.yml").write_text(action_content)

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_registry_with_dates():
    """Create a temporary registry with entities having various due dates."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Date Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)

    # Create projects with different due dates
    project_early = {
        "type": "project",
        "uid": "proj-early",
        "id": "P-EARLY",
        "title": "Early Project",
        "status": "active",
        "due_date": "2024-03-15",
        "children": [],
        "related": [],
    }
    (registry_path / "projects" / "proj-proj-early.yml").write_text(
        yaml.dump(project_early)
    )

    project_mid = {
        "type": "project",
        "uid": "proj-mid",
        "id": "P-MID",
        "title": "Mid Project",
        "status": "active",
        "due_date": "2024-06-30",
        "children": [],
        "related": [],
    }
    (registry_path / "projects" / "proj-proj-mid.yml").write_text(
        yaml.dump(project_mid)
    )

    project_late = {
        "type": "project",
        "uid": "proj-late",
        "id": "P-LATE",
        "title": "Late Project",
        "status": "active",
        "due_date": "2024-12-31",
        "children": [],
        "related": [],
    }
    (registry_path / "projects" / "proj-proj-late.yml").write_text(
        yaml.dump(project_late)
    )

    project_nodate = {
        "type": "project",
        "uid": "proj-nodate",
        "id": "P-NODATE",
        "title": "No Date Project",
        "status": "active",
        "children": [],
        "related": [],
    }
    (registry_path / "projects" / "proj-proj-nodate.yml").write_text(
        yaml.dump(project_nodate)
    )

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def git_registry(git_env):
    """Create a temporary registry that is also a git repository."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Git Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=registry_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=registry_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def git_registry_with_entities(git_registry):
    """Create a git registry with tracked entity files for deletion testing."""
    registry_path = Path(git_registry)

    # Create test project
    project_content = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Git Project",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": ["test"],
        "children": [],
        "related": [],
    }
    with open(registry_path / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project_content, f)

    # Create second project for uniqueness tests
    project2_content = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Second Git Project",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": [],
        "children": [],
        "related": [],
    }
    with open(registry_path / "projects" / "proj-proj0002.yml", "w") as f:
        yaml.dump(project2_content, f)

    # Create test program
    program_content = {
        "type": "program",
        "uid": "prog0001",
        "id": "PRG-001",
        "title": "Git Program",
        "status": "active",
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "programs" / "prog-prog0001.yml", "w") as f:
        yaml.dump(program_content, f)

    # Create test mission
    mission_content = {
        "type": "mission",
        "uid": "miss0001",
        "id": "M-001",
        "title": "Git Mission",
        "status": "planned",
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "missions" / "miss-miss0001.yml", "w") as f:
        yaml.dump(mission_content, f)

    # Create test action
    action_content = {
        "type": "action",
        "uid": "act0001",
        "id": "A-001",
        "title": "Git Action",
        "status": "active",
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "actions" / "act-act0001.yml", "w") as f:
        yaml.dump(action_content, f)

    # Stage and commit the entity files
    subprocess.run(
        ["git", "add", "."], cwd=registry_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add test entities"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )

    return git_registry


@pytest.fixture
def empty_temp_dir():
    """Create an empty temporary directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def empty_temp_dir_with_git(git_env):
    """Create an empty temporary directory with git environment configured."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def non_empty_temp_dir():
    """Create a non-empty temporary directory."""
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "existing_file.txt"
    test_file.write_text("This file makes the directory non-empty")
    yield temp_dir
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def valid_registry_for_path_tests():
    """Create a valid registry for registry path management tests."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create required folders
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    (registry_path / "config.yml").write_text("# HoxCore Registry Config\n")

    # Create marker directory
    (registry_path / ".hxc").mkdir()

    yield str(registry_path)

    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def invalid_registry_path():
    """Create an invalid registry (missing required components)."""
    temp_dir = tempfile.mkdtemp()
    # Empty directory - not a valid registry
    yield temp_dir
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)