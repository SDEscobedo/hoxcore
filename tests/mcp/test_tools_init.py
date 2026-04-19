"""
Tests for init_registry_tool in MCP Tools.

This module tests the init_registry_tool that enables initializing new
HoxCore registries through the Model Context Protocol.
"""

import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hxc.core.operations.init import (
    DirectoryNotEmptyError,
    GitOperationError,
    InitOperation,
    InitOperationError,
)
from hxc.mcp.tools import (
    create_entity_tool,
    get_registry_stats_tool,
    init_registry_tool,
    list_entities_tool,
)


class TestInitRegistryTool:
    """Tests for init_registry_tool"""

    def test_init_basic(self, empty_temp_dir):
        """Test basic initialization with default options"""
        with patch("subprocess.run"):
            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=False,
                set_default=False,
            )

        assert result["success"] is True
        assert "registry_path" in result
        assert Path(result["registry_path"]).is_absolute()

        # Verify directory structure
        base = Path(empty_temp_dir)
        assert (base / "programs").exists()
        assert (base / "projects").exists()
        assert (base / "missions").exists()
        assert (base / "actions").exists()
        assert (base / "config.yml").exists()
        assert (base / ".gitignore").exists()
        assert (base / "index.db").exists()
        assert (base / ".hxc").exists()

    def test_init_creates_all_required_folders(self, empty_temp_dir):
        """Test that all required entity folders are created"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        base = Path(empty_temp_dir)
        for folder in ["programs", "projects", "missions", "actions"]:
            assert (base / folder).exists()
            assert (base / folder).is_dir()

    def test_init_creates_config_file(self, empty_temp_dir):
        """Test that config file is created"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        config_path = Path(empty_temp_dir) / "config.yml"
        assert config_path.exists()
        content = config_path.read_text()
        assert "#" in content  # Should have comment header

    def test_init_creates_gitignore(self, empty_temp_dir):
        """Test that .gitignore is created with correct content"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        gitignore_path = Path(empty_temp_dir) / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text()
        assert "index.db" in content

    def test_init_creates_index_database(self, empty_temp_dir):
        """Test that index database is created with correct schema"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        db_path = Path(empty_temp_dir) / "index.db"
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "registry_info" in tables

            cursor.execute("SELECT key FROM registry_info WHERE key='created_at'")
            result_row = cursor.fetchone()
            assert result_row is not None
        finally:
            conn.close()

    def test_init_creates_marker_directory(self, empty_temp_dir):
        """Test that .hxc marker directory is created"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        marker_path = Path(empty_temp_dir) / ".hxc"
        assert marker_path.exists()
        assert marker_path.is_dir()

    def test_init_with_git_initialization(self, empty_temp_dir_with_git):
        """Test initialization with git repository"""
        result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True
        assert result["git_initialized"] is True
        assert result["committed"] is True

        # Verify .git directory exists
        git_dir = Path(empty_temp_dir_with_git) / ".git"
        assert git_dir.exists()

    def test_init_without_git(self, empty_temp_dir):
        """Test initialization without git"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True
        assert result["git_initialized"] is False
        assert result["committed"] is False

        # Verify .git directory does NOT exist
        git_dir = Path(empty_temp_dir) / ".git"
        assert not git_dir.exists()

    def test_init_with_git_no_commit(self, empty_temp_dir_with_git):
        """Test initialization with git but without commit"""
        result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=False,
            set_default=False,
        )

        assert result["success"] is True
        assert result["git_initialized"] is True
        assert result["committed"] is False

    @patch("subprocess.run")
    def test_init_with_remote_url(self, mock_run, empty_temp_dir):
        """Test initialization with git remote URL"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            remote_url="https://github.com/user/repo.git",
            set_default=False,
        )

        assert result["success"] is True
        assert result["remote_added"] is True

        # Verify git remote add was called
        remote_calls = [
            call
            for call in mock_run.call_args_list
            if len(call[0][0]) >= 4 and call[0][0][:3] == ["git", "remote", "add"]
        ]
        assert len(remote_calls) >= 1

    def test_init_non_empty_directory_fails(self, non_empty_temp_dir):
        """Test that initialization fails for non-empty directory"""
        result = init_registry_tool(
            path=non_empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is False
        assert "error" in result
        assert (
            "not empty" in result["error"].lower() or "empty" in result["error"].lower()
        )

    def test_init_returns_absolute_path(self, empty_temp_dir):
        """Test that returned path is absolute"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True
        assert Path(result["registry_path"]).is_absolute()

    def test_init_nested_path(self):
        """Test initialization in a nested path that doesn't exist"""
        temp_dir = tempfile.mkdtemp()
        try:
            nested_path = Path(temp_dir) / "level1" / "level2" / "registry"

            result = init_registry_tool(
                path=str(nested_path),
                use_git=False,
                set_default=False,
            )

            assert result["success"] is True
            assert nested_path.exists()
            assert (nested_path / "programs").exists()
        finally:
            shutil.rmtree(temp_dir)

    def test_init_empty_path_fails(self):
        """Test that empty path returns an error"""
        result = init_registry_tool(
            path="",
            use_git=False,
            set_default=False,
        )

        assert result["success"] is False
        assert "error" in result

    def test_init_returns_set_as_default_field(self, empty_temp_dir):
        """Test that result includes set_as_default field"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True
        assert "set_as_default" in result
        assert result["set_as_default"] is False

    def test_init_with_set_default_true(self, empty_temp_dir):
        """Test initialization with set_default=True"""
        with patch("hxc.mcp.tools.Config") as MockConfig:
            mock_instance = MagicMock()
            MockConfig.return_value = mock_instance

            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=False,
                set_default=True,
            )

        assert result["success"] is True
        assert result["set_as_default"] is True
        mock_instance.set.assert_called_once()

    def test_init_with_set_default_false(self, empty_temp_dir):
        """Test initialization with set_default=False"""
        with patch("hxc.mcp.tools.Config") as MockConfig:
            mock_instance = MagicMock()
            MockConfig.return_value = mock_instance

            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=False,
                set_default=False,
            )

        assert result["success"] is True
        assert result["set_as_default"] is False
        mock_instance.set.assert_not_called()


class TestInitRegistryToolUsesSharedOperation:
    """Tests to verify init_registry_tool uses the shared InitOperation"""

    def test_init_uses_init_operation(self, empty_temp_dir):
        """Test that init_registry_tool uses InitOperation internally"""
        with patch("hxc.mcp.tools.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.return_value = {
                "success": True,
                "registry_path": str(Path(empty_temp_dir).resolve()),
                "git_initialized": False,
                "committed": False,
                "pushed": False,
                "remote_added": False,
            }
            MockOperation.return_value = mock_instance

            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=False,
                set_default=False,
            )

        MockOperation.assert_called_once_with(empty_temp_dir)
        mock_instance.initialize_registry.assert_called_once()

    def test_init_passes_all_parameters_to_operation(self, empty_temp_dir):
        """Test that init_registry_tool passes all parameters to InitOperation"""
        with patch("hxc.mcp.tools.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.return_value = {
                "success": True,
                "registry_path": str(Path(empty_temp_dir).resolve()),
                "git_initialized": True,
                "committed": True,
                "pushed": False,
                "remote_added": True,
            }
            MockOperation.return_value = mock_instance

            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=True,
                commit=True,
                remote_url="https://github.com/user/repo.git",
                set_default=False,
            )

        call_kwargs = mock_instance.initialize_registry.call_args[1]
        assert call_kwargs["use_git"] is True
        assert call_kwargs["commit"] is True
        assert call_kwargs["remote_url"] == "https://github.com/user/repo.git"
        assert call_kwargs["force_empty_check"] is True

    def test_init_handles_directory_not_empty_error(self, non_empty_temp_dir):
        """Test that DirectoryNotEmptyError is handled correctly"""
        result = init_registry_tool(
            path=non_empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is False
        assert "error" in result
        assert non_empty_temp_dir in result.get("path", "")

    def test_init_handles_git_operation_error(self, empty_temp_dir):
        """Test that GitOperationError is handled correctly"""
        with patch("hxc.mcp.tools.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = GitOperationError(
                "Git operation failed: permission denied"
            )
            MockOperation.return_value = mock_instance

            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=True,
                set_default=False,
            )

        assert result["success"] is False
        assert "Git operation failed" in result["error"]

    def test_init_handles_init_operation_error(self, empty_temp_dir):
        """Test that InitOperationError is handled correctly"""
        with patch("hxc.mcp.tools.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = InitOperationError(
                "Failed to create directory"
            )
            MockOperation.return_value = mock_instance

            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=False,
                set_default=False,
            )

        assert result["success"] is False
        assert "Failed to create directory" in result["error"]

    def test_init_handles_path_security_error(self, empty_temp_dir):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.mcp.tools.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            result = init_registry_tool(
                path=empty_temp_dir,
                use_git=False,
                set_default=False,
            )

        assert result["success"] is False
        assert "Security error" in result["error"]


class TestInitRegistryToolGitIntegration:
    """Tests for git integration in init_registry_tool"""

    def test_init_with_git_creates_repository(self, empty_temp_dir_with_git):
        """Test that git repository is created when use_git=True"""
        result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True
        assert result["git_initialized"] is True

        # Verify .git directory exists
        git_dir = Path(empty_temp_dir_with_git) / ".git"
        assert git_dir.exists()

    def test_init_with_git_creates_initial_commit(self, empty_temp_dir_with_git):
        """Test that initial commit is created"""
        result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True
        assert result["committed"] is True

        # Verify commit exists
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=empty_temp_dir_with_git,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Initialize HoxCore registry" in log.stdout

    def test_init_commit_message_format(self, empty_temp_dir_with_git):
        """Test that commit message follows expected format"""
        result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=empty_temp_dir_with_git,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Initialize HoxCore registry" in log.stdout

    @patch("subprocess.run")
    def test_init_with_remote_adds_origin(self, mock_run, empty_temp_dir):
        """Test that remote is added when URL specified"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            remote_url="https://github.com/user/repo.git",
            set_default=False,
        )

        assert result["success"] is True
        assert result["remote_added"] is True

        # Verify git remote add was called
        remote_add_calls = [
            call
            for call in mock_run.call_args_list
            if (
                len(call[0][0]) >= 5
                and call[0][0][:4] == ["git", "remote", "add", "origin"]
            )
        ]
        assert len(remote_add_calls) >= 1

    def test_init_all_files_committed(self, empty_temp_dir_with_git):
        """Test that all registry files are committed"""
        result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True

        # Check git status - should be clean
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=empty_temp_dir_with_git,
            capture_output=True,
            text=True,
            check=True,
        )

        # Only index.db should be untracked (in .gitignore)
        # All other files should be committed
        lines = [line for line in status.stdout.strip().split("\n") if line]
        for line in lines:
            # Untracked files start with '??'
            if line.startswith("??"):
                assert "index.db" in line


