"""
Tests for the registry command
"""

import os
import pathlib
import shutil
from unittest.mock import MagicMock, patch

import pytest

from hxc.cli import main
from hxc.commands.registry import RegistryCommand
from hxc.core.config import Config


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
    # Create directory structure
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)

    # Create marker files and directories
    (registry_path / ".hxc").mkdir()
    (registry_path / "config.yml").write_text("# Test config")
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    yield registry_path

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


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


def test_registry_command_registration():
    """Test that the registry command is properly registered"""
    from hxc.commands import get_available_commands

    available_commands = get_available_commands()
    assert "registry" in available_commands


def test_registry_command_parser():
    """Test registry command parser registration"""
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers()

    cmd_parser = RegistryCommand.register_subparser(subparsers)

    # Check if the parser was created correctly
    assert cmd_parser is not None


def test_registry_path_get(mock_config):
    """Test getting the registry path"""
    # Set up mock to return a path
    mock_config.get.return_value = "/path/to/registry"

    with patch(
        "hxc.commands.registry.RegistryCommand._validate_registry_path",
        return_value=True,
    ):
        with patch("builtins.print") as mock_print:
            result = main(["registry", "path"])
            assert result == 0
            mock_print.assert_called_once_with("/path/to/registry")


def test_registry_path_get_not_set(mock_config):
    """Test getting the registry path when not set"""
    # Set up mock to return None
    mock_config.get.return_value = None

    with patch("hxc.commands.registry.get_project_root", return_value=None):
        with patch("builtins.print") as mock_print:
            result = main(["registry", "path"])
            assert result == 1
            # First call should be "No registry path is set."
            assert mock_print.call_args_list[0][0][0] == "No registry path is set."


def test_registry_path_set(mock_config, temp_registry):
    """Test setting the registry path"""
    with patch("builtins.print") as mock_print:
        result = main(["registry", "path", "--set", str(temp_registry)])
        assert result == 0
        mock_config.set.assert_called_once_with(
            RegistryCommand.CONFIG_KEY, str(temp_registry)
        )
        assert "set to" in mock_print.call_args[0][0]


def test_registry_list(mock_config):
    """Test listing registries"""
    # Set up mock to return a path
    mock_config.get.return_value = "/path/to/registry"

    with patch(
        "hxc.commands.registry.RegistryCommand._validate_registry_path",
        return_value=True,
    ):
        with patch("builtins.print") as mock_print:
            result = main(["registry", "list"])
            assert result == 0
            assert "Current registry" in mock_print.call_args[0][0]


def test_registry_list_empty(mock_config):
    """Test listing registries when none are set"""
    # Set up mock to return None
    mock_config.get.return_value = None

    with patch("builtins.print") as mock_print:
        result = main(["registry", "list"])
        assert result == 1
        mock_print.assert_called_once_with("No registries configured.")


def test_registry_path_validation(temp_registry):
    """Test registry path validation"""
    # Valid registry
    assert RegistryCommand._validate_registry_path(temp_registry)

    # Invalid path (doesn't exist)
    assert not RegistryCommand._validate_registry_path(temp_registry / "nonexistent")

    # Invalid path (missing required files)
    invalid_dir = temp_registry / "invalid"
    invalid_dir.mkdir()
    assert not RegistryCommand._validate_registry_path(invalid_dir)


def test_init_sets_registry_path(mock_config, tmp_path):
    """Test that init command sets the registry path"""
    registry_path = tmp_path / "new_registry"

    # Use a more comprehensive patch to capture all subprocess calls
    with patch("subprocess.run") as mock_run:
        with patch("builtins.print") as mock_print:
            # We need to also patch the RegistryCommand._validate_registry_path method
            # to prevent validation failures during the test
            with patch(
                "hxc.commands.registry.RegistryCommand._validate_registry_path",
                return_value=True,
            ):
                result = main(["init", str(registry_path)])
                assert result == 0

                # Check that the registry path was set in the config with the correct key
                # This should match the key used in the InitCommand
                mock_config.set.assert_called_with(
                    "registry_path",  # This should match InitCommand.CONFIG_KEY
                    str(registry_path.resolve()),
                )


def test_init_no_set_default(mock_config, tmp_path):
    """Test init with --no-set-default option"""
    registry_path = tmp_path / "new_registry"

    with patch("subprocess.run") as mock_run:
        with patch("builtins.print") as mock_print:
            # Clear any previous calls
            mock_config.set.reset_mock()

            result = main(["init", str(registry_path), "--no-set-default"])
            assert result == 0

            # Check that the registry path was not set
            assert not mock_config.set.called, "Config.set should not have been called"
