"""
Tests for HoxCore Core Delete Operation.

This module provides unit and integration tests for the DeleteOperation class
that ensures behavioral consistency between CLI commands and MCP tools.
"""
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest
import yaml

from hxc.core.operations.delete import (
    DeleteOperation,
    DeleteOperationError,
    EntityNotFoundError,
    AmbiguousEntityError,
)
from hxc.core.enums import EntityType
from hxc.utils.path_security import PathSecurityError


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
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
    
    yield registry_path
    
    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def git_registry(tmp_path):
    """Create a temporary registry that is also a git repository."""
    registry_path = tmp_path / "git_registry"
    registry_path.mkdir(parents=True)
    
    # Create marker files and directories
    (registry_path / ".hxc").mkdir()
    (registry_path / "config.yml").write_text("# Test config")
    
    # Create entity directories
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()
    
    # Initialize git repository
    subprocess.run(["git", "init"], cwd=registry_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=registry_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=registry_path, check=True, capture_output=True
    )
    subprocess.run(["git", "add", "."], cwd=registry_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=registry_path, check=True, capture_output=True
    )
    
    yield registry_path
    
    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def registry_with_entities(temp_registry):
    """Create a registry with various entity types for testing"""
    # Create project with id "P-001"
    project1 = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Test Project One",
        "status": "active",
        "start_date": "2024-01-01",
    }
    with open(temp_registry / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project1, f)
    
    # Create project with id "P-002"
    project2 = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Test Project Two",
        "status": "completed",
        "start_date": "2024-02-01",
    }
    with open(temp_registry / "projects" / "proj-proj0002.yml", "w") as f:
        yaml.dump(project2, f)
    
    # Create program
    program = {
        "type": "program",
        "uid": "prog0001",
        "id": "PRG-001",
        "title": "Test Program",
        "status": "active",
        "start_date": "2024-01-01",
    }
    with open(temp_registry / "programs" / "prog-prog0001.yml", "w") as f:
        yaml.dump(program, f)
    
    # Create mission
    mission = {
        "type": "mission",
        "uid": "miss0001",
        "id": "M-001",
        "title": "Test Mission",
        "status": "planned",
        "start_date": "2024-03-01",
    }
    with open(temp_registry / "missions" / "miss-miss0001.yml", "w") as f:
        yaml.dump(mission, f)
    
    # Create action
    action = {
        "type": "action",
        "uid": "act0001",
        "id": "A-001",
        "title": "Test Action",
        "status": "active",
        "start_date": "2024-01-15",
    }
    with open(temp_registry / "actions" / "act-act0001.yml", "w") as f:
        yaml.dump(action, f)
    
    return temp_registry


@pytest.fixture
def git_registry_with_entities(git_registry):
    """Create a git registry with tracked entity files"""
    # Create project
    project = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Git Project",
        "status": "active",
        "start_date": "2024-01-01",
    }
    with open(git_registry / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project, f)
    
    # Create program
    program = {
        "type": "program",
        "uid": "prog0001",
        "id": "PRG-001",
        "title": "Git Program",
        "status": "active",
        "start_date": "2024-01-01",
    }
    with open(git_registry / "programs" / "prog-prog0001.yml", "w") as f:
        yaml.dump(program, f)
    
    # Stage and commit the entity files
    subprocess.run(["git", "add", "."], cwd=git_registry, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Add test entities"],
        cwd=git_registry, check=True, capture_output=True
    )
    
    return git_registry


class TestDeleteOperationInit:
    """Tests for DeleteOperation initialization"""
    
    def test_init_stores_registry_path(self, temp_registry):
        """Test that registry path is stored"""
        operation = DeleteOperation(str(temp_registry))
        assert operation.registry_path == str(temp_registry)
    
    def test_init_with_path_object(self, temp_registry):
        """Test initialization with Path object converts to string"""
        operation = DeleteOperation(str(temp_registry))
        assert isinstance(operation.registry_path, str)
    
    def test_entity_folders_mapping(self, temp_registry):
        """Test ENTITY_FOLDERS class attribute is correct"""
        expected = {
            "program": "programs",
            "project": "projects",
            "mission": "missions",
            "action": "actions",
        }
        assert DeleteOperation.ENTITY_FOLDERS == expected
    
    def test_file_prefixes_mapping(self, temp_registry):
        """Test FILE_PREFIXES class attribute is correct"""
        expected = {
            "program": "prog",
            "project": "proj",
            "mission": "miss",
            "action": "act",
        }
        assert DeleteOperation.FILE_PREFIXES == expected


