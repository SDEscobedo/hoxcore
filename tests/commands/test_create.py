"""
Tests for the create command
"""

import os
import pathlib
import shutil
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.cli import main
from hxc.commands.create import CreateCommand, title_to_id
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.create import (
    CreateOperation,
    CreateOperationError,
    DuplicateIdError,
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

    yield registry_path

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def git_registry(tmp_path):
    """Create a temporary registry that is also a git repository."""
    registry_path = tmp_path / "git_registry"
    registry_path.mkdir(parents=True)

    # Create marker files and directories
    (registry_path / ".hxc").mkdir()
    (registry_path / "config.yml").write_text("# Test config")

    # Create entity directories
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

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

    yield registry_path

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def registry_with_projects(temp_registry):
    """Create a registry with existing project entities for ID uniqueness tests"""
    # Create project with id "P-001"
    project1 = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Existing Project One",
        "status": "active",
    }
    with open(temp_registry / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project1, f)

    # Create project with id "P-002"
    project2 = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Existing Project Two",
        "status": "active",
    }
    with open(temp_registry / "projects" / "proj-proj0002.yml", "w") as f:
        yaml.dump(project2, f)

    return temp_registry


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


def test_create_command_parser_has_no_commit_flag():
    """Test that create command parser has --no-commit flag"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = CreateCommand.register_subparser(subparsers)

    # Verify parser has the --no-commit argument
    actions = {action.dest for action in cmd_parser._actions}
    assert "no_commit" in actions


def test_create_command_parser_entity_type_choices():
    """Test that entity type choices match enum values"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = CreateCommand.register_subparser(subparsers)

    # Find the 'type' argument
    type_action = None
    for action in cmd_parser._actions:
        if action.dest == "type":
            type_action = action
            break

    assert type_action is not None
    assert type_action.choices == EntityType.values()


