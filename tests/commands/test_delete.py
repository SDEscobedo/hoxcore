"""
Tests for the delete command
"""
import os
import sys
import yaml
import pathlib
import shutil
import pytest
from unittest.mock import patch, MagicMock
import subprocess


from hxc.cli import main
from hxc.commands.delete import DeleteCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.path_security import PathSecurityError


@pytest.fixture
def temp_git_registry(temp_registry):
    """Create a temporary registry and initialize it as a git repository."""
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=str(temp_registry), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(temp_registry))
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(temp_registry))
    
    # Add all existing files
    subprocess.run(["git", "add", "."], cwd=str(temp_registry), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(temp_registry), capture_output=True)
    
    return temp_registry


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
    # Create directory structure
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)
    
    # Create marker files and directories
    (registry_path / ".hxc").mkdir()
    (registry_path / "config.yml").write_text("# Test config")
    
    # Create entity directories
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()
    
    # Create test entity files
    project_dir = registry_path / "projects"
    
    # Create a test project file
    project_data = {
        "type": "project",
        "uid": "12345678",
        "id": "P-001",
        "title": "Test Project",
        "status": "active",
        "start_date": "2024-01-01"
    }
    
    with open(project_dir / "proj-12345678.yml", 'w') as f:
        yaml.dump(project_data, f)
    
    # Create a second project with only ID (no UID in filename)
    project_data2 = {
        "type": "project",
        "uid": "87654321",
        "id": "P-ID-ONLY",
        "title": "ID Only Project",
        "status": "active",
        "start_date": "2024-01-01"
    }
    
    with open(project_dir / "proj-87654321.yml", 'w') as f:
        yaml.dump(project_data2, f)
        
    # Create test program file
    program_dir = registry_path / "programs"
    program_data = {
        "type": "program",
        "uid": "abcdef12",
        "id": "PG-001",
        "title": "Test Program",
        "status": "active",
        "start_date": "2024-01-01"
    }
    
    with open(program_dir / "prog-abcdef12.yml", 'w') as f:
        yaml.dump(program_data, f)
    
    yield registry_path
    
    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


def test_delete_command_registration():
    """Test that the delete command is properly registered"""
    from hxc.commands import get_available_commands
    
    available_commands = get_available_commands()
    assert "delete" in available_commands


def test_delete_command_parser():
    """Test delete command parser registration"""
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = DeleteCommand.register_subparser(subparsers)
    
    # Verify parser has the expected arguments
    actions = {action.dest for action in cmd_parser._actions}
    assert "identifier" in actions
    assert "type" in actions
    assert "force" in actions
    assert "registry" in actions


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_by_uid_with_confirmation(mock_get_registry_path, temp_registry):
    """Test deleting an entity by UID with confirmation"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock the input function to simulate user confirmation
    with patch("builtins.input", return_value="y"):
        # We add --no-commit to isolate the test from git operations
        result = main(["delete", "12345678", "--no-commit"])
        
        # Check result
        assert result == 0
        
        # Check that file was deleted
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert not project_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_by_uid_cancelled(mock_get_registry_path, temp_registry):
    """Test cancelling deletion when user doesn't confirm"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock the input function to simulate user declining
    with patch("builtins.input", return_value="n"):
        result = main(["delete", "12345678", "--no-commit"])
        
        # Check result indicates cancellation
        assert result == 1
        
        # Check that file was not deleted
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_by_uid_force(mock_get_registry_path, temp_registry):
    """Test deleting an entity with --force flag (no confirmation)"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    result = main(["delete", "12345678", "--force", "--no-commit"])
    
    # Check result
    assert result == 0
    
    # Check that file was deleted
    project_file = temp_registry / "projects" / "proj-12345678.yml"
    assert not project_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_by_id(mock_get_registry_path, temp_registry):
    """Test deleting an entity by ID"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock the input function to simulate user confirmation
    with patch("builtins.input", return_value="y"):
        result = main(["delete", "P-ID-ONLY", "--no-commit"])
        
        # Check result
        assert result == 0
        
        # Check that file was deleted
        project_file = temp_registry / "projects" / "proj-87654321.yml"
        assert not project_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_with_type_filter(mock_get_registry_path, temp_registry):
    """Test deleting an entity with type filter"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock the input function to simulate user confirmation
    with patch("builtins.input", return_value="y"):
        result = main(["delete", "12345678", "--type", "project", "--no-commit"])
        
        # Check result
        assert result == 0
        
        # Check that file was deleted
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert not project_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_entity_not_found(mock_get_registry_path, temp_registry):
    """Test error when entity is not found"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["delete", "nonexistent"])
        
        # Check result indicates failure
        assert result == 1
        
        # Check error message
        mock_print.assert_called_with("❌ No entity found with identifier 'nonexistent'")


@patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None)
@patch("hxc.commands.delete.DeleteCommand._get_registry_path", return_value=None)
def test_delete_no_registry(mock_get_project_root, mock_get_registry_path):
    """Test deleting when no registry is available"""
    with patch("builtins.print") as mock_print:
        result = main(["delete", "12345678"])
        
        # Check result indicates failure
        assert result == 1
        
        # Check error message
        mock_print.assert_called_with("❌ No registry found. Please specify with --registry or initialize one with 'hxc init'")


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_error_handling(mock_get_registry_path, temp_registry):
    """Test error handling during deletion"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Force an error by patching os.remove
    with patch("os.remove", side_effect=Exception("Test error")):
        with patch("builtins.input", return_value="y"):
            with patch("builtins.print") as mock_print:
                result = main(["delete", "12345678", "--no-commit"])
                
                # Check result indicates failure
                assert result == 1
                
                # Check error message
                assert any("Error deleting entity" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_path_traversal_protection(mock_get_registry_path, temp_registry):
    """Test that path traversal attempts are blocked during deletion"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock _find_entity_files to raise PathSecurityError
    with patch("hxc.commands.delete.DeleteCommand._find_entity_files", side_effect=PathSecurityError("Path traversal detected")):
        with patch("builtins.print") as mock_print:
            result = main(["delete", "12345678"])
            
            # Check result indicates failure
            assert result == 1
            
            # Check that security error message is displayed
            assert any("Security error" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_file_outside_registry_blocked(mock_get_registry_path, temp_registry, tmp_path):
    """Test that files outside the registry cannot be deleted"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Create a file outside the registry
    external_file = tmp_path / "external_file.yml"
    external_file.write_text("external: data")
    
    # Mock _find_entity_files to return the external file
    with patch("hxc.commands.delete.DeleteCommand._find_entity_files", return_value=[(str(external_file), "project")]):
        with patch("builtins.input", return_value="y"):
            with patch("builtins.print") as mock_print:
                result = main(["delete", "external"])
                
                # Check result indicates failure due to security error
                assert result == 1
                
                # Check that security error is raised
                assert any("Security error" in call[0][0] for call in mock_print.call_args_list)
                
                # Verify external file still exists
                assert external_file.exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Symlinks require admin privileges on Windows")
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_symlink_escape_blocked(mock_get_registry_path, temp_registry, tmp_path):
    """Test that symlinks pointing outside registry are blocked"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Create a file outside the registry
    external_file = tmp_path / "external_secret.yml"
    external_file.write_text("secret: data")
    
    # Create a symlink inside the registry pointing outside
    symlink_path = temp_registry / "projects" / "proj-symlink.yml"
    symlink_path.symlink_to(external_file)
    
    # Attempt to delete via the symlink
    with patch("builtins.input", return_value="y"):
        with patch("builtins.print") as mock_print:
            result = main(["delete", "symlink"])
            
            # Check result indicates failure (entity not found or security error)
            assert result == 1
            
            # Verify external file still exists
            assert external_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_all_entity_types_within_registry(mock_get_registry_path, temp_registry):
    """Test that deletion only affects files within the registry"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Test deleting each entity type
    entity_tests = [
        ("12345678", "projects", "proj-12345678.yml"),
        ("abcdef12", "programs", "prog-abcdef12.yml")
    ]
    
    for uid, folder, filename in entity_tests:
        entity_file = temp_registry / folder / filename
        
        # Verify file exists before deletion
        assert entity_file.exists()
        
        # Delete with force flag
        result = main(["delete", uid, "--force", "--no-commit"])
        
        # Check result
        assert result == 0
        
        # Verify file was deleted
        assert not entity_file.exists()
        
        # Verify deletion stayed within registry
        assert not any(
            f.exists() for f in temp_registry.parent.rglob(filename)
            if temp_registry not in f.parents
        )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_with_relative_path_traversal(mock_get_registry_path, temp_registry):
    """Test that relative path traversal in identifiers is blocked"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Attempt to delete using path traversal in identifier
    malicious_identifiers = [
        "../../../etc/passwd",
        "../../external_file",
        "./../outside/file"
    ]
    
    for identifier in malicious_identifiers:
        with patch("builtins.print") as mock_print:
            result = main(["delete", identifier, "--force"])
            
            # Check result indicates failure
            assert result == 1
            
            # Verify appropriate error message
            assert any(
                "Security error" in call[0][0] or "No entity found" in call[0][0]
                for call in mock_print.call_args_list
            )


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_find_entity_files_security(mock_get_registry_path, temp_registry, tmp_path):
    """Test that _find_entity_files respects path security"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Create a file outside the registry
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    external_file = external_dir / "proj-external.yml"
    external_file.write_text("type: project\nuid: external\ntitle: External")
    
    # Call _find_entity_files directly
    files = DeleteCommand._find_entity_files(str(temp_registry), "external", None)
    
    # Verify that external file is not found
    assert len(files) == 0 or all(str(temp_registry) in str(f[0]) for f in files)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_respects_registry_boundaries(mock_get_registry_path, temp_registry, tmp_path):
    """Test that delete command respects registry boundaries in all operations"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Create a similar structure outside the registry
    external_registry = tmp_path / "external_registry"
    external_registry.mkdir()
    (external_registry / "projects").mkdir()
    
    external_project = external_registry / "projects" / "proj-12345678.yml"
    external_project.write_text("type: project\nuid: 12345678\ntitle: External Project")
    
    # Delete the internal project
    result = main(["delete", "12345678", "--force", "--no-commit"])
    
    # Check result
    assert result == 0
    
    # Verify internal file was deleted
    internal_file = temp_registry / "projects" / "proj-12345678.yml"
    assert not internal_file.exists()
    
    # Verify external file still exists
    assert external_project.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_multiple_matches_with_type_filter(mock_get_registry_path, temp_registry):
    """Test that type filter prevents ambiguous deletions"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Create entities with same UID in different folders
    mission_dir = temp_registry / "missions"
    mission_data = {
        "type": "mission",
        "uid": "duplicate",
        "id": "M-001",
        "title": "Test Mission",
        "status": "active",
        "start_date": "2024-01-01"
    }
    
    with open(mission_dir / "miss-duplicate.yml", 'w') as f:
        yaml.dump(mission_data, f)
    
    action_dir = temp_registry / "actions"
    action_data = {
        "type": "action",
        "uid": "duplicate",
        "id": "A-001",
        "title": "Test Action",
        "status": "active",
        "start_date": "2024-01-01"
    }
    
    with open(action_dir / "act-duplicate.yml", 'w') as f:
        yaml.dump(action_data, f)
    
    # Try to delete without type filter (should fail)
    with patch("builtins.print") as mock_print:
        result = main(["delete", "duplicate", "--force"])
        
        # Check result indicates failure due to ambiguity
        assert result == 1
        assert any("Multiple entities found" in call[0][0] for call in mock_print.call_args_list)
    
    # Delete with type filter (should succeed)
    result = main(["delete", "duplicate", "--type", "mission", "--force", "--no-commit"])
    assert result == 0
    
    # Verify only mission was deleted
    assert not (mission_dir / "miss-duplicate.yml").exists()
    assert (action_dir / "act-duplicate.yml").exists()


# --- Git Integration Tests ---

@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_full_workflow_commit_and_log(mock_get_registry_path, temp_git_registry):
    """Test full workflow: delete -> commit -> verify in git log"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    result = main(["delete", "12345678", "--force"])
    
    assert result == 0
    
    # Verify file is deleted from filesystem
    project_file = temp_git_registry / "projects" / "proj-12345678.yml"
    assert not project_file.exists()
    
    # Verify file is removed from git index
    status_result = subprocess.run(["git", "status", "--porcelain"], cwd=str(temp_git_registry), capture_output=True, text=True)
    assert "proj-12345678.yml" not in status_result.stdout
    
    # Verify commit message in log
    log_result = subprocess.run(["git", "log", "-1", "--pretty=%B"], cwd=str(temp_git_registry), capture_output=True, text=True)
    assert "Delete proj-12345678: Test Project" in log_result.stdout
    assert "Entity ID: P-001" in log_result.stdout


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_appears_in_git_history(mock_get_registry_path, temp_git_registry):
    """Test deletion appears correctly in git history"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    main(["delete", "12345678", "--force"])
    
    # Check git history for the deleted file
    history_result = subprocess.run(
        ["git", "log", "--", "projects/proj-12345678.yml"],
        cwd=str(temp_git_registry),
        capture_output=True,
        text=True
    )
    
    # The log should show the initial commit and the delete commit
    assert "Initial commit" in history_result.stdout
    assert "Delete proj-12345678: Test Project" in history_result.stdout


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_with_uncommitted_changes(mock_get_registry_path, temp_git_registry):
    """Test delete with existing uncommitted changes (unrelated files)"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    # Create an unrelated file with uncommitted changes
    unrelated_file = temp_git_registry / "unrelated.txt"
    unrelated_file.write_text("This is an unrelated file.")
    
    # Run the delete command
    main(["delete", "12345678", "--force"])
    
    # Check that the deleted file is committed
    log_result = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=str(temp_git_registry), capture_output=True, text=True)
    assert "Delete proj-12345678: Test Project" in log_result.stdout
    
    # Check that the unrelated file is still uncommitted
    status_result = subprocess.run(["git", "status", "--porcelain"], cwd=str(temp_git_registry), capture_output=True, text=True)
    assert "?? unrelated.txt" in status_result.stdout


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_git_log_shows_deleted_file_path(mock_get_registry_path, temp_git_registry):
    """Test git log shows deleted file path"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    main(["delete", "12345678", "--force"])
    
    # Check git log with file stats
    log_stat_result = subprocess.run(["git", "log", "-1", "--stat"], cwd=str(temp_git_registry), capture_output=True, text=True)
    
    assert "projects/proj-12345678.yml" in log_stat_result.stdout
    assert "1 file changed, 7 deletions(-)" in log_stat_result.stdout


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_automatic_commit(mock_get_registry_path, temp_git_registry):
    """Test automatic commit after successful delete"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    result = main(["delete", "12345678", "--force"])
    
    assert result == 0
    
    # Check that the file is gone from the filesystem
    project_file = temp_git_registry / "projects" / "proj-12345678.yml"
    assert not project_file.exists()
    
    # Check git log for the delete commit
    log_result = subprocess.run(["git", "log", "-1", "--pretty=%s"], cwd=str(temp_git_registry), capture_output=True, text=True)
    assert "Delete proj-12345678: Test Project" in log_result.stdout


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_no_commit_flag(mock_get_registry_path, temp_git_registry):
    """Test --no-commit flag prevents commit"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    # Get the commit hash before the operation
    log_before = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(temp_git_registry), capture_output=True, text=True).stdout.strip()
    
    result = main(["delete", "12345678", "--force", "--no-commit"])
    
    assert result == 0
    
    # Check that the file is deleted
    project_file = temp_git_registry / "projects" / "proj-12345678.yml"
    assert not project_file.exists()
    
    # Check that no new commit was made
    log_after = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(temp_git_registry), capture_output=True, text=True).stdout.strip()
    assert log_before == log_after


@patch("hxc.commands.edit.EditCommand._git_available", return_value=False)
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_git_not_available(mock_get_registry_path, mock_git_available, temp_git_registry):
    """Test error handling when git is not available"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["delete", "12345678", "--force"])
        
        assert result == 0
        mock_print.assert_any_call("⚠️ Git is not installed.")
        
        # File should still be deleted
        project_file = temp_git_registry / "projects" / "proj-12345678.yml"
        assert not project_file.exists()


