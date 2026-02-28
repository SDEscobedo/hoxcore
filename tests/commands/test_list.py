"""
Tests for the list command
"""
import os
import yaml
import pathlib
import datetime
import shutil
import pytest
from unittest.mock import patch, MagicMock

from hxc.cli import main
from hxc.commands.cmd_list import ListCommand
from hxc.commands.registry import RegistryCommand


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
    projects_dir = registry_path / "projects"
    programs_dir = registry_path / "programs"
    missions_dir = registry_path / "missions"
    actions_dir = registry_path / "actions"
    
    projects_dir.mkdir()
    programs_dir.mkdir()
    missions_dir.mkdir()
    actions_dir.mkdir()
    
    # Create sample items
    # Projects
    create_sample_project(projects_dir, "proj-001", "Test Project 1", "P-001", "active")
    create_sample_project(projects_dir, "proj-002", "Test Project 2", "P-002", "completed", 
                         tags=["test", "important"], category="software.dev/cli-tool")
    create_sample_project(projects_dir, "proj-003", "Test Project 3", "P-003", "on-hold", 
                         due_date="2024-12-31", parent="P-002")
    
    # Programs
    create_sample_item(programs_dir, "prog-001", "program", "Test Program 1", "PG-001", "active")
    create_sample_item(programs_dir, "prog-002", "program", "Test Program 2", "PG-002", "planned")
    
    # Missions
    create_sample_item(missions_dir, "miss-001", "mission", "Test Mission 1", "M-001", "active")
    
    # Actions
    create_sample_item(actions_dir, "act-001", "action", "Test Action 1", "A-001", "active")
    create_sample_item(actions_dir, "act-002", "action", "Test Action 2", "A-002", "completed")
    
    yield registry_path
    
    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


def create_sample_project(directory, filename, title, item_id, status, **kwargs):
    """Create a sample project file"""
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": filename.split("-")[1],
        "status": status,
        "description": f"Description for {title}",
    }
    
    # Add optional fields
    if "tags" in kwargs:
        project_data["tags"] = kwargs["tags"]
    if "category" in kwargs:
        project_data["category"] = kwargs["category"]
    if "due_date" in kwargs:
        project_data["due_date"] = kwargs["due_date"]
    if "parent" in kwargs:
        project_data["parent"] = kwargs["parent"]
    
    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(project_data, f)


def create_sample_item(directory, filename, item_type, title, item_id, status):
    """Create a sample item file"""
    item_data = {
        "type": item_type,
        "title": title,
        "id": item_id,
        "uid": filename.split("-")[1],
        "status": status,
        "description": f"Description for {title}",
    }
    
    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(item_data, f)


def test_list_command_registration():
    """Test that the list command is properly registered"""
    from hxc.commands import get_available_commands
    
    available_commands = get_available_commands()
    assert "list" in available_commands


