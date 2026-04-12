"""
Tests for the edit command
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.cli import main
from hxc.commands.edit import EditCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.edit import (
    DuplicateIdError,
    EditOperation,
    EditOperationError,
    EntityNotFoundError,
    InvalidValueError,
    NoChangesError,
)
from hxc.utils.path_security import PathSecurityError


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
    # Create directory structure
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)

    # Create marker files and directories
    (registry_path / ".hxc").mkdir()
    (registry_path / "config.yml").write_text("# Test config")

    # Create entity directories
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create test entity files
    project_dir = registry_path / "projects"

    # Create a test project file
    project_data = {
        "type": "project",
        "uid": "12345678",
        "id": "P-001",
        "title": "Test Project",
        "description": "Original description",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": ["original", "test"],
        "children": [],
        "related": [],
        "repositories": [],
        "storage": [],
        "databases": [],
        "tools": [],
        "models": [],
        "knowledge_bases": [],
    }

    with open(project_dir / "proj-12345678.yml", "w") as f:
        yaml.dump(project_data, f)

    # Create a second project
    project_data2 = {
        "type": "project",
        "uid": "87654321",
        "id": "P-002",
        "title": "Second Project",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": ["tag1", "tag2", "tag3"],
        "children": ["child1", "child2"],
        "related": ["rel1"],
        "repositories": [{"name": "main", "url": "https://github.com/test/main"}],
        "storage": [
            {
                "name": "docs",
                "provider": "gdrive",
                "url": "https://drive.google.com/test",
            }
        ],
        "databases": [{"name": "main_db", "type": "sqlite", "url": "/path/to/db"}],
        "tools": [
            {"name": "jira", "provider": "atlassian", "url": "https://jira.test.com"}
        ],
        "models": [
            {"id": "gpt-4", "provider": "openai", "url": "https://api.openai.com"}
        ],
        "knowledge_bases": [{"id": "kb-001", "url": "https://kb.test.com"}],
    }

    with open(project_dir / "proj-87654321.yml", "w") as f:
        yaml.dump(project_data2, f)

    # Create test program file
    program_dir = registry_path / "programs"
    program_data = {
        "type": "program",
        "uid": "abcdef12",
        "id": "PG-001",
        "title": "Test Program",
        "status": "active",
        "start_date": "2024-01-01",
    }

    with open(program_dir / "prog-abcdef12.yml", "w") as f:
        yaml.dump(program_data, f)

    yield registry_path

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


def test_edit_command_registration():
    """Test that the edit command is properly registered"""
    from hxc.commands import get_available_commands

    available_commands = get_available_commands()
    assert "edit" in available_commands


def test_edit_command_parser():
    """Test edit command parser registration"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = EditCommand.register_subparser(subparsers)

    # Verify parser has the expected arguments
    actions = {action.dest for action in cmd_parser._actions}
    assert "identifier" in actions
    assert "type" in actions
    assert "set_title" in actions
    assert "set_description" in actions
    assert "set_status" in actions
    assert "add_tag" in actions
    assert "remove_tag" in actions
    assert "set_tags" in actions
    assert "dry_run" in actions
    assert "no_commit" in actions


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_title(mock_get_registry_path, temp_registry):
    """Test editing the title field"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--set-title", "New Title", "--no-commit"])

    assert result == 0

    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "New Title"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_description(mock_get_registry_path, temp_registry):
    """Test editing the description field"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        ["edit", "P-001", "--set-description", "New description", "--no-commit"]
    )

    assert result == 0

    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["description"] == "New description"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_status(mock_get_registry_path, temp_registry):
    """Test editing the status field"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--set-status", "completed", "--no-commit"])

    assert result == 0

    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["status"] == "completed"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_multiple_fields(mock_get_registry_path, temp_registry):
    """Test editing multiple fields at once"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        [
            "edit",
            "12345678",
            "--set-title",
            "Updated Title",
            "--set-description",
            "Updated description",
            "--set-status",
            "on-hold",
            "--set-due-date",
            "2024-12-31",
            "--no-commit",
        ]
    )

    assert result == 0

    # Verify all changes were made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated description"
    assert data["status"] == "on-hold"
    assert data["due_date"] == "2024-12-31"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_tag(mock_get_registry_path, temp_registry):
    """Test adding a tag"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--add-tag", "newtag", "--no-commit"])

    assert result == 0

    # Verify the tag was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "newtag" in data["tags"]
    assert "original" in data["tags"]
    assert "test" in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_multiple_tags(mock_get_registry_path, temp_registry):
    """Test adding multiple tags"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        ["edit", "12345678", "--add-tag", "tag1", "--add-tag", "tag2", "--no-commit"]
    )

    assert result == 0

    # Verify the tags were added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "tag1" in data["tags"]
    assert "tag2" in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_tag(mock_get_registry_path, temp_registry):
    """Test removing a tag"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-tag", "tag2", "--no-commit"])

    assert result == 0

    # Verify the tag was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "tag2" not in data["tags"]
    assert "tag1" in data["tags"]
    assert "tag3" in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_tags(mock_get_registry_path, temp_registry):
    """Test replacing all tags"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        ["edit", "12345678", "--set-tags", "new1", "new2", "new3", "--no-commit"]
    )

    assert result == 0

    # Verify the tags were replaced
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["tags"] == ["new1", "new2", "new3"]
    assert "original" not in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_child(mock_get_registry_path, temp_registry):
    """Test adding a child UID"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--add-child", "child-uid-1", "--no-commit"])

    assert result == 0

    # Verify the child was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "child-uid-1" in data["children"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_child(mock_get_registry_path, temp_registry):
    """Test removing a child UID"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-child", "child1", "--no-commit"])

    assert result == 0

    # Verify the child was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "child1" not in data["children"]
    assert "child2" in data["children"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_children(mock_get_registry_path, temp_registry):
    """Test replacing all children"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        [
            "edit",
            "12345678",
            "--set-children",
            "new-child-1",
            "new-child-2",
            "--no-commit",
        ]
    )

    assert result == 0

    # Verify the children were replaced
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["children"] == ["new-child-1", "new-child-2"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_related(mock_get_registry_path, temp_registry):
    """Test adding a related UID"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--add-related", "related-uid", "--no-commit"])

    assert result == 0

    # Verify the related was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "related-uid" in data["related"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_related(mock_get_registry_path, temp_registry):
    """Test removing a related UID"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-related", "rel1", "--no-commit"])

    assert result == 0

    # Verify the related was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "rel1" not in data["related"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_repository(mock_get_registry_path, temp_registry):
    """Test adding a repository using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    repo_json = json.dumps({"name": "myrepo", "url": "https://github.com/test/repo"})
    result = main(["edit", "12345678", "--add-repository", repo_json, "--no-commit"])

    assert result == 0

    # Verify the repository was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["name"] == "myrepo"
    assert data["repositories"][0]["url"] == "https://github.com/test/repo"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_repository_with_path(mock_get_registry_path, temp_registry):
    """Test adding a repository with local path using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    repo_json = json.dumps({"name": "local", "path": "./repos/myrepo"})
    result = main(["edit", "12345678", "--add-repository", repo_json, "--no-commit"])

    assert result == 0

    # Verify the repository was added with path instead of url
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["name"] == "local"
    assert data["repositories"][0]["path"] == "./repos/myrepo"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_repository_with_complex_url(mock_get_registry_path, temp_registry):
    """Test adding a repository with a URL containing multiple colons"""
    mock_get_registry_path.return_value = str(temp_registry)

    # URL with port number and protocol - this would break the old colon-delimited format
    repo_json = json.dumps(
        {"name": "gitlab", "url": "https://gitlab.example.com:8443/org/repo"}
    )
    result = main(["edit", "12345678", "--add-repository", repo_json, "--no-commit"])

    assert result == 0

    # Verify the repository was added with full URL preserved
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["name"] == "gitlab"
    assert data["repositories"][0]["url"] == "https://gitlab.example.com:8443/org/repo"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_repository(mock_get_registry_path, temp_registry):
    """Test removing a repository"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-repository", "main", "--no-commit"])

    assert result == 0

    # Verify the repository was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_storage(mock_get_registry_path, temp_registry):
    """Test adding storage using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    storage_json = json.dumps(
        {
            "name": "mystorage",
            "provider": "s3",
            "url": "https://s3.amazonaws.com/bucket",
        }
    )
    result = main(["edit", "12345678", "--add-storage", storage_json, "--no-commit"])

    assert result == 0

    # Verify the storage was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["storage"]) == 1
    assert data["storage"][0]["name"] == "mystorage"
    assert data["storage"][0]["provider"] == "s3"
    assert data["storage"][0]["url"] == "https://s3.amazonaws.com/bucket"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_storage_with_complex_url(mock_get_registry_path, temp_registry):
    """Test adding storage with Google Drive URL containing special characters"""
    mock_get_registry_path.return_value = str(temp_registry)

    storage_json = json.dumps(
        {
            "name": "gdrive-docs",
            "provider": "google-drive",
            "url": "https://drive.google.com/drive/folders/1ABC123_xyz?resourcekey=0-AbCdEfG",
        }
    )
    result = main(["edit", "12345678", "--add-storage", storage_json, "--no-commit"])

    assert result == 0

    # Verify the storage was added with full URL preserved
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["storage"]) == 1
    assert data["storage"][0]["name"] == "gdrive-docs"
    assert data["storage"][0]["provider"] == "google-drive"
    assert "resourcekey" in data["storage"][0]["url"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_storage(mock_get_registry_path, temp_registry):
    """Test removing storage"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-storage", "docs", "--no-commit"])

    assert result == 0

    # Verify the storage was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["storage"]) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_database(mock_get_registry_path, temp_registry):
    """Test adding a database using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    db_json = json.dumps(
        {"name": "mydb", "type": "postgres", "url": "postgres://localhost/mydb"}
    )
    result = main(["edit", "12345678", "--add-database", db_json, "--no-commit"])

    assert result == 0

    # Verify the database was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["databases"]) == 1
    assert data["databases"][0]["name"] == "mydb"
    assert data["databases"][0]["type"] == "postgres"
    assert data["databases"][0]["url"] == "postgres://localhost/mydb"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_database_with_credentials_url(mock_get_registry_path, temp_registry):
    """Test adding a database with URL containing credentials and port"""
    mock_get_registry_path.return_value = str(temp_registry)

    # URL with username:password@host:port pattern
    db_json = json.dumps(
        {
            "name": "production",
            "type": "postgres",
            "url": "postgres://user:pass@db.example.com:5432/production",
        }
    )
    result = main(["edit", "12345678", "--add-database", db_json, "--no-commit"])

    assert result == 0

    # Verify the database was added with full URL preserved
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["databases"]) == 1
    assert (
        data["databases"][0]["url"]
        == "postgres://user:pass@db.example.com:5432/production"
    )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_database(mock_get_registry_path, temp_registry):
    """Test removing a database"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-database", "main_db", "--no-commit"])

    assert result == 0

    # Verify the database was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["databases"]) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_tool(mock_get_registry_path, temp_registry):
    """Test adding a tool using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    tool_json = json.dumps(
        {"name": "github", "provider": "github", "url": "https://github.com"}
    )
    result = main(["edit", "12345678", "--add-tool", tool_json, "--no-commit"])

    assert result == 0

    # Verify the tool was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["tools"]) == 1
    assert data["tools"][0]["name"] == "github"
    assert data["tools"][0]["provider"] == "github"
    assert data["tools"][0]["url"] == "https://github.com"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_tool_with_atlassian_url(mock_get_registry_path, temp_registry):
    """Test adding a tool with Atlassian-style URL"""
    mock_get_registry_path.return_value = str(temp_registry)

    tool_json = json.dumps(
        {
            "name": "confluence",
            "provider": "atlassian",
            "url": "https://myorg.atlassian.net/wiki/spaces/TEAM/overview",
        }
    )
    result = main(["edit", "12345678", "--add-tool", tool_json, "--no-commit"])

    assert result == 0

    # Verify the tool was added with full URL preserved
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["tools"]) == 1
    assert data["tools"][0]["name"] == "confluence"
    assert "atlassian.net" in data["tools"][0]["url"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_tool(mock_get_registry_path, temp_registry):
    """Test removing a tool"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-tool", "jira", "--no-commit"])

    assert result == 0

    # Verify the tool was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["tools"]) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_model(mock_get_registry_path, temp_registry):
    """Test adding a model using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    model_json = json.dumps(
        {"id": "claude", "provider": "anthropic", "url": "https://api.anthropic.com"}
    )
    result = main(["edit", "12345678", "--add-model", model_json, "--no-commit"])

    assert result == 0

    # Verify the model was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["models"]) == 1
    assert data["models"][0]["id"] == "claude"
    assert data["models"][0]["provider"] == "anthropic"
    assert data["models"][0]["url"] == "https://api.anthropic.com"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_model_with_openwebui_url(mock_get_registry_path, temp_registry):
    """Test adding a model with OpenWebUI URL containing query parameters"""
    mock_get_registry_path.return_value = str(temp_registry)

    model_json = json.dumps(
        {
            "id": "local-assistant",
            "provider": "openwebui",
            "url": "http://openwebui.local/?models=assistant:latest",
        }
    )
    result = main(["edit", "12345678", "--add-model", model_json, "--no-commit"])

    assert result == 0

    # Verify the model was added with full URL preserved (including colon in query param)
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["models"]) == 1
    assert data["models"][0]["id"] == "local-assistant"
    assert "models=assistant:latest" in data["models"][0]["url"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_model(mock_get_registry_path, temp_registry):
    """Test removing a model"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-model", "gpt-4", "--no-commit"])

    assert result == 0

    # Verify the model was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["models"]) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_kb(mock_get_registry_path, temp_registry):
    """Test adding a knowledge base using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    kb_json = json.dumps({"id": "kb-new", "url": "https://kb.example.com"})
    result = main(["edit", "12345678", "--add-kb", kb_json, "--no-commit"])

    assert result == 0

    # Verify the knowledge base was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["knowledge_bases"]) == 1
    assert data["knowledge_bases"][0]["id"] == "kb-new"
    assert data["knowledge_bases"][0]["url"] == "https://kb.example.com"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_kb_with_complex_url(mock_get_registry_path, temp_registry):
    """Test adding a knowledge base with a complex URL containing UUIDs"""
    mock_get_registry_path.return_value = str(temp_registry)

    kb_json = json.dumps(
        {
            "id": "kb-registry-specs",
            "url": "http://openwebui.local/workspace/knowledge/5f0f9cc7-abc1-4def-89ab-123456789012",
        }
    )
    result = main(["edit", "12345678", "--add-kb", kb_json, "--no-commit"])

    assert result == 0

    # Verify the knowledge base was added with full URL preserved
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["knowledge_bases"]) == 1
    assert data["knowledge_bases"][0]["id"] == "kb-registry-specs"
    assert "5f0f9cc7" in data["knowledge_bases"][0]["url"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_kb(mock_get_registry_path, temp_registry):
    """Test removing a knowledge base"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-002", "--remove-kb", "kb-001", "--no-commit"])

    assert result == 0

    # Verify the knowledge base was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["knowledge_bases"]) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_dry_run(mock_get_registry_path, temp_registry):
    """Test dry-run mode (no changes written)"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Get original title
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        original_data = yaml.safe_load(f)
    original_title = original_data["title"]

    with patch("builtins.print") as mock_print:
        result = main(["edit", "12345678", "--set-title", "Dry Run Title", "--dry-run"])

    assert result == 0

    # Verify no changes were made
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == original_title

    # Verify dry-run message was printed
    assert any("Dry run" in str(call) for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_no_changes(mock_get_registry_path, temp_registry):
    """Test when no changes are specified"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["edit", "12345678"])

    assert result == 0

    # Verify warning message was printed
    assert any(
        "No changes specified" in call[0][0] for call in mock_print.call_args_list
    )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_entity_not_found(mock_get_registry_path, temp_registry):
    """Test error when entity is not found"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["edit", "nonexistent", "--set-title", "New Title"])

    assert result == 1

    # Verify error message was printed
    assert any("No entity found" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None)
@patch("hxc.commands.edit.EditCommand._get_registry_path", return_value=None)
def test_edit_no_registry(mock_get_project_root, mock_get_registry_path):
    """Test editing when no registry is available"""
    with patch("builtins.print") as mock_print:
        result = main(["edit", "12345678", "--set-title", "New Title"])

    assert result == 1

    # Verify error message was printed
    assert any("No registry found" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_with_type_filter(mock_get_registry_path, temp_registry):
    """Test editing with entity type filter"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        [
            "edit",
            "12345678",
            "--type",
            "project",
            "--set-title",
            "Filtered Title",
            "--no-commit",
        ]
    )

    assert result == 0

    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "Filtered Title"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_program(mock_get_registry_path, temp_registry):
    """Test editing a program entity"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "PG-001", "--set-title", "Updated Program", "--no-commit"])

    assert result == 0

    # Verify the change was made
    program_file = temp_registry / "programs" / "prog-abcdef12.yml"
    with open(program_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "Updated Program"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_multiple_complex_operations(mock_get_registry_path, temp_registry):
    """Test multiple complex field operations in one command using JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    repo1_json = json.dumps({"name": "repo1", "url": "https://github.com/test/repo1"})
    repo2_json = json.dumps({"name": "repo2", "url": "https://github.com/test/repo2"})
    storage_json = json.dumps(
        {"name": "storage1", "provider": "s3", "url": "https://s3.aws.com/bucket1"}
    )
    tool_json = json.dumps(
        {"name": "tool1", "provider": "provider1", "url": "https://tool1.com"}
    )

    result = main(
        [
            "edit",
            "12345678",
            "--add-repository",
            repo1_json,
            "--add-repository",
            repo2_json,
            "--add-storage",
            storage_json,
            "--add-tool",
            tool_json,
            "--no-commit",
        ]
    )

    assert result == 0

    # Verify all changes were made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 2
    assert len(data["storage"]) == 1
    assert len(data["tools"]) == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_all_scalar_fields(mock_get_registry_path, temp_registry):
    """Test editing all available scalar fields"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        [
            "edit",
            "12345678",
            "--set-title",
            "All Fields Test",
            "--set-description",
            "Testing all fields",
            "--set-status",
            "completed",
            "--set-id",
            "P-NEW",
            "--set-start-date",
            "2024-02-01",
            "--set-due-date",
            "2024-12-31",
            "--set-completion-date",
            "2024-11-30",
            "--set-duration-estimate",
            "6m",
            "--set-category",
            "test.category",
            "--set-parent",
            "parent-uid",
            "--set-template",
            "test.template",
            "--no-commit",
        ]
    )

    assert result == 0

    # Verify all changes were made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "All Fields Test"
    assert data["description"] == "Testing all fields"
    assert data["status"] == "completed"
    assert data["id"] == "P-NEW"
    assert data["start_date"] == "2024-02-01"
    assert data["due_date"] == "2024-12-31"
    assert data["completion_date"] == "2024-11-30"
    assert data["duration_estimate"] == "6m"
    assert data["category"] == "test.category"
    assert data["parent"] == "parent-uid"
    assert data["template"] == "test.template"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_error_handling(mock_get_registry_path, temp_registry):
    """Test error handling during editing"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Mock file write to raise an exception
    with patch("builtins.open", side_effect=Exception("Write error")):
        with patch("builtins.print") as mock_print:
            result = main(["edit", "12345678", "--set-title", "Error Test"])

            # Check result indicates failure
            assert result == 1

            # Check error message
            assert any("Error" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_path_traversal_protection(mock_get_registry_path, temp_registry):
    """Test that path traversal attempts are blocked"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Mock the EditOperation's find_entity_file to return a path outside registry
    with patch.object(
        EditOperation,
        "find_entity_file",
        return_value=(Path("/etc/passwd"), EntityType.PROJECT),
    ):
        with patch(
            "hxc.core.operations.edit.resolve_safe_path",
            side_effect=PathSecurityError("Path traversal detected"),
        ):
            with patch("builtins.print") as mock_print:
                result = main(["edit", "12345678", "--set-title", "Malicious"])

                assert result == 1
                assert any(
                    "Security error" in call[0][0] or "Error" in call[0][0]
                    for call in mock_print.call_args_list
                )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_invalid_yaml_file(mock_get_registry_path, temp_registry):
    """Test handling of invalid YAML files"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Create an invalid YAML file
    invalid_file = temp_registry / "projects" / "proj-invalid.yml"
    invalid_file.write_text("invalid: yaml: [")

    with patch("builtins.print") as mock_print:
        result = main(["edit", "invalid", "--set-title", "New Title"])

        # Should return error
        assert result == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_duplicate_tag(mock_get_registry_path, temp_registry):
    """Test that adding a duplicate tag is handled correctly"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--add-tag", "original", "--no-commit"])

    assert result == 0

    # Verify the tag was not duplicated
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    # Count occurrences of "original"
    assert data["tags"].count("original") == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_nonexistent_tag(mock_get_registry_path, temp_registry):
    """Test removing a tag that doesn't exist"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Get original tags
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        original_data = yaml.safe_load(f)
    original_tags = original_data["tags"].copy()

    result = main(["edit", "12345678", "--remove-tag", "nonexistent", "--no-commit"])

    assert result == 0

    # Verify tags unchanged
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["tags"] == original_tags


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_duplicate_child(mock_get_registry_path, temp_registry):
    """Test that adding a duplicate child is handled correctly"""
    mock_get_registry_path.return_value = str(temp_registry)

    # First add a child
    result = main(["edit", "12345678", "--add-child", "child-1", "--no-commit"])
    assert result == 0

    # Try to add the same child again
    result = main(["edit", "12345678", "--add-child", "child-1", "--no-commit"])
    assert result == 0

    # Verify the child was not duplicated
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["children"].count("child-1") == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_invalid_json_format_for_complex_field(
    mock_get_registry_path, temp_registry
):
    """Test handling of invalid JSON format for complex fields"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        # Pass an invalid JSON string
        result = main(
            ["edit", "12345678", "--add-repository", "not_valid_json", "--no-commit"]
        )

        # Should show warning about invalid format
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Invalid format" in printed_output or "Warning" in printed_output
        assert "JSON object" in printed_output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_invalid_json_array_instead_of_object(
    mock_get_registry_path, temp_registry
):
    """Test handling of JSON array when object is expected"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        # Pass a JSON array instead of object
        result = main(
            [
                "edit",
                "12345678",
                "--add-repository",
                '["not", "an", "object"]',
                "--no-commit",
            ]
        )

        # Should show warning about invalid format
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Invalid format" in printed_output or "Warning" in printed_output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_malformed_json_syntax(mock_get_registry_path, temp_registry):
    """Test handling of malformed JSON syntax"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        # Pass malformed JSON
        result = main(
            [
                "edit",
                "12345678",
                "--add-repository",
                '{"name": "test", "url":}',
                "--no-commit",
            ]
        )

        # Should show warning about invalid format
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Invalid format" in printed_output or "Warning" in printed_output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_nonexistent_repository(mock_get_registry_path, temp_registry):
    """Test removing a repository that doesn't exist"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(
            ["edit", "12345678", "--remove-repository", "nonexistent", "--no-commit"]
        )

        assert result == 0

        # Should show warning
        assert any(
            "not found" in str(call) or "Warning" in str(call)
            for call in mock_print.call_args_list
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_find_by_uid_in_filename(mock_get_registry_path, temp_registry):
    """Test finding entity by UID in filename"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--set-title", "Found by UID", "--no-commit"])

    assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "Found by UID"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_find_by_id_field(mock_get_registry_path, temp_registry):
    """Test finding entity by ID field in YAML"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "P-001", "--set-title", "Found by ID", "--no-commit"])

    assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "Found by ID"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_preserves_other_fields(mock_get_registry_path, temp_registry):
    """Test that editing one field doesn't affect others"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Get original data
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        original_data = yaml.safe_load(f)

    # Edit one field
    result = main(["edit", "12345678", "--set-title", "New Title Only", "--no-commit"])

    assert result == 0

    # Verify other fields unchanged
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["title"] == "New Title Only"
    assert data["description"] == original_data["description"]
    assert data["status"] == original_data["status"]
    assert data["uid"] == original_data["uid"]
    assert data["type"] == original_data["type"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_shows_changes_summary(mock_get_registry_path, temp_registry):
    """Test that changes are displayed before writing"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(
            [
                "edit",
                "12345678",
                "--set-title",
                "Changed Title",
                "--add-tag",
                "newtag",
                "--no-commit",
            ]
        )

        assert result == 0

        # Verify changes summary was printed
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert (
            "Changes to be applied" in printed_output or "Set title" in printed_output
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_invalid_entity_type(mock_get_registry_path, temp_registry):
    """Test that invalid entity type is rejected"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit):
            result = main(
                ["edit", "12345678", "--type", "invalid", "--set-title", "Test"]
            )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_combines_add_and_remove_operations(mock_get_registry_path, temp_registry):
    """Test combining add and remove operations in one command"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(
        [
            "edit",
            "P-002",
            "--remove-tag",
            "tag1",
            "--add-tag",
            "newtag",
            "--remove-child",
            "child1",
            "--add-child",
            "newchild",
            "--no-commit",
        ]
    )

    assert result == 0

    # Verify all operations were applied
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert "tag1" not in data["tags"]
    assert "newtag" in data["tags"]
    assert "child1" not in data["children"]
    assert "newchild" in data["children"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_respects_registry_boundaries(mock_get_registry_path, temp_registry):
    """Test that edit command respects registry boundaries"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--set-title", "Boundary Test", "--no-commit"])

    assert result == 0

    # Verify file is within registry
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    assert project_file.exists()
    assert str(temp_registry) in str(project_file.resolve())


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_empty_entity_data(mock_get_registry_path, temp_registry):
    """Test handling of empty entity data"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Create an empty YAML file
    empty_file = temp_registry / "projects" / "proj-empty.yml"
    empty_file.write_text("")

    with patch("builtins.print") as mock_print:
        result = main(["edit", "empty", "--set-title", "New Title"])

        # Should return error
        assert result == 1
        assert any(
            "Invalid entity data" in call[0][0] for call in mock_print.call_args_list
        )


def test_edit_field_mappings():
    """Test that field mappings are correctly defined"""
    # Verify scalar fields
    assert "title" in EditCommand.SCALAR_FIELDS
    assert "description" in EditCommand.SCALAR_FIELDS
    assert "status" in EditCommand.SCALAR_FIELDS

    # Verify list fields
    assert "tags" in EditCommand.LIST_FIELDS
    assert "children" in EditCommand.LIST_FIELDS
    assert "related" in EditCommand.LIST_FIELDS

    # Verify complex fields
    assert "repositories" in EditCommand.COMPLEX_FIELDS
    assert "storage" in EditCommand.COMPLEX_FIELDS
    assert "databases" in EditCommand.COMPLEX_FIELDS
    assert "tools" in EditCommand.COMPLEX_FIELDS
    assert "models" in EditCommand.COMPLEX_FIELDS
    assert "knowledge_bases" in EditCommand.COMPLEX_FIELDS


# ─── ID UNIQUENESS TESTS ────────────────────────────────────────────────────────


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_to_existing_id_fails(mock_get_registry_path, temp_registry):
    """Test that --set-id with an ID already used by another entity of the same type returns exit code 1"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Get original data to verify it stays unchanged
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        original_data = yaml.safe_load(f)

    with patch("builtins.print") as mock_print:
        # Try to set P-001's id to P-002 (which already exists)
        result = main(["edit", "P-001", "--set-id", "P-002"])

    # Should fail with exit code 1
    assert result == 1

    # Verify error message mentions duplicate/existing id
    printed_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "P-002" in printed_output
    assert "already exists" in printed_output.lower()

    # Verify the original file was NOT changed
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["id"] == original_data["id"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_to_same_id_succeeds(mock_get_registry_path, temp_registry):
    """Test that --set-id with the entity's own current ID (no-op) returns exit code 0"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Set id to the same value it already has (P-001)
    result = main(["edit", "12345678", "--set-id", "P-001", "--no-commit"])

    # Should succeed with exit code 0
    assert result == 0

    # Verify the file still has the same id
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["id"] == "P-001"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_to_new_unique_id_succeeds(mock_get_registry_path, temp_registry):
    """Test that --set-id with a genuinely new, unused ID returns exit code 0 and updates the file"""
    mock_get_registry_path.return_value = str(temp_registry)

    result = main(["edit", "12345678", "--set-id", "P-NEW-UNIQUE", "--no-commit"])

    # Should succeed with exit code 0
    assert result == 0

    # Verify the file was updated with the new id
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["id"] == "P-NEW-UNIQUE"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_allows_same_id_in_different_type(
    mock_get_registry_path, temp_registry
):
    """Test that --set-id with an ID that exists in a different entity type returns exit code 0"""
    mock_get_registry_path.return_value = str(temp_registry)

    # First, set the program's id to something unique
    result = main(["edit", "PG-001", "--set-id", "P-001", "--no-commit"])

    # Should succeed because P-001 exists in projects, but we're editing a program
    # The uniqueness check is scoped per entity type
    assert result == 0

    # Verify the program file was updated
    program_file = temp_registry / "programs" / "prog-abcdef12.yml"
    with open(program_file, "r") as f:
        data = yaml.safe_load(f)

    assert data["id"] == "P-001"

    # Verify the project with P-001 still exists unchanged
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        project_data = yaml.safe_load(f)

    assert project_data["id"] == "P-001"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_error_message_contains_entity_type(
    mock_get_registry_path, temp_registry
):
    """Test that the error message for duplicate ID includes the entity type"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["edit", "P-001", "--set-id", "P-002"])

    assert result == 1

    # Verify error message mentions the entity type
    printed_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "project" in printed_output.lower()


# ─── JSON FORMAT EDGE CASES ─────────────────────────────────────────────────────


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_repository_with_ssh_url(mock_get_registry_path, temp_registry):
    """Test adding a repository with SSH URL format"""
    mock_get_registry_path.return_value = str(temp_registry)

    repo_json = json.dumps({"name": "ssh-repo", "url": "git@github.com:org/repo.git"})
    result = main(["edit", "12345678", "--add-repository", repo_json, "--no-commit"])

    assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["url"] == "git@github.com:org/repo.git"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_complex_item_with_extra_fields(mock_get_registry_path, temp_registry):
    """Test that extra fields in JSON are preserved"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Include extra fields beyond the standard ones
    repo_json = json.dumps(
        {
            "name": "myrepo",
            "url": "https://github.com/org/repo",
            "branch": "main",
            "private": True,
            "custom_field": "custom_value",
        }
    )
    result = main(["edit", "12345678", "--add-repository", repo_json, "--no-commit"])

    assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["branch"] == "main"
    assert data["repositories"][0]["private"] is True
    assert data["repositories"][0]["custom_field"] == "custom_value"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_database_with_sqlite_path(mock_get_registry_path, temp_registry):
    """Test adding a SQLite database with file path instead of URL"""
    mock_get_registry_path.return_value = str(temp_registry)

    db_json = json.dumps(
        {"name": "local-db", "type": "sqlite", "path": "./data/local.db"}
    )
    result = main(["edit", "12345678", "--add-database", db_json, "--no-commit"])

    assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["databases"]) == 1
    assert data["databases"][0]["path"] == "./data/local.db"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_json_with_unicode_characters(mock_get_registry_path, temp_registry):
    """Test JSON with Unicode characters"""
    mock_get_registry_path.return_value = str(temp_registry)

    repo_json = json.dumps(
        {"name": "プロジェクト", "url": "https://example.com/日本語/path"}
    )
    result = main(["edit", "12345678", "--add-repository", repo_json, "--no-commit"])

    assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["name"] == "プロジェクト"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_json_with_empty_string_values(mock_get_registry_path, temp_registry):
    """Test JSON with empty string values"""
    mock_get_registry_path.return_value = str(temp_registry)

    repo_json = json.dumps({"name": "minimal", "url": ""})
    result = main(["edit", "12345678", "--add-repository", repo_json, "--no-commit"])

    assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, "r") as f:
        data = yaml.safe_load(f)

    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["url"] == ""


