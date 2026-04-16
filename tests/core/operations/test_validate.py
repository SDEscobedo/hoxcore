"""
Tests for the ValidateOperation core module.

This module tests the shared validation operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.validate import (
    EntityValidationResult,
    ValidateOperation,
    ValidateOperationError,
    ValidationResult,
)
from hxc.utils.path_security import PathSecurityError


class TestValidationResult:
    """Tests for ValidationResult dataclass"""

    def test_default_values(self):
        """Test that ValidationResult has correct default values"""
        result = ValidationResult()

        assert result.errors == []
        assert result.warnings == []
        assert result.entities_checked == 0
        assert result.entities_by_type == {}

    def test_valid_property_with_no_errors(self):
        """Test that valid is True when no errors"""
        result = ValidationResult()

        assert result.valid is True

    def test_valid_property_with_errors(self):
        """Test that valid is False when errors exist"""
        result = ValidationResult()
        result.errors.append("Some error")

        assert result.valid is False

    def test_valid_property_with_only_warnings(self):
        """Test that valid is True with only warnings"""
        result = ValidationResult()
        result.warnings.append("Some warning")

        assert result.valid is True

    def test_error_count_property(self):
        """Test error_count property"""
        result = ValidationResult()
        result.errors.append("Error 1")
        result.errors.append("Error 2")

        assert result.error_count == 2

    def test_warning_count_property(self):
        """Test warning_count property"""
        result = ValidationResult()
        result.warnings.append("Warning 1")
        result.warnings.append("Warning 2")
        result.warnings.append("Warning 3")

        assert result.warning_count == 3

    def test_add_error(self):
        """Test add_error method"""
        result = ValidationResult()
        result.add_error("Test error")

        assert "Test error" in result.errors
        assert result.error_count == 1

    def test_add_warning(self):
        """Test add_warning method"""
        result = ValidationResult()
        result.add_warning("Test warning")

        assert "Test warning" in result.warnings
        assert result.warning_count == 1

    def test_merge(self):
        """Test merge method combines results"""
        result1 = ValidationResult()
        result1.add_error("Error 1")
        result1.add_warning("Warning 1")

        result2 = ValidationResult()
        result2.add_error("Error 2")
        result2.add_warning("Warning 2")

        result1.merge(result2)

        assert result1.error_count == 2
        assert result1.warning_count == 2
        assert "Error 1" in result1.errors
        assert "Error 2" in result1.errors
        assert "Warning 1" in result1.warnings
        assert "Warning 2" in result1.warnings

    def test_to_dict(self):
        """Test to_dict serialization"""
        result = ValidationResult()
        result.add_error("Test error")
        result.add_warning("Test warning")
        result.entities_checked = 10
        result.entities_by_type = {"project": 5, "program": 3, "mission": 2}

        d = result.to_dict()

        assert d["valid"] is False
        assert d["errors"] == ["Test error"]
        assert d["warnings"] == ["Test warning"]
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        assert d["entities_checked"] == 10
        assert d["entities_by_type"] == {"project": 5, "program": 3, "mission": 2}

    def test_to_dict_valid_registry(self):
        """Test to_dict for valid registry"""
        result = ValidationResult()
        result.entities_checked = 5

        d = result.to_dict()

        assert d["valid"] is True
        assert d["errors"] == []
        assert d["warnings"] == []


class TestEntityValidationResult:
    """Tests for EntityValidationResult dataclass"""

    def test_default_values(self):
        """Test default values"""
        result = EntityValidationResult()

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.entity_data is None

    def test_add_error_marks_invalid(self):
        """Test that add_error marks result as invalid"""
        result = EntityValidationResult()
        assert result.valid is True

        result.add_error("Test error")

        assert result.valid is False
        assert "Test error" in result.errors

    def test_add_warning_keeps_valid(self):
        """Test that add_warning does not affect valid status"""
        result = EntityValidationResult()

        result.add_warning("Test warning")

        assert result.valid is True
        assert "Test warning" in result.warnings

    def test_to_dict(self):
        """Test to_dict serialization"""
        result = EntityValidationResult()
        result.add_error("Error")
        result.add_warning("Warning")

        d = result.to_dict()

        assert d["valid"] is False
        assert d["errors"] == ["Error"]
        assert d["warnings"] == ["Warning"]
        assert d["error_count"] == 1
        assert d["warning_count"] == 1

    def test_entity_data_stored(self):
        """Test that entity_data is stored"""
        entity = {"type": "project", "uid": "test-001", "title": "Test"}
        result = EntityValidationResult(entity_data=entity)

        assert result.entity_data == entity


class TestValidateOperationInit:
    """Tests for ValidateOperation initialization"""

    def test_init_stores_registry_path(self):
        """Test that __init__ stores registry path"""
        operation = ValidateOperation("/path/to/registry")

        assert operation.registry_path == "/path/to/registry"

    def test_required_fields_constant(self):
        """Test REQUIRED_FIELDS constant"""
        assert ValidateOperation.REQUIRED_FIELDS == ["type", "uid", "title"]


class TestValidateOperationFixtures:
    """Test fixtures for ValidateOperation tests"""

    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry structure"""
        temp_dir = tempfile.mkdtemp()
        registry_path = Path(temp_dir)

        # Create entity directories
        for entity_type in ["programs", "projects", "missions", "actions"]:
            (registry_path / entity_type).mkdir()

        # Create config file
        (registry_path / "config.yml").write_text("version: 1.0\n")

        yield str(registry_path)

        shutil.rmtree(temp_dir)

    @pytest.fixture
    def valid_entity(self):
        """Create a valid entity"""
        return {
            "type": "project",
            "uid": "proj-001",
            "title": "Test Project",
            "status": "active",
            "description": "A test project",
            "children": [],
            "related": [],
        }

    def create_entity_file(
        self, registry_path: str, entity_type: str, filename: str, data: Dict[str, Any]
    ) -> Path:
        """Helper to create an entity file"""
        folder_map = {
            "program": "programs",
            "project": "projects",
            "mission": "missions",
            "action": "actions",
        }

        folder = folder_map.get(entity_type, "projects")
        file_path = Path(registry_path) / folder / filename

        with open(file_path, "w") as f:
            yaml.dump(data, f)

        return file_path


