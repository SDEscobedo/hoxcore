"""
Tests for the git commit functionality added to the edit command.
"""

import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest
import yaml

from hxc.commands.edit import EditCommand

# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_registry(tmp_path):
    """Minimal registry used by git-commit tests."""
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)

    for folder in ("programs", "projects", "missions", "actions"):
        (registry_path / folder).mkdir()

    (registry_path / "config.yml").write_text("# Test config")

    project_data = {
        "type": "project",
        "uid": "abc12345",
        "id": "P-GIT",
        "title": "Git Test Project",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": ["original"],
        "children": [],
        "related": [],
        "repositories": [],
        "storage": [],
        "databases": [],
        "tools": [],
        "models": [],
        "knowledge_bases": [],
    }
    proj_file = registry_path / "projects" / "proj-abc12345.yml"
    with open(proj_file, "w") as f:
        yaml.dump(project_data, f)

    yield registry_path

    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def git_registry(temp_registry):
    """Registry that is also a proper git repository."""
    subprocess.run(["git", "init"], cwd=temp_registry, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_registry,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_registry,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=temp_registry, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=temp_registry,
        check=True,
        capture_output=True,
    )
    return temp_registry


# ─── _find_git_root ───────────────────────────────────────────────────────────


class TestFindGitRoot:
    def test_finds_root_when_git_repo(self, git_registry):
        root = EditCommand._find_git_root(str(git_registry))
        assert root == str(git_registry)

    def test_finds_root_from_subdir(self, git_registry):
        subdir = git_registry / "projects"
        root = EditCommand._find_git_root(str(subdir))
        assert root == str(git_registry)

    def test_returns_none_when_not_git(self, temp_registry):
        root = EditCommand._find_git_root(str(temp_registry))
        assert root is None

    def test_returns_none_for_filesystem_root(self, tmp_path):
        # Create an isolated directory guaranteed to have no .git above it
        isolated = tmp_path / "no_git"
        isolated.mkdir()
        # Patch Path.parent cycling detection by walking from tmp_path
        # (safe because tmp dirs are under /tmp which has no .git)
        root = EditCommand._find_git_root(str(isolated))
        assert root is None


# ─── _git_available ───────────────────────────────────────────────────────────


