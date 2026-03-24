"""
Tests for the shared git utilities module.
"""
import subprocess
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from hxc.utils.git import (
    GitOperationResult,
    find_git_root,
    git_available,
    parse_commit_hash,
    summarize_changes,
    build_commit_message,
    commit_entity_change,
    print_commit_result,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir(parents=True)
    yield test_dir
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing."""
    repo_path = tmp_path / "git_repo"
    repo_path.mkdir(parents=True)
    
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path, check=True, capture_output=True
    )
    
    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repository")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path, check=True, capture_output=True
    )
    
    yield repo_path
    
    if repo_path.exists():
        shutil.rmtree(repo_path)


# ─── GitOperationResult Tests ────────────────────────────────────────────────


class TestGitOperationResult:
    """Tests for the GitOperationResult class."""

    def test_success_result(self):
        result = GitOperationResult(
            success=True,
            commit_hash="abc1234",
            message="Test commit message",
        )
        assert result.success is True
        assert result.commit_hash == "abc1234"
        assert result.message == "Test commit message"
        assert result.error is None

    def test_failure_result(self):
        result = GitOperationResult(
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.commit_hash is None
        assert result.message is None
        assert result.error == "Something went wrong"

    def test_partial_success_result(self):
        result = GitOperationResult(
            success=True,
            message="Partial success",
        )
        assert result.success is True
        assert result.commit_hash is None
        assert result.message == "Partial success"
        assert result.error is None

    def test_all_fields_populated(self):
        result = GitOperationResult(
            success=False,
            commit_hash="def5678",
            message="Attempted message",
            error="But failed",
        )
        assert result.success is False
        assert result.commit_hash == "def5678"
        assert result.message == "Attempted message"
        assert result.error == "But failed"


# ─── find_git_root Tests ─────────────────────────────────────────────────────


class TestFindGitRoot:
    """Tests for the find_git_root function."""

    def test_finds_root_when_git_repo(self, git_repo):
        root = find_git_root(str(git_repo))
        assert root == str(git_repo)

    def test_finds_root_from_subdir(self, git_repo):
        subdir = git_repo / "subdir"
        subdir.mkdir()
        root = find_git_root(str(subdir))
        assert root == str(git_repo)

    def test_finds_root_from_nested_subdir(self, git_repo):
        nested = git_repo / "level1" / "level2" / "level3"
        nested.mkdir(parents=True)
        root = find_git_root(str(nested))
        assert root == str(git_repo)

    def test_returns_none_when_not_git(self, temp_dir):
        root = find_git_root(str(temp_dir))
        assert root is None

    def test_returns_none_for_isolated_directory(self, tmp_path):
        isolated = tmp_path / "no_git"
        isolated.mkdir()
        root = find_git_root(str(isolated))
        assert root is None

    def test_handles_nonexistent_path(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        # Path doesn't exist, but resolve should still work
        root = find_git_root(str(nonexistent))
        assert root is None


# ─── git_available Tests ─────────────────────────────────────────────────────


class TestGitAvailable:
    """Tests for the git_available function."""

    def test_returns_true_when_git_present(self):
        # This test assumes git is installed on the test system
        assert git_available() is True

    def test_returns_false_when_git_missing(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert git_available() is False

    def test_returns_false_on_nonzero_exit(self):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            assert git_available() is False

    def test_returns_false_on_permission_error(self):
        with patch("subprocess.run", side_effect=PermissionError):
            assert git_available() is False


# ─── parse_commit_hash Tests ─────────────────────────────────────────────────


class TestParseCommitHash:
    """Tests for the parse_commit_hash function."""

    def test_parses_standard_output(self):
        output = "[main abc1234] Create proj-xxx: New Project"
        assert parse_commit_hash(output) == "abc1234"

    def test_parses_detached_head(self):
        output = "[HEAD detached at def5678] Create proj-xxx: ..."
        assert parse_commit_hash(output) == "def5678"

    def test_parses_branch_with_slash(self):
        output = "[feature/test abc9999] Edit proj-xxx: ..."
        assert parse_commit_hash(output) == "abc9999"

    def test_parses_longer_hash(self):
        output = "[main abcdef1234567890] Full hash commit"
        assert parse_commit_hash(output) == "abcdef1234567890"

    def test_returns_none_for_unexpected_output(self):
        assert parse_commit_hash("nothing useful here") is None

    def test_returns_none_for_empty_string(self):
        assert parse_commit_hash("") is None

    def test_returns_none_for_malformed_bracket(self):
        assert parse_commit_hash("[main] no hash here") is None

    def test_returns_none_for_short_hash(self):
        # Hash must be at least 5 characters
        assert parse_commit_hash("[main abc] too short") is None


# ─── summarize_changes Tests ─────────────────────────────────────────────────


class TestSummarizeChanges:
    """Tests for the summarize_changes function."""

    def test_empty_list(self):
        assert summarize_changes([]) == "no changes"

    def test_single_change(self):
        result = summarize_changes(["Created new project"])
        assert result == "Created new project"

    def test_single_long_change_is_truncated(self):
        long_change = "A" * 100
        result = summarize_changes([long_change])
        assert len(result) <= 72
        assert result.endswith("...")

    def test_single_change_at_max_length(self):
        exact_length = "B" * 72
        result = summarize_changes([exact_length])
        assert result == exact_length
        assert not result.endswith("...")

    def test_multiple_changes(self):
        changes = [
            "Added title",
            "Added category",
            "Added tags",
        ]
        result = summarize_changes(changes)
        assert "Added title" in result
        assert "2 more change" in result

    def test_two_changes(self):
        changes = ["First change", "Second change"]
        result = summarize_changes(changes)
        assert "First change" in result
        assert "1 more change" in result

    def test_change_with_colon_extracts_prefix(self):
        changes = [
            "Set title: 'Old' → 'New'",
            "Added tag: 'python'",
        ]
        result = summarize_changes(changes)
        assert "Set title" in result
        assert "1 more change" in result

    def test_custom_max_length(self):
        long_change = "C" * 50
        result = summarize_changes([long_change], max_length=40)
        assert len(result) <= 40
        assert result.endswith("...")


# ─── build_commit_message Tests ──────────────────────────────────────────────


class TestBuildCommitMessage:
    """Tests for the build_commit_message function."""

    def test_create_action_basic(self):
        entity_data = {
            "type": "project",
            "uid": "abc12345",
            "id": "P-001",
            "title": "Test Project",
        }
        message = build_commit_message("Create", "proj-abc12345", entity_data)
        
        assert "Create proj-abc12345: Test Project" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: abc12345" in message

    def test_create_action_with_metadata(self):
        entity_data = {
            "type": "project",
            "uid": "abc12345",
            "id": "P-001",
            "title": "Test Project",
            "category": "software.dev/cli-tool",
            "status": "active",
            "start_date": "2024-01-15",
        }
        message = build_commit_message("Create", "proj-abc12345", entity_data)
        
        assert "Category: software.dev/cli-tool" in message
        assert "Status: active" in message
        assert "Created: 2024-01-15" in message

    def test_edit_action_with_changes(self):
        entity_data = {
            "type": "project",
            "uid": "abc12345",
            "title": "Test Project",
        }
        changes = ["Set title: 'Old' → 'New'", "Added tag: 'python'"]
        message = build_commit_message("Edit", "proj-abc12345", entity_data, changes)
        
        assert "Edit proj-abc12345" in message
        for change in changes:
            assert change in message

    def test_delete_action(self):
        entity_data = {
            "type": "project",
            "uid": "abc12345",
            "id": "P-001",
            "title": "Test Project",
        }
        message = build_commit_message("Delete", "proj-abc12345", entity_data)
        
        assert "Delete proj-abc12345: Test Project" in message
        assert "Entity type: project" in message

    def test_missing_title_uses_default(self):
        entity_data = {
            "type": "action",
            "uid": "def67890",
        }
        message = build_commit_message("Create", "act-def67890", entity_data)
        
        assert "Create act-def67890: Untitled" in message

    def test_missing_id_not_included(self):
        entity_data = {
            "type": "mission",
            "uid": "miss1234",
            "title": "Test Mission",
        }
        message = build_commit_message("Create", "miss-miss1234", entity_data)
        
        assert "Entity type: mission" in message
        assert "Entity ID:" not in message

    def test_all_entity_types(self):
        entity_types = ["program", "project", "mission", "action"]
        file_prefixes = ["prog", "proj", "miss", "act"]
        
        for etype, prefix in zip(entity_types, file_prefixes):
            entity_data = {
                "type": etype,
                "uid": "test1234",
                "title": f"Test {etype.title()}",
            }
            message = build_commit_message("Create", f"{prefix}-test1234", entity_data)
            
            assert f"Create {prefix}-test1234" in message
            assert f"Entity type: {etype}" in message


# ─── commit_entity_change Tests ──────────────────────────────────────────────


class TestCommitEntityChange:
    """Tests for the commit_entity_change function."""

    @staticmethod
    def _entity(uid="abc12345", etype="project"):
        return {
            "type": etype,
            "uid": uid,
            "id": "P-001",
            "title": "Test Project",
            "status": "active",
        }

    def test_returns_error_when_not_git_repo(self, temp_dir):
        file_path = temp_dir / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        result = commit_entity_change(
            registry_path=str(temp_dir),
            file_path=file_path,
            action="Create",
            entity_data=self._entity(),
        )
        
        assert result.success is False
        assert "not inside a git repository" in result.error

    def test_returns_error_when_git_not_installed(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        with patch("hxc.utils.git.git_available", return_value=False):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )
        
        assert result.success is False
        assert "git is not installed" in result.error

    def test_stages_the_file(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=self._entity(),
                )

        calls = mock_run.call_args_list
        add_call = calls[0]
        assert add_call[0][0] == ["git", "add", str(file_path)]

    def test_commit_message_contains_action(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=self._entity(),
                )

        commit_call = mock_run.call_args_list[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        assert "Create proj-abc12345" in commit_msg

    def test_returns_commit_hash_on_success(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is True
        assert result.commit_hash == "abc1234"

    def test_handles_nothing_to_commit(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        error = subprocess.CalledProcessError(1, "git")
        error.stdout = "nothing to commit"
        error.stderr = ""

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is False
        assert "Nothing new to commit" in result.error

    def test_handles_nothing_to_commit_in_stderr(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        error = subprocess.CalledProcessError(1, "git")
        error.stdout = ""
        error.stderr = "nothing to commit, working tree clean"

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is False
        assert "Nothing new to commit" in result.error

    def test_handles_generic_git_error(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: some unexpected error"

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is False
        assert "some unexpected error" in result.error

    def test_edit_action_with_changes(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test: data")
        changes = ["Set title: 'Old' → 'New'"]
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Edit proj-abc12345: Set title"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Edit",
                    entity_data=self._entity(),
                    changes=changes,
                )

        commit_call = mock_run.call_args_list[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        assert "Edit proj-abc12345" in commit_msg
        assert "Set title" in commit_msg

    def test_delete_action(self, git_repo):
        file_path = git_repo / "proj-abc12345.yml"
        # File doesn't exist (simulating deletion)
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Delete proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Delete",
                    entity_data=self._entity(),
                )

        commit_call = mock_run.call_args_list[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        assert "Delete proj-abc12345" in commit_msg

    def test_handles_path_object(self, git_repo):
        file_path = Path(git_repo) / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is True

    def test_handles_string_path(self, git_repo):
        file_path = str(git_repo / "proj-abc12345.yml")
        Path(file_path).write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is True


# ─── print_commit_result Tests ───────────────────────────────────────────────


class TestPrintCommitResult:
    """Tests for the print_commit_result function."""

    def test_prints_no_commit_warning_when_flag_used(self, capsys):
        result = GitOperationResult(success=True)
        print_commit_result(result, no_commit_flag=True)
        
        out = capsys.readouterr().out
        assert "--no-commit" in out
        assert "not committed" in out

    def test_prints_success_with_hash(self, capsys):
        result = GitOperationResult(
            success=True,
            commit_hash="abc1234",
            message="Create proj-abc12345: Test Project",
        )
        print_commit_result(result, no_commit_flag=False)
        
        out = capsys.readouterr().out
        assert "committed to git" in out
        assert "abc1234" in out
        assert "Create proj-abc12345: Test Project" in out

    def test_prints_success_without_hash(self, capsys):
        result = GitOperationResult(
            success=True,
            message="Create proj-abc12345: Test Project",
        )
        print_commit_result(result, no_commit_flag=False)
        
        out = capsys.readouterr().out
        assert "committed to git" in out
        assert "Create proj-abc12345: Test Project" in out

    def test_prints_not_git_repo_error(self, capsys):
        result = GitOperationResult(
            success=False,
            error="Registry is not inside a git repository",
        )
        print_commit_result(result, no_commit_flag=False)
        
        out = capsys.readouterr().out
        assert "not inside a git repository" in out
        assert "not committed" in out

    def test_prints_git_not_installed_error(self, capsys):
        result = GitOperationResult(
            success=False,
            error="git is not installed or not on PATH",
        )
        print_commit_result(result, no_commit_flag=False)
        
        out = capsys.readouterr().out
        assert "git is not installed" in out
        assert "not committed" in out

    def test_prints_nothing_to_commit_error(self, capsys):
        result = GitOperationResult(
            success=False,
            error="Nothing new to commit (file may not have changed on disk)",
        )
        print_commit_result(result, no_commit_flag=False)
        
        out = capsys.readouterr().out
        assert "Nothing new to commit" in out

    def test_prints_generic_error(self, capsys):
        result = GitOperationResult(
            success=False,
            error="fatal: some unexpected git error",
        )
        print_commit_result(result, no_commit_flag=False)
        
        out = capsys.readouterr().out
        assert "git commit failed" in out
        assert "fatal: some unexpected git error" in out
        assert "not committed" in out


# ─── Integration Tests ───────────────────────────────────────────────────────


class TestRealGitOperations:
    """Integration tests using real git operations."""

    def test_real_commit_create(self, git_repo):
        """Test actual git commit for create operation."""
        file_path = git_repo / "proj-realtest.yml"
        file_path.write_text("type: project\nuid: realtest\ntitle: Real Test")
        
        entity_data = {
            "type": "project",
            "uid": "realtest",
            "id": "P-REAL",
            "title": "Real Test Project",
            "status": "active",
        }
        
        result = commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Create",
            entity_data=entity_data,
        )
        
        assert result.success is True
        assert result.commit_hash is not None
        
        # Verify in git log
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Create proj-realtest" in log.stdout
        assert "Real Test Project" in log.stdout

    def test_real_commit_delete(self, git_repo):
        """Test actual git commit for delete operation."""
        # Create and commit a file first
        file_path = git_repo / "proj-todelete.yml"
        file_path.write_text("type: project\nuid: todelete\ntitle: To Delete")
        subprocess.run(["git", "add", "."], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add file to delete"],
            cwd=git_repo, check=True, capture_output=True
        )
        
        # Now delete the file
        file_path.unlink()
        
        entity_data = {
            "type": "project",
            "uid": "todelete",
            "id": "P-DEL",
            "title": "To Delete Project",
        }
        
        result = commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Delete",
            entity_data=entity_data,
        )
        
        assert result.success is True
        
        # Verify in git log
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Delete proj-todelete" in log.stdout

    def test_only_specified_file_committed(self, git_repo):
        """Test that only the specified file is committed, not unrelated changes."""
        # Create an unrelated file
        unrelated = git_repo / "unrelated.txt"
        unrelated.write_text("do not commit me")
        
        # Create the entity file
        file_path = git_repo / "proj-specific.yml"
        file_path.write_text("type: project\nuid: specific\ntitle: Specific")
        
        entity_data = {
            "type": "project",
            "uid": "specific",
            "title": "Specific Project",
        }
        
        result = commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Create",
            entity_data=entity_data,
        )
        
        assert result.success is True
        
        # Check that unrelated file is not committed
        show = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        committed_files = show.stdout.strip().splitlines()
        assert any("proj-specific.yml" in f for f in committed_files)
        assert not any("unrelated.txt" in f for f in committed_files)
        
        # Verify unrelated file still exists and is untracked
        assert unrelated.exists()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "unrelated.txt" in status.stdout

    def test_commit_from_subdir(self, git_repo):
        """Test commit works when file is in a subdirectory."""
        subdir = git_repo / "projects"
        subdir.mkdir()
        
        file_path = subdir / "proj-subdir.yml"
        file_path.write_text("type: project\nuid: subdir\ntitle: Subdir Project")
        
        entity_data = {
            "type": "project",
            "uid": "subdir",
            "title": "Subdir Project",
        }
        
        result = commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Create",
            entity_data=entity_data,
        )
        
        assert result.success is True
        
        # Verify in git log
        show = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "projects/proj-subdir.yml" in show.stdout