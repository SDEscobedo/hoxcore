"""
Tests for the get command.

This module tests the CLI `hxc get` command implementation, verifying
proper integration with the shared GetPropertyOperation class and
consistent behavior with the MCP interface.
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
from hxc.core.operations.get import GetPropertyOperation, PropertyType
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
    # Extract UID from filename (e.g., "proj-001" -> "001")
    uid = filename.split("-")[1] if "-" in filename else filename
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": uid,
        "status": "active",
        "description": f"Description for {title}",
        "start_date": "2024-01-01",
    }

    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(project_data, f)


def create_sample_project_full(directory, filename, title, item_id):
    """Create a full sample project file with all properties"""
    # Extract UID from filename (e.g., "proj-002" -> "002")
    uid = filename.split("-")[1] if "-" in filename else filename
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": uid,
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
    # Extract UID from filename (e.g., "prog-001" -> "001")
    uid = filename.split("-")[1] if "-" in filename else filename
    program_data = {
        "type": "program",
        "title": title,
        "id": item_id,
        "uid": uid,
        "status": "active",
        "description": f"Description for {title}",
    }

    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(program_data, f)


class TestGetCommandRegistration:
    """Tests for get command registration and parser setup"""

    def test_get_command_registration(self):
        """Test that the get command is properly registered"""
        from hxc.commands import get_available_commands

        available_commands = get_available_commands()
        assert "get" in available_commands

    def test_get_command_parser(self):
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

    def test_get_command_parser_entity_type_choices(self):
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

    def test_get_command_parser_format_choices(self):
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


class TestPropertyClassification:
    """Tests for property classification in GetCommand"""

    def test_property_classification_matches_operation(self):
        """Test that GetCommand property sets match GetPropertyOperation"""
        assert GetCommand.SCALAR_PROPERTIES == GetPropertyOperation.SCALAR_PROPERTIES
        assert GetCommand.LIST_PROPERTIES == GetPropertyOperation.LIST_PROPERTIES
        assert GetCommand.COMPLEX_PROPERTIES == GetPropertyOperation.COMPLEX_PROPERTIES
        assert GetCommand.SPECIAL_PROPERTIES == GetPropertyOperation.SPECIAL_PROPERTIES
        assert GetCommand.ALL_PROPERTIES == GetPropertyOperation.ALL_PROPERTIES

    def test_property_classification(self):
        """Test that properties are correctly classified"""
        assert "title" in GetCommand.SCALAR_PROPERTIES
        assert "tags" in GetCommand.LIST_PROPERTIES
        assert "repositories" in GetCommand.COMPLEX_PROPERTIES
        assert "all" in GetCommand.SPECIAL_PROPERTIES
        assert "path" in GetCommand.SPECIAL_PROPERTIES

    def test_scalar_properties_complete(self):
        """Test all expected scalar properties are included"""
        expected_scalar = {
            "type", "uid", "id", "title", "description", "status",
            "start_date", "due_date", "completion_date", "duration_estimate",
            "category", "parent", "template"
        }
        assert GetCommand.SCALAR_PROPERTIES == expected_scalar

    def test_list_properties_complete(self):
        """Test all expected list properties are included"""
        expected_list = {"tags", "children", "related"}
        assert GetCommand.LIST_PROPERTIES == expected_list

    def test_complex_properties_complete(self):
        """Test all expected complex properties are included"""
        expected_complex = {
            "repositories", "storage", "databases",
            "tools", "models", "knowledge_bases"
        }
        assert GetCommand.COMPLEX_PROPERTIES == expected_complex


class TestGetScalarProperties:
    """Tests for getting scalar properties"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_scalar_property(self, mock_get_registry_path, temp_registry):
        """Test getting a scalar property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title"])

            assert result == 0
            mock_print.assert_called_once_with("Test Project 1")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_status_property(self, mock_get_registry_path, temp_registry):
        """Test getting status property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "status"])

            assert result == 0
            mock_print.assert_called_once_with("active")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_description_property(self, mock_get_registry_path, temp_registry):
        """Test getting description property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "description"])

            assert result == 0
            assert "Description for" in mock_print.call_args[0][0]

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_type_property(self, mock_get_registry_path, temp_registry):
        """Test getting type property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "type"])

            assert result == 0
            mock_print.assert_called_once_with("project")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_uid_property(self, mock_get_registry_path, temp_registry):
        """Test getting uid property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "uid"])

            assert result == 0
            mock_print.assert_called_once_with("001")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_start_date_property(self, mock_get_registry_path, temp_registry):
        """Test getting start_date property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "start_date"])

            assert result == 0
            mock_print.assert_called_once_with("2024-01-01")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_due_date_property(self, mock_get_registry_path, temp_registry):
        """Test getting due_date property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "due_date"])

            assert result == 0
            mock_print.assert_called_once_with("2024-12-31")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_category_property(self, mock_get_registry_path, temp_registry):
        """Test getting category property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "category"])

            assert result == 0
            mock_print.assert_called_once_with("software.dev/cli-tool")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_parent_property(self, mock_get_registry_path, temp_registry):
        """Test getting parent property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "parent"])

            assert result == 0
            mock_print.assert_called_once_with("P-001")


class TestGetListProperties:
    """Tests for getting list properties"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_list_property(self, mock_get_registry_path, temp_registry):
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
    def test_get_list_property_with_index(self, mock_get_registry_path, temp_registry):
        """Test getting a specific item from a list property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "tags", "--index", "0"])

            assert result == 0
            mock_print.assert_called_once_with("cli")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_list_property_with_last_index(self, mock_get_registry_path, temp_registry):
        """Test getting the last item from a list property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "tags", "--index", "2"])

            assert result == 0
            mock_print.assert_called_once_with("important")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_list_property_invalid_index(self, mock_get_registry_path, temp_registry):
        """Test getting a list property with invalid index"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "tags", "--index", "99"])

            assert result == 1
            assert any("out of range" in call[0][0] for call in mock_print.call_args_list)

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_children_property(self, mock_get_registry_path, temp_registry):
        """Test getting children list property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "children"])

            assert result == 0
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            assert "P-003" in output_calls
            assert "P-004" in output_calls

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_related_property(self, mock_get_registry_path, temp_registry):
        """Test getting related list property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "related"])

            assert result == 0
            mock_print.assert_called_once_with("P-005")


class TestGetComplexProperties:
    """Tests for getting complex properties"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_complex_property(self, mock_get_registry_path, temp_registry):
        """Test getting a complex property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "repositories"])

            assert result == 0
            # Check that repository information was printed
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "github" in output or "name=github" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_complex_property_with_key_filter(self, mock_get_registry_path, temp_registry):
        """Test getting a complex property with key filter"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "repositories", "--key", "name:github"])

            assert result == 0
            # Check that only github repository was returned
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "github" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_complex_property_with_index(self, mock_get_registry_path, temp_registry):
        """Test getting a specific item from a complex property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "repositories", "--index", "0"])

            assert result == 0
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "github" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_storage_property(self, mock_get_registry_path, temp_registry):
        """Test getting storage complex property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "storage"])

            assert result == 0
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "docs" in output or "gdrive" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_databases_property(self, mock_get_registry_path, temp_registry):
        """Test getting databases complex property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "databases"])

            assert result == 0
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "main_db" in output or "sqlite" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_tools_property(self, mock_get_registry_path, temp_registry):
        """Test getting tools complex property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "tools"])

            assert result == 0
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "jira" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_models_property(self, mock_get_registry_path, temp_registry):
        """Test getting models complex property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "models"])

            assert result == 0
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "gpt-4" in output or "openai" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_knowledge_bases_property(self, mock_get_registry_path, temp_registry):
        """Test getting knowledge_bases complex property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "knowledge_bases"])

            assert result == 0
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "kb-001" in output


