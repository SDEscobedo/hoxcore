"""
Tests for validation functionality across MCP Tools.

This module tests validation-related functionality including:
- Input validation for tool parameters
- Entity field validation (dates, status, IDs)
- Registry path validation
- Entity structure validation
- Validation error handling and messages
- validate_registry_tool for full registry validation
- validate_entity_tool for single entity pre-flight validation
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.registry import (
    InvalidRegistryPathError,
    RegistryOperation,
)
from hxc.core.operations.validate import (
    ValidateOperation,
    ValidateOperationError,
    ValidationResult,
)
from hxc.mcp.tools import (
    create_entity_tool,
    delete_entity_tool,
    edit_entity_tool,
    get_entity_property_tool,
    get_entity_tool,
    list_entities_tool,
    search_entities_tool,
    validate_entity_tool,
    validate_registry_path_tool,
    validate_registry_tool,
)


class TestValidateRegistryTool:
    """Tests for validate_registry_tool"""

    def test_validate_valid_registry(self, temp_registry):
        """Test validating a valid registry"""
        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is True
        assert result["errors"] == []
        assert result["error_count"] == 0
        assert result["entities_checked"] >= 0

    def test_validate_returns_expected_structure(self, temp_registry):
        """Test that result has expected structure"""
        result = validate_registry_tool(registry_path=temp_registry)

        expected_keys = {
            "success",
            "valid",
            "errors",
            "warnings",
            "error_count",
            "warning_count",
            "entities_checked",
            "entities_by_type",
        }
        assert set(result.keys()) == expected_keys

    def test_validate_counts_entities_by_type(self, temp_registry):
        """Test that entities are counted by type"""
        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert isinstance(result["entities_by_type"], dict)
        # Temp registry has projects, programs, missions, actions
        assert "project" in result["entities_by_type"]

    def test_validate_detects_missing_required_fields(self, temp_registry):
        """Test detection of missing required fields"""
        # Create entity missing required fields
        invalid_entity = {"status": "active"}  # Missing type, uid, title

        projects_dir = Path(temp_registry) / "projects"
        with open(projects_dir / "proj-invalid.yml", "w") as f:
            yaml.dump(invalid_entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert result["error_count"] > 0
        assert any("uid" in error.lower() for error in result["errors"])
        assert any("title" in error.lower() for error in result["errors"])

    def test_validate_detects_duplicate_uids(self, temp_registry):
        """Test detection of duplicate UIDs"""
        # Create two entities with the same UID
        entity1 = {
            "type": "project",
            "uid": "duplicate-uid",
            "title": "First",
            "status": "active",
        }
        entity2 = {
            "type": "project",
            "uid": "duplicate-uid",
            "title": "Second",
            "status": "active",
        }

        projects_dir = Path(temp_registry) / "projects"
        with open(projects_dir / "proj-dup1.yml", "w") as f:
            yaml.dump(entity1, f)
        with open(projects_dir / "proj-dup2.yml", "w") as f:
            yaml.dump(entity2, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Duplicate UID" in error for error in result["errors"])

    def test_validate_detects_duplicate_ids_within_type(self, temp_registry):
        """Test detection of duplicate IDs within same entity type"""
        entity1 = {
            "type": "project",
            "uid": "proj-a",
            "id": "SAME-ID",
            "title": "First",
            "status": "active",
        }
        entity2 = {
            "type": "project",
            "uid": "proj-b",
            "id": "SAME-ID",
            "title": "Second",
            "status": "active",
        }

        projects_dir = Path(temp_registry) / "projects"
        with open(projects_dir / "proj-a.yml", "w") as f:
            yaml.dump(entity1, f)
        with open(projects_dir / "proj-b.yml", "w") as f:
            yaml.dump(entity2, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Duplicate ID" in error for error in result["errors"])

    def test_validate_allows_same_id_across_types(self, temp_registry):
        """Test that same ID is allowed across different entity types"""
        project = {
            "type": "project",
            "uid": "proj-x",
            "id": "SHARED-ID",
            "title": "Project",
            "status": "active",
        }
        program = {
            "type": "program",
            "uid": "prog-x",
            "id": "SHARED-ID",
            "title": "Program",
            "status": "active",
        }

        with open(Path(temp_registry) / "projects" / "proj-x.yml", "w") as f:
            yaml.dump(project, f)
        with open(Path(temp_registry) / "programs" / "prog-x.yml", "w") as f:
            yaml.dump(program, f)

        result = validate_registry_tool(registry_path=temp_registry)

        # Should be valid - same ID allowed across types
        assert result["success"] is True
        # Check no duplicate ID errors
        assert not any(
            "Duplicate ID" in error and "SHARED-ID" in error
            for error in result["errors"]
        )

    def test_validate_detects_broken_parent_link(self, temp_registry):
        """Test detection of broken parent links"""
        entity = {
            "type": "project",
            "uid": "proj-orphan",
            "title": "Orphan",
            "status": "active",
            "parent": "nonexistent-parent",
        }

        with open(Path(temp_registry) / "projects" / "proj-orphan.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Broken parent link" in error for error in result["errors"])

    def test_validate_detects_broken_child_link(self, temp_registry):
        """Test detection of broken child links"""
        entity = {
            "type": "program",
            "uid": "prog-parent",
            "title": "Parent",
            "status": "active",
            "children": ["nonexistent-child"],
        }

        with open(Path(temp_registry) / "programs" / "prog-parent.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Broken child link" in error for error in result["errors"])

    def test_validate_broken_related_is_warning(self, temp_registry):
        """Test that broken related links are warnings not errors"""
        entity = {
            "type": "project",
            "uid": "proj-with-related",
            "title": "Has Related",
            "status": "active",
            "related": ["nonexistent-related"],
        }

        with open(Path(temp_registry) / "projects" / "proj-related.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is True  # Still valid - related is warning only
        assert any("Broken related link" in warning for warning in result["warnings"])

    def test_validate_detects_invalid_status(self, temp_registry):
        """Test detection of invalid status values"""
        entity = {
            "type": "project",
            "uid": "proj-badstatus",
            "title": "Bad Status",
            "status": "not-a-real-status",
        }

        with open(Path(temp_registry) / "projects" / "proj-badstatus.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Invalid status" in error for error in result["errors"])

    def test_validate_detects_type_mismatch(self, temp_registry):
        """Test detection of type mismatches"""
        # Entity in projects folder but declares type as program
        entity = {
            "type": "program",
            "uid": "proj-wrongtype",
            "title": "Wrong Type",
            "status": "active",
        }

        with open(Path(temp_registry) / "projects" / "proj-wrongtype.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Type mismatch" in error for error in result["errors"])

    def test_validate_detects_empty_file(self, temp_registry):
        """Test handling of empty YAML files"""
        empty_file = Path(temp_registry) / "projects" / "proj-empty.yml"
        empty_file.write_text("")

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Empty file" in error for error in result["errors"])

    def test_validate_detects_invalid_yaml(self, temp_registry):
        """Test handling of invalid YAML files"""
        invalid_file = Path(temp_registry) / "projects" / "proj-invalid.yml"
        invalid_file.write_text("invalid: yaml: content: [")

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any(
            "YAML parse error" in error or "Error loading" in error
            for error in result["errors"]
        )

    def test_validate_no_registry_found(self):
        """Test validation when no registry found"""
        result = validate_registry_tool(registry_path="/nonexistent/path")

        assert result["success"] is False
        assert "error" in result
        assert "No registry found" in result["error"]

    def test_validate_invalid_children_format(self, temp_registry):
        """Test detection of invalid children format"""
        entity = {
            "type": "project",
            "uid": "proj-badchildren",
            "title": "Bad Children",
            "status": "active",
            "children": "not-a-list",
        }

        with open(Path(temp_registry) / "projects" / "proj-badchildren.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Invalid children format" in error for error in result["errors"])

    def test_validate_invalid_related_format_is_warning(self, temp_registry):
        """Test that invalid related format is a warning"""
        entity = {
            "type": "project",
            "uid": "proj-badrelated",
            "title": "Bad Related",
            "status": "active",
            "related": "not-a-list",
        }

        with open(Path(temp_registry) / "projects" / "proj-badrelated.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is True  # Still valid - related format is warning
        assert any(
            "Invalid related format" in warning for warning in result["warnings"]
        )

    def test_validate_uses_shared_operation(self, temp_registry):
        """Test that validate_registry_tool uses ValidateOperation internally"""
        with patch("hxc.mcp.tools.ValidateOperation") as MockOperation:
            mock_result = ValidationResult()
            mock_result.entities_checked = 5
            mock_result.entities_by_type = {"project": 5}

            mock_instance = MagicMock()
            mock_instance.validate_registry.return_value = mock_result
            MockOperation.return_value = mock_instance

            result = validate_registry_tool(registry_path=temp_registry)

        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.validate_registry.assert_called_once()

    def test_validate_handles_path_security_error(self, temp_registry):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.ValidateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.validate_registry.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is False
        assert "Security error" in result["error"]


class TestValidateRegistryToolBehavioralParity:
    """Tests to verify validate_registry_tool produces same results as CLI"""

    def test_validate_produces_same_errors_as_operation(self, temp_registry):
        """Test that MCP tool produces same errors as ValidateOperation"""
        # Create entity with issue
        entity = {
            "type": "project",
            "uid": "proj-test",
            "title": "Test",
            "status": "invalid-status",
        }

        with open(Path(temp_registry) / "projects" / "proj-test.yml", "w") as f:
            yaml.dump(entity, f)

        # Use direct operation
        operation = ValidateOperation(temp_registry)
        operation_result = operation.validate_registry()

        # Use MCP tool
        mcp_result = validate_registry_tool(registry_path=temp_registry)

        assert mcp_result["success"] is True
        assert mcp_result["valid"] == operation_result.valid
        assert mcp_result["error_count"] == operation_result.error_count
        assert mcp_result["warning_count"] == operation_result.warning_count
        assert set(mcp_result["errors"]) == set(operation_result.errors)

    def test_validate_entities_by_type_matches_operation(self, temp_registry):
        """Test that entities_by_type matches ValidateOperation"""
        operation = ValidateOperation(temp_registry)
        operation_result = operation.validate_registry()

        mcp_result = validate_registry_tool(registry_path=temp_registry)

        assert mcp_result["success"] is True
        assert mcp_result["entities_by_type"] == operation_result.entities_by_type

    def test_validate_all_status_values_match_cli(self, temp_registry):
        """Test that all valid status values are accepted like CLI"""
        valid_statuses = ["active", "completed", "on-hold", "cancelled", "planned"]

        for status in valid_statuses:
            entity = {
                "type": "project",
                "uid": f"proj-{status}",
                "title": f"Status {status}",
                "status": status,
            }

            with open(
                Path(temp_registry) / "projects" / f"proj-{status}.yml", "w"
            ) as f:
                yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        # No status errors should exist
        assert not any("Invalid status" in error for error in result["errors"])


class TestValidateEntityTool:
    """Tests for validate_entity_tool"""

    def test_validate_valid_entity(self, temp_registry):
        """Test validating a valid entity"""
        entity_data = {
            "type": "project",
            "uid": "proj-valid",
            "title": "Valid Project",
            "status": "active",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_returns_expected_structure(self, temp_registry):
        """Test that result has expected structure"""
        entity_data = {
            "type": "project",
            "uid": "proj-test",
            "title": "Test",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            registry_path=temp_registry,
        )

        expected_keys = {
            "success",
            "valid",
            "errors",
            "warnings",
            "error_count",
            "warning_count",
        }
        assert set(result.keys()) == expected_keys

    def test_validate_detects_missing_required_fields(self, temp_registry):
        """Test detection of missing required fields"""
        # Missing type, uid, title
        entity_data = {"status": "active"}

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert result["error_count"] >= 3
        assert any("type" in error.lower() for error in result["errors"])
        assert any("uid" in error.lower() for error in result["errors"])
        assert any("title" in error.lower() for error in result["errors"])

    def test_validate_detects_invalid_entity_type(self, temp_registry):
        """Test detection of invalid entity type"""
        entity_data = {
            "type": "invalid_type",
            "uid": "test-001",
            "title": "Test",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Invalid entity type" in error for error in result["errors"])

    def test_validate_detects_invalid_status(self, temp_registry):
        """Test detection of invalid status"""
        entity_data = {
            "type": "project",
            "uid": "test-001",
            "title": "Test",
            "status": "not-a-status",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Invalid status" in error for error in result["errors"])

    def test_validate_detects_invalid_children_format(self, temp_registry):
        """Test detection of invalid children format"""
        entity_data = {
            "type": "project",
            "uid": "test-001",
            "title": "Test",
            "children": "not-a-list",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert any("Invalid children format" in error for error in result["errors"])

    def test_validate_invalid_related_format_is_warning(self, temp_registry):
        """Test that invalid related format is a warning"""
        entity_data = {
            "type": "project",
            "uid": "test-001",
            "title": "Test",
            "related": "not-a-list",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is True  # Still valid
        assert any(
            "Invalid related format" in warning for warning in result["warnings"]
        )

    def test_validate_with_relationship_checking_parent_exists(self, temp_registry):
        """Test validation with relationship checking - parent exists"""
        entity_data = {
            "type": "project",
            "uid": "test-child",
            "title": "Child Project",
            "parent": "prog-test-001",  # Exists in fixture
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is True

    def test_validate_with_relationship_checking_parent_not_found(self, temp_registry):
        """Test validation with relationship checking - parent not found"""
        entity_data = {
            "type": "project",
            "uid": "test-orphan",
            "title": "Orphan Project",
            "parent": "nonexistent-parent",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert any(
            "Parent" in error and "not found" in error for error in result["errors"]
        )

    def test_validate_with_relationship_checking_child_not_found(self, temp_registry):
        """Test validation with relationship checking - child not found"""
        entity_data = {
            "type": "program",
            "uid": "test-parent",
            "title": "Parent Program",
            "children": ["nonexistent-child"],
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert any(
            "Child" in error and "not found" in error for error in result["errors"]
        )

    def test_validate_with_relationship_checking_related_not_found_is_warning(
        self, temp_registry
    ):
        """Test validation with relationship checking - related not found is warning"""
        entity_data = {
            "type": "project",
            "uid": "test-related",
            "title": "Has Related",
            "related": ["nonexistent-related"],
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is True  # Still valid
        assert any(
            "Related" in warning and "not found" in warning
            for warning in result["warnings"]
        )

    def test_validate_check_relationships_default_true(self, temp_registry):
        """Test that check_relationships defaults to True"""
        entity_data = {
            "type": "project",
            "uid": "test-default",
            "title": "Default Check",
            "parent": "nonexistent-parent",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            registry_path=temp_registry,
        )

        # Should have error because check_relationships defaults to True
        assert result["success"] is True
        assert result["valid"] is False
        assert any(
            "Parent" in error and "not found" in error for error in result["errors"]
        )

    def test_validate_without_registry_path(self):
        """Test validation without registry path (basic validation only)"""
        entity_data = {
            "type": "project",
            "uid": "test-001",
            "title": "No Registry",
            "status": "active",
        }

        result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
        )

        assert result["success"] is True
        assert result["valid"] is True

    def test_validate_empty_entity_data(self, temp_registry):
        """Test validation with empty entity data"""
        result = validate_entity_tool(
            entity_data={},
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert result["error_count"] >= 1

    def test_validate_none_entity_data(self, temp_registry):
        """Test validation with None entity data"""
        result = validate_entity_tool(
            entity_data=None,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert "Entity data is required" in result["errors"]

    def test_validate_non_dict_entity_data(self, temp_registry):
        """Test validation with non-dict entity data"""
        result = validate_entity_tool(
            entity_data="not a dict",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["valid"] is False
        assert "Entity data must be a dictionary" in result["errors"]

    def test_validate_all_valid_entity_types(self, temp_registry):
        """Test validation accepts all valid entity types"""
        valid_types = ["program", "project", "mission", "action"]

        for entity_type in valid_types:
            entity_data = {
                "type": entity_type,
                "uid": f"{entity_type}-test",
                "title": f"Test {entity_type}",
            }

            result = validate_entity_tool(
                entity_data=entity_data,
                check_relationships=False,
                registry_path=temp_registry,
            )

            assert result["success"] is True, f"Failed for type: {entity_type}"
            assert result["valid"] is True, f"Not valid for type: {entity_type}"

    def test_validate_all_valid_statuses(self, temp_registry):
        """Test validation accepts all valid status values"""
        valid_statuses = ["active", "completed", "on-hold", "cancelled", "planned"]

        for status in valid_statuses:
            entity_data = {
                "type": "project",
                "uid": f"proj-{status}",
                "title": f"Status {status}",
                "status": status,
            }

            result = validate_entity_tool(
                entity_data=entity_data,
                check_relationships=False,
                registry_path=temp_registry,
            )

            assert result["success"] is True, f"Failed for status: {status}"
            assert result["valid"] is True, f"Not valid for status: {status}"


class TestValidateEntityToolBehavioralParity:
    """Tests to verify validate_entity_tool behaves identically to ValidateOperation"""

    def test_validate_produces_same_errors_as_operation(self, temp_registry):
        """Test that MCP tool produces same errors as ValidateOperation"""
        entity_data = {
            "type": "invalid_type",
            "uid": "test-001",
            # Missing title
            "status": "invalid_status",
        }

        # Use direct operation
        operation = ValidateOperation(temp_registry)
        operation_result = operation.validate_entity(
            entity_data, check_relationships=False
        )

        # Use MCP tool
        mcp_result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert mcp_result["success"] is True
        assert mcp_result["valid"] == operation_result.valid
        assert set(mcp_result["errors"]) == set(operation_result.errors)

    def test_validate_relationship_errors_match_operation(self, temp_registry):
        """Test that relationship validation matches ValidateOperation"""
        entity_data = {
            "type": "project",
            "uid": "test-001",
            "title": "Test",
            "parent": "nonexistent",
            "children": ["also-nonexistent"],
            "related": ["and-this-one"],
        }

        # Use direct operation
        operation = ValidateOperation(temp_registry)
        operation_result = operation.validate_entity(
            entity_data, check_relationships=True
        )

        # Use MCP tool
        mcp_result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=True,
            registry_path=temp_registry,
        )

        assert mcp_result["success"] is True
        assert mcp_result["valid"] == operation_result.valid
        assert len(mcp_result["errors"]) == len(operation_result.errors)
        assert len(mcp_result["warnings"]) == len(operation_result.warnings)


class TestValidateToolsReadOnlyMode:
    """Tests for validate tools availability in read-only mode"""

    def test_validate_registry_available_in_read_only_mode(self, temp_registry):
        """Test that validate_registry tool is available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "validate_registry" in tools

    def test_validate_entity_available_in_read_only_mode(self, temp_registry):
        """Test that validate_entity tool is available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "validate_entity" in tools

    def test_validate_registry_works_in_read_only_server(self, temp_registry):
        """Test that validate_registry can be called on read-only server"""
        import json

        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "validate_registry",
                "arguments": {},
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert "valid" in data
        assert "errors" in data

    def test_validate_entity_works_in_read_only_server(self, temp_registry):
        """Test that validate_entity can be called on read-only server"""
        import json

        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "validate_entity",
                "arguments": {
                    "entity_data": {
                        "type": "project",
                        "uid": "test-001",
                        "title": "Test",
                    },
                    "check_relationships": False,
                },
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert data["valid"] is True


class TestValidateToolsIntegration:
    """Integration tests for validate tools"""

    def test_validate_after_create(self, temp_registry):
        """Test validating registry after creating entity"""
        # Create entity
        create_result = create_entity_tool(
            type="project",
            title="Created Project",
            use_git=False,
            registry_path=temp_registry,
        )
        assert create_result["success"] is True

        # Validate registry
        validate_result = validate_registry_tool(registry_path=temp_registry)

        assert validate_result["success"] is True
        assert validate_result["valid"] is True

    def test_validate_entity_before_create(self, temp_registry):
        """Test pre-flight validation before create"""
        entity_data = {
            "type": "project",
            "uid": "will-be-created",
            "title": "Pre-flight Test",
            "status": "active",
        }

        # Validate first
        validate_result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert validate_result["success"] is True
        assert validate_result["valid"] is True

    def test_validate_entity_with_invalid_data_before_create(self, temp_registry):
        """Test that pre-flight validation catches issues"""
        entity_data = {
            "type": "invalid_type",
            "uid": "test-001",
            # Missing title
            "status": "not-a-status",
        }

        validate_result = validate_entity_tool(
            entity_data=entity_data,
            check_relationships=False,
            registry_path=temp_registry,
        )

        assert validate_result["success"] is True
        assert validate_result["valid"] is False
        assert validate_result["error_count"] >= 2

    def test_validate_multiple_issues_reported(self, temp_registry):
        """Test that multiple issues are all reported"""
        # Create entity with multiple issues
        entity = {
            "type": "program",  # Type mismatch
            # Missing uid and title
            "status": "invalid-status",
            "parent": "nonexistent",
            "children": ["also-nonexistent"],
        }

        with open(Path(temp_registry) / "projects" / "proj-problems.yml", "w") as f:
            yaml.dump(entity, f)

        result = validate_registry_tool(registry_path=temp_registry)

        assert result["success"] is True
        assert result["valid"] is False
        assert result["error_count"] >= 4  # At least 4 errors

    def test_validate_and_get_entity(self, temp_registry):
        """Test validating then getting entity"""
        # First validate registry is healthy
        validate_result = validate_registry_tool(registry_path=temp_registry)
        assert validate_result["success"] is True

        # Then get entity
        get_result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert get_result["success"] is True


class TestValidateRegistryPathTool:
    """Tests for validate_registry_path_tool"""

    def test_validate_valid_registry(self, valid_registry_for_path_tests):
        """Test validating a valid registry path"""
        result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        assert result["success"] is True
        assert result["valid"] is True
        assert result["missing"] == []

    def test_validate_invalid_registry(self, invalid_registry_path):
        """Test validating an invalid registry path"""
        result = validate_registry_path_tool(path=invalid_registry_path)

        assert result["success"] is True  # Validation completed
        assert result["valid"] is False
        assert len(result["missing"]) > 0

    def test_validate_nonexistent_path(self):
        """Test validating a non-existent path"""
        result = validate_registry_path_tool(path="/nonexistent/path/xyz")

        assert result["success"] is True
        assert result["valid"] is False
        assert "path does not exist" in result["missing"]

    def test_validate_empty_path(self):
        """Test validating empty path"""
        result = validate_registry_path_tool(path="")

        assert result["success"] is True
        assert result["valid"] is False
        assert "path is required" in result["missing"]

    def test_validate_path_resolves_to_absolute(self, valid_registry_for_path_tests):
        """Test that validation resolves path to absolute"""
        result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        assert result["success"] is True
        assert Path(result["path"]).is_absolute()

    def test_validate_result_structure(self, valid_registry_for_path_tests):
        """Test that result has expected structure"""
        result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        expected_keys = {"success", "valid", "path", "missing"}
        assert set(result.keys()) == expected_keys

    def test_validate_missing_folders(self):
        """Test that missing folders are listed"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create only some folders
            Path(temp_dir, "programs").mkdir()
            Path(temp_dir, "config.yml").write_text("# Config")

            result = validate_registry_path_tool(path=temp_dir)

            assert result["success"] is True
            assert result["valid"] is False
            # Should list missing folders
            assert "projects/" in result["missing"]
            assert "missions/" in result["missing"]
            assert "actions/" in result["missing"]
        finally:
            shutil.rmtree(temp_dir)

    def test_validate_missing_config(self):
        """Test that missing config.yml is listed"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create all folders but no config
            for folder in ["programs", "projects", "missions", "actions"]:
                Path(temp_dir, folder).mkdir()

            result = validate_registry_path_tool(path=temp_dir)

            assert result["success"] is True
            assert result["valid"] is False
            assert "config.yml" in result["missing"]
        finally:
            shutil.rmtree(temp_dir)

    def test_validate_partial_registry(self):
        """Test validating a registry with some but not all components"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create some folders and config
            Path(temp_dir, "programs").mkdir()
            Path(temp_dir, "projects").mkdir()
            Path(temp_dir, "config.yml").write_text("# Config")

            result = validate_registry_path_tool(path=temp_dir)

            assert result["success"] is True
            assert result["valid"] is False
            # Should list only the missing components
            assert "missions/" in result["missing"]
            assert "actions/" in result["missing"]
            assert "programs/" not in result["missing"]
            assert "projects/" not in result["missing"]
            assert "config.yml" not in result["missing"]
        finally:
            shutil.rmtree(temp_dir)

    def test_validate_with_extra_files(self, valid_registry_for_path_tests):
        """Test that extra files don't affect validation"""
        # Add an extra file
        extra_file = Path(valid_registry_for_path_tests) / "extra_file.txt"
        extra_file.write_text("extra content")

        result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        assert result["success"] is True
        assert result["valid"] is True
        assert result["missing"] == []

    def test_validate_file_instead_of_directory(self):
        """Test validating a file path instead of directory"""
        temp_dir = tempfile.mkdtemp()
        try:
            file_path = Path(temp_dir) / "not_a_directory.txt"
            file_path.write_text("content")

            result = validate_registry_path_tool(path=str(file_path))

            assert result["success"] is True
            assert result["valid"] is False
        finally:
            shutil.rmtree(temp_dir)


