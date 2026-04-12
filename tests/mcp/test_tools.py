"""
Tests for MCP Tools implementation.

This module tests the tools that enable LLM interaction with HoxCore registries
through the Model Context Protocol.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityStatus, EntityType, SortField
from hxc.core.operations.create import CreateOperation, DuplicateIdError
from hxc.core.operations.delete import (
    AmbiguousEntityError,
    DeleteOperation,
    DeleteOperationError,
    EntityNotFoundError,
)
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
from hxc.core.operations.init import (
    DirectoryNotEmptyError,
    GitOperationError,
    InitOperation,
    InitOperationError,
)
from hxc.core.operations.list import ListOperation, ListOperationError
from hxc.mcp.tools import (
    create_entity_tool,
    delete_entity_tool,
    edit_entity_tool,
    get_entity_hierarchy_tool,
    get_entity_property_tool,
    get_entity_tool,
    get_registry_stats_tool,
    init_registry_tool,
    list_entities_tool,
    search_entities_tool,
)


@pytest.fixture
def temp_registry():
    """Create a temporary test registry"""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)

    # Create test entities
    project1_content = """
type: project
uid: proj-test-001
id: P-001
title: Test Project One
description: A test project for MCP tools testing
status: active
category: software.dev/cli-tool
tags: [test, mcp, cli]
start_date: 2024-01-01
due_date: 2024-12-31
children: []
related: []
repositories:
  - name: github
    url: https://github.com/test/repo
storage:
  - name: gdrive
    provider: google-drive
    url: https://drive.google.com/test
"""
    (registry_path / "projects" / "proj-proj-test-001.yml").write_text(project1_content)

    project2_content = """
type: project
uid: proj-test-002
id: P-002
title: Test Project Two
description: Another test project
status: completed
category: software.dev/web-app
tags: [test, web]
start_date: 2024-01-01
completion_date: 2024-06-30
children: []
related: []
"""
    (registry_path / "projects" / "proj-proj-test-002.yml").write_text(project2_content)

    program_content = """
type: program
uid: prog-test-001
id: PRG-001
title: Test Program
description: A test program
status: active
category: software.dev
tags: [test, program]
children: [proj-test-001, proj-test-002]
related: []
"""
    (registry_path / "programs" / "prog-prog-test-001.yml").write_text(program_content)

    mission_content = """
type: mission
uid: miss-test-001
id: M-001
title: Test Mission
description: A test mission
status: planned
category: research
tags: [test, mission]
parent: prog-test-001
children: []
related: []
"""
    (registry_path / "missions" / "miss-miss-test-001.yml").write_text(mission_content)

    action_content = """