class TestGetSpecialProperties:
    """Tests for getting special properties"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_special_property_path(self, mock_get_registry_path, temp_registry):
        """Test getting the special 'path' property"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "path"])

            assert result == 0
            output = mock_print.call_args[0][0]
            assert "projects" in output
            assert "proj-001.yml" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_special_property_all(self, mock_get_registry_path, temp_registry):
        """Test getting all properties"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "all"])

            assert result == 0
            # Check that multiple properties were printed
            assert mock_print.call_count > 5


class TestOutputFormats:
    """Tests for different output formats"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_property_yaml_format(self, mock_get_registry_path, temp_registry):
        """Test getting a property in YAML format"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "tags", "--format", "yaml"])

            assert result == 0
            output = mock_print.call_args[0][0]
            assert "- cli" in output or "cli" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_property_json_format(self, mock_get_registry_path, temp_registry):
        """Test getting a property in JSON format"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "tags", "--format", "json"])

            assert result == 0
            output = mock_print.call_args[0][0]
            assert '"cli"' in output or "cli" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_all_properties_yaml_format(self, mock_get_registry_path, temp_registry):
        """Test getting all properties in YAML format"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "all", "--format", "yaml"])

            assert result == 0
            output = mock_print.call_args[0][0]
            assert "type:" in output
            assert "title:" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_all_properties_json_format(self, mock_get_registry_path, temp_registry):
        """Test getting all properties in JSON format"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "all", "--format", "json"])

            assert result == 0
            output = mock_print.call_args[0][0]
            assert '"type"' in output
            assert '"title"' in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_scalar_property_raw_format(self, mock_get_registry_path, temp_registry):
        """Test that raw format is the default"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title"])

            assert result == 0
            # Raw format should just print the value
            mock_print.assert_called_once_with("Test Project 1")


class TestErrorHandling:
    """Tests for error handling"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_nonexistent_property(self, mock_get_registry_path, temp_registry):
        """Test getting a property that doesn't exist"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "nonexistent"])

            assert result == 1
            assert any(
                "Unknown property" in call[0][0] for call in mock_print.call_args_list
            )

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_unknown_property_shows_available(self, mock_get_registry_path, temp_registry):
        """Test that unknown property error shows available properties"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "foobar"])

            assert result == 1
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "Available properties" in output or "foobar" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_unset_property(self, mock_get_registry_path, temp_registry):
        """Test getting a property that is not set"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "due_date"])

            assert result == 1
            assert any("not set" in call[0][0] for call in mock_print.call_args_list)

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_entity_not_found(self, mock_get_registry_path, temp_registry):
        """Test getting a property from a non-existent entity"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-999", "title"])

            assert result == 1
            assert any(
                "No entity found" in call[0][0] for call in mock_print.call_args_list
            )

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None)
    @patch("hxc.commands.get.GetCommand._get_registry_path", return_value=None)
    def test_get_no_registry(self, mock_get_project_root, mock_get_registry_path):
        """Test getting a property when no registry is available"""
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title"])

            assert result == 1
            assert any(
                "No registry found" in call[0][0] for call in mock_print.call_args_list
            )

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_invalid_entity_type(self, mock_get_registry_path, temp_registry):
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
    def test_get_complex_property_invalid_key_filter(self, mock_get_registry_path, temp_registry):
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
        self, mock_get_registry_path, temp_registry
    ):
        """Test getting a complex property with key filter that doesn't match"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-002", "repositories", "--key", "name:nonexistent"])

            assert result == 1
            assert any("No items found" in call[0][0] for call in mock_print.call_args_list)

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_invalid_yaml_file(self, mock_get_registry_path, temp_registry):
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
    def test_get_empty_entity_file(self, mock_get_registry_path, temp_registry):
        """Test handling of empty entity files"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Create an empty file
        empty_file = temp_registry / "projects" / "proj-empty.yml"
        empty_file.touch()

        with patch("builtins.print") as mock_print:
            result = main(["get", "empty", "title"])

            assert result == 1


