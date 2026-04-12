"""
Tests for the registry command.

This module tests the CLI registry command which uses the shared RegistryOperation
for behavioral consistency with MCP tools.
"""

import pathlib
import shutil
import sys
from unittest.mock import MagicMock, patch

import pytest

from hxc.cli import main
from hxc.commands.registry import RegistryCommand
from hxc.core.config import Config
from hxc.core.operations.registry import (
    InvalidRegistryPathError,
    RegistryOperation,
    RegistryOperationError,
)


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
def invalid_registry(tmp_path):
    """Create an invalid registry (missing required components)"""
    registry_path = tmp_path / "invalid_registry"
    registry_path.mkdir(parents=True)
    # Missing config.yml and entity folders
    yield registry_path

    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def mock_config():
    """Mock the Config class"""
    with patch("hxc.commands.registry.Config") as registry_config, patch(
        "hxc.commands.init.Config"
    ) as init_config:
        mock_config = MagicMock()
        registry_config.return_value = mock_config
        init_config.return_value = mock_config
        yield mock_config


@pytest.fixture
def mock_registry_operation():
    """Mock the RegistryOperation class"""
    with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
        mock_instance = MagicMock()
        MockOperation.return_value = mock_instance
        yield mock_instance, MockOperation


class TestRegistryCommandRegistration:
    """Tests for registry command registration"""

    def test_registry_command_registration(self):
        """Test that the registry command is properly registered"""
        from hxc.commands import get_available_commands

        available_commands = get_available_commands()
        assert "registry" in available_commands

    def test_registry_command_parser(self):
        """Test registry command parser registration"""
        from argparse import ArgumentParser

        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        cmd_parser = RegistryCommand.register_subparser(subparsers)

        assert cmd_parser is not None

    def test_registry_command_name(self):
        """Test that registry command has correct name"""
        assert RegistryCommand.name == "registry"

    def test_registry_command_help(self):
        """Test that registry command has help text"""
        assert RegistryCommand.help == "Manage registry locations"

    def test_config_key_matches_operation(self):
        """Test that CONFIG_KEY matches RegistryOperation.CONFIG_KEY"""
        assert RegistryCommand.CONFIG_KEY == RegistryOperation.CONFIG_KEY
        assert RegistryCommand.CONFIG_KEY == "registry_path"


class TestRegistryPathGet:
    """Tests for getting registry path"""

    def test_registry_path_get_valid(self, mock_registry_operation, temp_registry):
        """Test getting a valid registry path"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.get_registry_path.return_value = {
            "success": True,
            "path": str(temp_registry),
            "is_valid": True,
            "source": "config",
            "discovered_path": None,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "path"])

        assert result == 0
        mock_print.assert_called_once_with(str(temp_registry))

    def test_registry_path_get_not_set(self, mock_registry_operation):
        """Test getting the registry path when not set"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.get_registry_path.return_value = {
            "success": False,
            "path": None,
            "is_valid": False,
            "source": "none",
            "discovered_path": None,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "path"])

        assert result == 1
        assert mock_print.call_args_list[0][0][0] == "No registry path is set."

    def test_registry_path_get_with_discovery(self, mock_registry_operation, temp_registry):
        """Test getting registry path with auto-discovery suggestion"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.get_registry_path.return_value = {
            "success": False,
            "path": None,
            "is_valid": False,
            "source": "none",
            "discovered_path": str(temp_registry),
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "path"])

        assert result == 1
        # Should mention the discovered path
        printed_lines = [call[0][0] for call in mock_print.call_args_list]
        assert any("Found registry at" in line for line in printed_lines)

    def test_registry_path_get_invalid_configured(self, mock_registry_operation, tmp_path):
        """Test getting registry path when configured path is invalid"""
        mock_instance, MockOperation = mock_registry_operation
        invalid_path = str(tmp_path / "invalid")

        # When success=True and path is set but is_valid=False, the warning is printed
        mock_instance.get_registry_path.return_value = {
            "success": True,
            "path": invalid_path,
            "is_valid": False,
            "source": "config",
            "discovered_path": None,
            "validation_errors": ["config.yml", "programs/"],
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "path"])

        assert result == 1
        printed_lines = [call[0][0] for call in mock_print.call_args_list]
        # Check for "Warning" which is part of "Warning: Configured registry path is invalid"
        assert any("Warning" in line or "invalid" in line.lower() for line in printed_lines)

    def test_registry_path_default_subcommand(self, mock_registry_operation, temp_registry):
        """Test that no subcommand defaults to 'path'"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.get_registry_path.return_value = {
            "success": True,
            "path": str(temp_registry),
            "is_valid": True,
            "source": "config",
            "discovered_path": None,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry"])

        assert result == 0
        mock_print.assert_called_once_with(str(temp_registry))


