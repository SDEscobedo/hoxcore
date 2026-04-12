"""
Tests for the init operation module.

This module tests the shared initialization logic that ensures behavioral
consistency between CLI commands and MCP tools.
"""

import os
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
from hxc.utils.path_security import PathSecurityError


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)


@pytest.fixture
def empty_temp_dir(temp_dir):
    """Create an empty temporary directory"""
    return temp_dir


@pytest.fixture
def non_empty_temp_dir(temp_dir):
    """Create a non-empty temporary directory"""
    test_file = Path(temp_dir) / "existing_file.txt"
    test_file.write_text("This file makes the directory non-empty")
    return temp_dir


@pytest.fixture
def temp_dir_with_hidden_files(temp_dir):
    """Create a temporary directory with only hidden files"""
    hidden_file = Path(temp_dir) / ".hidden_file"
    hidden_file.write_text("Hidden content")
    return temp_dir


class TestInitOperationConstants:
    """Tests for InitOperation class constants"""

    def test_required_folders(self):
        """Test that required folders are correctly defined"""
        assert InitOperation.REQUIRED_FOLDERS == [
            "programs",
            "projects",
            "missions",
            "actions",
        ]

    def test_config_file_name(self):
        """Test config file name constant"""
        assert InitOperation.CONFIG_FILE == "config.yml"

    def test_marker_directory_name(self):
        """Test marker directory name constant"""
        assert InitOperation.MARKER_DIR == ".hxc"

    def test_index_database_name(self):
        """Test index database name constant"""
        assert InitOperation.INDEX_DB == "index.db"

    def test_gitignore_name(self):
        """Test gitignore file name constant"""
        assert InitOperation.GITIGNORE == ".gitignore"

    def test_gitignore_content(self):
        """Test gitignore default content"""
        assert "index.db" in InitOperation.GITIGNORE_CONTENT


class TestInitOperationResolveBasePath:
    """Tests for _resolve_base_path method"""

    def test_resolve_relative_path(self, temp_dir):
        """Test resolving a relative path"""
        operation = InitOperation(temp_dir)
        resolved = operation._resolve_base_path()

        assert resolved.is_absolute()
        assert resolved == Path(temp_dir).resolve()

    def test_resolve_absolute_path(self, temp_dir):
        """Test resolving an absolute path"""
        abs_path = os.path.abspath(temp_dir)
        operation = InitOperation(abs_path)
        resolved = operation._resolve_base_path()

        assert resolved == Path(abs_path).resolve()

    def test_resolve_path_with_dots(self, temp_dir):
        """Test resolving a path with .. components"""
        nested_path = os.path.join(temp_dir, "subdir", "..")
        operation = InitOperation(nested_path)
        resolved = operation._resolve_base_path()

        assert resolved == Path(temp_dir).resolve()

    def test_resolve_stores_base_path(self, temp_dir):
        """Test that resolved path is stored in instance"""
        operation = InitOperation(temp_dir)
        operation._resolve_base_path()

        assert operation.base_path is not None
        assert operation.base_path == Path(temp_dir).resolve()


