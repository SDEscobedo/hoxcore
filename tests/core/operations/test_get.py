"""
Tests for the GetPropertyOperation class.

This module tests the shared get property operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools.
"""

import shutil
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityType
from hxc.core.operations.get import (
    GetPropertyOperation,
    GetPropertyOperationError,
    IndexOutOfRangeError,
    InvalidKeyFilterError,
    KeyFilterNoMatchError,
    PropertyNotSetError,
    PropertyType,
    UnknownPropertyError,
)
from hxc.core.operations.show import ShowOperation
from hxc.utils.path_security import PathSecurityError


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
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
    _create_sample_project_basic(
        registry_path / "projects", "proj-001", "Test Project 1", "P-001"
    )
    _create_sample_project_full(
        registry_path / "projects", "proj-002", "Test Project 2", "P-002"
    )
    _create_sample_program(
        registry_path / "programs", "prog-001", "Test Program 1", "PG-001"
    )
    _create_sample_mission(
        registry_path / "missions", "miss-001", "Test Mission 1", "M-001"
    )
    _create_sample_action(
        registry_path / "actions", "act-001", "Test Action 1", "A-001"
    )

    yield str(registry_path)

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


def _create_sample_project_basic(
    directory: Path, filename: str, title: str, item_id: str
):
    """Create a basic sample project file"""
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": filename,
        "status": "active",
        "description": f"Description for {title}",
        "start_date": "2024-01-01",
        "tags": ["test", "sample"],
    }

    filepath = directory / f"proj-{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(project_data, f)


def _create_sample_project_full(
    directory: Path, filename: str, title: str, item_id: str
):
    """Create a full sample project file with all properties"""
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": filename,
        "status": "completed",
        "description": f"Full description for {title}",
        "start_date": "2024-01-01",
        "due_date": "2024-12-31",
        "completion_date": "2024-11-30",
        "duration_estimate": "6 months",
        "category": "software.dev/cli-tool",
        "tags": ["cli", "test", "important"],
        "parent": "PG-001",
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

    filepath = directory / f"proj-{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(project_data, f)


def _create_sample_program(directory: Path, filename: str, title: str, item_id: str):
    """Create a sample program file"""
    program_data = {
        "type": "program",
        "title": title,
        "id": item_id,
        "uid": filename,
        "status": "active",
        "description": f"Description for {title}",
        "children": ["P-001", "P-002"],
    }

    filepath = directory / f"prog-{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(program_data, f)


def _create_sample_mission(directory: Path, filename: str, title: str, item_id: str):
    """Create a sample mission file"""
    mission_data = {
        "type": "mission",
        "title": title,
        "id": item_id,
        "uid": filename,
        "status": "active",
        "description": f"Description for {title}",
        "parent": "PG-001",
    }

    filepath = directory / f"miss-{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(mission_data, f)


def _create_sample_action(directory: Path, filename: str, title: str, item_id: str):
    """Create a sample action file"""
    action_data = {
        "type": "action",
        "title": title,
        "id": item_id,
        "uid": filename,
        "status": "active",
        "description": f"Description for {title}",
        "tags": ["recurring"],
    }

    filepath = directory / f"act-{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(action_data, f)


