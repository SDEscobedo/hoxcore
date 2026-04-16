"""
Tests for registry management tools in MCP Tools.

This module tests the tools that enable managing registry paths and configuration
through the Model Context Protocol:
- get_registry_path_tool
- set_registry_path_tool
- validate_registry_path_tool
- list_registries_tool
- discover_registry_tool
- clear_registry_path_tool
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hxc.core.operations.registry import (
    InvalidRegistryPathError,
    RegistryOperation,
    RegistryOperationError,
)
from hxc.mcp.tools import (
    clear_registry_path_tool,
    discover_registry_tool,
    get_registry_path_tool,
    list_registries_tool,
    set_registry_path_tool,
    validate_registry_path_tool,
)


class TestGetRegistryPathTool:
    """Tests for get_registry_path_tool"""

    def test_get_registry_path_returns_configured_path(
        self, valid_registry_for_path_tests
    ):
        """Test getting a configured registry path"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "is_valid": True,
                "source": "config",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool()

        assert result["success"] is True
        assert result["path"] == valid_registry_for_path_tests
        assert result["is_valid"] is True
        assert result["source"] == "config"

    def test_get_registry_path_no_path_configured(self):
        """Test getting registry path when none is configured"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": False,
                "path": None,
                "is_valid": False,
                "source": "none",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool()

        assert result["success"] is False
        assert result["path"] is None
        assert result["is_valid"] is False
        assert result["source"] == "none"

    def test_get_registry_path_with_discovery(self, valid_registry_for_path_tests):
        """Test getting registry path with auto-discovery"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "is_valid": True,
                "source": "discovered",
                "discovered_path": valid_registry_for_path_tests,
            }
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool(include_discovery=True)

        assert result["success"] is True
        assert result["source"] == "discovered"
        assert result["discovered_path"] == valid_registry_for_path_tests

    def test_get_registry_path_without_discovery(self):
        """Test getting registry path without auto-discovery"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": False,
                "path": None,
                "is_valid": False,
                "source": "none",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool(include_discovery=False)

        mock_instance.get_registry_path.assert_called_once_with(include_discovery=False)

    def test_get_registry_path_invalid_configured(self, invalid_registry_path):
        """Test getting registry path when configured path is invalid"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": False,
                "path": invalid_registry_path,
                "is_valid": False,
                "source": "config",
                "discovered_path": None,
                "validation_errors": ["config.yml", "programs/"],
            }
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool()

        assert result["success"] is False
        assert result["path"] == invalid_registry_path
        assert result["is_valid"] is False
        assert "validation_errors" in result
        assert len(result["validation_errors"]) > 0

    def test_get_registry_path_handles_exception(self):
        """Test that exceptions are handled gracefully"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.side_effect = RegistryOperationError(
                "Config error"
            )
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool()

        assert result["success"] is False
        assert "Config error" in result["error"]

    def test_get_registry_path_result_structure(self):
        """Test that result has expected structure"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": True,
                "path": "/test/path",
                "is_valid": True,
                "source": "config",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool()

        # Check all expected keys
        expected_keys = {"success", "path", "is_valid", "source", "discovered_path"}
        assert set(result.keys()) >= expected_keys


