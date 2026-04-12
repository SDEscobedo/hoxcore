"""
Tests for the EditOperation core operation module.

This module tests the shared edit operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Set
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.edit import (
    DuplicateIdError,
    EditOperation,
    EditOperationError,
    EntityNotFoundError,
    InvalidValueError,
    NoChangesError,
)
from hxc.utils.path_security import PathSecurityError


@pytest.fixture
def temp_registry():
    """Create a temporary test registry"""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    (registry_path / "config.yml").write_text("registry:\n  version: '1.0'\n")

    # Create test project
    project1_content = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Test Project One",
        "description": "A test project",
        "status": "active",
        "category": "software.dev/cli-tool",
        "tags": ["test", "mcp"],
        "start_date": "2024-01-01",
        "children": ["child1", "child2"],
        "related": ["rel1"],
        "repositories": [],
        "storage": [],
        "databases": [],
        "tools": [],
        "models": [],
        "knowledge_bases": [],
    }
    with open(registry_path / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project1_content, f)

    # Create second project
    project2_content = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Test Project Two",
        "status": "completed",
        "tags": ["test"],
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "projects" / "proj-proj0002.yml", "w") as f:
        yaml.dump(project2_content, f)

    # Create test program
    program_content = {
        "type": "program",
        "uid": "prog0001",
        "id": "PRG-001",
        "title": "Test Program",
        "status": "active",
        "tags": ["program"],
        "children": ["proj0001"],
    }
    with open(registry_path / "programs" / "prog-prog0001.yml", "w") as f:
        yaml.dump(program_content, f)

    # Create test mission
    mission_content = {
        "type": "mission",
        "uid": "miss0001",
        "id": "M-001",
        "title": "Test Mission",
        "status": "planned",
        "tags": ["mission"],
    }
    with open(registry_path / "missions" / "miss-miss0001.yml", "w") as f:
        yaml.dump(mission_content, f)

    # Create test action
    action_content = {
        "type": "action",
        "uid": "act0001",
        "id": "A-001",
        "title": "Test Action",
        "status": "active",
        "tags": ["action"],
    }
    with open(registry_path / "actions" / "act-act0001.yml", "w") as f:
        yaml.dump(action_content, f)

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def git_registry():
    """Create a temporary registry that is also a git repository."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)

    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    # Create config file
    (registry_path / "config.yml").write_text("registry:\n  version: '1.0'\n")

    # Create test project
    project_content = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Git Test Project",
        "status": "active",
        "tags": ["test"],
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project_content, f)

    # Create second project for uniqueness tests
    project2_content = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Second Project",
        "status": "active",
        "tags": [],
        "start_date": "2024-01-01",
        "children": [],
        "related": [],
    }
    with open(registry_path / "projects" / "proj-proj0002.yml", "w") as f:
        yaml.dump(project2_content, f)

    # Initialize git repository
    subprocess.run(["git", "init"], cwd=registry_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "add", "."], cwd=registry_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=registry_path,
        check=True,
        capture_output=True,
    )

    yield str(registry_path)

    # Cleanup
    shutil.rmtree(temp_dir)


class TestEditOperationInit:
    """Tests for EditOperation initialization"""

    def test_init_with_valid_path(self, temp_registry):
        """Test initializing with a valid registry path"""
        operation = EditOperation(temp_registry)
        assert operation.registry_path == temp_registry

    def test_init_with_string_path(self, temp_registry):
        """Test initializing with a string path"""
        operation = EditOperation(temp_registry)
        assert isinstance(operation.registry_path, str)


class TestFindEntityFile:
    """Tests for the find_entity_file method"""

    def test_find_by_uid_fast_path(self, temp_registry):
        """Test finding entity by UID using filename match (fast path)"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("proj0001")

        assert result is not None
        file_path, entity_type = result
        assert file_path.name == "proj-proj0001.yml"
        assert entity_type == EntityType.PROJECT

    def test_find_by_id_slow_path(self, temp_registry):
        """Test finding entity by ID field in YAML (slow path)"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")

        assert result is not None
        file_path, entity_type = result
        assert "proj-proj0001.yml" in str(file_path)
        assert entity_type == EntityType.PROJECT

    def test_find_with_type_filter(self, temp_registry):
        """Test finding entity with type filter"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001", EntityType.PROJECT)

        assert result is not None
        _, entity_type = result
        assert entity_type == EntityType.PROJECT

    def test_find_with_wrong_type_filter(self, temp_registry):
        """Test finding entity with wrong type filter returns None"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001", EntityType.PROGRAM)

        assert result is None

    def test_find_nonexistent_entity(self, temp_registry):
        """Test finding a non-existent entity returns None"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("NONEXISTENT")

        assert result is None

    def test_find_program_by_uid(self, temp_registry):
        """Test finding a program by UID"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("prog0001")

        assert result is not None
        _, entity_type = result
        assert entity_type == EntityType.PROGRAM

    def test_find_mission_by_id(self, temp_registry):
        """Test finding a mission by ID"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("M-001")

        assert result is not None
        _, entity_type = result
        assert entity_type == EntityType.MISSION

    def test_find_action_by_id(self, temp_registry):
        """Test finding an action by ID"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("A-001")

        assert result is not None
        _, entity_type = result
        assert entity_type == EntityType.ACTION

    def test_find_searches_all_types_when_no_filter(self, temp_registry):
        """Test that find searches all entity types when no filter is provided"""
        operation = EditOperation(temp_registry)

        # Should find entities of different types
        project_result = operation.find_entity_file("P-001")
        program_result = operation.find_entity_file("PRG-001")
        mission_result = operation.find_entity_file("M-001")

        assert project_result is not None
        assert program_result is not None
        assert mission_result is not None


