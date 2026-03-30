"""
Tests for the git utility module.
"""
import subprocess
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from hxc.utils.git import (
    find_git_root,
    git_available,
    parse_commit_hash,
    summarise_changes,
    _build_create_commit_message,
    _build_edit_commit_message,
    _build_delete_commit_message,
    commit_entity_change,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory without git."""
    test_dir = tmp_path / "test_dir"
    test_dir.mkdir(parents=True)
    yield test_dir
    if test_dir.exists():
        shutil.rmtree(test_dir)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository."""
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
    (repo_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "."], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path, check=True, capture_output=True
    )
    
    yield repo_path
    
    if repo_path.exists():
        shutil.rmtree(repo_path)


@pytest.fixture
def sample_entity_data():
    """Sample entity data for testing."""
    return {
        "type": "project",
        "uid": "abc12345",
        "id": "P-001",
        "title": "Test Project",
        "status": "active",
        "category": "software.dev/cli-tool",
    }


# ─── find_git_root Tests ─────────────────────────────────────────────────────


class TestFindGitRoot:
    def test_finds_root_when_in_git_repo(self, git_repo):
        result = find_git_root(str(git_repo))
        assert result == str(git_repo)

    def test_finds_root_from_subdirectory(self, git_repo):
        subdir = git_repo / "subdir" / "nested"
        subdir.mkdir(parents=True)
        
        result = find_git_root(str(subdir))
        assert result == str(git_repo)

    def test_returns_none_when_not_in_git_repo(self, temp_dir):
        result = find_git_root(str(temp_dir))
        assert result is None

    def test_returns_none_for_nonexistent_path(self, tmp_path):
        nonexistent = tmp_path / "does_not_exist"
        result = find_git_root(str(nonexistent))
        assert result is None

    def test_handles_deeply_nested_subdirectory(self, git_repo):
        deep_path = git_repo / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        
        result = find_git_root(str(deep_path))
        assert result == str(git_repo)


# ─── git_available Tests ─────────────────────────────────────────────────────


class TestGitAvailable:
    def test_returns_true_when_git_is_installed(self):
        # This test assumes git is installed on the test machine
        assert git_available() is True

    def test_returns_false_when_git_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert git_available() is False

    def test_returns_false_on_nonzero_exit_code(self):
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")):
            assert git_available() is False


# ─── parse_commit_hash Tests ─────────────────────────────────────────────────


class TestParseCommitHash:
    def test_parses_standard_branch_output(self):
        output = "[main abc1234] Create proj-xxx: Test Project"
        assert parse_commit_hash(output) == "abc1234"

    def test_parses_feature_branch_output(self):
        output = "[feature/test def5678] Edit proj-xxx: Updated title"
        assert parse_commit_hash(output) == "def5678"

    def test_parses_detached_head_output(self):
        output = "[HEAD detached at 1234567] Delete proj-xxx: Removed"
        assert parse_commit_hash(output) == "1234567"

    def test_parses_longer_hash(self):
        output = "[main abcdef123456] Some commit message"
        assert parse_commit_hash(output) == "abcdef123456"

    def test_returns_none_for_invalid_output(self):
        assert parse_commit_hash("not a valid git output") is None

    def test_returns_none_for_empty_string(self):
        assert parse_commit_hash("") is None

    def test_returns_none_for_output_without_hash(self):
        assert parse_commit_hash("[main] No hash here") is None


# ─── summarise_changes Tests ─────────────────────────────────────────────────


class TestSummariseChanges:
    def test_empty_list_returns_no_changes(self):
        assert summarise_changes([]) == "no changes"

    def test_single_change_returned_as_is(self):
        changes = ["Set title: 'Old' → 'New'"]
        assert summarise_changes(changes) == "Set title: 'Old' → 'New'"

    def test_single_long_change_is_truncated(self):
        long_change = "A" * 100
        result = summarise_changes([long_change])
        assert len(result) <= 72
        assert result.endswith("...")

    def test_multiple_changes_shows_count(self):
        changes = [
            "Set title: 'A' → 'B'",
            "Added tag: 'python'",
            "Removed child: 'uid-1'",
        ]
        result = summarise_changes(changes)
        assert "Set title" in result
        assert "2 more change(s)" in result

    def test_two_changes_shows_one_more(self):
        changes = ["Set title: 'A' → 'B'", "Added tag: 'test'"]
        result = summarise_changes(changes)
        assert "1 more change(s)" in result

    def test_custom_max_length(self):
        changes = ["A very long change description that exceeds the limit"]
        result = summarise_changes(changes, max_length=30)
        assert len(result) <= 30

    def test_extracts_first_part_before_colon(self):
        changes = [
            "Set description: 'old desc' → 'new desc'",
            "Another change",
        ]
        result = summarise_changes(changes)
        assert "Set description" in result