class TestRegistryPathSet:
    """Tests for setting registry path"""

    def test_registry_path_set(self, mock_registry_operation, temp_registry):
        """Test setting the registry path"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.set_registry_path.return_value = {
            "success": True,
            "path": str(temp_registry),
            "previous_path": None,
            "is_valid": True,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "path", "--set", str(temp_registry)])

        assert result == 0
        mock_instance.set_registry_path.assert_called_once()
        call_kwargs = mock_instance.set_registry_path.call_args
        assert call_kwargs[1]["validate"] is True
        assert "set to" in mock_print.call_args[0][0].lower()

    def test_registry_path_set_invalid(self, mock_registry_operation, tmp_path):
        """Test setting an invalid registry path"""
        mock_instance, MockOperation = mock_registry_operation
        invalid_path = str(tmp_path / "invalid")

        mock_instance.set_registry_path.side_effect = InvalidRegistryPathError(
            invalid_path, ["config.yml", "programs/"]
        )

        with patch("builtins.print") as mock_print:
            result = main(["registry", "path", "--set", invalid_path])

        assert result == 1
        printed_lines = [call[0][0] for call in mock_print.call_args_list]
        assert any("Invalid registry path" in line for line in printed_lines)

    def test_registry_path_set_resolves_path(self, mock_registry_operation, temp_registry):
        """Test that set path is resolved to absolute"""
        mock_instance, MockOperation = mock_registry_operation

        resolved_path = str(temp_registry.resolve())
        mock_instance.set_registry_path.return_value = {
            "success": True,
            "path": resolved_path,
            "previous_path": None,
            "is_valid": True,
        }

        with patch("builtins.print"):
            result = main(["registry", "path", "--set", str(temp_registry)])

        assert result == 0

    def test_registry_path_set_error_handling(self, mock_registry_operation, temp_registry):
        """Test error handling when setting registry path"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.set_registry_path.side_effect = RegistryOperationError(
            "Failed to save config"
        )

        with patch("builtins.print") as mock_print:
            result = main(["registry", "path", "--set", str(temp_registry)])

        assert result == 1
        printed_lines = [call[0][0] for call in mock_print.call_args_list]
        assert any("Error" in line for line in printed_lines)


class TestRegistryList:
    """Tests for listing registries"""

    def test_registry_list(self, mock_registry_operation, temp_registry):
        """Test listing registries"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.list_registries.return_value = {
            "success": True,
            "registries": [
                {
                    "path": str(temp_registry),
                    "is_current": True,
                    "is_valid": True,
                    "name": "default",
                    "source": "config",
                }
            ],
            "count": 1,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "list"])

        assert result == 0
        printed_lines = [call[0][0] for call in mock_print.call_args_list]
        assert any("Current registry" in line for line in printed_lines)

    def test_registry_list_empty(self, mock_registry_operation):
        """Test listing registries when none are set"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.list_registries.return_value = {
            "success": True,
            "registries": [],
            "count": 0,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "list"])

        assert result == 1
        mock_print.assert_called_once_with("No registries configured.")

    def test_registry_list_multiple(self, mock_registry_operation, temp_registry, tmp_path):
        """Test listing multiple registries"""
        mock_instance, MockOperation = mock_registry_operation
        other_registry = tmp_path / "other_registry"

        mock_instance.list_registries.return_value = {
            "success": True,
            "registries": [
                {
                    "path": str(temp_registry),
                    "is_current": True,
                    "is_valid": True,
                    "name": "default",
                    "source": "config",
                },
                {
                    "path": str(other_registry),
                    "is_current": False,
                    "is_valid": True,
                    "name": "discovered",
                    "source": "discovered",
                },
            ],
            "count": 2,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "list"])

        assert result == 0
        # Should print info about both registries
        assert mock_print.call_count >= 2

    def test_registry_list_shows_invalid_status(self, mock_registry_operation, tmp_path):
        """Test that list shows invalid status for misconfigured registries"""
        mock_instance, MockOperation = mock_registry_operation
        invalid_path = str(tmp_path / "invalid")

        mock_instance.list_registries.return_value = {
            "success": True,
            "registries": [
                {
                    "path": invalid_path,
                    "is_current": True,
                    "is_valid": False,
                    "name": "default",
                    "source": "config",
                }
            ],
            "count": 1,
        }

        with patch("builtins.print") as mock_print:
            result = main(["registry", "list"])

        assert result == 0
        printed_lines = [call[0][0] for call in mock_print.call_args_list]
        # Should show invalid status indicator
        assert any("✗" in line for line in printed_lines)