def test_create_command_parser_status_choices():
    """Test that status choices match enum values"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = CreateCommand.register_subparser(subparsers)

    # Find the 'status' argument
    status_action = None
    for action in cmd_parser._actions:
        if action.dest == "status":
            status_action = action
            break

    assert status_action is not None
    assert status_action.choices == EntityStatus.values()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_project_basic(mock_get_registry_path, temp_registry):
    """Test creating a basic project"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Fix uuid for predictable output
    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Test Project", "--no-commit"])

            # Check result
            assert result == 0

            # Check that file was created
            project_file = temp_registry / "projects" / "proj-12345678.yml"
            assert project_file.exists(), f"Project file {project_file} not created"

            # Check file contents
            with open(project_file, "r") as f:
                project_data = yaml.safe_load(f)

            assert project_data["type"] == EntityType.PROJECT.value
            assert project_data["title"] == "Test Project"
            assert project_data["uid"] == "12345678"
            assert project_data["status"] == EntityStatus.ACTIVE.value
            assert "start_date" in project_data

            # Check success message
            assert any(
                "Created project" in call[0][0] for call in mock_print.call_args_list
            )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_project_full(mock_get_registry_path, temp_registry):
    """Test creating a project with all options"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Fix uuid for predictable output
    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        result = main(
            [
                "create",
                "project",
                "Full Project",
                "--id",
                "P-001",
                "--description",
                "This is a full project",
                "--status",
                "on-hold",
                "--start-date",
                "2024-01-01",
                "--due-date",
                "2024-12-31",
                "--category",
                "software.dev/cli-tool",
                "--tags",
                "cli",
                "test",
                "yaml",
                "--parent",
                "P-000",
                "--template",
                "software.dev/cli-tool.default",
                "--no-commit",
            ]
        )

        # Check result
        assert result == 0

        # Check that file was created
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()

        # Check file contents
        with open(project_file, "r") as f:
            project_data = yaml.safe_load(f)

        assert project_data["type"] == EntityType.PROJECT.value
        assert project_data["title"] == "Full Project"
        assert project_data["id"] == "P-001"
        assert project_data["description"] == "This is a full project"
        assert project_data["status"] == EntityStatus.ON_HOLD.value
        assert project_data["start_date"] == "2024-01-01"
        assert project_data["due_date"] == "2024-12-31"
        assert project_data["category"] == "software.dev/cli-tool"
        assert project_data["tags"] == ["cli", "test", "yaml"]
        assert project_data["parent"] == "P-000"
        assert project_data["template"] == "software.dev/cli-tool.default"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_custom_id_overrides_auto_generation(
    mock_get_registry_path, temp_registry
):
    """Custom `--id` should override the auto-generated title-based id."""
    mock_get_registry_path.return_value = str(temp_registry)

    title = "My Project"
    auto_id = title_to_id(title, "project")
    custom_id = "P-CUSTOM-123"

    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        result = main(["create", "project", title, "--id", custom_id, "--no-commit"])
        assert result == 0

    project_file = temp_registry / "projects" / "proj-12345678.yml"
    assert project_file.exists()

    with open(project_file, "r") as f:
        project_data = yaml.safe_load(f)

    assert project_data["uid"] == "12345678"
    assert project_data["id"] == custom_id
    assert project_data["id"] != auto_id


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_custom_id_used_exactly_as_provided(
    mock_get_registry_path, temp_registry
):
    """Custom `--id` should be written to YAML exactly as provided."""
    mock_get_registry_path.return_value = str(temp_registry)

    title = "Test Action"
    custom_id = "my.Custom-ID_123"

    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        result = main(["create", "action", title, "--id", custom_id, "--no-commit"])
        assert result == 0

    action_file = temp_registry / "actions" / "act-12345678.yml"
    assert action_file.exists()

    with open(action_file, "r") as f:
        action_data = yaml.safe_load(f)

    assert action_data["uid"] == "12345678"
    assert action_data["id"] == custom_id


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_all_entity_types_include_auto_generated_ids_and_uid(
    mock_get_registry_path, temp_registry
):
    """Each entity type should write `uid` and auto-generated `id` to YAML."""
    mock_get_registry_path.return_value = str(temp_registry)

    for entity_type in EntityType:
        folder_name = entity_type.get_folder_name()
        file_prefix = entity_type.get_file_prefix()
        title = f"Test {entity_type.value.title()}"

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", entity_type.value, title, "--no-commit"])
            assert result == 0

        entity_file = temp_registry / folder_name / f"{file_prefix}-12345678.yml"
        assert entity_file.exists()

        with open(entity_file, "r") as f:
            entity_data = yaml.safe_load(f)

        assert entity_data["uid"] == "12345678"
        assert "id" in entity_data
        assert entity_data["id"] == title_to_id(title, entity_type.value)
        assert entity_data["title"] == title
        assert entity_data["type"] == entity_type.value

        # Clean up to keep the registry empty for the next entity_type iteration.
        entity_file.unlink()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_program(mock_get_registry_path, temp_registry):
    """Test creating a program"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Fix uuid for predictable output
    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        result = main(["create", "program", "Test Program", "--no-commit"])

        # Check result
        assert result == 0

        # Check that file was created
        program_file = temp_registry / "programs" / "prog-12345678.yml"
        assert program_file.exists()

        # Check file contents
        with open(program_file, "r") as f:
            program_data = yaml.safe_load(f)

        assert program_data["type"] == EntityType.PROGRAM.value
        assert program_data["title"] == "Test Program"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_action(mock_get_registry_path, temp_registry):
    """Test creating an action"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Fix uuid for predictable output
    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        result = main(["create", "action", "Test Action", "--no-commit"])

        # Check result
        assert result == 0

        # Check that file was created
        action_file = temp_registry / "actions" / "act-12345678.yml"
        assert action_file.exists()

        # Check file contents
        with open(action_file, "r") as f:
            action_data = yaml.safe_load(f)

        assert action_data["type"] == EntityType.ACTION.value
        assert action_data["title"] == "Test Action"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_mission(mock_get_registry_path, temp_registry):
    """Test creating a mission"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Fix uuid for predictable output
    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        result = main(["create", "mission", "Test Mission", "--no-commit"])

        # Check result
        assert result == 0

        # Check that file was created
        mission_file = temp_registry / "missions" / "miss-12345678.yml"
        assert mission_file.exists()

        # Check file contents
        with open(mission_file, "r") as f:
            mission_data = yaml.safe_load(f)

        assert mission_data["type"] == EntityType.MISSION.value
        assert mission_data["title"] == "Test Mission"


