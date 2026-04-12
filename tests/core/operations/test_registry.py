"""
Tests for Registry Operation implementation.

This module tests the shared registry management operation that ensures
behavioral consistency between CLI commands and MCP tools.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from hxc.core.config import Config
from hxc.core.operations.registry import (
    InvalidRegistryPathError,
    RegistryNotFoundError,
    RegistryOperation,
    RegistryOperationError,
)


def _resolve_path(path: str) -> str:
    """Resolve a path to its real absolute path (follows symlinks, resolves short names)"""
    return str(Path(path).resolve())


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    # Resolve to handle macOS /var -> /private/var symlinks
    # and Windows 8.3 short names
    resolved_path = _resolve_path(temp_dir)
    yield resolved_path
    if Path(resolved_path).exists():
        shutil.rmtree(resolved_path)


@pytest.fixture
def valid_registry(temp_dir):
    """Create a valid registry structure"""
    registry_path = Path(temp_dir)

    # Create required folders
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    (registry_path / "config.yml").write_text("# HoxCore Registry Config\n")

    # Create marker directory
    (registry_path / ".hxc").mkdir()

    return str(registry_path)


@pytest.fixture
def invalid_registry_missing_folders(temp_dir):
    """Create an invalid registry missing some folders"""
    registry_path = Path(temp_dir)

    # Only create some folders
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    # Missing: missions, actions

    # Create config file
    (registry_path / "config.yml").write_text("# HoxCore Registry Config\n")

    return str(registry_path)


@pytest.fixture
def invalid_registry_missing_config(temp_dir):
    """Create an invalid registry missing config.yml"""
    registry_path = Path(temp_dir)

    # Create all folders
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # No config.yml

    return str(registry_path)


@pytest.fixture
def mock_config():
    """Create a mock Config instance"""
    mock = MagicMock(spec=Config)
    mock.load.return_value = {}
    return mock


class TestRegistryOperationValidation:
    """Tests for registry path validation"""

    def test_validate_valid_registry(self, valid_registry):
        """Test validation passes for a valid registry"""
        result = RegistryOperation.validate_registry_path(valid_registry)

        assert result["valid"] is True
        assert result["path"] == valid_registry
        assert result["missing"] == []

    def test_validate_nonexistent_path(self):
        """Test validation fails for non-existent path"""
        result = RegistryOperation.validate_registry_path("/nonexistent/path/xyz")

        assert result["valid"] is False
        assert "path does not exist" in result["missing"]

    def test_validate_file_not_directory(self, temp_dir):
        """Test validation fails for a file instead of directory"""
        file_path = Path(temp_dir) / "not_a_directory.txt"
        file_path.write_text("I am a file")

        result = RegistryOperation.validate_registry_path(str(file_path))

        assert result["valid"] is False
        assert "path is not a directory" in result["missing"]

    def test_validate_missing_folders(self, invalid_registry_missing_folders):
        """Test validation reports missing folders"""
        result = RegistryOperation.validate_registry_path(
            invalid_registry_missing_folders
        )

        assert result["valid"] is False
        assert "missions/" in result["missing"]
        assert "actions/" in result["missing"]
        assert "programs/" not in result["missing"]
        assert "projects/" not in result["missing"]

    def test_validate_missing_config(self, invalid_registry_missing_config):
        """Test validation reports missing config.yml"""
        result = RegistryOperation.validate_registry_path(
            invalid_registry_missing_config
        )

        assert result["valid"] is False
        assert "config.yml" in result["missing"]

    def test_validate_empty_directory(self, temp_dir):
        """Test validation fails for empty directory"""
        result = RegistryOperation.validate_registry_path(temp_dir)

        assert result["valid"] is False
        # Should be missing all required components
        assert "config.yml" in result["missing"]
        assert "programs/" in result["missing"]
        assert "projects/" in result["missing"]
        assert "missions/" in result["missing"]
        assert "actions/" in result["missing"]

    def test_validate_resolves_to_absolute_path(self, valid_registry):
        """Test that validation resolves paths to absolute"""
        result = RegistryOperation.validate_registry_path(valid_registry)

        assert result["valid"] is True
        assert Path(result["path"]).is_absolute()

    def test_validate_with_path_object(self, valid_registry):
        """Test validation works with Path object"""
        result = RegistryOperation.validate_registry_path(Path(valid_registry))

        assert result["valid"] is True

    def test_required_folders_constant(self):
        """Test that REQUIRED_FOLDERS contains expected values"""
        expected = ["programs", "projects", "missions", "actions"]
        assert RegistryOperation.REQUIRED_FOLDERS == expected

    def test_required_files_constant(self):
        """Test that REQUIRED_FILES contains expected values"""
        expected = ["config.yml"]
        assert RegistryOperation.REQUIRED_FILES == expected


class TestRegistryOperationGetPath:
    """Tests for getting registry path"""

    def test_get_path_from_config(self, valid_registry):
        """Test getting path from configuration"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = valid_registry

        operation = RegistryOperation(config=mock_config)
        result = operation.get_registry_path(include_discovery=False)

        assert result["success"] is True
        assert result["path"] == valid_registry
        assert result["is_valid"] is True
        assert result["source"] == "config"
        assert result["discovered_path"] is None

    def test_get_path_not_configured(self):
        """Test getting path when not configured"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.get_registry_path(include_discovery=False)

        assert result["success"] is False
        assert result["path"] is None
        assert result["is_valid"] is False
        assert result["source"] == "none"

    def test_get_path_configured_but_invalid(self, temp_dir):
        """Test getting path when configured path is invalid"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = temp_dir  # Empty dir, not a valid registry

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.get_registry_path(include_discovery=True)

        assert result["success"] is False
        assert result["path"] == temp_dir
        assert result["is_valid"] is False
        assert result["source"] == "config"
        assert "validation_errors" in result
        assert len(result["validation_errors"]) > 0

    def test_get_path_with_discovery_finds_registry(self, valid_registry):
        """Test that discovery finds a registry when not configured"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        with patch(
            "hxc.core.operations.registry.get_project_root",
            return_value=valid_registry,
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.get_registry_path(include_discovery=True)

        assert result["success"] is True
        assert result["path"] == valid_registry
        assert result["is_valid"] is True
        assert result["source"] == "discovered"
        assert result["discovered_path"] == valid_registry

    def test_get_path_invalid_config_with_discovery(self, valid_registry):
        """Test that discovery is suggested when configured path is invalid"""
        # Create a separate invalid directory (not the same as valid_registry)
        invalid_temp_dir = _resolve_path(tempfile.mkdtemp())
        try:
            mock_config = MagicMock(spec=Config)
            mock_config.get.return_value = invalid_temp_dir  # Invalid (empty dir)

            with patch(
                "hxc.core.operations.registry.get_project_root",
                return_value=valid_registry,
            ):
                operation = RegistryOperation(config=mock_config)
                result = operation.get_registry_path(include_discovery=True)

            assert result["success"] is False
            assert result["path"] == invalid_temp_dir
            assert result["is_valid"] is False
            assert result["discovered_path"] == valid_registry
        finally:
            if Path(invalid_temp_dir).exists():
                shutil.rmtree(invalid_temp_dir)

    def test_get_path_without_discovery(self):
        """Test that include_discovery=False skips discovery"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)
        result = operation.get_registry_path(include_discovery=False)

        assert result["success"] is False
        assert result["path"] is None
        assert result["discovered_path"] is None


