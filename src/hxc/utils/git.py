"""
Git utilities for HXC registry operations.

Provides shared git functionality for create, edit, and delete commands
to maintain consistent version control behavior across the registry.
"""
import subprocess
import re
from pathlib import Path
from typing import Optional, List, Dict, Any


class GitOperationResult:
    """Result of a git operation."""
    
    def __init__(
        self,
        success: bool,
        commit_hash: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
    ):
        self.success = success
        self.commit_hash = commit_hash
        self.message = message
        self.error = error


def find_git_root(start_path: str) -> Optional[str]:
    """
    Walk up from start_path looking for a .git directory.
    
    Args:
        start_path: Directory to start searching from
        
    Returns:
        Path to the git repository root, or None if not found
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
        True if git is installed and accessible, False otherwise
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
        git_output: Standard output from git commit command
        
    Returns:
        Short commit hash string, or None if not found
    """
    match = re.search(r'\[.*?\s+([0-9a-f]{5,})\]', git_output)
    return match.group(1) if match else None


def summarize_changes(changes: List[str], max_length: int = 72) -> str:
    """
    Build a short one-line summary from the changes list.
    
    Args:
        changes: List of change descriptions
        max_length: Maximum length of the summary line
        
    Returns:
        Summary string suitable for commit subject line
    """
    if not changes:
        return "no changes"
    if len(changes) == 1:
        summary = changes[0]
        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."
        return summary
    first_change = changes[0].split(':')[0] if ':' in changes[0] else changes[0]
    return f"{first_change}; {len(changes) - 1} more change(s)"


def build_commit_message(
    action: str,
    file_stem: str,
    entity_data: Dict[str, Any],
    changes: Optional[List[str]] = None,
) -> str:
    """
    Build a commit message for an entity operation.
    
    Args:
        action: The action performed ("Create", "Edit", "Delete")
        file_stem: The file name without extension (e.g., "proj-abc12345")
        entity_data: Entity data dictionary containing metadata
        changes: Optional list of changes (for Edit operations)
        
    Returns:
        Complete commit message with subject and body
    """
    title = entity_data.get('title', 'Untitled')
    entity_type = entity_data.get('type', 'entity')
    entity_id = entity_data.get('id', '')
    uid = entity_data.get('uid', '')
    
    if action == "Edit" and changes:
        summary = summarize_changes(changes)
        subject = f"{action} {file_stem}: {summary}"
    else:
        subject = f"{action} {file_stem}: {title}"
    
    # Build commit body with metadata
    body_lines = []
    
    if action == "Edit" and changes:
        body_lines.extend(f"- {change}" for change in changes)
        body_lines.append("")
    
    body_lines.append(f"Entity type: {entity_type}")
    if entity_id:
        body_lines.append(f"Entity ID: {entity_id}")
    if uid:
        body_lines.append(f"Entity UID: {uid}")
    
    # Add optional metadata for Create operations
    if action == "Create":
        category = entity_data.get('category')
        status = entity_data.get('status')
        start_date = entity_data.get('start_date')
        
        if category:
            body_lines.append(f"Category: {category}")
        if status:
            body_lines.append(f"Status: {status}")
        if start_date:
            body_lines.append(f"Created: {start_date}")
    
    body = "\n".join(body_lines)
    return f"{subject}\n\n{body}"


def commit_entity_change(
    registry_path: str,
    file_path: Path,
    action: str,
    entity_data: Dict[str, Any],
    changes: Optional[List[str]] = None,
) -> GitOperationResult:
    """
    Stage and commit an entity file change.
    
    This function handles the complete git workflow for entity operations:
    1. Verifies the registry is in a git repository
    2. Verifies git is available
    3. Stages the specific file
    4. Creates a commit with descriptive message
    
    Args:
        registry_path: Path to the registry root
        file_path: Path to the entity file (created, modified, or deleted)
        action: The action performed ("Create", "Edit", "Delete")
        entity_data: Entity data dictionary containing metadata
        changes: Optional list of changes (for Edit operations)
        
    Returns:
        GitOperationResult with success status and details
    """
    # Find git root
    git_root = find_git_root(registry_path)
    if git_root is None:
        return GitOperationResult(
            success=False,
            error="Registry is not inside a git repository"
        )
    
    # Verify git is available
    if not git_available():
        return GitOperationResult(
            success=False,
            error="git is not installed or not on PATH"
        )
    
    # Build commit message
    file_stem = file_path.stem if isinstance(file_path, Path) else Path(file_path).stem
    commit_message = build_commit_message(action, file_stem, entity_data, changes)
    
    # Extract subject line for display
    subject_line = commit_message.split('\n')[0]
    
    try:
        # Stage the file (git add handles both new, modified, and deleted files)
        subprocess.run(
            ["git", "add", str(file_path)],
            cwd=git_root,
            check=True,
            capture_output=True,
            text=True,
        )
        
        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_message],
            cwd=git_root,
            check=True,
            capture_output=True,
            text=True,
        )
        
        commit_hash = parse_commit_hash(result.stdout)
        
        return GitOperationResult(
            success=True,
            commit_hash=commit_hash,
            message=subject_line,
        )
        
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if e.stderr else ""
        stdout = e.stdout.strip() if e.stdout else ""
        
        # "nothing to commit" is not really an error
        if "nothing to commit" in stderr or "nothing to commit" in stdout:
            return GitOperationResult(
                success=False,
                error="Nothing new to commit (file may not have changed on disk)"
            )
        
        return GitOperationResult(
            success=False,
            error=stderr or stdout or "Unknown git error"
        )


def print_commit_result(result: GitOperationResult, no_commit_flag: bool = False) -> None:
    """
    Print the result of a git commit operation to stdout.
    
    Args:
        result: The GitOperationResult to display
        no_commit_flag: Whether the --no-commit flag was used
    """
    if no_commit_flag:
        print("⚠️  Changes not committed (--no-commit flag used)")
        return
    
    if result.success:
        hash_display = f" ({result.commit_hash})" if result.commit_hash else ""
        print(f'📦 Changes committed to git{hash_display}')
        if result.message:
            print(f'   "{result.message}"')
    else:
        if result.error:
            if "not inside a git repository" in result.error:
                print(f"⚠️  Registry is not inside a git repository — changes not committed.")
            elif "git is not installed" in result.error:
                print(f"⚠️  git is not installed or not on PATH — changes not committed.")
            elif "Nothing new to commit" in result.error:
                print(f"⚠️  {result.error}")
            else:
                print(f"⚠️  git commit failed: {result.error}")
                print("    Operation was completed but not committed.")