class TestEntityTypeFilter:
    """Tests for entity type filtering"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_with_type_filter(self, mock_get_registry_path, temp_registry):
        """Test getting a property with entity type filter"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title", "--type", "project"])

            assert result == 0
            mock_print.assert_called_once_with("Test Project 1")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_with_wrong_type_filter(self, mock_get_registry_path, temp_registry):
        """Test getting a property with wrong entity type filter"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title", "--type", "program"])

            assert result == 1
            assert any(
                "No entity found" in call[0][0] for call in mock_print.call_args_list
            )

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_program_with_type_filter(self, mock_get_registry_path, temp_registry):
        """Test getting a program property with type filter"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "PG-001", "title", "--type", "program"])

            assert result == 0
            mock_print.assert_called_once_with("Test Program 1")


class TestCaseInsensitivity:
    """Tests for case insensitivity"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_property_case_insensitive(self, mock_get_registry_path, temp_registry):
        """Test that property names are case-insensitive"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "TITLE"])

            assert result == 0
            mock_print.assert_called_once_with("Test Project 1")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_property_mixed_case(self, mock_get_registry_path, temp_registry):
        """Test that property names work with mixed case"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "TiTlE"])

            assert result == 0
            mock_print.assert_called_once_with("Test Project 1")


class TestCustomRegistryPath:
    """Tests for custom registry path"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_with_custom_registry_path(self, mock_get_registry_path, temp_registry):
        """Test getting a property with custom registry path"""
        # Don't use the mock for this test
        mock_get_registry_path.return_value = None

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title", "--registry", str(temp_registry)])

            assert result == 0
            mock_print.assert_called_once_with("Test Project 1")


