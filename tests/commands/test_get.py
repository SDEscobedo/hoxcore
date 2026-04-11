"""
Tests for the get command
"""

import os
import pathlib
import shutil
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.cli import main
from hxc.commands.get import GetCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityType
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

    # Create sample entities
    create_sample_project(
        registry_path / "projects", "proj-001", "Test Project 1", "P-001"
    )
    create_sample_project_full(
        registry_path / "projects", "proj-002", "Test Project 2", "P-002"
    )
    create_sample_program(
        registry_path / "programs", "prog-001", "Test Program 1", "PG-001"
    )

    yield registry_path

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


def create_sample_project(directory, filename, title, item_id):
    """Create a basic sample project file"""
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": filename.split("-")[1],
        "status": "active",
        "description": f"Description for {title}",
        "start_date": "2024-01-01",
    }

    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(project_data, f)


def create_sample_project_full(directory, filename, title, item_id):
    """Create a full sample project file with all properties"""
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": filename.split("-")[1],
        "status": "completed",
        "description": f"Full description for {title}",
        "start_date": "2024-01-01",
        "due_date": "2024-12-31",
        "completion_date": "2024-11-30",
        "duration_estimate": "6 months",
        "category": "software.dev/cli-tool",
        "tags": ["cli", "test", "important"],
        "parent": "P-001",
        "children": ["P-003", "P-004"],
        "related": ["P-005"],
        "repositories": [
            {"name": "github", "url": "https://github.com/example/repo"},
            {"name": "gitlab", "url": "https://gitlab.com/example/repo"},
        ],
        "storage": [
            {"name": "docs", "provider": "gdrive", "url": "https://drive.google.com"}
        ],
        "databases": [{"name": "main_db", "type": "sqlite", "path": "/path/to/db"}],
        "tools": [
            {"name": "jira", "provider": "atlassian", "url": "https://jira.example.com"}
        ],
        "models": [
            {"id": "gpt-4", "provider": "openai", "url": "https://api.openai.com"}
        ],
        "knowledge_bases": [{"id": "kb-001", "url": "https://kb.example.com"}],
        "template": "software.dev/cli-tool.default",
    }

    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(project_data, f)


def create_sample_program(directory, filename, title, item_id):
    """Create a sample program file"""
    program_data = {
        "type": "program",
        "title": title,
        "id": item_id,
        "uid": filename.split("-")[1],
        "status": "active",
        "description": f"Description for {title}",
    }

    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(program_data, f)


def test_get_command_registration():
    """Test that the get command is properly registered"""
    from hxc.commands import get_available_commands

    available_commands = get_available_commands()
    assert "get" in available_commands


def test_get_command_parser():
    """Test get command parser registration"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = GetCommand.register_subparser(subparsers)

    # Verify parser has the expected arguments
    actions = {action.dest for action in cmd_parser._actions}
    assert "identifier" in actions
    assert "property" in actions
    assert "type" in actions
    assert "format" in actions
    assert "registry" in actions
    assert "index" in actions
    assert "key" in actions


def test_get_command_parser_entity_type_choices():
    """Test that entity type choices match enum values"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = GetCommand.register_subparser(subparsers)

    # Find the 'type' argument
    type_action = None
    for action in cmd_parser._actions:
        if action.dest == "type":
            type_action = action
            break

    assert type_action is not None
    assert type_action.choices == EntityType.values()


def test_get_command_parser_format_choices():
    """Test that format choices are correct"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = GetCommand.register_subparser(subparsers)

    # Find the 'format' argument
    format_action = None
    for action in cmd_parser._actions:
        if action.dest == "format":
            format_action = action
            break

    assert format_action is not None
    assert format_action.choices == ["raw", "yaml", "json", "pretty"]
    assert format_action.default == "raw"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_scalar_property(mock_get_registry_path, temp_registry):
    """Test getting a scalar property"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "title"])

        assert result == 0
        mock_print.assert_called_once_with("Test Project 1")