type: action
uid: act-test-001
id: A-001
title: Test Action
description: A test action
status: active
category: maintenance
tags: [test, action]
children: []
related: []
"""
    (registry_path / "actions" / "act-act-test-001.yml").write_text(action_content)

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_registry_with_dates():
    """Create a temporary registry with entities having various due dates"""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Date Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)

    # Create projects with different due dates
    project_early = {
        "type": "project",
        "uid": "proj-early",
        "id": "P-EARLY",
        "title": "Early Project",
        "status": "active",
        "due_date": "2024-03-15",
    }
    (registry_path / "projects" / "proj-proj-early.yml").write_text(
        yaml.dump(project_early)
    )

    project_mid = {
        "type": "project",
        "uid": "proj-mid",
        "id": "P-MID",
        "title": "Mid Project",
        "status": "active",
        "due_date": "2024-06-30",
    }
    (registry_path / "projects" / "proj-proj-mid.yml").write_text(
        yaml.dump(project_mid)
    )

    project_late = {
        "type": "project",
        "uid": "proj-late",
        "id": "P-LATE",
        "title": "Late Project",
        "status": "active",
        "due_date": "2024-12-31",
    }
    (registry_path / "projects" / "proj-proj-late.yml").write_text(
        yaml.dump(project_late)
    )

    project_nodate = {
        "type": "project",
        "uid": "proj-nodate",
        "id": "P-NODATE",
        "title": "No Date Project",
        "status": "active",
    }
    (registry_path / "projects" / "proj-proj-nodate.yml").write_text(
        yaml.dump(project_nodate)
    )

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def git_registry():
    """Create a temporary registry that is also a git repository."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Git Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=registry_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=registry_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def git_registry_with_entities(git_registry):
    """Create a git registry with tracked entity files for deletion testing."""
    registry_path = Path(git_registry)

    # Create test project
    project_content = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Git Project",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": ["test"],
        "children": [],
        "related": [],
    }
    with open(registry_path / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project_content, f)

    # Create second project for uniqueness tests
    project2_content = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Second Git Project",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": [],
        "children": [],
        "related": [],
    }
    with open(registry_path / "projects" / "proj-proj0002.yml", "w") as f:
        yaml.dump(project2_content, f)

    # Create test program
    program_content = {
        "type": "program",
        "uid": "prog0001",
        "id": "PRG-001",
        "title": "Git Program",
        "status": "active",
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "programs" / "prog-prog0001.yml", "w") as f:
        yaml.dump(program_content, f)

    # Create test mission
    mission_content = {
        "type": "mission",
        "uid": "miss0001",
        "id": "M-001",
        "title": "Git Mission",
        "status": "planned",
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "missions" / "miss-miss0001.yml", "w") as f:
        yaml.dump(mission_content, f)

    # Create test action
    action_content = {
        "type": "action",
        "uid": "act0001",
        "id": "A-001",
        "title": "Git Action",
        "status": "active",
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "actions" / "act-act0001.yml", "w") as f:
        yaml.dump(action_content, f)

    # Stage and commit the entity files
    subprocess.run(
        ["git", "add", "."], cwd=registry_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Add test entities"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )

    return git_registry


@pytest.fixture
def empty_temp_dir():
    """Create an empty temporary directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def non_empty_temp_dir():
    """Create a non-empty temporary directory"""
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "existing_file.txt"
    test_file.write_text("This file makes the directory non-empty")
    yield temp_dir
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


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
        import sqlite3

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

    def test_init_with_git_initialization(self, empty_temp_dir):
        """Test initialization with git repository"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True
        assert result["git_initialized"] is True
        assert result["committed"] is True

        # Verify .git directory exists
        git_dir = Path(empty_temp_dir) / ".git"
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

    def test_init_with_git_no_commit(self, empty_temp_dir):
        """Test initialization with git but without commit"""
        result = init_registry_tool(
            path=empty_temp_dir,
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

    def test_init_with_git_creates_repository(self, empty_temp_dir):
        """Test that git repository is created when use_git=True"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True
        assert result["git_initialized"] is True

        # Verify .git directory exists
        git_dir = Path(empty_temp_dir) / ".git"
        assert git_dir.exists()

    def test_init_with_git_creates_initial_commit(self, empty_temp_dir):
        """Test that initial commit is created"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True
        assert result["committed"] is True

        # Verify commit exists
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=empty_temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Initialize HoxCore registry" in log.stdout

    def test_init_commit_message_format(self, empty_temp_dir):
        """Test that commit message follows expected format"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=empty_temp_dir,
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

    def test_init_all_files_committed(self, empty_temp_dir):
        """Test that all registry files are committed"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True

        # Check git status - should be clean
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=empty_temp_dir,
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
        import sqlite3

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

    def test_init_and_cli_produce_same_git_history(self, empty_temp_dir):
        """Test that MCP init produces same git commit as CLI would"""
        result = init_registry_tool(
            path=empty_temp_dir,
            use_git=True,
            commit=True,
            set_default=False,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=empty_temp_dir,
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

    def test_init_with_git_then_create_with_commit(self, empty_temp_dir):
        """Test full workflow: init with git, then create entity with commit"""
        # Initialize registry with git
        init_result = init_registry_tool(
            path=empty_temp_dir,
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
            registry_path=empty_temp_dir,
        )

        assert create_result["success"] is True
        assert create_result["git_committed"] is True

        # Verify both commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=empty_temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have at least 2 commits (init + create)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 2

    def test_init_full_lifecycle(self, empty_temp_dir):
        """Test complete lifecycle: init -> create -> edit -> delete"""
        # Initialize
        init_result = init_registry_tool(
            path=empty_temp_dir,
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
            registry_path=empty_temp_dir,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]

        # Edit
        edit_result = edit_entity_tool(
            identifier=uid,
            set_title="Edited Lifecycle Project",
            use_git=True,
            registry_path=empty_temp_dir,
        )
        assert edit_result["success"] is True

        # Delete
        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=True,
            registry_path=empty_temp_dir,
        )
        assert delete_result["success"] is True

        # Verify git history has all commits
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=empty_temp_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have at least 4 commits (init + create + edit + delete)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 4


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

    def test_get_entity_uses_list_operation(self, temp_registry):
        """Test that get_entity_tool uses ListOperation internally"""
        with patch("hxc.mcp.tools.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_entity_by_identifier.return_value = {
                "type": "project",
                "uid": "proj-test-001",
                "id": "P-001",
                "title": "Test Project",
                "_file": {"path": "/test/path.yml"},
            }
            MockOperation.return_value = mock_instance

            result = get_entity_tool(identifier="P-001", registry_path=temp_registry)

        MockOperation.assert_called_once_with(temp_registry)
        mock_instance.get_entity_by_identifier.assert_called_once()


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


class TestToolsIntegration:
    """Integration tests for MCP tools"""

    def test_list_then_get(self, temp_registry):
        """Test listing entities then getting specific one"""
        # First list
        list_result = list_entities_tool(
            entity_type="project", registry_path=temp_registry
        )

        assert list_result["success"] is True
        assert len(list_result["entities"]) > 0

        # Get first entity
        entity_id = list_result["entities"][0]["id"]
        get_result = get_entity_tool(identifier=entity_id, registry_path=temp_registry)

        assert get_result["success"] is True
        assert get_result["entity"]["id"] == entity_id

    def test_search_then_get_property(self, temp_registry):
        """Test searching then getting property"""
        # First search
        search_result = search_entities_tool(query="test", registry_path=temp_registry)

        assert search_result["success"] is True
        assert search_result["count"] > 0

        # Get property from first result
        entity_id = search_result["entities"][0]["id"]
        property_result = get_entity_property_tool(
            identifier=entity_id, property_name="title", registry_path=temp_registry
        )

        assert property_result["success"] is True
        assert "value" in property_result

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
        child_result = get_entity_tool(identifier=child_id, registry_path=temp_registry)

        assert child_result["success"] is True

    def test_stats_then_list_by_type(self, temp_registry):
        """Test getting stats then listing by type"""
        # Get stats
        stats_result = get_registry_stats_tool(registry_path=temp_registry)

        assert stats_result["success"] is True
        by_type = stats_result["stats"]["by_type"]

        # List each type
        for entity_type, count in by_type.items():
            list_result = list_entities_tool(
                entity_type=entity_type, registry_path=temp_registry
            )

            assert list_result["success"] is True
            assert list_result["count"] == count


class TestToolsErrorHandling:
    """Tests for error handling in tools"""

    def test_list_with_security_error(self):
        """Test list with path security error"""
        result = list_entities_tool(entity_type="all", registry_path="/etc/passwd")

        assert result["success"] is False
        assert "error" in result

    def test_get_with_security_error(self):
        """Test get with path security error"""
        result = get_entity_tool(identifier="test", registry_path="/etc/passwd")

        assert result["success"] is False
        assert "error" in result

    def test_search_with_empty_query(self, temp_registry):
        """Test search with empty query"""
        result = search_entities_tool(query="", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] >= 0

    def test_property_with_none_value(self, temp_registry):
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
        result = edit_entity_tool(
            identifier="PRG-001",
            remove_children=["proj-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "proj-test-001" not in result["entity"]["children"]

    def test_edit_add_duplicate_child_is_idempotent(self, temp_registry):
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
        result = edit_entity_tool(
            identifier="A-001",
            add_related=["proj-test-001"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        assert "proj-test-001" in result["entity"]["related"]

    def test_edit_add_duplicate_related_is_idempotent(self, temp_registry):
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

        result = edit_entity_tool(
            identifier="PRG-001",
            remove_children=["nonexistent-uid"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True  # anything_specified=True, but no error raised

    def test_edit_remove_nonexistent_related_is_noop(self, temp_registry):

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

    # ─── ID UNIQUENESS TESTS ────────────────────────────────────────────────────

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


class TestReadOnlyServer:
    """Tests for the --read-only server mode"""

    def test_read_only_server_omits_write_tools(self, temp_registry):
        """Test that a read-only server does not expose write tools"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "list_entities" in tools
        assert "get_entity" in tools
        assert "search_entities" in tools
        assert "get_entity_property" in tools

        assert "init_registry" not in tools
        assert "create_entity" not in tools
        assert "edit_entity" not in tools
        assert "delete_entity" not in tools

    def test_read_only_server_capabilities_flag(self, temp_registry):
        """Test that read_only is reflected in capabilities"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        assert server.get_capabilities()["read_only"] is True

    def test_non_read_only_server_exposes_write_tools(self, temp_registry):
        """Test that a normal server does expose write tools"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=False)
        tools = server.get_capabilities()["tools"]

        assert "init_registry" in tools
        assert "create_entity" in tools
        assert "edit_entity" in tools
        assert "delete_entity" in tools

    def test_read_only_server_rejects_write_tool_call(self, temp_registry):
        """Test that calling a write tool on a read-only server returns an error"""
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
        # Should return an error because the tool is not registered
        assert "error" in response


class TestWriteToolsIntegration:
    """Integration tests for the full create → edit → delete lifecycle"""

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

    def test_create_then_edit(self, temp_registry):
        """Test creating an entity and then editing it"""
        create_result = create_entity_tool(
            type="mission",
            title="Original Mission",
            use_git=False,
            registry_path=temp_registry,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]

        edit_result = edit_entity_tool(
            identifier=uid,
            set_title="Updated Mission",
            add_tags=["important"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert edit_result["success"] is True
        assert edit_result["entity"]["title"] == "Updated Mission"
        assert "important" in edit_result["entity"]["tags"]

    def test_create_edit_delete_lifecycle(self, temp_registry):
        """Test the full entity lifecycle"""
        # Create
        create_result = create_entity_tool(
            type="action",
            title="Lifecycle Action",
            use_git=False,
            registry_path=temp_registry,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]
        file_path = Path(create_result["file_path"])
        assert file_path.exists()

        # Edit
        edit_result = edit_entity_tool(
            identifier=uid,
            set_status="completed",
            use_git=False,
            registry_path=temp_registry,
        )
        assert edit_result["success"] is True

        # Confirm before delete
        confirm_result = delete_entity_tool(
            identifier=uid,
            force=False,
            registry_path=temp_registry,
        )
        assert confirm_result.get("confirmation_required") is True
        assert file_path.exists()  # not deleted yet

        # Delete with force
        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )
        assert delete_result["success"] is True
        assert not file_path.exists()

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

    def test_create_then_delete_with_git(self, git_registry):
        """Test creating and then deleting an entity with git integration"""
        # Create
        create_result = create_entity_tool(
            type="project",
            title="Git Delete Test",
            id="P-GIT-DEL",
            use_git=True,
            registry_path=git_registry,
        )

        assert create_result["success"] is True
        uid = create_result["uid"]

        # Delete
        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=True,
            registry_path=git_registry,
        )

        assert delete_result["success"] is True
        assert delete_result["git_committed"] is True

        # Verify both commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have create and delete commits
        assert "Create" in log.stdout or "Git Delete Test" in log.stdout
        assert "Delete" in log.stdout

    def test_full_lifecycle_with_git(self, git_registry):
        """Test full create -> edit -> delete lifecycle with git"""
        # Create
        create_result = create_entity_tool(
            type="project",
            title="Lifecycle Git Test",
            id="P-LIFECYCLE",
            use_git=True,
            registry_path=git_registry,
        )
        assert create_result["success"] is True
        assert create_result["git_committed"] is True
        uid = create_result["uid"]

        # Edit
        edit_result = edit_entity_tool(
            identifier=uid,
            set_title="Lifecycle Git Test - Edited",
            use_git=True,
            registry_path=git_registry,
        )
        assert edit_result["success"] is True
        assert edit_result["git_committed"] is True

        # Delete
        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=True,
            registry_path=git_registry,
        )
        assert delete_result["success"] is True
        # File was committed by edit, so git rm should work
        assert delete_result["git_committed"] is True

        # Verify git history has create, edit, and delete commits
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        # Should have at least initial + create + edit + delete
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 4


class TestMCPCLIBehavioralParity:
    """Tests to verify MCP tools behave identically to CLI commands"""

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

    def test_edit_change_format_matches_cli(self, temp_registry):
        """Test that edit change descriptions match CLI format"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="New Title",
            add_tags=["new-tag"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert result["success"] is True
        changes = result["changes"]

        # Should have changes in expected format
        assert any("title" in c.lower() for c in changes)
        assert any("tag" in c.lower() for c in changes)

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

    def test_delete_handles_untracked_files_like_cli(self, git_registry):
        """Test that MCP handles untracked files the same as CLI"""
        # Create an untracked entity file
        untracked_entity = {
            "type": "project",
            "uid": "untracked",
            "id": "P-UNTRACKED",
            "title": "Untracked Project",
            "status": "active",
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


class TestEditEntityToolBehavioralParityWithCLI:
    """Tests to verify edit_entity_tool produces identical results to CLI"""

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
