"""
Tests for create_entity_tool in MCP Tools.

This module tests the create_entity_tool that enables creating new entities
in HoxCore registries through the Model Context Protocol.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.operations.create import CreateOperation, DuplicateIdError
from hxc.core.operations.init import InitOperation
from hxc.mcp.tools import (
    create_entity_tool,
    get_entity_tool,
    list_entities_tool,
)


class TestCreateEntityTool:
    """Tests for create_entity_tool"""

    def test_create_project(self, temp_registry):
        """Test creating a project entity"""
        result = create_entity_tool(
            type="project",
            title="New Test Project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "uid" in result
        assert "file_path" in result

        # Verify file was created
        file_path = Path(result["file_path"])
        assert file_path.exists()

        with open(file_path) as f:
            data = yaml.safe_load(f)

        assert data["type"] == "project"
        assert data["title"] == "New Test Project"
        assert data["status"] == "active"

    def test_create_with_all_optional_fields(self, temp_registry):
        """Test creating an entity with all optional fields populated"""
        result = create_entity_tool(
            type="project",
            title="Full Project",
            description="A fully specified project",
            status="on-hold",
            id="P-999",
            category="software.dev/api",
            tags=["python", "api"],
            parent="prog-test-001",
            start_date="2025-01-01",
            due_date="2025-12-31",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        entity = result["entity"]
        assert entity["title"] == "Full Project"
        assert entity["description"] == "A fully specified project"
        assert entity["status"] == "on-hold"
        assert entity["id"] == "P-999"
        assert entity["category"] == "software.dev/api"
        assert entity["tags"] == ["python", "api"]
        assert entity["parent"] == "prog-test-001"
        assert entity["start_date"] == "2025-01-01"
        assert entity["due_date"] == "2025-12-31"

    def test_create_all_entity_types(self, temp_registry):
        """Test creating each entity type"""
        for entity_type in ["program", "project", "mission", "action"]:
            result = create_entity_tool(
                type=entity_type,
                title=f"Test {entity_type.title()}",
                use_git=False,
                registry_path=temp_registry,
            )
            assert (
                result["success"] is True
            ), f"Failed for type {entity_type}: {result.get('error')}"

    def test_create_default_start_date_is_today(self, temp_registry):
        """Test that start_date defaults to today"""
        import datetime

        today = datetime.date.today().isoformat()

        result = create_entity_tool(
            type="project",
            title="Date Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["entity"]["start_date"] == today

    def test_create_invalid_type(self, temp_registry):
        """Test creating with an invalid entity type"""
        result = create_entity_tool(
            type="invalid_type",
            title="Should Fail",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_create_invalid_status(self, temp_registry):
        """Test creating with an invalid status"""
        result = create_entity_tool(
            type="project",
            title="Bad Status",
            status="not-a-status",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result

    def test_create_with_no_registry(self):
        """Test creating with a nonexistent registry path"""
        result = create_entity_tool(
            type="project",
            title="No Registry",
            use_git=False,
            registry_path="/nonexistent/path",
        )

        assert result["success"] is False
        assert "error" in result

    def test_create_file_in_correct_subfolder(self, temp_registry):
        """Test that each entity type lands in its correct subfolder"""
        type_folder_map = {
            "program": "programs",
            "project": "projects",
            "mission": "missions",
            "action": "actions",
        }

        for entity_type, folder in type_folder_map.items():
            result = create_entity_tool(
                type=entity_type,
                title=f"Folder Test {entity_type}",
                use_git=False,
                registry_path=temp_registry,
            )

            assert result["success"] is True
            file_path = Path(result["file_path"])
            assert (
                file_path.parent.name == folder
            ), f"Expected {folder}, got {file_path.parent.name}"

    def test_create_returns_uid_and_file_path(self, temp_registry):
        """Test that create returns uid and file_path"""
        result = create_entity_tool(
            type="project",
            title="Return Fields Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert isinstance(result["uid"], str)
        assert len(result["uid"]) > 0
        assert isinstance(result["file_path"], str)

    def test_create_returns_git_committed_field(self, temp_registry):
        """Test that create returns git_committed field"""
        result = create_entity_tool(
            type="project",
            title="Git Field Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "git_committed" in result
        assert result["git_committed"] is False

    def test_create_uses_shared_create_operation(self, temp_registry):
        """Test that create_entity_tool uses CreateOperation internally"""
        with patch("hxc.mcp.tools.CreateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.create_entity.return_value = {
                "success": True,
                "uid": "12345678",
                "id": "test_project",
                "file_path": str(
                    Path(temp_registry) / "projects" / "proj-12345678.yml"
                ),
                "entity": {"type": "project", "title": "Test Project"},
                "git_committed": False,
            }
            MockOperation.return_value = mock_instance

            result = create_entity_tool(
                type="project",
                title="Test Project",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is True
        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.create_entity.assert_called_once()


class TestCreateEntityToolIdUniqueness:
    """Tests for ID uniqueness validation in create_entity_tool"""

    def test_create_duplicate_custom_id_fails(self, temp_registry):
        """Test that creating with a duplicate custom ID fails"""
        # P-001 already exists in the fixture
        result = create_entity_tool(
            type="project",
            title="New Project",
            id="P-001",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert "error" in result
        assert "P-001" in result["error"]
        assert "already exists" in result["error"].lower()

    def test_create_unique_custom_id_succeeds(self, temp_registry):
        """Test that creating with a unique custom ID succeeds"""
        result = create_entity_tool(
            type="project",
            title="Unique Project",
            id="P-UNIQUE-999",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["id"] == "P-UNIQUE-999"
        assert result["entity"]["id"] == "P-UNIQUE-999"

    def test_create_auto_id_collision_resolution(self, temp_registry):
        """Test that auto-generated ID collision is resolved with suffix"""
        # Create first entity with title that generates "test_project"
        result1 = create_entity_tool(
            type="project",
            title="Test Project",
            use_git=False,
            registry_path=temp_registry,
        )
        assert result1["success"] is True
        first_id = result1["id"]

        # Create second entity with same title
        result2 = create_entity_tool(
            type="project",
            title="Test Project",
            use_git=False,
            registry_path=temp_registry,
        )
        assert result2["success"] is True
        second_id = result2["id"]

        # IDs should be different
        assert first_id != second_id
        # Second one should have a suffix
        assert second_id.startswith("test_project_")

    def test_create_same_id_different_entity_types_allowed(self, temp_registry):
        """Test that same ID can be used for different entity types"""
        # P-001 exists as a project, but should be allowed for a program
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


class TestCreateEntityToolGitIntegration:
    """Tests for git integration in create_entity_tool"""

    def test_create_with_use_git_true_creates_commit(self, git_registry):
        """Test that use_git=True creates a git commit"""
        result = create_entity_tool(
            type="project",
            title="Git Project",
            use_git=True,
            registry_path=git_registry,
        )

        assert result["success"] is True
        assert result["git_committed"] is True

        # Verify commit exists
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "proj-" in log.stdout

    def test_create_with_use_git_false_skips_commit(self, git_registry):
        """Test that use_git=False skips git commit"""
        # Get initial commit count
        log_before = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        initial_count = len(log_before.stdout.strip().splitlines())

        result = create_entity_tool(
            type="project",
            title="No Git Project",
            use_git=False,
            registry_path=git_registry,
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        # Verify no new commit
        log_after = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        final_count = len(log_after.stdout.strip().splitlines())

        assert final_count == initial_count

    def test_create_default_use_git_is_true(self, git_registry):
        """Test that use_git defaults to True"""
        result = create_entity_tool(
            type="project",
            title="Default Git Project",
            registry_path=git_registry,
        )

        assert result["success"] is True
        assert result["git_committed"] is True

    def test_create_commit_message_format(self, git_registry):
        """Test that commit message follows expected format"""
        result = create_entity_tool(
            type="project",
            title="Commit Format Test",
            id="P-FORMAT",
            use_git=True,
            registry_path=git_registry,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        message = log.stdout

        # Verify message components
        assert "Commit Format Test" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-FORMAT" in message
        assert f"Entity UID: {result['uid']}" in message

    def test_create_in_non_git_registry_handles_gracefully(self, temp_registry, capsys):
        """Test that git operations handle non-git registry gracefully"""
        result = create_entity_tool(
            type="project",
            title="Non Git Project",
            use_git=True,  # Requesting git, but registry is not git
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        out = capsys.readouterr().out
        assert "not inside a git repository" in out

    def test_create_sequential_commits(self, git_registry):
        """Test that multiple creations produce separate commits"""
        # Create first entity
        result1 = create_entity_tool(
            type="project",
            title="First Project",
            use_git=True,
            registry_path=git_registry,
        )

        # Create second entity
        result2 = create_entity_tool(
            type="project",
            title="Second Project",
            use_git=True,
            registry_path=git_registry,
        )

        assert result1["success"] is True
        assert result2["success"] is True

        # Verify both commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result1["uid"] in log.stdout or "First Project" in log.stdout
        assert result2["uid"] in log.stdout or "Second Project" in log.stdout

        # Count commits (initial + 2 new)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 3

    def test_create_commit_includes_category(self, git_registry):
        """Test that commit message includes category when provided"""
        result = create_entity_tool(
            type="project",
            title="Category Test",
            category="software.dev/cli-tool",
            use_git=True,
            registry_path=git_registry,
        )

        assert result["success"] is True

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Category: software.dev/cli-tool" in log.stdout

    def test_create_commit_includes_status(self, git_registry):
        """Test that commit message includes status"""
        result = create_entity_tool(
            type="project",
            title="Status Test",
            status="on-hold",
            use_git=True,
            registry_path=git_registry,
        )

        assert result["success"] is True

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Status: on-hold" in log.stdout


class TestCreateEntityToolErrorHandling:
    """Tests for error handling in create_entity_tool"""

    def test_create_handles_duplicate_id_error(self, temp_registry):
        """Test that DuplicateIdError is handled correctly"""
        with patch("hxc.mcp.tools.CreateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.create_entity.side_effect = DuplicateIdError(
                "project with id 'P-001' already exists in this registry"
            )
            MockOperation.return_value = mock_instance

            result = create_entity_tool(
                type="project",
                title="Test",
                id="P-001",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "P-001" in result["error"]
        assert "already exists" in result["error"].lower()

    def test_create_handles_path_security_error(self, temp_registry):
        """Test that path security errors are handled"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.CreateOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.create_entity.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = create_entity_tool(
                type="project",
                title="Security Test",
                use_git=False,
                registry_path=temp_registry,
            )

        assert result["success"] is False
        assert "Security error" in result["error"]