class TestSetRegistryPathTool:
    """Tests for set_registry_path_tool"""

    def test_set_registry_path_valid(self, valid_registry_for_path_tests):
        """Test setting a valid registry path"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            result = set_registry_path_tool(path=valid_registry_for_path_tests)

        assert result["success"] is True
        assert result["path"] == valid_registry_for_path_tests
        assert result["is_valid"] is True

    def test_set_registry_path_replaces_previous(self, valid_registry_for_path_tests):
        """Test that setting path returns previous path"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": "/old/path",
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            result = set_registry_path_tool(path=valid_registry_for_path_tests)

        assert result["success"] is True
        assert result["previous_path"] == "/old/path"

    def test_set_registry_path_invalid_raises_error(self, invalid_registry_path):
        """Test that setting an invalid path returns error"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.side_effect = InvalidRegistryPathError(
                invalid_registry_path, ["config.yml", "programs/"]
            )
            MockOperation.return_value = mock_instance

            result = set_registry_path_tool(path=invalid_registry_path, validate=True)

        assert result["success"] is False
        assert invalid_registry_path in result["path"]
        assert "missing_components" in result
        assert len(result["missing_components"]) > 0

    def test_set_registry_path_without_validation(self, invalid_registry_path):
        """Test setting path without validation"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": invalid_registry_path,
                "previous_path": None,
                "is_valid": True,  # Not actually validated
            }
            MockOperation.return_value = mock_instance

            result = set_registry_path_tool(path=invalid_registry_path, validate=False)

        # Should succeed (not validated)
        mock_instance.set_registry_path.assert_called_once_with(
            path=invalid_registry_path, validate=False
        )

    def test_set_registry_path_empty_path_fails(self):
        """Test that empty path returns error"""
        result = set_registry_path_tool(path="")

        assert result["success"] is False
        assert "Path is required" in result["error"]

    def test_set_registry_path_result_structure(self, valid_registry_for_path_tests):
        """Test that result has expected structure"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            result = set_registry_path_tool(path=valid_registry_for_path_tests)

        # Check all expected keys
        expected_keys = {"success", "path", "previous_path", "is_valid"}
        assert set(result.keys()) == expected_keys

    def test_set_registry_path_handles_operation_error(self):
        """Test that RegistryOperationError is handled"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.side_effect = RegistryOperationError(
                "Failed to save config"
            )
            MockOperation.return_value = mock_instance

            result = set_registry_path_tool(path="/some/path")

        assert result["success"] is False
        assert "Failed to save config" in result["error"]


class TestValidateRegistryPathTool:
    """Tests for validate_registry_path_tool"""

    def test_validate_valid_registry(self, valid_registry_for_path_tests):
        """Test validating a valid registry path"""
        result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        assert result["success"] is True
        assert result["valid"] is True
        assert result["missing"] == []

    def test_validate_invalid_registry(self, invalid_registry_path):
        """Test validating an invalid registry path"""
        result = validate_registry_path_tool(path=invalid_registry_path)

        assert result["success"] is True  # Validation completed
        assert result["valid"] is False
        assert len(result["missing"]) > 0

    def test_validate_nonexistent_path(self):
        """Test validating a non-existent path"""
        result = validate_registry_path_tool(path="/nonexistent/path/xyz")

        assert result["success"] is True
        assert result["valid"] is False
        assert "path does not exist" in result["missing"]

    def test_validate_empty_path(self):
        """Test validating empty path"""
        result = validate_registry_path_tool(path="")

        assert result["success"] is True
        assert result["valid"] is False
        assert "path is required" in result["missing"]

    def test_validate_path_resolves_to_absolute(self, valid_registry_for_path_tests):
        """Test that validation resolves path to absolute"""
        result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        assert result["success"] is True
        assert Path(result["path"]).is_absolute()

    def test_validate_result_structure(self, valid_registry_for_path_tests):
        """Test that result has expected structure"""
        result = validate_registry_path_tool(path=valid_registry_for_path_tests)

        expected_keys = {"success", "valid", "path", "missing"}
        assert set(result.keys()) == expected_keys

    def test_validate_missing_folders(self):
        """Test that missing folders are listed"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create only some folders
            Path(temp_dir, "programs").mkdir()
            Path(temp_dir, "config.yml").write_text("# Config")

            result = validate_registry_path_tool(path=temp_dir)

            assert result["success"] is True
            assert result["valid"] is False
            # Should list missing folders
            assert "projects/" in result["missing"]
            assert "missions/" in result["missing"]
            assert "actions/" in result["missing"]
        finally:
            shutil.rmtree(temp_dir)

    def test_validate_missing_config(self):
        """Test that missing config.yml is listed"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create all folders but no config
            for folder in ["programs", "projects", "missions", "actions"]:
                Path(temp_dir, folder).mkdir()

            result = validate_registry_path_tool(path=temp_dir)

            assert result["success"] is True
            assert result["valid"] is False
            assert "config.yml" in result["missing"]
        finally:
            shutil.rmtree(temp_dir)