class TestValidateRegistryMethod(TestValidateOperationFixtures):
    """Tests for validate_registry method"""

    def test_validate_empty_registry(self, temp_registry):
        """Test validation of empty registry returns valid"""
        operation = ValidateOperation(temp_registry)

        result = operation.validate_registry()

        assert result.valid is True
        assert result.entities_checked == 0
        assert result.error_count == 0

    def test_validate_valid_registry(self, temp_registry, valid_entity):
        """Test validation of valid registry"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True
        assert result.entities_checked == 1
        assert result.entities_by_type.get("project") == 1

    def test_validate_multiple_entity_types(self, temp_registry, valid_entity):
        """Test validation with multiple entity types"""
        # Create project
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        # Create program
        program = valid_entity.copy()
        program["type"] = "program"
        program["uid"] = "prog-001"
        self.create_entity_file(temp_registry, "program", "prog-001.yml", program)

        # Create mission
        mission = valid_entity.copy()
        mission["type"] = "mission"
        mission["uid"] = "miss-001"
        self.create_entity_file(temp_registry, "mission", "miss-001.yml", mission)

        # Create action
        action = valid_entity.copy()
        action["type"] = "action"
        action["uid"] = "act-001"
        self.create_entity_file(temp_registry, "action", "act-001.yml", action)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True
        assert result.entities_checked == 4
        assert result.entities_by_type.get("project") == 1
        assert result.entities_by_type.get("program") == 1
        assert result.entities_by_type.get("mission") == 1
        assert result.entities_by_type.get("action") == 1

    def test_validate_detects_missing_required_fields(self, temp_registry):
        """Test detection of missing required fields"""
        invalid_entity = {
            "type": "project",
            # Missing uid and title
            "status": "active",
        }

        self.create_entity_file(
            temp_registry, "project", "proj-invalid.yml", invalid_entity
        )

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("uid" in error.lower() for error in result.errors)
        assert any("title" in error.lower() for error in result.errors)

    def test_validate_detects_duplicate_uids(self, temp_registry, valid_entity):
        """Test detection of duplicate UIDs"""
        entity1 = valid_entity.copy()
        entity2 = valid_entity.copy()
        entity2["title"] = "Another Project"

        # Both have same UID
        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity1)
        self.create_entity_file(temp_registry, "project", "proj-002.yml", entity2)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Duplicate UID" in error for error in result.errors)
        assert any("proj-001" in error for error in result.errors)

    def test_validate_detects_duplicate_ids_within_type(self, temp_registry):
        """Test detection of duplicate IDs within same entity type"""
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

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity1)
        self.create_entity_file(temp_registry, "project", "proj-002.yml", entity2)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Duplicate ID" in error for error in result.errors)
        assert any("P-SAME" in error for error in result.errors)

    def test_validate_allows_duplicate_ids_across_types(self, temp_registry):
        """Test that same ID is allowed across different entity types"""
        project = {
            "type": "project",
            "uid": "proj-001",
            "id": "SHARED-ID",
            "title": "A Project",
            "status": "active",
        }
        program = {
            "type": "program",
            "uid": "prog-001",
            "id": "SHARED-ID",
            "title": "A Program",
            "status": "active",
        }

        self.create_entity_file(temp_registry, "project", "proj-001.yml", project)
        self.create_entity_file(temp_registry, "program", "prog-001.yml", program)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True

    def test_validate_detects_broken_parent_link(self, temp_registry, valid_entity):
        """Test detection of broken parent links"""
        entity = valid_entity.copy()
        entity["parent"] = "nonexistent-parent"

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Broken parent link" in error for error in result.errors)
        assert any("nonexistent-parent" in error for error in result.errors)

    def test_validate_detects_broken_child_link(self, temp_registry, valid_entity):
        """Test detection of broken child links"""
        entity = valid_entity.copy()
        entity["children"] = ["nonexistent-child"]

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Broken child link" in error for error in result.errors)

    def test_validate_broken_related_is_warning(self, temp_registry, valid_entity):
        """Test that broken related links are warnings not errors"""
        entity = valid_entity.copy()
        entity["related"] = ["nonexistent-related"]

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True  # Still valid
        assert any("Broken related link" in warning for warning in result.warnings)

    def test_validate_detects_invalid_status(self, temp_registry, valid_entity):
        """Test detection of invalid status values"""
        entity = valid_entity.copy()
        entity["status"] = "invalid-status"

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Invalid status" in error for error in result.errors)

    def test_validate_detects_type_mismatch(self, temp_registry, valid_entity):
        """Test detection of type mismatches"""
        # Entity in projects folder but declares type as program
        entity = valid_entity.copy()
        entity["type"] = "program"

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Type mismatch" in error for error in result.errors)

    def test_validate_detects_empty_file(self, temp_registry):
        """Test handling of empty YAML files"""
        file_path = Path(temp_registry) / "projects" / "empty.yml"
        file_path.write_text("")

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Empty file" in error for error in result.errors)

    def test_validate_detects_invalid_yaml(self, temp_registry):
        """Test handling of invalid YAML files"""
        file_path = Path(temp_registry) / "projects" / "invalid.yml"
        file_path.write_text("invalid: yaml: content: [")

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any(
            "YAML parse error" in error or "Error loading" in error
            for error in result.errors
        )

    def test_validate_valid_parent_child_relationship(self, temp_registry, valid_entity):
        """Test validation with valid parent-child relationships"""
        parent = valid_entity.copy()
        parent["uid"] = "prog-001"
        parent["type"] = "program"
        parent["children"] = ["proj-001"]

        child = valid_entity.copy()
        child["uid"] = "proj-001"
        child["parent"] = "prog-001"

        self.create_entity_file(temp_registry, "program", "prog-001.yml", parent)
        self.create_entity_file(temp_registry, "project", "proj-001.yml", child)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True
        assert result.error_count == 0

    def test_validate_invalid_children_format(self, temp_registry, valid_entity):
        """Test detection of invalid children format"""
        entity = valid_entity.copy()
        entity["children"] = "not-a-list"

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Invalid children format" in error for error in result.errors)

    def test_validate_invalid_related_format_is_warning(
        self, temp_registry, valid_entity
    ):
        """Test that invalid related format is a warning"""
        entity = valid_entity.copy()
        entity["related"] = "not-a-list"

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True
        assert any("Invalid related format" in warning for warning in result.warnings)


class TestValidateEntityMethod(TestValidateOperationFixtures):
    """Tests for validate_entity method"""

    def test_validate_valid_entity(self, temp_registry, valid_entity):
        """Test validation of valid entity"""
        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(valid_entity, check_relationships=False)

        assert result.valid is True
        assert result.errors == []

    def test_validate_missing_required_fields(self, temp_registry):
        """Test validation detects missing required fields"""
        invalid_entity = {"status": "active"}

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(invalid_entity, check_relationships=False)

        assert result.valid is False
        assert any("type" in error.lower() for error in result.errors)
        assert any("uid" in error.lower() for error in result.errors)
        assert any("title" in error.lower() for error in result.errors)

    def test_validate_invalid_entity_type(self, temp_registry, valid_entity):
        """Test validation detects invalid entity type"""
        entity = valid_entity.copy()
        entity["type"] = "invalid_type"

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=False)

        assert result.valid is False
        assert any("Invalid entity type" in error for error in result.errors)

    def test_validate_invalid_status(self, temp_registry, valid_entity):
        """Test validation detects invalid status"""
        entity = valid_entity.copy()
        entity["status"] = "invalid_status"

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=False)

        assert result.valid is False
        assert any("Invalid status" in error for error in result.errors)

    def test_validate_invalid_children_format(self, temp_registry, valid_entity):
        """Test validation detects invalid children format"""
        entity = valid_entity.copy()
        entity["children"] = "not-a-list"

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=False)

        assert result.valid is False
        assert any("Invalid children format" in error for error in result.errors)

    def test_validate_invalid_related_format_is_warning(
        self, temp_registry, valid_entity
    ):
        """Test validation warns on invalid related format"""
        entity = valid_entity.copy()
        entity["related"] = "not-a-list"

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=False)

        assert result.valid is True
        assert any("Invalid related format" in warning for warning in result.warnings)

    def test_validate_with_relationship_checking(self, temp_registry, valid_entity):
        """Test validation with relationship checking enabled"""
        # Create parent entity
        parent = valid_entity.copy()
        parent["uid"] = "parent-001"
        parent["type"] = "program"
        self.create_entity_file(temp_registry, "program", "prog-001.yml", parent)

        # Validate entity with existing parent
        entity = valid_entity.copy()
        entity["parent"] = "parent-001"

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=True)

        assert result.valid is True

    def test_validate_with_nonexistent_parent(self, temp_registry, valid_entity):
        """Test validation detects nonexistent parent"""
        entity = valid_entity.copy()
        entity["parent"] = "nonexistent-parent"

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=True)

        assert result.valid is False
        assert any("Parent" in error and "not found" in error for error in result.errors)

    def test_validate_with_nonexistent_children(self, temp_registry, valid_entity):
        """Test validation detects nonexistent children"""
        entity = valid_entity.copy()
        entity["children"] = ["nonexistent-child"]

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=True)

        assert result.valid is False
        assert any("Child" in error and "not found" in error for error in result.errors)

    def test_validate_with_nonexistent_related_is_warning(
        self, temp_registry, valid_entity
    ):
        """Test validation warns on nonexistent related"""
        entity = valid_entity.copy()
        entity["related"] = ["nonexistent-related"]

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=True)

        assert result.valid is True
        assert any(
            "Related" in warning and "not found" in warning
            for warning in result.warnings
        )

    def test_validate_stores_entity_data(self, temp_registry, valid_entity):
        """Test that entity_data is stored in result"""
        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(valid_entity, check_relationships=False)

        assert result.entity_data == valid_entity


class TestCheckUidUnique(TestValidateOperationFixtures):
    """Tests for check_uid_unique method"""

    def test_uid_unique_in_empty_registry(self, temp_registry):
        """Test UID is unique in empty registry"""
        operation = ValidateOperation(temp_registry)

        assert operation.check_uid_unique("new-uid") is True

    def test_uid_not_unique(self, temp_registry, valid_entity):
        """Test UID not unique when exists"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        operation = ValidateOperation(temp_registry)

        assert operation.check_uid_unique("proj-001") is False

    def test_uid_unique_different_uid(self, temp_registry, valid_entity):
        """Test different UID is unique"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        operation = ValidateOperation(temp_registry)

        assert operation.check_uid_unique("different-uid") is True

    def test_uid_unique_with_exclude_file(self, temp_registry, valid_entity):
        """Test UID uniqueness with file exclusion for edits"""
        file_path = self.create_entity_file(
            temp_registry, "project", "proj-001.yml", valid_entity
        )

        operation = ValidateOperation(temp_registry)

        # Same UID but excluded file
        assert operation.check_uid_unique("proj-001", exclude_file=str(file_path)) is True

    def test_uid_unique_across_entity_types(self, temp_registry, valid_entity):
        """Test UID uniqueness across entity types"""
        # Create project with UID
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        # Create program with same UID
        program = valid_entity.copy()
        program["type"] = "program"
        self.create_entity_file(temp_registry, "program", "prog-001.yml", program)

        operation = ValidateOperation(temp_registry)

        # UID should not be unique (exists in both)
        assert operation.check_uid_unique("proj-001") is False


class TestCheckIdUnique(TestValidateOperationFixtures):
    """Tests for check_id_unique method"""

    def test_id_unique_in_empty_registry(self, temp_registry):
        """Test ID is unique in empty registry"""
        operation = ValidateOperation(temp_registry)

        assert operation.check_id_unique("P-001", EntityType.PROJECT) is True

    def test_id_not_unique_within_type(self, temp_registry):
        """Test ID not unique within same entity type"""
        entity = {
            "type": "project",
            "uid": "proj-001",
            "id": "P-001",
            "title": "Test",
            "status": "active",
        }
        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)

        assert operation.check_id_unique("P-001", EntityType.PROJECT) is False

    def test_id_unique_in_different_type(self, temp_registry):
        """Test ID is unique in different entity type"""
        entity = {
            "type": "project",
            "uid": "proj-001",
            "id": "P-001",
            "title": "Test",
            "status": "active",
        }
        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)

        # Same ID but different type
        assert operation.check_id_unique("P-001", EntityType.PROGRAM) is True

    def test_id_unique_with_exclude_file(self, temp_registry):
        """Test ID uniqueness with file exclusion for edits"""
        entity = {
            "type": "project",
            "uid": "proj-001",
            "id": "P-001",
            "title": "Test",
            "status": "active",
        }
        file_path = self.create_entity_file(
            temp_registry, "project", "proj-001.yml", entity
        )

        operation = ValidateOperation(temp_registry)

        # Same ID but excluded file
        assert (
            operation.check_id_unique("P-001", EntityType.PROJECT, exclude_file=str(file_path))
            is True
        )


class TestGetAllUids(TestValidateOperationFixtures):
    """Tests for get_all_uids method"""

    def test_empty_registry(self, temp_registry):
        """Test get_all_uids on empty registry"""
        operation = ValidateOperation(temp_registry)

        uids = operation.get_all_uids()

        assert uids == set()

    def test_single_entity(self, temp_registry, valid_entity):
        """Test get_all_uids with single entity"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        operation = ValidateOperation(temp_registry)

        uids = operation.get_all_uids()

        assert uids == {"proj-001"}

    def test_multiple_entities(self, temp_registry, valid_entity):
        """Test get_all_uids with multiple entities"""
        entity1 = valid_entity.copy()
        entity1["uid"] = "proj-001"
        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity1)

        entity2 = valid_entity.copy()
        entity2["uid"] = "proj-002"
        self.create_entity_file(temp_registry, "project", "proj-002.yml", entity2)

        program = valid_entity.copy()
        program["type"] = "program"
        program["uid"] = "prog-001"
        self.create_entity_file(temp_registry, "program", "prog-001.yml", program)

        operation = ValidateOperation(temp_registry)

        uids = operation.get_all_uids()

        assert uids == {"proj-001", "proj-002", "prog-001"}