def test_list_command_parser():
    """Test list command parser registration"""
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = ListCommand.register_subparser(subparsers)
    
    # Verify parser has the expected arguments
    actions = {action.dest for action in cmd_parser._actions}
    assert "type" in actions
    assert "status" in actions
    assert "tags" in actions
    assert "category" in actions
    assert "parent" in actions
    assert "id" in actions
    assert "query" in actions
    assert "before" in actions
    assert "after" in actions
    assert "max" in actions
    assert "sort" in actions
    assert "desc" in actions
    assert "format" in actions


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_projects_basic(mock_get_registry_path, temp_registry):
    """Test basic listing of projects"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project"])
        
        # Check result
        assert result == 0
        
        # Check that output included all projects
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 1" in output
        assert "Test Project 2" in output
        assert "Test Project 3" in output
        assert "active" in output
        assert "completed" in output
        assert "on-hold" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_all_items(mock_get_registry_path, temp_registry):
    """Test listing all items"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "all"])
        
        # Check result
        assert result == 0
        
        # Check that output included items from all types
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project" in output
        assert "Test Program" in output
        assert "Test Mission" in output
        assert "Test Action" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_status(mock_get_registry_path, temp_registry):
    """Test filtering items by status"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--status", "completed"])
        
        # Check result
        assert result == 0
        
        # Check that output included only completed projects
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_tag(mock_get_registry_path, temp_registry):
    """Test filtering items by tag"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--tag", "important"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects with the tag
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_category(mock_get_registry_path, temp_registry):
    """Test filtering items by category"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--category", "software.dev/cli-tool"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects with the category
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_parent(mock_get_registry_path, temp_registry):
    """Test filtering items by parent"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--parent", "P-002"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects with the parent
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 3" in output
        assert "Test Project 1" not in output
        assert "Test Project 2" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_id(mock_get_registry_path, temp_registry):
    """Test filtering items by ID"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--id", "P-001"])
        
        # Check result
        assert result == 0
        
        # Check that output included only the project with the ID
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 1" in output
        assert "Test Project 2" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_query(mock_get_registry_path, temp_registry):
    """Test filtering items by text query"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--query", "Project 2"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects matching the query
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_max_items(mock_get_registry_path, temp_registry):
    """Test limiting the number of items"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--max", "2"])
        
        # Check result
        assert result == 0
        
        # Count the number of projects in the output
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        # Count project lines (excluding header and separator)
        project_lines = 0
        for line in output_calls:
            if "Project" in line and "TYPE" not in line:
                project_lines += 1
        
        assert project_lines == 2


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_sort_order(mock_get_registry_path, temp_registry):
    """Test sorting items"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        # Test ascending sort by title (default)
        result = main(["list", "project", "--sort", "title"])
        
        # Check result
        assert result == 0
        
        # Get the output lines
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        project_lines = [line for line in output_calls if "Project" in line and "TYPE" not in line]
        
        # Check that projects are sorted by title
        assert "Test Project 1" in project_lines[0]
        assert "Test Project 2" in project_lines[1]
        assert "Test Project 3" in project_lines[2]
        
        # Clear the mock for the next test
        mock_print.reset_mock()
        
        # Test descending sort by title
        result = main(["list", "project", "--sort", "title", "--desc"])
        
        # Check result
        assert result == 0
        
        # Get the output lines
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        project_lines = [line for line in output_calls if "Project" in line and "TYPE" not in line]
        
        # Check that projects are sorted by title in descending order
        assert "Test Project 3" in project_lines[0]
        assert "Test Project 2" in project_lines[1]
        assert "Test Project 1" in project_lines[2]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_output_formats(mock_get_registry_path, temp_registry):
    """Test different output formats"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Test yaml format
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--format", "yaml", "--id", "P-001"])
        
        # Check result
        assert result == 0
        
        # Check that output is in YAML format
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "title: Test Project 1" in output
        assert "type: project" in output
        assert "id: P-001" in output
    
    # Test json format
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--format", "json", "--id", "P-001"])
        
        # Check result
        assert result == 0
        
        # Check that output is in JSON format
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert '"title": "Test Project 1"' in output
        assert '"type": "project"' in output
        assert '"id": "P-001"' in output
    
    # Test id format
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--format", "id"])
        
        # Check result
        assert result == 0
        
        # Check that output contains only IDs
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        
        assert "P-001" in output_calls
        assert "P-002" in output_calls
        assert "P-003" in output_calls
        assert "Test Project" not in "\n".join(output_calls)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None)
@patch("hxc.commands.cmd_list.ListCommand._get_registry_path", return_value=None)
def test_list_no_registry(mock_get_project_root, mock_get_registry_path):
    """Test listing with no registry found"""
    with patch("builtins.print") as mock_print:
        result = main(["list", "project"])
        
        # Check result indicates failure
        assert result == 1
        
        # Check error message
        mock_print.assert_called_once()
        assert "No registry found" in mock_print.call_args[0][0]