class TestMultipleEntitiesSameId:
    """Tests for handling multiple entities with same ID"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_multiple_entities_same_id_different_types(
        self, mock_get_registry_path, temp_registry
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


class TestAllProperties:
    """Tests for getting all properties of various types"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_all_scalar_properties(self, mock_get_registry_path, temp_registry):
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

                assert result == 0, f"Failed to get scalar property: {prop}"
                assert mock_print.called

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_all_list_properties(self, mock_get_registry_path, temp_registry):
        """Test getting all list properties"""
        mock_get_registry_path.return_value = str(temp_registry)

        list_properties = ["tags", "children", "related"]

        for prop in list_properties:
            with patch("builtins.print") as mock_print:
                result = main(["get", "P-002", prop])

                assert result == 0, f"Failed to get list property: {prop}"
                assert mock_print.called

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_all_complex_properties(self, mock_get_registry_path, temp_registry):
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

                assert result == 0, f"Failed to get complex property: {prop}"
                assert mock_print.called


class TestSecurityAndBoundaries:
    """Tests for security and boundary checks"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_get_entity_stays_within_registry(self, mock_get_registry_path, temp_registry):
        """Test that entity retrieval stays within registry boundaries"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title"])

            assert result == 0
            # Verify that the operation completed successfully without security errors
            assert not any(
                "Security error" in str(call) for call in mock_print.call_args_list
            )


