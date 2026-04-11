"""
Tests for path security utilities
"""

import os
import sys
from pathlib import Path

import pytest

from hxc.utils.path_security import (
    PathSecurityError,
    ensure_within_registry,
    get_safe_entity_path,
    resolve_safe_path,
    validate_registry_path,
)


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)

    # Create entity directories
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    return registry_path


def test_resolve_safe_path_relative(temp_registry):
    """Test resolving a safe relative path"""
    target = "projects/proj-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert resolved.parent.name == "projects"
    assert resolved.name == "proj-123.yml"
    assert str(temp_registry) in str(resolved)


def test_resolve_safe_path_absolute_within_registry(temp_registry):
    """Test resolving an absolute path that is within the registry"""
    target = temp_registry / "projects" / "proj-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert resolved == target.resolve()


def test_resolve_safe_path_traversal_relative(temp_registry):
    """Test that relative path traversal is blocked"""
    target = "../../../etc/passwd"

    with pytest.raises(PathSecurityError) as exc_info:
        resolve_safe_path(temp_registry, target)

    assert "outside the registry root" in str(exc_info.value)


def test_resolve_safe_path_traversal_absolute(temp_registry):
    """Test that absolute path outside registry is blocked"""
    target = "/etc/passwd"

    with pytest.raises(PathSecurityError) as exc_info:
        resolve_safe_path(temp_registry, target)

    assert "outside the registry root" in str(exc_info.value)


@pytest.mark.skipif(
    sys.platform == "win32", reason="Symlinks require admin privileges on Windows"
)
def test_resolve_safe_path_symlink_escape(temp_registry, tmp_path):
    """Test that symlinks cannot escape the registry"""
    # Create a directory outside the registry
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_file = external_dir / "secret.txt"
    external_file.write_text("secret data")

    # Create a symlink inside the registry pointing outside
    symlink_path = temp_registry / "projects" / "escape_link"
    symlink_path.symlink_to(external_file)

    # Attempt to resolve the symlink
    with pytest.raises(PathSecurityError) as exc_info:
        resolve_safe_path(temp_registry, symlink_path)

    assert "outside the registry root" in str(exc_info.value)


def test_resolve_safe_path_dot_segments(temp_registry):
    """Test that paths with . and .. segments are properly resolved"""
    target = "projects/../projects/./proj-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert resolved.parent.name == "projects"
    assert resolved.name == "proj-123.yml"


def test_validate_registry_path_valid(temp_registry):
    """Test validating a valid path"""
    target = "projects/proj-123.yml"
    assert validate_registry_path(temp_registry, target) is True


def test_validate_registry_path_invalid(temp_registry):
    """Test validating an invalid path"""
    target = "../../../etc/passwd"
    assert validate_registry_path(temp_registry, target) is False


def test_validate_registry_path_absolute_outside(temp_registry):
    """Test validating an absolute path outside registry"""
    target = "/etc/passwd"
    assert validate_registry_path(temp_registry, target) is False


def test_get_safe_entity_path_project(temp_registry):
    """Test getting a safe path for a project entity"""
    filename = "proj-123.yml"
    path = get_safe_entity_path(temp_registry, "project", filename)

    assert path.is_absolute()
    assert path.parent.name == "projects"
    assert path.name == filename


def test_get_safe_entity_path_program(temp_registry):
    """Test getting a safe path for a program entity"""
    filename = "prog-456.yml"
    path = get_safe_entity_path(temp_registry, "program", filename)

    assert path.is_absolute()
    assert path.parent.name == "programs"
    assert path.name == filename


def test_get_safe_entity_path_mission(temp_registry):
    """Test getting a safe path for a mission entity"""
    filename = "miss-789.yml"
    path = get_safe_entity_path(temp_registry, "mission", filename)

    assert path.is_absolute()
    assert path.parent.name == "missions"
    assert path.name == filename


def test_get_safe_entity_path_action(temp_registry):
    """Test getting a safe path for an action entity"""
    filename = "act-abc.yml"
    path = get_safe_entity_path(temp_registry, "action", filename)

    assert path.is_absolute()
    assert path.parent.name == "actions"
    assert path.name == filename


def test_get_safe_entity_path_invalid_type(temp_registry):
    """Test that invalid entity type raises ValueError"""
    filename = "invalid-123.yml"

    with pytest.raises(ValueError) as exc_info:
        get_safe_entity_path(temp_registry, "invalid_type", filename)

    assert "Invalid entity type" in str(exc_info.value)


def test_get_safe_entity_path_traversal_in_filename(temp_registry):
    """Test that path traversal in filename is blocked"""
    filename = "../../../etc/passwd"

    with pytest.raises(PathSecurityError) as exc_info:
        get_safe_entity_path(temp_registry, "project", filename)

    assert "outside the registry root" in str(exc_info.value)