class TestRegistryOperationSetPath:
    """Tests for setting registry path"""

    def test_set_path_valid_registry(self, valid_registry):
        """Test setting a valid registry path"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)
        result = operation.set_registry_path(valid_registry, validate=True)

        assert result["success"] is True
        assert result["path"] == valid_registry
        assert result["previous_path"] is None
        assert result["is_valid"] is True

        mock_config.set.assert_called_once_with(
            RegistryOperation.CONFIG_KEY, valid_registry
        )

    def test_set_path_replaces_previous(self, valid_registry):
        """Test that setting path returns previous path"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = "/old/registry/path"

        operation = RegistryOperation(config=mock_config)
        result = operation.set_registry_path(valid_registry, validate=True)

        assert result["success"] is True
        assert result["previous_path"] == "/old/registry/path"

    def test_set_path_invalid_raises_error(self, temp_dir):
        """Test that setting an invalid path raises InvalidRegistryPathError"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)

        with pytest.raises(InvalidRegistryPathError) as exc_info:
            operation.set_registry_path(temp_dir, validate=True)

        # Compare resolved paths to handle platform differences
        assert _resolve_path(temp_dir) == _resolve_path(exc_info.value.path)
        assert len(exc_info.value.missing_components) > 0

    def test_set_path_without_validation(self, temp_dir):
        """Test setting path without validation"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)
        result = operation.set_registry_path(temp_dir, validate=False)

        assert result["success"] is True
        assert result["is_valid"] is True  # Not validated, assumed valid

        mock_config.set.assert_called_once()

    def test_set_path_resolves_to_absolute(self, valid_registry):
        """Test that set path resolves to absolute"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)
        result = operation.set_registry_path(valid_registry, validate=True)

        assert result["success"] is True
        assert Path(result["path"]).is_absolute()

    def test_config_key_constant(self):
        """Test that CONFIG_KEY has expected value"""
        assert RegistryOperation.CONFIG_KEY == "registry_path"


class TestRegistryOperationListRegistries:
    """Tests for listing registries"""

    def test_list_single_configured_registry(self, valid_registry):
        """Test listing when one registry is configured"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = valid_registry

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.list_registries()

        assert result["success"] is True
        assert result["count"] == 1

        registry = result["registries"][0]
        assert registry["path"] == valid_registry
        assert registry["is_current"] is True
        assert registry["is_valid"] is True
        assert registry["name"] == "default"
        assert registry["source"] == "config"

    def test_list_no_registries(self):
        """Test listing when no registries are configured"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.list_registries()

        assert result["success"] is True
        assert result["count"] == 0
        assert result["registries"] == []

    def test_list_includes_discovered_registry(self, valid_registry):
        """Test that discovered registry is included if different from configured"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        with patch(
            "hxc.core.operations.registry.get_project_root",
            return_value=valid_registry,
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.list_registries()

        assert result["success"] is True
        assert result["count"] == 1

        registry = result["registries"][0]
        assert registry["path"] == valid_registry
        assert registry["is_current"] is True  # Current because nothing else configured
        assert registry["source"] == "discovered"

    def test_list_both_configured_and_discovered(self, valid_registry):
        """Test listing when configured and discovered differ"""
        # Create another valid registry in a separate temp directory
        other_temp_dir = _resolve_path(tempfile.mkdtemp())
        try:
            other_registry = Path(other_temp_dir)
            (other_registry / "programs").mkdir()
            (other_registry / "projects").mkdir()
            (other_registry / "missions").mkdir()
            (other_registry / "actions").mkdir()
            (other_registry / "config.yml").write_text("# Config\n")

            mock_config = MagicMock(spec=Config)
            mock_config.get.return_value = valid_registry

            with patch(
                "hxc.core.operations.registry.get_project_root",
                return_value=str(other_registry),
            ):
                operation = RegistryOperation(config=mock_config)
                result = operation.list_registries()

            assert result["success"] is True
            assert result["count"] == 2

            # Find configured and discovered
            configured = next(r for r in result["registries"] if r["source"] == "config")
            discovered = next(
                r for r in result["registries"] if r["source"] == "discovered"
            )

            assert configured["path"] == valid_registry
            assert configured["is_current"] is True
            assert discovered["path"] == str(other_registry)
            assert discovered["is_current"] is False
        finally:
            if Path(other_temp_dir).exists():
                shutil.rmtree(other_temp_dir)

    def test_list_does_not_duplicate_same_path(self, valid_registry):
        """Test that same path is not listed twice"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = valid_registry

        with patch(
            "hxc.core.operations.registry.get_project_root",
            return_value=valid_registry,
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.list_registries()

        assert result["success"] is True
        assert result["count"] == 1  # Not duplicated

    def test_list_shows_invalid_configured_registry(self, temp_dir):
        """Test that invalid configured registry is still listed"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = temp_dir  # Invalid

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.list_registries()

        assert result["success"] is True
        assert result["count"] == 1

        registry = result["registries"][0]
        assert registry["path"] == temp_dir
        assert registry["is_valid"] is False