def test_create_invalid_entity_type():
    """Test that invalid entity type is rejected by CLI parser"""
    with patch("builtins.print") as mock_print:
        with pytest.raises(SystemExit) as exc_info:
            result = main(["create", "invalid_type", "Test Entity"])

        # argparse exits with code 2 for invalid choice
        assert exc_info.value.code == 2


def test_create_invalid_status():
    """Test that invalid status is rejected by CLI parser"""
    with patch(
        "hxc.commands.registry.RegistryCommand.get_registry_path",
        return_value="/tmp/test",
    ):
        with patch("builtins.print") as mock_print:
            with pytest.raises(SystemExit) as exc_info:
                result = main(
                    ["create", "project", "Test Project", "--status", "invalid_status"]
                )

            # argparse exits with code 2 for invalid choice
            assert exc_info.value.code == 2


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_all_valid_entity_types(mock_get_registry_path, temp_registry):
    """Test creating all valid entity types from enum"""
    mock_get_registry_path.return_value = str(temp_registry)

    for entity_type in EntityType:
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(
                [
                    "create",
                    entity_type.value,
                    f"Test {entity_type.value.title()}",
                    "--no-commit",
                ]
            )

            assert result == 0

            folder_name = entity_type.get_folder_name()
            file_prefix = entity_type.get_file_prefix()
            entity_file = temp_registry / folder_name / f"{file_prefix}-12345678.yml"

            assert entity_file.exists()

            with open(entity_file, "r") as f:
                entity_data = yaml.safe_load(f)

            assert entity_data["type"] == entity_type.value

            # Clean up for next iteration
            entity_file.unlink()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_all_valid_statuses(mock_get_registry_path, temp_registry):
    """Test creating entities with all valid statuses from enum"""
    mock_get_registry_path.return_value = str(temp_registry)

    for status in EntityStatus:
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: f"status{status.value[:4]}1234-5678-1234-567812345678"
            ),
        ):
            result = main(
                [
                    "create",
                    "project",
                    f"Test {status.value}",
                    "--status",
                    status.value,
                    "--no-commit",
                ]
            )

            assert result == 0

            # Find the created file
            project_files = list((temp_registry / "projects").glob("proj-*.yml"))
            assert len(project_files) > 0

            # Get the most recently created file
            latest_file = max(project_files, key=lambda p: p.stat().st_mtime)

            with open(latest_file, "r") as f:
                project_data = yaml.safe_load(f)

            assert project_data["status"] == status.value


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
            assert any(
                "Error creating project" in call[0][0]
                for call in mock_print.call_args_list
            )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_path_traversal_protection(mock_get_registry_path, temp_registry):
    """Test that path traversal attempts are blocked during entity creation"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Mock get_safe_entity_path to raise PathSecurityError (in core.operations.create)
    with patch(
        "hxc.core.operations.create.get_safe_entity_path",
        side_effect=PathSecurityError("Path traversal detected"),
    ):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Malicious Project"])

            # Check result indicates failure
            assert result == 1

            # Check that security error message is displayed
            assert any(
                "Security error" in call[0][0] for call in mock_print.call_args_list
            )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_invalid_entity_type_protection(mock_get_registry_path, temp_registry):
    """Test that invalid entity types are rejected"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Mock get_safe_entity_path to raise ValueError for invalid type (in core.operations.create)
    with patch(
        "hxc.core.operations.create.get_safe_entity_path",
        side_effect=ValueError("Invalid entity type"),
    ):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Test Project"])

            # Check result indicates failure
            assert result == 1

            # Check that error message is displayed
            assert any(
                "Invalid entity type" in call[0][0]
                for call in mock_print.call_args_list
            )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_entity_stays_within_registry(mock_get_registry_path, temp_registry):
    """Test that created entities are always within the registry boundaries"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)

    # Fix uuid for predictable output
    with patch(
        "hxc.core.operations.create.uuid.uuid4",
        return_value=MagicMock(
            __str__=lambda x: "12345678-1234-5678-1234-567812345678"
        ),
    ):
        result = main(["create", "project", "Test Project", "--no-commit"])

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

    for entity_type in EntityType:
        # Fix uuid for predictable output
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(
                [
                    "create",
                    entity_type.value,
                    f"Test {entity_type.value.title()}",
                    "--no-commit",
                ]
            )

            # Check result
            assert result == 0

            # Check that file was created in correct location
            folder_name = entity_type.get_folder_name()
            file_prefix = entity_type.get_file_prefix()
            entity_file = temp_registry / folder_name / f"{file_prefix}-12345678.yml"
            assert entity_file.exists()

            # Verify the file is within the registry root
            assert str(temp_registry) in str(entity_file.resolve())

            # Verify the file is in the correct subdirectory
            assert entity_file.parent == temp_registry / folder_name

            # Clean up for next iteration
            entity_file.unlink()


def test_entity_type_enum_usage():
    """Test that EntityType enum is used correctly in create command"""
    # Verify that EntityType enum values match expected entity types
    assert EntityType.PROGRAM.value == "program"
    assert EntityType.PROJECT.value == "project"
    assert EntityType.MISSION.value == "mission"
    assert EntityType.ACTION.value == "action"

    # Verify enum provides correct folder names
    assert EntityType.PROGRAM.get_folder_name() == "programs"
    assert EntityType.PROJECT.get_folder_name() == "projects"
    assert EntityType.MISSION.get_folder_name() == "missions"
    assert EntityType.ACTION.get_folder_name() == "actions"

    # Verify enum provides correct file prefixes
    assert EntityType.PROGRAM.get_file_prefix() == "prog"
    assert EntityType.PROJECT.get_file_prefix() == "proj"
    assert EntityType.MISSION.get_file_prefix() == "miss"
    assert EntityType.ACTION.get_file_prefix() == "act"


def test_entity_status_enum_usage():
    """Test that EntityStatus enum is used correctly in create command"""
    # Verify that EntityStatus enum values match expected statuses
    assert EntityStatus.ACTIVE.value == "active"
    assert EntityStatus.COMPLETED.value == "completed"
    assert EntityStatus.ON_HOLD.value == "on-hold"
    assert EntityStatus.CANCELLED.value == "cancelled"
    assert EntityStatus.PLANNED.value == "planned"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_validates_entity_type_early(mock_get_registry_path, temp_registry):
    """Test that entity type validation happens before file operations"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Mock EntityType.from_string to raise ValueError
    with patch(
        "hxc.commands.create.EntityType.from_string",
        side_effect=ValueError("Invalid entity type"),
    ):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Test Project"])

            # Should fail with validation error
            assert result == 1

            # Should show error message
            assert any(
                "Invalid argument" in call[0][0] for call in mock_print.call_args_list
            )

            # No files should be created
            project_files = list((temp_registry / "projects").glob("*.yml"))
            assert len(project_files) == 0


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_create_validates_status_early(mock_get_registry_path, temp_registry):
    """Test that status validation happens before file operations"""
    mock_get_registry_path.return_value = str(temp_registry)

    # Mock EntityStatus.from_string to raise ValueError
    with patch(
        "hxc.commands.create.EntityStatus.from_string",
        side_effect=ValueError("Invalid status"),
    ):
        with patch("builtins.print") as mock_print:
            result = main(["create", "project", "Test Project", "--status", "active"])

            # Should fail with validation error
            assert result == 1

            # Should show error message
            assert any(
                "Invalid argument" in call[0][0] for call in mock_print.call_args_list
            )

            # No files should be created
            project_files = list((temp_registry / "projects").glob("*.yml"))
            assert len(project_files) == 0


