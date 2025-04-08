"""
Tests for the init command
"""
import os
import pathlib
import shutil
import pytest
from unittest.mock import patch, Mock

from hxc.cli import main
from hxc.commands.init import InitCommand


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing"""
    yield tmp_path
    # Clean up
    if tmp_path.exists():
        shutil.rmtree(tmp_path)


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


@patch("subprocess.run")
def test_init_basic(mock_run, temp_dir):
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
        
        # Check git commands were called
        assert mock_run.call_count == 3
        
        # Check git init was called - fixed assertion
        args, kwargs = mock_run.call_args_list[0]
        assert args[0] == ["git", "init"]
        
        # Check git add was called
        args, kwargs = mock_run.call_args_list[1]
        assert args[0] == ["git", "add", "."]
        
        # Check git commit was called
        args, kwargs = mock_run.call_args_list[2]
        assert args[0][0:2] == ["git", "commit"]
    finally:
        # Restore original directory
        os.chdir(orig_dir)


@patch("subprocess.run")
def test_init_no_git(mock_run, temp_dir):
    """Test initialization with --no-git option"""
    result = main(["init", str(temp_dir), "--no-git"])
    
    # Check the result is successful
    assert result == 0
    
    # Check directories were created
    for folder in ["programs", "projects", "missions", "actions"]:
        assert (temp_dir / folder).exists()
    
    # Check git commands were NOT called
    assert mock_run.call_count == 0


@patch("subprocess.run")
def test_init_no_commit(mock_run, temp_dir):
    """Test initialization with --no-commit option"""
    result = main(["init", str(temp_dir), "--no-commit"])
    
    # Check the result is successful
    assert result == 0
    
    # Check git init was called but not commit
    assert mock_run.call_count == 1
    
    # Fixed assertion to properly check the git init command
    args, kwargs = mock_run.call_args_list[0]
    assert args[0] == ["git", "init"]