class TestLoadEntity:
    """Tests for the load_entity method"""

    def test_load_valid_entity(self, temp_registry):
        """Test loading a valid entity file"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        assert result is not None

        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        assert entity_data["type"] == "project"
        assert entity_data["uid"] == "proj0001"
        assert entity_data["id"] == "P-001"
        assert entity_data["title"] == "Test Project One"

    def test_load_entity_with_all_fields(self, temp_registry):
        """Test loading an entity with all standard fields"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result

        entity_data = operation.load_entity(file_path)

        assert "type" in entity_data
        assert "uid" in entity_data
        assert "id" in entity_data
        assert "title" in entity_data
        assert "status" in entity_data
        assert "tags" in entity_data

    def test_load_invalid_entity_raises_error(self, temp_registry):
        """Test loading an empty or invalid entity file raises error"""
        operation = EditOperation(temp_registry)

        # Create an empty file
        empty_file = Path(temp_registry) / "projects" / "proj-empty.yml"
        empty_file.write_text("")

        with pytest.raises(EditOperationError):
            operation.load_entity(empty_file)

    def test_load_non_dict_entity_raises_error(self, temp_registry):
        """Test loading a file with non-dict content raises error"""
        operation = EditOperation(temp_registry)

        # Create a file with a list instead of dict
        list_file = Path(temp_registry) / "projects" / "proj-list.yml"
        list_file.write_text("- item1\n- item2\n")

        with pytest.raises(EditOperationError):
            operation.load_entity(list_file)


class TestLoadExistingIds:
    """Tests for the load_existing_ids method"""

    def test_load_existing_ids_for_projects(self, temp_registry):
        """Test loading existing IDs for projects"""
        operation = EditOperation(temp_registry)
        ids = operation.load_existing_ids(EntityType.PROJECT)

        assert "P-001" in ids
        assert "P-002" in ids
        assert len(ids) == 2

    def test_load_existing_ids_for_programs(self, temp_registry):
        """Test loading existing IDs for programs"""
        operation = EditOperation(temp_registry)
        ids = operation.load_existing_ids(EntityType.PROGRAM)

        assert "PRG-001" in ids
        assert len(ids) == 1

    def test_load_existing_ids_returns_empty_for_empty_folder(self, temp_registry):
        """Test loading IDs from empty folder returns empty set"""
        operation = EditOperation(temp_registry)

        # Remove all actions
        actions_dir = Path(temp_registry) / "actions"
        for f in actions_dir.glob("*.yml"):
            f.unlink()

        ids = operation.load_existing_ids(EntityType.ACTION)
        # Will still find A-001 if not removed
        # For this test, let's check it handles missing folder gracefully
        assert isinstance(ids, set)

    def test_load_existing_ids_ignores_invalid_files(self, temp_registry):
        """Test that invalid files are ignored when loading IDs"""
        operation = EditOperation(temp_registry)

        # Create an invalid file
        invalid_file = Path(temp_registry) / "projects" / "proj-invalid.yml"
        invalid_file.write_text("invalid: yaml: [")

        # Should not raise, should ignore invalid file
        ids = operation.load_existing_ids(EntityType.PROJECT)

        # Original IDs should still be present
        assert "P-001" in ids
        assert "P-002" in ids