class TestPropertyClassification:
    """Tests for property classification constants"""

    def test_scalar_properties_defined(self):
        """Test that scalar properties are defined correctly"""
        expected_scalar = {
            "type",
            "uid",
            "id",
            "title",
            "description",
            "status",
            "start_date",
            "due_date",
            "completion_date",
            "duration_estimate",
            "category",
            "parent",
            "template",
        }
        assert GetPropertyOperation.SCALAR_PROPERTIES == expected_scalar

    def test_list_properties_defined(self):
        """Test that list properties are defined correctly"""
        expected_list = {"tags", "children", "related"}
        assert GetPropertyOperation.LIST_PROPERTIES == expected_list

    def test_complex_properties_defined(self):
        """Test that complex properties are defined correctly"""
        expected_complex = {
            "repositories",
            "storage",
            "databases",
            "tools",
            "models",
            "knowledge_bases",
        }
        assert GetPropertyOperation.COMPLEX_PROPERTIES == expected_complex

    def test_special_properties_defined(self):
        """Test that special properties are defined correctly"""
        expected_special = {"all", "path"}
        assert GetPropertyOperation.SPECIAL_PROPERTIES == expected_special

    def test_all_properties_is_union_of_all_sets(self):
        """Test that ALL_PROPERTIES contains all property sets"""
        expected_all = (
            GetPropertyOperation.SCALAR_PROPERTIES
            | GetPropertyOperation.LIST_PROPERTIES
            | GetPropertyOperation.COMPLEX_PROPERTIES
            | GetPropertyOperation.SPECIAL_PROPERTIES
        )
        assert GetPropertyOperation.ALL_PROPERTIES == expected_all

    def test_property_sets_are_disjoint(self):
        """Test that property sets don't overlap"""
        sets = [
            GetPropertyOperation.SCALAR_PROPERTIES,
            GetPropertyOperation.LIST_PROPERTIES,
            GetPropertyOperation.COMPLEX_PROPERTIES,
            GetPropertyOperation.SPECIAL_PROPERTIES,
        ]
        for i, s1 in enumerate(sets):
            for j, s2 in enumerate(sets):
                if i != j:
                    assert s1.isdisjoint(s2), f"Sets {i} and {j} overlap"


class TestPropertyType:
    """Tests for PropertyType constants"""

    def test_property_type_constants(self):
        """Test that PropertyType constants are defined"""
        assert PropertyType.SCALAR == "scalar"
        assert PropertyType.LIST == "list"
        assert PropertyType.COMPLEX == "complex"
        assert PropertyType.SPECIAL == "special"


class TestGetPropertyType:
    """Tests for get_property_type class method"""

    def test_scalar_property_types(self):
        """Test detection of scalar properties"""
        scalar_props = ["type", "uid", "id", "title", "description", "status"]
        for prop in scalar_props:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.SCALAR

    def test_list_property_types(self):
        """Test detection of list properties"""
        list_props = ["tags", "children", "related"]
        for prop in list_props:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.LIST

    def test_complex_property_types(self):
        """Test detection of complex properties"""
        complex_props = [
            "repositories",
            "storage",
            "databases",
            "tools",
            "models",
            "knowledge_bases",
        ]
        for prop in complex_props:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.COMPLEX

    def test_special_property_types(self):
        """Test detection of special properties"""
        special_props = ["all", "path"]
        for prop in special_props:
            assert GetPropertyOperation.get_property_type(prop) == PropertyType.SPECIAL

    def test_unknown_property_returns_none(self):
        """Test that unknown properties return None"""
        assert GetPropertyOperation.get_property_type("unknown") is None
        assert GetPropertyOperation.get_property_type("nonexistent") is None
        assert GetPropertyOperation.get_property_type("") is None


class TestValidatePropertyName:
    """Tests for validate_property_name class method"""

    def test_valid_property_names(self):
        """Test validation of valid property names"""
        valid_props = ["title", "status", "tags", "repositories", "all", "path"]
        for prop in valid_props:
            is_valid, normalized = GetPropertyOperation.validate_property_name(prop)
            assert is_valid is True
            assert normalized == prop.lower()

    def test_case_insensitive_validation(self):
        """Test that validation is case-insensitive"""
        test_cases = [
            ("TITLE", "title"),
            ("Title", "title"),
            ("STATUS", "status"),
            ("Tags", "tags"),
            ("REPOSITORIES", "repositories"),
        ]
        for input_prop, expected_normalized in test_cases:
            is_valid, normalized = GetPropertyOperation.validate_property_name(
                input_prop
            )
            assert is_valid is True
            assert normalized == expected_normalized

    def test_invalid_property_names(self):
        """Test validation of invalid property names"""
        invalid_props = ["unknown", "nonexistent", "foo", "bar", ""]
        for prop in invalid_props:
            is_valid, normalized = GetPropertyOperation.validate_property_name(prop)
            assert is_valid is False
            assert normalized is None


