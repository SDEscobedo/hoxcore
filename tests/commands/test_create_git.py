"""
Tests for the git commit functionality added to the create command.
"""
import os
import subprocess
import yaml
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from hxc.commands.create import CreateCommand
from hxc.utils.git import (
    find_git_root,
    git_available,
    parse_commit_hash,
    summarize_changes,
    build_commit_message,
    commit_entity_change,
    GitOperationResult,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def temp_registry(tmp_path):
    """Minimal registry used by git-commit tests."""
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)

    for folder in ("programs", "projects", "missions", "actions"):
        (registry_path / folder).mkdir()

    (registry_path / ".hxc").mkdir()
    (registry_path / "config.yml").write_text("# Test config")

    yield registry_path

    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def git_registry(temp_registry):
    """Registry that is also a proper git repository."""
    subprocess.run(["git", "init"], cwd=temp_registry, check=True,
                   capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"],
                   cwd=temp_registry, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"],
                   cwd=temp_registry, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=temp_registry, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"],
                   cwd=temp_registry, check=True, capture_output=True)
    return temp_registry


# ─── Unit Tests for Shared Git Utilities ─────────────────────────────────────


class TestFindGitRoot:
    def test_finds_root_when_git_repo(self, git_registry):
        root = find_git_root(str(git_registry))
        assert root == str(git_registry)

    def test_finds_root_from_subdir(self, git_registry):
        subdir = git_registry / "projects"
        root = find_git_root(str(subdir))
        assert root == str(git_registry)

    def test_returns_none_when_not_git(self, temp_registry):
        root = find_git_root(str(temp_registry))
        assert root is None

    def test_returns_none_for_filesystem_root(self, tmp_path):
        isolated = tmp_path / "no_git"
        isolated.mkdir()
        root = find_git_root(str(isolated))
        assert root is None


