"""
Tests for delete_entity_tool in MCP Tools.

This module tests the delete_entity_tool that enables deleting entities
from HoxCore registries through the Model Context Protocol.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.operations.delete import (
    AmbiguousEntityError,
    DeleteOperation,
    DeleteOperationError,
    EntityNotFoundError,
)
from hxc.mcp.tools import (
    delete_entity_tool,
    get_entity_tool,
)

from .test_tools_common import (
    ENTITY_TYPE_FOLDERS,
    ENTITY_TYPE_PREFIXES,
    verify_confirmation_required,
    verify_delete_result,
    verify_entity_not_exists,
    verify_error_result,
    verify_git_commit_exists,
    verify_git_status_clean,
    verify_success_result,
)


class TestDeleteEntityTool:
    """Tests for delete_entity_tool"""

    def test_delete_without_force_returns_confirmation(self, temp_registry):
        """Test that calling without force=True returns a confirmation prompt"""
        result = delete_entity_tool(
            identifier="P-001",
            force=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert result.get("confirmation_required") is True
        assert "message" in result
        assert "force=True" in result["message"]

        # File must still exist
        assert Path(temp_registry, "projects", "proj-proj-test-001.yml").exists()

    def test_delete_without_force_does_not_delete(self, temp_registry):
        """Test that the entity file is NOT removed when force is False"""
        delete_entity_tool(identifier="P-001", force=False, registry_path=temp_registry)

        assert Path(temp_registry, "projects", "proj-proj-test-001.yml").exists()

    def test_delete_with_force_removes_file(self, temp_registry):
        """Test that force=True actually deletes the file"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert not Path(temp_registry, "projects", "proj-proj-test-001.yml").exists()

    def test_delete_returns_entity_info(self, temp_registry):
        """Test that delete returns the deleted entity's title and type"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["deleted_title"] == "Test Project One"
        assert result["deleted_type"] == "project"
        assert "file_path" in result

    def test_delete_nonexistent_entity(self, temp_registry):
        """Test deleting an entity that does not exist"""
        result = delete_entity_tool(
            identifier="P-DOES-NOT-EXIST",
            force=True,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_delete_by_uid(self, temp_registry):
        """Test deleting an entity by UID"""
        result = delete_entity_tool(
            identifier="proj-test-002",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert not Path(temp_registry, "projects", "proj-proj-test-002.yml").exists()

    def test_delete_with_no_registry(self):
        """Test delete with a nonexistent registry path"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False
        assert "error" in result

    def test_delete_confirmation_includes_entity_details(self, temp_registry):
        """Test that the confirmation response includes entity details"""
        result = delete_entity_tool(
            identifier="P-001",
            force=False,
            registry_path=temp_registry,
        )

        assert result.get("confirmation_required") is True
        assert result["entity_title"] == "Test Project One"
        assert result["entity_type"] == "project"
        assert "file_path" in result

    def test_delete_returns_git_committed_field(self, temp_registry):
        """Test that delete returns git_committed field"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "git_committed" in result
        assert result["git_committed"] is False

    def test_delete_uses_shared_delete_operation(self, temp_registry):
        """Test that delete_entity_tool uses DeleteOperation internally"""
        with patch("hxc.mcp.tools.DeleteOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity_info.return_value = {
                "success": True,
                "identifier": "P-001",
                "entity_title": "Test Project",
                "entity_type": "project",
                "file_path": str(
                    Path(temp_registry) / "projects" / "proj-proj-test-001.yml"
                ),
                "entity": {
                    "type": "project",
                    "uid": "proj-test-001",
                    "title": "Test Project",
                },
            }
            mock_instance.delete_entity.return_value = {
                "success": True,
                "identifier": "P-001",
                "deleted_title": "Test Project",
                "deleted_type": "project",
                "file_path": str(
                    Path(temp_registry) / "projects" / "proj-proj-test-001.yml"
                ),
                "entity": {
                    "type": "project",
                    "uid": "proj-test-001",
                    "title": "Test Project",
                },
                "git_committed": False,
            }
            MockOperation.return_value = mock_instance

            result = delete_entity_tool(
                identifier="P-001",
                force=True,
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is True
        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.delete_entity.assert_called_once()

    def test_delete_handles_entity_not_found_error(self, temp_registry):
        """Test that EntityNotFoundError is handled correctly"""
        with patch("hxc.mcp.tools.DeleteOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity_info.side_effect = EntityNotFoundError(
                "Entity not found: nonexistent"
            )
            MockOperation.return_value = mock_instance

            result = delete_entity_tool(
                identifier="nonexistent",
                force=True,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_delete_handles_ambiguous_entity_error(self, temp_registry):
        """Test that AmbiguousEntityError is handled correctly"""
        with patch("hxc.mcp.tools.DeleteOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity_info.side_effect = AmbiguousEntityError(
                "Multiple entities found with identifier 'duplicate'"
            )
            MockOperation.return_value = mock_instance

            result = delete_entity_tool(
                identifier="duplicate",
                force=True,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Multiple entities found" in result["error"]

    def test_delete_with_entity_type_filter(self, temp_registry):
        """Test delete with entity_type filter"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            entity_type="project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["deleted_type"] == "project"

    def test_delete_with_invalid_entity_type(self, temp_registry):
        """Test delete with invalid entity type"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            entity_type="invalid_type",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_delete_all_entity_types(self, temp_registry):
        """Test deleting each entity type"""
        entity_tests = [
            ("P-001", "project", "proj-proj-test-001.yml"),
            ("PRG-001", "program", "prog-prog-test-001.yml"),
            ("M-001", "mission", "miss-miss-test-001.yml"),
            ("A-001", "action", "act-act-test-001.yml"),
        ]

        for entity_id, entity_type, filename in entity_tests:
            folder = ENTITY_TYPE_FOLDERS[entity_type]
            file_path = Path(temp_registry) / folder / filename

            # Verify file exists before deletion
            assert file_path.exists(), f"File should exist before deletion: {file_path}"

            result = delete_entity_tool(
                identifier=entity_id,
                force=True,
                use_git=False,
                registry_path=temp_registry,
            )

            assert (
                result["success"] is True
            ), f"Failed for {entity_type}: {result.get('error')}"
            assert result["deleted_type"] == entity_type
            assert not file_path.exists(), f"File should be deleted: {file_path}"


class TestDeleteEntityToolGitIntegration:
    """Tests for git integration in delete_entity_tool"""

    def test_delete_with_use_git_true_creates_commit(self, git_registry_with_entities):
        """Test that use_git=True creates a git commit"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
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
        assert "Delete" in log.stdout
        assert "proj-proj0001" in log.stdout

    def test_delete_with_use_git_false_skips_commit(self, git_registry_with_entities):
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

        result = delete_entity_tool(
            identifier="P-001",
            force=True,
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

    def test_delete_default_use_git_is_true(self, git_registry_with_entities):
        """Test that use_git defaults to True"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True
        assert result["git_committed"] is True

    def test_delete_commit_message_format(self, git_registry_with_entities):
        """Test that commit message follows expected format"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
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

        # Verify message components
        assert "Delete proj-proj0001: Git Project" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: proj0001" in message

    def test_delete_in_non_git_registry_handles_gracefully(self, temp_registry):
        """Test that git operations handle non-git registry gracefully"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=True,  # Requesting git, but registry is not git
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        # File should still be deleted
        assert not Path(temp_registry, "projects", "proj-proj-test-001.yml").exists()

    def test_delete_sequential_commits(self, git_registry_with_entities):
        """Test that multiple deletions produce separate commits"""
        # Delete first entity
        result1 = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        # Delete second entity
        result2 = delete_entity_tool(
            identifier="PRG-001",
            force=True,
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

        assert "proj-proj0001" in log.stdout or "Git Project" in log.stdout
        assert "prog-prog0001" in log.stdout or "Git Program" in log.stdout

        # Count commits (initial + add entities + 2 deletes)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 4

    def test_delete_all_entity_types_with_git(self, git_registry_with_entities):
        """Test deleting all entity types with git integration"""
        entity_tests = [
            ("P-001", "project", "proj-proj0001"),
            ("PRG-001", "program", "prog-prog0001"),
            ("M-001", "mission", "miss-miss0001"),
            ("A-001", "action", "act-act0001"),
        ]

        for entity_id, entity_type, expected_prefix in entity_tests:
            result = delete_entity_tool(
                identifier=entity_id,
                force=True,
                use_git=True,
                registry_path=git_registry_with_entities,
            )

            assert (
                result["success"] is True
            ), f"Failed for {entity_type}: {result.get('error')}"
            assert result["git_committed"] is True
            assert result["deleted_type"] == entity_type

        # Verify all commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have at least 6 commits (initial + add entities + 4 deletes)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 6

    def test_delete_file_removed_from_git_index(self, git_registry_with_entities):
        """Test that file is removed from git index after deletion"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True

        # Check git status
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        # File should not appear in status (committed)
        assert "proj-proj0001.yml" not in status.stdout

    def test_delete_handles_untracked_files(self, git_registry):
        """Test that MCP handles untracked files gracefully"""
        # Create an untracked entity file
        untracked_entity = {
            "type": "project",
            "uid": "untracked",
            "id": "P-UNTRACKED",
            "title": "Untracked Project",
            "status": "active",
            "children": [],
            "related": [],
        }
        untracked_file = Path(git_registry) / "projects" / "proj-untracked.yml"
        with open(untracked_file, "w") as f:
            yaml.dump(untracked_entity, f)

        # Delete via MCP
        result = delete_entity_tool(
            identifier="P-UNTRACKED",
            force=True,
            use_git=True,
            registry_path=git_registry,
        )

        # Should succeed (fallback to simple deletion)
        assert result["success"] is True
        # git_committed may be False for untracked files
        assert not untracked_file.exists()


class TestDeleteEntityToolErrorHandling:
    """Tests for error handling in delete_entity_tool"""

    def test_delete_handles_path_security_error(self, temp_registry):
        """Test that path security errors are handled"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.DeleteOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity_info.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = delete_entity_tool(
                identifier="../../../etc/passwd",
                force=True,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Security error" in result["error"]

    def test_delete_handles_delete_operation_error(self, temp_registry):
        """Test that DeleteOperationError is handled correctly"""
        with patch("hxc.mcp.tools.DeleteOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity_info.return_value = {
                "success": True,
                "identifier": "P-001",
                "entity_title": "Test Project",
                "entity_type": "project",
                "file_path": str(
                    Path(temp_registry) / "projects" / "proj-proj-test-001.yml"
                ),
                "entity": {
                    "type": "project",
                    "uid": "proj-test-001",
                    "title": "Test Project",
                },
            }
            mock_instance.delete_entity.side_effect = DeleteOperationError(
                "Delete operation failed"
            )
            MockOperation.return_value = mock_instance

            result = delete_entity_tool(
                identifier="P-001",
                force=True,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Error deleting entity" in result["error"]

    def test_delete_handles_unexpected_error(self, temp_registry):
        """Test that unexpected errors are handled gracefully"""
        with patch("hxc.mcp.tools.DeleteOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity_info.side_effect = RuntimeError("Unexpected error")
            MockOperation.return_value = mock_instance

            result = delete_entity_tool(
                identifier="P-001",
                force=True,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Unexpected error" in result["error"]


class TestDeleteEntityToolReadOnlyMode:
    """Tests for delete_entity_tool in read-only server mode"""

    def test_delete_not_available_in_read_only_mode(self, temp_registry):
        """Test that delete tool is not available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "delete_entity" not in tools

    def test_delete_available_in_read_write_mode(self, temp_registry):
        """Test that delete tool is available in read-write server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=False)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "delete_entity" in tools

    def test_read_only_server_rejects_delete_tool_call(self, temp_registry):
        """Test that calling delete tool on read-only server returns error"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "delete_entity",
                "arguments": {"identifier": "P-001", "force": True},
            },
        }

        response = server.handle_request(request)
        assert "error" in response