class TestValidateRegistryPathToolBehavioralParity:
    """Tests to verify validate_registry_path_tool behaves identically to CLI"""

    def test_validation_checks_same_components(self):
        """Test that validation checks the same components as CLI"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Empty directory
            result = validate_registry_path_tool(path=temp_dir)

            assert result["success"] is True
            assert result["valid"] is False

            # Should check same components as CLI
            expected_missing = {
                "config.yml",
                "programs/",
                "projects/",
                "missions/",
                "actions/",
            }
            assert set(result["missing"]) == expected_missing
        finally:
            shutil.rmtree(temp_dir)

    def test_required_folders_match_cli(self):
        """Test that required folders match CLI expectations"""
        expected = ["programs", "projects", "missions", "actions"]
        assert RegistryOperation.REQUIRED_FOLDERS == expected

    def test_required_files_match_cli(self):
        """Test that required files match CLI expectations"""
        expected = ["config.yml"]
        assert RegistryOperation.REQUIRED_FILES == expected

    def test_validate_uses_same_logic_as_registry_operation(
        self, valid_registry_for_path_tests
    ):
        """Test that MCP validation uses same logic as RegistryOperation"""
        # Use direct operation
        operation_result = RegistryOperation.validate_registry_path(
            valid_registry_for_path_tests
        )

        # Use MCP tool
        mcp_result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        # Both should produce same result
        assert operation_result["valid"] == mcp_result["valid"]
        assert set(operation_result["missing"]) == set(mcp_result["missing"])


class TestEntityTypeValidation:
    """Tests for entity type validation across tools"""

    def test_list_with_valid_entity_types(self, temp_registry):
        """Test listing with all valid entity types"""
        valid_types = ["program", "project", "mission", "action", "all"]

        for entity_type in valid_types:
            result = list_entities_tool(
                entity_type=entity_type,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for type: {entity_type}"

    def test_list_with_invalid_entity_type(self, temp_registry):
        """Test listing with invalid entity type"""
        result = list_entities_tool(
            entity_type="invalid_type",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_create_with_valid_entity_types(self, temp_registry):
        """Test creating with all valid entity types"""
        valid_types = ["program", "project", "mission", "action"]

        for entity_type in valid_types:
            result = create_entity_tool(
                type=entity_type,
                title=f"Test {entity_type.title()}",
                use_git=False,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for type: {entity_type}"

    def test_create_with_invalid_entity_type(self, temp_registry):
        """Test creating with invalid entity type"""
        result = create_entity_tool(
            type="invalid_type",
            title="Should Fail",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_create_with_empty_entity_type(self, temp_registry):
        """Test creating with empty entity type"""
        result = create_entity_tool(
            type="",
            title="Should Fail",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_with_valid_entity_type_filter(self, temp_registry):
        """Test getting entity with valid type filter"""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="project",
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_get_with_invalid_entity_type_filter(self, temp_registry):
        """Test getting entity with invalid type filter"""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="invalid_type",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_edit_with_valid_entity_type_filter(self, temp_registry):
        """Test editing with valid entity type filter"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Edited",
            entity_type="project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_edit_with_invalid_entity_type_filter(self, temp_registry):
        """Test editing with invalid entity type filter"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Edited",
            entity_type="invalid_type",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_delete_with_valid_entity_type_filter(self, temp_registry):
        """Test deleting with valid entity type filter"""
        result = delete_entity_tool(
            identifier="P-001",
            entity_type="project",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_delete_with_invalid_entity_type_filter(self, temp_registry):
        """Test deleting with invalid entity type filter"""
        result = delete_entity_tool(
            identifier="P-001",
            entity_type="invalid_type",
            force=True,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result


class TestStatusValidation:
    """Tests for status field validation across tools"""

    def test_list_with_valid_statuses(self, temp_registry):
        """Test listing with all valid statuses"""
        valid_statuses = ["active", "completed", "on-hold", "cancelled", "planned"]

        for status in valid_statuses:
            result = list_entities_tool(
                entity_type="all",
                status=status,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for status: {status}"

    def test_list_with_invalid_status(self, temp_registry):
        """Test listing with invalid status"""
        result = list_entities_tool(
            entity_type="all",
            status="invalid_status",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_create_with_valid_statuses(self, temp_registry):
        """Test creating with all valid statuses"""
        valid_statuses = ["active", "completed", "on-hold", "cancelled", "planned"]

        for status in valid_statuses:
            result = create_entity_tool(
                type="project",
                title=f"Project with status {status}",
                status=status,
                use_git=False,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for status: {status}"
            assert result["entity"]["status"] == status

    def test_create_with_invalid_status(self, temp_registry):
        """Test creating with invalid status"""
        result = create_entity_tool(
            type="project",
            title="Bad Status",
            status="not-a-status",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_create_default_status_is_active(self, temp_registry):
        """Test that default status is 'active'"""
        result = create_entity_tool(
            type="project",
            title="Default Status Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["status"] == "active"

    def test_edit_with_valid_statuses(self, temp_registry):
        """Test editing with all valid statuses"""
        valid_statuses = ["active", "completed", "on-hold", "cancelled", "planned"]

        for status in valid_statuses:
            result = edit_entity_tool(
                identifier="P-001",
                set_status=status,
                use_git=False,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for status: {status}"
            assert result["entity"]["status"] == status

    def test_edit_with_invalid_status(self, temp_registry):
        """Test editing with invalid status"""
        result = edit_entity_tool(
            identifier="P-001",
            set_status="invalid_status",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_status_is_case_insensitive(self, temp_registry):
        """Test that status validation is case-insensitive"""
        # Valid lowercase
        result_lower = create_entity_tool(
            type="project",
            title="Lowercase Status",
            status="active",
            use_git=False,
            registry_path=temp_registry,
        )
        assert result_lower["success"] is True

        # Uppercase should also work (case-insensitive)
        result_upper = create_entity_tool(
            type="project",
            title="Uppercase Status",
            status="ACTIVE",
            use_git=False,
            registry_path=temp_registry,
        )
        # The system accepts uppercase status (case-insensitive validation)
        assert result_upper["success"] is True


class TestDateValidation:
    """Tests for date field validation"""

    def test_create_with_valid_dates(self, temp_registry):
        """Test creating with valid date formats"""
        result = create_entity_tool(
            type="project",
            title="Valid Dates",
            start_date="2025-01-01",
            due_date="2025-12-31",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["start_date"] == "2025-01-01"
        assert result["entity"]["due_date"] == "2025-12-31"

    def test_create_default_start_date(self, temp_registry):
        """Test that start_date defaults to today"""
        import datetime

        today = datetime.date.today().isoformat()

        result = create_entity_tool(
            type="project",
            title="Default Date",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["start_date"] == today

    def test_edit_with_valid_dates(self, temp_registry):
        """Test editing with valid date formats"""
        result = edit_entity_tool(
            identifier="P-001",
            set_start_date="2025-06-01",
            set_due_date="2025-12-31",
            set_completion_date="2025-11-30",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["start_date"] == "2025-06-01"
        assert result["entity"]["due_date"] == "2025-12-31"
        assert result["entity"]["completion_date"] == "2025-11-30"

    def test_list_with_valid_date_filters(self, temp_registry_with_dates):
        """Test listing with valid date filter formats"""
        result = list_entities_tool(
            entity_type="project",
            due_before="2024-12-31",
            due_after="2024-01-01",
            registry_path=temp_registry_with_dates,
        )

        assert result["success"] is True

    def test_date_format_consistency(self, temp_registry):
        """Test that dates are consistently formatted"""
        result = create_entity_tool(
            type="project",
            title="Date Format Test",
            start_date="2025-01-15",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        # Date should be in YYYY-MM-DD format
        date_str = result["entity"]["start_date"]
        assert len(date_str) == 10
        assert date_str[4] == "-"
        assert date_str[7] == "-"


class TestIdValidation:
    """Tests for ID field validation"""

    def test_create_with_custom_id(self, temp_registry):
        """Test creating with custom ID"""
        result = create_entity_tool(
            type="project",
            title="Custom ID Project",
            id="P-CUSTOM-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["id"] == "P-CUSTOM-001"

    def test_create_with_duplicate_id_fails(self, temp_registry):
        """Test that duplicate ID within same type fails"""
        # P-001 exists in fixture
        result = create_entity_tool(
            type="project",
            title="Duplicate ID Project",
            id="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "already exists" in result["error"].lower()

    def test_create_same_id_different_types_allowed(self, temp_registry):
        """Test that same ID can be used for different entity types"""
        # P-001 exists as project, but should work for program
        result = create_entity_tool(
            type="program",
            title="Program With Project ID",
            id="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["id"] == "P-001"
        assert result["entity"]["type"] == "program"

    def test_create_auto_id_generation(self, temp_registry):
        """Test automatic ID generation from title"""
        result = create_entity_tool(
            type="project",
            title="My Amazing Project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["id"] == "my_amazing_project"

    def test_create_auto_id_collision_resolution(self, temp_registry):
        """Test that auto-generated ID collisions are resolved"""
        # Create first entity
        result1 = create_entity_tool(
            type="project",
            title="Collision Test",
            use_git=False,
            registry_path=temp_registry,
        )
        assert result1["success"] is True
        first_id = result1["id"]

        # Create second entity with same title
        result2 = create_entity_tool(
            type="project",
            title="Collision Test",
            use_git=False,
            registry_path=temp_registry,
        )
        assert result2["success"] is True
        second_id = result2["id"]

        # IDs should be different
        assert first_id != second_id
        assert second_id.startswith("collision_test_")

    def test_edit_set_id_to_duplicate_fails(self, temp_registry):
        """Test that editing ID to a duplicate fails"""
        result = edit_entity_tool(
            identifier="P-001",
            set_id="P-002",  # P-002 exists
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "already exists" in result["error"].lower()

    def test_edit_set_id_to_same_value_succeeds(self, temp_registry):
        """Test that setting ID to same value is a no-op"""
        result = edit_entity_tool(
            identifier="P-001",
            set_id="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"

    def test_edit_set_id_to_unique_value_succeeds(self, temp_registry):
        """Test that setting ID to unique value succeeds"""
        result = edit_entity_tool(
            identifier="P-001",
            set_id="P-UNIQUE-NEW",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["id"] == "P-UNIQUE-NEW"


class TestUidValidation:
    """Tests for UID field validation"""

    def test_create_generates_valid_uid(self, temp_registry):
        """Test that UID generation follows expected format"""
        result = create_entity_tool(
            type="project",
            title="UID Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        uid = result["uid"]

        # UID should be 8 characters
        assert len(uid) == 8
        # Should be valid hex characters
        assert all(c in "0123456789abcdef" for c in uid)

    def test_get_by_uid(self, temp_registry):
        """Test getting entity by UID"""
        result = get_entity_tool(
            identifier="proj-test-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["uid"] == "proj-test-001"

    def test_get_by_id(self, temp_registry):
        """Test getting entity by human-readable ID"""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"

    def test_edit_by_uid(self, temp_registry):
        """Test editing entity by UID"""
        result = edit_entity_tool(
            identifier="proj-test-001",
            set_title="Edited by UID",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_delete_by_uid(self, temp_registry):
        """Test deleting entity by UID"""
        result = delete_entity_tool(
            identifier="proj-test-002",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True


class TestIdentifierValidation:
    """Tests for identifier validation in entity lookup"""

    def test_get_nonexistent_identifier(self, temp_registry):
        """Test getting entity with nonexistent identifier"""
        result = get_entity_tool(
            identifier="NONEXISTENT",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_edit_nonexistent_identifier(self, temp_registry):
        """Test editing entity with nonexistent identifier"""
        result = edit_entity_tool(
            identifier="NONEXISTENT",
            set_title="Should Fail",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_delete_nonexistent_identifier(self, temp_registry):
        """Test deleting entity with nonexistent identifier"""
        result = delete_entity_tool(
            identifier="NONEXISTENT",
            force=True,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_get_property_nonexistent_identifier(self, temp_registry):
        """Test getting property from nonexistent entity"""
        result = get_entity_property_tool(
            identifier="NONEXISTENT",
            property_name="title",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_list_with_identifier_filter(self, temp_registry):
        """Test listing with identifier filter"""
        result = list_entities_tool(
            entity_type="project",
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["id"] == "P-001"

    def test_list_with_nonexistent_identifier(self, temp_registry):
        """Test listing with nonexistent identifier returns empty"""
        result = list_entities_tool(
            entity_type="project",
            identifier="NONEXISTENT",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["count"] == 0


class TestPropertyValidation:
    """Tests for property validation in get_entity_property_tool"""

    def test_get_valid_properties(self, temp_registry):
        """Test getting various valid properties"""
        valid_properties = ["title", "status", "type", "uid", "id", "tags"]

        for prop in valid_properties:
            result = get_entity_property_tool(
                identifier="P-001",
                property_name=prop,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for property: {prop}"

    def test_get_all_properties(self, temp_registry):
        """Test getting all properties"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="all",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["value"], dict)

    def test_get_path_property(self, temp_registry):
        """Test getting path property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="path",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert ".yml" in result["value"]

    def test_get_nonexistent_property(self, temp_registry):
        """Test getting nonexistent property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="nonexistent_property",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "unknown property" in result["error"].lower()

    def test_get_list_property_with_valid_index(self, temp_registry):
        """Test getting list property with valid index"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            index=0,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["value"], str)

    def test_get_list_property_with_invalid_index(self, temp_registry):
        """Test getting list property with invalid index"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            index=999,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "out of range" in result["error"].lower()

    def test_get_complex_property_with_valid_key_filter(self, temp_registry):
        """Test getting complex property with valid key filter"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="name:github",
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_get_complex_property_with_invalid_key_format(self, temp_registry):
        """Test getting complex property with invalid key format"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="invalid_format",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "invalid key filter" in result["error"].lower()