class TestGitAvailable:
    def test_returns_true_when_git_present(self):
        assert git_available() is True

    def test_returns_false_when_git_missing(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert git_available() is False

    def test_returns_false_on_nonzero_exit(self):
        with patch("subprocess.run",
                   side_effect=subprocess.CalledProcessError(1, "git")):
            assert git_available() is False


class TestParseCommitHash:
    def test_parses_standard_output(self):
        output = "[main abc1234] Create proj-xxx: New Project"
        assert parse_commit_hash(output) == "abc1234"

    def test_parses_detached_head(self):
        output = "[HEAD detached at def5678] Create proj-xxx: ..."
        assert parse_commit_hash(output) == "def5678"

    def test_returns_none_for_unexpected_output(self):
        assert parse_commit_hash("nothing useful here") is None

    def test_returns_none_for_empty_string(self):
        assert parse_commit_hash("") is None


class TestSummarizeChanges:
    def test_empty_list(self):
        assert summarize_changes([]) == "no changes"

    def test_single_change(self):
        result = summarize_changes(["Created new project"])
        assert result == "Created new project"

    def test_single_long_change_is_truncated(self):
        long = "A" * 100
        result = summarize_changes([long])
        assert len(result) <= 72

    def test_multiple_changes(self):
        changes = [
            "Added title",
            "Added category",
            "Added tags",
        ]
        result = summarize_changes(changes)
        assert "Added title" in result
        assert "2 more change" in result


class TestBuildCommitMessage:
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

    def test_create_action_with_category(self):
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


class TestCommitEntityChange:
    """Unit tests for commit_entity_change using mocks."""

    def _entity(self, uid="abc12345", etype="project"):
        return {
            "type": etype,
            "uid": uid,
            "id": "P-001",
            "title": "Test Project",
            "status": "active",
        }

    def test_returns_error_when_not_git_repo(self, temp_registry):
        file_path = temp_registry / "projects" / "proj-abc12345.yml"
        result = commit_entity_change(
            registry_path=str(temp_registry),
            file_path=file_path,
            action="Create",
            entity_data=self._entity(),
        )
        
        assert result.success is False
        assert "not inside a git repository" in result.error

    def test_returns_error_when_git_not_installed(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        with patch("hxc.utils.git.git_available", return_value=False):
            result = commit_entity_change(
                registry_path=str(git_registry),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )
        
        assert result.success is False
        assert "git is not installed" in result.error

    def test_stages_only_the_created_file(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        # Create the file
        file_path.write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    action="Create",
                    entity_data=self._entity(),
                )

        calls = mock_run.call_args_list
        add_call = calls[0]
        assert add_call[0][0] == ["git", "add", str(file_path)]

    def test_commit_message_contains_filename_stem(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    action="Create",
                    entity_data=self._entity(),
                )

        commit_call = mock_run.call_args_list[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        assert "proj-abc12345" in commit_msg

    def test_returns_commit_hash_on_success(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Create proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = commit_entity_change(
                registry_path=str(git_registry),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is True
        assert result.commit_hash == "abc1234"

    def test_handles_nothing_to_commit_gracefully(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        error = subprocess.CalledProcessError(1, "git")
        error.stdout = "nothing to commit"
        error.stderr = ""

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = commit_entity_change(
                registry_path=str(git_registry),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is False
        assert "Nothing new to commit" in result.error

    def test_handles_generic_git_error_gracefully(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.write_text("test: data")
        
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: not a git repository"

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = commit_entity_change(
                registry_path=str(git_registry),
                file_path=file_path,
                action="Create",
                entity_data=self._entity(),
            )

        assert result.success is False
        assert "not a git repository" in result.error


# ─── Integration: --no-commit flag ───────────────────────────────────────────


class TestNoCommitFlag:
    """Tests that --no-commit prevents git operations."""

    def _run_create(self, registry_path, extra_args=None):
        """Helper: invoke CreateCommand.execute via hxc.cli.main."""
        from hxc.cli import main
        args = ["create", "project", "Test Project"]
        if extra_args:
            args.extend(extra_args)
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(registry_path)):
            with patch("uuid.uuid4", return_value="12345678-1234-5678-1234-567812345678"):
                return main(args)

    def test_no_commit_flag_prevents_git_call(self, git_registry):
        with patch("hxc.commands.create.commit_entity_change") as mock_commit:
            result = self._run_create(git_registry, ["--no-commit"])
        assert result == 0
        mock_commit.assert_not_called()

    def test_no_commit_flag_prints_warning(self, git_registry, capsys):
        result = self._run_create(git_registry, ["--no-commit"])
        assert result == 0
        out = capsys.readouterr().out
        assert "--no-commit" in out

    def test_without_no_commit_flag_calls_commit(self, git_registry):
        with patch("hxc.commands.create.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(
                success=True,
                commit_hash="abc1234",
                message="Create proj-12345678: Test Project"
            )
            result = self._run_create(git_registry)
        assert result == 0
        mock_commit.assert_called_once()

    def test_create_file_exists_even_with_no_commit(self, git_registry):
        result = self._run_create(git_registry, ["--no-commit"])
        assert result == 0
        
        project_file = git_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()


# ─── Integration: real git commit ────────────────────────────────────────────


class TestRealGitCommit:
    """End-to-end tests that actually run git."""

    def _run_create(self, registry_path, args=None):
        from hxc.cli import main
        cmd = ["create", "project", "Real Git Project"]
        if args:
            cmd.extend(args)
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(registry_path)):
            with patch("uuid.uuid4", return_value="gittest1-1234-5678-1234-567812345678"):
                return main(cmd)

    def test_commit_is_created_in_git_log(self, git_registry):
        result = self._run_create(git_registry)
        assert result == 0

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "proj-gittest1" in log.stdout

    def test_commit_message_contains_entity_title(self, git_registry):
        result = self._run_create(git_registry)
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Real Git Project" in log.stdout

    def test_commit_message_contains_entity_metadata(self, git_registry):
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("uuid.uuid4", return_value="metadata1-1234-5678-1234-567812345678"):
                result = main([
                    "create", "project", "Metadata Test Project",
                    "--id", "P-META",
                    "--category", "software.dev/test",
                    "--status", "planned",
                ])
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Entity type: project" in log.stdout
        assert "Entity ID: P-META" in log.stdout
        assert "Category: software.dev/test" in log.stdout
        assert "Status: planned" in log.stdout

    def test_only_entity_file_is_in_commit(self, git_registry):
        # Create an unrelated unstaged file
        unrelated = git_registry / "unrelated.txt"
        unrelated.write_text("do not commit me")

        result = self._run_create(git_registry)
        assert result == 0

        show = subprocess.run(
            ["git", "show", "--name-only", "--format="],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        committed_files = show.stdout.strip().splitlines()
        assert any("proj-gittest1.yml" in f for f in committed_files)
        assert not any("unrelated.txt" in f for f in committed_files)
        # Unrelated file should still exist and be untracked
        assert unrelated.exists()

    def test_no_commit_leaves_file_unstaged(self, git_registry):
        result = self._run_create(git_registry, ["--no-commit"])
        assert result == 0

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        # File should appear as untracked (either directly or via the projects/ folder)
        assert "proj-gittest1.yml" in status.stdout or "projects/" in status.stdout

    def test_registry_without_git_creates_successfully(self, temp_registry, capsys):
        """Create should succeed and warn gracefully when no git repo exists."""
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(temp_registry)):
            with patch("uuid.uuid4", return_value="nogit123-1234-5678-1234-567812345678"):
                result = main(["create", "project", "No Git Project"])

        assert result == 0
        out = capsys.readouterr().out
        assert "not inside a git repository" in out

        # File was still created
        proj_file = temp_registry / "projects" / "proj-nogit123.yml"
        assert proj_file.exists()
        
        with open(proj_file) as f:
            data = yaml.safe_load(f)
        assert data["title"] == "No Git Project"

    def test_multiple_creates_produce_individual_commits(self, git_registry):
        """Each create should produce its own commit."""
        from hxc.cli import main
        
        for i, title in enumerate(["First Project", "Second Project", "Third Project"]):
            with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                       return_value=str(git_registry)):
                with patch("uuid.uuid4", return_value=f"multi{i:03d}1-1234-5678-1234-567812345678"):
                    result = main(["create", "project", title])
            assert result == 0

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        
        # Should have 4 commits: initial + 3 creates
        commits = [line for line in log.stdout.strip().splitlines() if line]
        assert len(commits) >= 4
        
        # Each project should appear in log
        assert "First Project" in log.stdout
        assert "Second Project" in log.stdout
        assert "Third Project" in log.stdout


class TestAllEntityTypesGitCommit:
    """Test git commits work for all entity types."""

    def test_program_commit(self, git_registry):
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("uuid.uuid4", return_value="progtes1-1234-5678-1234-567812345678"):
                result = main(["create", "program", "Test Program"])
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "prog-progtes1" in log.stdout
        assert "Entity type: program" in log.stdout

    def test_mission_commit(self, git_registry):
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("uuid.uuid4", return_value="misstes1-1234-5678-1234-567812345678"):
                result = main(["create", "mission", "Test Mission"])
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "miss-misstes1" in log.stdout
        assert "Entity type: mission" in log.stdout

    def test_action_commit(self, git_registry):
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("uuid.uuid4", return_value="acttest1-1234-5678-1234-567812345678"):
                result = main(["create", "action", "Test Action"])
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "act-acttest1" in log.stdout
        assert "Entity type: action" in log.stdout


class TestGitCommitErrorHandling:
    """Test error handling scenarios for git operations."""

    def test_git_error_does_not_fail_create(self, git_registry, capsys):
        """If git commit fails, the file should still be created."""
        from hxc.cli import main
        
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("uuid.uuid4", return_value="giterror-1234-5678-1234-567812345678"):
                # Patch commit to fail after file creation
                with patch("hxc.commands.create.commit_entity_change") as mock_commit:
                    mock_commit.return_value = GitOperationResult(
                        success=False,
                        error="Simulated git error"
                    )
                    result = main(["create", "project", "Git Error Project"])
        
        # Create should still succeed
        assert result == 0
        
        # File should exist
        proj_file = git_registry / "projects" / "proj-giterror.yml"
        assert proj_file.exists()
        
        # Warning should be printed
        out = capsys.readouterr().out
        assert "Created project" in out

    def test_commit_success_prints_hash(self, git_registry, capsys):
        """Successful commit should display the commit hash."""
        from hxc.cli import main
        
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("uuid.uuid4", return_value="hashtest-1234-5678-1234-567812345678"):
                result = main(["create", "project", "Hash Test Project"])
        
        assert result == 0
        out = capsys.readouterr().out
        assert "committed to git" in out
        # The output should contain a commit hash in parentheses
        assert "(" in out and ")" in out