class TestDeleteEntityToolBehavioralParity:
    """Tests to verify delete_entity_tool behaves identically to CLI"""

    def test_delete_commit_message_matches_cli(self, git_registry_with_entities):
        """Test that delete commit message format matches CLI"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
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

        # Subject line format: "Delete {prefix}-{uid}: {title}"
        assert "Delete proj-proj0001: Git Project" in message

        # Body contains entity metadata
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: proj0001" in message

    def test_delete_file_prefix_conventions(self, git_registry_with_entities):
        """Test that delete file prefixes match expected conventions"""
        tests = [
            ("P-001", "proj-"),
            ("PRG-001", "prog-"),
            ("M-001", "miss-"),
            ("A-001", "act-"),
        ]

        for entity_id, expected_prefix in tests:
            result = delete_entity_tool(
                identifier=entity_id,
                force=True,
                use_git=True,
                registry_path=git_registry_with_entities,
            )

            assert result["success"] is True
            assert expected_prefix in result["file_path"]

    def test_delete_return_structure_matches_cli(self, temp_registry):
        """Test that delete return structure is consistent"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True

        # All expected keys should be present
        expected_keys = {
            "success",
            "identifier",
            "deleted_title",
            "deleted_type",
            "file_path",
            "git_committed",
        }

        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_delete_mcp_and_cli_produce_same_git_history(
        self, git_registry_with_entities
    ):
        """Test that MCP and CLI produce identical git history structure"""
        # Use MCP to delete
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True
        assert result["git_committed"] is True

        # Verify commit structure
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )

        message = log.stdout

        # Verify CLI-compatible format
        lines = message.strip().split("\n")

        # Subject line
        assert lines[0].startswith("Delete ")
        assert ":" in lines[0]

        # Body (after blank line)
        body = "\n".join(lines[2:])
        assert "Entity type:" in body
        assert "Entity ID:" in body
        assert "Entity UID:" in body

    def test_delete_confirmation_structure_matches_cli(self, temp_registry):
        """Test that confirmation response structure matches CLI"""
        result = delete_entity_tool(
            identifier="P-001",
            force=False,
            registry_path=temp_registry,
        )

        # Should require confirmation
        assert result["success"] is False
        assert result.get("confirmation_required") is True

        # Should include all needed info
        assert "identifier" in result
        assert "entity_title" in result
        assert "entity_type" in result
        assert "file_path" in result
        assert "message" in result

        # Message should mention force=True
        assert "force=True" in result["message"]