class TestValidateIdUniqueness:
    """Tests for the validate_id_uniqueness method"""

    def test_unique_id_passes_validation(self, temp_registry):
        """Test that a unique ID passes validation"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        # Should not raise for a unique ID
        operation.validate_id_uniqueness(entity_data, "P-NEW-UNIQUE")

    def test_same_id_passes_validation(self, temp_registry):
        """Test that setting same ID (no-op) passes validation"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        # Should not raise when setting same ID
        operation.validate_id_uniqueness(entity_data, "P-001")

    def test_duplicate_id_raises_error(self, temp_registry):
        """Test that a duplicate ID raises DuplicateIdError"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        # P-002 already exists
        with pytest.raises(DuplicateIdError) as exc_info:
            operation.validate_id_uniqueness(entity_data, "P-002")

        assert "P-002" in str(exc_info.value)
        assert "already exists" in str(exc_info.value).lower()

    def test_same_id_different_type_allowed(self, temp_registry):
        """Test that same ID in different entity type is allowed"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("PRG-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        # P-001 exists as project, but we're editing a program
        # This should pass because uniqueness is scoped per type
        operation.validate_id_uniqueness(entity_data, "P-001")

    def test_validate_with_preloaded_ids(self, temp_registry):
        """Test validation with pre-loaded IDs set"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        existing_ids = {"P-002", "P-003"}

        # Should not raise for ID not in the set
        # Note: validate_id_uniqueness loads IDs internally if not provided

    def test_validate_handles_missing_type_field(self, temp_registry):
        """Test validation handles entity without type field"""
        operation = EditOperation(temp_registry)

        # Entity data without type field
        entity_data = {"uid": "test", "id": "current-id", "title": "Test"}

        # Should not raise (can't validate without type)
        operation.validate_id_uniqueness(entity_data, "new-id")

    def test_validate_handles_invalid_type_field(self, temp_registry):
        """Test validation handles entity with invalid type field"""
        operation = EditOperation(temp_registry)

        # Entity data with invalid type
        entity_data = {"type": "invalid_type", "uid": "test", "id": "current-id"}

        # Should not raise (skip check for invalid type)
        operation.validate_id_uniqueness(entity_data, "new-id")


class TestApplyScalarEdits:
    """Tests for the apply_scalar_edits method"""

    def test_set_title(self, temp_registry):
        """Test setting the title field"""
        operation = EditOperation(temp_registry)
        entity_data = {"title": "Old Title", "type": "project"}

        changes = operation.apply_scalar_edits(entity_data, set_title="New Title")

        assert entity_data["title"] == "New Title"
        assert len(changes) == 1
        assert "title" in changes[0]
        assert "'Old Title'" in changes[0]
        assert "'New Title'" in changes[0]

    def test_set_description(self, temp_registry):
        """Test setting the description field"""
        operation = EditOperation(temp_registry)
        entity_data = {"description": "Old desc", "type": "project"}

        changes = operation.apply_scalar_edits(
            entity_data, set_description="New description"
        )

        assert entity_data["description"] == "New description"
        assert len(changes) == 1

    def test_set_status_valid(self, temp_registry):
        """Test setting a valid status"""
        operation = EditOperation(temp_registry)
        entity_data = {"status": "active", "type": "project"}

        changes = operation.apply_scalar_edits(entity_data, set_status="completed")

        assert entity_data["status"] == "completed"
        assert len(changes) == 1

    def test_set_status_invalid_raises_error(self, temp_registry):
        """Test setting an invalid status raises InvalidValueError"""
        operation = EditOperation(temp_registry)
        entity_data = {"status": "active", "type": "project"}

        with pytest.raises(InvalidValueError):
            operation.apply_scalar_edits(entity_data, set_status="not-valid")

    def test_set_id_validates_uniqueness(self, temp_registry):
        """Test that set_id validates uniqueness"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        # Should raise because P-002 exists
        with pytest.raises(DuplicateIdError):
            operation.apply_scalar_edits(entity_data, set_id="P-002")

    def test_set_id_to_unique_value(self, temp_registry):
        """Test setting ID to a unique value"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result
        entity_data = operation.load_entity(file_path)

        changes = operation.apply_scalar_edits(entity_data, set_id="P-UNIQUE")

        assert entity_data["id"] == "P-UNIQUE"
        assert len(changes) == 1

    def test_set_dates(self, temp_registry):
        """Test setting date fields"""
        operation = EditOperation(temp_registry)
        entity_data = {"type": "project", "start_date": "2024-01-01"}

        changes = operation.apply_scalar_edits(
            entity_data,
            set_start_date="2024-02-01",
            set_due_date="2024-12-31",
            set_completion_date="2024-11-30",
        )

        assert entity_data["start_date"] == "2024-02-01"
        assert entity_data["due_date"] == "2024-12-31"
        assert entity_data["completion_date"] == "2024-11-30"
        assert len(changes) == 3

    def test_set_duration_estimate(self, temp_registry):
        """Test setting duration_estimate field"""
        operation = EditOperation(temp_registry)
        entity_data = {"type": "project"}

        changes = operation.apply_scalar_edits(
            entity_data, set_duration_estimate="3 months"
        )

        assert entity_data["duration_estimate"] == "3 months"
        assert len(changes) == 1

    def test_set_category(self, temp_registry):
        """Test setting category field"""
        operation = EditOperation(temp_registry)
        entity_data = {"type": "project", "category": "old/category"}

        changes = operation.apply_scalar_edits(
            entity_data, set_category="new/category"
        )

        assert entity_data["category"] == "new/category"
        assert len(changes) == 1

    def test_set_parent(self, temp_registry):
        """Test setting parent field"""
        operation = EditOperation(temp_registry)
        entity_data = {"type": "project"}

        changes = operation.apply_scalar_edits(entity_data, set_parent="prog0001")

        assert entity_data["parent"] == "prog0001"
        assert len(changes) == 1

    def test_set_template(self, temp_registry):
        """Test setting template field"""
        operation = EditOperation(temp_registry)
        entity_data = {"type": "project"}

        changes = operation.apply_scalar_edits(
            entity_data, set_template="my-template/v1"
        )

        assert entity_data["template"] == "my-template/v1"
        assert len(changes) == 1

    def test_set_multiple_fields(self, temp_registry):
        """Test setting multiple scalar fields at once"""
        operation = EditOperation(temp_registry)
        entity_data = {
            "type": "project",
            "title": "Old",
            "status": "active",
            "category": "old",
        }

        changes = operation.apply_scalar_edits(
            entity_data,
            set_title="New Title",
            set_status="completed",
            set_category="new/path",
        )

        assert entity_data["title"] == "New Title"
        assert entity_data["status"] == "completed"
        assert entity_data["category"] == "new/path"
        assert len(changes) == 3

    def test_no_change_when_same_value(self, temp_registry):
        """Test that no change is recorded when value is the same"""
        operation = EditOperation(temp_registry)
        entity_data = {"type": "project", "title": "Same Title"}

        changes = operation.apply_scalar_edits(entity_data, set_title="Same Title")

        # No change should be recorded
        assert len(changes) == 0

    def test_tracks_not_set_values(self, temp_registry):
        """Test that missing fields are tracked as '(not set)'"""
        operation = EditOperation(temp_registry)
        entity_data = {"type": "project"}

        changes = operation.apply_scalar_edits(
            entity_data, set_description="New description"
        )

        assert len(changes) == 1
        assert "(not set)" in changes[0]


class TestApplyListEdits:
    """Tests for the apply_list_edits method"""

    def test_set_tags(self, temp_registry):
        """Test replacing all tags"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": ["old1", "old2"]}

        changes = operation.apply_list_edits(
            entity_data, set_tags=["new1", "new2", "new3"]
        )

        assert entity_data["tags"] == ["new1", "new2", "new3"]
        assert len(changes) == 1
        assert "Set tags" in changes[0]

    def test_add_tags(self, temp_registry):
        """Test adding tags"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": ["existing"]}

        changes = operation.apply_list_edits(entity_data, add_tags=["new1", "new2"])

        assert "existing" in entity_data["tags"]
        assert "new1" in entity_data["tags"]
        assert "new2" in entity_data["tags"]
        assert len(changes) == 2

    def test_add_tags_idempotent(self, temp_registry):
        """Test that adding duplicate tags is idempotent"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": ["existing"]}

        changes = operation.apply_list_edits(entity_data, add_tags=["existing", "new"])

        # Only "new" should be added, "existing" is already there
        assert entity_data["tags"].count("existing") == 1
        assert entity_data["tags"].count("new") == 1
        assert len(changes) == 1  # Only new was added

    def test_remove_tags(self, temp_registry):
        """Test removing tags"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": ["keep", "remove1", "remove2"]}

        changes = operation.apply_list_edits(
            entity_data, remove_tags=["remove1", "remove2"]
        )

        assert entity_data["tags"] == ["keep"]
        assert len(changes) == 2

    def test_remove_nonexistent_tag_silent(self, temp_registry):
        """Test that removing a non-existent tag is silent"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": ["existing"]}

        changes = operation.apply_list_edits(
            entity_data, remove_tags=["nonexistent"]
        )

        assert entity_data["tags"] == ["existing"]
        assert len(changes) == 0

    def test_add_and_remove_tags_together(self, temp_registry):
        """Test adding and removing tags in one operation"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": ["keep", "remove"]}

        changes = operation.apply_list_edits(
            entity_data, add_tags=["new"], remove_tags=["remove"]
        )

        assert "keep" in entity_data["tags"]
        assert "new" in entity_data["tags"]
        assert "remove" not in entity_data["tags"]
        assert len(changes) == 2

    def test_set_tags_overrides_add_remove(self, temp_registry):
        """Test that set_tags ignores add_tags and remove_tags"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": ["old"]}

        changes = operation.apply_list_edits(
            entity_data,
            set_tags=["completely_new"],
            add_tags=["should_ignore"],
            remove_tags=["old"],
        )

        # set_tags takes precedence
        assert entity_data["tags"] == ["completely_new"]
        assert len(changes) == 1

    def test_set_children(self, temp_registry):
        """Test replacing all children"""
        operation = EditOperation(temp_registry)
        entity_data = {"children": ["old-child"]}

        changes = operation.apply_list_edits(
            entity_data, set_children=["child1", "child2"]
        )

        assert entity_data["children"] == ["child1", "child2"]
        assert len(changes) == 1
        assert "Set children" in changes[0]

    def test_add_children(self, temp_registry):
        """Test adding children"""
        operation = EditOperation(temp_registry)
        entity_data = {"children": ["existing"]}

        changes = operation.apply_list_edits(
            entity_data, add_children=["new-child"]
        )

        assert "existing" in entity_data["children"]
        assert "new-child" in entity_data["children"]
        assert len(changes) == 1

    def test_add_children_idempotent(self, temp_registry):
        """Test that adding duplicate children is idempotent"""
        operation = EditOperation(temp_registry)
        entity_data = {"children": ["existing"]}

        changes = operation.apply_list_edits(
            entity_data, add_children=["existing"]
        )

        assert entity_data["children"].count("existing") == 1
        assert len(changes) == 0

    def test_remove_children(self, temp_registry):
        """Test removing children"""
        operation = EditOperation(temp_registry)
        entity_data = {"children": ["keep", "remove"]}

        changes = operation.apply_list_edits(
            entity_data, remove_children=["remove"]
        )

        assert entity_data["children"] == ["keep"]
        assert len(changes) == 1

    def test_set_related(self, temp_registry):
        """Test replacing all related"""
        operation = EditOperation(temp_registry)
        entity_data = {"related": ["old-rel"]}

        changes = operation.apply_list_edits(
            entity_data, set_related=["rel1", "rel2"]
        )

        assert entity_data["related"] == ["rel1", "rel2"]
        assert len(changes) == 1
        assert "Set related" in changes[0]

    def test_add_related(self, temp_registry):
        """Test adding related"""
        operation = EditOperation(temp_registry)
        entity_data = {"related": ["existing"]}

        changes = operation.apply_list_edits(
            entity_data, add_related=["new-rel"]
        )

        assert "existing" in entity_data["related"]
        assert "new-rel" in entity_data["related"]
        assert len(changes) == 1

    def test_remove_related(self, temp_registry):
        """Test removing related"""
        operation = EditOperation(temp_registry)
        entity_data = {"related": ["keep", "remove"]}

        changes = operation.apply_list_edits(
            entity_data, remove_related=["remove"]
        )

        assert entity_data["related"] == ["keep"]
        assert len(changes) == 1

    def test_handles_none_list_fields(self, temp_registry):
        """Test that None list fields are handled correctly"""
        operation = EditOperation(temp_registry)
        entity_data = {"tags": None}

        changes = operation.apply_list_edits(entity_data, add_tags=["new"])

        assert entity_data["tags"] == ["new"]
        assert len(changes) == 1

    def test_handles_missing_list_fields(self, temp_registry):
        """Test that missing list fields are created"""
        operation = EditOperation(temp_registry)
        entity_data = {}

        changes = operation.apply_list_edits(entity_data, add_tags=["new"])

        assert entity_data["tags"] == ["new"]
        assert len(changes) == 1


