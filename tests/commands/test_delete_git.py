"""
Tests for the git commit functionality added to the delete command.
"""
import os
import subprocess
import yaml
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from hxc.commands.delete import DeleteCommand
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

    # Create a test project for deletion tests
    project_data = {
        "type": "project",
        "uid": "abc12345",
        "id": "P-GIT",
        "title": "Git Test Project",
        "status": "active",
        "start_date": "2024-01-01",
        "tags": ["test"],
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


def _create_entity_file(registry_path, entity_type, uid, entity_id, title):
    """Helper to create an entity file for testing."""
    from hxc.core.enums import EntityType
    
    etype = EntityType.from_string(entity_type)
    folder = etype.get_folder_name()
    prefix = etype.get_file_prefix()
    
    entity_data = {
        "type": entity_type,
        "uid": uid,
        "id": entity_id,
        "title": title,
        "status": "active",
        "start_date": "2024-01-01",
    }
    
    file_path = registry_path / folder / f"{prefix}-{uid}.yml"
    with open(file_path, "w") as f:
        yaml.dump(entity_data, f)
    
    return file_path


# ─── Unit Tests for Commit Entity Change with Delete ─────────────────────────


class TestCommitEntityChangeDelete:
    """Unit tests for commit_entity_change with delete action using mocks."""

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
            action="Delete",
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
                action="Delete",
                entity_data=self._entity(),
            )
        
        assert result.success is False
        assert "git is not installed" in result.error

    def test_stages_the_deleted_file(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        # File should exist initially
        assert file_path.exists()
        # Delete the file (simulating what delete command does)
        file_path.unlink()
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Delete proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    action="Delete",
                    entity_data=self._entity(),
                )

        calls = mock_run.call_args_list
        add_call = calls[0]
        assert add_call[0][0] == ["git", "add", str(file_path)]

    def test_commit_message_contains_delete_action(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.unlink()
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Delete proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    action="Delete",
                    entity_data=self._entity(),
                )

        commit_call = mock_run.call_args_list[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        assert "Delete proj-abc12345" in commit_msg

    def test_commit_message_contains_entity_title(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.unlink()
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Delete proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("hxc.utils.git.git_available", return_value=True):
            with patch("subprocess.run", return_value=mock_result) as mock_run:
                commit_entity_change(
                    registry_path=str(git_registry),
                    file_path=file_path,
                    action="Delete",
                    entity_data=self._entity(),
                )

        commit_call = mock_run.call_args_list[1]
        commit_msg = commit_call[0][0][commit_call[0][0].index("-m") + 1]
        assert "Test Project" in commit_msg

    def test_returns_commit_hash_on_success(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.unlink()
        
        mock_result = MagicMock()
        mock_result.stdout = "[main abc1234] Delete proj-abc12345: Test Project"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = commit_entity_change(
                registry_path=str(git_registry),
                file_path=file_path,
                action="Delete",
                entity_data=self._entity(),
            )

        assert result.success is True
        assert result.commit_hash == "abc1234"

    def test_handles_nothing_to_commit_gracefully(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        # Don't actually delete - simulates nothing to commit
        
        error = subprocess.CalledProcessError(1, "git")
        error.stdout = "nothing to commit"
        error.stderr = ""

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = commit_entity_change(
                registry_path=str(git_registry),
                file_path=file_path,
                action="Delete",
                entity_data=self._entity(),
            )

        assert result.success is False
        assert "Nothing new to commit" in result.error

    def test_handles_generic_git_error_gracefully(self, git_registry):
        file_path = git_registry / "projects" / "proj-abc12345.yml"
        file_path.unlink()
        
        error = subprocess.CalledProcessError(128, "git")
        error.stdout = ""
        error.stderr = "fatal: some git error"

        with patch("subprocess.run", side_effect=[MagicMock(), error]):
            result = commit_entity_change(
                registry_path=str(git_registry),
                file_path=file_path,
                action="Delete",
                entity_data=self._entity(),
            )

        assert result.success is False
        assert "some git error" in result.error


class TestBuildCommitMessageDelete:
    """Test commit message generation for delete operations."""

    def test_delete_action_basic(self):
        entity_data = {
            "type": "project",
            "uid": "abc12345",
            "id": "P-001",
            "title": "Test Project",
        }
        message = build_commit_message("Delete", "proj-abc12345", entity_data)
        
        assert "Delete proj-abc12345: Test Project" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: abc12345" in message

    def test_delete_action_all_entity_types(self):
        entity_types = [
            ("program", "prog-test1234", "PG-001"),
            ("project", "proj-test1234", "P-001"),
            ("mission", "miss-test1234", "M-001"),
            ("action", "act-test1234", "A-001"),
        ]
        
        for etype, file_stem, entity_id in entity_types:
            entity_data = {
                "type": etype,
                "uid": "test1234",
                "id": entity_id,
                "title": f"Test {etype.title()}",
            }
            message = build_commit_message("Delete", file_stem, entity_data)
            
            assert f"Delete {file_stem}" in message
            assert f"Entity type: {etype}" in message
            assert f"Entity ID: {entity_id}" in message


# ─── Integration: --no-commit flag ───────────────────────────────────────────


class TestNoCommitFlag:
    """Tests that --no-commit prevents git operations."""

    def _run_delete(self, registry_path, identifier, extra_args=None):
        """Helper: invoke DeleteCommand.execute via hxc.cli.main."""
        from hxc.cli import main
        args = ["delete", identifier, "--force"]
        if extra_args:
            args.extend(extra_args)
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(registry_path)):
            return main(args)

    def test_no_commit_flag_prevents_git_call(self, git_registry):
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            result = self._run_delete(git_registry, "P-GIT", ["--no-commit"])
        assert result == 0
        mock_commit.assert_not_called()

    def test_no_commit_flag_prints_warning(self, git_registry, capsys):
        result = self._run_delete(git_registry, "P-GIT", ["--no-commit"])
        assert result == 0
        out = capsys.readouterr().out
        assert "--no-commit" in out

    def test_without_no_commit_flag_calls_commit(self, git_registry):
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(
                success=True,
                commit_hash="abc1234",
                message="Delete proj-abc12345: Git Test Project"
            )
            result = self._run_delete(git_registry, "P-GIT")
        assert result == 0
        mock_commit.assert_called_once()

    def test_file_is_deleted_even_with_no_commit(self, git_registry):
        project_file = git_registry / "projects" / "proj-abc12345.yml"
        assert project_file.exists()
        
        result = self._run_delete(git_registry, "P-GIT", ["--no-commit"])
        assert result == 0
        
        assert not project_file.exists()


# ─── Integration: real git commit ────────────────────────────────────────────


class TestRealGitCommit:
    """End-to-end tests that actually run git."""

    def _run_delete(self, registry_path, identifier, args=None):
        from hxc.cli import main
        cmd = ["delete", identifier, "--force"]
        if args:
            cmd.extend(args)
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(registry_path)):
            return main(cmd)

    def test_commit_is_created_in_git_log(self, git_registry):
        result = self._run_delete(git_registry, "P-GIT")
        assert result == 0

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "proj-abc12345" in log.stdout

    def test_commit_message_contains_delete_action(self, git_registry):
        result = self._run_delete(git_registry, "P-GIT")
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Delete" in log.stdout

    def test_commit_message_contains_entity_title(self, git_registry):
        result = self._run_delete(git_registry, "P-GIT")
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Git Test Project" in log.stdout

    def test_commit_message_contains_entity_metadata(self, git_registry):
        result = self._run_delete(git_registry, "P-GIT")
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Entity type: project" in log.stdout
        assert "Entity ID: P-GIT" in log.stdout
        assert "Entity UID: abc12345" in log.stdout

    def test_only_deleted_file_is_in_commit(self, git_registry):
        # Create an unrelated unstaged file
        unrelated = git_registry / "unrelated.txt"
        unrelated.write_text("do not commit me")

        result = self._run_delete(git_registry, "P-GIT")
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
        # Unrelated file should still exist and be untracked
        assert unrelated.exists()

    def test_no_commit_leaves_deletion_unstaged(self, git_registry):
        result = self._run_delete(git_registry, "P-GIT", ["--no-commit"])
        assert result == 0

        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        # File should appear as deleted but not staged
        assert "proj-abc12345.yml" in status.stdout

    def test_registry_without_git_deletes_successfully(self, temp_registry, capsys):
        """Delete should succeed and warn gracefully when no git repo exists."""
        from hxc.cli import main
        
        project_file = temp_registry / "projects" / "proj-abc12345.yml"
        assert project_file.exists()
        
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(temp_registry)):
            result = main(["delete", "P-GIT", "--force"])

        assert result == 0
        out = capsys.readouterr().out
        assert "not inside a git repository" in out

        # File was still deleted
        assert not project_file.exists()

    def test_delete_shows_commit_hash(self, git_registry, capsys):
        result = self._run_delete(git_registry, "P-GIT")
        assert result == 0

        out = capsys.readouterr().out
        assert "committed to git" in out
        # The output should contain a commit hash in parentheses
        assert "(" in out and ")" in out


class TestAllEntityTypesGitCommit:
    """Test git commits work for all entity types."""

    def test_program_delete_commit(self, git_registry):
        # Create a program
        _create_entity_file(git_registry, "program", "progtest", "PG-001", "Test Program")
        subprocess.run(["git", "add", "."], cwd=git_registry, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add program"], cwd=git_registry, check=True, capture_output=True)
        
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            result = main(["delete", "PG-001", "--force"])
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "prog-progtest" in log.stdout
        assert "Entity type: program" in log.stdout

    def test_mission_delete_commit(self, git_registry):
        # Create a mission
        _create_entity_file(git_registry, "mission", "misstest", "M-001", "Test Mission")
        subprocess.run(["git", "add", "."], cwd=git_registry, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add mission"], cwd=git_registry, check=True, capture_output=True)
        
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            result = main(["delete", "M-001", "--force"])
        assert result == 0

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "miss-misstest" in log.stdout
        assert "Entity type: mission" in log.stdout

    def test_action_delete_commit(self, git_registry):
        # Create an action
        _create_entity_file(git_registry, "action", "acttest1", "A-001", "Test Action")
        subprocess.run(["git", "add", "."], cwd=git_registry, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add action"], cwd=git_registry, check=True, capture_output=True)
        
        from hxc.cli import main
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            result = main(["delete", "A-001", "--force"])
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

    def test_git_error_does_not_fail_delete(self, git_registry, capsys):
        """If git commit fails, the file should still be deleted."""
        from hxc.cli import main
        
        project_file = git_registry / "projects" / "proj-abc12345.yml"
        assert project_file.exists()
        
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            # Patch commit to fail after file deletion
            with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
                mock_commit.return_value = GitOperationResult(
                    success=False,
                    error="Simulated git error"
                )
                result = main(["delete", "P-GIT", "--force"])
        
        # Delete should still succeed
        assert result == 0
        
        # File should be deleted
        assert not project_file.exists()
        
        # Warning should be printed
        out = capsys.readouterr().out
        assert "Deleted project" in out

    def test_commit_success_prints_hash(self, git_registry, capsys):
        """Successful commit should display the commit hash."""
        from hxc.cli import main
        
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            result = main(["delete", "P-GIT", "--force"])
        
        assert result == 0
        out = capsys.readouterr().out
        assert "committed to git" in out
        # The output should contain a commit hash in parentheses
        assert "(" in out and ")" in out


class TestDeleteWithUserConfirmation:
    """Test git commit works correctly with user confirmation flow."""

    def test_commit_created_after_user_confirms(self, git_registry, capsys):
        """Git commit should be created when user confirms deletion."""
        from hxc.cli import main
        
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("builtins.input", return_value="y"):
                result = main(["delete", "P-GIT"])
        
        assert result == 0
        
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Delete" in log.stdout
        assert "proj-abc12345" in log.stdout

    def test_no_commit_when_user_declines(self, git_registry):
        """No git commit should be created when user declines deletion."""
        from hxc.cli import main
        
        initial_log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        initial_commit_count = len(initial_log.stdout.strip().splitlines())
        
        with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                   return_value=str(git_registry)):
            with patch("builtins.input", return_value="n"):
                result = main(["delete", "P-GIT"])
        
        # Should indicate cancellation
        assert result == 1
        
        # File should still exist
        project_file = git_registry / "projects" / "proj-abc12345.yml"
        assert project_file.exists()
        
        # No new commits should be created
        final_log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        final_commit_count = len(final_log.stdout.strip().splitlines())
        assert final_commit_count == initial_commit_count


class TestMultipleDeletesGitHistory:
    """Test that multiple deletes produce correct git history."""

    def test_multiple_deletes_produce_individual_commits(self, git_registry):
        """Each delete should produce its own commit."""
        from hxc.cli import main
        
        # Create additional entities
        for i, entity_type in enumerate(["project", "mission", "action"]):
            _create_entity_file(
                git_registry, entity_type, f"multi{i:04d}",
                f"MULTI-{i}", f"Multi Delete {entity_type.title()}"
            )
        
        subprocess.run(["git", "add", "."], cwd=git_registry, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "add test entities"], cwd=git_registry, check=True, capture_output=True)
        
        # Get initial commit count
        initial_log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        initial_count = len(initial_log.stdout.strip().splitlines())
        
        # Delete each entity
        for i in range(3):
            with patch("hxc.commands.registry.RegistryCommand.get_registry_path",
                       return_value=str(git_registry)):
                result = main(["delete", f"MULTI-{i}", "--force"])
            assert result == 0
        
        # Should have 3 new commits (one per delete)
        final_log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        final_count = len(final_log.stdout.strip().splitlines())
        assert final_count == initial_count + 3
        
        # Each delete should appear in log
        assert "Multi Delete Project" in final_log.stdout or "proj-multi0000" in final_log.stdout
        assert "Multi Delete Mission" in final_log.stdout or "miss-multi0001" in final_log.stdout
        assert "Multi Delete Action" in final_log.stdout or "act-multi0002" in final_log.stdout