class TestDeleteEntityToolIntegration:
    """Integration tests for delete_entity_tool"""

    def test_delete_then_get_returns_not_found(self, temp_registry):
        """Test that deleted entity cannot be retrieved"""
        # Delete
        delete_result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )
        assert delete_result["success"] is True

        # Try to get
        get_result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )

        assert get_result["success"] is False
        assert "not found" in get_result["error"].lower()

    def test_delete_preserves_other_entities(self, temp_registry):
        """Test that deleting one entity doesn't affect others"""
        # Delete P-001
        delete_result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )
        assert delete_result["success"] is True

        # P-002 should still exist
        get_result = get_entity_tool(
            identifier="P-002",
            registry_path=temp_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["id"] == "P-002"

    def test_delete_with_git_then_verify_file_removed(self, git_registry_with_entities):
        """Test that git deletion actually removes the file"""
        file_path = Path(git_registry_with_entities) / "projects" / "proj-proj0001.yml"
        assert file_path.exists()

        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            use_git=True,
            registry_path=git_registry_with_entities,
        )

        assert result["success"] is True
        assert not file_path.exists()

    def test_delete_multiple_entities_sequentially(self, temp_registry):
        """Test deleting multiple entities in sequence"""
        entities_to_delete = ["P-001", "P-002", "PRG-001", "M-001", "A-001"]

        for entity_id in entities_to_delete:
            result = delete_entity_tool(
                identifier=entity_id,
                force=True,
                use_git=False,
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed to delete {entity_id}"

        # Verify all are deleted by trying to get them
        for entity_id in entities_to_delete:
            get_result = get_entity_tool(
                identifier=entity_id,
                registry_path=temp_registry,
            )
            assert get_result["success"] is False
            assert "not found" in get_result["error"].lower()
