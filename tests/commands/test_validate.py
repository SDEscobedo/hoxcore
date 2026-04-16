"""
Tests for the validate command.

This module tests the CLI validate command that uses the shared ValidateOperation
to ensure behavioral consistency with MCP tools.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.commands.validate import ValidateCommand
from hxc.core.operations.validate import ValidateOperation, ValidationResult


class TestValidateCommand:
    """Test suite for ValidateCommand"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        # Create entity directories
        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        # Create config file
        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    @pytest.fixture
    def valid_entity(self):
        """Create a valid entity"""
        return {
            "type": "project",
            "uid": "proj-001",
            "title": "Test Project",
            "status": "active",
            "description": "A test project",
        }

    def create_entity_file(self, registry_path, entity_type, filename, data):
        """Helper to create an entity file"""
        folder_map = {
            "program": "programs",
            "project": "projects",
            "mission": "missions",
            "action": "actions",
        }

        folder = folder_map.get(entity_type, "projects")
        file_path = registry_path / folder / filename

        with open(file_path, "w") as f:
            yaml.dump(data, f)

        return file_path

    def test_register_subparser(self):
        """Test that subparser is registered correctly"""
        mock_subparsers = MagicMock()
        mock_parser = MagicMock()
        mock_subparsers.add_parser.return_value = mock_parser

        parser = ValidateCommand.register_subparser(mock_subparsers)

        mock_subparsers.add_parser.assert_called_once_with(
            ValidateCommand.name, help=ValidateCommand.help
        )
        assert parser == mock_parser

    def test_command_name_and_help(self):
        """Test that command has correct name and help text"""
        assert ValidateCommand.name == "validate"
        assert ValidateCommand.help == "Validate registry integrity and consistency"

    def test_validate_valid_registry(self, mock_registry, valid_entity, capsys):
        """Test validation of a valid registry"""
        # Create valid entities
        self.create_entity_file(mock_registry, "project", "proj-001.yml", valid_entity)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "✅ Registry validation passed!" in captured.out

    def test_validate_missing_required_fields(self, mock_registry, capsys):
        """Test detection of missing required fields"""
        # Create entity missing required fields
        invalid_entity = {
            "type": "project",
            # Missing uid and title
            "status": "active",
        }

        self.create_entity_file(
            mock_registry, "project", "proj-invalid.yml", invalid_entity
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Missing required field 'uid'" in captured.out
        assert "Missing required field 'title'" in captured.out

    def test_validate_duplicate_uids(self, mock_registry, valid_entity, capsys):
        """Test detection of duplicate UIDs"""
        # Create two entities with the same UID
        entity1 = valid_entity.copy()
        entity2 = valid_entity.copy()
        entity2["title"] = "Another Project"

        self.create_entity_file(mock_registry, "project", "proj-001.yml", entity1)
        self.create_entity_file(mock_registry, "project", "proj-002.yml", entity2)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Duplicate UID 'proj-001'" in captured.out

    def test_validate_duplicate_ids(self, mock_registry, capsys):
        """Test detection of duplicate IDs within the same entity type"""
        # Create two entities of the same type with identical 'id' fields
        entity1 = {
            "type": "project",
            "uid": "proj-001",
            "id": "P-DUPLICATE",
            "title": "First Project",
            "status": "active",
        }
        entity2 = {
            "type": "project",
            "uid": "proj-002",
            "id": "P-DUPLICATE",  # Same ID as entity1
            "title": "Second Project",
            "status": "active",
        }

        self.create_entity_file(mock_registry, "project", "proj-001.yml", entity1)
        self.create_entity_file(mock_registry, "project", "proj-002.yml", entity2)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Duplicate ID 'P-DUPLICATE'" in captured.out
        assert "proj-001.yml" in captured.out
        assert "proj-002.yml" in captured.out

    def test_validate_duplicate_ids_different_types_allowed(
        self, mock_registry, capsys
    ):
        """Test that duplicate IDs across different entity types are allowed"""
        # Create entities of different types with the same 'id' field
        project_entity = {
            "type": "project",
            "uid": "proj-001",
            "id": "SHARED-ID",
            "title": "A Project",
            "status": "active",
        }
        program_entity = {
            "type": "program",
            "uid": "prog-001",
            "id": "SHARED-ID",  # Same ID as project, but different type
            "title": "A Program",
            "status": "active",
        }

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", project_entity
        )
        self.create_entity_file(
            mock_registry, "program", "prog-001.yml", program_entity
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        # Should pass - duplicate IDs are only checked within the same entity type
        assert result == 0
        captured = capsys.readouterr()
        assert "✅ Registry validation passed!" in captured.out

    def test_validate_broken_parent_link(self, mock_registry, valid_entity, capsys):
        """Test detection of broken parent links"""
        # Create entity with non-existent parent
        entity_with_parent = valid_entity.copy()
        entity_with_parent["parent"] = "nonexistent-parent"

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", entity_with_parent
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Broken parent link" in captured.out
        assert "nonexistent-parent" in captured.out

    def test_validate_broken_child_link(self, mock_registry, valid_entity, capsys):
        """Test detection of broken child links"""
        # Create entity with non-existent children
        entity_with_children = valid_entity.copy()
        entity_with_children["children"] = [
            "nonexistent-child-1",
            "nonexistent-child-2",
        ]

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", entity_with_children
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Broken child link" in captured.out
        assert "nonexistent-child-1" in captured.out

    def test_validate_broken_related_link(self, mock_registry, valid_entity, capsys):
        """Test detection of broken related links (warnings)"""
        # Create entity with non-existent related entities
        entity_with_related = valid_entity.copy()
        entity_with_related["related"] = ["nonexistent-related"]

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", entity_with_related
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        # Related links are warnings, not errors
        assert result == 0
        captured = capsys.readouterr()
        assert "Broken related link" in captured.out
        assert "⚠️" in captured.out

    def test_validate_invalid_status(self, mock_registry, valid_entity, capsys):
        """Test detection of invalid status values"""
        # Create entity with invalid status
        invalid_status_entity = valid_entity.copy()
        invalid_status_entity["status"] = "invalid-status"

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", invalid_status_entity
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid status 'invalid-status'" in captured.out

    def test_validate_type_mismatch(self, mock_registry, valid_entity, capsys):
        """Test detection of type mismatches"""
        # Create entity with type that doesn't match directory
        mismatched_entity = valid_entity.copy()
        mismatched_entity["type"] = "program"  # But in projects directory

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", mismatched_entity
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Type mismatch" in captured.out
        assert "declared as 'program'" in captured.out
        assert "in 'project' directory" in captured.out

    def test_validate_empty_file(self, mock_registry, capsys):
        """Test handling of empty YAML files"""
        # Create empty file
        file_path = mock_registry / "projects" / "empty.yml"
        file_path.write_text("")

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Empty file" in captured.out

    def test_validate_invalid_yaml(self, mock_registry, capsys):
        """Test handling of invalid YAML files"""
        # Create file with invalid YAML
        file_path = mock_registry / "projects" / "invalid.yml"
        file_path.write_text("invalid: yaml: content: [")

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "YAML parse error" in captured.out or "Error loading" in captured.out

    def test_validate_no_registry(self, capsys):
        """Test validation when no registry is found"""
        args = MagicMock()
        args.registry = None
        args.verbose = False
        args.fix = False

        with patch(
            "hxc.commands.validate.ValidateCommand._get_registry_path",
            return_value=None,
        ):
            result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "No registry found" in captured.out

    def test_validate_with_verbose(self, mock_registry, valid_entity, capsys):
        """Test validation with verbose output"""
        self.create_entity_file(mock_registry, "project", "proj-001.yml", valid_entity)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "Loading entities" in captured.out
        assert "Checking required fields" in captured.out
        assert "Checking UID uniqueness" in captured.out
        assert "Checking ID uniqueness" in captured.out
        assert "Checking relationships" in captured.out
        assert "Checking status values" in captured.out
        assert "Checking entity types" in captured.out

    def test_validate_fix_warning(self, mock_registry, valid_entity, capsys):
        """Test that --fix option shows warning"""
        self.create_entity_file(mock_registry, "project", "proj-001.yml", valid_entity)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = True

        result = ValidateCommand.execute(args)

        captured = capsys.readouterr()
        assert "--fix option is not implemented" in captured.out

    def test_validate_invalid_children_format(
        self, mock_registry, valid_entity, capsys
    ):
        """Test detection of invalid children format"""
        # Create entity with children as string instead of list
        invalid_children_entity = valid_entity.copy()
        invalid_children_entity["children"] = "not-a-list"

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", invalid_children_entity
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid children format" in captured.out

    def test_validate_invalid_related_format(self, mock_registry, valid_entity, capsys):
        """Test detection of invalid related format"""
        # Create entity with related as string instead of list
        invalid_related_entity = valid_entity.copy()
        invalid_related_entity["related"] = "not-a-list"

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", invalid_related_entity
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        # Related format issues are warnings
        assert result == 0
        captured = capsys.readouterr()
        assert "Invalid related format" in captured.out
        assert "⚠️" in captured.out

    def test_validate_multiple_errors(self, mock_registry, capsys):
        """Test validation with multiple errors"""
        # Create entity with multiple issues
        problematic_entity = {
            "type": "program",  # Type mismatch
            # Missing uid and title
            "status": "invalid-status",  # Invalid status
            "parent": "nonexistent-parent",  # Broken parent link
            "children": ["nonexistent-child"],  # Broken child link
        }

        self.create_entity_file(
            mock_registry, "project", "proj-001.yml", problematic_entity
        )

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()

        # Check that all errors are reported
        assert "Missing required field 'uid'" in captured.out
        assert "Missing required field 'title'" in captured.out
        assert "Invalid status" in captured.out
        assert "Type mismatch" in captured.out
        assert "Broken parent link" in captured.out
        assert "Broken child link" in captured.out

    def test_validate_valid_relationships(self, mock_registry, valid_entity, capsys):
        """Test validation with valid parent/child relationships"""
        # Create parent entity
        parent_entity = valid_entity.copy()
        parent_entity["uid"] = "prog-001"
        parent_entity["type"] = "program"
        parent_entity["children"] = ["proj-001"]

        # Create child entity
        child_entity = valid_entity.copy()
        child_entity["uid"] = "proj-001"
        child_entity["parent"] = "prog-001"

        self.create_entity_file(mock_registry, "program", "prog-001.yml", parent_entity)
        self.create_entity_file(mock_registry, "project", "proj-001.yml", child_entity)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "All relationships are valid" in captured.out

    def test_validate_results_summary(self, mock_registry, valid_entity, capsys):
        """Test that validation results summary is displayed"""
        self.create_entity_file(mock_registry, "project", "proj-001.yml", valid_entity)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        result = ValidateCommand.execute(args)

        captured = capsys.readouterr()
        assert "VALIDATION RESULTS" in captured.out
        assert "Total entities:" in captured.out
        assert "Errors:" in captured.out
        assert "Warnings:" in captured.out

    @patch("hxc.commands.validate.RegistryCommand.get_registry_path")
    def test_get_registry_path_from_config(self, mock_get_path, mock_registry):
        """Test getting registry path from config"""
        mock_get_path.return_value = str(mock_registry)

        result = ValidateCommand._get_registry_path()

        assert result == str(mock_registry)
        mock_get_path.assert_called_once()

    @patch("hxc.commands.validate.get_project_root")
    @patch("hxc.commands.validate.RegistryCommand.get_registry_path")
    def test_get_registry_path_from_current_dir(
        self, mock_get_path, mock_get_root, mock_registry
    ):
        """Test getting registry path from current directory"""
        mock_get_path.return_value = None
        mock_get_root.return_value = str(mock_registry)

        result = ValidateCommand._get_registry_path()

        assert result == str(mock_registry)
        mock_get_path.assert_called_once()
        mock_get_root.assert_called_once()

    def test_validate_duplicate_ids_multiple_files(self, mock_registry, capsys):
        """Test that duplicate ID error message lists all conflicting files"""
        # Create three entities of the same type with the same 'id' field
        entity1 = {
            "type": "project",
            "uid": "proj-001",
            "id": "P-SAME",
            "title": "First Project",
            "status": "active",
        }
        entity2 = {
            "type": "project",
            "uid": "proj-002",
            "id": "P-SAME",
            "title": "Second Project",
            "status": "active",
        }
        entity3 = {
            "type": "project",
            "uid": "proj-003",
            "id": "P-SAME",
            "title": "Third Project",
            "status": "active",
        }

        self.create_entity_file(mock_registry, "project", "proj-001.yml", entity1)
        self.create_entity_file(mock_registry, "project", "proj-002.yml", entity2)
        self.create_entity_file(mock_registry, "project", "proj-003.yml", entity3)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Duplicate ID 'P-SAME'" in captured.out
        # All three files should be mentioned
        assert "proj-001.yml" in captured.out
        assert "proj-002.yml" in captured.out
        assert "proj-003.yml" in captured.out

    def test_validate_unique_ids_pass(self, mock_registry, capsys):
        """Test that unique IDs within the same entity type pass validation"""
        entity1 = {
            "type": "project",
            "uid": "proj-001",
            "id": "P-001",
            "title": "First Project",
            "status": "active",
        }
        entity2 = {
            "type": "project",
            "uid": "proj-002",
            "id": "P-002",
            "title": "Second Project",
            "status": "active",
        }

        self.create_entity_file(mock_registry, "project", "proj-001.yml", entity1)
        self.create_entity_file(mock_registry, "project", "proj-002.yml", entity2)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "All" in captured.out and "IDs are unique" in captured.out


class TestValidateCommandUsesSharedOperation:
    """Tests to verify ValidateCommand uses shared ValidateOperation"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    def test_validate_uses_validate_operation(self, mock_registry):
        """Test that ValidateCommand uses ValidateOperation internally"""
        with patch("hxc.commands.validate.ValidateOperation") as MockOperation:
            mock_result = ValidationResult()
            mock_result.entities_checked = 5
            mock_result.entities_by_type = {"project": 5}

            mock_instance = MagicMock()
            mock_instance.validate_registry.return_value = mock_result
            MockOperation.return_value = mock_instance

            args = MagicMock()
            args.registry = str(mock_registry)
            args.verbose = False
            args.fix = False

            ValidateCommand.execute(args)

            MockOperation.assert_called_once_with(str(mock_registry))
            mock_instance.validate_registry.assert_called_once_with(verbose=False)

    def test_validate_passes_verbose_to_operation(self, mock_registry):
        """Test that verbose parameter is passed to ValidateOperation"""
        with patch("hxc.commands.validate.ValidateOperation") as MockOperation:
            mock_result = ValidationResult()
            mock_instance = MagicMock()
            mock_instance.validate_registry.return_value = mock_result
            MockOperation.return_value = mock_instance

            args = MagicMock()
            args.registry = str(mock_registry)
            args.verbose = True
            args.fix = False

            ValidateCommand.execute(args)

            mock_instance.validate_registry.assert_called_once_with(verbose=True)


class TestValidateCommandErrorHandling:
    """Tests for error handling in ValidateCommand"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    def test_validate_handles_path_security_error(self, mock_registry, capsys):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.commands.validate.ValidateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.validate_registry.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            args = MagicMock()
            args.registry = str(mock_registry)
            args.verbose = False
            args.fix = False

            result = ValidateCommand.execute(args)

            assert result == 1
            captured = capsys.readouterr()
            assert "Security error" in captured.out

    def test_validate_handles_unexpected_exception(self, mock_registry, capsys):
        """Test that unexpected exceptions are handled"""
        with patch("hxc.commands.validate.ValidateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.validate_registry.side_effect = RuntimeError("Unexpected")
            MockOperation.return_value = mock_instance

            args = MagicMock()
            args.registry = str(mock_registry)
            args.verbose = False
            args.fix = False

            result = ValidateCommand.execute(args)

            assert result == 1
            captured = capsys.readouterr()
            assert "Error validating registry" in captured.out

    def test_validate_handles_exception_with_verbose_traceback(
        self, mock_registry, capsys
    ):
        """Test that verbose mode shows traceback on exception"""
        with patch("hxc.commands.validate.ValidateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.validate_registry.side_effect = RuntimeError("Unexpected")
            MockOperation.return_value = mock_instance

            args = MagicMock()
            args.registry = str(mock_registry)
            args.verbose = True
            args.fix = False

            result = ValidateCommand.execute(args)

            assert result == 1
            captured = capsys.readouterr()
            # Traceback is printed to stderr, not stdout
            assert "Traceback" in captured.err or "RuntimeError" in captured.err


class TestValidateCommandBehavioralParity:
    """Tests to verify ValidateCommand produces same results as ValidateOperation"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    def create_entity_file(self, registry_path, entity_type, filename, data):
        """Helper to create an entity file"""
        folder_map = {
            "program": "programs",
            "project": "projects",
            "mission": "missions",
            "action": "actions",
        }
        folder = folder_map.get(entity_type, "projects")
        file_path = registry_path / folder / filename
        with open(file_path, "w") as f:
            yaml.dump(data, f)
        return file_path

    def test_cli_produces_same_errors_as_operation(self, mock_registry, capsys):
        """Test that CLI produces same errors as direct ValidateOperation"""
        # Create entity with issues
        entity = {
            "type": "project",
            "uid": "proj-test",
            "title": "Test",
            "status": "invalid-status",
        }
        self.create_entity_file(mock_registry, "project", "proj-test.yml", entity)

        # Use direct operation
        operation = ValidateOperation(str(mock_registry))
        operation_result = operation.validate_registry()

        # Use CLI command
        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = True
        args.fix = False

        cli_result = ValidateCommand.execute(args)

        # CLI should return 1 (error) when operation has errors
        assert cli_result == 1 if not operation_result.valid else 0

        captured = capsys.readouterr()

        # All operation errors should appear in CLI output
        for error in operation_result.errors:
            assert error in captured.out

    def test_cli_counts_match_operation_counts(self, mock_registry, capsys):
        """Test that CLI displays same counts as ValidateOperation"""
        # Create some valid entities
        entity1 = {
            "type": "project",
            "uid": "proj-001",
            "title": "Project 1",
            "status": "active",
        }
        entity2 = {
            "type": "project",
            "uid": "proj-002",
            "title": "Project 2",
            "status": "active",
        }
        self.create_entity_file(mock_registry, "project", "proj-001.yml", entity1)
        self.create_entity_file(mock_registry, "project", "proj-002.yml", entity2)

        # Use direct operation
        operation = ValidateOperation(str(mock_registry))
        operation_result = operation.validate_registry()

        # Use CLI command
        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        ValidateCommand.execute(args)

        captured = capsys.readouterr()

        # CLI should display same entity count
        assert f"Total entities: {operation_result.entities_checked}" in captured.out
        assert f"Errors: {operation_result.error_count}" in captured.out
        assert f"Warnings: {operation_result.warning_count}" in captured.out

    def test_cli_returns_0_when_operation_valid(self, mock_registry):
        """Test that CLI returns 0 when operation reports valid"""
        # Create valid entity
        entity = {
            "type": "project",
            "uid": "proj-001",
            "title": "Valid Project",
            "status": "active",
        }
        self.create_entity_file(mock_registry, "project", "proj-001.yml", entity)

        # Use direct operation
        operation = ValidateOperation(str(mock_registry))
        operation_result = operation.validate_registry()

        # Verify operation reports valid
        assert operation_result.valid is True

        # CLI should return 0
        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        cli_result = ValidateCommand.execute(args)
        assert cli_result == 0

    def test_cli_returns_1_when_operation_invalid(self, mock_registry):
        """Test that CLI returns 1 when operation reports invalid"""
        # Create invalid entity (missing required fields)
        entity = {
            "type": "project",
            "status": "active",
            # Missing uid and title
        }
        self.create_entity_file(mock_registry, "project", "proj-bad.yml", entity)

        # Use direct operation
        operation = ValidateOperation(str(mock_registry))
        operation_result = operation.validate_registry()

        # Verify operation reports invalid
        assert operation_result.valid is False

        # CLI should return 1
        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        cli_result = ValidateCommand.execute(args)
        assert cli_result == 1


class TestValidateCommandDisplayResults:
    """Tests for _display_results method"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    def test_display_results_shows_errors_section(self, capsys):
        """Test that ERRORS section is displayed when errors exist"""
        result = ValidationResult()
        result.add_error("Error 1")
        result.add_error("Error 2")
        result.entities_checked = 1

        ValidateCommand._display_results(result, verbose=False)

        captured = capsys.readouterr()
        assert "ERRORS:" in captured.out
        assert "Error 1" in captured.out
        assert "Error 2" in captured.out

    def test_display_results_shows_warnings_section(self, capsys):
        """Test that WARNINGS section is displayed when warnings exist"""
        result = ValidationResult()
        result.add_warning("Warning 1")
        result.entities_checked = 1

        ValidateCommand._display_results(result, verbose=False)

        captured = capsys.readouterr()
        assert "WARNINGS:" in captured.out
        assert "Warning 1" in captured.out

    def test_display_results_valid_no_warnings(self, capsys):
        """Test display for valid registry without warnings"""
        result = ValidationResult()
        result.entities_checked = 5

        ValidateCommand._display_results(result, verbose=False)

        captured = capsys.readouterr()
        assert "✅ Registry validation passed! No issues found." in captured.out

    def test_display_results_valid_with_warnings(self, capsys):
        """Test display for valid registry with warnings"""
        result = ValidationResult()
        result.add_warning("Minor issue")
        result.entities_checked = 5

        ValidateCommand._display_results(result, verbose=False)

        captured = capsys.readouterr()
        assert "✅ Registry validation passed with warnings." in captured.out

    def test_display_results_invalid(self, capsys):
        """Test display for invalid registry"""
        result = ValidationResult()
        result.add_error("Critical issue")
        result.entities_checked = 5

        ValidateCommand._display_results(result, verbose=False)

        captured = capsys.readouterr()
        assert "❌ Registry validation failed." in captured.out

    def test_display_results_verbose_valid(self, capsys):
        """Test verbose display for valid registry"""
        result = ValidationResult()
        result.entities_checked = 5

        ValidateCommand._display_results(result, verbose=True)

        captured = capsys.readouterr()
        assert "✓ All required fields present" in captured.out
        assert "✓ All 5 UIDs are unique" in captured.out
        assert "✓ All 5 IDs are unique within their entity types" in captured.out
        assert "✓ All relationships are valid" in captured.out
        assert "✓ All status values are valid" in captured.out
        assert "✓ All entity types match their directories" in captured.out

    def test_display_results_verbose_with_errors(self, capsys):
        """Test verbose display shows errors"""
        result = ValidationResult()
        result.add_error("Verbose error")
        result.add_warning("Verbose warning")
        result.entities_checked = 1

        ValidateCommand._display_results(result, verbose=True)

        captured = capsys.readouterr()
        assert "❌ Verbose error" in captured.out
        assert "⚠️  Verbose warning" in captured.out


class TestValidateCommandSpecifiedRegistry:
    """Tests for specifying registry path via --registry argument"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    def test_validate_with_specified_registry(self, mock_registry, capsys):
        """Test validation uses specified registry path"""
        entity = {
            "type": "project",
            "uid": "proj-001",
            "title": "Test",
            "status": "active",
        }
        file_path = mock_registry / "projects" / "proj-001.yml"
        with open(file_path, "w") as f:
            yaml.dump(entity, f)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert str(mock_registry) in captured.out

    def test_get_registry_path_prefers_specified(self, mock_registry):
        """Test that specified path is preferred over config"""
        result = ValidateCommand._get_registry_path(str(mock_registry))

        assert result == str(mock_registry)


class TestValidateCommandAllStatusValues:
    """Tests for validation of all valid status values"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    @pytest.mark.parametrize(
        "status",
        ["active", "completed", "on-hold", "cancelled", "planned"],
    )
    def test_validate_accepts_all_valid_statuses(self, mock_registry, status, capsys):
        """Test that all valid status values are accepted"""
        entity = {
            "type": "project",
            "uid": f"proj-{status}",
            "title": f"Project with {status}",
            "status": status,
        }
        file_path = mock_registry / "projects" / f"proj-{status}.yml"
        with open(file_path, "w") as f:
            yaml.dump(entity, f)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "✅ Registry validation passed!" in captured.out


class TestValidateCommandAllEntityTypes:
    """Tests for validation of all entity types"""

    @pytest.fixture
    def mock_registry(self, tmp_path):
        """Create a mock registry structure"""
        registry_path = tmp_path / "test_registry"
        registry_path.mkdir()

        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        config_file = registry_path / "config.yml"
        config_file.write_text("version: 1.0\n")

        return registry_path

    @pytest.mark.parametrize(
        "entity_type,folder",
        [
            ("program", "programs"),
            ("project", "projects"),
            ("mission", "missions"),
            ("action", "actions"),
        ],
    )
    def test_validate_accepts_all_entity_types(
        self, mock_registry, entity_type, folder, capsys
    ):
        """Test that all entity types are validated correctly"""
        entity = {
            "type": entity_type,
            "uid": f"{entity_type}-001",
            "title": f"Test {entity_type.title()}",
            "status": "active",
        }
        file_path = mock_registry / folder / f"{entity_type}-001.yml"
        with open(file_path, "w") as f:
            yaml.dump(entity, f)

        args = MagicMock()
        args.registry = str(mock_registry)
        args.verbose = False
        args.fix = False

        result = ValidateCommand.execute(args)

        assert result == 0
        captured = capsys.readouterr()
        assert "✅ Registry validation passed!" in captured.out