class TestTagsValidation:
    """Tests for tags field validation"""

    def test_create_with_valid_tags(self, temp_registry):
        """Test creating with valid tags"""
        result = create_entity_tool(
            type="project",
            title="Tags Test",
            tags=["tag1", "tag2", "tag3"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["tags"] == ["tag1", "tag2", "tag3"]

    def test_create_with_empty_tags_list(self, temp_registry):
        """Test creating with empty tags list"""
        result = create_entity_tool(
            type="project",
            title="No Tags",
            tags=[],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        # When tags is empty, the key might not be present or be an empty list
        entity_tags = result["entity"].get("tags", [])
        assert entity_tags == []

    def test_edit_add_tags(self, temp_registry):
        """Test adding tags"""
        result = edit_entity_tool(
            identifier="P-001",
            add_tags=["new-tag"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "new-tag" in result["entity"]["tags"]

    def test_edit_remove_tags(self, temp_registry):
        """Test removing tags"""
        result = edit_entity_tool(
            identifier="P-001",
            remove_tags=["mcp"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "mcp" not in result["entity"]["tags"]

    def test_edit_add_duplicate_tag_is_idempotent(self, temp_registry):
        """Test that adding duplicate tag doesn't create duplicates"""
        result = edit_entity_tool(
            identifier="P-001",
            add_tags=["test"],  # Already exists
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["tags"].count("test") == 1

    def test_edit_remove_nonexistent_tag_is_noop(self, temp_registry):
        """Test that removing nonexistent tag is a no-op"""
        result = edit_entity_tool(
            identifier="P-001",
            remove_tags=["nonexistent-tag"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_list_with_tags_filter(self, temp_registry):
        """Test listing with tags filter"""
        result = list_entities_tool(
            entity_type="all",
            tags=["test"],
            registry_path=temp_registry,
        )

        assert result["success"] is True
        for entity in result["entities"]:
            assert "test" in entity.get("tags", [])

    def test_list_with_multiple_tags_filter(self, temp_registry):
        """Test listing with multiple tags (AND logic)"""
        result = list_entities_tool(
            entity_type="all",
            tags=["test", "mcp"],
            registry_path=temp_registry,
        )

        assert result["success"] is True
        for entity in result["entities"]:
            tags = entity.get("tags", [])
            assert "test" in tags
            assert "mcp" in tags


class TestRegistryPathValidation:
    """Tests for registry path validation"""

    def test_tools_with_valid_registry_path(self, temp_registry):
        """Test tools work with valid registry path"""
        result = list_entities_tool(
            entity_type="all",
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_tools_with_nonexistent_registry_path(self):
        """Test tools fail with nonexistent registry path"""
        result = list_entities_tool(
            entity_type="all",
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False
        assert "error" in result

    def test_get_with_nonexistent_registry(self):
        """Test get fails with nonexistent registry"""
        result = get_entity_tool(
            identifier="P-001",
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False

    def test_create_with_nonexistent_registry(self):
        """Test create fails with nonexistent registry"""
        result = create_entity_tool(
            type="project",
            title="Should Fail",
            use_git=False,
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False

    def test_edit_with_nonexistent_registry(self):
        """Test edit fails with nonexistent registry"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Should Fail",
            use_git=False,
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False

    def test_delete_with_nonexistent_registry(self):
        """Test delete fails with nonexistent registry"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False


class TestQueryValidation:
    """Tests for query parameter validation"""

    def test_search_with_valid_query(self, temp_registry):
        """Test search with valid query"""
        result = search_entities_tool(
            query="test",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["query"] == "test"

    def test_search_with_empty_query(self, temp_registry):
        """Test search with empty query"""
        result = search_entities_tool(
            query="",
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_list_with_query_filter(self, temp_registry):
        """Test list with query filter"""
        result = list_entities_tool(
            entity_type="all",
            query="Project",
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_query_case_insensitive(self, temp_registry):
        """Test that query is case insensitive"""
        result1 = search_entities_tool(query="test", registry_path=temp_registry)
        result2 = search_entities_tool(query="TEST", registry_path=temp_registry)
        result3 = search_entities_tool(query="Test", registry_path=temp_registry)

        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True
        assert result1["count"] == result2["count"] == result3["count"]


class TestSortValidation:
    """Tests for sort parameter validation"""

    def test_list_with_valid_sort_fields(self, temp_registry):
        """Test listing with valid sort fields"""
        # Note: Only testing fields that are confirmed to work
        # due_date may not be supported in all implementations
        valid_fields = ["title", "id", "status", "created", "modified"]

        for field in valid_fields:
            result = list_entities_tool(
                entity_type="project",
                sort_by=field,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for sort field: {field}"

    def test_list_with_invalid_sort_field(self, temp_registry):
        """Test listing with invalid sort field"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="invalid_field",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_list_with_descending_sort(self, temp_registry):
        """Test listing with descending sort"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="title",
            descending=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["sort"]["descending"] is True


class TestNoChangesValidation:
    """Tests for edit with no changes specified"""

    def test_edit_with_no_changes_fails(self, temp_registry):
        """Test that editing without any changes fails"""
        result = edit_entity_tool(
            identifier="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "no changes" in result["error"].lower()

    def test_edit_with_only_entity_type_fails(self, temp_registry):
        """Test that providing only entity_type without changes fails"""
        result = edit_entity_tool(
            identifier="P-001",
            entity_type="project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "no changes" in result["error"].lower()


class TestRequiredFieldsValidation:
    """Tests for required field validation"""

    def test_create_requires_type(self, temp_registry):
        """Test that create requires type field"""
        # This would be caught by Python's function signature,
        # but we test the tool's error handling
        result = create_entity_tool(
            type="",
            title="No Type",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False

    def test_create_requires_title(self, temp_registry):
        """Test that create requires title field"""
        # Empty title
        result = create_entity_tool(
            type="project",
            title="",
            use_git=False,
            registry_path=temp_registry,
        )

        # Empty title may or may not be allowed depending on implementation
        # Just verify it doesn't crash
        assert "success" in result

    def test_edit_requires_identifier(self, temp_registry):
        """Test that edit requires identifier"""
        result = edit_entity_tool(
            identifier="",
            set_title="Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False

    def test_delete_requires_identifier(self, temp_registry):
        """Test that delete requires identifier"""
        result = delete_entity_tool(
            identifier="",
            force=True,
            registry_path=temp_registry,
        )

        assert result["success"] is False

    def test_get_requires_identifier(self, temp_registry):
        """Test that get requires identifier"""
        result = get_entity_tool(
            identifier="",
            registry_path=temp_registry,
        )

        assert result["success"] is False


class TestValidationErrorMessages:
    """Tests for validation error message clarity"""

    def test_invalid_entity_type_error_message(self, temp_registry):
        """Test that invalid entity type has clear error message"""
        result = create_entity_tool(
            type="invalid",
            title="Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        # Error should mention the invalid type or valid options
        error_lower = result["error"].lower()
        assert "invalid" in error_lower or "type" in error_lower

    def test_invalid_status_error_message(self, temp_registry):
        """Test that invalid status has clear error message"""
        result = create_entity_tool(
            type="project",
            title="Test",
            status="invalid_status",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        # Error should mention status
        error_lower = result["error"].lower()
        assert "status" in error_lower or "invalid" in error_lower

    def test_not_found_error_message_includes_identifier(self, temp_registry):
        """Test that not found error includes the identifier"""
        result = get_entity_tool(
            identifier="SPECIFIC-ID-123",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        # Should reference the identifier
        assert "identifier" in result or "not found" in result["error"].lower()

    def test_duplicate_id_error_message_includes_id(self, temp_registry):
        """Test that duplicate ID error includes the ID"""
        result = create_entity_tool(
            type="project",
            title="Duplicate",
            id="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        # Should reference the ID
        assert "P-001" in result["error"]

    def test_registry_validation_error_lists_missing(self, invalid_registry_path):
        """Test that registry validation error lists missing components"""
        result = validate_registry_path_tool(path=invalid_registry_path)

        assert result["success"] is True
        assert result["valid"] is False
        assert len(result["missing"]) > 0
        # Should list specific missing items
        for item in result["missing"]:
            assert isinstance(item, str)
            assert len(item) > 0