class TestValidateOperationStatusValues(TestValidateOperationFixtures):
    """Tests for status value validation"""

    @pytest.mark.parametrize(
        "status",
        ["active", "completed", "on-hold", "cancelled", "planned"],
    )
    def test_valid_statuses(self, temp_registry, valid_entity, status):
        """Test all valid status values"""
        entity = valid_entity.copy()
        entity["status"] = status

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True

    def test_invalid_status(self, temp_registry, valid_entity):
        """Test invalid status value"""
        entity = valid_entity.copy()
        entity["status"] = "not-a-valid-status"

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("not-a-valid-status" in error for error in result.errors)


class TestValidateOperationEntityTypes(TestValidateOperationFixtures):
    """Tests for entity type validation"""

    @pytest.mark.parametrize(
        "entity_type,folder",
        [
            ("program", "program"),
            ("project", "project"),
            ("mission", "mission"),
            ("action", "action"),
        ],
    )
    def test_valid_type_in_correct_folder(
        self, temp_registry, valid_entity, entity_type, folder
    ):
        """Test valid entity types in correct folders"""
        entity = valid_entity.copy()
        entity["type"] = entity_type
        entity["uid"] = f"{entity_type}-001"

        self.create_entity_file(temp_registry, folder, f"{entity_type}-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True

    def test_invalid_entity_type(self, temp_registry, valid_entity):
        """Test invalid entity type"""
        entity = valid_entity.copy()
        entity["type"] = "invalid_type"

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert any("Invalid entity type" in error for error in result.errors)


class TestValidateOperationVerboseMode(TestValidateOperationFixtures):
    """Tests for verbose mode in validate_registry"""

    def test_verbose_parameter_accepted(self, temp_registry, valid_entity):
        """Test that verbose parameter is accepted"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        operation = ValidateOperation(temp_registry)

        # Should not raise
        result = operation.validate_registry(verbose=True)

        assert result.valid is True

    def test_verbose_false_default(self, temp_registry, valid_entity):
        """Test that verbose defaults to False"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        operation = ValidateOperation(temp_registry)

        # Should not raise with default verbose=False
        result = operation.validate_registry()

        assert result.valid is True


class TestValidateOperationPathSecurity(TestValidateOperationFixtures):
    """Tests for path security in validation"""

    def test_handles_path_security_error_gracefully(self, temp_registry):
        """Test that path security errors are handled gracefully"""
        operation = ValidateOperation(temp_registry)

        # Create a file with potentially dangerous path (will be caught by security)
        # The operation should handle this without crashing
        result = operation.validate_registry()

        # Should complete without raising
        assert isinstance(result, ValidationResult)


class TestValidateOperationIntegration(TestValidateOperationFixtures):
    """Integration tests for ValidateOperation"""

    def test_multiple_errors_all_reported(self, temp_registry):
        """Test that multiple errors are all reported"""
        # Entity with multiple issues
        problematic_entity = {
            "type": "program",  # Type mismatch (in projects folder)
            # Missing uid and title
            "status": "invalid-status",
            "parent": "nonexistent-parent",
            "children": ["nonexistent-child"],
        }

        self.create_entity_file(
            temp_registry, "project", "proj-001.yml", problematic_entity
        )

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False
        assert result.error_count >= 4  # At least 4 errors expected

    def test_errors_and_warnings_together(self, temp_registry, valid_entity):
        """Test that both errors and warnings can exist"""
        entity = valid_entity.copy()
        entity["parent"] = "nonexistent-parent"  # Error
        entity["related"] = ["nonexistent-related"]  # Warning

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is False  # Has errors
        assert result.error_count >= 1
        assert result.warning_count >= 1

    def test_validation_result_to_dict_complete(self, temp_registry, valid_entity):
        """Test that to_dict returns complete information"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        d = result.to_dict()

        # All expected keys present
        assert "valid" in d
        assert "errors" in d
        assert "warnings" in d
        assert "error_count" in d
        assert "warning_count" in d
        assert "entities_checked" in d
        assert "entities_by_type" in d

        # Correct types
        assert isinstance(d["valid"], bool)
        assert isinstance(d["errors"], list)
        assert isinstance(d["warnings"], list)
        assert isinstance(d["error_count"], int)
        assert isinstance(d["warning_count"], int)
        assert isinstance(d["entities_checked"], int)
        assert isinstance(d["entities_by_type"], dict)


class TestValidateOperationEdgeCases(TestValidateOperationFixtures):
    """Edge case tests for ValidateOperation"""

    def test_entity_without_optional_fields(self, temp_registry):
        """Test validation of entity with only required fields"""
        minimal_entity = {
            "type": "project",
            "uid": "proj-001",
            "title": "Minimal Project",
        }

        self.create_entity_file(
            temp_registry, "project", "proj-001.yml", minimal_entity
        )

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True

    def test_entity_with_null_optional_fields(self, temp_registry):
        """Test validation of entity with null optional fields"""
        entity = {
            "type": "project",
            "uid": "proj-001",
            "title": "Project with nulls",
            "status": "active",
            "description": None,
            "parent": None,
            "children": [],
            "related": [],
        }

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True

    def test_entity_with_empty_lists(self, temp_registry, valid_entity):
        """Test validation with empty children and related lists"""
        entity = valid_entity.copy()
        entity["children"] = []
        entity["related"] = []

        self.create_entity_file(temp_registry, "project", "proj-001.yml", entity)

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True

    def test_validate_entity_empty_data(self, temp_registry):
        """Test validate_entity with empty data"""
        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity({}, check_relationships=False)

        assert result.valid is False
        assert len(result.errors) >= 3  # Missing type, uid, title

    def test_validate_entity_none_values(self, temp_registry):
        """Test validate_entity with None values for required fields"""
        entity = {
            "type": None,
            "uid": None,
            "title": None,
        }

        operation = ValidateOperation(temp_registry)
        result = operation.validate_entity(entity, check_relationships=False)

        assert result.valid is False

    def test_nonexistent_registry_directory(self):
        """Test validation with nonexistent registry path"""
        operation = ValidateOperation("/nonexistent/path/to/registry")
        result = operation.validate_registry()

        # Should complete without crashing, with 0 entities
        assert result.entities_checked == 0

    def test_registry_with_extra_files(self, temp_registry, valid_entity):
        """Test that extra non-YAML files are ignored"""
        self.create_entity_file(temp_registry, "project", "proj-001.yml", valid_entity)

        # Add a non-YAML file
        extra_file = Path(temp_registry) / "projects" / "readme.txt"
        extra_file.write_text("This is not a YAML file")

        operation = ValidateOperation(temp_registry)
        result = operation.validate_registry()

        assert result.valid is True
        assert result.entities_checked == 1  # Only YAML file counted