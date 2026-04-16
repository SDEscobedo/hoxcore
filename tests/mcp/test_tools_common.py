"""
Common test utilities and helpers for MCP Tools tests.

This module provides shared test utilities, helper functions, and constants
that are used across multiple MCP tools test files. Fixtures are defined
in conftest.py for proper pytest sharing.
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# ─── COMMON CONSTANTS ───────────────────────────────────────────────────────


VALID_ENTITY_TYPES = ["program", "project", "mission", "action"]
VALID_STATUSES = ["active", "completed", "on-hold", "cancelled", "planned"]
VALID_SORT_FIELDS = ["title", "id", "due_date", "status", "created", "modified"]

ENTITY_TYPE_PREFIXES = {
    "program": "prog-",
    "project": "proj-",
    "mission": "miss-",
    "action": "act-",
}

ENTITY_TYPE_FOLDERS = {
    "program": "programs",
    "project": "projects",
    "mission": "missions",
    "action": "actions",
}


# ─── ENTITY VERIFICATION HELPERS ────────────────────────────────────────────


def verify_entity_structure(entity: Dict[str, Any], entity_type: str) -> None:
    """
    Verify that an entity has all required fields.

    Args:
        entity: Entity dictionary to verify
        entity_type: Expected entity type

    Raises:
        AssertionError: If entity structure is invalid
    """
    required_fields = [
        "type",
        "uid",
        "id",
        "title",
        "status",
    ]

    for field in required_fields:
        assert field in entity, f"Entity missing required field: {field}"

    assert entity["type"] == entity_type, f"Expected type '{entity_type}', got '{entity['type']}'"


def verify_entity_file_exists(
    registry_path: str,
    entity_type: str,
    uid: str,
) -> Path:
    """
    Verify that an entity file exists in the correct location.

    Args:
        registry_path: Path to the registry
        entity_type: Entity type
        uid: Entity UID

    Returns:
        Path to the entity file

    Raises:
        AssertionError: If file does not exist
    """
    folder = ENTITY_TYPE_FOLDERS[entity_type]
    prefix = ENTITY_TYPE_PREFIXES[entity_type]
    file_path = Path(registry_path) / folder / f"{prefix}{uid}.yml"

    assert file_path.exists(), f"Entity file does not exist: {file_path}"
    return file_path


def verify_entity_file_content(
    file_path: Path,
    expected_values: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Verify that an entity file contains expected values.

    Args:
        file_path: Path to the entity file
        expected_values: Dictionary of field -> expected value

    Returns:
        The loaded entity data

    Raises:
        AssertionError: If content does not match
    """
    with open(file_path) as f:
        data = yaml.safe_load(f)

    for field, expected in expected_values.items():
        actual = data.get(field)
        assert actual == expected, f"Field '{field}': expected '{expected}', got '{actual}'"

    return data


def verify_entity_not_exists(
    registry_path: str,
    entity_type: str,
    uid: str,
) -> None:
    """
    Verify that an entity file does not exist.

    Args:
        registry_path: Path to the registry
        entity_type: Entity type
        uid: Entity UID

    Raises:
        AssertionError: If file exists
    """
    folder = ENTITY_TYPE_FOLDERS[entity_type]
    prefix = ENTITY_TYPE_PREFIXES[entity_type]
    file_path = Path(registry_path) / folder / f"{prefix}{uid}.yml"

    assert not file_path.exists(), f"Entity file should not exist: {file_path}"


# ─── GIT VERIFICATION HELPERS ───────────────────────────────────────────────


def get_git_log(
    registry_path: str,
    format_string: str = "--oneline",
    count: Optional[int] = None,
) -> str:
    """
    Get git log output from a repository.

    Args:
        registry_path: Path to the git repository
        format_string: Git log format string
        count: Optional number of commits to retrieve

    Returns:
        Git log output as string
    """
    cmd = ["git", "log", format_string]
    if count:
        cmd.append(f"-{count}")

    result = subprocess.run(
        cmd,
        cwd=registry_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def get_last_commit_message(registry_path: str) -> str:
    """
    Get the last commit message from a git repository.

    Args:
        registry_path: Path to the git repository

    Returns:
        Last commit message
    """
    return get_git_log(registry_path, format_string="--format=%B", count=1)


def get_commit_count(registry_path: str) -> int:
    """
    Get the number of commits in a git repository.

    Args:
        registry_path: Path to the git repository

    Returns:
        Number of commits
    """
    log = get_git_log(registry_path)
    lines = [line for line in log.strip().splitlines() if line]
    return len(lines)


def verify_git_commit_exists(
    registry_path: str,
    expected_in_message: List[str],
) -> None:
    """
    Verify that a git commit exists with expected content in message.

    Args:
        registry_path: Path to the git repository
        expected_in_message: List of strings expected in commit message

    Raises:
        AssertionError: If commit message doesn't contain expected content
    """
    message = get_last_commit_message(registry_path)

    for expected in expected_in_message:
        assert expected in message, f"Expected '{expected}' in commit message:\n{message}"


def verify_git_status_clean(registry_path: str, allow_untracked: bool = True) -> None:
    """
    Verify that the git working directory is clean.

    Args:
        registry_path: Path to the git repository
        allow_untracked: If True, untracked files are allowed

    Raises:
        AssertionError: If working directory is not clean
    """
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=registry_path,
        capture_output=True,
        text=True,
        check=True,
    )

    lines = result.stdout.strip().splitlines()

    if allow_untracked:
        # Filter out untracked files (starting with '??')
        lines = [line for line in lines if not line.startswith("??")]

    assert len(lines) == 0, f"Git working directory not clean:\n{result.stdout}"