class TestRegistryOperationDiscoverRegistry:
    """Tests for registry discovery"""

    def test_discover_finds_registry(self, valid_registry):
        """Test that discover finds a valid registry"""
        mock_config = MagicMock(spec=Config)

        with patch(
            "hxc.core.operations.registry.get_project_root",
            return_value=valid_registry,
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.discover_registry()

        assert result["success"] is True
        assert result["path"] == valid_registry
        assert result["is_valid"] is True

    def test_discover_no_registry_found(self):
        """Test discovery when no registry exists"""
        mock_config = MagicMock(spec=Config)

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.discover_registry()

        assert result["success"] is False
        assert result["path"] is None
        assert result["is_valid"] is False

    def test_discover_validates_found_path(self, temp_dir):
        """Test that discovered path is validated"""
        mock_config = MagicMock(spec=Config)

        # Return an invalid path
        with patch(
            "hxc.core.operations.registry.get_project_root",
            return_value=temp_dir,
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.discover_registry()

        assert result["success"] is True  # Found something
        assert result["path"] == temp_dir
        assert result["is_valid"] is False  # But it's not valid


class TestRegistryOperationClearPath:
    """Tests for clearing registry path"""

    def test_clear_path(self):
        """Test clearing the configured registry path"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = "/some/registry/path"
        mock_config.load.return_value = {"registry_path": "/some/registry/path"}

        operation = RegistryOperation(config=mock_config)
        result = operation.clear_registry_path()

        assert result["success"] is True
        assert result["previous_path"] == "/some/registry/path"

        mock_config.save.assert_called_once()

    def test_clear_path_when_not_set(self):
        """Test clearing when no path is set"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None
        mock_config.load.return_value = {}

        operation = RegistryOperation(config=mock_config)
        result = operation.clear_registry_path()

        assert result["success"] is True
        assert result["previous_path"] is None

    def test_clear_removes_key_from_config(self):
        """Test that clear actually removes the key from config"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = "/some/path"
        config_data = {"registry_path": "/some/path", "other_key": "value"}
        mock_config.load.return_value = config_data

        operation = RegistryOperation(config=mock_config)
        operation.clear_registry_path()

        # Verify save was called with config minus the registry_path key
        mock_config.save.assert_called_once()
        saved_config = mock_config.save.call_args[0][0]
        assert "registry_path" not in saved_config
        assert "other_key" in saved_config


class TestRegistryOperationExceptions:
    """Tests for exception classes"""

    def test_invalid_registry_path_error_attributes(self):
        """Test InvalidRegistryPathError has correct attributes"""
        missing = ["config.yml", "programs/"]
        error = InvalidRegistryPathError("/bad/path", missing)

        assert error.path == "/bad/path"
        assert error.missing_components == missing
        assert "/bad/path" in str(error)
        assert "config.yml" in str(error)

    def test_invalid_registry_path_error_inherits(self):
        """Test InvalidRegistryPathError inherits from RegistryOperationError"""
        error = InvalidRegistryPathError("/path", [])
        assert isinstance(error, RegistryOperationError)

    def test_registry_not_found_error_inherits(self):
        """Test RegistryNotFoundError inherits from RegistryOperationError"""
        error = RegistryNotFoundError("No registry")
        assert isinstance(error, RegistryOperationError)


class TestRegistryOperationDefaultConfig:
    """Tests for default configuration handling"""

    def test_creates_default_config_if_not_provided(self):
        """Test that RegistryOperation creates a Config if not provided"""
        with patch("hxc.core.operations.registry.Config") as MockConfig:
            mock_instance = MagicMock()
            MockConfig.return_value = mock_instance
            mock_instance.get.return_value = None

            operation = RegistryOperation()

            # Should have created a Config
            MockConfig.assert_called_once()

    def test_uses_provided_config(self, mock_config):
        """Test that RegistryOperation uses provided Config"""
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)

        # Access the config to trigger usage
        operation.get_registry_path(include_discovery=False)

        mock_config.get.assert_called()


class TestRegistryOperationIntegration:
    """Integration tests for RegistryOperation"""

    def test_set_then_get_path(self, valid_registry):
        """Test setting a path then getting it"""
        # Use real Config with temp directory
        temp_config_dir = _resolve_path(tempfile.mkdtemp())
        try:
            config = Config(config_dir=temp_config_dir)
            operation = RegistryOperation(config=config)

            # Set path
            set_result = operation.set_registry_path(valid_registry, validate=True)
            assert set_result["success"] is True

            # Get path
            get_result = operation.get_registry_path(include_discovery=False)
            assert get_result["success"] is True
            assert get_result["path"] == valid_registry
            assert get_result["is_valid"] is True

        finally:
            shutil.rmtree(temp_config_dir)

    def test_set_then_clear_then_get(self, valid_registry):
        """Test setting, clearing, then getting path"""
        temp_config_dir = _resolve_path(tempfile.mkdtemp())
        try:
            config = Config(config_dir=temp_config_dir)
            operation = RegistryOperation(config=config)

            # Set path
            operation.set_registry_path(valid_registry, validate=True)

            # Clear path
            clear_result = operation.clear_registry_path()
            assert clear_result["success"] is True
            assert clear_result["previous_path"] == valid_registry

            # Get path (should be empty)
            with patch(
                "hxc.core.operations.registry.get_project_root", return_value=None
            ):
                get_result = operation.get_registry_path(include_discovery=False)
                assert get_result["success"] is False
                assert get_result["path"] is None

        finally:
            shutil.rmtree(temp_config_dir)

    def test_set_then_list(self, valid_registry):
        """Test setting a path then listing registries"""
        temp_config_dir = _resolve_path(tempfile.mkdtemp())
        try:
            config = Config(config_dir=temp_config_dir)
            operation = RegistryOperation(config=config)

            # Set path
            operation.set_registry_path(valid_registry, validate=True)

            # List registries
            with patch(
                "hxc.core.operations.registry.get_project_root", return_value=None
            ):
                list_result = operation.list_registries()

            assert list_result["success"] is True
            assert list_result["count"] == 1
            assert list_result["registries"][0]["path"] == valid_registry

        finally:
            shutil.rmtree(temp_config_dir)


class TestRegistryOperationEdgeCases:
    """Tests for edge cases"""

    def test_validate_path_with_symlink(self, valid_registry):
        """Test validation with symlinked path"""
        import os

        symlink_temp_dir = _resolve_path(tempfile.mkdtemp())
        try:
            symlink_path = Path(symlink_temp_dir) / "registry_link"

            # Skip if symlinks not supported
            try:
                symlink_path.symlink_to(valid_registry)
            except OSError:
                pytest.skip("Symlinks not supported on this platform")

            result = RegistryOperation.validate_registry_path(str(symlink_path))

            # Should resolve symlink and validate
            assert result["valid"] is True
        finally:
            if Path(symlink_temp_dir).exists():
                shutil.rmtree(symlink_temp_dir)

    def test_validate_path_with_trailing_slash(self, valid_registry):
        """Test validation with trailing slash"""
        path_with_slash = valid_registry + "/"

        result = RegistryOperation.validate_registry_path(path_with_slash)

        assert result["valid"] is True

    def test_set_path_with_relative_path(self, valid_registry):
        """Test setting a relative path resolves to absolute"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)

        # Get the relative path
        cwd = Path.cwd()
        try:
            rel_path = Path(valid_registry).relative_to(cwd)
        except ValueError:
            # Not relative to cwd, skip this test
            pytest.skip("Registry path not relative to cwd")

        result = operation.set_registry_path(str(rel_path), validate=True)

        assert result["success"] is True
        assert Path(result["path"]).is_absolute()

    def test_get_path_config_returns_nonexistent_path(self):
        """Test behavior when config contains a path that no longer exists"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = "/path/that/does/not/exist/xyz123"

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.get_registry_path(include_discovery=False)

        assert result["success"] is False
        assert result["is_valid"] is False
        assert "validation_errors" in result

    def test_list_registries_with_both_invalid(self, temp_dir):
        """Test listing when both configured and discovered are invalid"""
        other_invalid = _resolve_path(tempfile.mkdtemp())
        try:
            mock_config = MagicMock(spec=Config)
            mock_config.get.return_value = temp_dir  # Invalid

            with patch(
                "hxc.core.operations.registry.get_project_root",
                return_value=other_invalid,  # Also invalid
            ):
                operation = RegistryOperation(config=mock_config)
                result = operation.list_registries()

            assert result["success"] is True
            assert result["count"] == 2

            for registry in result["registries"]:
                assert registry["is_valid"] is False

        finally:
            shutil.rmtree(other_invalid)


class TestRegistryOperationBehavioralParity:
    """Tests to verify behavioral parity with CLI"""

    def test_validation_checks_same_components_as_cli(self, temp_dir):
        """Test that validation checks the same components as CLI does"""
        # Create a registry missing different components
        path = Path(temp_dir)

        # Test missing all
        result = RegistryOperation.validate_registry_path(temp_dir)
        assert result["valid"] is False

        expected_missing = {"config.yml", "programs/", "projects/", "missions/", "actions/"}
        assert set(result["missing"]) == expected_missing

    def test_config_key_matches_cli(self):
        """Test that the config key matches what CLI uses"""
        # This ensures both CLI and operations use the same config key
        assert RegistryOperation.CONFIG_KEY == "registry_path"

    def test_validation_result_structure(self, valid_registry):
        """Test that validation result has expected structure"""
        result = RegistryOperation.validate_registry_path(valid_registry)

        # Check all expected keys are present
        assert "valid" in result
        assert "path" in result
        assert "missing" in result

        # Check types
        assert isinstance(result["valid"], bool)
        assert isinstance(result["path"], str)
        assert isinstance(result["missing"], list)

    def test_get_registry_path_result_structure(self, valid_registry):
        """Test that get_registry_path result has expected structure"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = valid_registry

        operation = RegistryOperation(config=mock_config)
        result = operation.get_registry_path()

        # Check all expected keys are present
        expected_keys = {"success", "path", "is_valid", "source", "discovered_path"}
        assert set(result.keys()) >= expected_keys

    def test_set_registry_path_result_structure(self, valid_registry):
        """Test that set_registry_path result has expected structure"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = None

        operation = RegistryOperation(config=mock_config)
        result = operation.set_registry_path(valid_registry, validate=True)

        # Check all expected keys are present
        expected_keys = {"success", "path", "previous_path", "is_valid"}
        assert set(result.keys()) == expected_keys

    def test_list_registries_result_structure(self, valid_registry):
        """Test that list_registries result has expected structure"""
        mock_config = MagicMock(spec=Config)
        mock_config.get.return_value = valid_registry

        with patch(
            "hxc.core.operations.registry.get_project_root", return_value=None
        ):
            operation = RegistryOperation(config=mock_config)
            result = operation.list_registries()

        # Check all expected keys are present
        assert "success" in result
        assert "registries" in result
        assert "count" in result

        # Check registry object structure
        if result["count"] > 0:
            registry = result["registries"][0]
            expected_registry_keys = {"path", "is_current", "is_valid", "name", "source"}
            assert set(registry.keys()) == expected_registry_keys