class TestGetAvailableProperties:
    """Tests for get_available_properties class method"""

    def test_returns_sorted_list(self):
        """Test that available properties are returned sorted"""
        props = GetPropertyOperation.get_available_properties()
        assert props == sorted(props)

    def test_contains_all_properties(self):
        """Test that all known properties are returned"""
        props = GetPropertyOperation.get_available_properties()
        for prop in GetPropertyOperation.ALL_PROPERTIES:
            assert prop in props

    def test_returns_list(self):
        """Test that a list is returned"""
        props = GetPropertyOperation.get_available_properties()
        assert isinstance(props, list)


class TestGetPropertiesByType:
    """Tests for get_properties_by_type class method"""

    def test_returns_dict_with_all_types(self):
        """Test that dict contains all property types"""
        by_type = GetPropertyOperation.get_properties_by_type()
        assert PropertyType.SCALAR in by_type
        assert PropertyType.LIST in by_type
        assert PropertyType.COMPLEX in by_type
        assert PropertyType.SPECIAL in by_type

    def test_scalar_properties_sorted(self):
        """Test that scalar properties are sorted"""
        by_type = GetPropertyOperation.get_properties_by_type()
        scalar = by_type[PropertyType.SCALAR]
        assert scalar == sorted(scalar)

    def test_list_properties_sorted(self):
        """Test that list properties are sorted"""
        by_type = GetPropertyOperation.get_properties_by_type()
        list_props = by_type[PropertyType.LIST]
        assert list_props == sorted(list_props)

    def test_complex_properties_sorted(self):
        """Test that complex properties are sorted"""
        by_type = GetPropertyOperation.get_properties_by_type()
        complex_props = by_type[PropertyType.COMPLEX]
        assert complex_props == sorted(complex_props)

    def test_special_properties_sorted(self):
        """Test that special properties are sorted"""
        by_type = GetPropertyOperation.get_properties_by_type()
        special = by_type[PropertyType.SPECIAL]
        assert special == sorted(special)


class TestGetPropertyOperationInit:
    """Tests for GetPropertyOperation initialization"""

    def test_init_with_registry_path(self, temp_registry):
        """Test initialization with a valid registry path"""
        operation = GetPropertyOperation(temp_registry)
        assert operation.registry_path == temp_registry

    def test_init_creates_show_operation(self, temp_registry):
        """Test that initialization creates ShowOperation"""
        operation = GetPropertyOperation(temp_registry)
        assert operation._show_operation is not None
        assert isinstance(operation._show_operation, ShowOperation)