class TestFindEntityFiles:
    """Tests for find_entity_files method"""
    
    def test_find_by_uid_in_filename(self, registry_with_entities):
        """Test finding entity by UID that matches filename"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("proj0001")
        
        assert len(results) == 1
        file_path, entity_type = results[0]
        assert entity_type == "project"
        assert "proj-proj0001.yml" in str(file_path)
    
    def test_find_by_human_id(self, registry_with_entities):
        """Test finding entity by human-readable ID"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("P-001")
        
        assert len(results) == 1
        file_path, entity_type = results[0]
        assert entity_type == "project"
    
    def test_find_by_uid_inside_file(self, registry_with_entities):
        """Test finding entity by UID when searching file contents"""
        operation = DeleteOperation(str(registry_with_entities))
        # Search by uid field value (should match)
        results = operation.find_entity_files("proj0001")
        
        assert len(results) >= 1
    
    def test_find_with_type_filter_project(self, registry_with_entities):
        """Test finding entity with project type filter"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("proj0001", EntityType.PROJECT)
        
        assert len(results) == 1
        _, entity_type = results[0]
        assert entity_type == "project"
    
    def test_find_with_type_filter_program(self, registry_with_entities):
        """Test finding entity with program type filter"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("prog0001", EntityType.PROGRAM)
        
        assert len(results) == 1
        _, entity_type = results[0]
        assert entity_type == "program"
    
    def test_find_with_type_filter_mission(self, registry_with_entities):
        """Test finding entity with mission type filter"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("miss0001", EntityType.MISSION)
        
        assert len(results) == 1
        _, entity_type = results[0]
        assert entity_type == "mission"
    
    def test_find_with_type_filter_action(self, registry_with_entities):
        """Test finding entity with action type filter"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("act0001", EntityType.ACTION)
        
        assert len(results) == 1
        _, entity_type = results[0]
        assert entity_type == "action"
    
    def test_find_with_wrong_type_filter_returns_empty(self, registry_with_entities):
        """Test that wrong type filter returns empty results"""
        operation = DeleteOperation(str(registry_with_entities))
        # proj0001 is a project, not a program
        results = operation.find_entity_files("proj0001", EntityType.PROGRAM)
        
        assert len(results) == 0
    
    def test_find_nonexistent_returns_empty(self, registry_with_entities):
        """Test that searching for nonexistent entity returns empty"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("nonexistent-uid")
        
        assert len(results) == 0
    
    def test_find_empty_registry_returns_empty(self, temp_registry):
        """Test searching in empty registry returns empty"""
        operation = DeleteOperation(str(temp_registry))
        results = operation.find_entity_files("any-identifier")
        
        assert len(results) == 0
    
    def test_find_returns_path_and_type_tuple(self, registry_with_entities):
        """Test that results contain Path and entity type string"""
        operation = DeleteOperation(str(registry_with_entities))
        results = operation.find_entity_files("proj0001")
        
        assert len(results) > 0
        file_path, entity_type = results[0]
        assert isinstance(file_path, Path)
        assert isinstance(entity_type, str)
    
    def test_find_handles_invalid_yaml_gracefully(self, temp_registry):
        """Test that invalid YAML files are skipped gracefully"""
        # Create invalid YAML file
        with open(temp_registry / "projects" / "proj-invalid.yml", "w") as f:
            f.write("{ invalid yaml [")
        
        operation = DeleteOperation(str(temp_registry))
        # Should not raise, should return empty
        results = operation.find_entity_files("invalid")
        
        assert isinstance(results, list)
    
    def test_find_searches_all_types_without_filter(self, registry_with_entities):
        """Test that without type filter, all entity types are searched"""
        operation = DeleteOperation(str(registry_with_entities))
        
        # Search for each type
        project_results = operation.find_entity_files("proj0001")
        program_results = operation.find_entity_files("prog0001")
        mission_results = operation.find_entity_files("miss0001")
        action_results = operation.find_entity_files("act0001")
        
        assert len(project_results) > 0
        assert len(program_results) > 0
        assert len(mission_results) > 0
        assert len(action_results) > 0


class TestLoadEntityData:
    """Tests for load_entity_data method"""
    
    def test_load_valid_entity(self, registry_with_entities):
        """Test loading valid entity data"""
        operation = DeleteOperation(str(registry_with_entities))
        file_path = registry_with_entities / "projects" / "proj-proj0001.yml"
        
        data = operation.load_entity_data(file_path)
        
        assert data["type"] == "project"
        assert data["uid"] == "proj0001"
        assert data["id"] == "P-001"
        assert data["title"] == "Test Project One"
    
    def test_load_all_entity_types(self, registry_with_entities):
        """Test loading data for all entity types"""
        operation = DeleteOperation(str(registry_with_entities))
        
        # Load project
        proj_data = operation.load_entity_data(
            registry_with_entities / "projects" / "proj-proj0001.yml"
        )
        assert proj_data["type"] == "project"
        
        # Load program
        prog_data = operation.load_entity_data(
            registry_with_entities / "programs" / "prog-prog0001.yml"
        )
        assert prog_data["type"] == "program"
        
        # Load mission
        miss_data = operation.load_entity_data(
            registry_with_entities / "missions" / "miss-miss0001.yml"
        )
        assert miss_data["type"] == "mission"
        
        # Load action
        act_data = operation.load_entity_data(
            registry_with_entities / "actions" / "act-act0001.yml"
        )
        assert act_data["type"] == "action"
    
    def test_load_nonexistent_file_raises(self, temp_registry):
        """Test that loading nonexistent file raises FileNotFoundError"""
        operation = DeleteOperation(str(temp_registry))
        
        with pytest.raises(FileNotFoundError):
            operation.load_entity_data(temp_registry / "projects" / "nonexistent.yml")
    
    def test_load_invalid_yaml_raises(self, temp_registry):
        """Test that loading invalid YAML raises exception"""
        # Create invalid YAML file
        invalid_file = temp_registry / "projects" / "proj-invalid.yml"
        with open(invalid_file, "w") as f:
            f.write("not: valid: yaml: [")
        
        operation = DeleteOperation(str(temp_registry))
        
        with pytest.raises(Exception):
            operation.load_entity_data(invalid_file)
    
    def test_load_empty_file_raises_value_error(self, temp_registry):
        """Test that loading empty file raises ValueError"""
        # Create empty YAML file
        empty_file = temp_registry / "projects" / "proj-empty.yml"
        empty_file.write_text("")
        
        operation = DeleteOperation(str(temp_registry))
        
        with pytest.raises(ValueError) as exc_info:
            operation.load_entity_data(empty_file)
        
        assert "Invalid entity data" in str(exc_info.value)
    
    def test_load_non_dict_raises_value_error(self, temp_registry):
        """Test that loading non-dict YAML raises ValueError"""
        # Create YAML file with list instead of dict
        list_file = temp_registry / "projects" / "proj-list.yml"
        list_file.write_text("- item1\n- item2\n")
        
        operation = DeleteOperation(str(temp_registry))
        
        with pytest.raises(ValueError) as exc_info:
            operation.load_entity_data(list_file)
        
        assert "Invalid entity data" in str(exc_info.value)


class TestGetEntityTitle:
    """Tests for get_entity_title method"""
    
    def test_get_title_returns_title(self, registry_with_entities):
        """Test getting entity title"""
        operation = DeleteOperation(str(registry_with_entities))
        file_path = registry_with_entities / "projects" / "proj-proj0001.yml"
        
        title = operation.get_entity_title(file_path)
        
        assert title == "Test Project One"
    
    def test_get_title_fallback_to_filename(self, temp_registry):
        """Test that title falls back to filename on error"""
        # Create entity without title field
        no_title = {"type": "project", "uid": "notitle", "status": "active"}
        no_title_file = temp_registry / "projects" / "proj-notitle.yml"
        with open(no_title_file, "w") as f:
            yaml.dump(no_title, f)
        
        operation = DeleteOperation(str(temp_registry))
        title = operation.get_entity_title(no_title_file)
        
        # Should return filename since title is missing
        assert "proj-notitle.yml" in title
    
    def test_get_title_invalid_file_returns_filename(self, temp_registry):
        """Test that invalid file returns filename as fallback"""
        invalid_file = temp_registry / "projects" / "proj-invalid.yml"
        invalid_file.write_text("{ invalid yaml [")
        
        operation = DeleteOperation(str(temp_registry))
        title = operation.get_entity_title(invalid_file)
        
        assert "proj-invalid.yml" in title


class TestDeleteFile:
    """Tests for delete_file method"""
    
    def test_delete_existing_file(self, registry_with_entities):
        """Test deleting an existing file"""
        operation = DeleteOperation(str(registry_with_entities))
        file_path = registry_with_entities / "projects" / "proj-proj0001.yml"
        
        assert file_path.exists()
        
        operation.delete_file(file_path)
        
        assert not file_path.exists()
    
    def test_delete_nonexistent_file_raises(self, temp_registry):
        """Test that deleting nonexistent file raises OSError"""
        operation = DeleteOperation(str(temp_registry))
        nonexistent = temp_registry / "projects" / "nonexistent.yml"
        
        with pytest.raises(OSError):
            operation.delete_file(nonexistent)
    
    def test_delete_respects_path_security(self, temp_registry, tmp_path):
        """Test that delete_file respects path security"""
        operation = DeleteOperation(str(temp_registry))
        
        # Create file outside registry
        external_file = tmp_path / "external.yml"
        external_file.write_text("external: data")
        
        with pytest.raises(PathSecurityError):
            operation.delete_file(external_file)
        
        # Verify file still exists
        assert external_file.exists()


class TestDeleteWithGit:
    """Tests for delete_with_git method"""
    
    def test_delete_with_git_creates_commit(self, git_registry_with_entities):
        """Test that git deletion creates a commit"""
        operation = DeleteOperation(str(git_registry_with_entities))
        file_path = git_registry_with_entities / "projects" / "proj-proj0001.yml"
        
        entity_data = operation.load_entity_data(file_path)
        
        result = operation.delete_with_git(file_path, entity_data, "project")
        
        assert result is True
        assert not file_path.exists()
        
        # Verify commit was created
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        
        assert "Delete" in log.stdout
        assert "proj-proj0001" in log.stdout
    
    def test_delete_with_git_commit_message_format(self, git_registry_with_entities):
        """Test that commit message follows expected format"""
        operation = DeleteOperation(str(git_registry_with_entities))
        file_path = git_registry_with_entities / "projects" / "proj-proj0001.yml"
        
        entity_data = operation.load_entity_data(file_path)
        
        operation.delete_with_git(file_path, entity_data, "project")
        
        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        
        message = log.stdout
        
        # Verify message format
        assert "Delete proj-proj0001: Git Project" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: proj0001" in message
    
    def test_delete_with_git_non_git_registry_falls_back(self, registry_with_entities):
        """Test that non-git registry falls back to simple deletion"""
        operation = DeleteOperation(str(registry_with_entities))
        file_path = registry_with_entities / "projects" / "proj-proj0001.yml"
        
        entity_data = operation.load_entity_data(file_path)
        
        result = operation.delete_with_git(file_path, entity_data, "project")
        
        # Should return False (not committed to git)
        assert result is False
        # But file should still be deleted
        assert not file_path.exists()
    
    def test_delete_with_git_untracked_file_falls_back(self, git_registry):
        """Test that untracked file falls back to simple deletion"""
        # Create untracked entity
        untracked_entity = {
            "type": "project",
            "uid": "untracked",
            "id": "P-UNTRACKED",
            "title": "Untracked Project",
            "status": "active",
        }
        untracked_file = git_registry / "projects" / "proj-untracked.yml"
        with open(untracked_file, "w") as f:
            yaml.dump(untracked_entity, f)
        
        operation = DeleteOperation(str(git_registry))
        
        result = operation.delete_with_git(untracked_file, untracked_entity, "project")
        
        # Should return False (git rm fails for untracked)
        assert result is False
        # But file should still be deleted
        assert not untracked_file.exists()
    
    def test_delete_with_git_unavailable_falls_back(self, registry_with_entities):
        """Test that git unavailable falls back to simple deletion"""
        operation = DeleteOperation(str(registry_with_entities))
        file_path = registry_with_entities / "projects" / "proj-proj0001.yml"
        entity_data = operation.load_entity_data(file_path)
        
        with patch("hxc.core.operations.delete.git_available", return_value=False):
            result = operation.delete_with_git(file_path, entity_data, "project")
        
        assert result is False
        assert not file_path.exists()


class TestDeleteEntity:
    """Tests for the main delete_entity method"""
    
    def test_delete_entity_by_uid(self, registry_with_entities):
        """Test deleting entity by UID"""
        operation = DeleteOperation(str(registry_with_entities))
        file_path = registry_with_entities / "projects" / "proj-proj0001.yml"
        
        assert file_path.exists()
        
        result = operation.delete_entity("proj0001", use_git=False)
        
        assert result["success"] is True
        assert result["identifier"] == "proj0001"
        assert result["deleted_title"] == "Test Project One"
        assert result["deleted_type"] == "project"
        assert not file_path.exists()
    
    def test_delete_entity_by_human_id(self, registry_with_entities):
        """Test deleting entity by human-readable ID"""
        operation = DeleteOperation(str(registry_with_entities))
        
        result = operation.delete_entity("P-001", use_git=False)
        
        assert result["success"] is True
        assert result["deleted_title"] == "Test Project One"
    
    def test_delete_entity_with_type_filter(self, registry_with_entities):
        """Test deleting entity with type filter"""
        operation = DeleteOperation(str(registry_with_entities))
        
        result = operation.delete_entity(
            "prog0001",
            entity_type=EntityType.PROGRAM,
            use_git=False,
        )
        
        assert result["success"] is True
        assert result["deleted_type"] == "program"
    
    def test_delete_entity_all_types(self, registry_with_entities):
        """Test deleting each entity type"""
        operation = DeleteOperation(str(registry_with_entities))
        
        # Delete project
        result = operation.delete_entity("proj0001", use_git=False)
        assert result["success"] is True
        assert result["deleted_type"] == "project"
        
        # Delete program
        result = operation.delete_entity("prog0001", use_git=False)
        assert result["success"] is True
        assert result["deleted_type"] == "program"
        
        # Delete mission
        result = operation.delete_entity("miss0001", use_git=False)
        assert result["success"] is True
        assert result["deleted_type"] == "mission"
        
        # Delete action
        result = operation.delete_entity("act0001", use_git=False)
        assert result["success"] is True
        assert result["deleted_type"] == "action"
    
    def test_delete_entity_not_found(self, temp_registry):
        """Test that EntityNotFoundError is raised for missing entity"""
        operation = DeleteOperation(str(temp_registry))
        
        with pytest.raises(EntityNotFoundError) as exc_info:
            operation.delete_entity("nonexistent", use_git=False)
        
        assert "nonexistent" in str(exc_info.value)
    
    def test_delete_entity_returns_entity_data(self, registry_with_entities):
        """Test that deleted entity data is returned"""
        operation = DeleteOperation(str(registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=False)
        
        assert result["success"] is True
        assert "entity" in result
        assert result["entity"]["type"] == "project"
        assert result["entity"]["uid"] == "proj0001"
    
    def test_delete_entity_returns_file_path(self, registry_with_entities):
        """Test that file path is returned"""
        operation = DeleteOperation(str(registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=False)
        
        assert result["success"] is True
        assert "file_path" in result
        assert "proj-proj0001.yml" in result["file_path"]
    
    def test_delete_entity_git_committed_false_when_use_git_false(self, registry_with_entities):
        """Test that git_committed is False when use_git=False"""
        operation = DeleteOperation(str(registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=False)
        
        assert result["success"] is True
        assert result["git_committed"] is False
    
    def test_delete_entity_with_git_integration(self, git_registry_with_entities):
        """Test deleting with git creates commit"""
        operation = DeleteOperation(str(git_registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=True)
        
        assert result["success"] is True
        assert result["git_committed"] is True
        
        # Verify commit exists
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        
        assert "Delete" in log.stdout
    
    def test_delete_entity_default_use_git_is_true(self, git_registry_with_entities):
        """Test that use_git defaults to True"""
        operation = DeleteOperation(str(git_registry_with_entities))
        
        result = operation.delete_entity("proj0001")
        
        assert result["success"] is True
        assert result["git_committed"] is True


class TestDeleteEntityAmbiguous:
    """Tests for ambiguous entity handling"""
    
    @pytest.fixture
    def registry_with_duplicate_uid(self, temp_registry):
        """Create a registry with same UID in different entity types"""
        # Create project with uid "duplicate"
        project = {
            "type": "project",
            "uid": "duplicate",
            "id": "P-DUP",
            "title": "Duplicate Project",
            "status": "active",
        }
        with open(temp_registry / "projects" / "proj-duplicate.yml", "w") as f:
            yaml.dump(project, f)
        
        # Create mission with same uid "duplicate"
        mission = {
            "type": "mission",
            "uid": "duplicate",
            "id": "M-DUP",
            "title": "Duplicate Mission",
            "status": "active",
        }
        with open(temp_registry / "missions" / "miss-duplicate.yml", "w") as f:
            yaml.dump(mission, f)
        
        return temp_registry
    
    def test_delete_ambiguous_raises_error(self, registry_with_duplicate_uid):
        """Test that ambiguous identifier raises AmbiguousEntityError"""
        operation = DeleteOperation(str(registry_with_duplicate_uid))
        
        with pytest.raises(AmbiguousEntityError) as exc_info:
            operation.delete_entity("duplicate", use_git=False)
        
        assert "duplicate" in str(exc_info.value)
        assert "Multiple entities" in str(exc_info.value)
    
    def test_delete_ambiguous_with_type_filter_succeeds(self, registry_with_duplicate_uid):
        """Test that type filter resolves ambiguity"""
        operation = DeleteOperation(str(registry_with_duplicate_uid))
        
        # Delete project specifically
        result = operation.delete_entity(
            "duplicate",
            entity_type=EntityType.PROJECT,
            use_git=False,
        )
        
        assert result["success"] is True
        assert result["deleted_type"] == "project"
        
        # Mission should still exist
        assert (registry_with_duplicate_uid / "missions" / "miss-duplicate.yml").exists()


class TestGetEntityInfo:
    """Tests for get_entity_info method"""
    
    def test_get_entity_info_returns_info(self, registry_with_entities):
        """Test getting entity info"""
        operation = DeleteOperation(str(registry_with_entities))
        
        info = operation.get_entity_info("proj0001")
        
        assert info["success"] is True
        assert info["identifier"] == "proj0001"
        assert info["entity_title"] == "Test Project One"
        assert info["entity_type"] == "project"
        assert "file_path" in info
        assert "entity" in info
    
    def test_get_entity_info_by_human_id(self, registry_with_entities):
        """Test getting entity info by human-readable ID"""
        operation = DeleteOperation(str(registry_with_entities))
        
        info = operation.get_entity_info("P-001")
        
        assert info["success"] is True
        assert info["entity_title"] == "Test Project One"
    
    def test_get_entity_info_with_type_filter(self, registry_with_entities):
        """Test getting entity info with type filter"""
        operation = DeleteOperation(str(registry_with_entities))
        
        info = operation.get_entity_info("prog0001", EntityType.PROGRAM)
        
        assert info["success"] is True
        assert info["entity_type"] == "program"
    
    def test_get_entity_info_not_found(self, temp_registry):
        """Test that EntityNotFoundError is raised for missing entity"""
        operation = DeleteOperation(str(temp_registry))
        
        with pytest.raises(EntityNotFoundError) as exc_info:
            operation.get_entity_info("nonexistent")
        
        assert "nonexistent" in str(exc_info.value)
    
    def test_get_entity_info_ambiguous(self, temp_registry):
        """Test that AmbiguousEntityError is raised for ambiguous match"""
        # Create entities with same uid in different types
        project = {"type": "project", "uid": "same", "id": "P-SAME", "title": "Same Project"}
        with open(temp_registry / "projects" / "proj-same.yml", "w") as f:
            yaml.dump(project, f)
        
        mission = {"type": "mission", "uid": "same", "id": "M-SAME", "title": "Same Mission"}
        with open(temp_registry / "missions" / "miss-same.yml", "w") as f:
            yaml.dump(mission, f)
        
        operation = DeleteOperation(str(temp_registry))
        
        with pytest.raises(AmbiguousEntityError):
            operation.get_entity_info("same")
    
    def test_get_entity_info_includes_full_entity(self, registry_with_entities):
        """Test that full entity data is included"""
        operation = DeleteOperation(str(registry_with_entities))
        
        info = operation.get_entity_info("proj0001")
        
        assert info["success"] is True
        entity = info["entity"]
        assert entity["type"] == "project"
        assert entity["uid"] == "proj0001"
        assert entity["id"] == "P-001"
        assert entity["title"] == "Test Project One"
        assert entity["status"] == "active"


class TestDeleteEntityGitIntegration:
    """Integration tests for git functionality"""
    
    def test_delete_creates_proper_commit_message(self, git_registry_with_entities):
        """Test that commit message includes all required information"""
        operation = DeleteOperation(str(git_registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=True)
        
        assert result["success"] is True
        
        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        
        message = log.stdout
        
        # Verify all components are present
        assert "Delete" in message
        assert "proj-proj0001" in message
        assert "Git Project" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: proj0001" in message
    
    def test_delete_file_removed_from_git_index(self, git_registry_with_entities):
        """Test that file is removed from git index"""
        operation = DeleteOperation(str(git_registry_with_entities))
        
        operation.delete_entity("proj0001", use_git=True)
        
        # Check git status
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        
        # File should not appear in status (committed)
        assert "proj-proj0001.yml" not in status.stdout
    
    def test_delete_sequential_commits(self, git_registry_with_entities):
        """Test multiple sequential deletions create separate commits"""
        # Add another entity for deletion
        project2 = {
            "type": "project",
            "uid": "proj0002",
            "id": "P-002",
            "title": "Second Project",
            "status": "active",
        }
        with open(git_registry_with_entities / "projects" / "proj-proj0002.yml", "w") as f:
            yaml.dump(project2, f)
        
        subprocess.run(["git", "add", "."], cwd=git_registry_with_entities, check=True)
        subprocess.run(["git", "commit", "-m", "Add second project"],
                      cwd=git_registry_with_entities, check=True)
        
        operation = DeleteOperation(str(git_registry_with_entities))
        
        # Delete first
        result1 = operation.delete_entity("proj0001", use_git=True)
        assert result1["success"] is True
        
        # Delete second
        result2 = operation.delete_entity("proj0002", use_git=True)
        assert result2["success"] is True
        
        # Count commits
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        
        lines = log.stdout.strip().splitlines()
        # Should have at least: initial + add entities + add second + 2 deletes
        assert len(lines) >= 4
    
    def test_delete_non_git_registry_no_commit(self, registry_with_entities, capsys):
        """Test that non-git registry doesn't try to commit"""
        operation = DeleteOperation(str(registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=True)
        
        assert result["success"] is True
        assert result["git_committed"] is False
        
        # File should still be deleted
        assert not (registry_with_entities / "projects" / "proj-proj0001.yml").exists()


class TestDeleteOperationErrorHandling:
    """Tests for error handling"""
    
    def test_delete_path_traversal_blocked(self, temp_registry, tmp_path):
        """Test that path traversal attempts are blocked"""
        # Create file outside registry
        external = tmp_path / "external.yml"
        external.write_text("external: data")
        
        operation = DeleteOperation(str(temp_registry))
        
        # Try to delete with path traversal
        with pytest.raises(EntityNotFoundError):
            operation.delete_entity("../external", use_git=False)
        
        # External file should still exist
        assert external.exists()
    
    def test_delete_handles_io_error(self, registry_with_entities):
        """Test that IO errors are handled"""
        operation = DeleteOperation(str(registry_with_entities))
        
        with patch("os.remove", side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                operation.delete_entity("proj0001", use_git=False)
    
    def test_delete_handles_yaml_load_error(self, temp_registry):
        """Test handling of YAML load errors during deletion"""
        # Create entity with valid filename but invalid content
        invalid_file = temp_registry / "projects" / "proj-invalid.yml"
        invalid_file.write_text("{ not valid yaml [")
        
        operation = DeleteOperation(str(temp_registry))
        
        # Search finds it, but load fails
        with pytest.raises(Exception):
            operation.delete_entity("invalid", use_git=False)


class TestExceptionClasses:
    """Tests for custom exception classes"""
    
    def test_delete_operation_error_is_exception(self):
        """Test that DeleteOperationError is an Exception"""
        error = DeleteOperationError("test error")
        assert isinstance(error, Exception)
    
    def test_entity_not_found_error_inherits(self):
        """Test that EntityNotFoundError inherits from DeleteOperationError"""
        error = EntityNotFoundError("not found")
        assert isinstance(error, DeleteOperationError)
        assert isinstance(error, Exception)
    
    def test_ambiguous_entity_error_inherits(self):
        """Test that AmbiguousEntityError inherits from DeleteOperationError"""
        error = AmbiguousEntityError("ambiguous")
        assert isinstance(error, DeleteOperationError)
        assert isinstance(error, Exception)
    
    def test_exception_preserves_message(self):
        """Test that exception messages are preserved"""
        message = "Custom error message"
        
        error1 = DeleteOperationError(message)
        assert str(error1) == message
        
        error2 = EntityNotFoundError(message)
        assert str(error2) == message
        
        error3 = AmbiguousEntityError(message)
        assert str(error3) == message


class TestDeleteOperationCLIMCPParity:
    """Tests to verify behavioral parity between CLI and MCP interfaces"""
    
    def test_commit_message_format_matches_cli(self, git_registry_with_entities):
        """Test that commit message format matches CLI implementation"""
        operation = DeleteOperation(str(git_registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=True)
        
        assert result["success"] is True
        
        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry_with_entities,
            capture_output=True,
            text=True,
            check=True,
        )
        
        message = log.stdout
        
        # Subject line format: "Delete {prefix}-{uid}: {title}"
        assert "Delete proj-proj0001: Git Project" in message
        
        # Body contains entity metadata
        assert "Entity type: project" in message
        assert "Entity ID: P-001" in message
        assert "Entity UID: proj0001" in message
    
    def test_file_prefix_conventions(self, registry_with_entities):
        """Test that file prefixes match expected conventions"""
        operation = DeleteOperation(str(registry_with_entities))
        
        # Delete each type and verify prefix in file path
        tests = [
            ("proj0001", "proj-"),
            ("prog0001", "prog-"),
            ("miss0001", "miss-"),
            ("act0001", "act-"),
        ]
        
        for identifier, expected_prefix in tests:
            info = operation.get_entity_info(identifier)
            assert expected_prefix in info["file_path"]
    
    def test_return_structure_consistency(self, registry_with_entities):
        """Test that return structure is consistent"""
        operation = DeleteOperation(str(registry_with_entities))
        
        result = operation.delete_entity("proj0001", use_git=False)
        
        # All expected keys should be present
        expected_keys = {
            "success",
            "identifier",
            "deleted_title",
            "deleted_type",
            "file_path",
            "entity",
            "git_committed",
        }
        
        assert set(result.keys()) == expected_keys
    
    def test_entity_info_return_structure(self, registry_with_entities):
        """Test that get_entity_info return structure is consistent"""
        operation = DeleteOperation(str(registry_with_entities))
        
        info = operation.get_entity_info("proj0001")
        
        expected_keys = {
            "success",
            "identifier",
            "entity_title",
            "entity_type",
            "file_path",
            "entity",
        }
        
        assert set(info.keys()) == expected_keys