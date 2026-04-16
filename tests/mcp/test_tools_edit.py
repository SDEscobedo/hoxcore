"""
Tests for edit_entity_tool in MCP Tools.

This module tests the edit_entity_tool that enables modifying existing entities
in HoxCore registries through the Model Context Protocol.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.edit import DuplicateIdError as EditDuplicateIdError
from hxc.core.operations.edit import (
    EditOperation,
    EditOperationError,
)
from hxc.core.operations.edit import EntityNotFoundError as EditEntityNotFoundError
from hxc.core.operations.edit import (
    InvalidValueError,
    NoChangesError,
)
from hxc.mcp.tools import (
    edit_entity_tool,
    get_entity_tool,
)

from .test_tools_common import (
    verify_edit_result,
    verify_error_result,
    verify_git_commit_exists,
    verify_success_result,
)


class TestEditEntityTool:
    """Tests for edit_entity_tool"""

    def test_edit_title(self, temp_registry):
        """Test editing an entity's title"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Renamed Project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["title"] == "Renamed Project"
        assert any("title" in c for c in result["changes"])

    def test_edit_status(self, temp_registry):
        """Test editing an entity's status"""
        result = edit_entity_tool(
            identifier="P-001",
            set_status="completed",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["status"] == "completed"

    def test_edit_description(self, temp_registry):
        """Test editing an entity's description"""
        result = edit_entity_tool(
            identifier="P-001",
            set_description="Updated description text",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["description"] == "Updated description text"

    def test_edit_category(self, temp_registry):
        """Test editing an entity's category"""
        result = edit_entity_tool(
            identifier="P-001",
            set_category="research/new-category",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["category"] == "research/new-category"

    def test_edit_start_date(self, temp_registry):
        """Test editing an entity's start date"""
        result = edit_entity_tool(
            identifier="P-001",
            set_start_date="2025-06-01",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["start_date"] == "2025-06-01"

    def test_edit_due_date(self, temp_registry):
        """Test editing an entity's due date"""
        result = edit_entity_tool(
            identifier="P-001",
            set_due_date="2026-12-31",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["due_date"] == "2026-12-31"

    def test_edit_completion_date(self, temp_registry):
        """Test editing an entity's completion date"""
        result = edit_entity_tool(
            identifier="P-001",
            set_completion_date="2025-11-30",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["completion_date"] == "2025-11-30"

    def test_edit_parent(self, temp_registry):
        """Test editing an entity's parent"""
        result = edit_entity_tool(
            identifier="P-001",
            set_parent="prog-test-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["parent"] == "prog-test-001"

    def test_edit_add_tags(self, temp_registry):
        """Test adding tags to an entity"""
        result = edit_entity_tool(
            identifier="P-001",
            add_tags=["new-tag", "another-tag"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        tags = result["entity"]["tags"]
        assert "new-tag" in tags
        assert "another-tag" in tags

    def test_edit_remove_tags(self, temp_registry):
        """Test removing tags from an entity"""
        # First confirm the tag exists (fixture project has "mcp" tag)
        result = edit_entity_tool(
            identifier="P-001",
            remove_tags=["mcp"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "mcp" not in result["entity"].get("tags", [])

    def test_edit_add_duplicate_tag_is_idempotent(self, temp_registry):
        """Test that adding an existing tag doesn't duplicate it"""
        result = edit_entity_tool(
            identifier="P-001",
            add_tags=["test"],  # "test" already exists in fixture
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        tags = result["entity"]["tags"]
        assert tags.count("test") == 1

    def test_edit_add_children(self, temp_registry):
        """Test adding children to an entity"""
        result = edit_entity_tool(
            identifier="PRG-001",
            add_children=["act-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        children = result["entity"]["children"]
        assert "act-test-001" in children
        assert any("child" in c.lower() for c in result["changes"])

    def test_edit_remove_children(self, temp_registry):
        """Test removing children from an entity"""
        result = edit_entity_tool(
            identifier="PRG-001",
            remove_children=["proj-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "proj-test-001" not in result["entity"]["children"]

    def test_edit_add_duplicate_child_is_idempotent(self, temp_registry):
        """Test that adding an existing child doesn't duplicate it"""
        result = edit_entity_tool(
            identifier="PRG-001",
            add_children=["proj-test-001"],  # already in fixture
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        children = result["entity"]["children"]
        assert children.count("proj-test-001") == 1

    def test_edit_add_related(self, temp_registry):
        """Test adding related entities"""
        result = edit_entity_tool(
            identifier="P-001",
            add_related=["proj-test-002", "act-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        related = result["entity"]["related"]
        assert "proj-test-002" in related
        assert "act-test-001" in related

    def test_edit_remove_related(self, temp_registry):
        """Test removing related entities"""
        # add first, then remove
        edit_entity_tool(
            identifier="P-001",
            add_related=["proj-test-002"],
            use_git=False,
            registry_path=temp_registry,
        )
        result = edit_entity_tool(
            identifier="P-001",
            remove_related=["proj-test-002"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "proj-test-002" not in result["entity"].get("related", [])

    def test_edit_add_related_to_entity_without_related(self, temp_registry):
        """Test adding related to an entity that doesn't have a related field"""
        result = edit_entity_tool(
            identifier="A-001",
            add_related=["proj-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "proj-test-001" in result["entity"]["related"]

    def test_edit_add_duplicate_related_is_idempotent(self, temp_registry):
        """Test that adding an existing related doesn't duplicate it"""
        edit_entity_tool(
            identifier="P-001",
            add_related=["proj-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        result = edit_entity_tool(
            identifier="P-001",
            add_related=["proj-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["related"].count("proj-test-001") == 1

    def test_edit_remove_nonexistent_child_is_noop(self, temp_registry):
        """Test that removing a nonexistent child is a no-op"""
        result = edit_entity_tool(
            identifier="PRG-001",
            remove_children=["nonexistent-uid"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_edit_remove_nonexistent_related_is_noop(self, temp_registry):
        """Test that removing a nonexistent related is a no-op"""
        result = edit_entity_tool(
            identifier="P-001",
            remove_related=["nonexistent-uid"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

    def test_edit_multiple_scalar_fields(self, temp_registry):
        """Test editing multiple scalar fields at once"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Updated Title",
            set_description="Updated description",
            set_category="research/new",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        entity = result["entity"]
        assert entity["title"] == "Updated Title"
        assert entity["description"] == "Updated description"
        assert entity["category"] == "research/new"
        assert len(result["changes"]) == 3

    def test_edit_invalid_status(self, temp_registry):
        """Test editing with an invalid status value"""
        result = edit_entity_tool(
            identifier="P-001",
            set_status="not-valid",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_edit_no_changes_specified(self, temp_registry):
        """Test that providing no changes returns an error"""
        result = edit_entity_tool(
            identifier="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "no changes" in result["error"].lower()

    def test_edit_nonexistent_entity(self, temp_registry):
        """Test editing an entity that does not exist"""
        result = edit_entity_tool(
            identifier="P-DOES-NOT-EXIST",
            set_title="Ghost",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_edit_persists_to_file(self, temp_registry):
        """Test that edits are actually written to disk"""
        edit_result = edit_entity_tool(
            identifier="P-001",
            set_title="Persisted Title",
            use_git=False,
            registry_path=temp_registry,
        )

        assert edit_result["success"] is True

        file_path = edit_result["file_path"]
        with open(file_path) as f:
            on_disk = yaml.safe_load(f)

        assert on_disk["title"] == "Persisted Title"

    def test_edit_by_uid(self, temp_registry):
        """Test editing an entity by its UID"""
        result = edit_entity_tool(
            identifier="proj-test-001",
            set_title="UID Edit Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["title"] == "UID Edit Test"

    def test_edit_returns_updated_entity(self, temp_registry):
        """Test that edit returns the full updated entity"""
        result = edit_entity_tool(
            identifier="P-001",
            set_due_date="2026-06-30",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "entity" in result
        assert result["entity"]["due_date"] == "2026-06-30"
        assert "identifier" in result
        assert "file_path" in result

    def test_edit_returns_git_committed_field(self, temp_registry):
        """Test that edit returns git_committed field"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Git Field Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "git_committed" in result
        assert result["git_committed"] is False

    def test_edit_with_entity_type_filter(self, temp_registry):
        """Test editing with entity_type filter"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Type Filter Test",
            entity_type="project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["type"] == "project"

    def test_edit_with_wrong_entity_type_filter(self, temp_registry):
        """Test editing with wrong entity_type filter"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Wrong Type Test",
            entity_type="program",  # P-001 is a project, not a program
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_edit_with_no_registry(self):
        """Test edit with a nonexistent registry path"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="No Registry",
            use_git=False,
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False
        assert "error" in result

    def test_edit_all_entity_types(self, temp_registry):
        """Test editing each entity type"""
        entity_tests = [
            ("P-001", "project"),
            ("PRG-001", "program"),
            ("M-001", "mission"),
            ("A-001", "action"),
        ]

        for entity_id, entity_type in entity_tests:
            result = edit_entity_tool(
                identifier=entity_id,
                set_title=f"Edited {entity_type.title()}",
                use_git=False,
                registry_path=temp_registry,
            )

            assert (
                result["success"] is True
            ), f"Failed for {entity_type}: {result.get('error')}"
            assert result["entity"]["title"] == f"Edited {entity_type.title()}"


class TestEditEntityToolIdUniqueness:
    """Tests for ID uniqueness validation in edit_entity_tool"""

    def test_edit_set_id_to_existing_id_fails(self, temp_registry):
        """Test that set_id with an ID already used by another entity of the same type returns success=False"""
        # Try to set P-001's id to P-002 (which already exists in the fixture)
        result = edit_entity_tool(
            identifier="P-001",
            set_id="P-002",
            use_git=False,
            registry_path=temp_registry,
        )

        # Should fail
        assert result["success"] is False
        assert "error" in result
        # Error message should mention the conflicting ID
        assert "P-002" in result["error"]
        assert "already exists" in result["error"].lower()

    def test_edit_set_id_to_same_id_succeeds(self, temp_registry):
        """Test that set_id with the entity's own current ID (no-op) returns success=True"""
        # Set id to the same value it already has (P-001)
        result = edit_entity_tool(
            identifier="proj-test-001",
            set_id="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        # Should succeed (no-op)
        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"

    def test_edit_set_id_to_unique_id_succeeds(self, temp_registry):
        """Test that set_id with a genuinely new, unused ID returns success=True and updates the entity"""
        result = edit_entity_tool(
            identifier="P-001",
            set_id="P-NEW-UNIQUE",
            use_git=False,
            registry_path=temp_registry,
        )

        # Should succeed
        assert result["success"] is True
        assert result["entity"]["id"] == "P-NEW-UNIQUE"

        # Verify persisted to file
        with open(result["file_path"]) as f:
            on_disk = yaml.safe_load(f)
        assert on_disk["id"] == "P-NEW-UNIQUE"

    def test_edit_set_id_allows_same_id_in_different_type(self, temp_registry):
        """Test that set_id with an ID that exists in a different entity type returns success=True"""
        # P-001 exists as a project, but we're editing a program
        # The uniqueness check is scoped per entity type, so this should succeed
        result = edit_entity_tool(
            identifier="PRG-001",
            set_id="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        # Should succeed because programs and projects are different types
        assert result["success"] is True
        assert result["entity"]["id"] == "P-001"

        # Verify the original project still has P-001
        get_result = get_entity_tool(
            identifier="proj-test-001",
            registry_path=temp_registry,
        )
        assert get_result["success"] is True
        assert get_result["entity"]["id"] == "P-001"

    def test_edit_set_id_error_contains_entity_type(self, temp_registry):
        """Test that the error message for duplicate ID includes the entity type"""
        result = edit_entity_tool(
            identifier="P-001",
            set_id="P-002",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        # Error message should mention the entity type
        assert "project" in result["error"].lower()


class TestEditEntityToolUsesSharedOperation:
    """Tests to verify edit_entity_tool uses the shared EditOperation"""

    def test_edit_uses_edit_operation(self, temp_registry):
        """Test that edit_entity_tool uses EditOperation internally"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.return_value = {
                "success": True,
                "identifier": "P-001",
                "changes": ["Set title: 'Old' → 'New'"],
                "entity": {"type": "project", "title": "New"},
                "file_path": "/test/path.yml",
                "git_committed": False,
            }
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="P-001",
                set_title="New Title",
                use_git=False,
                registry_path=temp_registry,
            )

        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.edit_entity.assert_called_once()

    def test_edit_passes_all_parameters_to_operation(self, temp_registry):
        """Test that edit_entity_tool passes all parameters to EditOperation"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.return_value = {
                "success": True,
                "identifier": "P-001",
                "changes": [],
                "entity": {"type": "project"},
                "file_path": "/test/path.yml",
                "git_committed": False,
            }
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="P-001",
                set_title="New Title",
                set_description="New Desc",
                set_status="completed",
                set_id="P-NEW",
                set_category="new/category",
                set_parent="parent-uid",
                set_start_date="2025-01-01",
                set_due_date="2025-12-31",
                set_completion_date="2025-11-30",
                add_tags=["tag1"],
                remove_tags=["tag2"],
                add_children=["child1"],
                remove_children=["child2"],
                add_related=["rel1"],
                remove_related=["rel2"],
                entity_type="project",
                use_git=False,
                registry_path=temp_registry,
            )

        call_kwargs = mock_instance.edit_entity.call_args[1]
        assert call_kwargs["identifier"] == "P-001"
        assert call_kwargs["set_title"] == "New Title"
        assert call_kwargs["set_description"] == "New Desc"
        assert call_kwargs["set_status"] == "completed"
        assert call_kwargs["set_id"] == "P-NEW"
        assert call_kwargs["set_category"] == "new/category"
        assert call_kwargs["set_parent"] == "parent-uid"
        assert call_kwargs["set_start_date"] == "2025-01-01"
        assert call_kwargs["set_due_date"] == "2025-12-31"
        assert call_kwargs["set_completion_date"] == "2025-11-30"
        assert call_kwargs["add_tags"] == ["tag1"]
        assert call_kwargs["remove_tags"] == ["tag2"]
        assert call_kwargs["add_children"] == ["child1"]
        assert call_kwargs["remove_children"] == ["child2"]
        assert call_kwargs["add_related"] == ["rel1"]
        assert call_kwargs["remove_related"] == ["rel2"]
        assert call_kwargs["entity_type"] == EntityType.PROJECT
        assert call_kwargs["use_git"] is False

    def test_edit_handles_entity_not_found_error(self, temp_registry):
        """Test that EntityNotFoundError is handled correctly"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.side_effect = EditEntityNotFoundError(
                "Entity not found: NONEXISTENT"
            )
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="NONEXISTENT",
                set_title="Test",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_edit_handles_duplicate_id_error(self, temp_registry):
        """Test that DuplicateIdError is handled correctly"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.side_effect = EditDuplicateIdError(
                "project with id 'P-002' already exists"
            )
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="P-001",
                set_id="P-002",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "P-002" in result["error"]
        assert "already exists" in result["error"].lower()

    def test_edit_handles_invalid_value_error(self, temp_registry):
        """Test that InvalidValueError is handled correctly"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.side_effect = InvalidValueError(
                "Invalid status 'banana'"
            )
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="P-001",
                set_status="banana",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "banana" in result["error"] or "status" in result["error"].lower()

    def test_edit_handles_no_changes_error(self, temp_registry):
        """Test that NoChangesError is handled correctly"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.side_effect = NoChangesError(
                "No changes specified"
            )
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="P-001",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "no changes" in result["error"].lower()

    def test_edit_handles_operation_error(self, temp_registry):
        """Test that EditOperationError is handled correctly"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.side_effect = EditOperationError(
                "Edit operation failed"
            )
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="P-001",
                set_title="Test",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Edit operation failed" in result["error"]

    def test_edit_handles_path_security_error(self, temp_registry):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="../../../etc/passwd",
                set_title="Test",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Security error" in result["error"]

    def test_edit_handles_unexpected_error(self, temp_registry):
        """Test that unexpected errors are handled gracefully"""
        with patch("hxc.mcp.tools.EditOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.edit_entity.side_effect = RuntimeError("Unexpected error")
            MockOperation.return_value = mock_instance

            result = edit_entity_tool(
                identifier="P-001",
                set_title="Test",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Unexpected error" in result["error"]


class TestEditEntityToolGitIntegration:
    """Tests for git integration in edit_entity_tool"""

    def test_edit_with_use_git_true_creates_commit(self, git_registry_with_entities):
        """Test that use_git=True creates a git commit"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Git Edit Title",
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True
        assert result["git_committed"] is True

        # Verify commit exists
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Edit" in log.stdout
        assert "proj-proj0001" in log.stdout

    def test_edit_with_use_git_false_skips_commit(self, git_registry_with_entities):
        """Test that use_git=False skips git commit"""
        # Get initial commit count
        log_before = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        initial_count = len(log_before.stdout.strip().splitlines())

        result = edit_entity_tool(
            identifier="P-001",
            set_title="No Git Title",
            use_git=False,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        # Verify no new commit
        log_after = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        final_count = len(log_after.stdout.strip().splitlines())

        assert final_count == initial_count

    def test_edit_default_use_git_is_true(self, git_registry_with_entities):
        """Test that use_git defaults to True"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Default Git Edit",
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True
        assert result["git_committed"] is True

    def test_edit_commit_message_format(self, git_registry_with_entities):
        """Test that commit message follows expected format"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Commit Format Test",
            add_tags=["new-tag"],
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        message = log.stdout

        # Verify subject line format
        assert "Edit proj-proj0001:" in message

        # Verify body contains changes
        assert "Set title" in message or "title" in message
        assert "tag" in message.lower()

    def test_edit_in_non_git_registry_handles_gracefully(self, temp_registry, capsys):
        """Test that git operations handle non-git registry gracefully"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Non Git Title",
            use_git=True,  # Request git, but not a git repo
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        out = capsys.readouterr().out
        assert "not inside a git repository" in out

    def test_edit_sequential_commits(self, git_registry_with_entities):
        """Test that multiple edits produce separate commits"""
        # First edit
        result1 = edit_entity_tool(
            identifier="P-001",
            set_title="First Edit",
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        # Second edit
        result2 = edit_entity_tool(
            identifier="P-001",
            set_status="completed",
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result1["success"] is True
        assert result2["success"] is True

        # Verify both commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        # Count commits (initial + add entities + 2 edits)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 4

    def test_edit_commit_includes_all_changes(self, git_registry_with_entities):
        """Test that commit message includes all changes"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Multi Change",
            set_status="completed",
            add_tags=["tag1", "tag2"],
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        message = log.stdout

        # All changes should be mentioned
        assert "title" in message.lower()
        assert "status" in message.lower() or "completed" in message.lower()
        assert "tag" in message.lower()

    def test_edit_all_entity_types_with_git(self, git_registry_with_entities):
        """Test editing all entity types with git integration"""
        entity_tests = [
            ("P-001", "project"),
            ("PRG-001", "program"),
            ("M-001", "mission"),
            ("A-001", "action"),
        ]

        for entity_id, entity_type in entity_tests:
            result = edit_entity_tool(
                identifier=entity_id,
                set_title=f"Edited {entity_type.title()}",
                use_git=True,
                registry_path=git_registry_with_entities,
            )

            assert (
                result["success"] is True
            ), f"Failed for {entity_type}: {result.get('error')}"
            assert result["git_committed"] is True

        # Verify all commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have at least 6 commits (initial + add entities + 4 edits)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 6

    def test_edit_file_staged_and_committed(self, git_registry_with_entities):
        """Test that edited file is properly staged and committed"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Staged Edit Test",
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True

        # Check git status - should be clean
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        # File should not appear in status (already committed)
        assert "proj-proj0001.yml" not in status.stdout


class TestEditEntityToolBehavioralParity:
    """Tests to verify edit_entity_tool behaves identically to CLI"""

    def test_edit_produces_same_results_as_cli_operation(self, temp_registry):
        """Test that MCP edit produces same results as direct EditOperation"""
        # Use direct operation
        operation = EditOperation(temp_registry)
        operation_result = operation.edit_entity(
            identifier="P-001",
            set_title="Direct Operation Edit",
            use_git=False,
        )

        # Read the file
        with open(operation_result["file_path"]) as f:
            direct_data = yaml.safe_load(f)

        # Now use MCP to edit a different entity
        mcp_result = edit_entity_tool(
            identifier="P-002",
            set_title="MCP Tool Edit",
            use_git=False,
            registry_path=temp_registry,
        )

        # Both should succeed with same structure
        assert operation_result["success"] is True
        assert mcp_result["success"] is True

        # Both should have same keys
        assert set(operation_result.keys()) == set(mcp_result.keys())

    def test_edit_changes_format_matches_cli_operation(self, temp_registry):
        """Test that change descriptions match between MCP and EditOperation"""
        # Use MCP
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Format Test",
            set_status="completed",
            add_tags=["new-tag"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        # Changes should follow consistent format
        for change in result["changes"]:
            assert isinstance(change, str)
            assert len(change) > 5  # Not trivially short

    def test_edit_id_validation_matches_cli_operation(self, temp_registry):
        """Test that ID validation matches between MCP and EditOperation"""
        # Use direct operation for duplicate ID
        operation = EditOperation(temp_registry)

        try:
            operation.edit_entity(
                identifier="P-001",
                set_id="P-002",
                use_git=False,
            )
            operation_failed = False
        except EditDuplicateIdError:
            operation_failed = True

        # Use MCP
        mcp_result = edit_entity_tool(
            identifier="proj-test-001",
            set_id="P-002",
            use_git=False,
            registry_path=temp_registry,
        )

        # Both should fail
        assert operation_failed is True
        assert mcp_result["success"] is False

    def test_edit_status_validation_matches_cli(self, temp_registry):
        """Test that status validation is identical"""
        # Valid statuses should work
        for status in ["active", "completed", "on-hold", "cancelled", "planned"]:
            result = edit_entity_tool(
                identifier="P-001",
                set_status=status,
                use_git=False,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Status '{status}' should be valid"

    def test_edit_invalid_status_matches_cli(self, temp_registry):
        """Test that invalid status error matches CLI"""
        result = edit_entity_tool(
            identifier="P-001",
            set_status="invalid-status",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        # Error should mention the status or valid options
        assert (
            "status" in result["error"].lower() or "invalid" in result["error"].lower()
        )

    def test_edit_id_uniqueness_matches_cli(self, temp_registry):
        """Test that edit ID uniqueness validation matches CLI"""
        # Try to set P-001's ID to P-002 (duplicate)
        result = edit_entity_tool(
            identifier="P-001",
            set_id="P-002",
            use_git=False,
            registry_path=temp_registry,
        )

        # Should fail just like CLI
        assert result["success"] is False
        assert "P-002" in result["error"]
        assert "already exists" in result["error"].lower()
        assert "project" in result["error"].lower()

    def test_edit_produces_same_file_content_as_cli(self, temp_registry):
        """Test that MCP edit produces same file content as CLI would"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Parity Test",
            set_status="on-hold",
            add_tags=["parity"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        # Verify file content
        with open(result["file_path"]) as f:
            data = yaml.safe_load(f)

        # Should have exactly the expected values
        assert data["title"] == "Parity Test"
        assert data["status"] == "on-hold"
        assert "parity" in data["tags"]

        # Original fields should be preserved
        assert data["type"] == "project"
        assert data["uid"] == "proj-test-001"

    def test_edit_commit_message_matches_cli(self, git_registry_with_entities):
        """Test that edit commit message format matches CLI"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Edit Commit Test",
            add_tags=["test-tag"],
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        message = log.stdout

        # Subject line format: "Edit {prefix}-{uid}: ..."
        assert "Edit proj-proj0001:" in message

        # Body contains changes
        assert "Set title" in message or "title" in message
        assert "tag" in message.lower()


class TestEditEntityToolReadOnlyMode:
    """Tests for edit_entity_tool in read-only server mode"""

    def test_edit_not_available_in_read_only_mode(self, temp_registry):
        """Test that edit tool is not available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "edit_entity" not in tools

    def test_edit_available_in_read_write_mode(self, temp_registry):
        """Test that edit tool is available in read-write server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=False)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "edit_entity" in tools

    def test_read_only_server_rejects_edit_tool_call(self, temp_registry):
        """Test that calling edit tool on read-only server returns error"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "edit_entity",
                "arguments": {"identifier": "P-001", "set_title": "Blocked"},
            },
        }

        response = server.handle_request(request)
        assert "error" in response


class TestEditEntityToolIntegration:
    """Integration tests for edit_entity_tool"""

    def test_edit_then_get(self, temp_registry):
        """Test editing an entity and then retrieving it"""
        edit_result = edit_entity_tool(
            identifier="P-001",
            set_title="Integration Edit Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert edit_result["success"] is True

        get_result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["title"] == "Integration Edit Test"

    def test_edit_multiple_times(self, temp_registry):
        """Test editing an entity multiple times"""
        # First edit
        edit1 = edit_entity_tool(
            identifier="P-001",
            set_title="First Edit",
            use_git=False,
            registry_path=temp_registry,
        )
        assert edit1["success"] is True

        # Second edit
        edit2 = edit_entity_tool(
            identifier="P-001",
            set_status="completed",
            use_git=False,
            registry_path=temp_registry,
        )
        assert edit2["success"] is True

        # Third edit
        edit3 = edit_entity_tool(
            identifier="P-001",
            add_tags=["multi-edit"],
            use_git=False,
            registry_path=temp_registry,
        )
        assert edit3["success"] is True

        # Verify all changes applied
        get_result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["title"] == "First Edit"
        assert get_result["entity"]["status"] == "completed"
        assert "multi-edit" in get_result["entity"]["tags"]

    def test_edit_with_git_then_verify_history(self, git_registry_with_entities):
        """Test editing with git and verifying the commit history"""
        # Make multiple edits
        edit1 = edit_entity_tool(
            identifier="P-001",
            set_title="Git History Test 1",
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        edit2 = edit_entity_tool(
            identifier="P-001",
            set_title="Git History Test 2",
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert edit1["success"] is True
        assert edit2["success"] is True

        # Verify git history
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have multiple Edit commits
        assert log.stdout.count("Edit") >= 2

    def test_edit_by_id_then_by_uid(self, temp_registry):
        """Test editing by ID then by UID"""
        # Edit by ID
        edit1 = edit_entity_tool(
            identifier="P-001",
            set_title="Edit by ID",
            use_git=False,
            registry_path=temp_registry,
        )
        assert edit1["success"] is True

        # Edit by UID
        edit2 = edit_entity_tool(
            identifier="proj-test-001",
            set_description="Edit by UID",
            use_git=False,
            registry_path=temp_registry,
        )
        assert edit2["success"] is True

        # Verify both edits applied to same entity
        get_result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["title"] == "Edit by ID"
        assert get_result["entity"]["description"] == "Edit by UID"