class TestGetEntity:
    """Tests for get_entity method"""

    def test_get_entity_by_id(self, temp_registry):
        """Test getting entity by ID"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_entity("P-001")

        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"

    def test_get_entity_by_uid(self, temp_registry):
        """Test getting entity by UID"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_entity("proj-001")

        assert result["success"] is True
        assert result["entity"]["uid"] == "proj-001"

    def test_get_entity_with_type_filter(self, temp_registry):
        """Test getting entity with type filter"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_entity("P-001", entity_type=EntityType.PROJECT)

        assert result["success"] is True
        assert result["entity"]["type"] == "project"

    def test_get_entity_not_found(self, temp_registry):
        """Test getting non-existent entity"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_entity("NONEXISTENT")

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestGetScalarProperty:
    """Tests for getting scalar properties"""

    def test_get_title(self, temp_registry):
        """Test getting title property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "title")

        assert result["success"] is True
        assert result["value"] == "Test Project 1"
        assert result["property"] == "title"
        assert result["property_type"] == PropertyType.SCALAR

    def test_get_status(self, temp_registry):
        """Test getting status property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "status")

        assert result["success"] is True
        assert result["value"] == "completed"

    def test_get_description(self, temp_registry):
        """Test getting description property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "description")

        assert result["success"] is True
        assert "Description for" in result["value"]

    def test_get_type(self, temp_registry):
        """Test getting type property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "type")

        assert result["success"] is True
        assert result["value"] == "project"

    def test_get_uid(self, temp_registry):
        """Test getting uid property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "uid")

        assert result["success"] is True
        assert result["value"] == "proj-001"

    def test_get_start_date(self, temp_registry):
        """Test getting start_date property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "start_date")

        assert result["success"] is True
        assert result["value"] == "2024-01-01"

    def test_get_due_date(self, temp_registry):
        """Test getting due_date property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "due_date")

        assert result["success"] is True
        assert result["value"] == "2024-12-31"

    def test_get_category(self, temp_registry):
        """Test getting category property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "category")

        assert result["success"] is True
        assert result["value"] == "software.dev/cli-tool"

    def test_get_parent(self, temp_registry):
        """Test getting parent property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "parent")

        assert result["success"] is True
        assert result["value"] == "PG-001"


class TestGetListProperty:
    """Tests for getting list properties"""

    def test_get_tags(self, temp_registry):
        """Test getting tags property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "tags")

        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert "test" in result["value"]
        assert result["property_type"] == PropertyType.LIST

    def test_get_children(self, temp_registry):
        """Test getting children property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("PG-001", "children")

        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert "P-001" in result["value"]

    def test_get_related(self, temp_registry):
        """Test getting related property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "related")

        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert "P-005" in result["value"]

    def test_get_list_with_index(self, temp_registry):
        """Test getting list property with index"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "tags", index=0)

        assert result["success"] is True
        assert isinstance(result["value"], str)
        assert result["value"] == "cli"

    def test_get_list_with_last_index(self, temp_registry):
        """Test getting list property with last valid index"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "tags", index=2)

        assert result["success"] is True
        assert isinstance(result["value"], str)
        assert result["value"] == "important"

    def test_get_list_invalid_index(self, temp_registry):
        """Test getting list property with invalid index"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "tags", index=99)

        assert result["success"] is False
        assert "out of range" in result["error"].lower()


class TestGetComplexProperty:
    """Tests for getting complex properties"""

    def test_get_repositories(self, temp_registry):
        """Test getting repositories property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "repositories")

        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert len(result["value"]) == 2
        assert result["property_type"] == PropertyType.COMPLEX

    def test_get_storage(self, temp_registry):
        """Test getting storage property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "storage")

        assert result["success"] is True
        assert isinstance(result["value"], list)

    def test_get_databases(self, temp_registry):
        """Test getting databases property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "databases")

        assert result["success"] is True
        assert isinstance(result["value"], list)

    def test_get_tools(self, temp_registry):
        """Test getting tools property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "tools")

        assert result["success"] is True
        assert isinstance(result["value"], list)

    def test_get_models(self, temp_registry):
        """Test getting models property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "models")

        assert result["success"] is True
        assert isinstance(result["value"], list)

    def test_get_knowledge_bases(self, temp_registry):
        """Test getting knowledge_bases property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "knowledge_bases")

        assert result["success"] is True
        assert isinstance(result["value"], list)

    def test_get_complex_with_index(self, temp_registry):
        """Test getting complex property with index"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-002", "repositories", index=0)

        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert result["value"]["name"] == "github"

    def test_get_complex_with_key_filter(self, temp_registry):
        """Test getting complex property with key filter"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property(
            "P-002", "repositories", key_filter="name:github"
        )

        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert result["value"]["name"] == "github"

    def test_get_complex_key_filter_single_match(self, temp_registry):
        """Test key filter returning single match"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property(
            "P-002", "repositories", key_filter="name:gitlab"
        )

        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert result["value"]["name"] == "gitlab"


class TestGetSpecialProperty:
    """Tests for getting special properties"""

    def test_get_all(self, temp_registry):
        """Test getting 'all' special property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "all")

        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert "type" in result["value"]
        assert "title" in result["value"]
        assert "uid" in result["value"]
        assert result["property_type"] == PropertyType.SPECIAL

    def test_get_path(self, temp_registry):
        """Test getting 'path' special property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "path")

        assert result["success"] is True
        assert isinstance(result["value"], str)
        assert "proj-proj-001.yml" in result["value"]
        assert result["property_type"] == PropertyType.SPECIAL