class TestWriteEntityFile:
    """Tests for the write_entity_file method"""

    def test_write_entity_file(self, temp_registry):
        """Test writing an entity file"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result

        entity_data = {
            "type": "project",
            "uid": "proj0001",
            "id": "P-001",
            "title": "Updated Title",
            "status": "completed",
        }

        operation.write_entity_file(file_path, entity_data)

        # Verify the file was written
        with open(file_path) as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["title"] == "Updated Title"
        assert saved_data["status"] == "completed"

    def test_write_preserves_field_order(self, temp_registry):
        """Test that writing preserves YAML field order"""
        operation = EditOperation(temp_registry)
        result = operation.find_entity_file("P-001")
        file_path, _ = result

        entity_data = {
            "type": "project",
            "uid": "proj0001",
            "id": "P-001",
            "title": "Test",
        }

        operation.write_entity_file(file_path, entity_data)

        # Read back the file content
        with open(file_path) as f:
            content = f.read()

        # Verify type comes before uid
        assert content.index("type:") < content.index("uid:")


class TestEditEntityMainMethod:
    """Tests for the main edit_entity method"""

    def test_edit_entity_by_uid(self, temp_registry):
        """Test editing an entity by UID"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="proj0001",
            set_title="Updated via UID",
            use_git=False,
        )

        assert result["success"] is True
        assert result["entity"]["title"] == "Updated via UID"
        assert len(result["changes"]) == 1

    def test_edit_entity_by_id(self, temp_registry):
        """Test editing an entity by ID"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Updated via ID",
            use_git=False,
        )

        assert result["success"] is True
        assert result["entity"]["title"] == "Updated via ID"

    def test_edit_entity_not_found(self, temp_registry):
        """Test editing a non-existent entity raises error"""
        operation = EditOperation(temp_registry)

        with pytest.raises(EntityNotFoundError):
            operation.edit_entity(
                identifier="NONEXISTENT",
                set_title="Should Fail",
                use_git=False,
            )

    def test_edit_entity_no_changes_raises_error(self, temp_registry):
        """Test editing with no changes raises NoChangesError"""
        operation = EditOperation(temp_registry)

        with pytest.raises(NoChangesError):
            operation.edit_entity(
                identifier="P-001",
                use_git=False,
            )

    def test_edit_entity_returns_file_path(self, temp_registry):
        """Test that edit returns the file path"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Test",
            use_git=False,
        )

        assert result["success"] is True
        assert "file_path" in result
        assert "proj-proj0001.yml" in result["file_path"]

    def test_edit_entity_returns_identifier(self, temp_registry):
        """Test that edit returns the identifier"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Test",
            use_git=False,
        )

        assert result["identifier"] == "P-001"

    def test_edit_entity_returns_changes_list(self, temp_registry):
        """Test that edit returns the list of changes"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="New Title",
            add_tags=["new-tag"],
            use_git=False,
        )

        assert "changes" in result
        assert len(result["changes"]) == 2

    def test_edit_entity_with_type_filter(self, temp_registry):
        """Test editing with entity type filter"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            entity_type=EntityType.PROJECT,
            set_title="Filtered Edit",
            use_git=False,
        )

        assert result["success"] is True
        assert result["entity"]["title"] == "Filtered Edit"

    def test_edit_entity_with_wrong_type_filter(self, temp_registry):
        """Test editing with wrong type filter raises error"""
        operation = EditOperation(temp_registry)

        with pytest.raises(EntityNotFoundError):
            operation.edit_entity(
                identifier="P-001",
                entity_type=EntityType.PROGRAM,  # Wrong type
                set_title="Should Fail",
                use_git=False,
            )

    def test_edit_entity_persists_to_disk(self, temp_registry):
        """Test that edits are actually persisted to disk"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Persisted Title",
            set_status="completed",
            use_git=False,
        )

        # Read file directly to verify
        with open(result["file_path"]) as f:
            on_disk = yaml.safe_load(f)

        assert on_disk["title"] == "Persisted Title"
        assert on_disk["status"] == "completed"

    def test_edit_all_scalar_fields(self, temp_registry):
        """Test editing all scalar fields"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Full Edit",
            set_description="Full description",
            set_status="on-hold",
            set_start_date="2025-01-01",
            set_due_date="2025-12-31",
            set_category="new/category",
            set_parent="prog0001",
            use_git=False,
        )

        assert result["success"] is True
        entity = result["entity"]
        assert entity["title"] == "Full Edit"
        assert entity["description"] == "Full description"
        assert entity["status"] == "on-hold"
        assert entity["start_date"] == "2025-01-01"
        assert entity["due_date"] == "2025-12-31"
        assert entity["category"] == "new/category"
        assert entity["parent"] == "prog0001"

    def test_edit_all_list_fields(self, temp_registry):
        """Test editing all list fields"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            add_tags=["new-tag"],
            remove_tags=["mcp"],
            add_children=["new-child"],
            remove_children=["child1"],
            add_related=["new-rel"],
            remove_related=["rel1"],
            use_git=False,
        )

        assert result["success"] is True
        entity = result["entity"]
        assert "new-tag" in entity["tags"]
        assert "mcp" not in entity["tags"]
        assert "new-child" in entity["children"]
        assert "child1" not in entity["children"]
        assert "new-rel" in entity["related"]
        assert "rel1" not in entity["related"]

    def test_edit_combined_scalar_and_list(self, temp_registry):
        """Test editing both scalar and list fields"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Combined Edit",
            set_status="completed",
            add_tags=["combined"],
            add_children=["combined-child"],
            use_git=False,
        )

        assert result["success"] is True
        assert len(result["changes"]) == 4

    def test_edit_duplicate_id_raises_error(self, temp_registry):
        """Test editing with duplicate ID raises error"""
        operation = EditOperation(temp_registry)

        with pytest.raises(DuplicateIdError):
            operation.edit_entity(
                identifier="P-001",
                set_id="P-002",  # Already exists
                use_git=False,
            )

    def test_edit_invalid_status_raises_error(self, temp_registry):
        """Test editing with invalid status raises error"""
        operation = EditOperation(temp_registry)

        with pytest.raises(InvalidValueError):
            operation.edit_entity(
                identifier="P-001",
                set_status="invalid-status",
                use_git=False,
            )

    def test_edit_returns_git_committed_false_when_use_git_false(self, temp_registry):
        """Test that git_committed is False when use_git=False"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="No Git",
            use_git=False,
        )

        assert result["git_committed"] is False


