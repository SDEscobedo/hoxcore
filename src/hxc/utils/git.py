"""
Git utilities for HXC registry operations.

Provides shared git functionality for create, edit, and delete commands
to ensure consistent version control behavior across the registry.
"""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


def find_git_root(start_path: str) -> Optional[str]:
    """
    Walk up from start_path looking for a .git directory.

    Args:
        start_path: The path to start searching from

    Returns:
        The git repository root path, or None if not found
    """
    current = Path(start_path).resolve()
    while True:
        if (current / ".git").exists():
            return str(current)
        parent = current.parent
        if parent == current:
            return None
        current = parent


def git_available() -> bool:
    """
    Check if the git executable can be found.

    Returns:
        True if git is available, False otherwise
    """
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def parse_commit_hash(git_output: str) -> Optional[str]:
    """
    Extract the short commit hash from git commit stdout.

    Typical output: "[main abc1234] Create proj-xxx: ..."

    Args:
        git_output: The stdout from a git commit command

    Returns:
        The short commit hash, or None if not found
    """
    match = re.search(r"\[.*?\s+([0-9a-f]{5,})\]", git_output)
    return match.group(1) if match else None


def summarise_changes(changes: List[str], max_length: int = 72) -> str:
    """
    Build a short one-line summary from the changes list.

    Args:
        changes: List of change descriptions
        max_length: Maximum length for the summary line

    Returns:
        A summarised string of changes
    """
    if not changes:
        return "no changes"
    if len(changes) == 1:
        summary = changes[0]
        if len(summary) > max_length:
            summary = summary[: max_length - 3] + "..."
        return summary
    first_part = changes[0].split(":")[0]
    return f"{first_part}; {len(changes) - 1} more change(s)"


def _build_create_commit_message(
    file_path: Path,
    entity_data: Dict[str, Any],
) -> str:
    """
    Build commit message for entity creation.

    Args:
        file_path: Path to the created entity file
        entity_data: The entity data dictionary

    Returns:
        Formatted commit message
    """
    entity_type = entity_data.get("type", "entity")
    entity_title = entity_data.get("title", "Untitled")
    entity_id = entity_data.get("id", "(not set)")
    entity_uid = entity_data.get("uid", "(not set)")
    category = entity_data.get("category", "(not set)")
    status = entity_data.get("status", "(not set)")

    subject = f"Create {file_path.stem}: {entity_title}"

    body_lines = [
        f"Entity type: {entity_type}",
        f"Entity ID: {entity_id}",
        f"Entity UID: {entity_uid}",
        f"Category: {category}",
        f"Status: {status}",
    ]

    body = "\n".join(body_lines)
    return f"{subject}\n\n{body}"


def _build_edit_commit_message(
    file_path: Path,
    entity_data: Dict[str, Any],
    changes: List[str],
) -> str:
    """
    Build commit message for entity edit.

    Args:
        file_path: Path to the edited entity file
        entity_data: The entity data dictionary
        changes: List of change descriptions

    Returns:
        Formatted commit message
    """
    subject = f"Edit {file_path.stem}: {summarise_changes(changes)}"
    body = "\n".join(f"- {c}" for c in changes)
    return f"{subject}\n\n{body}"


def _build_delete_commit_message(
    file_path: Path,
    entity_data: Dict[str, Any],
) -> str:
    """
    Build commit message for entity deletion.

    Args:
        file_path: Path to the deleted entity file
        entity_data: The entity data dictionary

    Returns:
        Formatted commit message
    """
    entity_type = entity_data.get("type", "entity")
    entity_title = entity_data.get("title", "Untitled")
    entity_id = entity_data.get("id", "(not set)")
    entity_uid = entity_data.get("uid", "(not set)")

    subject = f"Delete {file_path.stem}: {entity_title}"

    body_lines = [
        f"Entity type: {entity_type}",
        f"Entity ID: {entity_id}",
        f"Entity UID: {entity_uid}",
    ]

    body = "\n".join(body_lines)
    return f"{subject}\n\n{body}"


def commit_entity_change(
    registry_path: str,
    file_path: Path,
    action: str,
    entity_data: Dict[str, Any],
    changes: Optional[List[str]] = None,
) -> bool:
    """
    Stage and commit an entity file change.

    This function handles all git operations for entity changes including
    creation, editing, and deletion. It provides consistent behavior and
    error handling across all entity manipulation commands.

    Args:
        registry_path: Path to the registry root
        file_path: Path to the entity file
        action: The action type ("Create", "Edit", or "Delete")
        entity_data: The entity data dictionary
        changes: List of change descriptions (required for Edit action)

    Returns:
        True if commit was successful, False otherwise
    """
    git_root = find_git_root(registry_path)
    if git_root is None:
        print("⚠️  Registry is not inside a git repository — changes not committed.")
        return False

    if not git_available():
        print("⚠️  git is not installed or not on PATH — changes not committed.")
        return False

    # Build appropriate commit message based on action
    if action == "Create":
        commit_message = _build_create_commit_message(file_path, entity_data)
    elif action == "Edit":
        if changes is None:
            changes = []
        commit_message = _build_edit_commit_message(file_path, entity_data, changes)
    elif action == "Delete":
        commit_message = _build_delete_commit_message(file_path, entity_data)
    else:
        commit_message = f"{action} {file_path.stem}"

    try:
        # Stage the file
        # For delete operations, we need to use 'git rm' or 'git add' on the deleted file
        if action == "Delete":
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=git_root,
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=git_root,
                check=True,
                capture_output=True,
                text=True,
            )

        # Create the commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=git_root,
            check=True,
            capture_output=True,
            text=True,
        )

        # Extract commit hash and display confirmation
        commit_hash = parse_commit_hash(result.stdout)
        hash_display = f" ({commit_hash})" if commit_hash else ""

        # Extract subject line from commit message
        subject_line = commit_message.split("\n")[0]

        print(f"📦 Changes committed to git{hash_display}")
        print(f'   "{subject_line}"')

        return True

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else ""
        stdout = e.stdout.strip() if e.stdout else ""

        # "nothing to commit" is not really an error
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            print("⚠️  Nothing new to commit (file may not have changed on disk).")
            return False
        else:
            print(f"⚠️  git commit failed: {stderr or stdout}")
            if action == "Create":
                print("    File was created but not committed.")
            elif action == "Edit":
                print("    Edit was saved but not committed.")
            elif action == "Delete":
                print("    File was deleted but not committed.")
            return False