class TestPropertyNotSet:
    """Tests for handling unset properties"""

    def test_unset_scalar_property(self, temp_registry):
        """Test getting an unset scalar property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "due_date")

        assert result["success"] is False
        assert "not set" in result["error"].lower()

    def test_unset_list_property(self, temp_registry):
        """Test getting an unset list property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "children")

        assert result["success"] is False
        assert "not set" in result["error"].lower()

    def test_unset_complex_property(self, temp_registry):
        """Test getting an unset complex property"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "repositories")

        assert result["success"] is False
        assert "not set" in result["error"].lower()


class TestUnknownProperty:
    """Tests for handling unknown properties"""

    def test_unknown_property_error(self, temp_registry):
        """Test getting an unknown property returns error"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "unknown_property")

        assert result["success"] is False
        assert "unknown property" in result["error"].lower()
        assert "available_properties" in result

    def test_unknown_property_includes_available(self, temp_registry):
        """Test that unknown property error includes available properties"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "nonexistent")

        assert result["success"] is False
        assert "available_properties" in result
        assert isinstance(result["available_properties"], list)
        assert "title" in result["available_properties"]

    def test_unknown_property_message_format(self, temp_registry):
        """Test unknown property error message format"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "foobar")

        assert result["success"] is False
        assert "foobar" in result["error"]


class TestEntityNotFound:
    """Tests for handling entity not found"""

    def test_entity_not_found(self, temp_registry):
        """Test getting property from non-existent entity"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("NONEXISTENT", "title")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_entity_not_found_with_type_filter(self, temp_registry):
        """Test getting property with wrong entity type"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property(
            "P-001", "title", entity_type=EntityType.PROGRAM
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestIndexFilter:
    """Tests for index filtering"""

    def test_apply_index_filter_valid(self, temp_registry):
        """Test applying valid index filter"""
        operation = GetPropertyOperation(temp_registry)
        value = ["a", "b", "c"]
        result, error = operation._apply_index_filter(value, 1, "test")

        assert error is None
        assert result == "b"

    def test_apply_index_filter_zero(self, temp_registry):
        """Test applying index 0"""
        operation = GetPropertyOperation(temp_registry)
        value = ["first", "second"]
        result, error = operation._apply_index_filter(value, 0, "test")

        assert error is None
        assert result == "first"

    def test_apply_index_filter_last(self, temp_registry):
        """Test applying last index"""
        operation = GetPropertyOperation(temp_registry)
        value = ["a", "b", "c"]
        result, error = operation._apply_index_filter(value, 2, "test")

        assert error is None
        assert result == "c"

    def test_apply_index_filter_out_of_range(self, temp_registry):
        """Test applying out of range index"""
        operation = GetPropertyOperation(temp_registry)
        value = ["a", "b"]
        result, error = operation._apply_index_filter(value, 5, "test")

        assert error is not None
        assert "out of range" in error.lower()
        assert result is None

    def test_apply_index_filter_none(self, temp_registry):
        """Test applying None index returns original value"""
        operation = GetPropertyOperation(temp_registry)
        value = ["a", "b", "c"]
        result, error = operation._apply_index_filter(value, None, "test")

        assert error is None
        assert result == value

    def test_apply_index_filter_negative(self, temp_registry):
        """Test that negative index is out of range"""
        operation = GetPropertyOperation(temp_registry)
        value = ["a", "b", "c"]
        result, error = operation._apply_index_filter(value, -1, "test")

        assert error is not None
        assert "out of range" in error.lower()

    def test_apply_index_filter_empty_list(self, temp_registry):
        """Test applying index to empty list"""
        operation = GetPropertyOperation(temp_registry)
        value = []
        result, error = operation._apply_index_filter(value, 0, "test")

        assert error is not None
        assert "out of range" in error.lower()


