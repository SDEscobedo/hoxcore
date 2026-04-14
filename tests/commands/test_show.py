"""
Tests for the show command
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.cli import main
from hxc.commands.show import ShowCommand
from hxc.core.enums import EntityType, OutputFormat
from hxc.core.operations.show import ShowOperation
from hxc.utils.path_security import PathSecurityError


@pytest.fixture
def mock_registry_path(tmp_path):
    """Mock registry path for testing - uses tmp_path for cross-platform compatibility"""
    return str(tmp_path / "mock_registry")


@pytest.fixture
def sample_project_content():
    return {
        "type": "project",
        "id": "P-001",
        "uid": "proj-123",
        "title": "Example Project",
        "description": "This project builds an AI-integrated CLI for managing modular registries.",
        "status": "active",
        "start_date": "2024-01-01",
    }


@pytest.fixture
def temp_registry():
    """Create a temporary test registry"""
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

    # Create test project
    project_content = """
type: project
uid: proj-test-001
id: P-001
title: Test Project One
description: A test project for ShowCommand testing
status: active
category: software.dev/cli-tool
tags:
  - test
  - cli
start_date: "2024-01-01"
due_date: "2024-12-31"
children: []
related: []
"""
    (registry_path / "projects" / "proj-proj-test-001.yml").write_text(project_content)

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


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
        if action.dest == "format":
            format_arg = action
            break
    assert format_arg is not None
    assert "pretty" in format_arg.choices
    assert format_arg.default == "pretty"


class TestShowCommandFindFile:
    """Tests for ShowCommand.find_file() method"""

    def test_find_file_by_id(self, mock_registry_path, sample_project_content, tmp_path):
        """Test finding a file by ID delegates to ShowOperation"""
        file_path = tmp_path / "projects" / "proj-proj-123.yml"

        with patch.object(ShowOperation, "find_entity_file") as mock_find:
            mock_find.return_value = file_path

            result = ShowCommand.find_file(
                mock_registry_path, "P-001", EntityType.PROJECT
            )

            mock_find.assert_called_once_with("P-001", EntityType.PROJECT)
            assert result == file_path

    def test_find_file_by_uid(self, mock_registry_path, sample_project_content, tmp_path):
        """Test finding a file by UID delegates to ShowOperation"""
        file_path = tmp_path / "projects" / "proj-proj-123.yml"

        with patch.object(ShowOperation, "find_entity_file") as mock_find:
            mock_find.return_value = file_path

            result = ShowCommand.find_file(
                mock_registry_path, "proj-123", EntityType.PROJECT
            )

            mock_find.assert_called_once_with("proj-123", EntityType.PROJECT)
            assert result == file_path

    def test_find_file_multiple_types(self, mock_registry_path, sample_project_content, tmp_path):
        """Test finding a file by searching all types (no type filter)"""
        file_path = tmp_path / "projects" / "proj-proj-123.yml"

        with patch.object(ShowOperation, "find_entity_file") as mock_find:
            mock_find.return_value = file_path

            result = ShowCommand.find_file(mock_registry_path, "P-001", None)

            mock_find.assert_called_once_with("P-001", None)
            assert result == file_path

    def test_find_file_not_found(self, mock_registry_path):
        """Test finding a file that doesn't exist"""
        with patch.object(ShowOperation, "find_entity_file") as mock_find:
            mock_find.return_value = None

            result = ShowCommand.find_file(
                mock_registry_path, "nonexistent", EntityType.PROJECT
            )

            assert result is None

    def test_find_file_creates_show_operation(self, mock_registry_path):
        """Test that find_file creates ShowOperation with correct registry path"""
        with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
            mock_instance = MagicMock()
            mock_instance.find_entity_file.return_value = None
            MockShowOperation.return_value = mock_instance

            ShowCommand.find_file(mock_registry_path, "P-001", EntityType.PROJECT)

            MockShowOperation.assert_called_once_with(mock_registry_path)


