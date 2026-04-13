"""Shared registry initialization operations for CLI and MCP."""
from pathlib import Path
from typing import Any, Dict, Optional
import os
import sqlite3
import subprocess

from hxc.utils.path_security import resolve_safe_path, PathSecurityError


def initialize_registry(
    path: str,
    git: bool = True,
    commit: bool = True,
    remote_url: Optional[str] = None,
    set_default: bool = True,
) -> Dict[str, Any]:
    """Initialize a registry and return structured results."""
    base = Path(path).resolve()
    base.mkdir(parents=True, exist_ok=True)

    existing_files = [f for f in os.listdir(base) if not f.startswith('.')]
    if existing_files:
        return {
            "success": False,
            "error": "Directory is not empty. Registry initialization aborted.",
            "path": str(base),
        }

    try:
        for folder in ["programs", "projects", "missions", "actions"]:
            resolve_safe_path(base, folder).mkdir(exist_ok=True)

        config_path = resolve_safe_path(base, "config.yml")
        if not config_path.exists():
            config_path.write_text("# HoxCore Registry Configuration\n")

        resolve_safe_path(base, ".hxc").mkdir(exist_ok=True)
        resolve_safe_path(base, ".gitignore").write_text("index.db\n")

        db_path = resolve_safe_path(base, "index.db")
        if not db_path.exists():
            conn = sqlite3.connect(db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE registry_info (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO registry_info (key, value)
                    VALUES ('created_at', datetime('now'))
                    """
                )
                conn.commit()
            finally:
                conn.close()

        git_initialized = False
        committed = False
        git_dir = resolve_safe_path(base, ".git")
        if git and not git_dir.exists():
            subprocess.run(["git", "init"], cwd=base)
            git_initialized = True

            if remote_url:
                subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=base)

            if commit:
                subprocess.run(["git", "add", "."], cwd=base)
                subprocess.run(["git", "commit", "-m", "Initialize HoxCore registry"], cwd=base)
                committed = True

                if remote_url:
                    subprocess.run(["git", "push", "-u", "origin", "master"], cwd=base)

        absolute_path = str(base.resolve())
        return {
            "success": True,
            "registry_path": absolute_path,
            "git_initialized": git_initialized,
            "committed": committed,
            "set_as_default": set_default,
        }
    except PathSecurityError:
        raise
