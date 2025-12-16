"""
Tests for the create command
"""
import os
import yaml
import pathlib
import shutil
import pytest
from unittest.mock import patch, MagicMock

from hxc.cli import main
from hxc.commands.create import CreateCommand
from hxc.commands.registry import RegistryCommand
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
    
    yield registry_path
    
    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


def test_create_command_registration():
    """Test that the create command is properly registered"""
    from hxc.commands import get_available_commands
    
    available_commands = get_available_commands()
    assert "create" in available_commands


def test_create_command_parser():
    """Test create command parser registration"""
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = CreateCommand.register_subparser(subparsers)
    
    # Verify parser has the expected arguments
    actions = {action.dest for action in cmd_parser._actions}
    assert "type" in actions
    assert "title" in actions
    assert "custom_id" in actions
    assert "description" in actions
    assert "status" in actions
    assert "start_date" in actions
    assert "due_date" in actions


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_project_basic(mock_get_registry_path, temp_registry):
    """Test creating a basic project"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Fix uuid for predictable output
    with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Test Project"])
            
            # Check result
            assert result == 0
            
            # Check that file was created
            project_file = temp_registry / "projects" / "proj-12345678.yml"
            assert project_file.exists(), f"Project file {project_file} not created"
            
            # Check file contents
            with open(project_file, 'r') as f:
                project_data = yaml.safe_load(f)
                
            assert project_data["type"] == "project"
            assert project_data["title"] == "Test Project"
            assert project_data["uid"] == "12345678"
            assert project_data["status"] == "active"
            assert "start_date" in project_data
            
            # Check success message
            mock_print.assert_called_once()
            assert "Created project" in mock_print.call_args[0][0]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_project_full(mock_get_registry_path, temp_registry):
    """Test creating a project with all options"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Fix uuid for predictable output
    with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
        result = main([
            "create", "project", "Full Project",
            "--id", "P-001",
            "--description", "This is a full project",
            "--status", "on-hold",
            "--start-date", "2024-01-01",
            "--due-date", "2024-12-31",
            "--category", "software.dev/cli-tool",
            "--tags", "cli", "test", "yaml",
            "--parent", "P-000",
            "--template", "software.dev/cli-tool.default"
        ])
        
        # Check result
        assert result == 0
        
        # Check that file was created
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()
        
        # Check file contents
        with open(project_file, 'r') as f:
            project_data = yaml.safe_load(f)
            
        assert project_data["type"] == "project"
        assert project_data["title"] == "Full Project"
        assert project_data["id"] == "P-001"
        assert project_data["description"] == "This is a full project"
        assert project_data["status"] == "on-hold"
        assert project_data["start_date"] == "2024-01-01"
        assert project_data["due_date"] == "2024-12-31"
        assert project_data["category"] == "software.dev/cli-tool"
        assert project_data["tags"] == ["cli", "test", "yaml"]
        assert project_data["parent"] == "P-000"
        assert project_data["template"] == "software.dev/cli-tool.default"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_program(mock_get_registry_path, temp_registry):
    """Test creating a program"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Fix uuid for predictable output
    with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
        result = main(["create", "program", "Test Program"])
        
        # Check result
        assert result == 0
        
        # Check that file was created
        program_file = temp_registry / "programs" / "prog-12345678.yml"
        assert program_file.exists()
        
        # Check file contents
        with open(program_file, 'r') as f:
            program_data = yaml.safe_load(f)
            
        assert program_data["type"] == "program"
        assert program_data["title"] == "Test Program"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_action(mock_get_registry_path, temp_registry):
    """Test creating an action"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Fix uuid for predictable output
    with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
        result = main(["create", "action", "Test Action"])
        
        # Check result
        assert result == 0
        
        # Check that file was created
        action_file = temp_registry / "actions" / "act-12345678.yml"
        assert action_file.exists()
        
        # Check file contents
        with open(action_file, 'r') as f:
            action_data = yaml.safe_load(f)
            
        assert action_data["type"] == "action"
        assert action_data["title"] == "Test Action"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_mission(mock_get_registry_path, temp_registry):
    """Test creating a mission"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Fix uuid for predictable output
    with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
        result = main(["create", "mission", "Test Mission"])
        
        # Check result
        assert result == 0
        
        # Check that file was created
        mission_file = temp_registry / "missions" / "miss-12345678.yml"
        assert mission_file.exists()
        
        # Check file contents
        with open(mission_file, 'r') as f:
            mission_data = yaml.safe_load(f)
            
        assert mission_data["type"] == "mission"
        assert mission_data["title"] == "Test Mission"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None)
@patch("hxc.commands.create.CreateCommand._get_registry_path", return_value=None)
def test_create_no_registry(mock_get_project_root, mock_get_registry_path):
    """Test creating an entity when no registry is available"""
    with patch("builtins.print") as mock_print:
        result = main(["create", "project", "Test Project"])
        
        # Check result indicates failure
        assert result == 1
        
        # Check error message
        mock_print.assert_called_once()
        assert "No registry found" in mock_print.call_args[0][0]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_error_handling(mock_get_registry_path, temp_registry):
    """Test error handling during entity creation"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Force an error by patching the file write operation
    with patch("builtins.open", side_effect=Exception("Test error")):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Error Project"])
            
            # Check result indicates failure
            assert result == 1
            
            # Check error message
            assert any("Error creating project" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_path_traversal_protection(mock_get_registry_path, temp_registry):
    """Test that path traversal attempts are blocked during entity creation"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock get_safe_entity_path to raise PathSecurityError
    with patch("hxc.commands.create.get_safe_entity_path", side_effect=PathSecurityError("Path traversal detected")):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Malicious Project"])
            
            # Check result indicates failure
            assert result == 1
            
            # Check that security error message is displayed
            assert any("Security error" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_invalid_entity_type_protection(mock_get_registry_path, temp_registry):
    """Test that invalid entity types are rejected"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock get_safe_entity_path to raise ValueError for invalid type
    with patch("hxc.commands.create.get_safe_entity_path", side_effect=ValueError("Invalid entity type")):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Test Project"])
            
            # Check result indicates failure
            assert result == 1
            
            # Check that error message is displayed
            assert any("Invalid entity type" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_entity_stays_within_registry(mock_get_registry_path, temp_registry):
    """Test that created entities are always within the registry boundaries"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Fix uuid for predictable output
    with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
        result = main(["create", "project", "Test Project"])
        
        # Check result
        assert result == 0
        
        # Check that file was created within registry
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()
        
        # Verify the file is within the registry root
        assert str(temp_registry) in str(project_file.resolve())
        
        # Verify the file is in the correct subdirectory
        assert project_file.parent == temp_registry / "projects"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_all_entity_types_within_registry(mock_get_registry_path, temp_registry):
    """Test that all entity types are created within their respective directories"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    entity_types = [
        ("program", "programs", "prog"),
        ("project", "projects", "proj"),
        ("mission", "missions", "miss"),
        ("action", "actions", "act")
    ]
    
    for entity_type, folder, prefix in entity_types:
        # Fix uuid for predictable output
        with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
            result = main(["create", entity_type, f"Test {entity_type.title()}"])
            
            # Check result
            assert result == 0
            
            # Check that file was created in correct location
            entity_file = temp_registry / folder / f"{prefix}-12345678.yml"
            assert entity_file.exists()
            
            # Verify the file is within the registry root
            assert str(temp_registry) in str(entity_file.resolve())
            
            # Verify the file is in the correct subdirectory
            assert entity_file.parent == temp_registry / folder
            
            # Clean up for next iteration
            entity_file.unlink()