# ─── _build_create_commit_message Tests ──────────────────────────────────────


class TestBuildCreateCommitMessage:
    def test_includes_file_stem_in_subject(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_create_commit_message(file_path, sample_entity_data)
        
        assert "Create proj-abc12345" in message

    def test_includes_title_in_subject(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_create_commit_message(file_path, sample_entity_data)
        
        assert "Test Project" in message

    def test_includes_entity_type_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_create_commit_message(file_path, sample_entity_data)
        
        assert "Entity type: project" in message

    def test_includes_entity_id_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_create_commit_message(file_path, sample_entity_data)
        
        assert "Entity ID: P-001" in message

    def test_includes_entity_uid_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_create_commit_message(file_path, sample_entity_data)
        
        assert "Entity UID: abc12345" in message

    def test_includes_category_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_create_commit_message(file_path, sample_entity_data)
        
        assert "Category: software.dev/cli-tool" in message

    def test_includes_status_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_create_commit_message(file_path, sample_entity_data)
        
        assert "Status: active" in message

    def test_handles_missing_optional_fields(self):
        minimal_data = {"type": "project", "title": "Minimal"}
        file_path = Path("/registry/projects/proj-xyz.yml")
        message = _build_create_commit_message(file_path, minimal_data)
        
        assert "Create proj-xyz" in message
        assert "Minimal" in message
        assert "(not set)" in message


# ─── _build_edit_commit_message Tests ────────────────────────────────────────


class TestBuildEditCommitMessage:
    def test_includes_file_stem_in_subject(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        changes = ["Set title: 'Old' → 'New'"]
        message = _build_edit_commit_message(file_path, sample_entity_data, changes)
        
        assert "Edit proj-abc12345" in message

    def test_includes_change_summary_in_subject(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        changes = ["Set title: 'Old' → 'New'"]
        message = _build_edit_commit_message(file_path, sample_entity_data, changes)
        
        assert "Set title" in message

    def test_lists_all_changes_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        changes = [
            "Set title: 'Old' → 'New'",
            "Added tag: 'python'",
            "Removed child: 'uid-1'",
        ]
        message = _build_edit_commit_message(file_path, sample_entity_data, changes)
        
        for change in changes:
            assert f"- {change}" in message

    def test_handles_empty_changes_list(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_edit_commit_message(file_path, sample_entity_data, [])
        
        assert "Edit proj-abc12345" in message
        assert "no changes" in message


# ─── _build_delete_commit_message Tests ──────────────────────────────────────


class TestBuildDeleteCommitMessage:
    def test_includes_file_stem_in_subject(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_delete_commit_message(file_path, sample_entity_data)
        
        assert "Delete proj-abc12345" in message

    def test_includes_title_in_subject(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_delete_commit_message(file_path, sample_entity_data)
        
        assert "Test Project" in message

    def test_includes_entity_type_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_delete_commit_message(file_path, sample_entity_data)
        
        assert "Entity type: project" in message

    def test_includes_entity_id_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_delete_commit_message(file_path, sample_entity_data)
        
        assert "Entity ID: P-001" in message

    def test_includes_entity_uid_in_body(self, sample_entity_data):
        file_path = Path("/registry/projects/proj-abc12345.yml")
        message = _build_delete_commit_message(file_path, sample_entity_data)
        
        assert "Entity UID: abc12345" in message

    def test_handles_missing_fields(self):
        minimal_data = {"title": "Deleted Entity"}
        file_path = Path("/registry/projects/proj-xyz.yml")
        message = _build_delete_commit_message(file_path, minimal_data)
        
        assert "Delete proj-xyz" in message
        assert "Deleted Entity" in message


# ─── commit_entity_change Tests (Unit with Mocks) ────────────────────────────


class TestCommitEntityChangeUnit:
    def test_returns_false_when_not_in_git_repo(self, temp_dir, sample_entity_data, capsys):
        file_path = temp_dir / "proj-abc12345.yml"
        file_path.write_text("test")
        
        result = commit_entity_change(
            registry_path=str(temp_dir),
            file_path=file_path,
            action="Create",
            entity_data=sample_entity_data,
        )
        
        assert result is False
        out = capsys.readouterr().out
        assert "not inside a git repository" in out

    def test_returns_false_when_git_not_available(self, git_repo, sample_entity_data, capsys):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test")
        
        with patch("hxc.utils.git.git_available", return_value=False):
            result = commit_entity_change(
                registry_path=str(git_repo),
                file_path=file_path,
                action="Create",
                entity_data=sample_entity_data,
            )
        
        assert result is False
        out = capsys.readouterr().out
        assert "git is not installed" in out

    def test_stages_the_file_for_create(self, git_repo, sample_entity_data):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test"
        mock_result.stderr = ""
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=sample_entity_data,
                )
        
        calls = mock_run.call_args_list
        add_call = calls[0]
        assert add_call[0][0] == ["git", "add", str(file_path)]

    def test_creates_commit_with_message(self, git_repo, sample_entity_data):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test"
        mock_result.stderr = ""
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=sample_entity_data,
                )
        
        calls = mock_run.call_args_list
        commit_call = calls[1]
        assert commit_call[0][0][0:2] == ["git", "commit"]
        assert "-m" in commit_call[0][0]

    def test_returns_true_on_success(self, git_repo, sample_entity_data):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test"
        mock_result.stderr = ""
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                result = commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=sample_entity_data,
                )
        
        assert result is True

    def test_prints_commit_hash_on_success(self, git_repo, sample_entity_data, capsys):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test"
        mock_result.stderr = ""
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result):
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=sample_entity_data,
                )
        
        out = capsys.readouterr().out
        assert "committed to git" in out
        assert "abc1234" in out

    def test_handles_nothing_to_commit(self, git_repo, sample_entity_data, capsys):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        error = subprocess.CalledProcessError(1, "git")
        error.stdout = "nothing to commit"
        error.stderr = ""
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", side_effect=[MagicMock(), error]):
                result = commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=sample_entity_data,
                )
        
        assert result is False
        out = capsys.readouterr().out
        assert "Nothing new to commit" in out

    def test_handles_git_error_gracefully(self, git_repo, sample_entity_data, capsys):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: some error"
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", side_effect=[MagicMock(), error]):
                result = commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=sample_entity_data,
                )
        
        assert result is False
        out = capsys.readouterr().out
        assert "git commit failed" in out

    def test_edit_action_includes_changes_in_message(self, git_repo, sample_entity_data):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        changes = ["Set title: 'Old' → 'New'", "Added tag: 'test'"]
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Edit proj-abc12345: Set title"
        mock_result.stderr = ""
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Edit",
                    entity_data=sample_entity_data,
                    changes=changes,
                )
        
        calls = mock_run.call_args_list
        commit_call = calls[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        
        for change in changes:
            assert change in commit_msg

    def test_delete_action_message_format(self, git_repo, sample_entity_data):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Delete proj-abc12345: Test Project"
        mock_result.stderr = ""
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Delete",
                    entity_data=sample_entity_data,
                )
        
        calls = mock_run.call_args_list
        commit_call = calls[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        
        assert "Delete proj-abc12345" in commit_msg

    def test_error_message_mentions_create_action(self, git_repo, sample_entity_data, capsys):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: error"
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", side_effect=[MagicMock(), error]):
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Create",
                    entity_data=sample_entity_data,
                )
        
        out = capsys.readouterr().out
        assert "File was created but not committed" in out

    def test_error_message_mentions_edit_action(self, git_repo, sample_entity_data, capsys):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: error"
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", side_effect=[MagicMock(), error]):
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Edit",
                    entity_data=sample_entity_data,
                    changes=["Set title"],
                )
        
        out = capsys.readouterr().out
        assert "Edit was saved but not committed" in out

    def test_error_message_mentions_delete_action(self, git_repo, sample_entity_data, capsys):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("test content")
        
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: error"
        
        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", side_effect=[MagicMock(), error]):
                commit_entity_change(
                    registry_path=str(git_repo),
                    file_path=file_path,
                    action="Delete",
                    entity_data=sample_entity_data,
                )
        
        out = capsys.readouterr().out
        assert "File was deleted but not committed" in out