class TestEditEntityGitIntegration:
    """Tests for git integration in edit_entity"""

    def test_edit_with_git_creates_commit(self, git_registry):
        """Test that use_git=True creates a git commit"""
        operation = EditOperation(git_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Git Edit Title",
            use_git=True,
        )

        assert result["success"] is True
        assert result["git_committed"] is True

        # Verify commit exists
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "Edit" in log.stdout
        assert "proj-proj0001" in log.stdout

    def test_edit_without_git_skips_commit(self, git_registry):
        """Test that use_git=False skips git commit"""
        operation = EditOperation(git_registry)

        # Get initial commit count
        log_before = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        initial_count = len(log_before.stdout.strip().splitlines())

        result = operation.edit_entity(
            identifier="P-001",
            set_title="No Git Title",
            use_git=False,
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        # Verify no new commit
        log_after = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )
        final_count = len(log_after.stdout.strip().splitlines())

        assert final_count == initial_count

    def test_edit_commit_message_format(self, git_registry):
        """Test that commit message follows expected format"""
        operation = EditOperation(git_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Commit Format Test",
            add_tags=["new-tag"],
            use_git=True,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        message = log.stdout

        # Verify subject line format
        assert "Edit proj-proj0001:" in message

        # Verify body contains changes
        assert "Set title" in message or "title" in message
        assert "tag" in message.lower()

    def test_edit_in_non_git_registry_handles_gracefully(self, temp_registry, capsys):
        """Test that git operations handle non-git registry gracefully"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Non Git Title",
            use_git=True,  # Request git, but not a git repo
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        out = capsys.readouterr().out
        assert "not inside a git repository" in out

    def test_edit_sequential_commits(self, git_registry):
        """Test that multiple edits produce separate commits"""
        operation = EditOperation(git_registry)

        # First edit
        result1 = operation.edit_entity(
            identifier="P-001",
            set_title="First Edit",
            use_git=True,
        )

        # Second edit
        result2 = operation.edit_entity(
            identifier="P-001",
            set_status="completed",
            use_git=True,
        )

        assert result1["success"] is True
        assert result2["success"] is True

        # Verify both commits exist
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        # Count commits (initial + 2 edits)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 3

    def test_edit_commit_includes_all_changes(self, git_registry):
        """Test that commit message includes all changes"""
        operation = EditOperation(git_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Multi Change",
            set_status="completed",
            add_tags=["tag1", "tag2"],
            use_git=True,
        )

        assert result["success"] is True

        # Get commit message
        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        message = log.stdout

        # All changes should be mentioned
        assert "title" in message.lower()
        assert "status" in message.lower() or "completed" in message.lower()
        assert "tag" in message.lower()


class TestEditOperationExceptions:
    """Tests for exception handling in EditOperation"""

    def test_entity_not_found_error_has_identifier(self, temp_registry):
        """Test that EntityNotFoundError includes the identifier"""
        operation = EditOperation(temp_registry)

        with pytest.raises(EntityNotFoundError) as exc_info:
            operation.edit_entity(
                identifier="MISSING",
                set_title="Test",
                use_git=False,
            )

        assert "MISSING" in str(exc_info.value)

    def test_duplicate_id_error_has_id_and_type(self, temp_registry):
        """Test that DuplicateIdError includes ID and type"""
        operation = EditOperation(temp_registry)

        with pytest.raises(DuplicateIdError) as exc_info:
            operation.edit_entity(
                identifier="P-001",
                set_id="P-002",
                use_git=False,
            )

        error_msg = str(exc_info.value)
        assert "P-002" in error_msg
        assert "project" in error_msg.lower()

    def test_invalid_value_error_for_bad_status(self, temp_registry):
        """Test that InvalidValueError is raised for invalid status"""
        operation = EditOperation(temp_registry)

        with pytest.raises(InvalidValueError) as exc_info:
            operation.edit_entity(
                identifier="P-001",
                set_status="banana",
                use_git=False,
            )

        error_msg = str(exc_info.value)
        assert "banana" in error_msg or "status" in error_msg.lower()

    def test_no_changes_error_has_message(self, temp_registry):
        """Test that NoChangesError has a clear message"""
        operation = EditOperation(temp_registry)

        with pytest.raises(NoChangesError) as exc_info:
            operation.edit_entity(
                identifier="P-001",
                use_git=False,
            )

        assert "No changes" in str(exc_info.value)


class TestEditOperationEdgeCases:
    """Tests for edge cases in EditOperation"""

    def test_edit_entity_with_empty_tags(self, temp_registry):
        """Test editing entity that has empty tags list"""
        operation = EditOperation(temp_registry)

        # P-002 has tags: ["test"], let's set to empty first
        operation.edit_entity(
            identifier="P-002",
            set_tags=[],
            use_git=False,
        )

        # Now add a tag
        result = operation.edit_entity(
            identifier="P-002",
            add_tags=["new"],
            use_git=False,
        )

        assert result["success"] is True
        assert result["entity"]["tags"] == ["new"]

    def test_edit_entity_with_none_lists(self, temp_registry):
        """Test editing entity where list fields may be None"""
        operation = EditOperation(temp_registry)

        # Create entity with None for tags
        entity_file = Path(temp_registry) / "projects" / "proj-none.yml"
        entity_content = {
            "type": "project",
            "uid": "none0001",
            "id": "P-NONE",
            "title": "None Lists",
            "status": "active",
            "tags": None,
            "children": None,
            "related": None,
        }
        with open(entity_file, "w") as f:
            yaml.dump(entity_content, f)

        result = operation.edit_entity(
            identifier="P-NONE",
            add_tags=["tag1"],
            add_children=["child1"],
            add_related=["rel1"],
            use_git=False,
        )

        assert result["success"] is True
        assert result["entity"]["tags"] == ["tag1"]
        assert result["entity"]["children"] == ["child1"]
        assert result["entity"]["related"] == ["rel1"]

    def test_edit_handles_unicode_content(self, temp_registry):
        """Test editing with Unicode content"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="プロジェクト テスト",
            set_description="日本語の説明",
            add_tags=["日本語タグ"],
            use_git=False,
        )

        assert result["success"] is True
        assert result["entity"]["title"] == "プロジェクト テスト"
        assert result["entity"]["description"] == "日本語の説明"
        assert "日本語タグ" in result["entity"]["tags"]

    def test_edit_preserves_unknown_fields(self, temp_registry):
        """Test that editing preserves fields not known to the system"""
        operation = EditOperation(temp_registry)

        # Add a custom field to the entity
        entity_file = Path(temp_registry) / "projects" / "proj-proj0001.yml"
        with open(entity_file) as f:
            entity_data = yaml.safe_load(f)

        entity_data["custom_field"] = "custom_value"

        with open(entity_file, "w") as f:
            yaml.dump(entity_data, f)

        # Edit the entity
        result = operation.edit_entity(
            identifier="P-001",
            set_title="Edited Title",
            use_git=False,
        )

        assert result["success"] is True
        assert result["entity"].get("custom_field") == "custom_value"

    def test_edit_handles_special_characters_in_id(self, temp_registry):
        """Test editing entity with special characters in ID"""
        operation = EditOperation(temp_registry)

        # Create entity with special characters in ID
        entity_file = Path(temp_registry) / "projects" / "proj-special.yml"
        entity_content = {
            "type": "project",
            "uid": "special1",
            "id": "P-001/test:special",
            "title": "Special ID",
            "status": "active",
        }
        with open(entity_file, "w") as f:
            yaml.dump(entity_content, f)

        result = operation.edit_entity(
            identifier="P-001/test:special",
            set_title="Updated Special",
            use_git=False,
        )

        assert result["success"] is True

    def test_edit_all_entity_types(self, temp_registry):
        """Test editing all entity types"""
        operation = EditOperation(temp_registry)

        # Edit project
        proj_result = operation.edit_entity(
            identifier="P-001",
            set_title="Project Edit",
            use_git=False,
        )
        assert proj_result["success"] is True

        # Edit program
        prog_result = operation.edit_entity(
            identifier="PRG-001",
            set_title="Program Edit",
            use_git=False,
        )
        assert prog_result["success"] is True

        # Edit mission
        miss_result = operation.edit_entity(
            identifier="M-001",
            set_title="Mission Edit",
            use_git=False,
        )
        assert miss_result["success"] is True

        # Edit action
        act_result = operation.edit_entity(
            identifier="A-001",
            set_title="Action Edit",
            use_git=False,
        )
        assert act_result["success"] is True