class TestInitOperationCheckDirectoryEmpty:
    """Tests for _check_directory_empty method"""

    def test_empty_directory_returns_true(self, empty_temp_dir):
        """Test that empty directory returns True"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        assert operation._check_directory_empty(base) is True

    def test_non_empty_directory_returns_false(self, non_empty_temp_dir):
        """Test that non-empty directory returns False"""
        operation = InitOperation(non_empty_temp_dir)
        base = Path(non_empty_temp_dir)

        assert operation._check_directory_empty(base) is False

    def test_directory_with_hidden_files_only_returns_true(
        self, temp_dir_with_hidden_files
    ):
        """Test that directory with only hidden files is considered empty"""
        operation = InitOperation(temp_dir_with_hidden_files)
        base = Path(temp_dir_with_hidden_files)

        assert operation._check_directory_empty(base) is True

    def test_nonexistent_directory_returns_true(self, temp_dir):
        """Test that nonexistent directory returns True"""
        nonexistent = os.path.join(temp_dir, "does_not_exist")
        operation = InitOperation(nonexistent)
        base = Path(nonexistent)

        assert operation._check_directory_empty(base) is True


class TestInitOperationCreateDirectoryStructure:
    """Tests for _create_directory_structure method"""

    def test_creates_all_required_folders(self, empty_temp_dir):
        """Test that all required folders are created"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        operation._create_directory_structure(base)

        for folder in InitOperation.REQUIRED_FOLDERS:
            assert (base / folder).exists()
            assert (base / folder).is_dir()

    def test_creates_marker_directory(self, empty_temp_dir):
        """Test that .hxc marker directory is created"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        operation._create_directory_structure(base)

        marker = base / InitOperation.MARKER_DIR
        assert marker.exists()
        assert marker.is_dir()

    def test_creates_base_directory_if_not_exists(self, temp_dir):
        """Test that base directory is created if it doesn't exist"""
        new_base = os.path.join(temp_dir, "new_registry")
        operation = InitOperation(new_base)
        base = Path(new_base)

        operation._create_directory_structure(base)

        assert base.exists()
        assert base.is_dir()

    def test_idempotent_creation(self, empty_temp_dir):
        """Test that calling create twice doesn't cause errors"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        operation._create_directory_structure(base)
        operation._create_directory_structure(base)

        for folder in InitOperation.REQUIRED_FOLDERS:
            assert (base / folder).exists()


class TestInitOperationCreateConfigFile:
    """Tests for _create_config_file method"""

    def test_creates_config_file(self, empty_temp_dir):
        """Test that config file is created"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        config_path = operation._create_config_file(base)

        assert config_path.exists()
        assert config_path.name == InitOperation.CONFIG_FILE

    def test_config_file_has_content(self, empty_temp_dir):
        """Test that config file has expected content"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        config_path = operation._create_config_file(base)

        content = config_path.read_text()
        assert content == InitOperation.CONFIG_CONTENT

    def test_does_not_overwrite_existing_config(self, empty_temp_dir):
        """Test that existing config is not overwritten"""
        base = Path(empty_temp_dir)
        config_path = base / InitOperation.CONFIG_FILE
        existing_content = "existing: configuration"
        config_path.write_text(existing_content)

        operation = InitOperation(empty_temp_dir)
        operation._create_config_file(base)

        assert config_path.read_text() == existing_content


class TestInitOperationCreateGitignore:
    """Tests for _create_gitignore method"""

    def test_creates_gitignore_file(self, empty_temp_dir):
        """Test that .gitignore file is created"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        gitignore_path = operation._create_gitignore(base)

        assert gitignore_path.exists()
        assert gitignore_path.name == InitOperation.GITIGNORE

    def test_gitignore_contains_index_db(self, empty_temp_dir):
        """Test that .gitignore contains index.db"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        gitignore_path = operation._create_gitignore(base)

        content = gitignore_path.read_text()
        assert "index.db" in content


class TestInitOperationCreateIndexDatabase:
    """Tests for _create_index_database method"""

    def test_creates_database_file(self, empty_temp_dir):
        """Test that database file is created"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        db_path = operation._create_index_database(base)

        assert db_path.exists()
        assert db_path.name == InitOperation.INDEX_DB

    def test_database_has_registry_info_table(self, empty_temp_dir):
        """Test that database has registry_info table"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        db_path = operation._create_index_database(base)

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "registry_info" in tables
        finally:
            conn.close()

    def test_database_has_created_at_entry(self, empty_temp_dir):
        """Test that database has created_at entry"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        db_path = operation._create_index_database(base)

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM registry_info WHERE key='created_at'")
            result = cursor.fetchone()
            assert result is not None
        finally:
            conn.close()

    def test_does_not_recreate_existing_database(self, empty_temp_dir):
        """Test that existing database is not recreated"""
        base = Path(empty_temp_dir)
        db_path = base / InitOperation.INDEX_DB

        # Create database with custom data
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE custom_table (id INTEGER)")
            conn.commit()
        finally:
            conn.close()

        operation = InitOperation(empty_temp_dir)
        operation._create_index_database(base)

        # Verify custom table still exists
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "custom_table" in tables
        finally:
            conn.close()


