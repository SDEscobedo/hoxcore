"""
Tests for get_entity_tool and related retrieval tools in MCP Tools.

This module tests the tools that enable retrieving entity information
from HoxCore registries through the Model Context Protocol.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityType
from hxc.core.operations.show import (
    InvalidEntityError,
    ShowOperation,
    ShowOperationError,
)
from hxc.mcp.tools import (
    get_entity_hierarchy_tool,
    get_entity_property_tool,
    get_entity_tool,
    get_registry_stats_tool,
)

from .test_tools_common import (
    verify_error_result,
    verify_get_result,
    verify_success_result,
)


class TestGetEntityTool:
    """Tests for get_entity_tool"""

    def test_get_entity_by_id(self, temp_registry):
        """Test getting entity by ID"""
        result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert result["success"] is True
        assert "entity" in result
        assert result["entity"]["id"] == "P-001"
        assert result["entity"]["title"] == "Test Project One"

    def test_get_entity_by_uid(self, temp_registry):
        """Test getting entity by UID"""
        result = get_entity_tool(
            identifier="proj-test-001", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["entity"]["uid"] == "proj-test-001"
        assert result["entity"]["id"] == "P-001"

    def test_get_entity_with_type_filter(self, temp_registry):
        """Test getting entity with type filter"""
        result = get_entity_tool(
            identifier="P-001", entity_type="project", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "project"

    def test_get_entity_program(self, temp_registry):
        """Test getting a program entity"""
        result = get_entity_tool(identifier="PRG-001", registry_path=temp_registry)

        assert result["success"] is True
        assert result["entity"]["type"] == "program"
        assert result["entity"]["title"] == "Test Program"

    def test_get_entity_mission(self, temp_registry):
        """Test getting a mission entity"""
        result = get_entity_tool(identifier="M-001", registry_path=temp_registry)

        assert result["success"] is True
        assert result["entity"]["type"] == "mission"
        assert result["entity"]["title"] == "Test Mission"

    def test_get_entity_action(self, temp_registry):
        """Test getting an action entity"""
        result = get_entity_tool(identifier="A-001", registry_path=temp_registry)

        assert result["success"] is True
        assert result["entity"]["type"] == "action"
        assert result["entity"]["title"] == "Test Action"

    def test_get_entity_not_found(self, temp_registry):
        """Test getting non-existent entity"""
        result = get_entity_tool(identifier="NONEXISTENT", registry_path=temp_registry)

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_get_entity_with_invalid_type(self, temp_registry):
        """Test getting entity with invalid type"""
        result = get_entity_tool(
            identifier="P-001", entity_type="invalid", registry_path=temp_registry
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_entity_includes_file_path(self, temp_registry):
        """Test that result includes file path"""
        result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert result["success"] is True
        assert "file_path" in result
        assert "proj-proj-test-001.yml" in result["file_path"]

    def test_get_entity_includes_identifier(self, temp_registry):
        """Test that result includes identifier"""
        result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert result["success"] is True
        assert "identifier" in result
        assert result["identifier"] == "P-001"

    def test_get_entity_wrong_type_filter(self, temp_registry):
        """Test getting entity with wrong type filter returns not found"""
        result = get_entity_tool(
            identifier="P-001", entity_type="program", registry_path=temp_registry
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_get_entity_with_no_registry(self):
        """Test getting entity with no registry"""
        result = get_entity_tool(identifier="P-001", registry_path="/nonexistent/path")

        assert result["success"] is False
        assert "error" in result


class TestGetEntityToolUsesShowOperation:
    """Tests to verify get_entity_tool uses the shared ShowOperation"""

    def test_get_entity_uses_show_operation(self, temp_registry):
        """Test that get_entity_tool uses ShowOperation internally"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.return_value = {
                "success": True,
                "entity": {
                    "type": "project",
                    "uid": "proj-test-001",
                    "id": "P-001",
                    "title": "Test Project",
                },
                "file_path": "/test/path.yml",
                "identifier": "P-001",
            }
            MockOperation.return_value = mock_instance

            result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.get_entity.assert_called_once()

    def test_get_entity_passes_all_parameters_to_operation(self, temp_registry):
        """Test that get_entity_tool passes all parameters to ShowOperation"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.return_value = {
                "success": True,
                "entity": {
                    "type": "project",
                    "uid": "proj-test-001",
                    "id": "P-001",
                    "title": "Test Project",
                },
                "file_path": "/test/path.yml",
                "identifier": "P-001",
                "raw_content": "type: project\n...",
            }
            MockOperation.return_value = mock_instance

            result = get_entity_tool(
                identifier="P-001",
                entity_type="project",
                include_raw=True,
                registry_path=temp_registry,
            )

        call_kwargs = mock_instance.get_entity.call_args[1]
        assert call_kwargs["identifier"] == "P-001"
        assert call_kwargs["entity_type"] == EntityType.PROJECT
        assert call_kwargs["include_raw"] is True

    def test_get_entity_handles_operation_not_found(self, temp_registry):
        """Test that get_entity_tool handles not found from ShowOperation"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.return_value = {
                "success": False,
                "error": "Entity not found: NONEXISTENT",
                "entity": None,
                "file_path": None,
                "identifier": "NONEXISTENT",
            }
            MockOperation.return_value = mock_instance

            result = get_entity_tool(
                identifier="NONEXISTENT", registry_path=temp_registry
            )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert result["entity"] is None

    def test_get_entity_handles_invalid_entity_error(self, temp_registry):
        """Test that InvalidEntityError is handled correctly"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.side_effect = InvalidEntityError(
                "/test/path.yml", "Invalid YAML content"
            )
            MockOperation.return_value = mock_instance

            result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert result["success"] is False
        assert "Invalid YAML content" in result["error"]

    def test_get_entity_handles_show_operation_error(self, temp_registry):
        """Test that ShowOperationError is handled correctly"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.side_effect = ShowOperationError(
                "Show operation failed"
            )
            MockOperation.return_value = mock_instance

            result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert result["success"] is False
        assert "Show operation failed" in result["error"]

    def test_get_entity_handles_path_security_error(self, temp_registry):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = get_entity_tool(
                identifier="../../../etc/passwd", registry_path=temp_registry
            )

        assert result["success"] is False
        assert "Security error" in result["error"]

    def test_get_entity_handles_unexpected_error(self, temp_registry):
        """Test that unexpected errors are handled gracefully"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.side_effect = RuntimeError("Unexpected error")
            MockOperation.return_value = mock_instance

            result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert result["success"] is False
        assert "Unexpected error" in result["error"]


class TestGetEntityToolIncludeRaw:
    """Tests for include_raw parameter in get_entity_tool"""

    def test_get_entity_include_raw_true(self, temp_registry):
        """Test getting entity with raw content included"""
        result = get_entity_tool(
            identifier="P-001", include_raw=True, registry_path=temp_registry
        )

        assert result["success"] is True
        assert "raw_content" in result
        assert isinstance(result["raw_content"], str)
        assert "type: project" in result["raw_content"]

    def test_get_entity_include_raw_false(self, temp_registry):
        """Test getting entity without raw content (explicit)"""
        result = get_entity_tool(
            identifier="P-001", include_raw=False, registry_path=temp_registry
        )

        assert result["success"] is True
        assert "raw_content" not in result

    def test_get_entity_include_raw_default(self, temp_registry):
        """Test that raw content is not included by default"""
        result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert result["success"] is True
        assert "raw_content" not in result

    def test_get_entity_raw_content_matches_file(self, temp_registry):
        """Test that raw content matches actual file content"""
        result = get_entity_tool(
            identifier="P-001", include_raw=True, registry_path=temp_registry
        )

        assert result["success"] is True

        # Read file directly
        file_path = Path(result["file_path"])
        with open(file_path, "r") as f:
            actual_content = f.read()

        assert result["raw_content"] == actual_content

    def test_get_entity_raw_content_is_valid_yaml(self, temp_registry):
        """Test that raw content is valid YAML"""
        result = get_entity_tool(
            identifier="P-001", include_raw=True, registry_path=temp_registry
        )

        assert result["success"] is True

        # Parse the raw content
        parsed = yaml.safe_load(result["raw_content"])
        assert isinstance(parsed, dict)
        assert parsed["type"] == "project"
        assert parsed["uid"] == "proj-test-001"

    def test_get_entity_raw_content_consistent_with_entity(self, temp_registry):
        """Test that raw content is consistent with parsed entity"""
        result = get_entity_tool(
            identifier="P-001", include_raw=True, registry_path=temp_registry
        )

        assert result["success"] is True

        # Parse raw content
        parsed_raw = yaml.safe_load(result["raw_content"])

        # Compare with entity
        assert parsed_raw["type"] == result["entity"]["type"]
        assert parsed_raw["uid"] == result["entity"]["uid"]
        assert parsed_raw["id"] == result["entity"]["id"]
        assert parsed_raw["title"] == result["entity"]["title"]

    def test_get_entity_raw_content_with_type_filter(self, temp_registry):
        """Test getting entity with raw content and type filter"""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="project",
            include_raw=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "raw_content" in result
        assert result["entity"]["type"] == "project"

    def test_get_entity_raw_not_included_on_error(self, temp_registry):
        """Test that raw content is not included when entity not found"""
        result = get_entity_tool(
            identifier="NONEXISTENT", include_raw=True, registry_path=temp_registry
        )

        assert result["success"] is False
        assert "raw_content" not in result


class TestGetEntityToolBehavioralParityWithCLI:
    """Tests to verify get_entity_tool produces same results as CLI ShowCommand"""

    def test_entity_lookup_by_id_matches_cli(self, temp_registry):
        """Test that ID lookup produces same entity in both interfaces"""
        # Use ShowOperation directly (what CLI uses)
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("P-001")

        # Use MCP tool
        mcp_result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert operation_result["success"] is True
        assert mcp_result["success"] is True

        # Both should return same entity data
        assert operation_result["entity"]["id"] == mcp_result["entity"]["id"]
        assert operation_result["entity"]["uid"] == mcp_result["entity"]["uid"]
        assert operation_result["entity"]["title"] == mcp_result["entity"]["title"]

    def test_entity_lookup_by_uid_matches_cli(self, temp_registry):
        """Test that UID lookup produces same entity in both interfaces"""
        # Use ShowOperation directly
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("proj-test-001")

        # Use MCP tool
        mcp_result = get_entity_tool(
            identifier="proj-test-001", registry_path=temp_registry
        )

        assert operation_result["success"] is True
        assert mcp_result["success"] is True

        # Both should return same entity data
        assert operation_result["entity"]["id"] == mcp_result["entity"]["id"]
        assert operation_result["entity"]["uid"] == mcp_result["entity"]["uid"]

    def test_entity_type_filter_matches_cli(self, temp_registry):
        """Test that entity type filter works identically"""
        # Use ShowOperation directly
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("P-001", entity_type=EntityType.PROJECT)

        # Use MCP tool
        mcp_result = get_entity_tool(
            identifier="P-001", entity_type="project", registry_path=temp_registry
        )

        assert operation_result["success"] is True
        assert mcp_result["success"] is True

    def test_wrong_type_filter_matches_cli(self, temp_registry):
        """Test that wrong type filter produces same error in both"""
        # Use ShowOperation directly
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("P-001", entity_type=EntityType.PROGRAM)

        # Use MCP tool
        mcp_result = get_entity_tool(
            identifier="P-001", entity_type="program", registry_path=temp_registry
        )

        assert operation_result["success"] is False
        assert mcp_result["success"] is False
        assert "not found" in operation_result["error"].lower()
        assert "not found" in mcp_result["error"].lower()

    def test_not_found_error_matches_cli(self, temp_registry):
        """Test that not found error structure matches CLI"""
        # Use ShowOperation directly
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("NONEXISTENT")

        # Use MCP tool
        mcp_result = get_entity_tool(
            identifier="NONEXISTENT", registry_path=temp_registry
        )

        assert operation_result["success"] is False
        assert mcp_result["success"] is False
        assert operation_result["entity"] is None
        assert mcp_result["entity"] is None

    def test_raw_content_matches_cli(self, temp_registry):
        """Test that raw content matches what CLI would display with --raw"""
        # Use ShowOperation directly
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("P-001", include_raw=True)

        # Use MCP tool
        mcp_result = get_entity_tool(
            identifier="P-001", include_raw=True, registry_path=temp_registry
        )

        assert operation_result["success"] is True
        assert mcp_result["success"] is True
        assert operation_result["raw_content"] == mcp_result["raw_content"]

    def test_file_path_matches_cli(self, temp_registry):
        """Test that file path matches CLI output"""
        # Use ShowOperation directly
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("P-001")

        # Use MCP tool
        mcp_result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        assert operation_result["file_path"] == mcp_result["file_path"]

    def test_response_structure_matches_operation(self, temp_registry):
        """Test that MCP response structure matches ShowOperation"""
        # Use ShowOperation directly
        operation = ShowOperation(temp_registry)
        operation_result = operation.get_entity("P-001")

        # Use MCP tool
        mcp_result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        # MCP result should have same core keys
        assert "success" in mcp_result
        assert "entity" in mcp_result
        assert "file_path" in mcp_result
        assert "identifier" in mcp_result

    def test_all_entity_types_match_cli(self, temp_registry):
        """Test that all entity types are retrieved identically"""
        entity_tests = [
            ("P-001", "project"),
            ("PRG-001", "program"),
            ("M-001", "mission"),
            ("A-001", "action"),
        ]

        for identifier, expected_type in entity_tests:
            # Use ShowOperation directly
            operation = ShowOperation(temp_registry)
            operation_result = operation.get_entity(identifier)

            # Use MCP tool
            mcp_result = get_entity_tool(
                identifier=identifier, registry_path=temp_registry
            )

            assert (
                operation_result["success"] is True
            ), f"Operation failed for {identifier}"
            assert mcp_result["success"] is True, f"MCP failed for {identifier}"
            assert operation_result["entity"]["type"] == mcp_result["entity"]["type"]
            assert operation_result["entity"]["title"] == mcp_result["entity"]["title"]


class TestGetEntityPropertyTool:
    """Tests for get_entity_property_tool"""

    def test_get_scalar_property(self, temp_registry):
        """Test getting a scalar property"""
        result = get_entity_property_tool(
            identifier="P-001", property_name="title", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["value"] == "Test Project One"
        assert result["property"] == "title"

    def test_get_status_property(self, temp_registry):
        """Test getting status property"""
        result = get_entity_property_tool(
            identifier="P-001", property_name="status", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["value"] == "active"

    def test_get_list_property(self, temp_registry):
        """Test getting a list property"""
        result = get_entity_property_tool(
            identifier="P-001", property_name="tags", registry_path=temp_registry
        )

        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert "test" in result["value"]

    def test_get_list_property_with_index(self, temp_registry):
        """Test getting list property with index"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            index=0,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["value"], str)

    def test_get_list_property_invalid_index(self, temp_registry):
        """Test getting list property with invalid index"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            index=999,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "out of range" in result["error"].lower()

    def test_get_complex_property(self, temp_registry):
        """Test getting a complex property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert len(result["value"]) > 0

    def test_get_complex_property_with_key_filter(self, temp_registry):
        """Test getting complex property with key filter"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="name:github",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert result["value"]["name"] == "github"

    def test_get_complex_property_invalid_key_format(self, temp_registry):
        """Test getting complex property with invalid key format"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="invalid",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "invalid key filter" in result["error"].lower()

    def test_get_complex_property_key_not_found(self, temp_registry):
        """Test getting complex property with key not found"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="name:nonexistent",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "no items found" in result["error"].lower()

    def test_get_all_properties(self, temp_registry):
        """Test getting all properties"""
        result = get_entity_property_tool(
            identifier="P-001", property_name="all", registry_path=temp_registry
        )

        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert "title" in result["value"]
        assert "status" in result["value"]

    def test_get_path_property(self, temp_registry):
        """Test getting path property"""
        result = get_entity_property_tool(
            identifier="P-001", property_name="path", registry_path=temp_registry
        )

        assert result["success"] is True
        assert "proj-proj-test-001.yml" in result["value"]

    def test_get_nonexistent_property(self, temp_registry):
        """Test getting non-existent property"""
        result = get_entity_property_tool(
            identifier="P-001", property_name="nonexistent", registry_path=temp_registry
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_get_property_from_nonexistent_entity(self, temp_registry):
        """Test getting property from non-existent entity"""
        result = get_entity_property_tool(
            identifier="NONEXISTENT", property_name="title", registry_path=temp_registry
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_property_includes_identifier(self, temp_registry):
        """Test that result includes identifier"""
        result = get_entity_property_tool(
            identifier="P-001", property_name="title", registry_path=temp_registry
        )

        assert result["success"] is True
        assert "identifier" in result
        assert result["identifier"] == "P-001"

    def test_get_property_with_no_registry(self):
        """Test getting property with no registry"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_property_with_entity_type_filter(self, temp_registry):
        """Test getting property with entity type filter"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            entity_type="project",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["value"] == "Test Project One"

    def test_get_property_with_wrong_entity_type(self, temp_registry):
        """Test getting property with wrong entity type filter"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            entity_type="program",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestGetEntityPropertyToolUsesShowOperation:
    """Tests to verify get_entity_property_tool uses the shared ShowOperation"""

    def test_get_property_uses_show_operation(self, temp_registry):
        """Test that get_entity_property_tool uses ShowOperation internally"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.return_value = {
                "success": True,
                "entity": {
                    "type": "project",
                    "uid": "proj-test-001",
                    "id": "P-001",
                    "title": "Test Project",
                },
                "file_path": "/test/path.yml",
                "identifier": "P-001",
            }
            MockOperation.return_value = mock_instance

            result = get_entity_property_tool(
                identifier="P-001", property_name="title", registry_path=temp_registry
            )

        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.get_entity.assert_called_once()

    def test_get_property_handles_entity_not_found(self, temp_registry):
        """Test that get_entity_property_tool handles entity not found"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.return_value = {
                "success": False,
                "error": "Entity not found: NONEXISTENT",
                "entity": None,
                "file_path": None,
                "identifier": "NONEXISTENT",
            }
            MockOperation.return_value = mock_instance

            result = get_entity_property_tool(
                identifier="NONEXISTENT",
                property_name="title",
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_get_property_handles_path_security_error(self, temp_registry):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = get_entity_property_tool(
                identifier="../../../etc/passwd",
                property_name="title",
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Security error" in result["error"]

    def test_get_property_handles_unexpected_error(self, temp_registry):
        """Test that unexpected errors are handled gracefully"""
        with patch("hxc.mcp.tools.ShowOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity.side_effect = RuntimeError("Unexpected error")
            MockOperation.return_value = mock_instance

            result = get_entity_property_tool(
                identifier="P-001",
                property_name="title",
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Error retrieving property" in result["error"]


class TestGetEntityHierarchyTool:
    """Tests for get_entity_hierarchy_tool"""

    def test_get_hierarchy_basic(self, temp_registry):
        """Test getting basic hierarchy"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001", registry_path=temp_registry
        )

        assert result["success"] is True
        assert "hierarchy" in result
        assert "root" in result["hierarchy"]
        assert result["hierarchy"]["root"]["id"] == "PRG-001"

    def test_get_hierarchy_with_children(self, temp_registry):
        """Test getting hierarchy with children"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "children" in hierarchy
        assert len(hierarchy["children"]) > 0

    def test_get_hierarchy_without_children(self, temp_registry):
        """Test getting hierarchy without children"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "children" in hierarchy
        assert len(hierarchy["children"]) == 0

    def test_get_hierarchy_with_parent(self, temp_registry):
        """Test getting hierarchy with parent"""
        result = get_entity_hierarchy_tool(
            identifier="miss-test-001", registry_path=temp_registry
        )

        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "parent" in hierarchy
        assert hierarchy["parent"] is not None

    def test_get_hierarchy_without_parent(self, temp_registry):
        """Test getting hierarchy without parent"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001", registry_path=temp_registry
        )

        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "parent" in hierarchy
        assert hierarchy["parent"] is None

    def test_get_hierarchy_recursive(self, temp_registry):
        """Test getting hierarchy recursively"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            recursive=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "hierarchy" in result

    def test_get_hierarchy_includes_options(self, temp_registry):
        """Test that result includes options"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            include_related=False,
            recursive=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "options" in result
        assert result["options"]["include_children"] is True
        assert result["options"]["include_related"] is False
        assert result["options"]["recursive"] is True

    def test_get_hierarchy_nonexistent_entity(self, temp_registry):
        """Test getting hierarchy for non-existent entity"""
        result = get_entity_hierarchy_tool(
            identifier="NONEXISTENT", registry_path=temp_registry
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_hierarchy_with_related(self, temp_registry):
        """Test getting hierarchy with related entities"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_related=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "related" in hierarchy

    def test_get_hierarchy_without_related(self, temp_registry):
        """Test getting hierarchy without related entities"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_related=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "related" in hierarchy
        assert len(hierarchy["related"]) == 0

    def test_get_hierarchy_with_entity_type(self, temp_registry):
        """Test getting hierarchy with entity type filter"""
        result = get_entity_hierarchy_tool(
            identifier="PRG-001",
            entity_type="program",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["hierarchy"]["root"]["type"] == "program"


class TestGetRegistryStatsTool:
    """Tests for get_registry_stats_tool"""

    def test_get_stats_basic(self, temp_registry):
        """Test getting basic registry stats"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert "stats" in result
        assert "total_entities" in result["stats"]
        assert result["stats"]["total_entities"] > 0

    def test_get_stats_by_type(self, temp_registry):
        """Test stats by type"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        stats = result["stats"]
        assert "by_type" in stats
        assert "project" in stats["by_type"]
        assert "program" in stats["by_type"]
        assert "mission" in stats["by_type"]
        assert "action" in stats["by_type"]

    def test_get_stats_by_status(self, temp_registry):
        """Test stats by status"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        stats = result["stats"]
        assert "by_status" in stats
        assert "active" in stats["by_status"]

    def test_get_stats_by_category(self, temp_registry):
        """Test stats by category"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        stats = result["stats"]
        assert "by_category" in stats
        assert len(stats["by_category"]) > 0

    def test_get_stats_tags(self, temp_registry):
        """Test stats for tags"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        stats = result["stats"]
        assert "tags" in stats
        assert "test" in stats["tags"]
        assert stats["tags"]["test"] > 0

    def test_get_stats_includes_registry_path(self, temp_registry):
        """Test that result includes registry path"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert "registry_path" in result
        assert result["registry_path"] == temp_registry

    def test_get_stats_no_registry(self):
        """Test getting stats with no registry"""
        result = get_registry_stats_tool(registry_path="/nonexistent/path")

        assert result["success"] is False
        assert "error" in result

    def test_get_stats_type_counts_accurate(self, temp_registry):
        """Test that type counts are accurate"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        stats = result["stats"]

        # Verify total equals sum of types
        type_sum = sum(stats["by_type"].values())
        assert stats["total_entities"] == type_sum

    def test_get_stats_status_counts_accurate(self, temp_registry):
        """Test that status counts are accurate"""
        result = get_registry_stats_tool(registry_path=temp_registry)

        assert result["success"] is True
        stats = result["stats"]

        # Verify total equals sum of statuses
        status_sum = sum(stats["by_status"].values())
        assert stats["total_entities"] == status_sum

    def test_get_stats_handles_empty_registry(self, empty_temp_dir):
        """Test stats on empty registry"""
        # Initialize empty registry
        from hxc.mcp.tools import init_registry_tool

        init_result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )
        assert init_result["success"] is True

        # Get stats
        result = get_registry_stats_tool(registry_path=empty_temp_dir)

        assert result["success"] is True
        assert result["stats"]["total_entities"] == 0
        assert result["stats"]["by_type"]["project"] == 0
        assert result["stats"]["by_type"]["program"] == 0
        assert result["stats"]["by_type"]["mission"] == 0
        assert result["stats"]["by_type"]["action"] == 0


class TestGetToolsIntegration:
    """Integration tests for get tools"""

    def test_get_then_get_property(self, temp_registry):
        """Test getting an entity then getting its property"""
        # First get entity
        get_result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert get_result["success"] is True
        entity_id = get_result["entity"]["id"]

        # Then get property
        property_result = get_entity_property_tool(
            identifier=entity_id,
            property_name="title",
            registry_path=temp_registry,
        )

        assert property_result["success"] is True
        assert property_result["value"] == get_result["entity"]["title"]

    def test_get_hierarchy_then_get_children(self, temp_registry):
        """Test getting hierarchy then getting children"""
        # Get hierarchy
        hierarchy_result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            registry_path=temp_registry,
        )

        assert hierarchy_result["success"] is True
        children = hierarchy_result["hierarchy"]["children"]
        assert len(children) > 0

        # Get first child
        child_id = children[0]["id"]
        child_result = get_entity_tool(
            identifier=child_id,
            registry_path=temp_registry,
        )

        assert child_result["success"] is True

    def test_stats_then_get_by_type(self, temp_registry):
        """Test getting stats then getting entities by type"""
        # Get stats
        stats_result = get_registry_stats_tool(registry_path=temp_registry)

        assert stats_result["success"] is True
        project_count = stats_result["stats"]["by_type"]["project"]
        assert project_count > 0

        # Get a project
        get_result = get_entity_tool(
            identifier="P-001",
            entity_type="project",
            registry_path=temp_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["type"] == "project"

    def test_get_all_properties_then_specific(self, temp_registry):
        """Test getting all properties then a specific one"""
        # Get all properties
        all_result = get_entity_property_tool(
            identifier="P-001",
            property_name="all",
            registry_path=temp_registry,
        )

        assert all_result["success"] is True
        all_props = all_result["value"]

        # Get specific property
        title_result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            registry_path=temp_registry,
        )

        assert title_result["success"] is True
        assert title_result["value"] == all_props["title"]


class TestGetToolsErrorHandling:
    """Tests for error handling in get tools"""

    def test_get_with_security_error(self):
        """Test get with path security error"""
        result = get_entity_tool(
            identifier="test",
            registry_path="/etc/passwd",
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_property_with_none_value(self, temp_registry):
        """Test getting property with None value"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="completion_date",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert (
            "not found" in result["error"].lower()
            or "not set" in result["error"].lower()
        )

    def test_get_hierarchy_with_invalid_type(self, temp_registry):
        """Test getting hierarchy with invalid entity type"""
        result = get_entity_hierarchy_tool(
            identifier="P-001",
            entity_type="invalid_type",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_stats_with_corrupted_file(self, temp_registry):
        """Test stats when registry has corrupted file (should handle gracefully)"""
        # Create a corrupted YAML file
        corrupted_file = Path(temp_registry) / "projects" / "proj-corrupted.yml"
        corrupted_file.write_text("invalid: yaml: content: [")

        # Get stats should still work (skip corrupted files)
        result = get_registry_stats_tool(registry_path=temp_registry)

        # Should succeed, possibly with reduced count
        assert result["success"] is True

        # Cleanup
        corrupted_file.unlink()