class TestInitRegistryToolReadOnlyMode:
    """Tests for init_registry_tool in read-only server mode"""

    def test_init_not_available_in_read_only_mode(self, empty_temp_dir):
        """Test that init tool is not available in read-only server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=empty_temp_dir, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "init_registry" not in tools

    def test_init_available_in_read_write_mode(self, empty_temp_dir):
        """Test that init tool is available in read-write server"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=empty_temp_dir, read_only=False)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "init_registry" in tools

    def test_read_only_server_rejects_init_tool_call(self, empty_temp_dir):
        """Test that calling init tool on read-only server returns error"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=empty_temp_dir, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "init_registry",
                "arguments": {"path": empty_temp_dir},
            },
        }

        response = server.handle_request(request)
        assert "error" in response


class TestInitRegistryToolBehavioralParityWithCLI:
    """Tests to verify init_registry_tool produces identical results to CLI"""

    def test_init_produces_same_directory_structure(self, empty_temp_dir):
        """Test that MCP init produces same directory structure as CLI"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        base = Path(empty_temp_dir)

        # Same folders as CLI
        expected_folders = ["programs", "projects", "missions", "actions"]
        for folder in expected_folders:
            assert (base / folder).exists()
            assert (base / folder).is_dir()

        # Same marker directory as CLI
        assert (base / ".hxc").exists()
        assert (base / ".hxc").is_dir()

    def test_init_produces_same_config_file(self, empty_temp_dir):
        """Test that config file content matches CLI"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        config_path = Path(empty_temp_dir) / "config.yml"
        assert config_path.exists()
        content = config_path.read_text()

        # Should match CLI config content
        assert content == InitOperation.CONFIG_CONTENT

    def test_init_produces_same_gitignore(self, empty_temp_dir):
        """Test that .gitignore content matches CLI"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        gitignore_path = Path(empty_temp_dir) / ".gitignore"
        content = gitignore_path.read_text()

        # Should match CLI gitignore content
        assert content == InitOperation.GITIGNORE_CONTENT

    def test_init_produces_same_database_schema(self, empty_temp_dir):
        """Test that database schema matches CLI"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        db_path = Path(empty_temp_dir) / "index.db"
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Same table as CLI
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "registry_info" in tables

            # Same created_at key as CLI
            cursor.execute("SELECT key FROM registry_info")
            keys = [row[0] for row in cursor.fetchall()]
            assert "created_at" in keys
        finally:
            conn.close()

    def test_init_and_cli_produce_same_git_history(self, empty_temp_dir_with_git):
        """Test that MCP init produces same git commit as CLI would"""
        result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=empty_temp_dir_with_git,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should match CLI commit message
        assert "Initialize HoxCore registry" in log.stdout

    def test_init_file_count_matches_cli(self, empty_temp_dir):
        """Test that number of files/folders matches CLI output"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )

        assert result["success"] is True

        base = Path(empty_temp_dir)

        # Count all files and directories
        items = list(base.iterdir())

        # Expected: 4 entity folders + .hxc + config.yml + .gitignore + index.db
        expected_count = 8
        assert len(items) == expected_count


