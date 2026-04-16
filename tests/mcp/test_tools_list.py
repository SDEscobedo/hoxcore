"""
Tests for list_entities_tool and search_entities_tool in MCP Tools.

This module tests the tools that enable listing and searching entities
in HoxCore registries through the Model Context Protocol.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hxc.core.enums import EntityStatus, EntityType, SortField
from hxc.core.operations.list import ListOperation, ListOperationError
from hxc.mcp.tools import (
    list_entities_tool,
    search_entities_tool,
)

from .test_tools_common import (
    verify_error_result,
    verify_list_result,
    verify_success_result,
)


class TestListEntitiesTool:
    """Tests for list_entities_tool"""

    def test_list_all_entities(self, temp_registry):
        """Test listing all entities"""
        result = list_entities_tool(entity_type="all", registry_path=temp_registry)

        assert result["success"] is True
        assert "entities" in result
        assert result["count"] > 0
        assert len(result["entities"]) >= 5

    def test_list_projects_only(self, temp_registry):
        """Test listing only projects"""
        result = list_entities_tool(entity_type="project", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] == 2

        for entity in result["entities"]:
            assert entity["type"] == "project"

    def test_list_programs_only(self, temp_registry):
        """Test listing only programs"""
        result = list_entities_tool(entity_type="program", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["type"] == "program"

    def test_list_missions_only(self, temp_registry):
        """Test listing only missions"""
        result = list_entities_tool(entity_type="mission", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["type"] == "mission"

    def test_list_actions_only(self, temp_registry):
        """Test listing only actions"""
        result = list_entities_tool(entity_type="action", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["type"] == "action"

    def test_list_with_status_filter(self, temp_registry):
        """Test listing with status filter"""
        result = list_entities_tool(
            entity_type="all", status="active", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] > 0

        for entity in result["entities"]:
            assert entity["status"] == "active"

    def test_list_with_tags_filter(self, temp_registry):
        """Test listing with tags filter"""
        result = list_entities_tool(
            entity_type="all", tags=["test"], registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] > 0

        for entity in result["entities"]:
            assert "test" in entity.get("tags", [])

    def test_list_with_multiple_tags_filter(self, temp_registry):
        """Test listing with multiple tags filter"""
        result = list_entities_tool(
            entity_type="all", tags=["test", "mcp"], registry_path=temp_registry
        )

        assert result["success"] is True

        for entity in result["entities"]:
            entity_tags = entity.get("tags", [])
            assert "test" in entity_tags
            assert "mcp" in entity_tags

    def test_list_with_category_filter(self, temp_registry):
        """Test listing with category filter"""
        result = list_entities_tool(
            entity_type="all",
            category="software.dev/cli-tool",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["count"] > 0

        for entity in result["entities"]:
            assert entity["category"] == "software.dev/cli-tool"

    def test_list_with_parent_filter(self, temp_registry):
        """Test listing with parent filter"""
        result = list_entities_tool(
            entity_type="all", parent="prog-test-001", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] > 0

        for entity in result["entities"]:
            assert entity.get("parent") == "prog-test-001"

    def test_list_with_max_items(self, temp_registry):
        """Test listing with max items limit"""
        result = list_entities_tool(
            entity_type="all", max_items=2, registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] <= 2
        assert len(result["entities"]) <= 2

    def test_list_with_sort_by_title(self, temp_registry):
        """Test listing with sort by title"""
        result = list_entities_tool(
            entity_type="project", sort_by="title", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] > 1

        titles = [e["title"] for e in result["entities"]]
        assert titles == sorted(titles)

    def test_list_with_sort_descending(self, temp_registry):
        """Test listing with descending sort"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="title",
            descending=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["count"] > 1

        titles = [e["title"] for e in result["entities"]]
        assert titles == sorted(titles, reverse=True)

    def test_list_with_invalid_entity_type(self, temp_registry):
        """Test listing with invalid entity type"""
        result = list_entities_tool(entity_type="invalid", registry_path=temp_registry)

        assert result["success"] is False
        assert "error" in result

    def test_list_with_invalid_status(self, temp_registry):
        """Test listing with invalid status"""
        result = list_entities_tool(
            entity_type="all", status="invalid", registry_path=temp_registry
        )

        assert result["success"] is False
        assert "error" in result

    def test_list_with_no_registry(self):
        """Test listing with no registry"""
        result = list_entities_tool(
            entity_type="all", registry_path="/nonexistent/path"
        )

        assert result["success"] is False
        assert "error" in result

    def test_list_filters_metadata(self, temp_registry):
        """Test that filters metadata is included in result"""
        result = list_entities_tool(
            entity_type="project",
            status="active",
            tags=["test"],
            category="software.dev/cli-tool",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["type"] == "project"
        assert result["filters"]["status"] == "active"
        assert result["filters"]["tags"] == ["test"]
        assert result["filters"]["category"] == "software.dev/cli-tool"

    def test_list_sort_metadata(self, temp_registry):
        """Test that sort metadata is included in result"""
        result = list_entities_tool(
            entity_type="all",
            sort_by="title",
            descending=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "sort" in result
        assert result["sort"]["field"] == "title"
        assert result["sort"]["descending"] is True


class TestListEntitiesToolIdentifierFilter:
    """Tests for identifier filter in list_entities_tool"""

    def test_list_with_identifier_filter_by_id(self, temp_registry):
        """Test filtering by entity ID"""
        result = list_entities_tool(
            entity_type="project", identifier="P-001", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["id"] == "P-001"

    def test_list_with_identifier_filter_by_uid(self, temp_registry):
        """Test filtering by entity UID"""
        result = list_entities_tool(
            entity_type="project",
            identifier="proj-test-001",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["uid"] == "proj-test-001"

    def test_list_with_identifier_no_match(self, temp_registry):
        """Test filtering by identifier with no match"""
        result = list_entities_tool(
            entity_type="project", identifier="NONEXISTENT", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] == 0

    def test_list_with_identifier_across_types(self, temp_registry):
        """Test filtering by identifier across all entity types"""
        result = list_entities_tool(
            entity_type="all", identifier="PRG-001", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["type"] == "program"

    def test_list_filters_metadata_includes_identifier(self, temp_registry):
        """Test that filters metadata includes identifier"""
        result = list_entities_tool(
            entity_type="project", identifier="P-001", registry_path=temp_registry
        )

        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["identifier"] == "P-001"


class TestListEntitiesToolQueryFilter:
    """Tests for query filter in list_entities_tool"""

    def test_list_with_query_matches_title(self, temp_registry):
        """Test query filter matches in title"""
        result = list_entities_tool(
            entity_type="project", query="Project One", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] >= 1

        found = False
        for entity in result["entities"]:
            if "Project One" in entity["title"]:
                found = True
                break
        assert found

    def test_list_with_query_matches_description(self, temp_registry):
        """Test query filter matches in description"""
        result = list_entities_tool(
            entity_type="project", query="MCP tools", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] >= 1

    def test_list_with_query_case_insensitive(self, temp_registry):
        """Test that query filter is case insensitive"""
        result1 = list_entities_tool(
            entity_type="project", query="test", registry_path=temp_registry
        )

        result2 = list_entities_tool(
            entity_type="project", query="TEST", registry_path=temp_registry
        )

        result3 = list_entities_tool(
            entity_type="project", query="Test", registry_path=temp_registry
        )

        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True
        assert result1["count"] == result2["count"] == result3["count"]

    def test_list_with_query_no_match(self, temp_registry):
        """Test query filter with no matches"""
        result = list_entities_tool(
            entity_type="project",
            query="nonexistent query string xyz",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["count"] == 0

    def test_list_with_query_combined_with_other_filters(self, temp_registry):
        """Test query filter combined with other filters"""
        result = list_entities_tool(
            entity_type="project",
            query="test",
            status="active",
            tags=["mcp"],
            registry_path=temp_registry,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert entity["status"] == "active"
            assert "mcp" in entity.get("tags", [])

    def test_list_filters_metadata_includes_query(self, temp_registry):
        """Test that filters metadata includes query"""
        result = list_entities_tool(
            entity_type="project", query="test", registry_path=temp_registry
        )

        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["query"] == "test"


class TestListEntitiesToolDateFilters:
    """Tests for date range filters in list_entities_tool"""

    def test_list_with_due_before_filter(self, temp_registry_with_dates):
        """Test filtering by due date before"""
        result = list_entities_tool(
            entity_type="project",
            due_before="2024-07-01",
            registry_path=temp_registry_with_dates,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            if entity.get("due_date"):
                assert entity["due_date"] <= "2024-07-01"

    def test_list_with_due_after_filter(self, temp_registry_with_dates):
        """Test filtering by due date after"""
        result = list_entities_tool(
            entity_type="project",
            due_after="2024-07-01",
            registry_path=temp_registry_with_dates,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert entity.get("due_date")  # Must have due_date
            assert entity["due_date"] >= "2024-07-01"

    def test_list_with_date_range_filter(self, temp_registry_with_dates):
        """Test filtering by date range"""
        result = list_entities_tool(
            entity_type="project",
            due_after="2024-04-01",
            due_before="2024-10-01",
            registry_path=temp_registry_with_dates,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert entity.get("due_date")
            assert "2024-04-01" <= entity["due_date"] <= "2024-10-01"

    def test_list_due_after_excludes_no_due_date(self, temp_registry_with_dates):
        """Test that due_after filter excludes entities without due_date"""
        result = list_entities_tool(
            entity_type="project",
            due_after="2024-01-01",
            registry_path=temp_registry_with_dates,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert "due_date" in entity and entity["due_date"] is not None

    def test_list_filters_metadata_includes_date_filters(
        self, temp_registry_with_dates
    ):
        """Test that filters metadata includes date filters"""
        result = list_entities_tool(
            entity_type="project",
            due_before="2024-12-31",
            due_after="2024-01-01",
            registry_path=temp_registry_with_dates,
        )

        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["due_before"] == "2024-12-31"
        assert result["filters"]["due_after"] == "2024-01-01"


class TestListEntitiesToolFileMetadata:
    """Tests for file metadata handling in list_entities_tool"""

    def test_list_with_file_metadata_true(self, temp_registry):
        """Test listing with file metadata included"""
        result = list_entities_tool(
            entity_type="project",
            include_file_metadata=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert "_file" in entity
            assert "path" in entity["_file"]
            assert "name" in entity["_file"]
            assert "created" in entity["_file"]
            assert "modified" in entity["_file"]

    def test_list_with_file_metadata_false(self, temp_registry):
        """Test listing without file metadata"""
        result = list_entities_tool(
            entity_type="project",
            include_file_metadata=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert "_file" not in entity

    def test_list_default_excludes_file_metadata(self, temp_registry):
        """Test that file metadata is excluded by default"""
        result = list_entities_tool(entity_type="project", registry_path=temp_registry)

        assert result["success"] is True

        for entity in result["entities"]:
            assert "_file" not in entity

    def test_list_sort_by_created_with_file_metadata(self, temp_registry):
        """Test sorting by created date with file metadata enabled"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="created",
            include_file_metadata=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        # Verify created dates are sorted
        created_dates = [e["_file"]["created"] for e in result["entities"]]
        assert created_dates == sorted(created_dates)

    def test_list_sort_by_modified_with_file_metadata(self, temp_registry):
        """Test sorting by modified date with file metadata enabled"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="modified",
            include_file_metadata=True,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        # Verify modified dates are sorted
        modified_dates = [e["_file"]["modified"] for e in result["entities"]]
        assert modified_dates == sorted(modified_dates)

    def test_list_sort_by_created_without_file_metadata(self, temp_registry):
        """Test sorting by created date works even without file metadata in output"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="created",
            include_file_metadata=False,
            registry_path=temp_registry,
        )

        # Should still work (sorting happens on raw data)
        assert result["success"] is True


class TestListEntitiesToolUsesSharedOperation:
    """Tests to verify list_entities_tool uses the shared ListOperation"""

    def test_list_uses_list_operation(self, temp_registry):
        """Test that list_entities_tool uses ListOperation internally"""
        with patch("hxc.mcp.tools.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.return_value = {
                "success": True,
                "entities": [],
                "count": 0,
                "filters": {"types": ["project"]},
                "sort": {"field": "title", "descending": False},
            }
            MockOperation.return_value = mock_instance

            result = list_entities_tool(
                entity_type="project", registry_path=temp_registry
            )

        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.list_entities.assert_called_once()

    def test_list_passes_all_filters_to_operation(self, temp_registry):
        """Test that list_entities_tool passes all filter parameters to ListOperation"""
        with patch("hxc.mcp.tools.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.return_value = {
                "success": True,
                "entities": [],
                "count": 0,
                "filters": {},
                "sort": {"field": "title", "descending": False},
            }
            MockOperation.return_value = mock_instance

            result = list_entities_tool(
                entity_type="project",
                status="active",
                tags=["test"],
                category="software",
                parent="P-000",
                identifier="P-001",
                query="search term",
                due_before="2024-12-31",
                due_after="2024-01-01",
                sort_by="due_date",
                descending=True,
                max_items=10,
                include_file_metadata=True,
                registry_path=temp_registry,
            )

        # Verify the call arguments
        call_kwargs = mock_instance.list_entities.call_args[1]
        assert call_kwargs["status"] == EntityStatus.ACTIVE
        assert call_kwargs["tags"] == ["test"]
        assert call_kwargs["category"] == "software"
        assert call_kwargs["parent"] == "P-000"
        assert call_kwargs["identifier"] == "P-001"
        assert call_kwargs["query"] == "search term"
        assert call_kwargs["due_before"] == "2024-12-31"
        assert call_kwargs["due_after"] == "2024-01-01"
        assert call_kwargs["sort_field"] == SortField.DUE_DATE
        assert call_kwargs["descending"] is True
        assert call_kwargs["max_items"] == 10
        assert call_kwargs["include_file_metadata"] is True

    def test_list_handles_operation_error(self, temp_registry):
        """Test that list_entities_tool handles ListOperation errors gracefully"""
        with patch("hxc.mcp.tools.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.side_effect = ListOperationError("Test error")
            MockOperation.return_value = mock_instance

            result = list_entities_tool(
                entity_type="project", registry_path=temp_registry
            )

        assert result["success"] is False
        assert "Test error" in result["error"]

    def test_list_handles_path_security_error(self, temp_registry):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = list_entities_tool(
                entity_type="project", registry_path=temp_registry
            )

        assert result["success"] is False
        assert "Security error" in result["error"]

    def test_list_handles_unexpected_error(self, temp_registry):
        """Test that unexpected errors are handled gracefully"""
        with patch("hxc.mcp.tools.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.side_effect = RuntimeError("Unexpected error")
            MockOperation.return_value = mock_instance

            result = list_entities_tool(
                entity_type="project", registry_path=temp_registry
            )

        assert result["success"] is False
        assert "Unexpected error" in result["error"]


class TestListEntitiesToolBehavioralParityWithCLI:
    """Tests to verify list_entities_tool produces same results as CLI"""

    def test_list_filter_produces_same_results_as_cli_operation(self, temp_registry):
        """Test that MCP list produces same results as direct ListOperation"""
        # Get results via direct operation
        operation = ListOperation(temp_registry)
        operation_result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.ACTIVE,
            include_file_metadata=False,
        )

        # Get results via MCP tool
        mcp_result = list_entities_tool(
            entity_type="project",
            status="active",
            include_file_metadata=False,
            registry_path=temp_registry,
        )

        assert mcp_result["success"] is True
        assert operation_result["success"] is True

        # Compare IDs
        operation_ids = {e["id"] for e in operation_result["entities"]}
        mcp_ids = {e["id"] for e in mcp_result["entities"]}

        assert operation_ids == mcp_ids

    def test_list_sort_produces_same_order_as_cli_operation(self, temp_registry):
        """Test that MCP list produces same sort order as direct ListOperation"""
        # Get results via direct operation
        operation = ListOperation(temp_registry)
        operation_result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            sort_field=SortField.TITLE,
            descending=True,
            include_file_metadata=False,
        )

        # Get results via MCP tool
        mcp_result = list_entities_tool(
            entity_type="project",
            sort_by="title",
            descending=True,
            include_file_metadata=False,
            registry_path=temp_registry,
        )

        assert mcp_result["success"] is True
        assert operation_result["success"] is True

        # Compare order
        operation_ids = [e["id"] for e in operation_result["entities"]]
        mcp_ids = [e["id"] for e in mcp_result["entities"]]

        assert operation_ids == mcp_ids

    def test_list_with_all_filters_matches_operation(self, temp_registry):
        """Test that all filters work identically between MCP and ListOperation"""
        # Use MCP tool with all filters
        mcp_result = list_entities_tool(
            entity_type="project",
            status="active",
            tags=["mcp"],
            category="software.dev/cli-tool",
            query="MCP",
            max_items=10,
            sort_by="title",
            descending=False,
            include_file_metadata=False,
            registry_path=temp_registry,
        )

        # Use direct operation with same filters
        operation = ListOperation(temp_registry)
        operation_result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.ACTIVE,
            tags=["mcp"],
            category="software.dev/cli-tool",
            query="MCP",
            max_items=10,
            sort_field=SortField.TITLE,
            descending=False,
            include_file_metadata=False,
        )

        assert mcp_result["success"] is True
        assert operation_result["success"] is True

        # Should produce identical results
        assert mcp_result["count"] == operation_result["count"]

        mcp_ids = [e["id"] for e in mcp_result["entities"]]
        operation_ids = [e["id"] for e in operation_result["entities"]]

        assert mcp_ids == operation_ids

    def test_list_date_filters_match_operation(self, temp_registry_with_dates):
        """Test that date filters work identically between MCP and ListOperation"""
        # Use MCP tool with date filters
        mcp_result = list_entities_tool(
            entity_type="project",
            due_before="2024-07-01",
            due_after="2024-03-01",
            registry_path=temp_registry_with_dates,
        )

        # Use direct operation with same filters
        operation = ListOperation(temp_registry_with_dates)
        operation_result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            due_before="2024-07-01",
            due_after="2024-03-01",
            include_file_metadata=False,
        )

        assert mcp_result["success"] is True
        assert operation_result["success"] is True

        # Should produce identical results
        assert mcp_result["count"] == operation_result["count"]

        mcp_ids = {e["id"] for e in mcp_result["entities"]}
        operation_ids = {e["id"] for e in operation_result["entities"]}

        assert mcp_ids == operation_ids

    def test_list_file_metadata_structure_matches_operation(self, temp_registry):
        """Test that file metadata structure is identical between MCP and ListOperation"""
        # Use MCP tool with file metadata
        mcp_result = list_entities_tool(
            entity_type="project",
            identifier="P-001",
            include_file_metadata=True,
            registry_path=temp_registry,
        )

        assert mcp_result["success"] is True
        assert len(mcp_result["entities"]) == 1

        entity = mcp_result["entities"][0]
        assert "_file" in entity
        assert "path" in entity["_file"]
        assert "name" in entity["_file"]
        assert "created" in entity["_file"]
        assert "modified" in entity["_file"]

        # Verify date format (YYYY-MM-DD)
        import datetime

        datetime.datetime.strptime(entity["_file"]["created"], "%Y-%m-%d")
        datetime.datetime.strptime(entity["_file"]["modified"], "%Y-%m-%d")

    def test_list_all_entity_types_match_cli(self, temp_registry):
        """Test that listing all entity types produces same results as CLI"""
        # Use MCP tool
        mcp_result = list_entities_tool(
            entity_type="all",
            registry_path=temp_registry,
        )

        # Use direct operation
        operation = ListOperation(temp_registry)
        operation_result = operation.list_entities(
            entity_types=list(EntityType),
            include_file_metadata=False,
        )

        assert mcp_result["success"] is True
        assert operation_result["success"] is True
        assert mcp_result["count"] == operation_result["count"]

    def test_list_empty_results_match_cli(self, temp_registry):
        """Test that empty results are handled identically"""
        # Use MCP tool with filter that matches nothing
        mcp_result = list_entities_tool(
            entity_type="project",
            identifier="NONEXISTENT",
            registry_path=temp_registry,
        )

        assert mcp_result["success"] is True
        assert mcp_result["count"] == 0
        assert mcp_result["entities"] == []

    def test_list_response_structure_matches_cli(self, temp_registry):
        """Test that response structure matches what CLI would produce"""
        result = list_entities_tool(
            entity_type="project",
            status="active",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "entities" in result
        assert "count" in result
        assert "filters" in result
        assert "sort" in result

        # Filters should contain applied values
        assert result["filters"]["type"] == "project"
        assert result["filters"]["status"] == "active"

        # Sort should contain default values
        assert "field" in result["sort"]
        assert "descending" in result["sort"]


class TestSearchEntitiesTool:
    """Tests for search_entities_tool"""

    def test_search_by_title(self, temp_registry):
        """Test searching by title"""
        result = search_entities_tool(query="Project One", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] > 0

        found = False
        for entity in result["entities"]:
            if "Project One" in entity["title"]:
                found = True
                break
        assert found

    def test_search_by_description(self, temp_registry):
        """Test searching by description"""
        result = search_entities_tool(
            query="MCP tools testing", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] > 0

    def test_search_case_insensitive(self, temp_registry):
        """Test that search is case insensitive"""
        result1 = search_entities_tool(query="test", registry_path=temp_registry)

        result2 = search_entities_tool(query="TEST", registry_path=temp_registry)

        assert result1["success"] is True
        assert result2["success"] is True
        assert result1["count"] == result2["count"]

    def test_search_with_entity_type_filter(self, temp_registry):
        """Test searching with entity type filter"""
        result = search_entities_tool(
            query="test", entity_type="project", registry_path=temp_registry
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert entity["type"] == "project"

    def test_search_with_status_filter(self, temp_registry):
        """Test searching with status filter"""
        result = search_entities_tool(
            query="test", status="active", registry_path=temp_registry
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert entity["status"] == "active"

    def test_search_with_tags_filter(self, temp_registry):
        """Test searching with tags filter"""
        result = search_entities_tool(
            query="test", tags=["mcp"], registry_path=temp_registry
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert "mcp" in entity.get("tags", [])

    def test_search_with_category_filter(self, temp_registry):
        """Test searching with category filter"""
        result = search_entities_tool(
            query="test", category="software.dev/cli-tool", registry_path=temp_registry
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert entity["category"] == "software.dev/cli-tool"

    def test_search_with_max_items(self, temp_registry):
        """Test searching with max items limit"""
        result = search_entities_tool(
            query="test", max_items=2, registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] <= 2

    def test_search_no_results(self, temp_registry):
        """Test searching with no results"""
        result = search_entities_tool(
            query="nonexistent query string", registry_path=temp_registry
        )

        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["entities"]) == 0

    def test_search_includes_query(self, temp_registry):
        """Test that result includes query"""
        result = search_entities_tool(query="test", registry_path=temp_registry)

        assert result["success"] is True
        assert "query" in result
        assert result["query"] == "test"

    def test_search_includes_filters(self, temp_registry):
        """Test that result includes filters"""
        result = search_entities_tool(
            query="test",
            entity_type="project",
            status="active",
            tags=["test"],
            category="software.dev/cli-tool",
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["type"] == "project"
        assert result["filters"]["status"] == "active"

    def test_search_delegates_to_list_entities_tool(self, temp_registry):
        """Test that search_entities_tool delegates to list_entities_tool"""
        with patch("hxc.mcp.tools.list_entities_tool") as mock_list:
            mock_list.return_value = {
                "success": True,
                "entities": [],
                "count": 0,
                "filters": {},
                "sort": {},
            }

            result = search_entities_tool(
                query="test",
                entity_type="project",
                status="active",
                tags=["test"],
                category="software.dev/cli-tool",
                max_items=10,
                registry_path=temp_registry,
            )

        mock_list.assert_called_once_with(
            entity_type="project",
            status="active",
            tags=["test"],
            category="software.dev/cli-tool",
            query="test",
            max_items=10,
            registry_path=temp_registry,
        )

    def test_search_with_no_registry(self):
        """Test search with no registry"""
        result = search_entities_tool(
            query="test",
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False
        assert "error" in result

    def test_search_empty_query(self, temp_registry):
        """Test search with empty query"""
        result = search_entities_tool(query="", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] >= 0


class TestSearchEntitiesToolUsesListTool:
    """Tests to verify search_entities_tool correctly delegates to list_entities_tool"""

    def test_search_response_format(self, temp_registry):
        """Test that search response has expected format"""
        result = search_entities_tool(query="test", registry_path=temp_registry)

        assert result["success"] is True
        assert "entities" in result
        assert "count" in result
        assert "query" in result
        assert "filters" in result

    def test_search_filters_passed_correctly(self, temp_registry):
        """Test that all filters are passed to the underlying list operation"""
        result = search_entities_tool(
            query="project",
            entity_type="project",
            status="active",
            tags=["test"],
            category="software.dev/cli-tool",
            max_items=5,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["query"] == "project"
        assert result["filters"]["type"] == "project"
        assert result["filters"]["status"] == "active"
        assert result["filters"]["tags"] == ["test"]
        assert result["filters"]["category"] == "software.dev/cli-tool"

    def test_search_entity_type_all(self, temp_registry):
        """Test searching across all entity types"""
        result = search_entities_tool(
            query="test",
            entity_type="all",
            registry_path=temp_registry,
        )

        assert result["success"] is True

        # Should find entities of various types
        types_found = {e["type"] for e in result["entities"]}
        assert len(types_found) >= 1


class TestListEntitiesToolIntegration:
    """Integration tests for list_entities_tool"""

    def test_list_then_verify_entities(self, temp_registry):
        """Test listing entities and verifying their properties"""
        result = list_entities_tool(
            entity_type="project",
            status="active",
            registry_path=temp_registry,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert "uid" in entity
            assert "id" in entity
            assert "title" in entity
            assert entity["type"] == "project"
            assert entity["status"] == "active"

    def test_list_with_combined_filters(self, temp_registry):
        """Test listing with multiple filters combined"""
        result = list_entities_tool(
            entity_type="project",
            status="active",
            tags=["test"],
            query="Project",
            registry_path=temp_registry,
        )

        assert result["success"] is True

        for entity in result["entities"]:
            assert entity["type"] == "project"
            assert entity["status"] == "active"
            assert "test" in entity.get("tags", [])
            assert (
                "project" in entity["title"].lower()
                or "project" in entity.get("description", "").lower()
            )

    def test_list_sort_consistency(self, temp_registry):
        """Test that sorting is consistent across multiple calls"""
        result1 = list_entities_tool(
            entity_type="project",
            sort_by="title",
            registry_path=temp_registry,
        )

        result2 = list_entities_tool(
            entity_type="project",
            sort_by="title",
            registry_path=temp_registry,
        )

        assert result1["success"] is True
        assert result2["success"] is True

        ids1 = [e["id"] for e in result1["entities"]]
        ids2 = [e["id"] for e in result2["entities"]]

        assert ids1 == ids2

    def test_list_pagination_with_max_items(self, temp_registry):
        """Test pagination using max_items"""
        # Get first 2
        result1 = list_entities_tool(
            entity_type="all",
            sort_by="title",
            max_items=2,
            registry_path=temp_registry,
        )

        # Get all
        result_all = list_entities_tool(
            entity_type="all",
            sort_by="title",
            registry_path=temp_registry,
        )

        assert result1["success"] is True
        assert result_all["success"] is True
        assert result1["count"] <= 2
        assert result_all["count"] >= result1["count"]

        # First 2 from all should match result1
        if result_all["count"] >= 2:
            assert result1["entities"][0]["id"] == result_all["entities"][0]["id"]
            assert result1["entities"][1]["id"] == result_all["entities"][1]["id"]


class TestListEntitiesToolErrorHandling:
    """Tests for error handling in list_entities_tool"""

    def test_list_with_security_error(self):
        """Test list with path security error"""
        result = list_entities_tool(entity_type="all", registry_path="/etc/passwd")

        assert result["success"] is False
        assert "error" in result

    def test_list_with_invalid_sort_field(self, temp_registry):
        """Test list with invalid sort field"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="invalid_field",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_list_with_malformed_tags(self, temp_registry):
        """Test list handles tags parameter correctly"""
        # Tags should be a list
        result = list_entities_tool(
            entity_type="project",
            tags=["valid-tag"],
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_list_handles_empty_registry(self, empty_temp_dir):
        """Test listing in an empty (initialized) registry"""
        from hxc.mcp.tools import init_registry_tool

        # Initialize empty registry
        init_result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )
        assert init_result["success"] is True

        # List should return empty
        result = list_entities_tool(
            entity_type="all",
            registry_path=empty_temp_dir,
        )

        assert result["success"] is True
        assert result["count"] == 0
        assert result["entities"] == []


class TestListEntitiesToolReadOnlyMode:
    """Tests for list_entities_tool availability in read-only mode"""

    def test_list_available_in_read_only_mode(self, temp_registry):
        """Test that list tool is available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "list_entities" in tools

    def test_search_available_in_read_only_mode(self, temp_registry):
        """Test that search tool is available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "search_entities" in tools

    def test_list_works_in_read_only_server(self, temp_registry):
        """Test that list_entities can be called on read-only server"""
        import json

        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_entities",
                "arguments": {"entity_type": "all"},
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert "entities" in data

    def test_search_works_in_read_only_server(self, temp_registry):
        """Test that search_entities can be called on read-only server"""
        import json

        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_entities",
                "arguments": {"query": "test"},
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert "entities" in data
