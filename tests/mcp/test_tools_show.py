"""
Tests for MCP Show Tools.

This module tests the show-related functionality in MCP tools,
specifically focusing on the ShowOperation integration and
behaviors specific to entity retrieval and display.
"""

import pytest

from hxc.core.enums import EntityType
from hxc.core.operations.show import (
    InvalidEntityError,
    ShowOperation,
    ShowOperationError,
)
from hxc.mcp.tools import (
    get_entity_property_tool,
    get_entity_tool,
)


class TestShowOperationIntegration:
    """Tests for ShowOperation integration with MCP tools."""

    def test_show_operation_is_used_by_get_entity(self, temp_registry):
        """Test that get_entity_tool uses ShowOperation internally."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "entity" in result
        assert "file_path" in result

    def test_show_operation_entity_lookup_by_id(self, temp_registry):
        """Test entity lookup by human-readable ID."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"

    def test_show_operation_entity_lookup_by_uid(self, temp_registry):
        """Test entity lookup by UID."""
        result = get_entity_tool(
            identifier="proj-test-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["uid"] == "proj-test-001"

    def test_show_operation_returns_complete_entity(self, temp_registry):
        """Test that ShowOperation returns complete entity data."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        entity = result["entity"]

        # Verify required fields are present
        assert "type" in entity
        assert "uid" in entity
        assert "id" in entity
        assert "title" in entity
        assert "status" in entity

    def test_show_operation_with_type_filter(self, temp_registry):
        """Test ShowOperation with entity type filter."""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="project",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "project"

    def test_show_operation_type_filter_mismatch(self, temp_registry):
        """Test ShowOperation fails when type filter doesn't match."""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="program",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestShowOperationRawContent:
    """Tests for raw content retrieval functionality."""

    def test_show_with_include_raw_true(self, temp_registry):
        """Test retrieving raw YAML content."""
        result = get_entity_tool(
            identifier="P-001",
            include_raw=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "raw_content" in result
        assert isinstance(result["raw_content"], str)
        assert "type: project" in result["raw_content"]

    def test_show_with_include_raw_false(self, temp_registry):
        """Test that raw content is excluded by default."""
        result = get_entity_tool(
            identifier="P-001",
            include_raw=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "raw_content" not in result

    def test_show_raw_content_matches_parsed_entity(self, temp_registry):
        """Test that raw content is consistent with parsed entity."""
        import yaml

        result = get_entity_tool(
            identifier="P-001",
            include_raw=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        parsed_raw = yaml.safe_load(result["raw_content"])
        entity = result["entity"]

        assert parsed_raw["type"] == entity["type"]
        assert parsed_raw["uid"] == entity["uid"]
        assert parsed_raw["id"] == entity["id"]
        assert parsed_raw["title"] == entity["title"]


class TestShowOperationAllEntityTypes:
    """Tests for showing all entity types."""

    def test_show_project(self, temp_registry):
        """Test showing a project entity."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "project"

    def test_show_program(self, temp_registry):
        """Test showing a program entity."""
        result = get_entity_tool(
            identifier="PRG-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "program"

    def test_show_mission(self, temp_registry):
        """Test showing a mission entity."""
        result = get_entity_tool(
            identifier="M-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "mission"

    def test_show_action(self, temp_registry):
        """Test showing an action entity."""
        result = get_entity_tool(
            identifier="A-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "action"


class TestShowOperationErrorHandling:
    """Tests for error handling in show operations."""

    def test_show_nonexistent_entity(self, temp_registry):
        """Test showing a nonexistent entity."""
        result = get_entity_tool(
            identifier="NONEXISTENT",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["entity"] is None

    def test_show_with_invalid_registry(self):
        """Test showing entity with invalid registry path."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False
        assert "error" in result

    def test_show_with_invalid_entity_type(self, temp_registry):
        """Test showing entity with invalid entity type."""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="invalid_type",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_show_returns_identifier_on_error(self, temp_registry):
        """Test that identifier is returned even on error."""
        result = get_entity_tool(
            identifier="NONEXISTENT",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert result["identifier"] == "NONEXISTENT"


class TestShowOperationFilePath:
    """Tests for file path handling in show operations."""

    def test_show_returns_file_path(self, temp_registry):
        """Test that show returns the entity file path."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "file_path" in result
        assert result["file_path"].endswith(".yml")

    def test_show_file_path_contains_entity_uid(self, temp_registry):
        """Test that file path contains entity UID."""
        result = get_entity_tool(
            identifier="proj-test-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "proj-test-001" in result["file_path"]

    def test_show_file_path_in_correct_folder(self, temp_registry):
        """Test that file path is in correct entity folder."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "projects" in result["file_path"]


class TestShowPropertyRetrieval:
    """Tests for property retrieval through show tools."""

    def test_show_property_title(self, temp_registry):
        """Test retrieving title property."""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["property"] == "title"
        assert isinstance(result["value"], str)

    def test_show_property_status(self, temp_registry):
        """Test retrieving status property."""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="status",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["value"] in ["active", "completed", "on-hold", "cancelled", "planned"]

    def test_show_property_tags(self, temp_registry):
        """Test retrieving tags property."""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["value"], list)

    def test_show_property_all(self, temp_registry):
        """Test retrieving all properties."""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="all",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert "type" in result["value"]
        assert "uid" in result["value"]
        assert "title" in result["value"]

    def test_show_property_path(self, temp_registry):
        """Test retrieving path property."""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="path",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert ".yml" in result["value"]


class TestShowOperationDirectUse:
    """Tests for direct ShowOperation usage patterns."""

    def test_show_operation_direct_instantiation(self, temp_registry):
        """Test direct ShowOperation instantiation."""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("P-001")

        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"

    def test_show_operation_with_entity_type_enum(self, temp_registry):
        """Test ShowOperation with EntityType enum."""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity(
            identifier="P-001",
            entity_type=EntityType.PROJECT,
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "project"

    def test_show_operation_include_raw(self, temp_registry):
        """Test ShowOperation with include_raw parameter."""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity(
            identifier="P-001",
            include_raw=True,
        )

        assert result["success"] is True
        assert "raw_content" in result

    def test_show_operation_entity_not_found(self, temp_registry):
        """Test ShowOperation with nonexistent entity."""
        operation = ShowOperation(temp_registry)

        result = operation.get_entity("NONEXISTENT")

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestShowOperationResponseStructure:
    """Tests for response structure consistency."""

    def test_show_success_response_structure(self, temp_registry):
        """Test successful response has required fields."""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert "success" in result
        assert "entity" in result
        assert "file_path" in result
        assert "identifier" in result

    def test_show_error_response_structure(self, temp_registry):
        """Test error response has required fields."""
        result = get_entity_tool(
            identifier="NONEXISTENT",
            registry_path=temp_registry,
        )

        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert "entity" in result
        assert result["entity"] is None
        assert "identifier" in result

    def test_show_property_success_response_structure(self, temp_registry):
        """Test property retrieval success response structure."""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            registry_path=temp_registry,
        )

        assert "success" in result
        assert "property" in result
        assert "value" in result
        assert "identifier" in result

    def test_show_property_error_response_structure(self, temp_registry):
        """Test property retrieval error response structure."""
        result = get_entity_property_tool(
            identifier="NONEXISTENT",
            property_name="title",
            registry_path=temp_registry,
        )

        assert "success" in result
        assert result["success"] is False
        assert "error" in result
        assert "property" in result
        assert "identifier" in result