class TestKeyFilter:
    """Tests for key filter"""

    def test_apply_key_filter_valid(self, temp_registry):
        """Test applying valid key filter"""
        operation = GetPropertyOperation(temp_registry)
        value = [
            {"name": "github", "url": "https://github.com"},
            {"name": "gitlab", "url": "https://gitlab.com"},
        ]
        result, error = operation._apply_key_filter(value, "name:github", "test")

        assert error is None
        assert isinstance(result, dict)
        assert result["name"] == "github"

    def test_apply_key_filter_invalid_format(self, temp_registry):
        """Test applying invalid key filter format"""
        operation = GetPropertyOperation(temp_registry)
        value = [{"name": "test"}]
        result, error = operation._apply_key_filter(value, "invalid", "test")

        assert error is not None
        assert "invalid key filter" in error.lower()

    def test_apply_key_filter_no_match(self, temp_registry):
        """Test applying key filter with no match"""
        operation = GetPropertyOperation(temp_registry)
        value = [{"name": "github"}, {"name": "gitlab"}]
        result, error = operation._apply_key_filter(value, "name:bitbucket", "test")

        assert error is not None
        assert "no items found" in error.lower()

    def test_apply_key_filter_with_colon_in_value(self, temp_registry):
        """Test applying key filter with colon in value"""
        operation = GetPropertyOperation(temp_registry)
        value = [{"url": "https://example.com:8080"}]
        result, error = operation._apply_key_filter(
            value, "url:https://example.com:8080", "test"
        )

        assert error is None
        assert result["url"] == "https://example.com:8080"

    def test_apply_key_filter_multiple_matches(self, temp_registry):
        """Test key filter with multiple matches returns list"""
        operation = GetPropertyOperation(temp_registry)
        value = [
            {"type": "git", "name": "repo1"},
            {"type": "git", "name": "repo2"},
        ]
        result, error = operation._apply_key_filter(value, "type:git", "test")

        assert error is None
        assert isinstance(result, list)
        assert len(result) == 2


class TestGetEntityFilePath:
    """Tests for get_entity_file_path method"""

    def test_get_file_path_by_id(self, temp_registry):
        """Test getting file path by ID"""
        operation = GetPropertyOperation(temp_registry)
        path = operation.get_entity_file_path("P-001")

        assert path is not None
        assert "proj-proj-001.yml" in path

    def test_get_file_path_by_uid(self, temp_registry):
        """Test getting file path by UID"""
        operation = GetPropertyOperation(temp_registry)
        path = operation.get_entity_file_path("proj-001")

        assert path is not None
        assert "proj-proj-001.yml" in path

    def test_get_file_path_not_found(self, temp_registry):
        """Test getting file path for non-existent entity"""
        operation = GetPropertyOperation(temp_registry)
        path = operation.get_entity_file_path("NONEXISTENT")

        assert path is None


class TestEntityExists:
    """Tests for entity_exists method"""

    def test_entity_exists_by_id(self, temp_registry):
        """Test checking entity exists by ID"""
        operation = GetPropertyOperation(temp_registry)
        assert operation.entity_exists("P-001") is True

    def test_entity_exists_by_uid(self, temp_registry):
        """Test checking entity exists by UID"""
        operation = GetPropertyOperation(temp_registry)
        assert operation.entity_exists("proj-001") is True

    def test_entity_not_exists(self, temp_registry):
        """Test checking non-existent entity"""
        operation = GetPropertyOperation(temp_registry)
        assert operation.entity_exists("NONEXISTENT") is False

    def test_entity_exists_with_type_filter(self, temp_registry):
        """Test checking entity exists with type filter"""
        operation = GetPropertyOperation(temp_registry)
        assert operation.entity_exists("P-001", entity_type=EntityType.PROJECT) is True
        assert operation.entity_exists("P-001", entity_type=EntityType.PROGRAM) is False


class TestCaseInsensitivity:
    """Tests for case-insensitive property handling"""

    def test_property_name_case_insensitive(self, temp_registry):
        """Test that property names are case-insensitive"""
        operation = GetPropertyOperation(temp_registry)

        result_lower = operation.get_property("P-001", "title")
        result_upper = operation.get_property("P-001", "TITLE")
        result_mixed = operation.get_property("P-001", "TiTlE")

        assert result_lower["success"] is True
        assert result_upper["success"] is True
        assert result_mixed["success"] is True
        assert result_lower["value"] == result_upper["value"] == result_mixed["value"]