class TestInitRegistryToolIntegration:
    """Integration tests for init_registry_tool"""

    def test_init_then_create_entity(self, empty_temp_dir):
        """Test creating an entity in a newly initialized registry"""
        # Initialize registry
        init_result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )
        assert init_result["success"] is True

        # Create entity in the new registry
        create_result = create_entity_tool(
            type="project",
            title="First Project",
            use_git=False,
            registry_path=empty_temp_dir,
        )

        assert create_result["success"] is True
        assert "uid" in create_result

        # Verify file was created in the registry
        file_path = Path(create_result["file_path"])
        assert file_path.exists()
        assert file_path.parent.name == "projects"

    def test_init_then_list_entities(self, empty_temp_dir):
        """Test listing entities in a newly initialized (empty) registry"""
        # Initialize registry
        init_result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )
        assert init_result["success"] is True

        # List entities (should be empty)
        list_result = list_entities_tool(
            entity_type="all",
            registry_path=empty_temp_dir,
        )

        assert list_result["success"] is True
        assert list_result["count"] == 0
        assert list_result["entities"] == []

    def test_init_then_get_stats(self, empty_temp_dir):
        """Test getting stats from a newly initialized registry"""
        # Initialize registry
        init_result = init_registry_tool(
            path=empty_temp_dir,
            use_git=False,
            set_default=False,
        )
        assert init_result["success"] is True

        # Get stats
        stats_result = get_registry_stats_tool(registry_path=empty_temp_dir)

        assert stats_result["success"] is True
        assert stats_result["stats"]["total_entities"] == 0
        assert stats_result["stats"]["by_type"]["project"] == 0
        assert stats_result["stats"]["by_type"]["program"] == 0
        assert stats_result["stats"]["by_type"]["mission"] == 0
        assert stats_result["stats"]["by_type"]["action"] == 0

    def test_init_with_git_then_create_with_commit(self, empty_temp_dir_with_git):
        """Test full workflow: init with git, then create entity with commit"""
        # Initialize registry with git
        init_result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )
        assert init_result["success"] is True
        assert init_result["git_initialized"] is True

        # Create entity with git commit
        create_result = create_entity_tool(
            type="project",
            title="Git Tracked Project",
            use_git=True,
            registry_path=empty_temp_dir_with_git,
        )

        assert create_result["success"] is True
        assert create_result["git_committed"] is True

        # Verify both commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=empty_temp_dir_with_git,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have at least 2 commits (init + create)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 2

    def test_init_full_lifecycle(self, empty_temp_dir_with_git):
        """Test complete lifecycle: init -> create -> edit -> delete"""
        from hxc.mcp.tools import delete_entity_tool, edit_entity_tool

        # Initialize
        init_result = init_registry_tool(
            path=empty_temp_dir_with_git,
            use_git=True,
            commit=True,
            set_default=False,
        )
        assert init_result["success"] is True

        # Create
        create_result = create_entity_tool(
            type="project",
            title="Lifecycle Test Project",
            use_git=True,
            registry_path=empty_temp_dir_with_git,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]

        # Edit
        edit_result = edit_entity_tool(
            identifier=uid,
            set_title="Edited Lifecycle Project",
            use_git=True,
            registry_path=empty_temp_dir_with_git,
        )
        assert edit_result["success"] is True

        # Delete
        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=True,
            registry_path=empty_temp_dir_with_git,
        )
        assert delete_result["success"] is True

        # Verify git history has all commits
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=empty_temp_dir_with_git,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have at least 4 commits (init + create + edit + delete)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 4
