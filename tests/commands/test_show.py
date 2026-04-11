"""
Tests for the show command
"""

import os
import sys
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from hxc.cli import main
from hxc.commands.show import ShowCommand
from hxc.core.enums import EntityType, OutputFormat
from hxc.utils.path_security import resolve_safe_path


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
        "start_date": "2024-01-01",
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
        if action.dest == "format":
            format_arg = action
            break
    assert format_arg is not None
    assert "pretty" in format_arg.choices
    assert format_arg.default == "pretty"


def test_find_file_by_id(mock_registry_path, sample_project_content):
    """Test finding a file by ID"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path(mock_registry_path) / "projects" / "P-001.yml"

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob") as mock_rglob:
            mock_rglob.return_value = [file_path]

            with patch("builtins.open", mock_open(read_data=yml_content)):
                with patch(
                    "hxc.commands.show.resolve_safe_path", return_value=file_path
                ):
                    result = ShowCommand.find_file(
                        mock_registry_path, "P-001", EntityType.PROJECT
                    )

                    # Compare resolved paths
                    assert result is not None
                    assert result.name == file_path.name
                    assert "projects" in str(result)


def test_find_file_by_uid(mock_registry_path, sample_project_content):
    """Test finding a file by UID"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path(mock_registry_path) / "projects" / "P-001.yml"

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob") as mock_rglob:
            mock_rglob.return_value = [file_path]

            with patch("builtins.open", mock_open(read_data=yml_content)):
                with patch(
                    "hxc.commands.show.resolve_safe_path", return_value=file_path
                ):
                    result = ShowCommand.find_file(
                        mock_registry_path, "proj-123", EntityType.PROJECT
                    )

                    # Compare resolved paths
                    assert result is not None
                    assert result.name == file_path.name
                    assert "projects" in str(result)


def test_find_file_multiple_types(mock_registry_path, sample_project_content):
    """Test finding a file by searching all types"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path(mock_registry_path) / "projects" / "P-001.yml"

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob") as mock_rglob:
            mock_rglob.return_value = [file_path]

            with patch("builtins.open", mock_open(read_data=yml_content)):
                with patch(
                    "hxc.commands.show.resolve_safe_path", return_value=file_path
                ):
                    result = ShowCommand.find_file(mock_registry_path, "P-001", None)

                    # Compare resolved paths
                    assert result is not None
                    assert result.name == file_path.name
                    assert "projects" in str(result)


def test_display_file_yaml(sample_project_content):
    """Test displaying file content in YAML format"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")

    with patch("builtins.open", mock_open(read_data=yml_content)):
        with patch("builtins.print") as mock_print:
            result = ShowCommand.display_file(file_path, OutputFormat.YAML, False)

            assert result == 0
            # Check that print was called (with yaml content)
            assert mock_print.called


def test_display_file_json(sample_project_content):
    """Test displaying file content in JSON format"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")

    with patch("builtins.open", mock_open(read_data=yml_content)):
        with patch("builtins.print") as mock_print:
            result = ShowCommand.display_file(file_path, OutputFormat.JSON, False)

            assert result == 0
            # Check that print was called (with json content)
            assert mock_print.called


def test_display_file_pretty(sample_project_content):
    """Test displaying file content in pretty format"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")

    with patch("builtins.open", mock_open(read_data=yml_content)):
        with patch(
            "hxc.commands.show.ShowCommand.display_pretty"
        ) as mock_display_pretty:
            result = ShowCommand.display_file(file_path, OutputFormat.PRETTY, False)

            assert result == 0
            # Check that the pretty display method was called
            mock_display_pretty.assert_called_once()


def test_display_file_raw(sample_project_content):
    """Test displaying raw file content"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")

    with patch("builtins.open", mock_open(read_data=yml_content)):
        with patch("builtins.print") as mock_print:
            result = ShowCommand.display_file(file_path, OutputFormat.YAML, True)

            assert result == 0
            # Check that print was called with raw content
            mock_print.assert_called_once_with(yml_content)


def test_show_command_main(mock_registry_path, sample_project_content):
    """Test the show command via main CLI entry point"""
    # Create test data
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")

    with patch(
        "hxc.commands.registry.RegistryCommand.get_registry_path",
        return_value=mock_registry_path,
    ):
        with patch("hxc.commands.show.ShowCommand.find_file", return_value=file_path):
            with patch(
                "hxc.commands.show.ShowCommand.display_file", return_value=0
            ) as mock_display:
                result = main(["show", "P-001"])

                assert result == 0
                mock_display.assert_called_once()
                # Verify default format is OutputFormat.PRETTY enum
                assert mock_display.call_args[0][1] == OutputFormat.PRETTY


def test_show_command_file_not_found(mock_registry_path):
    """Test behavior when file is not found"""
    with patch(
        "hxc.commands.registry.RegistryCommand.get_registry_path",
        return_value=mock_registry_path,
    ):
        with patch("hxc.commands.show.ShowCommand.find_file", return_value=None):
            with patch("builtins.print") as mock_print:
                result = main(["show", "nonexistent-id"])

                assert result == 1
                # Check that an error message was printed
                assert mock_print.call_args_list[0][0][0].startswith("❌")


def test_display_pretty(sample_project_content):
    """Test the pretty display function"""
    file_path = Path("/mock/path/project.yml")

    with patch("builtins.print") as mock_print:
        ShowCommand.display_pretty(sample_project_content, file_path)

        # Verify that print was called multiple times to format the output
        assert mock_print.call_count > 5

        # Check for key elements in the output
        any_title_printed = any(
            "Example Project" in str(args) for args, _ in mock_print.call_args_list
        )
        any_id_printed = any(
            "P-001" in str(args) for args, _ in mock_print.call_args_list
        )
        any_status_printed = any(
            "Status" in str(args) for args, _ in mock_print.call_args_list
        )

        assert any_title_printed
        assert any_id_printed
        assert any_status_printed


def test_find_file_not_found(mock_registry_path):
    """Test finding a file that doesn't exist"""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob") as mock_rglob:
            mock_rglob.return_value = []

            result = ShowCommand.find_file(
                mock_registry_path, "nonexistent", EntityType.PROJECT
            )

            assert result is None