class TestWithEntityTypeFilter:
    """Tests for property retrieval with entity type filter"""

    def test_get_project_property(self, temp_registry):
        """Test getting project property with type filter"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property(
            "P-001", "title", entity_type=EntityType.PROJECT
        )

        assert result["success"] is True
        assert result["value"] == "Test Project 1"

    def test_get_program_property(self, temp_registry):
        """Test getting program property with type filter"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property(
            "PG-001", "title", entity_type=EntityType.PROGRAM
        )

        assert result["success"] is True
        assert result["value"] == "Test Program 1"

    def test_get_mission_property(self, temp_registry):
        """Test getting mission property with type filter"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property(
            "M-001", "title", entity_type=EntityType.MISSION
        )

        assert result["success"] is True
        assert result["value"] == "Test Mission 1"

    def test_get_action_property(self, temp_registry):
        """Test getting action property with type filter"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("A-001", "title", entity_type=EntityType.ACTION)

        assert result["success"] is True
        assert result["value"] == "Test Action 1"


class TestResponseStructure:
    """Tests for response structure consistency"""

    def test_success_response_structure(self, temp_registry):
        """Test structure of successful response"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "title")

        assert "success" in result
        assert "property" in result
        assert "property_type" in result
        assert "value" in result
        assert "identifier" in result

    def test_error_response_structure(self, temp_registry):
        """Test structure of error response"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "unknown_prop")

        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert "property" in result

    def test_unknown_property_response_structure(self, temp_registry):
        """Test structure of unknown property response"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "foobar")

        assert result["success"] is False
        assert "available_properties" in result

    def test_entity_not_found_response_structure(self, temp_registry):
        """Test structure of entity not found response"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("NONEXISTENT", "title")

        assert result["success"] is False
        assert "error" in result
        assert "identifier" in result


class TestExceptions:
    """Tests for custom exceptions"""

    def test_unknown_property_error_creation(self):
        """Test UnknownPropertyError creation"""
        error = UnknownPropertyError("foo", ["title", "status"])
        assert error.property_name == "foo"
        assert error.available_properties == ["title", "status"]
        assert "foo" in str(error)

    def test_property_not_set_error_creation(self):
        """Test PropertyNotSetError creation"""
        error = PropertyNotSetError("due_date")
        assert error.property_name == "due_date"
        assert "due_date" in str(error)

    def test_index_out_of_range_error_creation(self):
        """Test IndexOutOfRangeError creation"""
        error = IndexOutOfRangeError(5, 3)
        assert error.index == 5
        assert error.list_length == 3
        assert "5" in str(error)
        assert "3" in str(error)

    def test_invalid_key_filter_error_creation(self):
        """Test InvalidKeyFilterError creation"""
        error = InvalidKeyFilterError("invalid")
        assert error.key_filter == "invalid"
        assert "invalid" in str(error)

    def test_key_filter_no_match_error_creation(self):
        """Test KeyFilterNoMatchError creation"""
        error = KeyFilterNoMatchError("name", "missing")
        assert error.filter_key == "name"
        assert error.filter_value == "missing"
        assert "name" in str(error)
        assert "missing" in str(error)


class TestIntegrationWithShowOperation:
    """Integration tests verifying GetPropertyOperation uses ShowOperation"""

    def test_uses_show_operation_for_entity_retrieval(self, temp_registry):
        """Test that GetPropertyOperation uses ShowOperation internally"""
        with patch("hxc.core.operations.get.ShowOperation") as MockShow:
            mock_instance = MagicMock()
            mock_instance.get_entity.return_value = {
                "success": True,
                "entity": {
                    "type": "project",
                    "uid": "test",
                    "id": "P-001",
                    "title": "Test",
                },
                "file_path": "/test/path.yml",
                "identifier": "P-001",
            }
            MockShow.return_value = mock_instance

            operation = GetPropertyOperation(temp_registry)
            result = operation.get_property("P-001", "title")

            MockShow.assert_called_once_with(temp_registry)
            mock_instance.get_entity.assert_called_once()

    def test_handles_show_operation_errors(self, temp_registry):
        """Test that ShowOperation errors are handled correctly"""
        with patch("hxc.core.operations.get.ShowOperation") as MockShow:
            mock_instance = MagicMock()
            mock_instance.get_entity.return_value = {
                "success": False,
                "error": "Entity not found",
                "entity": None,
                "file_path": None,
                "identifier": "P-001",
            }
            MockShow.return_value = mock_instance

            operation = GetPropertyOperation(temp_registry)
            result = operation.get_property("P-001", "title")

            assert result["success"] is False
            assert "not found" in result["error"].lower()