class TestListRegistriesTool:
    """Tests for list_registries_tool"""

    def test_list_single_registry(self, valid_registry_for_path_tests):
        """Test listing when one registry is configured"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_registries.return_value = {
                "success": True,
                "registries": [
                    {
                        "path": valid_registry_for_path_tests,
                        "is_current": True,
                        "is_valid": True,
                        "name": "default",
                        "source": "config",
                    }
                ],
                "count": 1,
            }
            MockOperation.return_value = mock_instance

            result = list_registries_tool()

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["registries"]) == 1
        assert result["registries"][0]["is_current"] is True

    def test_list_no_registries(self):
        """Test listing when no registries are configured"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_registries.return_value = {
                "success": True,
                "registries": [],
                "count": 0,
            }
            MockOperation.return_value = mock_instance

            result = list_registries_tool()

        assert result["success"] is True
        assert result["count"] == 0
        assert result["registries"] == []

    def test_list_multiple_registries(self, valid_registry_for_path_tests):
        """Test listing multiple registries"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_registries.return_value = {
                "success": True,
                "registries": [
                    {
                        "path": valid_registry_for_path_tests,
                        "is_current": True,
                        "is_valid": True,
                        "name": "default",
                        "source": "config",
                    },
                    {
                        "path": "/other/registry",
                        "is_current": False,
                        "is_valid": True,
                        "name": "discovered",
                        "source": "discovered",
                    },
                ],
                "count": 2,
            }
            MockOperation.return_value = mock_instance

            result = list_registries_tool()

        assert result["success"] is True
        assert result["count"] == 2

        # Find current registry
        current = next(r for r in result["registries"] if r["is_current"])
        assert current["path"] == valid_registry_for_path_tests

    def test_list_registries_result_structure(self):
        """Test that result has expected structure"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_registries.return_value = {
                "success": True,
                "registries": [
                    {
                        "path": "/test",
                        "is_current": True,
                        "is_valid": True,
                        "name": "default",
                        "source": "config",
                    }
                ],
                "count": 1,
            }
            MockOperation.return_value = mock_instance

            result = list_registries_tool()

        expected_keys = {"success", "registries", "count"}
        assert set(result.keys()) == expected_keys

        # Check registry object structure
        registry = result["registries"][0]
        expected_registry_keys = {"path", "is_current", "is_valid", "name", "source"}
        assert set(registry.keys()) == expected_registry_keys

    def test_list_registries_handles_error(self):
        """Test that errors are handled"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_registries.side_effect = RegistryOperationError(
                "Config error"
            )
            MockOperation.return_value = mock_instance

            result = list_registries_tool()

        assert result["success"] is False
        assert "Config error" in result["error"]


class TestDiscoverRegistryTool:
    """Tests for discover_registry_tool"""

    def test_discover_finds_registry(self, valid_registry_for_path_tests):
        """Test that discover finds a valid registry"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.discover_registry.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            result = discover_registry_tool()

        assert result["success"] is True
        assert result["path"] == valid_registry_for_path_tests
        assert result["is_valid"] is True

    def test_discover_no_registry_found(self):
        """Test discovery when no registry exists"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.discover_registry.return_value = {
                "success": False,
                "path": None,
                "is_valid": False,
            }
            MockOperation.return_value = mock_instance

            result = discover_registry_tool()

        assert result["success"] is False
        assert result["path"] is None
        assert result["is_valid"] is False

    def test_discover_validates_found_path(self, invalid_registry_path):
        """Test that discovered path is validated"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.discover_registry.return_value = {
                "success": True,
                "path": invalid_registry_path,
                "is_valid": False,
            }
            MockOperation.return_value = mock_instance

            result = discover_registry_tool()

        assert result["success"] is True  # Found something
        assert result["path"] == invalid_registry_path
        assert result["is_valid"] is False  # But it's not valid

    def test_discover_result_structure(self):
        """Test that result has expected structure"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.discover_registry.return_value = {
                "success": True,
                "path": "/test",
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            result = discover_registry_tool()

        expected_keys = {"success", "path", "is_valid"}
        assert set(result.keys()) == expected_keys

    def test_discover_handles_error(self):
        """Test that errors are handled"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.discover_registry.side_effect = RegistryOperationError(
                "Discovery failed"
            )
            MockOperation.return_value = mock_instance

            result = discover_registry_tool()

        assert result["success"] is False
        assert "Discovery failed" in result["error"]