class TestInitOperationGitAvailable:
    """Tests for _git_available method"""

    def test_returns_true_when_git_installed(self, empty_temp_dir):
        """Test that returns True when git is installed"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            result = operation._git_available()

        assert result is True

    def test_returns_false_when_git_not_installed(self, empty_temp_dir):
        """Test that returns False when git is not installed"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            result = operation._git_available()

        assert result is False

    def test_returns_false_when_git_command_fails(self, empty_temp_dir):
        """Test that returns False when git command fails"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "git")
            result = operation._git_available()

        assert result is False


class TestInitOperationInitGitRepository:
    """Tests for _init_git_repository method"""

    @patch("subprocess.run")
    def test_initializes_git_repository(self, mock_run, empty_temp_dir):
        """Test that git repository is initialized"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        # Create structure first
        operation._create_directory_structure(base)

        result = operation._init_git_repository(base)

        assert result["initialized"] is True
        # Verify git init was called
        init_calls = [
            call for call in mock_run.call_args_list if call[0][0] == ["git", "init"]
        ]
        assert len(init_calls) >= 1

    @patch("subprocess.run")
    def test_adds_remote_when_specified(self, mock_run, empty_temp_dir):
        """Test that remote is added when URL specified"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)
        remote_url = "https://github.com/user/repo.git"

        operation._create_directory_structure(base)
        result = operation._init_git_repository(base, remote_url=remote_url)

        assert result["remote_added"] is True
        # Verify git remote add was called
        remote_calls = [
            call
            for call in mock_run.call_args_list
            if len(call[0][0]) >= 4 and call[0][0][:3] == ["git", "remote", "add"]
        ]
        assert len(remote_calls) >= 1

    @patch("subprocess.run")
    def test_creates_initial_commit(self, mock_run, empty_temp_dir):
        """Test that initial commit is created"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        operation._create_directory_structure(base)
        result = operation._init_git_repository(base, commit=True)

        assert result["committed"] is True
        # Verify git commit was called
        commit_calls = [
            call
            for call in mock_run.call_args_list
            if len(call[0][0]) >= 2 and call[0][0][:2] == ["git", "commit"]
        ]
        assert len(commit_calls) >= 1

    @patch("subprocess.run")
    def test_skips_commit_when_false(self, mock_run, empty_temp_dir):
        """Test that commit is skipped when commit=False"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        operation._create_directory_structure(base)
        result = operation._init_git_repository(base, commit=False)

        assert result["committed"] is False
        # Verify git commit was NOT called
        commit_calls = [
            call
            for call in mock_run.call_args_list
            if len(call[0][0]) >= 2 and call[0][0][:2] == ["git", "commit"]
        ]
        assert len(commit_calls) == 0

    @patch("subprocess.run")
    def test_returns_not_initialized_when_git_unavailable(
        self, mock_run, empty_temp_dir
    ):
        """Test that returns not initialized when git unavailable"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        # Make git unavailable
        mock_run.side_effect = FileNotFoundError()

        result = operation._init_git_repository(base)

        assert result["initialized"] is False

    @patch("subprocess.run")
    def test_skips_init_when_git_already_exists(self, mock_run, empty_temp_dir):
        """Test that skips init when .git already exists"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        # Create .git directory
        (base / ".git").mkdir()

        result = operation._init_git_repository(base)

        assert result["initialized"] is True
        # Verify git init was NOT called (already exists)
        init_calls = [
            call for call in mock_run.call_args_list if call[0][0] == ["git", "init"]
        ]
        assert len(init_calls) == 0

    @patch("subprocess.run")
    def test_raises_git_operation_error_on_failure(self, mock_run, empty_temp_dir):
        """Test that GitOperationError is raised on git failure"""
        operation = InitOperation(empty_temp_dir)
        base = Path(empty_temp_dir)

        # Make git fail after init check
        def side_effect(*args, **kwargs):
            if args[0] == ["git", "--version"]:
                return MagicMock()
            raise subprocess.CalledProcessError(1, args[0], stderr=b"git error")

        mock_run.side_effect = side_effect

        with pytest.raises(GitOperationError):
            operation._init_git_repository(base)


class TestInitOperationInitializeRegistry:
    """Tests for initialize_registry method"""

    @patch("subprocess.run")
    def test_full_initialization(self, mock_run, empty_temp_dir):
        """Test full registry initialization"""
        operation = InitOperation(empty_temp_dir)

        result = operation.initialize_registry(use_git=True, commit=True)

        assert result["success"] is True
        assert "registry_path" in result
        assert result["git_initialized"] is True
        assert result["committed"] is True

    @patch("subprocess.run")
    def test_creates_all_structure(self, mock_run, empty_temp_dir):
        """Test that all registry structure is created"""
        operation = InitOperation(empty_temp_dir)

        operation.initialize_registry(use_git=False)

        base = Path(empty_temp_dir)

        # Check folders
        for folder in InitOperation.REQUIRED_FOLDERS:
            assert (base / folder).exists()

        # Check files
        assert (base / InitOperation.CONFIG_FILE).exists()
        assert (base / InitOperation.GITIGNORE).exists()
        assert (base / InitOperation.INDEX_DB).exists()
        assert (base / InitOperation.MARKER_DIR).exists()

    @patch("subprocess.run")
    def test_returns_absolute_path(self, mock_run, empty_temp_dir):
        """Test that returned path is absolute"""
        operation = InitOperation(empty_temp_dir)

        result = operation.initialize_registry(use_git=False)

        assert Path(result["registry_path"]).is_absolute()

    def test_raises_error_for_non_empty_directory(self, non_empty_temp_dir):
        """Test that raises error for non-empty directory"""
        operation = InitOperation(non_empty_temp_dir)

        with pytest.raises(DirectoryNotEmptyError):
            operation.initialize_registry(force_empty_check=True)

    @patch("subprocess.run")
    def test_allows_non_empty_when_check_disabled(self, mock_run, non_empty_temp_dir):
        """Test that allows non-empty when force_empty_check=False"""
        operation = InitOperation(non_empty_temp_dir)

        result = operation.initialize_registry(force_empty_check=False, use_git=False)

        assert result["success"] is True

    @patch("subprocess.run")
    def test_skips_git_when_disabled(self, mock_run, empty_temp_dir):
        """Test that git is skipped when use_git=False"""
        operation = InitOperation(empty_temp_dir)

        result = operation.initialize_registry(use_git=False)

        assert result["git_initialized"] is False
        assert mock_run.call_count == 0

    @patch("subprocess.run")
    def test_passes_remote_url_to_git(self, mock_run, empty_temp_dir):
        """Test that remote URL is passed to git initialization"""
        operation = InitOperation(empty_temp_dir)
        remote_url = "https://github.com/user/repo.git"

        result = operation.initialize_registry(use_git=True, remote_url=remote_url)

        assert result["remote_added"] is True

    @patch("subprocess.run")
    def test_handles_commit_flag(self, mock_run, empty_temp_dir):
        """Test that commit flag is respected"""
        operation = InitOperation(empty_temp_dir)

        result = operation.initialize_registry(use_git=True, commit=False)

        assert result["committed"] is False

    @patch("subprocess.run")
    def test_creates_nested_directories(self, mock_run, temp_dir):
        """Test initialization in deeply nested path"""
        nested_path = os.path.join(temp_dir, "level1", "level2", "registry")
        operation = InitOperation(nested_path)

        result = operation.initialize_registry(use_git=False)

        assert result["success"] is True
        assert Path(nested_path).exists()


class TestInitOperationValidateRegistryPath:
    """Tests for validate_registry_path class method"""

    def test_valid_new_path(self, temp_dir):
        """Test validation of new valid path"""
        new_path = os.path.join(temp_dir, "new_registry")

        result = InitOperation.validate_registry_path(new_path)

        assert result is True

    def test_existing_directory(self, empty_temp_dir):
        """Test validation of existing directory"""
        result = InitOperation.validate_registry_path(empty_temp_dir)

        assert result is True

    def test_existing_file_returns_false(self, temp_dir):
        """Test validation of path that is a file"""
        file_path = os.path.join(temp_dir, "file.txt")
        Path(file_path).write_text("content")

        result = InitOperation.validate_registry_path(file_path)

        assert result is False


class TestInitOperationIsExistingRegistry:
    """Tests for is_existing_registry class method"""

    def test_empty_directory_is_not_registry(self, empty_temp_dir):
        """Test that empty directory is not a registry"""
        result = InitOperation.is_existing_registry(empty_temp_dir)

        assert result is False

    @patch("subprocess.run")
    def test_initialized_registry_is_detected(self, mock_run, empty_temp_dir):
        """Test that initialized registry is detected"""
        operation = InitOperation(empty_temp_dir)
        operation.initialize_registry(use_git=False)

        result = InitOperation.is_existing_registry(empty_temp_dir)

        assert result is True

    def test_marker_directory_detected(self, empty_temp_dir):
        """Test that .hxc marker directory is detected"""
        base = Path(empty_temp_dir)
        (base / InitOperation.MARKER_DIR).mkdir()

        result = InitOperation.is_existing_registry(empty_temp_dir)

        assert result is True

    def test_config_with_folders_detected(self, empty_temp_dir):
        """Test that config + folders is detected as registry"""
        base = Path(empty_temp_dir)
        (base / InitOperation.CONFIG_FILE).write_text("test")
        (base / "programs").mkdir()

        result = InitOperation.is_existing_registry(empty_temp_dir)

        assert result is True

    def test_nonexistent_path_is_not_registry(self, temp_dir):
        """Test that nonexistent path is not a registry"""
        nonexistent = os.path.join(temp_dir, "does_not_exist")

        result = InitOperation.is_existing_registry(nonexistent)

        assert result is False


class TestInitOperationExceptions:
    """Tests for exception classes"""

    def test_init_operation_error_inheritance(self):
        """Test that InitOperationError inherits from Exception"""
        assert issubclass(InitOperationError, Exception)

    def test_directory_not_empty_error_inheritance(self):
        """Test that DirectoryNotEmptyError inherits from InitOperationError"""
        assert issubclass(DirectoryNotEmptyError, InitOperationError)

    def test_git_operation_error_inheritance(self):
        """Test that GitOperationError inherits from InitOperationError"""
        assert issubclass(GitOperationError, InitOperationError)

    def test_directory_not_empty_error_message(self):
        """Test DirectoryNotEmptyError message"""
        error = DirectoryNotEmptyError("Test message")
        assert str(error) == "Test message"

    def test_git_operation_error_message(self):
        """Test GitOperationError message"""
        error = GitOperationError("Git failed")
        assert str(error) == "Git failed"


class TestInitOperationIntegration:
    """Integration tests for InitOperation"""

    def test_full_registry_structure(self, empty_temp_dir):
        """Test complete registry structure after initialization"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run"):
            result = operation.initialize_registry(use_git=False)

        assert result["success"] is True

        base = Path(empty_temp_dir)

        # Verify folders
        assert (base / "programs").is_dir()
        assert (base / "projects").is_dir()
        assert (base / "missions").is_dir()
        assert (base / "actions").is_dir()
        assert (base / ".hxc").is_dir()

        # Verify files
        assert (base / "config.yml").is_file()
        assert (base / ".gitignore").is_file()
        assert (base / "index.db").is_file()

        # Verify database
        conn = sqlite3.connect(base / "index.db")
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM registry_info WHERE key='created_at'")
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_git_integration_full_flow(self, empty_temp_dir):
        """Test full git integration flow"""
        operation = InitOperation(empty_temp_dir)

        # Simulate successful git operations
        with patch("subprocess.run") as mock_run:
            result = operation.initialize_registry(
                use_git=True,
                commit=True,
                remote_url="https://github.com/user/repo.git",
            )

        assert result["success"] is True
        assert result["git_initialized"] is True
        assert result["committed"] is True
        assert result["remote_added"] is True

    def test_multiple_initializations_fail(self, empty_temp_dir):
        """Test that re-initialization of non-empty registry fails"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run"):
            # First initialization
            result1 = operation.initialize_registry(use_git=False)
            assert result1["success"] is True

            # Second initialization should fail
            with pytest.raises(DirectoryNotEmptyError):
                operation.initialize_registry(use_git=False, force_empty_check=True)

    def test_initialization_preserves_hidden_files(self, temp_dir_with_hidden_files):
        """Test that initialization preserves hidden files"""
        hidden_file = Path(temp_dir_with_hidden_files) / ".hidden_file"
        original_content = hidden_file.read_text()

        operation = InitOperation(temp_dir_with_hidden_files)

        with patch("subprocess.run"):
            result = operation.initialize_registry(use_git=False)

        assert result["success"] is True
        assert hidden_file.exists()
        assert hidden_file.read_text() == original_content


class TestInitOperationEdgeCases:
    """Tests for edge cases and error handling"""

    def test_path_with_spaces(self, temp_dir):
        """Test initialization with spaces in path"""
        path_with_spaces = os.path.join(temp_dir, "path with spaces")
        os.makedirs(path_with_spaces)

        operation = InitOperation(path_with_spaces)

        with patch("subprocess.run"):
            result = operation.initialize_registry(use_git=False)

        assert result["success"] is True

    def test_path_with_special_characters(self, temp_dir):
        """Test initialization with special characters in path"""
        # Use characters that are valid on most filesystems
        path_with_special = os.path.join(temp_dir, "path-with_special.chars")
        os.makedirs(path_with_special)

        operation = InitOperation(path_with_special)

        with patch("subprocess.run"):
            result = operation.initialize_registry(use_git=False)

        assert result["success"] is True

    def test_unicode_path(self, temp_dir):
        """Test initialization with unicode path"""
        unicode_path = os.path.join(temp_dir, "путь_registry")

        try:
            os.makedirs(unicode_path)
            operation = InitOperation(unicode_path)

            with patch("subprocess.run"):
                result = operation.initialize_registry(use_git=False)

            assert result["success"] is True
        except OSError:
            # Skip test if filesystem doesn't support unicode
            pytest.skip("Filesystem doesn't support unicode paths")

    def test_current_directory_initialization(self, empty_temp_dir):
        """Test initialization with '.' path"""
        original_dir = os.getcwd()
        try:
            os.chdir(empty_temp_dir)
            operation = InitOperation(".")

            with patch("subprocess.run"):
                result = operation.initialize_registry(use_git=False)

            assert result["success"] is True
            assert (
                Path(result["registry_path"]).resolve()
                == Path(empty_temp_dir).resolve()
            )
        finally:
            os.chdir(original_dir)


class TestInitOperationConsistencyWithCLI:
    """Tests to verify behavioral consistency with CLI command"""

    def test_same_folder_structure(self, empty_temp_dir):
        """Test that folder structure matches CLI expectations"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run"):
            operation.initialize_registry(use_git=False)

        base = Path(empty_temp_dir)

        # Same folders as CLI
        expected_folders = ["programs", "projects", "missions", "actions"]
        for folder in expected_folders:
            assert (base / folder).exists()
            assert (base / folder).is_dir()

    def test_same_config_file(self, empty_temp_dir):
        """Test that config file matches CLI expectations"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run"):
            operation.initialize_registry(use_git=False)

        config_path = Path(empty_temp_dir) / "config.yml"
        assert config_path.exists()
        # Content should be the standard header comment
        assert "#" in config_path.read_text()

    def test_same_gitignore_content(self, empty_temp_dir):
        """Test that gitignore content matches CLI expectations"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run"):
            operation.initialize_registry(use_git=False)

        gitignore_path = Path(empty_temp_dir) / ".gitignore"
        content = gitignore_path.read_text()

        # index.db should be ignored (same as CLI)
        assert "index.db" in content

    def test_same_database_schema(self, empty_temp_dir):
        """Test that database schema matches CLI expectations"""
        operation = InitOperation(empty_temp_dir)

        with patch("subprocess.run"):
            operation.initialize_registry(use_git=False)

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