class TestShowCommandDisplayFile:
    """Tests for ShowCommand.display_file() method"""

    def test_display_file_yaml(self, sample_project_content, tmp_path):
        """Test displaying file content in YAML format"""
        file_path = tmp_path / "project.yml"

        with patch("builtins.print") as mock_print:
            result = ShowCommand.display_file(
                file_path, sample_project_content, OutputFormat.YAML
            )

            assert result == 0
            # Check that print was called with yaml content
            assert mock_print.called
            # Verify YAML output was generated
            call_args = mock_print.call_args[0][0]
            assert "type: project" in call_args

    def test_display_file_json(self, sample_project_content, tmp_path):
        """Test displaying file content in JSON format"""
        file_path = tmp_path / "project.yml"

        with patch("builtins.print") as mock_print:
            result = ShowCommand.display_file(
                file_path, sample_project_content, OutputFormat.JSON
            )

            assert result == 0
            # Check that print was called with json content
            assert mock_print.called
            call_args = mock_print.call_args[0][0]
            # Verify JSON structure
            assert '"type": "project"' in call_args

    def test_display_file_pretty(self, sample_project_content, tmp_path):
        """Test displaying file content in pretty format"""
        file_path = tmp_path / "project.yml"

        with patch.object(ShowCommand, "display_pretty") as mock_display_pretty:
            result = ShowCommand.display_file(
                file_path, sample_project_content, OutputFormat.PRETTY
            )

            assert result == 0
            # Check that the pretty display method was called
            mock_display_pretty.assert_called_once_with(sample_project_content, file_path)

    def test_display_file_error_handling(self, sample_project_content, tmp_path):
        """Test error handling in display_file"""
        file_path = tmp_path / "project.yml"

        with patch("yaml.dump", side_effect=Exception("Test error")):
            with patch("builtins.print") as mock_print:
                result = ShowCommand.display_file(
                    file_path, sample_project_content, OutputFormat.YAML
                )

                assert result == 1
                # Check that error message was printed
                assert any(
                    "Error reading file" in str(call[0][0])
                    for call in mock_print.call_args_list
                )


class TestShowCommandDisplayPretty:
    """Tests for ShowCommand.display_pretty() method"""

    def test_display_pretty(self, sample_project_content, tmp_path):
        """Test the pretty display function"""
        file_path = tmp_path / "project.yml"

        with patch("builtins.print") as mock_print:
            ShowCommand.display_pretty(sample_project_content, file_path)

            # Verify that print was called multiple times to format the output
            assert mock_print.call_count > 5

            # Check for key elements in the output
            all_output = " ".join(
                str(args[0]) if args else "" for args, _ in mock_print.call_args_list
            )

            assert "Example Project" in all_output
            assert "P-001" in all_output
            assert "Status" in all_output

    def test_display_pretty_with_all_fields(self, sample_project_content, tmp_path):
        """Test pretty display with all possible fields"""
        file_path = tmp_path / "project.yml"

        # Add all possible fields
        full_content = {
            **sample_project_content,
            "due_date": "2024-12-31",
            "completion_date": "2024-11-30",
            "duration_estimate": "6 months",
            "category": "software.dev/cli-tool",
            "tags": ["cli", "registry", "ai"],
            "parent": "P-000",
            "children": ["P-002", "P-003"],
            "related": ["P-004"],
            "repositories": [{"name": "main", "url": "https://github.com/example/repo"}],
            "storage": [
                {"name": "docs", "provider": "gdrive", "url": "https://drive.google.com"}
            ],
            "databases": [{"name": "main_db", "type": "sqlite", "path": str(tmp_path / "db")}],
            "tools": [
                {"name": "jira", "provider": "atlassian", "url": "https://jira.example.com"}
            ],
            "models": [
                {"id": "gpt-4", "provider": "openai", "url": "https://api.openai.com"}
            ],
            "knowledge_bases": [{"id": "kb-001", "url": "https://kb.example.com"}],
            "template": "software.dev/cli-tool.default",
        }

        with patch("builtins.print") as mock_print:
            ShowCommand.display_pretty(full_content, file_path)

            # Verify that all sections are printed
            printed_text = " ".join(
                str(args[0]) if args else "" for args, _ in mock_print.call_args_list
            )

            assert "Description" in printed_text
            assert "Status" in printed_text
            assert "Classification" in printed_text
            assert "Hierarchy" in printed_text
            assert "Repositories" in printed_text
            assert "Storage" in printed_text
            assert "Databases" in printed_text
            assert "Tools" in printed_text
            assert "Models" in printed_text
            assert "Knowledge Bases" in printed_text
            assert "Template" in printed_text