def test_create_title_to_id_basic_spaces():
    assert title_to_id("my project", "project") == "my_project"


def test_create_title_to_id_multiple_words():
    assert title_to_id("my awesome project", "project") == "my_awesome_project"


def test_create_title_to_id_very_long_title_exceeds_max_length():
    long_title = "a" * 300
    out = title_to_id(long_title, "project")
    assert len(out) == 255
    assert out == "a" * 255


def test_create_title_to_id_special_characters():
    assert title_to_id("my-project!", "project") == "my_project"


def test_create_title_to_id_non_ascii_characters():
    assert title_to_id("cäfé pròjěčt", "project") == "cafe_project"


def test_create_title_to_id_empty_title():
    assert title_to_id("", "project") == "project"


def test_create_title_to_id_whitespace_only_title():
    assert title_to_id("   ", "project") == "project"


def test_create_title_to_id_leading_trailing_whitespace():
    assert title_to_id("  my project  ", "project") == "my_project"


def test_create_title_to_id_consecutive_spaces_collapse():
    assert title_to_id("my    project", "project") == "my_project"


def test_create_title_to_id_mixed_case_is_lowercased():
    assert title_to_id("My Project", "project") == "my_project"


# ─── ID Uniqueness Tests ─────────────────────────────────────────────────────