def verify_file_in_git_index(registry_path: str, file_path: str) -> None:
    """
    Verify that a file is tracked in the git index.

    Args:
        registry_path: Path to the git repository
        file_path: Relative path to the file

    Raises:
        AssertionError: If file is not in git index
    """
    result = subprocess.run(
        ["git", "ls-files", file_path],
        cwd=registry_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert file_path in result.stdout, f"File not in git index: {file_path}"


def verify_file_not_in_git_index(registry_path: str, file_path: str) -> None:
    """
    Verify that a file is not tracked in the git index.

    Args:
        registry_path: Path to the git repository
        file_path: Relative path to the file

    Raises:
        AssertionError: If file is in git index
    """
    result = subprocess.run(
        ["git", "ls-files", file_path],
        cwd=registry_path,
        capture_output=True,
        text=True,
        check=True,
    )

    assert file_path not in result.stdout, f"File should not be in git index: {file_path}"


# ─── REGISTRY VERIFICATION HELPERS ──────────────────────────────────────────


def verify_registry_structure(registry_path: str) -> None:
    """
    Verify that a registry has the correct directory structure.

    Args:
        registry_path: Path to the registry

    Raises:
        AssertionError: If structure is invalid
    """
    base = Path(registry_path)

    # Check required folders
    for folder in ENTITY_TYPE_FOLDERS.values():
        folder_path = base / folder
        assert folder_path.exists(), f"Missing folder: {folder}"
        assert folder_path.is_dir(), f"Not a directory: {folder}"

    # Check required files
    assert (base / "config.yml").exists(), "Missing config.yml"

    # Check marker directory
    assert (base / ".hxc").exists(), "Missing .hxc marker directory"


def verify_registry_config(registry_path: str) -> Dict[str, Any]:
    """
    Load and return the registry configuration.

    Args:
        registry_path: Path to the registry

    Returns:
        Configuration dictionary

    Raises:
        AssertionError: If config is missing or invalid
    """
    config_path = Path(registry_path) / "config.yml"
    assert config_path.exists(), "Missing config.yml"

    with open(config_path) as f:
        content = f.read()

    # Config may be empty or have YAML content
    if content.strip() and not content.strip().startswith("#"):
        return yaml.safe_load(content) or {}

    return {}


# ─── RESULT VERIFICATION HELPERS ────────────────────────────────────────────


def verify_success_result(result: Dict[str, Any]) -> None:
    """
    Verify that a tool result indicates success.

    Args:
        result: Tool result dictionary

    Raises:
        AssertionError: If result is not successful
    """
    assert result.get("success") is True, f"Expected success, got error: {result.get('error')}"


def verify_error_result(
    result: Dict[str, Any],
    expected_in_error: Optional[str] = None,
) -> None:
    """
    Verify that a tool result indicates failure.

    Args:
        result: Tool result dictionary
        expected_in_error: Optional string expected in error message

    Raises:
        AssertionError: If result is not an error
    """
    assert result.get("success") is False, f"Expected failure, but got success: {result}"
    assert "error" in result, "Error result should contain 'error' key"

    if expected_in_error:
        assert expected_in_error.lower() in result["error"].lower(), (
            f"Expected '{expected_in_error}' in error: {result['error']}"
        )


def verify_list_result(
    result: Dict[str, Any],
    expected_count: Optional[int] = None,
    min_count: Optional[int] = None,
    max_count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Verify a list_entities result and return the entities.

    Args:
        result: Tool result dictionary
        expected_count: Expected exact count (optional)
        min_count: Minimum expected count (optional)
        max_count: Maximum expected count (optional)

    Returns:
        List of entities

    Raises:
        AssertionError: If result is invalid
    """
    verify_success_result(result)
    assert "entities" in result, "List result should contain 'entities'"
    assert "count" in result, "List result should contain 'count'"

    entities = result["entities"]
    count = result["count"]

    assert len(entities) == count, f"Count mismatch: {len(entities)} != {count}"

    if expected_count is not None:
        assert count == expected_count, f"Expected {expected_count} entities, got {count}"

    if min_count is not None:
        assert count >= min_count, f"Expected at least {min_count} entities, got {count}"

    if max_count is not None:
        assert count <= max_count, f"Expected at most {max_count} entities, got {count}"

    return entities


def verify_get_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify a get_entity result and return the entity.

    Args:
        result: Tool result dictionary

    Returns:
        Entity dictionary

    Raises:
        AssertionError: If result is invalid
    """
    verify_success_result(result)
    assert "entity" in result, "Get result should contain 'entity'"
    assert result["entity"] is not None, "Entity should not be None"
    assert "file_path" in result, "Get result should contain 'file_path'"

    return result["entity"]


def verify_create_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify a create_entity result and return relevant fields.

    Args:
        result: Tool result dictionary

    Returns:
        Dictionary with uid, id, file_path, entity

    Raises:
        AssertionError: If result is invalid
    """
    verify_success_result(result)
    assert "uid" in result, "Create result should contain 'uid'"
    assert "id" in result, "Create result should contain 'id'"
    assert "file_path" in result, "Create result should contain 'file_path'"
    assert "entity" in result, "Create result should contain 'entity'"
    assert "git_committed" in result, "Create result should contain 'git_committed'"

    return {
        "uid": result["uid"],
        "id": result["id"],
        "file_path": result["file_path"],
        "entity": result["entity"],
        "git_committed": result["git_committed"],
    }


def verify_edit_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify an edit_entity result and return relevant fields.

    Args:
        result: Tool result dictionary

    Returns:
        Dictionary with changes, entity, file_path

    Raises:
        AssertionError: If result is invalid
    """
    verify_success_result(result)
    assert "changes" in result, "Edit result should contain 'changes'"
    assert "entity" in result, "Edit result should contain 'entity'"
    assert "file_path" in result, "Edit result should contain 'file_path'"
    assert "git_committed" in result, "Edit result should contain 'git_committed'"

    return {
        "changes": result["changes"],
        "entity": result["entity"],
        "file_path": result["file_path"],
        "git_committed": result["git_committed"],
    }


def verify_delete_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify a delete_entity result and return relevant fields.

    Args:
        result: Tool result dictionary

    Returns:
        Dictionary with deleted_title, deleted_type, file_path

    Raises:
        AssertionError: If result is invalid
    """
    verify_success_result(result)
    assert "deleted_title" in result, "Delete result should contain 'deleted_title'"
    assert "deleted_type" in result, "Delete result should contain 'deleted_type'"
    assert "file_path" in result, "Delete result should contain 'file_path'"
    assert "git_committed" in result, "Delete result should contain 'git_committed'"

    return {
        "deleted_title": result["deleted_title"],
        "deleted_type": result["deleted_type"],
        "file_path": result["file_path"],
        "git_committed": result["git_committed"],
    }


def verify_confirmation_required(result: Dict[str, Any]) -> None:
    """
    Verify that a delete result requires confirmation.

    Args:
        result: Tool result dictionary

    Raises:
        AssertionError: If confirmation is not required
    """
    assert result.get("success") is False, "Confirmation result should have success=False"
    assert result.get("confirmation_required") is True, "Should require confirmation"
    assert "message" in result, "Should contain confirmation message"
    assert "force=True" in result["message"], "Message should mention force=True"


# ─── TEST DATA HELPERS ──────────────────────────────────────────────────────


def create_test_entity_content(
    entity_type: str,
    uid: str,
    entity_id: str,
    title: str,
    status: str = "active",
    **extra_fields,
) -> Dict[str, Any]:
    """
    Create a test entity dictionary with standard fields.

    Args:
        entity_type: Entity type
        uid: Entity UID
        entity_id: Human-readable ID
        title: Entity title
        status: Entity status
        **extra_fields: Additional fields to include

    Returns:
        Entity dictionary
    """
    entity = {
        "type": entity_type,
        "uid": uid,
        "id": entity_id,
        "title": title,
        "status": status,
        "children": [],
        "related": [],
    }

    entity.update(extra_fields)
    return entity


def write_test_entity(
    registry_path: str,
    entity_type: str,
    uid: str,
    entity_id: str,
    title: str,
    status: str = "active",
    **extra_fields,
) -> Path:
    """
    Write a test entity file to the registry.

    Args:
        registry_path: Path to the registry
        entity_type: Entity type
        uid: Entity UID
        entity_id: Human-readable ID
        title: Entity title
        status: Entity status
        **extra_fields: Additional fields to include

    Returns:
        Path to the created file
    """
    entity = create_test_entity_content(
        entity_type=entity_type,
        uid=uid,
        entity_id=entity_id,
        title=title,
        status=status,
        **extra_fields,
    )

    folder = ENTITY_TYPE_FOLDERS[entity_type]
    prefix = ENTITY_TYPE_PREFIXES[entity_type]
    file_path = Path(registry_path) / folder / f"{prefix}{uid}.yml"

    with open(file_path, "w") as f:
        yaml.dump(entity, f)

    return file_path