class TestClearRegistryPathTool:
    """Tests for clear_registry_path_tool"""

    def test_clear_path(self):
        """Test clearing the configured registry path"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.clear_registry_path.return_value = {
                "success": True,
                "previous_path": "/some/path",
            }
            MockOperation.return_value = mock_instance

            result = clear_registry_path_tool()

        assert result["success"] is True
        assert result["previous_path"] == "/some/path"

    def test_clear_path_when_not_set(self):
        """Test clearing when no path is set"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.clear_registry_path.return_value = {
                "success": True,
                "previous_path": None,
            }
            MockOperation.return_value = mock_instance

            result = clear_registry_path_tool()

        assert result["success"] is True
        assert result["previous_path"] is None

    def test_clear_result_structure(self):
        """Test that result has expected structure"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.clear_registry_path.return_value = {
                "success": True,
                "previous_path": "/old/path",
            }
            MockOperation.return_value = mock_instance

            result = clear_registry_path_tool()

        expected_keys = {"success", "previous_path"}
        assert set(result.keys()) == expected_keys

    def test_clear_handles_error(self):
        """Test that errors are handled"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.clear_registry_path.side_effect = RegistryOperationError(
                "Clear failed"
            )
            MockOperation.return_value = mock_instance

            result = clear_registry_path_tool()

        assert result["success"] is False
        assert "Clear failed" in result["error"]


class TestRegistryToolsReadOnlyMode:
    """Tests for registry tools in read-only server mode"""

    def test_read_only_server_includes_read_tools(self, temp_registry):
        """Test that read-only server includes read registry tools"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        # Read tools should be available
        assert "get_registry_path" in tools
        assert "validate_registry_path" in tools
        assert "list_registries" in tools
        assert "discover_registry" in tools

    def test_read_only_server_excludes_write_tools(self, temp_registry):
        """Test that read-only server excludes write registry tools"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        # Write tools should NOT be available
        assert "set_registry_path" not in tools
        assert "clear_registry_path" not in tools

    def test_read_write_server_includes_all_tools(self, temp_registry):
        """Test that read-write server includes all registry tools"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=False)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        # All tools should be available
        assert "get_registry_path" in tools
        assert "set_registry_path" in tools
        assert "validate_registry_path" in tools
        assert "list_registries" in tools
        assert "discover_registry" in tools
        assert "clear_registry_path" in tools

    def test_read_only_rejects_set_registry_path(self, temp_registry):
        """Test that calling set_registry_path on read-only server returns error"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "set_registry_path",
                "arguments": {"path": "/some/path"},
            },
        }

        response = server.handle_request(request)
        assert "error" in response

    def test_read_only_rejects_clear_registry_path(self, temp_registry):
        """Test that calling clear_registry_path on read-only server returns error"""
        from hxc.mcp.server import create_server

        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "clear_registry_path",
                "arguments": {},
            },
        }

        response = server.handle_request(request)
        assert "error" in response


class TestRegistryToolsIntegration:
    """Integration tests for registry management tools"""

    def test_validate_then_set(self, valid_registry_for_path_tests):
        """Test validating a path then setting it"""
        # First validate
        validate_result = validate_registry_path_tool(
            path=valid_registry_for_path_tests
        )
        assert validate_result["success"] is True
        assert validate_result["valid"] is True

        # Then set (with mock to avoid persisting)
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            set_result = set_registry_path_tool(path=valid_registry_for_path_tests)

        assert set_result["success"] is True
        assert set_result["path"] == valid_registry_for_path_tests

    def test_set_then_get(self, valid_registry_for_path_tests):
        """Test setting a path then getting it"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            mock_instance.get_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "is_valid": True,
                "source": "config",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            # Set
            set_result = set_registry_path_tool(path=valid_registry_for_path_tests)
            assert set_result["success"] is True

            # Get
            get_result = get_registry_path_tool()
            assert get_result["success"] is True
            assert get_result["path"] == valid_registry_for_path_tests

    def test_set_then_list(self, valid_registry_for_path_tests):
        """Test setting a path then listing registries"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            mock_instance.list_registries.return_value = {
                "success": True,
                "registries": [
                    {
                        "path": valid_registry_for_path_tests,
                        "is_current": True,
                        "is_valid": True,
                        "name": "default",
                        "source": "config",
                    }
                ],
                "count": 1,
            }
            MockOperation.return_value = mock_instance

            # Set
            set_result = set_registry_path_tool(path=valid_registry_for_path_tests)
            assert set_result["success"] is True

            # List
            list_result = list_registries_tool()
            assert list_result["success"] is True
            assert list_result["count"] == 1
            assert list_result["registries"][0]["path"] == valid_registry_for_path_tests

    def test_set_then_clear_then_get(self, valid_registry_for_path_tests):
        """Test setting, clearing, then getting path"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            mock_instance.clear_registry_path.return_value = {
                "success": True,
                "previous_path": valid_registry_for_path_tests,
            }
            mock_instance.get_registry_path.return_value = {
                "success": False,
                "path": None,
                "is_valid": False,
                "source": "none",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            # Set
            set_result = set_registry_path_tool(path=valid_registry_for_path_tests)
            assert set_result["success"] is True

            # Clear
            clear_result = clear_registry_path_tool()
            assert clear_result["success"] is True
            assert clear_result["previous_path"] == valid_registry_for_path_tests

            # Get (should be empty)
            get_result = get_registry_path_tool()
            assert get_result["success"] is False
            assert get_result["path"] is None

    def test_discover_then_set(self, valid_registry_for_path_tests):
        """Test discovering a registry then setting it as default"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.discover_registry.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "is_valid": True,
            }
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            # Discover
            discover_result = discover_registry_tool()
            assert discover_result["success"] is True
            discovered_path = discover_result["path"]

            # Set discovered path
            set_result = set_registry_path_tool(path=discovered_path)
            assert set_result["success"] is True
            assert set_result["path"] == discovered_path