def test_find_file_security_error(mock_registry_path, sample_project_content):
    """Test that security errors are handled properly"""
    from hxc.utils.path_security import PathSecurityError

    yml_content = yaml.dump(sample_project_content)
    file_path = Path(mock_registry_path) / "projects" / "P-001.yml"

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob") as mock_rglob:
            mock_rglob.return_value = [file_path]

            with patch("builtins.open", mock_open(read_data=yml_content)):
                with patch(
                    "hxc.commands.show.resolve_safe_path",
                    side_effect=PathSecurityError("Path traversal detected"),
                ):
                    result = ShowCommand.find_file(
                        mock_registry_path, "P-001", EntityType.PROJECT
                    )

                    # Should return None when security error occurs
                    assert result is None


def test_show_command_with_type_filter(mock_registry_path, sample_project_content):
    """Test show command with entity type filter"""
    yml_content = yaml.dump(sample_project_content)
    file_path = Path("/mock/path/project.yml")

    with patch(
        "hxc.commands.registry.RegistryCommand.get_registry_path",
        return_value=mock_registry_path,
    ):
        with patch(
            "hxc.commands.show.ShowCommand.find_file", return_value=file_path
        ) as mock_find:
            with patch("hxc.commands.show.ShowCommand.display_file", return_value=0):
                result = main(["show", "P-001", "--type", "project"])

                assert result == 0
                # Verify find_file was called with the correct type enum
                mock_find.assert_called_once()
                assert mock_find.call_args[0][2] == EntityType.PROJECT


def test_show_command_with_format_options(mock_registry_path, sample_project_content):
    """Test show command with different format options"""
    file_path = Path("/mock/path/project.yml")

    formats = [
        ("yaml", OutputFormat.YAML),
        ("json", OutputFormat.JSON),
        ("pretty", OutputFormat.PRETTY),
    ]

    for fmt_str, fmt_enum in formats:
        with patch(
            "hxc.commands.registry.RegistryCommand.get_registry_path",
            return_value=mock_registry_path,
        ):
            with patch(
                "hxc.commands.show.ShowCommand.find_file", return_value=file_path
            ):
                with patch(
                    "hxc.commands.show.ShowCommand.display_file", return_value=0
                ) as mock_display:
                    result = main(["show", "P-001", "--format", fmt_str])

                    assert result == 0
                    # Verify display_file was called with the correct format enum
                    assert mock_display.call_args[0][1] == fmt_enum


def test_show_command_with_raw_flag(mock_registry_path, sample_project_content):
    """Test show command with raw flag"""
    file_path = Path("/mock/path/project.yml")

    with patch(
        "hxc.commands.registry.RegistryCommand.get_registry_path",
        return_value=mock_registry_path,
    ):
        with patch("hxc.commands.show.ShowCommand.find_file", return_value=file_path):
            with patch(
                "hxc.commands.show.ShowCommand.display_file", return_value=0
            ) as mock_display:
                result = main(["show", "P-001", "--raw"])

                assert result == 0
                # Verify display_file was called with raw=True
                assert mock_display.call_args[0][2] is True


def test_show_command_no_registry(mock_registry_path):
    """Test show command when no registry is found"""
    with patch(
        "hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None
    ):
        with patch(
            "hxc.commands.show.ShowCommand._get_registry_path", return_value=None
        ):
            with patch("builtins.print") as mock_print:
                result = main(["show", "P-001"])

                assert result == 1
                # Check that error message was printed
                assert any(
                    "No registry found" in call[0][0]
                    for call in mock_print.call_args_list
                )


def test_display_file_error_handling(sample_project_content):
    """Test error handling in display_file"""
    file_path = Path("/mock/path/project.yml")

    with patch("builtins.open", side_effect=Exception("Test error")):
        with patch("builtins.print") as mock_print:
            result = ShowCommand.display_file(file_path, OutputFormat.YAML, False)

            assert result == 1
            # Check that error message was printed
            assert any(
                "Error reading file" in call[0][0] for call in mock_print.call_args_list
            )


def test_display_pretty_with_all_fields(sample_project_content):
    """Test pretty display with all possible fields"""
    file_path = Path("/mock/path/project.yml")

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

    with patch("builtins.print") as mock_print:
        ShowCommand.display_pretty(full_content, file_path)

        # Verify that all sections are printed
        printed_text = " ".join(str(args[0]) for args, _ in mock_print.call_args_list)

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