class TestCreateIdUniqueness:
    """Tests for ID uniqueness validation in create command"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_duplicate_custom_id_fails(
        self, mock_get_registry_path, registry_with_projects
    ):
        """Test that creating with a duplicate custom ID fails"""
        mock_get_registry_path.return_value = str(registry_with_projects)

        with patch("builtins.print") as mock_print:
            result = main(
                ["create", "project", "New Project", "--id", "P-001", "--no-commit"]
            )

        # Should fail
        assert result == 1

        # Error message should mention the duplicate ID
        assert any(
            "P-001" in call[0][0] and "already exists" in call[0][0].lower()
            for call in mock_print.call_args_list
        )

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_unique_custom_id_succeeds(
        self, mock_get_registry_path, registry_with_projects
    ):
        """Test that creating with a unique custom ID succeeds"""
        mock_get_registry_path.return_value = str(registry_with_projects)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "newuid12-1234-5678-1234-567812345678"
            ),
        ):
            result = main(
                ["create", "project", "New Project", "--id", "P-UNIQUE", "--no-commit"]
            )

        assert result == 0

        # File should be created
        project_file = registry_with_projects / "projects" / "proj-newuid12.yml"
        assert project_file.exists()

        with open(project_file) as f:
            data = yaml.safe_load(f)
        assert data["id"] == "P-UNIQUE"

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_auto_id_collision_resolution(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that auto-generated ID collision is resolved with suffix"""
        mock_get_registry_path.return_value = str(temp_registry)

        # Create first entity with auto ID
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "first123-1234-5678-1234-567812345678"
            ),
        ):
            result1 = main(["create", "project", "Test Project", "--no-commit"])
        assert result1 == 0

        # Create second entity with same title (would generate same base ID)
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "second12-1234-5678-1234-567812345678"
            ),
        ):
            result2 = main(["create", "project", "Test Project", "--no-commit"])
        assert result2 == 0

        # Both files should exist
        file1 = temp_registry / "projects" / "proj-first123.yml"
        file2 = temp_registry / "projects" / "proj-second12.yml"
        assert file1.exists()
        assert file2.exists()

        # IDs should be different
        with open(file1) as f:
            data1 = yaml.safe_load(f)
        with open(file2) as f:
            data2 = yaml.safe_load(f)

        assert data1["id"] != data2["id"]
        # Second one should have a suffix
        assert data2["id"].startswith("test_project_")

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_same_id_different_entity_types_allowed(
        self, mock_get_registry_path, registry_with_projects
    ):
        """Test that same ID can be used for different entity types"""
        mock_get_registry_path.return_value = str(registry_with_projects)

        # P-001 exists as a project, but should be allowed for a program
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "proguid1-1234-5678-1234-567812345678"
            ),
        ):
            result = main(
                ["create", "program", "Test Program", "--id", "P-001", "--no-commit"]
            )

        assert result == 0

        program_file = registry_with_projects / "programs" / "prog-proguid1.yml"
        assert program_file.exists()

        with open(program_file) as f:
            data = yaml.safe_load(f)
        assert data["id"] == "P-001"