"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_scalar_property_by_uid(mock_get_registry_path, temp_registry):
    \"""Test getting a property using UID""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["get", "001", "title"])
        
        assert result == 0
        mock_print.assert_called_once_with("Test Project 1")
"""


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_list_property(mock_get_registry_path, temp_registry):
    """Test getting a list property"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "tags"])

        assert result == 0
        # Check that all tags were printed
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        assert "cli" in output_calls
        assert "test" in output_calls
        assert "important" in output_calls


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_list_property_with_index(mock_get_registry_path, temp_registry):
    """Test getting a specific item from a list property"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "tags", "--index", "0"])

        assert result == 0
        mock_print.assert_called_once_with("cli")


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_list_property_invalid_index(mock_get_registry_path, temp_registry):
    """Test getting a list property with invalid index"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "tags", "--index", "99"])

        assert result == 1
        assert any("out of range" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_complex_property(mock_get_registry_path, temp_registry):
    """Test getting a complex property"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "repositories"])

        assert result == 0
        # Check that repository information was printed
        output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "github" in output or "name=github" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_complex_property_with_key_filter(mock_get_registry_path, temp_registry):
    """Test getting a complex property with key filter"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "repositories", "--key", "name:github"])

        assert result == 0
        # Check that only github repository was returned
        output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "github" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_complex_property_with_index(mock_get_registry_path, temp_registry):
    """Test getting a specific item from a complex property"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "repositories", "--index", "0"])

        assert result == 0
        output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "github" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_special_property_path(mock_get_registry_path, temp_registry):
    """Test getting the special 'path' property"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "path"])

        assert result == 0
        output = mock_print.call_args[0][0]
        assert "projects" in output
        assert "proj-001.yml" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_special_property_all(mock_get_registry_path, temp_registry):
    """Test getting all properties"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "all"])

        assert result == 0
        # Check that multiple properties were printed
        assert mock_print.call_count > 5


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_property_yaml_format(mock_get_registry_path, temp_registry):
    """Test getting a property in YAML format"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "tags", "--format", "yaml"])

        assert result == 0
        output = mock_print.call_args[0][0]
        assert "- cli" in output or "cli" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_property_json_format(mock_get_registry_path, temp_registry):
    """Test getting a property in JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "tags", "--format", "json"])

        assert result == 0
        output = mock_print.call_args[0][0]
        assert '"cli"' in output or "cli" in output


"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_property_pretty_format(mock_get_registry_path, temp_registry):
    \"""Test getting a property in pretty format""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "tags", "--format", "pretty"])
        
        assert result == 0
        # Check that pretty format includes emoji and formatting
        output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "📋" in output or "tags:" in output
"""


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_all_properties_yaml_format(mock_get_registry_path, temp_registry):
    """Test getting all properties in YAML format"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "all", "--format", "yaml"])

        assert result == 0
        output = mock_print.call_args[0][0]
        assert "type:" in output
        assert "title:" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_all_properties_json_format(mock_get_registry_path, temp_registry):
    """Test getting all properties in JSON format"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "all", "--format", "json"])

        assert result == 0
        output = mock_print.call_args[0][0]
        assert '"type"' in output
        assert '"title"' in output