class TestRegistryPathValidation:
    """Tests for registry path validation"""

    def test_validate_valid_registry(self, temp_registry):
        """Test validation of a valid registry"""
        assert RegistryCommand._validate_registry_path(temp_registry)

    def test_validate_nonexistent_path(self, tmp_path):
        """Test validation of non-existent path"""
        nonexistent = tmp_path / "nonexistent"
        assert not RegistryCommand._validate_registry_path(nonexistent)

    def test_validate_missing_config(self, tmp_path):
        """Test validation with missing config.yml"""
        registry = tmp_path / "missing_config"
        registry.mkdir()
        (registry / "programs").mkdir()
        (registry / "projects").mkdir()
        (registry / "missions").mkdir()
        (registry / "actions").mkdir()
        # Missing config.yml

        assert not RegistryCommand._validate_registry_path(registry)

    def test_validate_missing_folders(self, tmp_path):
        """Test validation with missing entity folders"""
        registry = tmp_path / "missing_folders"
        registry.mkdir()
        (registry / "config.yml").write_text("# Config")
        (registry / "programs").mkdir()
        # Missing: projects, missions, actions

        assert not RegistryCommand._validate_registry_path(registry)

    def test_validate_uses_registry_operation(self):
        """Test that _validate_registry_path uses RegistryOperation"""
        with patch.object(
            RegistryOperation, "validate_registry_path"
        ) as mock_validate:
            mock_validate.return_value = {"valid": True, "path": "/test", "missing": []}

            result = RegistryCommand._validate_registry_path(pathlib.Path("/test"))

            mock_validate.assert_called_once()
            assert result is True

    def test_validate_returns_false_on_invalid(self):
        """Test that _validate_registry_path returns False for invalid paths"""
        with patch.object(
            RegistryOperation, "validate_registry_path"
        ) as mock_validate:
            mock_validate.return_value = {
                "valid": False,
                "path": "/test",
                "missing": ["config.yml"],
            }

            result = RegistryCommand._validate_registry_path(pathlib.Path("/test"))

            assert result is False


class TestRegistryGetRegistryPath:
    """Tests for RegistryCommand.get_registry_path() convenience method"""

    def test_get_registry_path_returns_valid_path(self):
        """Test that get_registry_path returns path when valid"""
        with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": True,
                "path": "/valid/registry",
                "is_valid": True,
                "source": "config",
            }
            MockOperation.return_value = mock_instance

            result = RegistryCommand.get_registry_path()

            assert result == "/valid/registry"

    def test_get_registry_path_returns_none_when_not_set(self):
        """Test that get_registry_path returns None when not configured"""
        with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": False,
                "path": None,
                "is_valid": False,
                "source": "none",
            }
            MockOperation.return_value = mock_instance

            result = RegistryCommand.get_registry_path()

            assert result is None

    def test_get_registry_path_returns_none_when_invalid(self):
        """Test that get_registry_path returns None when path is invalid"""
        with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": False,
                "path": "/invalid/path",
                "is_valid": False,
                "source": "config",
            }
            MockOperation.return_value = mock_instance

            result = RegistryCommand.get_registry_path()

            assert result is None

    def test_get_registry_path_does_not_use_discovery(self):
        """Test that get_registry_path does not use auto-discovery"""
        with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": False,
                "path": None,
                "is_valid": False,
                "source": "none",
            }
            MockOperation.return_value = mock_instance

            RegistryCommand.get_registry_path()

            mock_instance.get_registry_path.assert_called_once_with(
                include_discovery=False
            )