# ─── Git Integration Tests ───────────────────────────────────────────────────


class TestCreateGitCommitUnit:
    """Unit tests for git commit functionality using mocks."""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_no_commit_flag_skips_git_operations(
        self, mock_get_registry_path, temp_registry, capsys
    ):
        """Test that --no-commit flag prevents git operations."""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch(
                "hxc.core.operations.create.commit_entity_change"
            ) as mock_commit:
                result = main(["create", "project", "Test Project", "--no-commit"])

        assert result == 0
        mock_commit.assert_not_called()

        out = capsys.readouterr().out
        assert "--no-commit" in out

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_without_no_commit_flag_calls_commit(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that commit is called when --no-commit is not specified."""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch(
                "hxc.core.operations.create.commit_entity_change"
            ) as mock_commit:
                result = main(["create", "project", "Test Project"])

        assert result == 0
        mock_commit.assert_called_once()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_called_with_correct_action(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that commit is called with action='Create'."""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch(
                "hxc.core.operations.create.commit_entity_change"
            ) as mock_commit:
                result = main(["create", "project", "Test Project"])

        assert result == 0
        call_kwargs = mock_commit.call_args[1]
        assert call_kwargs["action"] == "Create"

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_called_with_entity_data(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that commit is called with correct entity data."""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch(
                "hxc.core.operations.create.commit_entity_change"
            ) as mock_commit:
                result = main(["create", "project", "Test Project"])

        assert result == 0
        call_kwargs = mock_commit.call_args[1]
        entity_data = call_kwargs["entity_data"]
        assert entity_data["type"] == "project"
        assert entity_data["title"] == "Test Project"
        assert entity_data["uid"] == "12345678"

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_called_with_registry_path(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that commit is called with correct registry path."""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch(
                "hxc.core.operations.create.commit_entity_change"
            ) as mock_commit:
                result = main(["create", "project", "Test Project"])

        assert result == 0
        call_kwargs = mock_commit.call_args[1]
        assert call_kwargs["registry_path"] == str(temp_registry)


class TestCreateGitCommitNonGitRepo:
    """Tests for create command behavior when registry is not a git repo."""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_succeeds_without_git_repo(
        self, mock_get_registry_path, temp_registry, capsys
    ):
        """Test that create succeeds even if registry is not a git repo."""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project"])

        assert result == 0

        # File should be created
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()

        out = capsys.readouterr().out
        assert "not inside a git repository" in out

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_without_git_installed(
        self, mock_get_registry_path, temp_registry, capsys
    ):
        """Test that create succeeds even if git is not installed."""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch("hxc.utils.git.git_available", return_value=False):
                with patch(
                    "hxc.utils.git.find_git_root", return_value=str(temp_registry)
                ):
                    result = main(["create", "project", "Test Project"])

        assert result == 0

        # File should still be created
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()

        out = capsys.readouterr().out
        assert "git is not installed" in out


class TestCreateGitCommitIntegration:
    """Integration tests that perform real git operations."""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_commits_to_git(self, mock_get_registry_path, git_registry):
        """Test that create command commits the new file to git."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Git Test Project"])

        assert result == 0

        # Check git log for the commit
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "proj-12345678" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_message_contains_title(self, mock_get_registry_path, git_registry):
        """Test that commit message contains the entity title."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "My Amazing Project"])

        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "My Amazing Project" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_message_contains_entity_type(
        self, mock_get_registry_path, git_registry
    ):
        """Test that commit message body contains the entity type."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project"])

        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Entity type: project" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_message_contains_uid(self, mock_get_registry_path, git_registry):
        """Test that commit message body contains the entity UID."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project"])

        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Entity UID: 12345678" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_only_new_file_is_committed(self, mock_get_registry_path, git_registry):
        """Test that only the created file is committed, not other changes."""
        mock_get_registry_path.return_value = str(git_registry)

        # Create an unrelated file that should not be committed
        unrelated = git_registry / "unrelated.txt"
        unrelated.write_text("This should not be committed")

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project"])

        assert result == 0

        # Check what files were committed
        show = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        committed_files = show.stdout.strip().splitlines()
        assert any("proj-12345678.yml" in f for f in committed_files)
        assert not any("unrelated.txt" in f for f in committed_files)

        # Unrelated file should still exist but be untracked
        assert unrelated.exists()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_no_commit_flag_leaves_file_unstaged(
        self, mock_get_registry_path, git_registry
    ):
        """Test that --no-commit leaves the new file unstaged."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project", "--no-commit"])

        assert result == 0

        # Check git status with -uall to show individual untracked files
        status = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        # File should appear as untracked
        assert "proj-12345678.yml" in status.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_all_entity_types_commits(
        self, mock_get_registry_path, git_registry
    ):
        """Test that create commits work for all entity types."""
        mock_get_registry_path.return_value = str(git_registry)

        for i, entity_type in enumerate(EntityType):
            uid = f"1234567{i}"
            with patch(
                "hxc.core.operations.create.uuid.uuid4",
                return_value=MagicMock(
                    __str__=lambda x: f"{uid}-1234-5678-1234-567812345678"
                ),
            ):
                result = main(
                    ["create", entity_type.value, f"Test {entity_type.value.title()}"]
                )

            assert result == 0

            # Verify commit was created
            log = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=git_registry,
                capture_output=True,
                text=True,
                check=True,
            )

            file_prefix = entity_type.get_file_prefix()
            assert f"{file_prefix}-{uid}" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_sequential_creates_produce_separate_commits(
        self, mock_get_registry_path, git_registry
    ):
        """Test that multiple create commands produce separate commits."""
        mock_get_registry_path.return_value = str(git_registry)

        # Create first entity
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "11111111-1234-5678-1234-567812345678"
            ),
        ):
            result1 = main(["create", "project", "First Project"])
        assert result1 == 0

        # Create second entity
        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "22222222-1234-5678-1234-567812345678"
            ),
        ):
            result2 = main(["create", "project", "Second Project"])
        assert result2 == 0

        # Check that both commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "proj-11111111" in log.stdout
        assert "proj-22222222" in log.stdout

        # Count commits (should be initial + 2 new)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 3

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_includes_custom_id_in_message(
        self, mock_get_registry_path, git_registry
    ):
        """Test that commit message includes custom ID when provided."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project", "--id", "P-CUSTOM-001"])

        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Entity ID: P-CUSTOM-001" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_includes_category_in_message(
        self, mock_get_registry_path, git_registry
    ):
        """Test that commit message includes category when provided."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(
                [
                    "create",
                    "project",
                    "Test Project",
                    "--category",
                    "software.dev/cli-tool",
                ]
            )

        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Category: software.dev/cli-tool" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_includes_status_in_message(
        self, mock_get_registry_path, git_registry
    ):
        """Test that commit message includes status."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project", "--status", "on-hold"])

        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Status: on-hold" in log.stdout

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_commit_hash_displayed_to_user(
        self, mock_get_registry_path, git_registry, capsys
    ):
        """Test that the commit hash is displayed to the user."""
        mock_get_registry_path.return_value = str(git_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main(["create", "project", "Test Project"])

        assert result == 0

        out = capsys.readouterr().out
        assert "committed to git" in out
        # Should include a parenthesized hash like "(abc1234)"
        assert "(" in out and ")" in out


class TestCreateGitErrorHandling:
    """Tests for error handling in git operations during create."""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_git_error_does_not_fail_create(
        self, mock_get_registry_path, git_registry, capsys
    ):
        """Test that git errors don't fail the create operation."""
        mock_get_registry_path.return_value = str(git_registry)

        # Make git commit fail
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: some git error"

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch("hxc.utils.git.git_available", return_value=True):
                with patch("subprocess.run", side_effect=[MagicMock(), error]):
                    result = main(["create", "project", "Test Project"])

        # Create should still succeed
        assert result == 0

        # File should be created
        project_file = git_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()

        out = capsys.readouterr().out
        assert "git commit failed" in out
        assert "File was created but not committed" in out

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_nothing_to_commit_handled_gracefully(
        self, mock_get_registry_path, git_registry, capsys
    ):
        """Test that 'nothing to commit' is handled gracefully."""
        mock_get_registry_path.return_value = str(git_registry)

        error = subprocess.CalledProcessError(1, "git")
        error.stdout = "nothing to commit"
        error.stderr = ""

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            with patch("hxc.utils.git.git_available", return_value=True):
                with patch("subprocess.run", side_effect=[MagicMock(), error]):
                    result = main(["create", "project", "Test Project"])

        assert result == 0

        out = capsys.readouterr().out
        assert "Nothing new to commit" in out


class TestCreateUsesSharedOperation:
    """Tests to verify CLI command delegates to shared CreateOperation"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_command_uses_create_operation(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that CreateCommand uses CreateOperation internally"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.create.CreateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.create_entity.return_value = {
                "success": True,
                "uid": "12345678",
                "id": "test_project",
                "file_path": str(temp_registry / "projects" / "proj-12345678.yml"),
                "entity": {"type": "project", "title": "Test Project"},
                "git_committed": False,
            }
            MockOperation.return_value = mock_instance

            result = main(["create", "project", "Test Project", "--no-commit"])

        assert result == 0
        MockOperation.assert_called_once_with(str(temp_registry))
        mock_instance.create_entity.assert_called_once()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_command_passes_use_git_parameter(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that use_git parameter is passed correctly based on --no-commit flag"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.create.CreateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.create_entity.return_value = {
                "success": True,
                "uid": "12345678",
                "id": "test_project",
                "file_path": str(temp_registry / "projects" / "proj-12345678.yml"),
                "entity": {"type": "project", "title": "Test Project"},
                "git_committed": False,
            }
            MockOperation.return_value = mock_instance

            # With --no-commit, use_git should be False
            main(["create", "project", "Test Project", "--no-commit"])
            call_kwargs = mock_instance.create_entity.call_args[1]
            assert call_kwargs["use_git"] is False

            mock_instance.reset_mock()

            # Without --no-commit, use_git should be True
            main(["create", "project", "Test Project"])
            call_kwargs = mock_instance.create_entity.call_args[1]
            assert call_kwargs["use_git"] is True

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_handles_duplicate_id_error(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that DuplicateIdError is handled correctly"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.create.CreateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.create_entity.side_effect = DuplicateIdError(
                "project with id 'P-001' already exists in this registry"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                result = main(
                    ["create", "project", "Test", "--id", "P-001", "--no-commit"]
                )

        assert result == 1
        assert any(
            "P-001" in call[0][0] and "already exists" in call[0][0].lower()
            for call in mock_print.call_args_list
        )

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_handles_create_operation_error(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that CreateOperationError is handled correctly"""
        mock_get_registry_path.return_value = str(temp_registry)

        with patch("hxc.commands.create.CreateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.create_entity.side_effect = CreateOperationError(
                "Could not generate a unique project id"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                result = main(["create", "project", "Test", "--no-commit"])

        assert result == 1
        assert any(
            "Could not generate" in call[0][0] for call in mock_print.call_args_list
        )