class TestCreateEntityToolBehavioralParity:
    """Tests to verify create_entity_tool behaves identically to CLI"""

    def test_create_uid_generation_format(self, temp_registry):
        """Test that UID generation follows same format as CLI"""
        result = create_entity_tool(
            type="project",
            title="UID Format Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        uid = result["uid"]

        # UID should be 8 characters (first 8 chars of UUID)
        assert len(uid) == 8
        # Should be valid hex characters
        assert all(c in "0123456789abcdef-" for c in uid)

    def test_create_auto_id_generation(self, temp_registry):
        """Test that auto-ID generation follows same rules as CLI"""
        result = create_entity_tool(
            type="project",
            title="My Amazing Project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        # ID should be lowercase, spaces replaced with underscores
        assert result["id"] == "my_amazing_project"

    def test_create_id_uniqueness_matches_cli(self, temp_registry):
        """Test that ID uniqueness validation matches CLI behavior"""
        # Create first entity
        result1 = create_entity_tool(
            type="project",
            title="Collision Test",
            use_git=False,
            registry_path=temp_registry,
        )
        assert result1["success"] is True

        # Create second with explicit duplicate ID
        result2 = create_entity_tool(
            type="project",
            title="Another Project",
            id=result1["id"],  # Use first entity's ID
            use_git=False,
            registry_path=temp_registry,
        )

        # Should fail just like CLI
        assert result2["success"] is False
        assert "already exists" in result2["error"].lower()

    def test_create_file_naming_convention(self, temp_registry):
        """Test that file naming matches CLI convention"""
        result = create_entity_tool(
            type="project",
            title="Naming Test",
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        file_path = Path(result["file_path"])

        # File should be named {prefix}-{uid}.yml
        assert file_path.name == f"proj-{result['uid']}.yml"

    def test_create_entity_data_structure(self, temp_registry):
        """Test that entity data structure matches CLI output"""
        result = create_entity_tool(
            type="project",
            title="Structure Test",
            description="Test description",
            status="planned",
            category="test/category",
            tags=["tag1", "tag2"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        entity = result["entity"]

        # Verify all expected fields are present
        assert entity["type"] == "project"
        assert entity["uid"] == result["uid"]
        assert entity["id"] == result["id"]
        assert entity["title"] == "Structure Test"
        assert entity["description"] == "Test description"
        assert entity["status"] == "planned"
        assert entity["category"] == "test/category"
        assert entity["tags"] == ["tag1", "tag2"]
        assert "start_date" in entity
        assert entity["children"] == []
        assert entity["related"] == []
        assert entity["repositories"] == []
        assert entity["storage"] == []
        assert entity["databases"] == []
        assert entity["tools"] == []
        assert entity["models"] == []
        assert entity["knowledge_bases"] == []


class TestCreateEntityToolIntegration:
    """Integration tests for create_entity_tool"""

    def test_create_then_get(self, temp_registry):
        """Test creating an entity and then retrieving it"""
        create_result = create_entity_tool(
            type="project",
            title="Integration Project",
            use_git=False,
            registry_path=temp_registry,
        )

        assert create_result["success"] is True
        uid = create_result["uid"]

        get_result = get_entity_tool(
            identifier=uid,
            registry_path=temp_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["title"] == "Integration Project"

    def test_create_then_list(self, temp_registry):
        """Test creating an entity and then listing it"""
        create_result = create_entity_tool(
            type="mission",
            title="Listable Mission",
            use_git=False,
            registry_path=temp_registry,
        )

        assert create_result["success"] is True
        uid = create_result["uid"]

        list_result = list_entities_tool(
            entity_type="mission",
            identifier=uid,
            registry_path=temp_registry,
        )

        assert list_result["success"] is True
        assert list_result["count"] >= 1

        found = any(e["uid"] == uid for e in list_result["entities"])
        assert found

    def test_create_with_git_then_verify_commit(self, git_registry):
        """Test creating with git and verifying the commit exists"""
        create_result = create_entity_tool(
            type="project",
            title="Git Integration Test",
            id="P-GIT-INT",
            use_git=True,
            registry_path=git_registry,
        )

        assert create_result["success"] is True
        assert create_result["git_committed"] is True

        # Verify we can get the entity
        get_result = get_entity_tool(
            identifier="P-GIT-INT",
            registry_path=git_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["title"] == "Git Integration Test"

        # Verify git commit
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Git Integration Test" in log.stdout
        assert "P-GIT-INT" in log.stdout


class TestCreateEntityToolReadOnlyMode:
    """Tests for create_entity_tool in read-only server mode"""

    def test_create_not_available_in_read_only_mode(self, temp_registry):
        """Test that create tool is not available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "create_entity" not in tools

    def test_create_available_in_read_write_mode(self, temp_registry):
        """Test that create tool is available in read-write server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=False)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "create_entity" in tools

    def test_read_only_server_rejects_create_tool_call(self, temp_registry):
        """Test that calling create tool on read-only server returns error"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_entity",
                "arguments": {"type": "project", "title": "Blocked"},
            },
        }

        response = server.handle_request(request)
        assert "error" in response