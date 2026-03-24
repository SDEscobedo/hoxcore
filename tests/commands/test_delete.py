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

from hxc.cli import main
from hxc.commands.delete import DeleteCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.path_security import PathSecurityError
from hxc.utils.git import GitOperationResult


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
    assert "no_commit" in actions


def test_delete_command_parser_no_commit_flag():
    """Test that --no-commit flag is properly configured"""
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = DeleteCommand.register_subparser(subparsers)
    
    # Find the 'no_commit' argument
    no_commit_action = None
    for action in cmd_parser._actions:
        if action.dest == "no_commit":
            no_commit_action = action
            break
    
    assert no_commit_action is not None
    # Verify it's a store_true action (flag)
    assert no_commit_action.const is True
    assert no_commit_action.default is False


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_by_uid_with_confirmation(mock_get_registry_path, temp_registry):
    """Test deleting an entity by UID with confirmation"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Mock the input function to simulate user confirmation
    with patch("builtins.input", return_value="y"):
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
            result = main(["delete", "12345678"])
            
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
        result = main(["delete", "12345678"])
        
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
    
    with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
        mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
        result = main(["delete", "12345678", "--force"])
        
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
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
            result = main(["delete", "P-ID-ONLY"])
            
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
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
            result = main(["delete", "12345678", "--type", "project"])
            
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
                result = main(["delete", "12345678"])
                
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
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
            result = main(["delete", uid, "--force"])
            
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
    with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
        mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
        result = main(["delete", "12345678", "--force"])
        
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
    with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
        mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
        result = main(["delete", "duplicate", "--type", "mission", "--force"])
        assert result == 0
        
        # Verify only mission was deleted
        assert not (mission_dir / "miss-duplicate.yml").exists()
        assert (action_dir / "act-duplicate.yml").exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_with_no_commit_flag(mock_get_registry_path, temp_registry):
    """Test that --no-commit flag prevents git commit"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
        with patch("builtins.print") as mock_print:
            result = main(["delete", "12345678", "--force", "--no-commit"])
            
            # Check result
            assert result == 0
            
            # Check that commit was NOT called
            mock_commit.assert_not_called()
            
            # Check that file was still deleted
            project_file = temp_registry / "projects" / "proj-12345678.yml"
            assert not project_file.exists()
            
            # Check warning message about --no-commit
            assert any("--no-commit" in call[0][0] for call in mock_print.call_args_list)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_without_no_commit_flag_calls_commit(mock_get_registry_path, temp_registry):
    """Test that git commit is called when --no-commit is not used"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
        mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
        result = main(["delete", "12345678", "--force"])
        
        # Check result
        assert result == 0
        
        # Check that commit was called
        mock_commit.assert_called_once()
        
        # Verify commit was called with correct action
        call_kwargs = mock_commit.call_args.kwargs
        assert call_kwargs["action"] == "Delete"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_commit_includes_entity_data(mock_get_registry_path, temp_registry):
    """Test that git commit receives entity data"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
        mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
        result = main(["delete", "12345678", "--force"])
        
        # Check result
        assert result == 0
        
        # Check that commit was called with entity_data containing expected fields
        call_kwargs = mock_commit.call_args.kwargs
        entity_data = call_kwargs["entity_data"]
        
        assert entity_data["title"] == "Test Project"
        assert entity_data["id"] == "P-001"
        assert entity_data["type"] == "project"
        assert entity_data["uid"] == "12345678"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_commit_called_after_user_confirmation(mock_get_registry_path, temp_registry):
    """Test that git commit is called after user confirms deletion"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.input", return_value="y"):
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
            result = main(["delete", "12345678"])
            
            # Check result
            assert result == 0
            
            # Check that commit was called
            mock_commit.assert_called_once()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_no_commit_when_user_cancels(mock_get_registry_path, temp_registry):
    """Test that git commit is not called when user cancels deletion"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.input", return_value="n"):
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            result = main(["delete", "12345678"])
            
            # Check result indicates cancellation
            assert result == 1
            
            # Check that commit was NOT called
            mock_commit.assert_not_called()
            
            # Check that file was not deleted
            project_file = temp_registry / "projects" / "proj-12345678.yml"
            assert project_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_git_error_does_not_fail_deletion(mock_get_registry_path, temp_registry, capsys):
    """Test that git commit errors don't prevent successful deletion"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
        mock_commit.return_value = GitOperationResult(
            success=False,
            error="Simulated git error"
        )
        result = main(["delete", "12345678", "--force"])
        
        # Delete should still succeed
        assert result == 0
        
        # File should be deleted
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert not project_file.exists()


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_reads_entity_data_before_deletion(mock_get_registry_path, temp_registry):
    """Test that entity data is read before the file is deleted"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    captured_entity_data = {}
    
    def capture_entity_data(**kwargs):
        captured_entity_data.update(kwargs.get('entity_data', {}))
        return GitOperationResult(success=True, commit_hash="abc1234", message="test")
    
    with patch("hxc.commands.delete.commit_entity_change", side_effect=capture_entity_data) as mock_commit:
        result = main(["delete", "12345678", "--force"])
        
        # Check result
        assert result == 0
        
        # Verify entity data was captured with correct values
        assert captured_entity_data.get("title") == "Test Project"
        assert captured_entity_data.get("uid") == "12345678"
        assert captured_entity_data.get("type") == "project"


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_delete_all_entity_types_call_commit(mock_get_registry_path, temp_registry):
    """Test that commit is called for deletion of all entity types"""
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Create additional entity types for testing
    mission_data = {
        "type": "mission",
        "uid": "misstest",
        "id": "M-TEST",
        "title": "Test Mission",
        "status": "active",
        "start_date": "2024-01-01"
    }
    with open(temp_registry / "missions" / "miss-misstest.yml", 'w') as f:
        yaml.dump(mission_data, f)
    
    action_data = {
        "type": "action",
        "uid": "acttest1",
        "id": "A-TEST",
        "title": "Test Action",
        "status": "active",
        "start_date": "2024-01-01"
    }
    with open(temp_registry / "actions" / "act-acttest1.yml", 'w') as f:
        yaml.dump(action_data, f)
    
    test_cases = [
        ("12345678", "project"),
        ("abcdef12", "program"),
        ("misstest", "mission"),
        ("acttest1", "action"),
    ]
    
    for uid, expected_type in test_cases:
        with patch("hxc.commands.delete.commit_entity_change") as mock_commit:
            mock_commit.return_value = GitOperationResult(success=True, commit_hash="abc1234", message="test")
            result = main(["delete", uid, "--force"])
            
            assert result == 0
            mock_commit.assert_called_once()
            
            # Verify entity type in commit call
            call_kwargs = mock_commit.call_args.kwargs
            assert call_kwargs["entity_data"]["type"] == expected_type
            assert call_kwargs["action"] == "Delete"