# ─── Integration Tests (Real Git Operations) ─────────────────────────────────


class TestCommitEntityChangeIntegration:
    def test_create_commit_appears_in_git_log(self, git_repo, sample_entity_data):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("type: project\ntitle: Test Project")
        
        result = commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Create",
            entity_data=sample_entity_data,
        )
        
        assert result is True
        
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "proj-abc12345" in log.stdout

    def test_edit_commit_contains_changes(self, git_repo, sample_entity_data):
        # First create the file and commit
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("type: project\ntitle: Test Project")
        subprocess.run(["git", "add", str(file_path)], cwd=git_repo, check=True)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=git_repo, check=True)
        
        # Now modify and commit via our function
        file_path.write_text("type: project\ntitle: Updated Project")
        changes = ["Set title: 'Test Project' → 'Updated Project'"]
        
        result = commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Edit",
            entity_data=sample_entity_data,
            changes=changes,
        )
        
        assert result is True
        
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Set title" in log.stdout

    def test_only_specified_file_is_committed(self, git_repo, sample_entity_data):
        # Create an unrelated file
        unrelated = git_repo / "unrelated.txt"
        unrelated.write_text("should not be committed")
        
        # Create the entity file
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("type: project\ntitle: Test Project")
        
        commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Create",
            entity_data=sample_entity_data,
        )
        
        # Check what files were in the commit
        show = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        
        committed_files = show.stdout.strip().splitlines()
        assert any("proj-abc12345.yml" in f for f in committed_files)
        assert not any("unrelated.txt" in f for f in committed_files)

    def test_commit_message_has_correct_format(self, git_repo, sample_entity_data):
        file_path = git_repo / "proj-abc12345.yml"
        file_path.write_text("type: project\ntitle: Test Project")
        
        commit_entity_change(
            registry_path=str(git_repo),
            file_path=file_path,
            action="Create",
            entity_data=sample_entity_data,
        )
        
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        
        message = log.stdout
        assert "Create proj-abc12345: Test Project" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: abc12345" in message

    def test_multiple_commits_create_separate_entries(self, git_repo, sample_entity_data):
        # Create first entity
        file1 = git_repo / "proj-111.yml"
        file1.write_text("type: project\ntitle: First")
        entity1 = {**sample_entity_data, "uid": "111", "title": "First"}
        
        commit_entity_change(
            registry_path=str(git_repo),
            file_path=file1,
            action="Create",
            entity_data=entity1,
        )
        
        # Create second entity
        file2 = git_repo / "proj-222.yml"
        file2.write_text("type: project\ntitle: Second")
        entity2 = {**sample_entity_data, "uid": "222", "title": "Second"}
        
        commit_entity_change(
            registry_path=str(git_repo),
            file_path=file2,
            action="Create",
            entity_data=entity2,
        )
        
        # Check git log has both commits
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        
        assert "proj-111" in log.stdout
        assert "proj-222" in log.stdout

    def test_works_from_subdirectory(self, git_repo, sample_entity_data):
        # Create subdirectory structure
        projects_dir = git_repo / "projects"
        projects_dir.mkdir()
        
        file_path = projects_dir / "proj-abc12345.yml"
        file_path.write_text("type: project\ntitle: Test Project")
        
        # Commit from the subdirectory path
        result = commit_entity_change(
            registry_path=str(projects_dir),
            file_path=file_path,
            action="Create",
            entity_data=sample_entity_data,
        )
        
        assert result is True
        
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_repo,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "proj-abc12345" in log.stdout