class TestRegistryToolsBehavioralParityWithCLI:
    """Tests to verify registry tools behave identically to CLI"""

    def test_validation_checks_same_components(self):
        """Test that validation checks the same components as CLI"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Empty directory
            result = validate_registry_path_tool(path=temp_dir)

            assert result["success"] is True
            assert result["valid"] is False

            # Should check same components as CLI
            expected_missing = {
                "config.yml",
                "programs/",
                "projects/",
                "missions/",
                "actions/",
            }
            assert set(result["missing"]) == expected_missing
        finally:
            shutil.rmtree(temp_dir)

    def test_config_key_matches_cli(self):
        """Test that the config key matches CLI"""
        # Both should use "registry_path" key
        assert RegistryOperation.CONFIG_KEY == "registry_path"

    def test_required_folders_match_cli(self):
        """Test that required folders match CLI expectations"""
        expected = ["programs", "projects", "missions", "actions"]
        assert RegistryOperation.REQUIRED_FOLDERS == expected

    def test_required_files_match_cli(self):
        """Test that required files match CLI expectations"""
        expected = ["config.yml"]
        assert RegistryOperation.REQUIRED_FILES == expected

    def test_get_registry_path_structure_matches_cli(
        self, valid_registry_for_path_tests
    ):
        """Test that get_registry_path result structure matches CLI expectations"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.get_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "is_valid": True,
                "source": "config",
                "discovered_path": None,
            }
            MockOperation.return_value = mock_instance

            result = get_registry_path_tool()

        # Same keys as what CLI needs
        assert "success" in result
        assert "path" in result
        assert "is_valid" in result
        assert "source" in result

    def test_set_registry_path_structure_matches_cli(
        self, valid_registry_for_path_tests
    ):
        """Test that set_registry_path result structure matches CLI expectations"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.set_registry_path.return_value = {
                "success": True,
                "path": valid_registry_for_path_tests,
                "previous_path": None,
                "is_valid": True,
            }
            MockOperation.return_value = mock_instance

            result = set_registry_path_tool(path=valid_registry_for_path_tests)

        # Same keys as what CLI returns
        assert "success" in result
        assert "path" in result
        assert "previous_path" in result
        assert "is_valid" in result

    def test_list_registries_structure_matches_cli(self):
        """Test that list_registries result structure matches CLI expectations"""
        with patch("hxc.mcp.tools.RegistryOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_registries.return_value = {
                "success": True,
                "registries": [
                    {
                        "path": "/test",
                        "is_current": True,
                        "is_valid": True,
                        "name": "default",
                        "source": "config",
                    }
                ],
                "count": 1,
            }
            MockOperation.return_value = mock_instance

            result = list_registries_tool()

        # Same structure as CLI list output
        assert "registries" in result
        assert "count" in result

        registry = result["registries"][0]
        assert "path" in registry
        assert "is_current" in registry
        assert "is_valid" in registry