# ─── EDIT OPERATION INTEGRATION TESTS ────────────────────────────────────────────


class TestEditCommandUsesEditOperation:
    """Tests to verify EditCommand delegates to EditOperation"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_uses_shared_edit_operation_for_scalar_fields(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that scalar field edits use the shared EditOperation"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.edit.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.find_entity_file.return_value = (
                temp_registry / "projects" / "proj-12345678.yml",
                EntityType.PROJECT,
            )
            mock_instance.load_entity.return_value = {
                "type": "project",
                "uid": "12345678",
                "id": "P-001",
                "title": "Test",
                "status": "active",
            }
            mock_instance.apply_scalar_edits.return_value = [
                "Set title: 'Test' → 'New Title'"
            ]
            mock_instance.apply_list_edits.return_value = []
            MockOperation.return_value = mock_instance

            result = main(
                ["edit", "12345678", "--set-title", "New Title", "--no-commit"]
            )

        # Verify EditOperation was instantiated and methods were called
        MockOperation.assert_called_once_with(str(temp_registry))
        mock_instance.find_entity_file.assert_called_once()
        mock_instance.load_entity.assert_called_once()
        mock_instance.apply_scalar_edits.assert_called_once()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_uses_shared_edit_operation_for_list_fields(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that list field edits use the shared EditOperation"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.edit.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.find_entity_file.return_value = (
                temp_registry / "projects" / "proj-12345678.yml",
                EntityType.PROJECT,
            )
            mock_instance.load_entity.return_value = {
                "type": "project",
                "uid": "12345678",
                "id": "P-001",
                "title": "Test",
                "status": "active",
                "tags": ["existing"],
            }
            mock_instance.apply_scalar_edits.return_value = []
            mock_instance.apply_list_edits.return_value = ["Added tag: 'newtag'"]
            MockOperation.return_value = mock_instance

            result = main(["edit", "12345678", "--add-tag", "newtag", "--no-commit"])

        # Verify apply_list_edits was called
        mock_instance.apply_list_edits.assert_called_once()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_handles_duplicate_id_error_from_operation(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that DuplicateIdError from EditOperation is handled correctly"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.edit.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.find_entity_file.return_value = (
                temp_registry / "projects" / "proj-12345678.yml",
                EntityType.PROJECT,
            )
            mock_instance.load_entity.return_value = {
                "type": "project",
                "uid": "12345678",
                "id": "P-001",
                "title": "Test",
                "status": "active",
            }
            mock_instance.apply_scalar_edits.side_effect = DuplicateIdError(
                "project with id 'P-002' already exists"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                result = main(["edit", "12345678", "--set-id", "P-002"])

        assert result == 1
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "P-002" in printed_output
        assert "already exists" in printed_output.lower()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_handles_invalid_value_error_from_operation(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that InvalidValueError from EditOperation is handled correctly.

        Since argparse validates --set-status choices at parse time, we test this
        by mocking EditOperation to raise InvalidValueError for a different field
        that doesn't have argparse validation.
        """
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.edit.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.find_entity_file.return_value = (
                temp_registry / "projects" / "proj-12345678.yml",
                EntityType.PROJECT,
            )
            mock_instance.load_entity.return_value = {
                "type": "project",
                "uid": "12345678",
                "id": "P-001",
                "title": "Test",
                "status": "active",
            }
            # Simulate InvalidValueError being raised during scalar edit
            mock_instance.apply_scalar_edits.side_effect = InvalidValueError(
                "Invalid date format 'not-a-date'"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                # Use a field that doesn't have argparse choices validation
                result = main(["edit", "12345678", "--set-start-date", "not-a-date"])

        assert result == 1
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Invalid value" in printed_output


# ─── BEHAVIORAL PARITY TESTS ────────────────────────────────────────────────────


class TestEditCommandMCPParity:
    """Tests to verify CLI and MCP produce identical results"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_change_description_format_matches_mcp(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that change descriptions match MCP format"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Capture the printed output
        with patch("builtins.print") as mock_print:
            result = main(
                [
                    "edit",
                    "12345678",
                    "--set-title",
                    "New Title",
                    "--set-status",
                    "completed",
                    "--add-tag",
                    "newtag",
                    "--no-commit",
                ]
            )

        assert result == 0

        # Verify change format
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)

        # Should have changes in expected format
        assert "Set title" in printed_output or "title" in printed_output
        assert "Set status" in printed_output or "status" in printed_output
        assert "Added tag" in printed_output or "tag" in printed_output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_produces_same_file_content_as_mcp(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that CLI edit produces same file content as MCP would"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Perform edit via CLI
        result = main(
            [
                "edit",
                "12345678",
                "--set-title",
                "Parity Test",
                "--set-status",
                "on-hold",
                "--add-tag",
                "parity",
                "--no-commit",
            ]
        )

        assert result == 0

        # Verify file content
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        with open(project_file, "r") as f:
            data = yaml.safe_load(f)

        # Should have exactly the expected values
        assert data["title"] == "Parity Test"
        assert data["status"] == "on-hold"
        assert "parity" in data["tags"]

        # Original fields should be preserved
        assert data["type"] == "project"
        assert data["uid"] == "12345678"

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_id_uniqueness_matches_mcp_behavior(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that ID uniqueness validation matches MCP"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Create operation directly to compare behavior
        operation = EditOperation(str(temp_registry))

        # CLI should fail for duplicate ID
        with patch("builtins.print"):
            cli_result = main(["edit", "P-001", "--set-id", "P-002"])

        # Operation should also fail
        result = operation.find_entity_file("P-001")
        assert result is not None
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        with pytest.raises(DuplicateIdError):
            operation.apply_scalar_edits(entity_data, set_id="P-002")

        # Both should fail
        assert cli_result == 1

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_status_validation_matches_mcp(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that status validation matches MCP behavior"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Valid statuses should work
        valid_statuses = ["active", "completed", "on-hold", "cancelled", "planned"]

        for status in valid_statuses:
            result = main(["edit", "12345678", "--set-status", status, "--no-commit"])
            assert result == 0, f"Status '{status}' should be valid"

        # Invalid status should fail at argparse level (choices validation)
        # argparse validates choices and exits with code 2
        with pytest.raises(SystemExit) as exc_info:
            main(["edit", "12345678", "--set-status", "invalid-status"])

        # argparse exits with code 2 for invalid argument values
        assert exc_info.value.code == 2

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_edit_preserves_field_order_like_mcp(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that field order is preserved (YAML output consistency)"""
        mock_get_registry_path.return_value = str(temp_registry)

        result = main(["edit", "12345678", "--set-title", "Order Test", "--no-commit"])

        assert result == 0

        # Read file content
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        with open(project_file, "r") as f:
            content = f.read()

        # Type should come before uid (standard field order)
        assert content.index("type:") < content.index("uid:")


# ─── NO-COMMIT FLAG TESTS ────────────────────────────────────────────────────────


class TestEditNoCommitFlag:
    """Tests for --no-commit flag behavior"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_no_commit_flag_skips_git(self, mock_get_registry_path, temp_registry):
        """Test that --no-commit flag prevents git operations"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.edit.commit_entity_change") as mock_commit:
            result = main(
                ["edit", "12345678", "--set-title", "No Commit", "--no-commit"]
            )

        assert result == 0
        mock_commit.assert_not_called()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_no_commit_flag_prints_warning(
        self, mock_get_registry_path, temp_registry, capsys
    ):
        """Test that --no-commit flag prints a warning"""
        mock_get_registry_path.return_value = str(temp_registry)

        result = main(
            ["edit", "12345678", "--set-title", "No Commit Warning", "--no-commit"]
        )

        assert result == 0
        captured = capsys.readouterr()
        assert "--no-commit" in captured.out

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_without_no_commit_flag_calls_git(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that without --no-commit, git operations are attempted"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.edit.commit_entity_change") as mock_commit:
            result = main(["edit", "12345678", "--set-title", "With Commit"])

        assert result == 0
        mock_commit.assert_called_once()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_dry_run_also_skips_git(self, mock_get_registry_path, temp_registry):
        """Test that --dry-run also skips git operations"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.edit.commit_entity_change") as mock_commit:
            result = main(["edit", "12345678", "--set-title", "Dry Run", "--dry-run"])

        assert result == 0
        mock_commit.assert_not_called()


# ─── EDIT OPERATION DIRECT TESTS ─────────────────────────────────────────────────


class TestEditOperationDirectUsage:
    """Tests for direct usage of EditOperation (not via CLI)"""

    def test_edit_operation_find_entity_by_uid(self, temp_registry):
        """Test finding entity by UID"""
        operation = EditOperation(str(temp_registry))
        result = operation.find_entity_file("12345678")

        assert result is not None
        file_path, entity_type = result
        assert "proj-12345678.yml" in str(file_path)
        assert entity_type == EntityType.PROJECT

    def test_edit_operation_find_entity_by_id(self, temp_registry):
        """Test finding entity by ID"""
        operation = EditOperation(str(temp_registry))
        result = operation.find_entity_file("P-001")

        assert result is not None
        file_path, entity_type = result
        assert "proj-12345678.yml" in str(file_path)

    def test_edit_operation_find_with_type_filter(self, temp_registry):
        """Test finding entity with type filter"""
        operation = EditOperation(str(temp_registry))

        # Should find project
        result = operation.find_entity_file("P-001", EntityType.PROJECT)
        assert result is not None

        # Should not find with wrong type
        result = operation.find_entity_file("P-001", EntityType.PROGRAM)
        assert result is None

    def test_edit_operation_load_entity(self, temp_registry):
        """Test loading entity data"""
        operation = EditOperation(str(temp_registry))
        result = operation.find_entity_file("P-001")
        file_path, _ = result

        entity_data = operation.load_entity(file_path)

        assert entity_data["type"] == "project"
        assert entity_data["uid"] == "12345678"
        assert entity_data["id"] == "P-001"

    def test_edit_operation_apply_scalar_edits(self, temp_registry):
        """Test applying scalar edits"""
        operation = EditOperation(str(temp_registry))
        entity_data = {"type": "project", "title": "Old", "status": "active"}

        changes = operation.apply_scalar_edits(
            entity_data, set_title="New", set_status="completed"
        )

        assert entity_data["title"] == "New"
        assert entity_data["status"] == "completed"
        assert len(changes) == 2

    def test_edit_operation_apply_list_edits(self, temp_registry):
        """Test applying list edits"""
        operation = EditOperation(str(temp_registry))
        entity_data = {"tags": ["existing"], "children": [], "related": []}

        changes = operation.apply_list_edits(
            entity_data, add_tags=["new1", "new2"], add_children=["child1"]
        )

        assert "new1" in entity_data["tags"]
        assert "new2" in entity_data["tags"]
        assert "child1" in entity_data["children"]
        assert len(changes) == 3

    def test_edit_operation_id_uniqueness_validation(self, temp_registry):
        """Test ID uniqueness validation"""
        operation = EditOperation(str(temp_registry))
        result = operation.find_entity_file("P-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        # Should raise for duplicate ID
        with pytest.raises(DuplicateIdError):
            operation.validate_id_uniqueness(entity_data, "P-002")

        # Should not raise for same ID
        operation.validate_id_uniqueness(entity_data, "P-001")

        # Should not raise for unique ID
        operation.validate_id_uniqueness(entity_data, "P-UNIQUE")

    def test_edit_operation_invalid_status_raises_error(self, temp_registry):
        """Test that invalid status raises InvalidValueError"""
        operation = EditOperation(str(temp_registry))
        entity_data = {"type": "project", "status": "active"}

        with pytest.raises(InvalidValueError):
            operation.apply_scalar_edits(entity_data, set_status="invalid")

    def test_edit_operation_no_changes_error(self, temp_registry):
        """Test that no changes raises NoChangesError"""
        operation = EditOperation(str(temp_registry))

        with pytest.raises(NoChangesError):
            operation.edit_entity(identifier="P-001", use_git=False)
