"""
Init Operation for HoxCore Registry.

This module provides the shared init operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Registry directory structure creation
- Configuration file creation
- Index database initialization
- Git repository initialization with optional remote
- Path security enforcement
"""

import os
import pathlib
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from hxc.utils.path_security import PathSecurityError, resolve_safe_path


class InitOperationError(Exception):
    """Base exception for init operation errors"""

    pass


class DirectoryNotEmptyError(InitOperationError):
    """Raised when attempting to initialize a non-empty directory"""

    pass


class GitOperationError(InitOperationError):
    """Raised when a git operation fails"""

    pass


class InitOperation:
    """
    Shared init operation for CLI and MCP interfaces.

    This class provides the core registry initialization logic including:
    - Directory structure creation
    - Configuration file creation
    - Index database initialization
    - Git repository setup with optional remote
    - Path security enforcement
    """

    # Required subdirectories for a registry
    REQUIRED_FOLDERS: List[str] = ["programs", "projects", "missions", "actions"]

    # Config file name
    CONFIG_FILE: str = "config.yml"

    # Registry marker directory
    MARKER_DIR: str = ".hxc"

    # Index database file
    INDEX_DB: str = "index.db"

    # Gitignore file
    GITIGNORE: str = ".gitignore"

    # Default gitignore content
    GITIGNORE_CONTENT: str = "index.db\n"

    # Default config content
    CONFIG_CONTENT: str = "# HoxCore Registry Configuration\n"

    def __init__(self, path: str):
        """
        Initialize the init operation.

        Args:
            path: Path where the registry should be initialized
        """
        self.path = path
        self.base_path: Optional[Path] = None

    def _resolve_base_path(self) -> Path:
        """
        Resolve and validate the base path.

        Returns:
            Resolved absolute path

        Raises:
            InitOperationError: If path resolution fails
        """
        try:
            base = pathlib.Path(self.path).resolve()
            self.base_path = base
            return base
        except Exception as e:
            raise InitOperationError(f"Failed to resolve path '{self.path}': {e}")

    def _check_directory_empty(self, base: Path) -> bool:
        """
        Check if the directory is empty (excluding hidden files).

        Args:
            base: Path to check

        Returns:
            True if directory is empty or doesn't exist, False otherwise
        """
        if not base.exists():
            return True

        existing_files = [f for f in os.listdir(base) if not f.startswith(".")]
        return len(existing_files) == 0

    def _create_directory_structure(self, base: Path) -> None:
        """
        Create the registry directory structure.

        Args:
            base: Base path for the registry

        Raises:
            PathSecurityError: If path validation fails
            InitOperationError: If directory creation fails
        """
        # Create base directory if needed
        base.mkdir(parents=True, exist_ok=True)

        # Create required subdirectories
        for folder in self.REQUIRED_FOLDERS:
            folder_path = resolve_safe_path(base, folder)
            folder_path.mkdir(exist_ok=True)

        # Create marker directory
        marker_path = resolve_safe_path(base, self.MARKER_DIR)
        marker_path.mkdir(exist_ok=True)

    def _create_config_file(self, base: Path) -> Path:
        """
        Create the registry configuration file.

        Args:
            base: Base path for the registry

        Returns:
            Path to the created config file

        Raises:
            PathSecurityError: If path validation fails
        """
        config_path = resolve_safe_path(base, self.CONFIG_FILE)
        if not config_path.exists():
            config_path.write_text(self.CONFIG_CONTENT)
        return config_path

    def _create_gitignore(self, base: Path) -> Path:
        """
        Create the .gitignore file.

        Args:
            base: Base path for the registry

        Returns:
            Path to the created .gitignore file

        Raises:
            PathSecurityError: If path validation fails
        """
        gitignore_path = resolve_safe_path(base, self.GITIGNORE)
        gitignore_path.write_text(self.GITIGNORE_CONTENT)
        return gitignore_path

    def _create_index_database(self, base: Path) -> Path:
        """
        Create the index database with initial schema.

        Args:
            base: Base path for the registry

        Returns:
            Path to the created database file

        Raises:
            PathSecurityError: If path validation fails
            InitOperationError: If database creation fails
        """
        db_path = resolve_safe_path(base, self.INDEX_DB)

        if not db_path.exists():
            try:
                conn = sqlite3.connect(db_path)
                try:
                    cursor = conn.cursor()
                    # Create basic table structure
                    cursor.execute(
                        """
                        CREATE TABLE registry_info (
                            key TEXT PRIMARY KEY,
                            value TEXT
                        )
                        """
                    )
                    # Add creation timestamp
                    cursor.execute(
                        """
                        INSERT INTO registry_info (key, value) 
                        VALUES ('created_at', datetime('now'))
                        """
                    )
                    conn.commit()
                finally:
                    conn.close()
            except sqlite3.Error as e:
                raise InitOperationError(f"Failed to create index database: {e}")

        return db_path

    def _git_available(self) -> bool:
        """
        Check if git is available on the system.

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

    def _init_git_repository(
        self,
        base: Path,
        remote_url: Optional[str] = None,
        commit: bool = True,
    ) -> Dict[str, Any]:
        """
        Initialize a git repository in the registry.

        Args:
            base: Base path for the registry
            remote_url: Optional URL for git remote
            commit: Whether to create initial commit

        Returns:
            Dictionary with git operation results

        Raises:
            GitOperationError: If git operations fail
        """
        result = {
            "initialized": False,
            "remote_added": False,
            "committed": False,
            "pushed": False,
        }

        if not self._git_available():
            return result

        # Check if .git already exists
        git_dir = resolve_safe_path(base, ".git")
        if git_dir.exists():
            result["initialized"] = True
            return result

        try:
            # Initialize repository
            subprocess.run(
                ["git", "init"],
                cwd=base,
                check=True,
                capture_output=True,
            )
            result["initialized"] = True

            # Add remote if specified
            if remote_url:
                subprocess.run(
                    ["git", "remote", "add", "origin", remote_url],
                    cwd=base,
                    check=True,
                    capture_output=True,
                )
                result["remote_added"] = True

            # Create initial commit if requested
            if commit:
                subprocess.run(
                    ["git", "add", "."],
                    cwd=base,
                    check=True,
                    capture_output=True,
                )

                subprocess.run(
                    ["git", "commit", "-m", "Initialize HoxCore registry"],
                    cwd=base,
                    check=True,
                    capture_output=True,
                )
                result["committed"] = True

                # Push to remote if configured
                if remote_url:
                    try:
                        subprocess.run(
                            ["git", "push", "-u", "origin", "master"],
                            cwd=base,
                            check=True,
                            capture_output=True,
                        )
                        result["pushed"] = True
                    except subprocess.CalledProcessError:
                        # Push might fail for various reasons (no network, etc.)
                        # This is not a critical error
                        pass

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            raise GitOperationError(f"Git operation failed: {stderr}")

        return result

    def initialize_registry(
        self,
        *,
        use_git: bool = True,
        commit: bool = True,
        remote_url: Optional[str] = None,
        force_empty_check: bool = True,
    ) -> Dict[str, Any]:
        """
        Initialize a new registry at the specified path.

        This is the main entry point for registry initialization, handling:
        - Directory structure creation
        - Configuration file creation
        - Index database initialization
        - Optional git repository setup

        Args:
            use_git: Whether to initialize a git repository (default: True)
            commit: Whether to create initial commit (default: True, requires use_git)
            remote_url: Optional URL for git remote
            force_empty_check: Whether to enforce empty directory check (default: True)

        Returns:
            Dictionary containing:
            - success: bool
            - registry_path: str (absolute path on success)
            - git_initialized: bool
            - committed: bool
            - pushed: bool
            - remote_added: bool

        Raises:
            DirectoryNotEmptyError: If directory is not empty and force_empty_check is True
            PathSecurityError: If path validation fails
            InitOperationError: If initialization fails
        """
        # Resolve the base path
        base = self._resolve_base_path()

        # Ensure base directory exists for empty check
        base.mkdir(parents=True, exist_ok=True)

        # Check if directory is empty
        if force_empty_check and not self._check_directory_empty(base):
            raise DirectoryNotEmptyError(
                "Directory is not empty. Registry initialization aborted."
            )

        try:
            # Create directory structure
            self._create_directory_structure(base)

            # Create configuration file
            self._create_config_file(base)

            # Create gitignore
            self._create_gitignore(base)

            # Create index database
            self._create_index_database(base)

            # Initialize git if requested
            git_result = {
                "initialized": False,
                "remote_added": False,
                "committed": False,
                "pushed": False,
            }

            if use_git:
                git_result = self._init_git_repository(
                    base,
                    remote_url=remote_url,
                    commit=commit,
                )

            return {
                "success": True,
                "registry_path": str(base.resolve()),
                "git_initialized": git_result["initialized"],
                "committed": git_result["committed"],
                "pushed": git_result["pushed"],
                "remote_added": git_result["remote_added"],
            }

        except PathSecurityError:
            raise
        except DirectoryNotEmptyError:
            raise
        except GitOperationError:
            raise
        except Exception as e:
            raise InitOperationError(f"Failed to initialize registry: {e}")

    @classmethod
    def validate_registry_path(cls, path: str) -> bool:
        """
        Validate that a path can be used for a new registry.

        Args:
            path: Path to validate

        Returns:
            True if path is valid for a new registry, False otherwise
        """
        try:
            base = pathlib.Path(path).resolve()

            # Check if path would be a valid directory
            if base.exists() and not base.is_dir():
                return False

            return True
        except Exception:
            return False

    @classmethod
    def is_existing_registry(cls, path: str) -> bool:
        """
        Check if a path already contains a HoxCore registry.

        Args:
            path: Path to check

        Returns:
            True if path contains a registry, False otherwise
        """
        try:
            base = pathlib.Path(path).resolve()

            # Check for marker directory
            marker = base / cls.MARKER_DIR
            if marker.exists() and marker.is_dir():
                return True

            # Check for config file and required folders
            config = base / cls.CONFIG_FILE
            if config.exists():
                for folder in cls.REQUIRED_FOLDERS:
                    folder_path = base / folder
                    if folder_path.exists() and folder_path.is_dir():
                        return True

            return False
        except Exception:
            return False