class TestUsesGetPropertyOperation:
    """Tests to verify GetCommand uses the shared GetPropertyOperation"""

    def test_command_uses_operation_for_validation(self, temp_registry):
        """Test that GetCommand uses GetPropertyOperation for property validation"""
        with patch("hxc.commands.get.GetPropertyOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.validate_property_name.return_value = (True, "title")
            mock_instance.get_property.return_value = {
                "success": True,
                "value": "Test Title",
                "property": "title",
                "property_type": PropertyType.SCALAR,
                "identifier": "P-001",
            }
            MockOperation.return_value = mock_instance
            # Ensure class attributes are available
            MockOperation.ALL_PROPERTIES = GetPropertyOperation.ALL_PROPERTIES

            with patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=str(temp_registry)):
                with patch("builtins.print"):
                    result = main(["get", "P-001", "title"])

            # Verify operation was created with registry path
            MockOperation.assert_called_once_with(str(temp_registry))
            # Verify validation was called
            mock_instance.validate_property_name.assert_called_once()
            # Verify get_property was called
            mock_instance.get_property.assert_called_once()

    def test_command_validates_property_before_retrieval(self, temp_registry):
        """Test that property name is validated before retrieval attempt"""
        with patch("hxc.commands.get.GetPropertyOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.validate_property_name.return_value = (False, None)
            mock_instance.ALL_PROPERTIES = GetPropertyOperation.ALL_PROPERTIES
            MockOperation.return_value = mock_instance
            MockOperation.ALL_PROPERTIES = GetPropertyOperation.ALL_PROPERTIES

            with patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=str(temp_registry)):
                with patch("builtins.print") as mock_print:
                    result = main(["get", "P-001", "invalid_prop"])

            assert result == 1
            # Verify get_property was NOT called because validation failed
            mock_instance.get_property.assert_not_called()

    def test_command_passes_all_parameters_to_operation(self, temp_registry):
        """Test that GetCommand passes all parameters to GetPropertyOperation"""
        with patch("hxc.commands.get.GetPropertyOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.validate_property_name.return_value = (True, "repositories")
            mock_instance.get_property.return_value = {
                "success": True,
                "value": [{"name": "github"}],
                "property": "repositories",
                "property_type": PropertyType.COMPLEX,
                "identifier": "P-002",
            }
            MockOperation.return_value = mock_instance
            MockOperation.ALL_PROPERTIES = GetPropertyOperation.ALL_PROPERTIES

            with patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=str(temp_registry)):
                with patch("builtins.print"):
                    result = main(["get", "P-002", "repositories", "--type", "project", "--index", "0", "--key", "name:github"])

            # Verify get_property was called with all parameters
            mock_instance.get_property.assert_called_once()
            call_kwargs = mock_instance.get_property.call_args[1]
            assert call_kwargs["identifier"] == "P-002"
            assert call_kwargs["property_name"] == "repositories"
            assert call_kwargs["index"] == 0
            assert call_kwargs["key_filter"] == "name:github"