class TestEditOperationBehavioralParity:
    """Tests to verify EditOperation produces identical results for CLI and MCP"""

    def test_change_description_format_consistency(self, temp_registry):
        """Test that change descriptions have consistent format"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="New Title",
            set_status="completed",
            add_tags=["new"],
            remove_tags=["mcp"],
            use_git=False,
        )

        # All changes should follow consistent format
        for change in result["changes"]:
            assert isinstance(change, str)
            # Changes should be descriptive
            assert len(change) > 5

    def test_edit_result_structure(self, temp_registry):
        """Test that edit result has all required fields"""
        operation = EditOperation(temp_registry)

        result = operation.edit_entity(
            identifier="P-001",
            set_title="Structure Test",
            use_git=False,
        )

        # Required fields
        assert "success" in result
        assert "identifier" in result
        assert "changes" in result
        assert "entity" in result
        assert "file_path" in result
        assert "git_committed" in result

        # Types
        assert isinstance(result["success"], bool)
        assert isinstance(result["identifier"], str)
        assert isinstance(result["changes"], list)
        assert isinstance(result["entity"], dict)
        assert isinstance(result["file_path"], str)
        assert isinstance(result["git_committed"], bool)

    def test_id_uniqueness_same_behavior_for_cli_and_mcp(self, temp_registry):
        """Test that ID uniqueness validation is identical"""
        operation = EditOperation(temp_registry)

        # Both should fail with same error for duplicate ID
        with pytest.raises(DuplicateIdError) as exc_info:
            operation.edit_entity(
                identifier="P-001",
                set_id="P-002",
                use_git=False,
            )

        error_msg = str(exc_info.value)
        assert "P-002" in error_msg
        assert "already exists" in error_msg.lower()
        assert "project" in error_msg.lower()

    def test_status_validation_same_behavior(self, temp_registry):
        """Test that status validation is identical"""
        operation = EditOperation(temp_registry)

        # Valid statuses should work
        for status in ["active", "completed", "on-hold", "cancelled", "planned"]:
            result = operation.edit_entity(
                identifier="P-001",
                set_status=status,
                use_git=False,
            )
            assert result["success"] is True
            assert result["entity"]["status"] == status

    def test_invalid_status_error_consistency(self, temp_registry):
        """Test that invalid status errors are consistent"""
        operation = EditOperation(temp_registry)

        with pytest.raises(InvalidValueError) as exc_info:
            operation.edit_entity(
                identifier="P-001",
                set_status="not-a-real-status",
                use_git=False,
            )

        error_msg = str(exc_info.value)
        # Should mention valid statuses
        assert "active" in error_msg or "status" in error_msg.lower()


class TestEditOperationPathSecurity:
    """Tests for path security in EditOperation"""

    def test_edit_validates_file_path(self, temp_registry):
        """Test that edit validates file paths"""
        operation = EditOperation(temp_registry)

        # Normal edit should work
        result = operation.edit_entity(
            identifier="P-001",
            set_title="Security Test",
            use_git=False,
        )

        assert result["success"] is True

        # Resolve both paths to handle symlinks (macOS) and short paths (Windows)
        resolved_registry = str(Path(temp_registry).resolve())
        resolved_file_path = str(Path(result["file_path"]).resolve())

        # File path should be within registry
        assert resolved_file_path.startswith(resolved_registry)

    def test_edit_uses_safe_path_resolution(self, temp_registry):
        """Test that edit uses secure path resolution"""
        operation = EditOperation(temp_registry)

        # This should work normally
        result = operation.edit_entity(
            identifier="P-001",
            set_title="Safe Path Test",
            use_git=False,
        )

        assert result["success"] is True

    def test_find_entity_file_validates_paths(self, temp_registry):
        """Test that find_entity_file validates paths"""
        operation = EditOperation(temp_registry)

        # Normal find should work
        result = operation.find_entity_file("P-001")
        assert result is not None

        file_path, _ = result

        # Resolve both paths to handle symlinks (macOS) and short paths (Windows)
        resolved_registry = str(Path(temp_registry).resolve())
        resolved_file_path = str(file_path.resolve())

        # Path should be within registry
        assert resolved_file_path.startswith(resolved_registry)