class TestInitSetsRegistryPath:
    """Tests for init command setting registry path"""

    def test_init_sets_registry_path(self, mock_config, tmp_path):
        """Test that init command sets the registry path"""
        registry_path = tmp_path / "new_registry"

        with patch("subprocess.run") as mock_run:
            with patch("builtins.print"):
                with patch(
                    "hxc.commands.registry.RegistryCommand._validate_registry_path",
                    return_value=True,
                ):
                    result = main(["init", str(registry_path)])

        assert result == 0
        mock_config.set.assert_called_with(
            "registry_path",
            str(registry_path.resolve()),
        )

    def test_init_no_set_default(self, mock_config, tmp_path):
        """Test init with --no-set-default option"""
        registry_path = tmp_path / "new_registry"

        with patch("subprocess.run"):
            with patch("builtins.print"):
                mock_config.set.reset_mock()
                result = main(["init", str(registry_path), "--no-set-default"])

        assert result == 0
        assert not mock_config.set.called, "Config.set should not have been called"


class TestRegistryCommandUsesSharedOperation:
    """Tests to verify RegistryCommand uses the shared RegistryOperation"""

    def test_handle_path_uses_registry_operation(self, mock_registry_operation):
        """Test that handle_path uses RegistryOperation"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.get_registry_path.return_value = {
            "success": True,
            "path": "/test/registry",
            "is_valid": True,
            "source": "config",
            "discovered_path": None,
        }

        with patch("builtins.print"):
            main(["registry", "path"])

        MockOperation.assert_called_once()
        mock_instance.get_registry_path.assert_called_once()

    def test_handle_path_set_uses_registry_operation(
        self, mock_registry_operation, temp_registry
    ):
        """Test that handle_path with --set uses RegistryOperation"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.set_registry_path.return_value = {
            "success": True,
            "path": str(temp_registry),
            "previous_path": None,
            "is_valid": True,
        }

        with patch("builtins.print"):
            main(["registry", "path", "--set", str(temp_registry)])

        mock_instance.set_registry_path.assert_called_once()

    def test_handle_list_uses_registry_operation(self, mock_registry_operation):
        """Test that handle_list uses RegistryOperation"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.list_registries.return_value = {
            "success": True,
            "registries": [],
            "count": 0,
        }

        with patch("builtins.print"):
            main(["registry", "list"])

        mock_instance.list_registries.assert_called_once()


class TestRegistryCommandBehavioralParityWithMCP:
    """Tests to verify CLI registry command behaves identically to MCP tools"""

    def test_validation_uses_same_required_components(self, tmp_path):
        """Test that validation checks same components as MCP"""
        registry = tmp_path / "test"
        registry.mkdir()

        # Empty directory should fail validation
        result = RegistryOperation.validate_registry_path(str(registry))

        assert result["valid"] is False
        # Should check same components as MCP
        expected_missing = {"config.yml", "programs/", "projects/", "missions/", "actions/"}
        assert set(result["missing"]) == expected_missing

    def test_config_key_is_shared(self):
        """Test that the config key is shared between CLI and operation"""
        assert RegistryCommand.CONFIG_KEY == RegistryOperation.CONFIG_KEY

    def test_get_registry_path_result_structure(self):
        """Test that get_registry_path returns expected structure"""
        with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            # Return structure matching what MCP tools expect
            mock_instance.get_registry_path.return_value = {
                "success": True,
                "path": "/test/path",
                "is_valid": True,
                "source": "config",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            result = RegistryCommand.get_registry_path()

            # CLI method returns just the path (or None)
            assert result == "/test/path"

    def test_set_registry_path_validates_by_default(
        self, mock_registry_operation, temp_registry
    ):
        """Test that set_registry_path validates by default (like MCP)"""
        mock_instance, MockOperation = mock_registry_operation

        mock_instance.set_registry_path.return_value = {
            "success": True,
            "path": str(temp_registry),
            "previous_path": None,
            "is_valid": True,
        }

        with patch("builtins.print"):
            main(["registry", "path", "--set", str(temp_registry)])

        call_kwargs = mock_instance.set_registry_path.call_args
        assert call_kwargs[1]["validate"] is True


class TestRegistryCommandEdgeCases:
    """Tests for edge cases in registry command"""

    def test_unknown_subcommand(self, mock_registry_operation, capsys):
        """Test handling of unknown subcommand - argparse exits with code 2"""
        mock_instance, MockOperation = mock_registry_operation

        # argparse raises SystemExit(2) for invalid choices
        with pytest.raises(SystemExit) as exc_info:
            main(["registry", "unknown"])

        assert exc_info.value.code == 2

    def test_path_with_spaces(self, mock_registry_operation, tmp_path):
        """Test handling of paths with spaces"""
        mock_instance, MockOperation = mock_registry_operation
        space_path = tmp_path / "path with spaces"

        mock_instance.set_registry_path.return_value = {
            "success": True,
            "path": str(space_path),
            "previous_path": None,
            "is_valid": True,
        }

        with patch("builtins.print"):
            result = main(["registry", "path", "--set", str(space_path)])

        assert result == 0

    def test_relative_path_is_resolved(self, mock_registry_operation, tmp_path):
        """Test that relative paths are resolved to absolute"""
        mock_instance, MockOperation = mock_registry_operation
        
        # The path gets resolved in the command before calling the operation
        resolved_path = (tmp_path / "relative").resolve()

        mock_instance.set_registry_path.return_value = {
            "success": True,
            "path": str(resolved_path),
            "previous_path": None,
            "is_valid": True,
        }

        with patch("builtins.print"):
            import os
            old_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                result = main(["registry", "path", "--set", "relative"])
            finally:
                os.chdir(old_cwd)

        # Command should have called set_registry_path with resolved path
        call_args = mock_instance.set_registry_path.call_args[0]
        assert pathlib.Path(call_args[0]).is_absolute()


class TestRegistryCommandIntegration:
    """Integration tests for registry command"""

    def test_set_then_get_workflow(self, temp_registry):
        """Test setting a path then getting it"""
        import tempfile
        import shutil

        temp_config_dir = tempfile.mkdtemp()
        try:
            # We need to mock RegistryOperation since that's what the command uses
            with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
                # Create a mock that simulates storing values
                stored_values = {}
                mock_instance = MagicMock()

                def mock_set_registry_path(path, validate=True):
                    stored_values["registry_path"] = path
                    return {
                        "success": True,
                        "path": path,
                        "previous_path": None,
                        "is_valid": True,
                    }

                mock_instance.set_registry_path.side_effect = mock_set_registry_path
                MockOperation.return_value = mock_instance

                with patch("builtins.print"):
                    # Set the path
                    set_result = main(["registry", "path", "--set", str(temp_registry)])
                    assert set_result == 0

                    # Path should be stored
                    assert "registry_path" in stored_values

        finally:
            shutil.rmtree(temp_config_dir)

    def test_list_after_set(self, temp_registry):
        """Test listing after setting a registry"""
        with patch("hxc.commands.registry.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()

            # First call: set_registry_path
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": str(temp_registry),
                "previous_path": None,
                "is_valid": True,
            }

            # Second call: list_registries
            mock_instance.list_registries.return_value = {
                "success": True,
                "registries": [
                    {
                        "path": str(temp_registry),
                        "is_current": True,
                        "is_valid": True,
                        "name": "default",
                        "source": "config",
                    }
                ],
                "count": 1,
            }

            MockOperation.return_value = mock_instance

            with patch("builtins.print"):
                # Set path
                set_result = main(["registry", "path", "--set", str(temp_registry)])
                assert set_result == 0

                # List registries
                list_result = main(["registry", "list"])
                assert list_result == 0

            # Both methods should have been called
            mock_instance.set_registry_path.assert_called_once()
            mock_instance.list_registries.assert_called_once()