"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_all_properties_pretty_format(mock_get_registry_path, temp_registry):
    \"""Test getting all properties in pretty format""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "all", "--format", "pretty"])
        
        assert result == 0
        # Check that pretty format includes sections
        output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
        assert "Basic Information" in output or "🔖" in output
"""


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_nonexistent_property(mock_get_registry_path, temp_registry):
    """Test getting a property that doesn't exist"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "nonexistent"])

        assert result == 1
        assert any(
            "Unknown property" in call[0][0] for call in mock_print.call_args_list
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_unset_property(mock_get_registry_path, temp_registry):
    """Test getting a property that is not set"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "due_date"])

        assert result == 1
        assert any("not set" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_entity_not_found(mock_get_registry_path, temp_registry):
    """Test getting a property from a non-existent entity"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-999", "title"])

        assert result == 1
        assert any(
            "No entity found" in call[0][0] for call in mock_print.call_args_list
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_with_type_filter(mock_get_registry_path, temp_registry):
    """Test getting a property with entity type filter"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "title", "--type", "project"])

        assert result == 0
        mock_print.assert_called_once_with("Test Project 1")


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_with_wrong_type_filter(mock_get_registry_path, temp_registry):
    """Test getting a property with wrong entity type filter"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "title", "--type", "program"])

        assert result == 1
        assert any(
            "No entity found" in call[0][0] for call in mock_print.call_args_list
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None)
@patch("hxc.commands.get.GetCommand._get_registry_path", return_value=None)
def test_get_no_registry(mock_get_project_root, mock_get_registry_path):
    """Test getting a property when no registry is available"""
    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "title"])

        assert result == 1
        assert any(
            "No registry found" in call[0][0] for call in mock_print.call_args_list
        )


"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_error_handling(mock_get_registry_path, temp_registry):
    \"""Test error handling during property retrieval""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Force an error by patching the file read operation
    with patch("builtins.open", side_effect=Exception("Test error")):
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title"])
            
            assert result == 1
            assert any("Error" in call[0][0] for call in mock_print.call_args_list)
"""
"""
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_path_traversal_protection(mock_get_registry_path, temp_registry):
    \"""Test that path traversal attempts are blocked""\"
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("hxc.commands.get.resolve_safe_path", side_effect=PathSecurityError("Path traversal detected")):
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title"])
            
            assert result == 1
            assert any("Security error" in call[0][0] for call in mock_print.call_args_list)
"""


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_invalid_entity_type(mock_get_registry_path, temp_registry):
    """Test that invalid entity types are rejected"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch(
        "hxc.commands.get.EntityType.from_string",
        side_effect=ValueError("Invalid entity type"),
    ):
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title", "--type", "project"])

            assert result == 1
            assert any(
                "Invalid argument" in call[0][0] for call in mock_print.call_args_list
            )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_complex_property_invalid_key_filter(mock_get_registry_path, temp_registry):
    """Test getting a complex property with invalid key filter format"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "repositories", "--key", "invalid_format"])

        assert result == 1
        assert any(
            "Invalid key filter format" in call[0][0]
            for call in mock_print.call_args_list
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_complex_property_no_match_key_filter(
    mock_get_registry_path, temp_registry
):
    """Test getting a complex property with key filter that doesn't match"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-002", "repositories", "--key", "name:nonexistent"])

        assert result == 1
        assert any("No items found" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_all_scalar_properties(mock_get_registry_path, temp_registry):
    """Test getting all scalar properties"""
    mock_get_registry_path.return_value = str(temp_registry)

    scalar_properties = [
        "type",
        "uid",
        "id",
        "title",
        "description",
        "status",
        "start_date",
    ]

    for prop in scalar_properties:
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", prop])

            assert result == 0
            assert mock_print.called


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_all_list_properties(mock_get_registry_path, temp_registry):
    """Test getting all list properties"""
    mock_get_registry_path.return_value = str(temp_registry)

    list_properties = ["tags", "children", "related"]

    for prop in list_properties:
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", prop])

            assert result == 0
            assert mock_print.called


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_all_complex_properties(mock_get_registry_path, temp_registry):
    """Test getting all complex properties"""
    mock_get_registry_path.return_value = str(temp_registry)

    complex_properties = [
        "repositories",
        "storage",
        "databases",
        "tools",
        "models",
        "knowledge_bases",
    ]

    for prop in complex_properties:
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", prop])

            assert result == 0
            assert mock_print.called


def test_property_classification():
    """Test that properties are correctly classified"""
    assert "title" in GetCommand.SCALAR_PROPERTIES
    assert "tags" in GetCommand.LIST_PROPERTIES
    assert "repositories" in GetCommand.COMPLEX_PROPERTIES
    assert "all" in GetCommand.SPECIAL_PROPERTIES
    assert "path" in GetCommand.SPECIAL_PROPERTIES


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_entity_stays_within_registry(mock_get_registry_path, temp_registry):
    """Test that entity retrieval stays within registry boundaries"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "title"])

        assert result == 0
        # Verify that the operation completed successfully without security errors
        assert not any(
            "Security error" in str(call) for call in mock_print.call_args_list
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_invalid_yaml_file(mock_get_registry_path, temp_registry):
    """Test handling of invalid YAML files"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Create an invalid YAML file
    invalid_file = temp_registry / "projects" / "proj-invalid.yml"
    with open(invalid_file, "w") as f:
        f.write("invalid: yaml: content: [")

    with patch("builtins.print") as mock_print:
        result = main(["get", "invalid", "title"])

        assert result == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_empty_entity_file(mock_get_registry_path, temp_registry):
    """Test handling of empty entity files"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Create an empty file
    empty_file = temp_registry / "projects" / "proj-empty.yml"
    empty_file.touch()

    with patch("builtins.print") as mock_print:
        result = main(["get", "empty", "title"])

        assert result == 1


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_with_custom_registry_path(mock_get_registry_path, temp_registry):
    """Test getting a property with custom registry path"""
    # Don't use the mock for this test
    mock_get_registry_path.return_value = None

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "title", "--registry", str(temp_registry)])

        assert result == 0
        mock_print.assert_called_once_with("Test Project 1")


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_multiple_entities_same_id_different_types(
    mock_get_registry_path, temp_registry
):
    """Test getting property when multiple entities have same ID in different types"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Create a program with same ID as a project
    create_sample_program(
        temp_registry / "programs", "prog-002", "Test Program 2", "P-001"
    )

    with patch("builtins.print") as mock_print:
        # Without type filter, should find the first match
        result = main(["get", "P-001", "title"])

        assert result == 0
        # Should find one of them
        assert mock_print.called


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_get_property_case_insensitive(mock_get_registry_path, temp_registry):
    """Test that property names are case-insensitive"""
    mock_get_registry_path.return_value = str(temp_registry)

    with patch("builtins.print") as mock_print:
        result = main(["get", "P-001", "TITLE"])

        assert result == 0
        mock_print.assert_called_once_with("Test Project 1")