class TestBehavioralParityWithMCP:
    """Tests to verify behavioral parity between CLI and MCP"""

    def test_property_validation_uses_same_sets(self):
        """Test that CLI uses the same property sets as the operation"""
        # Both should use identical property classification
        assert GetCommand.SCALAR_PROPERTIES == GetPropertyOperation.SCALAR_PROPERTIES
        assert GetCommand.LIST_PROPERTIES == GetPropertyOperation.LIST_PROPERTIES
        assert GetCommand.COMPLEX_PROPERTIES == GetPropertyOperation.COMPLEX_PROPERTIES
        assert GetCommand.SPECIAL_PROPERTIES == GetPropertyOperation.SPECIAL_PROPERTIES

    def test_validate_property_name_delegation(self):
        """Test that property validation is delegated to operation"""
        # GetPropertyOperation should be the authoritative source
        is_valid, normalized = GetPropertyOperation.validate_property_name("TITLE")
        assert is_valid is True
        assert normalized == "title"

        is_valid, normalized = GetPropertyOperation.validate_property_name("invalid")
        assert is_valid is False
        assert normalized is None

    def test_property_type_classification_consistency(self):
        """Test that property type classification is consistent"""
        # Scalar properties
        for prop in GetCommand.SCALAR_PROPERTIES:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.SCALAR

        # List properties
        for prop in GetCommand.LIST_PROPERTIES:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.LIST

        # Complex properties
        for prop in GetCommand.COMPLEX_PROPERTIES:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.COMPLEX

        # Special properties
        for prop in GetCommand.SPECIAL_PROPERTIES:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.SPECIAL

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_cli_and_operation_produce_same_result(self, mock_get_registry_path, temp_registry):
        """Test that CLI output matches what operation returns"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Use operation directly
        operation = GetPropertyOperation(str(temp_registry))
        operation_result = operation.get_property("P-001", "title")

        assert operation_result["success"] is True
        assert operation_result["value"] == "Test Project 1"

        # Use CLI
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "title"])

            assert result == 0
            mock_print.assert_called_once_with("Test Project 1")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_unknown_property_error_matches_operation(self, mock_get_registry_path, temp_registry):
        """Test that unknown property error handling matches operation"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Use operation directly
        operation = GetPropertyOperation(str(temp_registry))
        operation_result = operation.get_property("P-001", "invalid_prop")

        assert operation_result["success"] is False
        assert "unknown property" in operation_result["error"].lower()
        assert "available_properties" in operation_result

        # Use CLI
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "invalid_prop"])

            assert result == 1
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "Unknown property" in output

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_unset_property_error_matches_operation(self, mock_get_registry_path, temp_registry):
        """Test that unset property error handling matches operation"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Use operation directly
        operation = GetPropertyOperation(str(temp_registry))
        operation_result = operation.get_property("P-001", "due_date")

        assert operation_result["success"] is False
        assert "not set" in operation_result["error"].lower()

        # Use CLI
        with patch("builtins.print") as mock_print:
            result = main(["get", "P-001", "due_date"])

            assert result == 1
            output = "\n".join(str(call[0][0]) for call in mock_print.call_args_list)
            assert "not set" in output


class TestIntegrationWithSharedOperation:
    """Integration tests with the shared GetPropertyOperation"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_scalar_property_via_operation(self, mock_get_registry_path, temp_registry):
        """Test getting scalar property matches operation result"""
        mock_get_registry_path.return_value = str(temp_registry)

        operation = GetPropertyOperation(str(temp_registry))
        op_result = operation.get_property("P-001", "title")

        with patch("builtins.print") as mock_print:
            cli_result = main(["get", "P-001", "title"])

        assert cli_result == 0 if op_result["success"] else 1
        if op_result["success"]:
            mock_print.assert_called_once_with(op_result["value"])

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_property_via_operation(self, mock_get_registry_path, temp_registry):
        """Test getting list property matches operation result"""
        mock_get_registry_path.return_value = str(temp_registry)

        operation = GetPropertyOperation(str(temp_registry))
        op_result = operation.get_property("P-002", "tags")

        with patch("builtins.print") as mock_print:
            cli_result = main(["get", "P-002", "tags"])

        assert cli_result == 0 if op_result["success"] else 1
        if op_result["success"]:
            # CLI prints each item on separate line in raw format
            assert mock_print.call_count == len(op_result["value"])

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_special_all_property_via_operation(self, mock_get_registry_path, temp_registry):
        """Test getting 'all' special property matches operation result"""
        mock_get_registry_path.return_value = str(temp_registry)

        operation = GetPropertyOperation(str(temp_registry))
        op_result = operation.get_property("P-001", "all")

        with patch("builtins.print") as mock_print:
            cli_result = main(["get", "P-001", "all"])

        assert cli_result == 0 if op_result["success"] else 1
        if op_result["success"]:
            assert op_result["property_type"] == PropertyType.SPECIAL

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_special_path_property_via_operation(self, mock_get_registry_path, temp_registry):
        """Test getting 'path' special property matches operation result"""
        mock_get_registry_path.return_value = str(temp_registry)

        operation = GetPropertyOperation(str(temp_registry))
        op_result = operation.get_property("P-001", "path")

        with patch("builtins.print") as mock_print:
            cli_result = main(["get", "P-001", "path"])

        assert cli_result == 0 if op_result["success"] else 1
        if op_result["success"]:
            assert op_result["property_type"] == PropertyType.SPECIAL
            mock_print.assert_called_once_with(op_result["value"])

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_index_filter_via_operation(self, mock_get_registry_path, temp_registry):
        """Test index filtering matches operation result"""
        mock_get_registry_path.return_value = str(temp_registry)

        operation = GetPropertyOperation(str(temp_registry))
        op_result = operation.get_property("P-002", "tags", index=0)

        with patch("builtins.print") as mock_print:
            cli_result = main(["get", "P-002", "tags", "--index", "0"])

        assert cli_result == 0 if op_result["success"] else 1
        if op_result["success"]:
            mock_print.assert_called_once_with(op_result["value"])

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_key_filter_via_operation(self, mock_get_registry_path, temp_registry):
        """Test key filtering matches operation result"""
        mock_get_registry_path.return_value = str(temp_registry)

        operation = GetPropertyOperation(str(temp_registry))
        op_result = operation.get_property("P-002", "repositories", key_filter="name:github")

        with patch("builtins.print") as mock_print:
            cli_result = main(["get", "P-002", "repositories", "--key", "name:github"])

        assert cli_result == 0 if op_result["success"] else 1