def test_ensure_within_registry_single_valid(temp_registry):
    """Test ensuring a single valid path"""
    path = "projects/proj-123.yml"
    # Should not raise any exception
    ensure_within_registry(temp_registry, path)


def test_ensure_within_registry_multiple_valid(temp_registry):
    """Test ensuring multiple valid paths"""
    paths = ["projects/proj-123.yml", "programs/prog-456.yml", "missions/miss-789.yml"]
    # Should not raise any exception
    ensure_within_registry(temp_registry, *paths)


def test_ensure_within_registry_single_invalid(temp_registry):
    """Test ensuring a single invalid path raises error"""
    path = "../../../etc/passwd"

    with pytest.raises(PathSecurityError) as exc_info:
        ensure_within_registry(temp_registry, path)

    assert "outside the registry root" in str(exc_info.value)


def test_ensure_within_registry_multiple_with_invalid(temp_registry):
    """Test ensuring multiple paths with one invalid raises error"""
    paths = ["projects/proj-123.yml", "../../../etc/passwd", "programs/prog-456.yml"]

    with pytest.raises(PathSecurityError) as exc_info:
        ensure_within_registry(temp_registry, *paths)

    assert "outside the registry root" in str(exc_info.value)


def test_resolve_safe_path_with_pathlib(temp_registry):
    """Test that Path objects work correctly"""
    target = Path("projects") / "proj-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert resolved.parent.name == "projects"
    assert resolved.name == "proj-123.yml"


def test_resolve_safe_path_registry_as_pathlib(tmp_path):
    """Test that registry root can be a Path object"""
    registry_path = Path(tmp_path) / "test_registry"
    registry_path.mkdir(parents=True)
    (registry_path / "projects").mkdir()

    target = "projects/proj-123.yml"
    resolved = resolve_safe_path(registry_path, target)

    assert resolved.is_absolute()
    assert resolved.parent.name == "projects"


def test_path_security_error_message_clarity(temp_registry):
    """Test that PathSecurityError provides clear error messages"""
    target = "../../../etc/passwd"

    with pytest.raises(PathSecurityError) as exc_info:
        resolve_safe_path(temp_registry, target)

    error_msg = str(exc_info.value)
    assert target in error_msg
    assert str(temp_registry) in error_msg
    assert "outside" in error_msg.lower()


def test_resolve_safe_path_empty_string(temp_registry):
    """Test resolving an empty string path"""
    target = ""
    resolved = resolve_safe_path(temp_registry, target)

    # Empty string should resolve to registry root
    assert resolved == temp_registry.resolve()


def test_resolve_safe_path_current_directory(temp_registry):
    """Test resolving current directory marker"""
    target = "."
    resolved = resolve_safe_path(temp_registry, target)

    # Current directory should resolve to registry root
    assert resolved == temp_registry.resolve()


def test_resolve_safe_path_nested_directories(temp_registry):
    """Test resolving deeply nested valid paths"""
    # Create nested structure
    nested_dir = temp_registry / "projects" / "subdir1" / "subdir2"
    nested_dir.mkdir(parents=True)

    target = "projects/subdir1/subdir2/proj-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert "subdir1" in str(resolved)
    assert "subdir2" in str(resolved)
    assert resolved.name == "proj-123.yml"


def test_get_safe_entity_path_with_subdirectory(temp_registry):
    """Test that entity paths with subdirectories in filename are blocked"""
    filename = "subdir/proj-123.yml"

    # This should work as it's still within the projects folder
    path = get_safe_entity_path(temp_registry, "project", filename)
    assert path.is_absolute()
    assert "projects" in str(path)
    assert "subdir" in str(path)


def test_resolve_safe_path_case_sensitivity(temp_registry):
    """Test path resolution with different case (on case-sensitive systems)"""
    target = "projects/PROJ-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert resolved.parent.name == "projects"
    assert resolved.name == "PROJ-123.yml"


def test_validate_registry_path_with_pathlib(temp_registry):
    """Test validation with Path objects"""
    target = Path("projects") / "proj-123.yml"
    assert validate_registry_path(temp_registry, target) is True


def test_ensure_within_registry_empty_paths(temp_registry):
    """Test ensuring with no paths provided"""
    # Should not raise any exception
    ensure_within_registry(temp_registry)


def test_resolve_safe_path_unicode_characters(temp_registry):
    """Test resolving paths with unicode characters"""
    target = "projects/proj-测试-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert "测试" in str(resolved)


def test_resolve_safe_path_special_characters(temp_registry):
    """Test resolving paths with special characters"""
    target = "projects/proj-test_file-123.yml"
    resolved = resolve_safe_path(temp_registry, target)

    assert resolved.is_absolute()
    assert "test_file" in str(resolved)