class TestBehavioralParityWithCLI:
    """Tests to verify behavioral parity with CLI"""

    def test_property_validation_matches_cli(self, temp_registry):
        """Test that property validation matches CLI behavior"""
        # CLI validates against ALL_PROPERTIES set
        operation = GetPropertyOperation(temp_registry)

        # Valid properties should work
        valid_result = operation.get_property("P-001", "title")
        assert valid_result["success"] is True

        # Invalid properties should fail with helpful message
        invalid_result = operation.get_property("P-001", "invalid_prop")
        assert invalid_result["success"] is False
        assert "available_properties" in invalid_result

    def test_property_classification_matches_cli(self, temp_registry):
        """Test that property classification matches CLI"""
        # CLI uses explicit sets for classification
        operation = GetPropertyOperation(temp_registry)

        # Scalar property
        scalar_result = operation.get_property("P-001", "title")
        assert scalar_result["property_type"] == PropertyType.SCALAR

        # List property
        list_result = operation.get_property("P-002", "tags")
        assert list_result["property_type"] == PropertyType.LIST

        # Complex property
        complex_result = operation.get_property("P-002", "repositories")
        assert complex_result["property_type"] == PropertyType.COMPLEX

        # Special property
        special_result = operation.get_property("P-001", "all")
        assert special_result["property_type"] == PropertyType.SPECIAL

    def test_index_handling_matches_cli(self, temp_registry):
        """Test that index handling matches CLI"""
        operation = GetPropertyOperation(temp_registry)

        # Valid index
        valid_result = operation.get_property("P-002", "tags", index=0)
        assert valid_result["success"] is True
        assert isinstance(valid_result["value"], str)

        # Invalid index
        invalid_result = operation.get_property("P-002", "tags", index=99)
        assert invalid_result["success"] is False
        assert "out of range" in invalid_result["error"].lower()

    def test_key_filter_handling_matches_cli(self, temp_registry):
        """Test that key filter handling matches CLI"""
        operation = GetPropertyOperation(temp_registry)

        # Valid key filter
        valid_result = operation.get_property(
            "P-002", "repositories", key_filter="name:github"
        )
        assert valid_result["success"] is True

        # Invalid key filter format
        invalid_format = operation.get_property(
            "P-002", "repositories", key_filter="invalid"
        )
        assert invalid_format["success"] is False
        assert "invalid key filter" in invalid_format["error"].lower()

        # Key filter no match
        no_match = operation.get_property(
            "P-002", "repositories", key_filter="name:nonexistent"
        )
        assert no_match["success"] is False
        assert "no items found" in no_match["error"].lower()


class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_string_property_name(self, temp_registry):
        """Test handling of empty string property name"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "")

        assert result["success"] is False

    def test_whitespace_property_name(self, temp_registry):
        """Test handling of whitespace property name"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001", "  title  ")

        # Should fail as whitespace is not trimmed
        assert result["success"] is False

    def test_empty_list_property(self, temp_registry):
        """Test handling of empty list property"""
        # Create entity with empty tags
        projects_dir = Path(temp_registry) / "projects"
        empty_tags_data = {
            "type": "project",
            "title": "Empty Tags Project",
            "id": "P-EMPTY",
            "uid": "proj-empty",
            "status": "active",
            "tags": [],
        }
        with open(projects_dir / "proj-proj-empty.yml", "w") as f:
            yaml.dump(empty_tags_data, f)

        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-EMPTY", "tags")

        # Empty list should still succeed (it's set, just empty)
        # Based on implementation, empty list returns success with empty list
        # Note: Current implementation may consider empty list as "not set"
        # This test documents the current behavior
        if result["success"]:
            assert result["value"] == []
        else:
            assert "not set" in result["error"].lower()

    def test_special_characters_in_identifier(self, temp_registry):
        """Test handling of special characters in identifier"""
        operation = GetPropertyOperation(temp_registry)
        result = operation.get_property("P-001/../../../etc/passwd", "title")

        # Should fail (entity not found, not security error at this level)
        assert result["success"] is False
