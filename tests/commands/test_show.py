"""
Tests for the show command
"""
import os
import yaml
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from hxc.cli import main
from hxc.commands.show import ShowCommand


@pytest.fixture
def mock_registry_path():
    """Mock registry path for testing"""
    return "/mock/registry/path"


@pytest.fixture
def sample_project_content():
    return {
        "type": "project",
        "id": "P-001",
        "uid": "proj-123",
        "title": "Example Project",
        "description": "This project builds an AI-integrated CLI for managing modular registries.",
        "status": "active",
        "start_date": "2024-01-01"
    }


def test_show_command_registration():
    """Test that the show command is properly registered"""
    from hxc.commands import get_available_commands
    
    available_commands = get_available_commands()
    assert "show" in available_commands


def test_show_command_parser():
    """Test show command parser registration"""
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = ShowCommand.register_subparser(subparsers)
    
    # Check if the parser was created correctly
    assert cmd_parser is not None
    # Check that 'pretty' is a valid format choice
    format_arg = None
    for action in cmd_parser._actions:
        if action.dest == 'format':
            format_arg = action
            break
    assert format_arg is not None
    assert 'pretty' in format_arg.choices
    assert format_arg.default == 'pretty'


def test_find_file_by_id(mock_registry_path, sample_project_content):
    """Test finding a file by ID"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path(mock_registry_path) / "projects" / "P-001.yml"
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = [file_path]
            
            with patch('builtins.open', mock_open(read_data=yml_content)):
                result = ShowCommand.find_file(mock_registry_path, "P-001", "project")
                
                assert result == file_path


def test_find_file_by_uid(mock_registry_path, sample_project_content):
    """Test finding a file by UID"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path(mock_registry_path) / "projects" / "P-001.yml"
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = [file_path]
            
            with patch('builtins.open', mock_open(read_data=yml_content)):
                result = ShowCommand.find_file(mock_registry_path, "proj-123", "project")
                
                assert result == file_path


def test_find_file_multiple_types(mock_registry_path, sample_project_content):
    """Test finding a file by searching all types"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path(mock_registry_path) / "projects" / "P-001.yml"
    
    with patch('pathlib.Path.exists', return_value=True):
        with patch('pathlib.Path.rglob') as mock_rglob:
            mock_rglob.return_value = [file_path]
            
            with patch('builtins.open', mock_open(read_data=yml_content)):
                result = ShowCommand.find_file(mock_registry_path, "P-001", None)
                
                assert result == file_path


def test_display_file_yaml(sample_project_content):
    """Test displaying file content in YAML format"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")
    
    with patch('builtins.open', mock_open(read_data=yml_content)):
        with patch('builtins.print') as mock_print:
            result = ShowCommand.display_file(file_path, "yaml", False)
            
            assert result == 0
            # Check that print was called (with yaml content)
            assert mock_print.called


def test_display_file_json(sample_project_content):
    """Test displaying file content in JSON format"""
    # Create test data 
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")
    
    with patch('builtins.open', mock_open(read_data=yml_content)):
        with patch('builtins.print') as mock_print:
            result = ShowCommand.display_file(file_path, "json", False)
            
            assert result == 0
            # Check that print was called (with json content)
            assert mock_print.called


def test_display_file_pretty(sample_project_content):
    """Test displaying file content in pretty format"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")
    
    with patch('builtins.open', mock_open(read_data=yml_content)):
        with patch('hxc.commands.show.ShowCommand.display_pretty') as mock_display_pretty:
            result = ShowCommand.display_file(file_path, "pretty", False)
            
            assert result == 0
            # Check that the pretty display method was called
            mock_display_pretty.assert_called_once()


def test_display_file_raw(sample_project_content):
    """Test displaying raw file content"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")
    
    with patch('builtins.open', mock_open(read_data=yml_content)):
        with patch('builtins.print') as mock_print:
            result = ShowCommand.display_file(file_path, "yaml", True)
            
            assert result == 0
            # Check that print was called with raw content
            mock_print.assert_called_once_with(yml_content)


def test_show_command_main(mock_registry_path, sample_project_content):
    """Test the show command via main CLI entry point"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")
    
    with patch('hxc.commands.registry.RegistryCommand.get_registry_path', 
               return_value=mock_registry_path):
        with patch('hxc.commands.show.ShowCommand.find_file', 
                  return_value=file_path):
            with patch('hxc.commands.show.ShowCommand.display_file', 
                      return_value=0) as mock_display:
                result = main(["show", "P-001"])
                
                assert result == 0
                mock_display.assert_called_once()
                # Verify default format is "pretty"
                assert mock_display.call_args[0][1] == "pretty"


def test_show_command_file_not_found(mock_registry_path):
    """Test behavior when file is not found"""
    with patch('hxc.commands.registry.RegistryCommand.get_registry_path', 
               return_value=mock_registry_path):
        with patch('hxc.commands.show.ShowCommand.find_file', 
                  return_value=None):
            with patch('builtins.print') as mock_print:
                result = main(["show", "nonexistent-id"])
                
                assert result == 1
                # Check that an error message was printed
                assert mock_print.call_args_list[0][0][0].startswith("❌")


def test_display_pretty(sample_project_content):
    """Test the pretty display function"""
    file_path = Path("/mock/path/project.yml")
    
    with patch('builtins.print') as mock_print:
        ShowCommand.display_pretty(sample_project_content, file_path)
        
        # Verify that print was called multiple times to format the output
        assert mock_print.call_count > 5
        
        # Check for key elements in the output
        any_title_printed = any("Example Project" in str(args) for args, _ in mock_print.call_args_list)
        any_id_printed = any("P-001" in str(args) for args, _ in mock_print.call_args_list)
        any_status_printed = any("Status" in str(args) for args, _ in mock_print.call_args_list)
        
        assert any_title_printed
        assert any_id_printed
        assert any_status_printed