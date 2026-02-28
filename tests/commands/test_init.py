"""
Tests for the init command
"""
import os
import pathlib
import shutil
import sqlite3
import pytest
from unittest.mock import patch, Mock, MagicMock

from hxc.cli import main
from hxc.commands.init import InitCommand
from hxc.core.config import Config


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
    with patch('hxc.commands.registry.Config') as registry_config, \
         patch('hxc.commands.init.Config') as init_config:
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
        
        # Check git commands were called
        assert mock_run.call_count == 3
        
        # Check git init was called
        args, kwargs = mock_run.call_args_list[0]
        assert args[0] == ["git", "init"]
        
        # Check git add was called
        args, kwargs = mock_run.call_args_list[1]
        assert args[0] == ["git", "add", "."]
        
        # Check git commit was called
        args, kwargs = mock_run.call_args_list[2]
        assert args[0][0:2] == ["git", "commit"]
        
        # Verify config was updated with registry path
        mock_config.set.assert_called_once_with(
            InitCommand.CONFIG_KEY,
            str(temp_dir.resolve())
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
        InitCommand.CONFIG_KEY,
        str(temp_dir.resolve())
    )


@patch("subprocess.run")
def test_init_no_commit(mock_run, temp_dir, mock_config):
    """Test initialization with --no-commit option"""
    result = main(["init", str(temp_dir), "--no-commit"])
    
    # Check the result is successful
    assert result == 0
    
    # Check git init was called but not commit
    assert mock_run.call_count == 1
    
    # Check the git init command
    args, kwargs = mock_run.call_args_list[0]
    assert args[0] == ["git", "init"]
    
    # Verify config was updated with registry path
    mock_config.set.assert_called_once_with(
        InitCommand.CONFIG_KEY,
        str(temp_dir.resolve())
    )


@patch("subprocess.run")
def test_init_with_remote(mock_run, temp_dir, mock_config):
    """Test initialization with --remote option"""
    remote_url = "https://github.com/user/repo.git"
    result = main(["init", str(temp_dir), "--remote", remote_url])
    
    # Check the result is successful
    assert result == 0
    
    # Check git commands were called (init, remote add, add, commit, push)
    assert mock_run.call_count == 5
    
    # Check git init was called
    args, kwargs = mock_run.call_args_list[0]
    assert args[0] == ["git", "init"]
    
    # Check git remote add was called
    args, kwargs = mock_run.call_args_list[1]
    assert args[0] == ["git", "remote", "add", "origin", remote_url]
    
    # Check git add was called
    args, kwargs = mock_run.call_args_list[2]
    assert args[0] == ["git", "add", "."]
    
    # Check git commit was called
    args, kwargs = mock_run.call_args_list[3]
    assert args[0][0:2] == ["git", "commit"]
    
    # Check git push was called
    args, kwargs = mock_run.call_args_list[4]
    assert args[0][0:2] == ["git", "push"]
    
    # Verify config was updated with registry path
    mock_config.set.assert_called_once_with(
        InitCommand.CONFIG_KEY,
        str(temp_dir.resolve())
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
    mock_print.assert_called_with("⚠️  Warning: Directory is not empty. Registry initialization aborted.")
    
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
@patch("hxc.commands.init.InitCommand.initialize_registry", side_effect=Exception("Test error"))
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