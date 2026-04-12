"""
Tests for the init command
"""

import os
import pathlib
import shutil
import sqlite3
from unittest.mock import MagicMock, Mock, patch

import pytest

from hxc.cli import main
from hxc.commands.init import InitCommand
from hxc.core.config import Config
from hxc.core.operations.init import (
    DirectoryNotEmptyError,
    GitOperationError,
    InitOperation,
    InitOperationError,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing"""
    yield tmp_path
    # Clean up
    if tmp_path.exists():
        shutil.rmtree(tmp_path)


@pytest.fixture
def mock_config():
    """Mock the Config class"""
    # Need to patch the Config in both modules
    with patch("hxc.commands.registry.Config") as registry_config, patch(
        "hxc.commands.init.Config"
    ) as init_config:
        # Create a single mock instance that both patches will return
        mock_config = MagicMock()
        registry_config.return_value = mock_config
        init_config.return_value = mock_config
        yield mock_config


def test_init_command_registration():
    """Test that the init command is properly registered"""
    from hxc.commands import get_available_commands

    available_commands = get_available_commands()
    assert "init" in available_commands


def test_init_command_parser():
    """Test init command parser registration"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = InitCommand.register_subparser(subparsers)

    # Verify parser has the expected arguments
    actions = {action.dest for action in cmd_parser._actions}
    assert "path" in actions
    assert "no_git" in actions
    assert "no_commit" in actions
    assert "remote" in actions
    assert "no_set_default" in actions


@patch("subprocess.run")
def test_init_basic(mock_run, temp_dir, mock_config):
    """Test basic initialization with default options"""
    # Change current working directory to the temp directory
    orig_dir = os.getcwd()
    os.chdir(temp_dir)

    try:
        # Execute the command
        result = main(["init"])

        # Check the result is successful
        assert result == 0

        # Check directories were created
        for folder in ["programs", "projects", "missions", "actions"]:
            assert (temp_dir / folder).exists()

        # Check config file was created
        config_path = temp_dir / "config.yml"
        assert config_path.exists()

        # Check index.db was created
        db_path = temp_dir / "index.db"
        assert db_path.exists()

        # Verify database has expected structure
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            assert ("registry_info",) in tables

            cursor.execute("SELECT key FROM registry_info WHERE key='created_at'")
            result = cursor.fetchone()
            assert result is not None
        finally:
            conn.close()

        # Check git commands were called (git --version, git init, git add, git commit)
        assert mock_run.call_count == 4

        # Check git --version was called first
        args, kwargs = mock_run.call_args_list[0]
        assert args[0] == ["git", "--version"]

        # Check git init was called
        args, kwargs = mock_run.call_args_list[1]
        assert args[0] == ["git", "init"]

        # Check git add was called
        args, kwargs = mock_run.call_args_list[2]
        assert args[0] == ["git", "add", "."]

        # Check git commit was called
        args, kwargs = mock_run.call_args_list[3]
        assert args[0][0:2] == ["git", "commit"]

        # Verify config was updated with registry path
        mock_config.set.assert_called_once_with(
            InitCommand.CONFIG_KEY, str(temp_dir.resolve())
        )
    finally:
        # Restore original directory
        os.chdir(orig_dir)


@patch("subprocess.run")
def test_init_no_git(mock_run, temp_dir, mock_config):
    """Test initialization with --no-git option"""
    result = main(["init", str(temp_dir), "--no-git"])

    # Check the result is successful
    assert result == 0

    # Check directories were created
    for folder in ["programs", "projects", "missions", "actions"]:
        assert (temp_dir / folder).exists()

    # Check git commands were NOT called
    assert mock_run.call_count == 0

    # Verify config was updated with registry path
    mock_config.set.assert_called_once_with(
        InitCommand.CONFIG_KEY, str(temp_dir.resolve())
    )


@patch("subprocess.run")
def test_init_no_commit(mock_run, temp_dir, mock_config):
    """Test initialization with --no-commit option"""
    result = main(["init", str(temp_dir), "--no-commit"])

    # Check the result is successful
    assert result == 0

    # Check git --version and git init were called but not commit
    assert mock_run.call_count == 2

    # Check git --version was called
    args, kwargs = mock_run.call_args_list[0]
    assert args[0] == ["git", "--version"]

    # Check the git init command
    args, kwargs = mock_run.call_args_list[1]
    assert args[0] == ["git", "init"]

    # Verify config was updated with registry path
    mock_config.set.assert_called_once_with(
        InitCommand.CONFIG_KEY, str(temp_dir.resolve())
    )


@patch("subprocess.run")
def test_init_with_remote(mock_run, temp_dir, mock_config):
    """Test initialization with --remote option"""
    remote_url = "https://github.com/user/repo.git"
    result = main(["init", str(temp_dir), "--remote", remote_url])

    # Check the result is successful
    assert result == 0

    # Check git commands were called (git --version, init, remote add, add, commit, push)
    assert mock_run.call_count == 6

    # Check git --version was called
    args, kwargs = mock_run.call_args_list[0]
    assert args[0] == ["git", "--version"]

    # Check git init was called
    args, kwargs = mock_run.call_args_list[1]
    assert args[0] == ["git", "init"]

    # Check git remote add was called
    args, kwargs = mock_run.call_args_list[2]
    assert args[0] == ["git", "remote", "add", "origin", remote_url]

    # Check git add was called
    args, kwargs = mock_run.call_args_list[3]
    assert args[0] == ["git", "add", "."]

    # Check git commit was called
    args, kwargs = mock_run.call_args_list[4]
    assert args[0][0:2] == ["git", "commit"]

    # Check git push was called
    args, kwargs = mock_run.call_args_list[5]
    assert args[0][0:2] == ["git", "push"]

    # Verify config was updated with registry path
    mock_config.set.assert_called_once_with(
        InitCommand.CONFIG_KEY, str(temp_dir.resolve())
    )


@patch("builtins.print")
def test_init_non_empty_directory(mock_print, temp_dir):
    """Test initialization in a non-empty directory"""
    # Create a file to make the directory non-empty
    test_file = temp_dir / "existing_file.txt"
    test_file.write_text("This is a test file")

    # Try to initialize
    result = main(["init", str(temp_dir)])

    # Check the result is successful (no error)
    assert result == 0

    # Check warning was printed
    mock_print.assert_called_with(
        "⚠️  Warning: Directory is not empty. Registry initialization aborted."
    )

    # Check that no directories were created
    assert not (temp_dir / "programs").exists()


@patch("subprocess.run")
def test_init_no_set_default(mock_run, temp_dir, mock_config):
    """Test initialization with --no-set-default option"""
    result = main(["init", str(temp_dir), "--no-set-default"])

    # Check the result is successful
    assert result == 0

    # Verify config was NOT updated with registry path
    mock_config.set.assert_not_called()


@patch("subprocess.run")
@patch(
    "hxc.commands.init.InitCommand.initialize_registry",
    side_effect=Exception("Test error"),
)
def test_init_error_handling(mock_init_registry, mock_run, temp_dir, mock_config):
    """Test error handling during initialization"""
    with patch("builtins.print") as mock_print:
        result = main(["init", str(temp_dir)])

        # Check result indicates failure
        assert result == 1

        # Verify error message was printed
        mock_print.assert_called_with("❌ Error initializing registry: Test error")

        # Verify config was NOT updated
        mock_config.set.assert_not_called()


def test_registry_path_consistency():
    """Test that registry path keys are consistent between Init and Registry commands"""
    from hxc.commands.registry import RegistryCommand

    # Verify both commands use the same configuration key
    assert InitCommand.CONFIG_KEY == RegistryCommand.CONFIG_KEY
    assert InitCommand.CONFIG_KEY == "registry_path"


class TestInitCommandUsesSharedOperation:
    """Tests to verify InitCommand uses the shared InitOperation"""

    def test_initialize_registry_uses_init_operation(self, temp_dir):
        """Test that initialize_registry method uses InitOperation internally"""
        with patch("hxc.commands.init.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.return_value = {
                "success": True,
                "registry_path": str(temp_dir.resolve()),
                "git_initialized": False,
                "committed": False,
                "pushed": False,
                "remote_added": False,
            }
            MockOperation.return_value = mock_instance

            result = InitCommand.initialize_registry(
                path=str(temp_dir),
                use_git=False,
            )

            MockOperation.assert_called_once_with(str(temp_dir))
            mock_instance.initialize_registry.assert_called_once()

    def test_initialize_registry_passes_all_parameters(self, temp_dir):
        """Test that initialize_registry passes all parameters to InitOperation"""
        with patch("hxc.commands.init.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.return_value = {
                "success": True,
                "registry_path": str(temp_dir.resolve()),
                "git_initialized": True,
                "committed": True,
                "pushed": False,
                "remote_added": True,
            }
            MockOperation.return_value = mock_instance

            result = InitCommand.initialize_registry(
                path=str(temp_dir),
                use_git=True,
                commit=True,
                remote_url="https://github.com/user/repo.git",
            )

            call_kwargs = mock_instance.initialize_registry.call_args[1]
            assert call_kwargs["use_git"] is True
            assert call_kwargs["commit"] is True
            assert call_kwargs["remote_url"] == "https://github.com/user/repo.git"
            assert call_kwargs["force_empty_check"] is True


class TestInitCommandExceptionHandling:
    """Tests for exception handling in InitCommand"""

    def test_directory_not_empty_error_handling(self, temp_dir, mock_config):
        """Test that DirectoryNotEmptyError is handled correctly"""
        # Create a file to make directory non-empty
        test_file = temp_dir / "existing.txt"
        test_file.write_text("content")

        with patch("builtins.print") as mock_print:
            result = main(["init", str(temp_dir)])

        assert result == 0
        mock_print.assert_called_with(
            "⚠️  Warning: Directory is not empty. Registry initialization aborted."
        )

    def test_git_operation_error_handling(self, temp_dir, mock_config):
        """Test that GitOperationError is handled correctly"""
        with patch("hxc.commands.init.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = GitOperationError(
                "Git init failed: permission denied"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                result = main(["init", str(temp_dir)])

            assert result == 1
            mock_print.assert_called_with(
                "❌ Git operation failed: Git init failed: permission denied"
            )

    def test_path_security_error_handling(self, temp_dir, mock_config):
        """Test that PathSecurityError is handled correctly"""
        from hxc.utils.path_security import PathSecurityError

        with patch("hxc.commands.init.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = PathSecurityError(
                "Path traversal detected"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                result = main(["init", str(temp_dir)])

            assert result == 1
            mock_print.assert_called_with("❌ Security error: Path traversal detected")

    def test_init_operation_error_handling(self, temp_dir, mock_config):
        """Test that InitOperationError is handled correctly"""
        with patch("hxc.commands.init.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = InitOperationError(
                "Failed to create directory"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                result = main(["init", str(temp_dir)])

            assert result == 1
            mock_print.assert_called_with(
                "❌ Error initializing registry: Failed to create directory"
            )

    def test_unexpected_exception_handling(self, temp_dir, mock_config):
        """Test that unexpected exceptions are handled correctly"""
        with patch("hxc.commands.init.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = RuntimeError(
                "Unexpected error"
            )
            MockOperation.return_value = mock_instance

            with patch("builtins.print") as mock_print:
                result = main(["init", str(temp_dir)])

            assert result == 1
            mock_print.assert_called_with(
                "❌ Error initializing registry: Unexpected error"
            )


class TestInitCommandBehavioralParity:
    """Tests to verify CLI command produces identical results to MCP tool"""

    @patch("subprocess.run")
    def test_creates_all_required_folders(self, mock_run, temp_dir, mock_config):
        """Test that CLI creates same folders as InitOperation"""
        result = main(["init", str(temp_dir), "--no-git"])

        assert result == 0

        # Same folders as InitOperation.REQUIRED_FOLDERS
        expected_folders = ["programs", "projects", "missions", "actions"]
        for folder in expected_folders:
            assert (temp_dir / folder).exists()
            assert (temp_dir / folder).is_dir()

    @patch("subprocess.run")
    def test_creates_marker_directory(self, mock_run, temp_dir, mock_config):
        """Test that CLI creates .hxc marker directory"""
        result = main(["init", str(temp_dir), "--no-git"])

        assert result == 0

        marker_dir = temp_dir / ".hxc"
        assert marker_dir.exists()
        assert marker_dir.is_dir()

    @patch("subprocess.run")
    def test_creates_config_file_with_correct_content(
        self, mock_run, temp_dir, mock_config
    ):
        """Test that CLI creates config.yml with correct content"""
        result = main(["init", str(temp_dir), "--no-git"])

        assert result == 0

        config_path = temp_dir / "config.yml"
        assert config_path.exists()
        content = config_path.read_text()
        assert content == InitOperation.CONFIG_CONTENT

    @patch("subprocess.run")
    def test_creates_gitignore_with_correct_content(
        self, mock_run, temp_dir, mock_config
    ):
        """Test that CLI creates .gitignore with correct content"""
        result = main(["init", str(temp_dir), "--no-git"])

        assert result == 0

        gitignore_path = temp_dir / ".gitignore"
        assert gitignore_path.exists()
        content = gitignore_path.read_text()
        assert content == InitOperation.GITIGNORE_CONTENT
        assert "index.db" in content

    @patch("subprocess.run")
    def test_creates_index_database_with_correct_schema(
        self, mock_run, temp_dir, mock_config
    ):
        """Test that CLI creates index.db with correct schema"""
        result = main(["init", str(temp_dir), "--no-git"])

        assert result == 0

        db_path = temp_dir / "index.db"
        assert db_path.exists()

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()

            # Same table as InitOperation
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            assert "registry_info" in tables

            # Same created_at key
            cursor.execute("SELECT key FROM registry_info")
            keys = [row[0] for row in cursor.fetchall()]
            assert "created_at" in keys
        finally:
            conn.close()

    @patch("subprocess.run")
    def test_returns_absolute_path(self, mock_run, temp_dir, mock_config, capsys):
        """Test that CLI reports absolute path"""
        result = main(["init", str(temp_dir), "--no-git"])

        assert result == 0

        captured = capsys.readouterr()
        # The absolute path should be in the output
        assert str(temp_dir.resolve()) in captured.out

    @patch("subprocess.run")
    def test_git_initialization_flow(self, mock_run, temp_dir, mock_config):
        """Test that git initialization follows expected flow"""
        result = main(["init", str(temp_dir)])

        assert result == 0
        # git --version, git init, git add, git commit
        assert mock_run.call_count == 4

        # Verify order: version check, init, add, commit
        calls = [call[0][0] for call in mock_run.call_args_list]
        assert calls[0] == ["git", "--version"]
        assert calls[1] == ["git", "init"]
        assert calls[2] == ["git", "add", "."]
        assert calls[3][0:2] == ["git", "commit"]


class TestInitCommandGitIntegration:
    """Tests for git integration in init command"""

    @patch("subprocess.run")
    def test_git_commit_message(self, mock_run, temp_dir, mock_config):
        """Test that git commit uses expected message"""
        result = main(["init", str(temp_dir)])

        assert result == 0

        # Find the commit call
        commit_call = None
        for call in mock_run.call_args_list:
            if call[0][0][0:2] == ["git", "commit"]:
                commit_call = call
                break

        assert commit_call is not None
        commit_args = commit_call[0][0]
        assert "-m" in commit_args
        message_index = commit_args.index("-m") + 1
        assert "Initialize HoxCore registry" in commit_args[message_index]

    @patch("subprocess.run")
    def test_git_remote_configuration(self, mock_run, temp_dir, mock_config):
        """Test that git remote is configured correctly"""
        remote_url = "https://github.com/user/repo.git"
        result = main(["init", str(temp_dir), "--remote", remote_url])

        assert result == 0

        # Find the remote add call
        remote_call = None
        for call in mock_run.call_args_list:
            if len(call[0][0]) >= 3 and call[0][0][0:3] == ["git", "remote", "add"]:
                remote_call = call
                break

        assert remote_call is not None
        assert remote_call[0][0] == ["git", "remote", "add", "origin", remote_url]

    @patch("subprocess.run")
    def test_git_push_after_remote(self, mock_run, temp_dir, mock_config):
        """Test that git push is attempted after setting remote"""
        remote_url = "https://github.com/user/repo.git"
        result = main(["init", str(temp_dir), "--remote", remote_url])

        assert result == 0

        # Find the push call
        push_call = None
        for call in mock_run.call_args_list:
            if len(call[0][0]) >= 2 and call[0][0][0:2] == ["git", "push"]:
                push_call = call
                break

        assert push_call is not None


class TestInitCommandConfigIntegration:
    """Tests for config integration in init command"""

    @patch("subprocess.run")
    def test_sets_default_registry(self, mock_run, temp_dir, mock_config):
        """Test that registry is set as default"""
        result = main(["init", str(temp_dir)])

        assert result == 0
        mock_config.set.assert_called_once_with(
            "registry_path", str(temp_dir.resolve())
        )

    @patch("subprocess.run")
    def test_no_set_default_skips_config(self, mock_run, temp_dir, mock_config):
        """Test that --no-set-default skips config update"""
        result = main(["init", str(temp_dir), "--no-set-default"])

        assert result == 0
        mock_config.set.assert_not_called()

    @patch("subprocess.run")
    def test_config_not_set_on_error(self, mock_run, temp_dir, mock_config):
        """Test that config is not set when initialization fails"""
        with patch("hxc.commands.init.InitOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.initialize_registry.side_effect = InitOperationError("Failed")
            MockOperation.return_value = mock_instance

            result = main(["init", str(temp_dir)])

        assert result == 1
        mock_config.set.assert_not_called()

    @patch("subprocess.run")
    def test_config_not_set_on_non_empty_directory(
        self, mock_run, temp_dir, mock_config
    ):
        """Test that config is not set when directory is non-empty"""
        # Create a file to make directory non-empty
        test_file = temp_dir / "existing.txt"
        test_file.write_text("content")

        result = main(["init", str(temp_dir)])

        assert result == 0
        mock_config.set.assert_not_called()


class TestInitCommandEdgeCases:
    """Tests for edge cases in init command"""

    @patch("subprocess.run")
    def test_init_with_spaces_in_path(self, mock_run, temp_dir, mock_config):
        """Test initialization with spaces in path"""
        path_with_spaces = temp_dir / "path with spaces"
        path_with_spaces.mkdir()

        result = main(["init", str(path_with_spaces), "--no-git"])

        assert result == 0
        assert (path_with_spaces / "programs").exists()

    @patch("subprocess.run")
    def test_init_creates_nested_directories(self, mock_run, tmp_path, mock_config):
        """Test initialization creates nested directories"""
        nested_path = tmp_path / "level1" / "level2" / "registry"

        result = main(["init", str(nested_path), "--no-git"])

        assert result == 0
        assert nested_path.exists()
        assert (nested_path / "programs").exists()

    @patch("subprocess.run")
    def test_init_current_directory_default(self, mock_run, temp_dir, mock_config):
        """Test that init defaults to current directory"""
        orig_dir = os.getcwd()
        os.chdir(temp_dir)

        try:
            result = main(["init", "--no-git"])

            assert result == 0
            assert (temp_dir / "programs").exists()
        finally:
            os.chdir(orig_dir)

    def test_init_hidden_files_not_counted_as_non_empty(self, temp_dir, mock_config):
        """Test that hidden files don't make directory count as non-empty"""
        # Create a hidden file
        hidden_file = temp_dir / ".hidden_file"
        hidden_file.write_text("hidden content")

        with patch("subprocess.run"):
            result = main(["init", str(temp_dir), "--no-git"])

        assert result == 0
        assert (temp_dir / "programs").exists()