class TestShowCommandExecute:
    """Tests for ShowCommand.execute() via CLI entry point"""

    def test_show_command_main(self, mock_registry_path, sample_project_content, tmp_path):
        """Test the show command via main CLI entry point"""
        mock_file_path = str(tmp_path / "project.yml")

        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                mock_instance = MagicMock()
                mock_instance.get_entity.return_value = {
                    "success": True,
                    "entity": sample_project_content,
                    "file_path": mock_file_path,
                    "identifier": "P-001",
                }
                MockShowOperation.return_value = mock_instance

                with patch.object(ShowCommand, "display_file", return_value=0) as mock_display:
                    result = main(["show", "P-001"])

                    assert result == 0
                    mock_display.assert_called_once()
                    # Verify display_file called with correct format
                    call_args = mock_display.call_args[0]
                    assert call_args[2] == OutputFormat.PRETTY

    def test_show_command_file_not_found(self, mock_registry_path):
        """Test behavior when file is not found"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                mock_instance = MagicMock()
                mock_instance.get_entity.return_value = {
                    "success": False,
                    "error": "Entity not found: nonexistent-id",
                    "entity": None,
                    "file_path": None,
                    "identifier": "nonexistent-id",
                }
                MockShowOperation.return_value = mock_instance

                with patch("builtins.print") as mock_print:
                    result = main(["show", "nonexistent-id"])

                    assert result == 1
                    # Check that an error message was printed
                    assert any(
                        "❌" in str(call[0][0])
                        for call in mock_print.call_args_list
                    )

    def test_show_command_with_type_filter(self, mock_registry_path, sample_project_content, tmp_path):
        """Test show command with entity type filter"""
        mock_file_path = str(tmp_path / "project.yml")

        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                mock_instance = MagicMock()
                mock_instance.get_entity.return_value = {
                    "success": True,
                    "entity": sample_project_content,
                    "file_path": mock_file_path,
                    "identifier": "P-001",
                }
                MockShowOperation.return_value = mock_instance

                with patch.object(ShowCommand, "display_file", return_value=0):
                    result = main(["show", "P-001", "--type", "project"])

                    assert result == 0
                    # Verify get_entity was called with correct type enum
                    mock_instance.get_entity.assert_called_once()
                    call_kwargs = mock_instance.get_entity.call_args[1]
                    assert call_kwargs["entity_type"] == EntityType.PROJECT

    def test_show_command_with_format_options(self, mock_registry_path, sample_project_content, tmp_path):
        """Test show command with different format options"""
        mock_file_path = str(tmp_path / "project.yml")

        formats = [
            ("yaml", OutputFormat.YAML),
            ("json", OutputFormat.JSON),
            ("pretty", OutputFormat.PRETTY),
        ]

        for fmt_str, fmt_enum in formats:
            with patch.object(
                ShowCommand, "_get_registry_path", return_value=mock_registry_path
            ):
                with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                    mock_instance = MagicMock()
                    mock_instance.get_entity.return_value = {
                        "success": True,
                        "entity": sample_project_content,
                        "file_path": mock_file_path,
                        "identifier": "P-001",
                    }
                    MockShowOperation.return_value = mock_instance

                    with patch.object(
                        ShowCommand, "display_file", return_value=0
                    ) as mock_display:
                        result = main(["show", "P-001", "--format", fmt_str])

                        assert result == 0
                        # Verify display_file was called with the correct format enum
                        call_args = mock_display.call_args[0]
                        assert call_args[2] == fmt_enum

    def test_show_command_with_raw_flag(self, mock_registry_path, sample_project_content, tmp_path):
        """Test show command with raw flag"""
        raw_content = yaml.dump(sample_project_content)
        mock_file_path = str(tmp_path / "project.yml")

        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                mock_instance = MagicMock()
                mock_instance.get_entity.return_value = {
                    "success": True,
                    "entity": sample_project_content,
                    "file_path": mock_file_path,
                    "identifier": "P-001",
                    "raw_content": raw_content,
                }
                MockShowOperation.return_value = mock_instance

                with patch("builtins.print") as mock_print:
                    result = main(["show", "P-001", "--raw"])

                    assert result == 0
                    # Verify get_entity was called with include_raw=True
                    call_kwargs = mock_instance.get_entity.call_args[1]
                    assert call_kwargs["include_raw"] is True
                    # Verify raw content was printed
                    mock_print.assert_called_with(raw_content)

    def test_show_command_no_registry(self):
        """Test show command when no registry is found"""
        with patch.object(ShowCommand, "_get_registry_path", return_value=None):
            with patch("builtins.print") as mock_print:
                result = main(["show", "P-001"])

                assert result == 1
                # Check that error message was printed
                assert any(
                    "No registry found" in str(call[0][0])
                    for call in mock_print.call_args_list
                )

    def test_show_command_security_error(self, mock_registry_path):
        """Test that security errors are handled properly"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                MockShowOperation.side_effect = PathSecurityError("Path traversal detected")

                with patch("builtins.print") as mock_print:
                    # Use a path that looks suspicious but won't actually traverse
                    result = main(["show", "suspicious-id"])

                    assert result == 1
                    assert any(
                        "Security error" in str(call[0][0])
                        for call in mock_print.call_args_list
                    )

    def test_show_command_invalid_type(self, mock_registry_path):
        """Test show command with invalid entity type"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("builtins.print"):
                result = main(["show", "P-001", "--type", "invalid_type"])

                # argparse should reject invalid type
                assert result != 0

    def test_show_command_invalid_format(self, mock_registry_path):
        """Test show command with invalid format option"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("builtins.print"):
                result = main(["show", "P-001", "--format", "invalid_format"])

                # argparse should reject invalid format
                assert result != 0


