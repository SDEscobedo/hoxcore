"""
Tests for the edit command
"""
import os
import sys
import yaml
import pathlib
import shutil
import pytest
from unittest.mock import patch, MagicMock

from pathlib import Path
from hxc.cli import main
from hxc.commands.edit import EditCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.path_security import PathSecurityError
from hxc.core.enums import EntityType, EntityStatus


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
        "knowledge_bases": []
    }
    
    with open(project_dir / "proj-12345678.yml", 'w') as f:
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
        "repositories": [
            {"name": "main", "url": "https://github.com/test/main"}
        ],
        "storage": [
            {"name": "docs", "provider": "gdrive", "url": "https://drive.google.com/test"}
        ],
        "databases": [
            {"name": "main_db", "type": "sqlite", "url": "/path/to/db"}
        ],
        "tools": [
            {"name": "jira", "provider": "atlassian", "url": "https://jira.test.com"}
        ],
        "models": [
            {"id": "gpt-4", "provider": "openai", "url": "https://api.openai.com"}
        ],
        "knowledge_bases": [
            {"id": "kb-001", "url": "https://kb.test.com"}
        ]
    }
    
    with open(project_dir / "proj-87654321.yml", 'w') as f:
        yaml.dump(project_data2, f)
    
    # Create test program file
    program_dir = registry_path / "programs"
    program_data = {
        "type": "program",
        "uid": "abcdef12",
        "id": "PG-001",
        "title": "Test Program",
        "status": "active",
        "start_date": "2024-01-01"
    }
    
    with open(program_dir / "prog-abcdef12.yml", 'w') as f:
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


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_title(mock_get_registry_path, temp_registry):
    """Test editing the title field"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--set-title", "New Title"])
    
    assert result == 0
    
    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["title"] == "New Title"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_description(mock_get_registry_path, temp_registry):
    """Test editing the description field"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-001", "--set-description", "New description"])
    
    assert result == 0
    
    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["description"] == "New description"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_status(mock_get_registry_path, temp_registry):
    """Test editing the status field"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--set-status", "completed"])
    
    assert result == 0
    
    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["status"] == "completed"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_multiple_fields(mock_get_registry_path, temp_registry):
    """Test editing multiple fields at once"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main([
        "edit", "12345678",
        "--set-title", "Updated Title",
        "--set-description", "Updated description",
        "--set-status", "on-hold",
        "--set-due-date", "2024-12-31"
    ])
    
    assert result == 0
    
    # Verify all changes were made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["title"] == "Updated Title"
    assert data["description"] == "Updated description"
    assert data["status"] == "on-hold"
    assert data["due_date"] == "2024-12-31"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_tag(mock_get_registry_path, temp_registry):
    """Test adding a tag"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-tag", "newtag"])
    
    assert result == 0
    
    # Verify the tag was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "newtag" in data["tags"]
    assert "original" in data["tags"]
    assert "test" in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_multiple_tags(mock_get_registry_path, temp_registry):
    """Test adding multiple tags"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-tag", "tag1", "--add-tag", "tag2"])
    
    assert result == 0
    
    # Verify the tags were added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "tag1" in data["tags"]
    assert "tag2" in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_tag(mock_get_registry_path, temp_registry):
    """Test removing a tag"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-tag", "tag2"])
    
    assert result == 0
    
    # Verify the tag was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "tag2" not in data["tags"]
    assert "tag1" in data["tags"]
    assert "tag3" in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_tags(mock_get_registry_path, temp_registry):
    """Test replacing all tags"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--set-tags", "new1", "new2", "new3"])
    
    assert result == 0
    
    # Verify the tags were replaced
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["tags"] == ["new1", "new2", "new3"]
    assert "original" not in data["tags"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_child(mock_get_registry_path, temp_registry):
    """Test adding a child UID"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-child", "child-uid-1"])
    
    assert result == 0
    
    # Verify the child was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "child-uid-1" in data["children"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_child(mock_get_registry_path, temp_registry):
    """Test removing a child UID"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-child", "child1"])
    
    assert result == 0
    
    # Verify the child was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "child1" not in data["children"]
    assert "child2" in data["children"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_children(mock_get_registry_path, temp_registry):
    """Test replacing all children"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--set-children", "new-child-1", "new-child-2"])
    
    assert result == 0
    
    # Verify the children were replaced
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["children"] == ["new-child-1", "new-child-2"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_related(mock_get_registry_path, temp_registry):
    """Test adding a related UID"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-related", "related-uid"])
    
    assert result == 0
    
    # Verify the related was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "related-uid" in data["related"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_related(mock_get_registry_path, temp_registry):
    """Test removing a related UID"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-related", "rel1"])
    
    assert result == 0
    
    # Verify the related was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "rel1" not in data["related"]

"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_repository(mock_get_registry_path, temp_registry):
    \"""Test adding a repository""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-repository", "myrepo:https://github.com/test/repo"])
    
    assert result == 0
    
    # Verify the repository was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["name"] == "myrepo"
    assert data["repositories"][0]["url"] == "https://github.com/test/repo"
"""
"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_repository_with_path(mock_get_registry_path, temp_registry):
    \"""Test adding a repository with local path""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-repository", "local:./repos/myrepo"])
    
    assert result == 0
    
    # Verify the repository was added with path instead of url
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["repositories"]) == 1
    assert data["repositories"][0]["name"] == "local"
    assert data["repositories"][0]["path"] == "./repos/myrepo"
"""

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_repository(mock_get_registry_path, temp_registry):
    """Test removing a repository"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-repository", "main"])
    
    assert result == 0
    
    # Verify the repository was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["repositories"]) == 0

"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_storage(mock_get_registry_path, temp_registry):
    \"""Test adding storage""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-storage", "mystorage:s3:https://s3.amazonaws.com/bucket"])
    
    assert result == 0
    
    # Verify the storage was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["storage"]) == 1
    assert data["storage"][0]["name"] == "mystorage"
    assert data["storage"][0]["provider"] == "s3"
    assert data["storage"][0]["url"] == "https://s3.amazonaws.com/bucket"
"""

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_storage(mock_get_registry_path, temp_registry):
    """Test removing storage"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-storage", "docs"])
    
    assert result == 0
    
    # Verify the storage was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["storage"]) == 0

"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_database(mock_get_registry_path, temp_registry):
    \"""Test adding a database""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-database", "mydb:postgres:postgres://localhost/mydb"])
    
    assert result == 0
    
    # Verify the database was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["databases"]) == 1
    assert data["databases"][0]["name"] == "mydb"
    assert data["databases"][0]["type"] == "postgres"
    assert data["databases"][0]["url"] == "postgres://localhost/mydb"
"""

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_database(mock_get_registry_path, temp_registry):
    """Test removing a database"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-database", "main_db"])
    
    assert result == 0
    
    # Verify the database was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["databases"]) == 0

"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_tool(mock_get_registry_path, temp_registry):
    \"""Test adding a tool""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-tool", "github:github:https://github.com"])
    
    assert result == 0
    
    # Verify the tool was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["tools"]) == 1
    assert data["tools"][0]["name"] == "github"
    assert data["tools"][0]["provider"] == "github"
    assert data["tools"][0]["url"] == "https://github.com"
"""

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_tool(mock_get_registry_path, temp_registry):
    """Test removing a tool"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-tool", "jira"])
    
    assert result == 0
    
    # Verify the tool was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["tools"]) == 0

"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_model(mock_get_registry_path, temp_registry):
    \"""Test adding a model""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-model", "claude:anthropic:https://api.anthropic.com"])
    
    assert result == 0
    
    # Verify the model was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["models"]) == 1
    assert data["models"][0]["id"] == "claude"
    assert data["models"][0]["provider"] == "anthropic"
    assert data["models"][0]["url"] == "https://api.anthropic.com"
"""

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_model(mock_get_registry_path, temp_registry):
    """Test removing a model"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-model", "gpt-4"])
    
    assert result == 0
    
    # Verify the model was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["models"]) == 0

"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_kb(mock_get_registry_path, temp_registry):
    \"""Test adding a knowledge base""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--add-kb", "kb-new:https://kb.example.com"])
    
    assert result == 0
    
    # Verify the knowledge base was added
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["knowledge_bases"]) == 1
    assert data["knowledge_bases"][0]["id"] == "kb-new"
    assert data["knowledge_bases"][0]["url"] == "https://kb.example.com"
"""

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_kb(mock_get_registry_path, temp_registry):
    """Test removing a knowledge base"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-002", "--remove-kb", "kb-001"])
    
    assert result == 0
    
    # Verify the knowledge base was removed
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["knowledge_bases"]) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_dry_run(mock_get_registry_path, temp_registry):
    """Test dry-run mode (no changes written)"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Get original title
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        original_data = yaml.safe_load(f)
    original_title = original_data["title"]
    
    with patch("builtins.print") as mock_print:
        result = main(["edit", "12345678", "--set-title", "Dry Run Title", "--dry-run"])
    
    assert result == 0
    
    # Verify no changes were made
    with open(project_file, 'r') as f:
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
    assert any("No changes specified" in call[0][0] for call in mock_print.call_args_list)


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
    
    result = main(["edit", "12345678", "--type", "project", "--set-title", "Filtered Title"])
    
    assert result == 0
    
    # Verify the change was made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["title"] == "Filtered Title"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_program(mock_get_registry_path, temp_registry):
    """Test editing a program entity"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "PG-001", "--set-title", "Updated Program"])
    
    assert result == 0
    
    # Verify the change was made
    program_file = temp_registry / "programs" / "prog-abcdef12.yml"
    with open(program_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["title"] == "Updated Program"

"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_multiple_complex_operations(mock_get_registry_path, temp_registry):
    \"""Test multiple complex field operations in one command""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main([
        "edit", "12345678",
        "--add-repository", "repo1:https://github.com/test/repo1",
        "--add-repository", "repo2:https://github.com/test/repo2",
        "--add-storage", "storage1:s3:https://s3.aws.com/bucket1",
        "--add-tool", "tool1:provider1:https://tool1.com"
    ])
    
    assert result == 0
    
    # Verify all changes were made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert len(data["repositories"]) == 2
    assert len(data["storage"]) == 1
    assert len(data["tools"]) == 1
"""

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_all_scalar_fields(mock_get_registry_path, temp_registry):
    """Test editing all available scalar fields"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main([
        "edit", "12345678",
        "--set-title", "All Fields Test",
        "--set-description", "Testing all fields",
        "--set-status", "completed",
        "--set-id", "P-NEW",
        "--set-start-date", "2024-02-01",
        "--set-due-date", "2024-12-31",
        "--set-completion-date", "2024-11-30",
        "--set-duration-estimate", "6m",
        "--set-category", "test.category",
        "--set-parent", "parent-uid",
        "--set-template", "test.template"
    ])
    
    assert result == 0
    
    # Verify all changes were made
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
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
    
    # Mock _find_entity_file to return a path outside registry
    with patch("hxc.commands.edit.EditCommand._find_entity_file", return_value=Path("/etc/passwd")):
        with patch("hxc.commands.edit.resolve_safe_path", side_effect=PathSecurityError("Path traversal detected")):
            with patch("builtins.print") as mock_print:
                result = main(["edit", "12345678", "--set-title", "Malicious"])
                
                assert result == 1
                assert any("Security error" in call[0][0] for call in mock_print.call_args_list)


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
    
    result = main(["edit", "12345678", "--add-tag", "original"])
    
    assert result == 0
    
    # Verify the tag was not duplicated
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    # Count occurrences of "original"
    assert data["tags"].count("original") == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_nonexistent_tag(mock_get_registry_path, temp_registry):
    """Test removing a tag that doesn't exist"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Get original tags
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        original_data = yaml.safe_load(f)
    original_tags = original_data["tags"].copy()
    
    result = main(["edit", "12345678", "--remove-tag", "nonexistent"])
    
    assert result == 0
    
    # Verify tags unchanged
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["tags"] == original_tags


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_add_duplicate_child(mock_get_registry_path, temp_registry):
    """Test that adding a duplicate child is handled correctly"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # First add a child
    result = main(["edit", "12345678", "--add-child", "child-1"])
    assert result == 0
    
    # Try to add the same child again
    result = main(["edit", "12345678", "--add-child", "child-1"])
    assert result == 0
    
    # Verify the child was not duplicated
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["children"].count("child-1") == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_invalid_complex_field_format(mock_get_registry_path, temp_registry):
    """Test handling of invalid format for complex fields"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["edit", "12345678", "--add-repository", "invalid_format"])
        
        # Should show warning about invalid format
        assert any("Invalid format" in str(call) or "Warning" in str(call) 
                   for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_remove_nonexistent_repository(mock_get_registry_path, temp_registry):
    """Test removing a repository that doesn't exist"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["edit", "12345678", "--remove-repository", "nonexistent"])
        
        assert result == 0
        
        # Should show warning
        assert any("not found" in str(call) or "Warning" in str(call) 
                   for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_find_by_uid_in_filename(mock_get_registry_path, temp_registry):
    """Test finding entity by UID in filename"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--set-title", "Found by UID"])
    
    assert result == 0
    
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["title"] == "Found by UID"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_find_by_id_field(mock_get_registry_path, temp_registry):
    """Test finding entity by ID field in YAML"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "P-001", "--set-title", "Found by ID"])
    
    assert result == 0
    
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["title"] == "Found by ID"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_preserves_other_fields(mock_get_registry_path, temp_registry):
    """Test that editing one field doesn't affect others"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Get original data
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        original_data = yaml.safe_load(f)
    
    # Edit one field
    result = main(["edit", "12345678", "--set-title", "New Title Only"])
    
    assert result == 0
    
    # Verify other fields unchanged
    with open(project_file, 'r') as f:
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
        result = main([
            "edit", "12345678",
            "--set-title", "Changed Title",
            "--add-tag", "newtag"
        ])
        
        assert result == 0
        
        # Verify changes summary was printed
        printed_output = " ".join(str(call) for call in mock_print.call_args_list)
        assert "Changes to be applied" in printed_output or "Set title" in printed_output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_invalid_entity_type(mock_get_registry_path, temp_registry):
    """Test that invalid entity type is rejected"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit):
            result = main(["edit", "12345678", "--type", "invalid", "--set-title", "Test"])


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_combines_add_and_remove_operations(mock_get_registry_path, temp_registry):
    """Test combining add and remove operations in one command"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main([
        "edit", "P-002",
        "--remove-tag", "tag1",
        "--add-tag", "newtag",
        "--remove-child", "child1",
        "--add-child", "newchild"
    ])
    
    assert result == 0
    
    # Verify all operations were applied
    project_file = temp_registry / "projects" / "proj-87654321.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert "tag1" not in data["tags"]
    assert "newtag" in data["tags"]
    assert "child1" not in data["children"]
    assert "newchild" in data["children"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_respects_registry_boundaries(mock_get_registry_path, temp_registry):
    """Test that edit command respects registry boundaries"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--set-title", "Boundary Test"])
    
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
        assert any("Invalid entity data" in call[0][0] for call in mock_print.call_args_list)


def test_edit_field_mappings():
    """Test that field mappings are correctly defined"""
    # Verify scalar fields
    assert 'title' in EditCommand.SCALAR_FIELDS
    assert 'description' in EditCommand.SCALAR_FIELDS
    assert 'status' in EditCommand.SCALAR_FIELDS
    
    # Verify list fields
    assert 'tags' in EditCommand.LIST_FIELDS
    assert 'children' in EditCommand.LIST_FIELDS
    assert 'related' in EditCommand.LIST_FIELDS
    
    # Verify complex fields
    assert 'repositories' in EditCommand.COMPLEX_FIELDS
    assert 'storage' in EditCommand.COMPLEX_FIELDS
    assert 'databases' in EditCommand.COMPLEX_FIELDS
    assert 'tools' in EditCommand.COMPLEX_FIELDS
    assert 'models' in EditCommand.COMPLEX_FIELDS
    assert 'knowledge_bases' in EditCommand.COMPLEX_FIELDS


# ─── ID UNIQUENESS TESTS ────────────────────────────────────────────────────────


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_to_existing_id_fails(mock_get_registry_path, temp_registry):
    """Test that --set-id with an ID already used by another entity of the same type returns exit code 1"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Get original data to verify it stays unchanged
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
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
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["id"] == original_data["id"]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_to_same_id_succeeds(mock_get_registry_path, temp_registry):
    """Test that --set-id with the entity's own current ID (no-op) returns exit code 0"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Set id to the same value it already has (P-001)
    result = main(["edit", "12345678", "--set-id", "P-001"])
    
    # Should succeed with exit code 0
    assert result == 0
    
    # Verify the file still has the same id
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["id"] == "P-001"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_to_new_unique_id_succeeds(mock_get_registry_path, temp_registry):
    """Test that --set-id with a genuinely new, unused ID returns exit code 0 and updates the file"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["edit", "12345678", "--set-id", "P-NEW-UNIQUE"])
    
    # Should succeed with exit code 0
    assert result == 0
    
    # Verify the file was updated with the new id
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["id"] == "P-NEW-UNIQUE"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_allows_same_id_in_different_type(mock_get_registry_path, temp_registry):
    """Test that --set-id with an ID that exists in a different entity type returns exit code 0"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # First, set the program's id to something unique
    result = main(["edit", "PG-001", "--set-id", "P-001"])
    
    # Should succeed because P-001 exists in projects, but we're editing a program
    # The uniqueness check is scoped per entity type
    assert result == 0
    
    # Verify the program file was updated
    program_file = temp_registry / "programs" / "prog-abcdef12.yml"
    with open(program_file, 'r') as f:
        data = yaml.safe_load(f)
    
    assert data["id"] == "P-001"
    
    # Verify the project with P-001 still exists unchanged
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    with open(project_file, 'r') as f:
        project_data = yaml.safe_load(f)
    
    assert project_data["id"] == "P-001"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_edit_set_id_error_message_contains_entity_type(mock_get_registry_path, temp_registry):
    """Test that the error message for duplicate ID includes the entity type"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["edit", "P-001", "--set-id", "P-002"])
    
    assert result == 1
    
    # Verify error message mentions the entity type
    printed_output = " ".join(str(call) for call in mock_print.call_args_list)
    assert "project" in printed_output.lower()