@patch("hxc.commands.edit.EditCommand._find_git_root", return_value=None)
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_not_a_git_repo(mock_get_registry_path, mock_find_git_root, temp_registry):
    """Test error handling when not in a git repository"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["delete", "12345678", "--force"])
        
        assert result == 0
        mock_print.assert_any_call("⚠️  No git repository found. Deleting file from disk only.")
        
        # File should still be deleted
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert not project_file.exists()


@patch("subprocess.run")
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_commit_message_generation(mock_get_registry_path, mock_subprocess_run, temp_git_registry):
    """Test commit message generation includes entity title"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    # Mock git responses to inspect the commit message
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="[main 12345] ...", stderr="")
    
    main(["delete", "12345678", "--force"])
    
    commit_call = None
    for call in mock_subprocess_run.call_args_list:
        if "commit" in call.args[0]:
            commit_call = call
            break
            
    assert commit_call is not None, "git commit was not called"
    
    commit_message = commit_call.args[0][2]
    assert "Delete proj-12345678: Test Project" in commit_message
    assert "Entity type: project" in commit_message
    assert "Entity ID: P-001" in commit_message
    assert "Entity UID: 12345678" in commit_message


@patch("subprocess.run")
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_only_stages_deleted_file(mock_get_registry_path, mock_subprocess_run, temp_git_registry):
    """Test that only the deleted file is staged"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    # Create a dummy file with uncommitted changes
    (temp_git_registry / "dummy.txt").write_text("uncommitted changes")
    
    # Mock git responses
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="[main 12345] ...", stderr="")
    
    main(["delete", "12345678", "--force"])
    
    rm_call = None
    for call in mock_subprocess_run.call_args_list:
        if "rm" in call.args[0]:
            rm_call = call
            break
            
    assert rm_call is not None, "git rm was not called"
    deleted_file_path = rm_call.args[0][2]
    assert deleted_file_path.endswith("projects/proj-12345678.yml")
    
    # Check that 'git add' was not called for the other file
    for call in mock_subprocess_run.call_args_list:
        if "add" in call.args[0] and "dummy.txt" in call.args[0]:
            assert False, "'git add' was called on an unrelated file"


@patch("subprocess.run")
@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_commit_with_user_confirmation(mock_get_registry_path, mock_subprocess_run, temp_git_registry):
    """Test commit still created when user confirms deletion (without --force)"""
    mock_get_registry_path.return_value = str(temp_git_registry)
    
    # Mock git responses
    mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="[main 12345] ...", stderr="")
    
    with patch("builtins.input", return_value="y"):
        result = main(["delete", "12345678"])
        
        assert result == 0
        
        commit_called = any("commit" in call.args[0] for call in mock_subprocess_run.call_args_list)
        assert commit_called, "git commit was not called"