class TestGitAvailable:
    def test_returns_true_when_git_present(self):
        assert EditCommand._git_available() is True

    def test_returns_false_when_git_missing(self):
        with patch("hxc.utils.git.subprocess.run", side_effect=FileNotFoundError):
            assert EditCommand._git_available() is False

    def test_returns_false_on_nonzero_exit(self):
        with patch(
            "hxc.utils.git.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            assert EditCommand._git_available() is False


# ─── _summarise_changes ──────────────────────────────────────────────────────


class TestSummariseChanges:
    def test_empty_list(self):
        assert EditCommand._summarise_changes([]) == "no changes"

    def test_single_change(self):
        result = EditCommand._summarise_changes(["Set title: 'Old' → 'New'"])
        assert result == "Set title: 'Old' → 'New'"

    def test_single_long_change_is_truncated(self):
        long = "A" * 100
        result = EditCommand._summarise_changes([long])
        assert len(result) <= 72

    def test_multiple_changes(self):
        changes = [
            "Set title: 'A' → 'B'",
            "Added tag: 'python'",
            "Removed child: 'uid-1'",
        ]
        result = EditCommand._summarise_changes(changes)
        assert "Set title" in result
        assert "2 more change" in result


# ─── _parse_commit_hash ──────────────────────────────────────────────────────


class TestParseCommitHash:
    def test_parses_standard_output(self):
        output = "[main abc1234] Edit proj-xxx: Set title"
        assert EditCommand._parse_commit_hash(output) == "abc1234"

    def test_parses_detached_head(self):
        output = "[HEAD detached at def5678] Edit proj-xxx: ..."
        assert EditCommand._parse_commit_hash(output) == "def5678"

    def test_returns_none_for_unexpected_output(self):
        assert EditCommand._parse_commit_hash("nothing useful here") is None

    def test_returns_none_for_empty_string(self):
        assert EditCommand._parse_commit_hash("") is None


# ─── _commit_changes (unit) ──────────────────────────────────────────────────


class TestCommitChangesUnit:
    """Unit tests using mocks — no real git calls."""

    def _entity(self, uid="abc12345", etype="project"):
        return {"type": etype, "uid": uid, "title": "Test"}

    def test_skips_when_not_git_repo(self, temp_registry, capsys):
        file_path = temp_registry / "projects" / "proj-abc12345.yml"
        EditCommand._commit_changes(
            registry_path=str(temp_registry),
            file_path=file_path,
            entity_data=self._entity(),
            changes=["Set title: 'A' → 'B'"],
        )
        out = capsys.readouterr().out
        assert "not inside a git repository" in out

    def test_skips_when_git_not_installed(self, git_registry, capsys):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        with patch("hxc.utils.git.git_available", return_value=False):
            EditCommand._commit_changes(
                registry_path=str(git_registry),
                file_path=file_path,
                entity_data=self._entity(),
                changes=["Set title: 'A' → 'B'"],
            )
        out = capsys.readouterr().out
        assert "git is not installed" in out

    def test_stages_only_the_edited_file(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Edit proj-abc12345: Set title"
        mock_result.stderr = ""

        # Patch git_available to return True without calling subprocess
        # Then patch subprocess.run at the git module level for actual git commands
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch(
                "hxc.utils.git.subprocess.run", return_value=mock_result
            ) as mock_run:
                EditCommand._commit_changes(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    entity_data=self._entity(),
                    changes=["Set title: 'A' → 'B'"],
                )

        calls = mock_run.call_args_list
        add_call = calls[0]
        assert add_call[0][0] == ["git", "add", str(file_path)]

    def test_commit_message_contains_filename_stem(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Edit proj-abc12345: Set title"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch(
                "hxc.utils.git.subprocess.run", return_value=mock_result
            ) as mock_run:
                EditCommand._commit_changes(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    entity_data=self._entity(),
                    changes=["Set title: 'A' → 'B'"],
                )

        # calls[0] = git add, calls[1] = git commit
        commit_call = mock_run.call_args_list[1]
        # The commit message is passed via -m flag
        commit_args = commit_call[0][0]
        assert "git" in commit_args
        assert "commit" in commit_args
        # Find the message after -m
        m_index = commit_args.index("-m")
        commit_msg = commit_args[m_index + 1]
        assert "proj-abc12345" in commit_msg

    def test_commit_message_body_lists_all_changes(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        changes = ["Set title: 'A' → 'B'", "Added tag: 'python'"]
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Edit proj-abc12345: ..."
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch(
                "hxc.utils.git.subprocess.run", return_value=mock_result
            ) as mock_run:
                EditCommand._commit_changes(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    entity_data=self._entity(),
                    changes=changes,
                )

        commit_call = mock_run.call_args_list[1]
        commit_args = commit_call[0][0]
        m_index = commit_args.index("-m")
        commit_msg = commit_args[m_index + 1]
        for change in changes:
            assert change in commit_msg

    def test_prints_commit_hash_on_success(self, git_registry, capsys):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Edit proj-abc12345: Set title"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("hxc.utils.git.subprocess.run", return_value=mock_result):
                EditCommand._commit_changes(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    entity_data=self._entity(),
                    changes=["Set title: 'A' → 'B'"],
                )

        out = capsys.readouterr().out
        assert "committed to git" in out
        assert "abc1234" in out

    def test_handles_nothing_to_commit_gracefully(self, git_registry, capsys):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        error = subprocess.CalledProcessError(1, "git")
        error.stdout = "nothing to commit"
        error.stderr = ""

        mock_add_result = MagicMock()
        mock_add_result.stdout = ""
        mock_add_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch(
                "hxc.utils.git.subprocess.run", side_effect=[mock_add_result, error]
            ):
                EditCommand._commit_changes(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    entity_data=self._entity(),
                    changes=["Set title: 'A' → 'B'"],
                )

        out = capsys.readouterr().out
        assert "Nothing new to commit" in out

    def test_handles_generic_git_error_gracefully(self, git_registry, capsys):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: not a git repository"

        mock_add_result = MagicMock()
        mock_add_result.stdout = ""
        mock_add_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch(
                "hxc.utils.git.subprocess.run", side_effect=[mock_add_result, error]
            ):
                EditCommand._commit_changes(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    entity_data=self._entity(),
                    changes=["Set title: 'A' → 'B'"],
                )

        out = capsys.readouterr().out
        assert "git commit failed" in out
        assert "Edit was saved but not committed" in out


# ─── Integration: --no-commit flag ───────────────────────────────────────────


class TestNoCommitFlag:
    """Tests that --no-commit prevents git operations."""

    def _run_edit(self, registry_path, extra_args=None):
        """Helper: invoke EditCommand.execute via hxc.cli.main."""
        from hxc.cli import main

        args = ["edit", "P-GIT", "--set-title", "Updated Title"]
        if extra_args:
            args.extend(extra_args)
        with patch(
            "hxc.commands.registry.RegistryCommand.get_registry_path",
            return_value=str(registry_path),
        ):
            return main(args)

    def test_no_commit_flag_prevents_git_call(self, git_registry):
        with patch("hxc.commands.edit.commit_entity_change") as mock_commit:
            result = self._run_edit(git_registry, ["--no-commit"])
        assert result == 0
        mock_commit.assert_not_called()

    def test_no_commit_flag_prints_warning(self, git_registry, capsys):
        result = self._run_edit(git_registry, ["--no-commit"])
        assert result == 0
        out = capsys.readouterr().out
        assert "--no-commit" in out

    def test_without_no_commit_flag_calls_commit(self, git_registry):
        with patch("hxc.commands.edit.commit_entity_change") as mock_commit:
            result = self._run_edit(git_registry)
        assert result == 0
        mock_commit.assert_called_once()

    def test_dry_run_does_not_commit(self, git_registry):
        with patch("hxc.commands.edit.commit_entity_change") as mock_commit:
            result = self._run_edit(git_registry, ["--dry-run"])
        assert result == 0
        mock_commit.assert_not_called()


# ─── Integration: real git commit ────────────────────────────────────────────


class TestRealGitCommit:
    """End-to-end tests that actually run git."""

    def _run_edit(self, registry_path, args=None):
        from hxc.cli import main

        cmd = ["edit", "P-GIT", "--set-title", "Real Commit Title"]
        if args:
            cmd.extend(args)
        with patch(
            "hxc.commands.registry.RegistryCommand.get_registry_path",
            return_value=str(registry_path),
        ):
            return main(cmd)

    def test_commit_is_created_in_git_log(self, git_registry):
        result = self._run_edit(git_registry)
        assert result == 0

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "proj-abc12345" in log.stdout

    def test_commit_message_contains_change_summary(self, git_registry):
        result = self._run_edit(git_registry)
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Set title" in log.stdout

    def test_only_entity_file_is_in_commit(self, git_registry):
        # Create an unrelated unstaged file
        unrelated = git_registry / "unrelated.txt"
        unrelated.write_text("do not commit me")

        result = self._run_edit(git_registry)
        assert result == 0

        show = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        committed_files = show.stdout.strip().splitlines()
        assert any("proj-abc12345.yml" in f for f in committed_files)
        assert not any("unrelated.txt" in f for f in committed_files)
        # Unrelated file should still be untracked
        assert unrelated.exists()

    def test_no_commit_leaves_changes_unstaged(self, git_registry):
        result = self._run_edit(git_registry, ["--no-commit"])
        assert result == 0

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        # File should appear as modified but not staged
        assert "proj-abc12345.yml" in status.stdout

    def test_registry_without_git_edits_successfully(self, temp_registry, capsys):
        """Edit should succeed and warn gracefully when no git repo exists."""
        from hxc.cli import main

        with patch(
            "hxc.commands.registry.RegistryCommand.get_registry_path",
            return_value=str(temp_registry),
        ):
            result = main(["edit", "P-GIT", "--set-title", "No Git Title"])

        assert result == 0
        out = capsys.readouterr().out
        assert "not inside a git repository" in out

        # File was still updated
        proj_file = temp_registry / "projects" / "proj-abc12345.yml"
        with open(proj_file) as f:
            data = yaml.safe_load(f)
        assert data["title"] == "No Git Title"