class TestShowCommandUsesShowOperation:
    """Tests to verify ShowCommand uses the shared ShowOperation"""

    def test_execute_creates_show_operation(self, mock_registry_path, sample_project_content, tmp_path):
        """Test that execute() creates ShowOperation with correct registry path"""
        mock_file_path = str(tmp_path / "project.yml")

        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                mock_instance = MagicMock()
                mock_instance.get_entity.return_value = {
                    "success": True,
                    "entity": sample_project_content,
                    "file_path": mock_file_path,
                    "identifier": "P-001",
                }
                MockShowOperation.return_value = mock_instance

                with patch.object(ShowCommand, "display_file", return_value=0):
                    main(["show", "P-001"])

                MockShowOperation.assert_called_once_with(mock_registry_path)

    def test_execute_passes_all_parameters_to_operation(
        self, mock_registry_path, sample_project_content, tmp_path
    ):
        """Test that execute() passes all parameters to ShowOperation.get_entity()"""
        mock_file_path = str(tmp_path / "project.yml")

        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                mock_instance = MagicMock()
                mock_instance.get_entity.return_value = {
                    "success": True,
                    "entity": sample_project_content,
                    "file_path": mock_file_path,
                    "identifier": "P-001",
                }
                MockShowOperation.return_value = mock_instance

                with patch.object(ShowCommand, "display_file", return_value=0):
                    main(["show", "P-001", "--type", "project", "--raw"])

                # Verify get_entity was called with correct parameters
                mock_instance.get_entity.assert_called_once()
                call_kwargs = mock_instance.get_entity.call_args[1]
                assert call_kwargs["identifier"] == "P-001"
                assert call_kwargs["entity_type"] == EntityType.PROJECT
                assert call_kwargs["include_raw"] is True

    def test_execute_handles_operation_error(self, mock_registry_path):
        """Test that execute() handles ShowOperation errors gracefully"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=mock_registry_path
        ):
            with patch("hxc.commands.show.ShowOperation") as MockShowOperation:
                mock_instance = MagicMock()
                mock_instance.get_entity.return_value = {
                    "success": False,
                    "error": "Test error",
                    "entity": None,
                    "file_path": None,
                    "identifier": "P-001",
                }
                MockShowOperation.return_value = mock_instance

                with patch("builtins.print") as mock_print:
                    result = main(["show", "P-001"])

                assert result == 1
                assert any(
                    "Test error" in str(call[0][0])
                    for call in mock_print.call_args_list
                )


class TestShowCommandGetRegistryPath:
    """Tests for ShowCommand._get_registry_path() method"""

    def test_get_registry_path_from_argument(self, tmp_path):
        """Test that explicit --registry argument is used"""
        specified_path = str(tmp_path / "explicit_registry")
        result = ShowCommand._get_registry_path(specified_path)
        assert result == specified_path

    def test_get_registry_path_from_config(self, tmp_path):
        """Test that registry path from config is used when not specified"""
        config_path = str(tmp_path / "config_registry")

        with patch(
            "hxc.commands.registry.RegistryCommand.get_registry_path",
            return_value=config_path,
        ):
            result = ShowCommand._get_registry_path(None)
            assert result == config_path

    def test_get_registry_path_from_project_root(self, tmp_path):
        """Test that project root is used when config has no path"""
        project_root = str(tmp_path / "project_root")

        with patch(
            "hxc.commands.registry.RegistryCommand.get_registry_path",
            return_value=None,
        ):
            with patch(
                "hxc.commands.show.get_project_root", return_value=project_root
            ):
                result = ShowCommand._get_registry_path(None)
                assert result == project_root

    def test_get_registry_path_none_when_not_found(self):
        """Test that None is returned when no registry can be found"""
        with patch(
            "hxc.commands.registry.RegistryCommand.get_registry_path",
            return_value=None,
        ):
            with patch("hxc.commands.show.get_project_root", return_value=None):
                result = ShowCommand._get_registry_path(None)
                assert result is None


class TestShowCommandIntegration:
    """Integration tests for ShowCommand with real registry"""

    def test_show_entity_by_id(self, temp_registry):
        """Test showing an entity by its human-readable ID"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=temp_registry
        ):
            with patch("builtins.print") as mock_print:
                result = main(["show", "P-001", "--format", "yaml"])

                assert result == 0
                # Verify entity content was printed
                printed = " ".join(
                    str(call[0][0]) if call[0] else ""
                    for call in mock_print.call_args_list
                )
                assert "Test Project One" in printed

    def test_show_entity_by_uid(self, temp_registry):
        """Test showing an entity by its UID"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=temp_registry
        ):
            with patch("builtins.print") as mock_print:
                result = main(["show", "proj-test-001", "--format", "yaml"])

                assert result == 0
                # Verify entity content was printed
                printed = " ".join(
                    str(call[0][0]) if call[0] else ""
                    for call in mock_print.call_args_list
                )
                assert "Test Project One" in printed

    def test_show_entity_not_found(self, temp_registry):
        """Test showing an entity that doesn't exist"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=temp_registry
        ):
            with patch("builtins.print") as mock_print:
                result = main(["show", "NONEXISTENT"])

                assert result == 1
                # Verify error message was printed
                printed = " ".join(
                    str(call[0][0]) if call[0] else ""
                    for call in mock_print.call_args_list
                )
                assert "not found" in printed.lower()

    def test_show_entity_wrong_type(self, temp_registry):
        """Test showing an entity with wrong type filter"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=temp_registry
        ):
            with patch("builtins.print") as mock_print:
                # P-001 is a project, not a program
                result = main(["show", "P-001", "--type", "program"])

                assert result == 1
                # Verify error message was printed
                printed = " ".join(
                    str(call[0][0]) if call[0] else ""
                    for call in mock_print.call_args_list
                )
                assert "not found" in printed.lower()

    def test_show_entity_raw_output(self, temp_registry):
        """Test showing entity in raw format"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=temp_registry
        ):
            with patch("builtins.print") as mock_print:
                result = main(["show", "P-001", "--raw"])

                assert result == 0
                # Verify raw YAML content was printed
                printed = str(mock_print.call_args[0][0])
                assert "type: project" in printed
                assert "uid: proj-test-001" in printed

    def test_show_entity_json_format(self, temp_registry):
        """Test showing entity in JSON format"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=temp_registry
        ):
            with patch("builtins.print") as mock_print:
                result = main(["show", "P-001", "--format", "json"])

                assert result == 0
                # Verify JSON content was printed
                printed = str(mock_print.call_args[0][0])
                assert '"type": "project"' in printed

    def test_show_entity_pretty_format(self, temp_registry):
        """Test showing entity in pretty format"""
        with patch.object(
            ShowCommand, "_get_registry_path", return_value=temp_registry
        ):
            with patch("builtins.print") as mock_print:
                result = main(["show", "P-001", "--format", "pretty"])

                assert result == 0
                # Verify pretty format elements
                printed = " ".join(
                    str(call[0][0]) if call[0] else ""
                    for call in mock_print.call_args_list
                )
                assert "Test Project One" in printed
                assert "PROJECT" in printed  # Type shown in header
                assert "P-001" in printed


class TestShowCommandBehavioralParityWithMCP:
    """Tests to verify ShowCommand produces same results as MCP get_entity_tool"""

    def test_result_structure_consistency(self, temp_registry):
        """Test that ShowOperation produces consistent results for both CLI and MCP"""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("P-001")

        # Verify result has all required keys
        assert "success" in result
        assert "entity" in result
        assert "file_path" in result
        assert "identifier" in result

    def test_entity_lookup_by_id_matches(self, temp_registry):
        """Test that ID lookup produces same entity in both interfaces"""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("P-001")

        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"
        assert result["entity"]["uid"] == "proj-test-001"

    def test_entity_lookup_by_uid_matches(self, temp_registry):
        """Test that UID lookup produces same entity in both interfaces"""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("proj-test-001")

        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"
        assert result["entity"]["uid"] == "proj-test-001"

    def test_raw_content_available(self, temp_registry):
        """Test that raw content is available via include_raw parameter"""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("P-001", include_raw=True)

        assert result["success"] is True
        assert "raw_content" in result
        assert isinstance(result["raw_content"], str)
        assert "type: project" in result["raw_content"]

    def test_entity_type_filter_works(self, temp_registry):
        """Test that entity type filter works correctly"""
        operation = ShowOperation(temp_registry)

        # Should find when type matches
        result = operation.get_entity("P-001", entity_type=EntityType.PROJECT)
        assert result["success"] is True

        # Should not find when type doesn't match
        result = operation.get_entity("P-001", entity_type=EntityType.PROGRAM)
        assert result["success"] is False

    def test_not_found_error_structure(self, temp_registry):
        """Test that not found errors have consistent structure"""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("NONEXISTENT")

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
        assert result["entity"] is None
        assert result["file_path"] is None

    def test_file_path_is_valid_path(self, temp_registry):
        """Test that file_path in result is a valid path on the current OS"""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("P-001")

        assert result["success"] is True
        # Verify the file path exists and is valid for the current OS
        file_path = Path(result["file_path"])
        assert file_path.exists()
        assert file_path.is_file()
        assert file_path.name == "proj-proj-test-001.yml"