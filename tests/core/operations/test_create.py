"""
Tests for HoxCore Core Create Operation.

This module provides unit and integration tests for the CreateOperation class
that ensures behavioral consistency between CLI commands and MCP tools.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Set
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.create import (
    MAX_ID_LENGTH,
    CreateOperation,
    CreateOperationError,
    DuplicateIdError,
)
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

    yield registry_path

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def registry_with_projects(temp_registry):
    """Create a registry with existing project entities"""
    # Create project with id "P-001"
    project1 = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Existing Project One",
        "status": "active",
    }
    with open(temp_registry / "projects" / "proj-proj0001.yml", "w") as f:
        yaml.dump(project1, f)

    # Create project with id "P-002"
    project2 = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Existing Project Two",
        "status": "active",
    }
    with open(temp_registry / "projects" / "proj-proj0002.yml", "w") as f:
        yaml.dump(project2, f)

    # Create project with id "test_project"
    project3 = {
        "type": "project",
        "uid": "proj0003",
        "id": "test_project",
        "title": "Test Project",
        "status": "active",
    }
    with open(temp_registry / "projects" / "proj-proj0003.yml", "w") as f:
        yaml.dump(project3, f)

    return temp_registry


class TestGenerateUid:
    """Tests for UID generation"""

    def test_generate_uid_returns_string(self):
        """Test that generate_uid returns a string"""
        uid = CreateOperation.generate_uid()
        assert isinstance(uid, str)

    def test_generate_uid_returns_8_characters(self):
        """Test that generate_uid returns exactly 8 characters"""
        uid = CreateOperation.generate_uid()
        assert len(uid) == 8

    def test_generate_uid_returns_hex_characters(self):
        """Test that generate_uid returns valid hex characters"""
        uid = CreateOperation.generate_uid()
        # UUID first 8 chars are hex digits and possibly hyphens
        assert all(c in "0123456789abcdef-" for c in uid)

    def test_generate_uid_produces_unique_values(self):
        """Test that generate_uid produces unique values"""
        uids = [CreateOperation.generate_uid() for _ in range(100)]
        assert len(set(uids)) == 100

    def test_generate_uid_no_hyphens(self):
        """Test that generate_uid does not include hyphens (first 8 chars of UUID)"""
        uid = CreateOperation.generate_uid()
        # First 8 chars of UUID are before the first hyphen
        assert "-" not in uid


class TestTransliterateToAscii:
    """Tests for ASCII transliteration"""

    def test_transliterate_ascii_unchanged(self):
        """Test that ASCII text is unchanged"""
        result = CreateOperation._transliterate_to_ascii("hello world")
        assert result == "hello world"

    def test_transliterate_removes_accents(self):
        """Test that accents are removed"""
        result = CreateOperation._transliterate_to_ascii("café")
        assert result == "cafe"

    def test_transliterate_complex_characters(self):
        """Test transliteration of complex non-ASCII characters"""
        result = CreateOperation._transliterate_to_ascii("pròjěčt")
        assert result == "project"

    def test_transliterate_german_umlauts(self):
        """Test transliteration of German umlauts"""
        result = CreateOperation._transliterate_to_ascii("über")
        assert result == "uber"

    def test_transliterate_empty_string(self):
        """Test transliteration of empty string"""
        result = CreateOperation._transliterate_to_ascii("")
        assert result == ""

    def test_transliterate_drops_non_translatable(self):
        """Test that non-translatable characters are dropped"""
        result = CreateOperation._transliterate_to_ascii("hello世界")
        assert result == "hello"


class TestTitleToId:
    """Tests for title_to_id conversion"""

    def test_title_to_id_basic_spaces(self):
        """Test that spaces become underscores"""
        result = CreateOperation.title_to_id("my project", "project")
        assert result == "my_project"

    def test_title_to_id_multiple_words(self):
        """Test multiple words"""
        result = CreateOperation.title_to_id("my awesome project", "project")
        assert result == "my_awesome_project"

    def test_title_to_id_uppercase_to_lowercase(self):
        """Test that uppercase is converted to lowercase"""
        result = CreateOperation.title_to_id("My Project", "project")
        assert result == "my_project"

    def test_title_to_id_special_characters_removed(self):
        """Test that special characters become underscores"""
        result = CreateOperation.title_to_id("my-project!", "project")
        assert result == "my_project"

    def test_title_to_id_non_ascii(self):
        """Test that non-ASCII characters are transliterated"""
        result = CreateOperation.title_to_id("cäfé pròjěčt", "project")
        assert result == "cafe_project"

    def test_title_to_id_empty_title_uses_entity_type(self):
        """Test that empty title falls back to entity type"""
        result = CreateOperation.title_to_id("", "project")
        assert result == "project"

    def test_title_to_id_whitespace_only_uses_entity_type(self):
        """Test that whitespace-only title falls back to entity type"""
        result = CreateOperation.title_to_id("   ", "project")
        assert result == "project"

    def test_title_to_id_leading_trailing_whitespace_stripped(self):
        """Test that leading/trailing whitespace is stripped"""
        result = CreateOperation.title_to_id("  my project  ", "project")
        assert result == "my_project"

    def test_title_to_id_consecutive_spaces_collapse(self):
        """Test that consecutive spaces collapse to single underscore"""
        result = CreateOperation.title_to_id("my    project", "project")
        assert result == "my_project"

    def test_title_to_id_consecutive_underscores_collapse(self):
        """Test that consecutive underscores collapse"""
        result = CreateOperation.title_to_id("my___project", "project")
        assert result == "my_project"

    def test_title_to_id_max_length(self):
        """Test that output is capped to MAX_ID_LENGTH"""
        long_title = "a" * 300
        result = CreateOperation.title_to_id(long_title, "project")
        assert len(result) == MAX_ID_LENGTH
        assert result == "a" * 255

    def test_title_to_id_numbers_preserved(self):
        """Test that numbers are preserved"""
        result = CreateOperation.title_to_id("project 123", "project")
        assert result == "project_123"

    def test_title_to_id_all_special_chars(self):
        """Test title with only special characters"""
        result = CreateOperation.title_to_id("!@#$%^&*()", "mission")
        assert result == "mission"

    def test_title_to_id_leading_underscore_stripped(self):
        """Test that leading underscores are stripped"""
        result = CreateOperation.title_to_id("___project", "project")
        assert result == "project"

    def test_title_to_id_trailing_underscore_stripped(self):
        """Test that trailing underscores are stripped"""
        result = CreateOperation.title_to_id("project___", "project")
        assert result == "project"


class TestLoadExistingIds:
    """Tests for loading existing IDs from registry"""

    def test_load_existing_ids_empty_registry(self, temp_registry):
        """Test loading IDs from empty registry"""
        operation = CreateOperation(str(temp_registry))
        ids = operation.load_existing_ids(EntityType.PROJECT)
        assert ids == set()

    def test_load_existing_ids_with_entities(self, registry_with_projects):
        """Test loading IDs from registry with entities"""
        operation = CreateOperation(str(registry_with_projects))
        ids = operation.load_existing_ids(EntityType.PROJECT)
        assert "P-001" in ids
        assert "P-002" in ids
        assert "test_project" in ids
        assert len(ids) == 3

    def test_load_existing_ids_different_entity_types(self, temp_registry):
        """Test that loading IDs is scoped to entity type"""
        # Create a project
        project = {
            "type": "project",
            "uid": "proj0001",
            "id": "P-001",
            "title": "Project",
            "status": "active",
        }
        with open(temp_registry / "projects" / "proj-proj0001.yml", "w") as f:
            yaml.dump(project, f)

        # Create a program
        program = {
            "type": "program",
            "uid": "prog0001",
            "id": "PRG-001",
            "title": "Program",
            "status": "active",
        }
        with open(temp_registry / "programs" / "prog-prog0001.yml", "w") as f:
            yaml.dump(program, f)

        operation = CreateOperation(str(temp_registry))

        project_ids = operation.load_existing_ids(EntityType.PROJECT)
        assert "P-001" in project_ids
        assert "PRG-001" not in project_ids

        program_ids = operation.load_existing_ids(EntityType.PROGRAM)
        assert "PRG-001" in program_ids
        assert "P-001" not in program_ids

    def test_load_existing_ids_ignores_missing_id_field(self, temp_registry):
        """Test that entities without id field are ignored"""
        # Create entity without id field
        entity = {
            "type": "project",
            "uid": "proj0001",
            "title": "No ID Project",
            "status": "active",
        }
        with open(temp_registry / "projects" / "proj-proj0001.yml", "w") as f:
            yaml.dump(entity, f)

        operation = CreateOperation(str(temp_registry))
        ids = operation.load_existing_ids(EntityType.PROJECT)
        assert len(ids) == 0

    def test_load_existing_ids_ignores_invalid_yaml(self, temp_registry):
        """Test that invalid YAML files are ignored"""
        # Write invalid YAML
        with open(temp_registry / "projects" / "proj-invalid.yml", "w") as f:
            f.write("{ invalid yaml [")

        operation = CreateOperation(str(temp_registry))
        ids = operation.load_existing_ids(EntityType.PROJECT)
        assert len(ids) == 0


class TestValidateIdUniqueness:
    """Tests for ID uniqueness validation"""

    def test_validate_unique_id(self, temp_registry):
        """Test that unique ID validates successfully"""
        operation = CreateOperation(str(temp_registry))
        assert operation.validate_id_uniqueness(EntityType.PROJECT, "new-id") is True

    def test_validate_duplicate_id(self, registry_with_projects):
        """Test that duplicate ID fails validation"""
        operation = CreateOperation(str(registry_with_projects))
        assert operation.validate_id_uniqueness(EntityType.PROJECT, "P-001") is False

    def test_validate_same_id_different_type_allowed(self, registry_with_projects):
        """Test that same ID is allowed for different entity types"""
        operation = CreateOperation(str(registry_with_projects))
        # P-001 exists as a project, but should be allowed for programs
        assert operation.validate_id_uniqueness(EntityType.PROGRAM, "P-001") is True

    def test_validate_with_preloaded_ids(self, temp_registry):
        """Test validation with pre-loaded IDs"""
        operation = CreateOperation(str(temp_registry))
        existing_ids = {"existing-1", "existing-2"}

        assert (
            operation.validate_id_uniqueness(EntityType.PROJECT, "new-id", existing_ids)
            is True
        )
        assert (
            operation.validate_id_uniqueness(
                EntityType.PROJECT, "existing-1", existing_ids
            )
            is False
        )


class TestResolveAutoId:
    """Tests for automatic ID resolution with collision avoidance"""

    def test_resolve_auto_id_no_collision(self):
        """Test that base ID is used when no collision"""
        existing_ids: Set[str] = set()
        result = CreateOperation.resolve_auto_id(existing_ids, "my_project", "abc12345")
        assert result == "my_project"

    def test_resolve_auto_id_with_collision_adds_suffix(self):
        """Test that suffix is added on collision"""
        existing_ids = {"my_project"}
        result = CreateOperation.resolve_auto_id(existing_ids, "my_project", "abc12345")
        assert result == "my_project_abc"

    def test_resolve_auto_id_extends_suffix_on_continued_collision(self):
        """Test that suffix is extended on continued collision"""
        existing_ids = {"my_project", "my_project_abc"}
        result = CreateOperation.resolve_auto_id(existing_ids, "my_project", "abc12345")
        assert result == "my_project_abc1"

    def test_resolve_auto_id_empty_base_uses_untitled(self):
        """Test that empty base ID uses 'untitled'"""
        existing_ids: Set[str] = set()
        result = CreateOperation.resolve_auto_id(existing_ids, "", "abc12345")
        assert result == "untitled"

    def test_resolve_auto_id_truncates_for_max_length(self):
        """Test that base is truncated to fit suffix within MAX_ID_LENGTH"""
        long_base = "a" * 300
        existing_ids = {long_base[:255]}  # Exact max length collision
        result = CreateOperation.resolve_auto_id(
            existing_ids, long_base[:255], "abc12345"
        )

        # Should truncate base to make room for suffix
        assert len(result) <= MAX_ID_LENGTH
        assert result.endswith("_abc")

    def test_resolve_auto_id_returns_none_when_exhausted(self):
        """Test that None is returned when all options exhausted"""
        uid = "ab"  # Very short UID
        existing_ids = {"base", "base_a", "base_ab"}
        result = CreateOperation.resolve_auto_id(existing_ids, "base", uid)
        assert result is None


class TestBuildEntityData:
    """Tests for building entity data dictionary"""

    def test_build_minimal_entity(self, temp_registry):
        """Test building entity with minimal fields"""
        operation = CreateOperation(str(temp_registry))
        data = operation.build_entity_data(
            entity_type=EntityType.PROJECT,
            title="Test Project",
            uid="abc12345",
        )

        assert data["type"] == "project"
        assert data["uid"] == "abc12345"
        assert data["title"] == "Test Project"
        assert data["status"] == "active"
        assert "start_date" in data
        assert "id" in data
        assert data["children"] == []
        assert data["related"] == []
        assert data["repositories"] == []

    def test_build_entity_with_all_fields(self, temp_registry):
        """Test building entity with all optional fields"""
        operation = CreateOperation(str(temp_registry))
        data = operation.build_entity_data(
            entity_type=EntityType.PROJECT,
            title="Full Project",
            uid="abc12345",
            entity_id="P-CUSTOM",
            description="A full description",
            status=EntityStatus.ON_HOLD,
            start_date="2024-01-01",
            due_date="2024-12-31",
            category="software.dev/cli-tool",
            tags=["tag1", "tag2"],
            parent="parent-uid",
            template="template.default",
        )

        assert data["id"] == "P-CUSTOM"
        assert data["description"] == "A full description"
        assert data["status"] == "on-hold"
        assert data["start_date"] == "2024-01-01"
        assert data["due_date"] == "2024-12-31"
        assert data["category"] == "software.dev/cli-tool"
        assert data["tags"] == ["tag1", "tag2"]
        assert data["parent"] == "parent-uid"
        assert data["template"] == "template.default"

    def test_build_entity_auto_generates_id(self, temp_registry):
        """Test that ID is auto-generated from title when not provided"""
        operation = CreateOperation(str(temp_registry))
        data = operation.build_entity_data(
            entity_type=EntityType.PROJECT,
            title="My Amazing Project",
            uid="abc12345",
        )

        assert data["id"] == "my_amazing_project"

    def test_build_entity_custom_id_overrides_auto(self, temp_registry):
        """Test that custom ID overrides auto-generated"""
        operation = CreateOperation(str(temp_registry))
        data = operation.build_entity_data(
            entity_type=EntityType.PROJECT,
            title="My Amazing Project",
            uid="abc12345",
            entity_id="CUSTOM-ID",
        )

        assert data["id"] == "CUSTOM-ID"

    def test_build_entity_defaults_start_date_to_today(self, temp_registry):
        """Test that start_date defaults to today"""
        import datetime

        today = datetime.date.today().isoformat()

        operation = CreateOperation(str(temp_registry))
        data = operation.build_entity_data(
            entity_type=EntityType.PROJECT,
            title="Test",
            uid="abc12345",
        )

        assert data["start_date"] == today

    def test_build_entity_all_entity_types(self, temp_registry):
        """Test building data for all entity types"""
        operation = CreateOperation(str(temp_registry))

        for entity_type in EntityType:
            data = operation.build_entity_data(
                entity_type=entity_type,
                title=f"Test {entity_type.value}",
                uid="abc12345",
            )

            assert data["type"] == entity_type.value
            assert data["uid"] == "abc12345"


class TestWriteEntityFile:
    """Tests for writing entity files"""

    def test_write_entity_file_creates_file(self, temp_registry):
        """Test that entity file is created"""
        operation = CreateOperation(str(temp_registry))
        entity_data = {
            "type": "project",
            "uid": "abc12345",
            "id": "test-id",
            "title": "Test Project",
            "status": "active",
        }

        file_path = operation.write_entity_file(
            EntityType.PROJECT,
            "abc12345",
            entity_data,
        )

        assert file_path.exists()
        assert file_path.name == "proj-abc12345.yml"

    def test_write_entity_file_correct_location(self, temp_registry):
        """Test that entity file is in correct directory"""
        operation = CreateOperation(str(temp_registry))
        entity_data = {"type": "project", "uid": "abc12345"}

        file_path = operation.write_entity_file(
            EntityType.PROJECT,
            "abc12345",
            entity_data,
        )

        assert file_path.parent == temp_registry / "projects"

    def test_write_entity_file_content(self, temp_registry):
        """Test that file content is correct"""
        operation = CreateOperation(str(temp_registry))
        entity_data = {
            "type": "project",
            "uid": "abc12345",
            "title": "Test Project",
            "status": "active",
        }

        file_path = operation.write_entity_file(
            EntityType.PROJECT,
            "abc12345",
            entity_data,
        )

        with open(file_path) as f:
            loaded = yaml.safe_load(f)

        assert loaded == entity_data

    def test_write_entity_file_all_types(self, temp_registry):
        """Test writing files for all entity types"""
        operation = CreateOperation(str(temp_registry))

        type_prefix_map = {
            EntityType.PROGRAM: "prog",
            EntityType.PROJECT: "proj",
            EntityType.MISSION: "miss",
            EntityType.ACTION: "act",
        }

        for entity_type, prefix in type_prefix_map.items():
            entity_data = {"type": entity_type.value, "uid": "abc12345"}
            file_path = operation.write_entity_file(
                entity_type,
                "abc12345",
                entity_data,
            )

            assert file_path.name == f"{prefix}-abc12345.yml"
            assert file_path.parent == temp_registry / entity_type.get_folder_name()

            # Clean up for next iteration
            file_path.unlink()


class TestCreateEntity:
    """Tests for the main create_entity method"""

    def test_create_entity_basic(self, temp_registry):
        """Test basic entity creation"""
        operation = CreateOperation(str(temp_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="New Project",
            use_git=False,
        )

        assert result["success"] is True
        assert "uid" in result
        assert "id" in result
        assert "file_path" in result
        assert "entity" in result

        # Verify file exists
        assert Path(result["file_path"]).exists()

    def test_create_entity_with_custom_id(self, temp_registry):
        """Test creation with custom ID"""
        operation = CreateOperation(str(temp_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Custom ID Project",
            entity_id="CUSTOM-001",
            use_git=False,
        )

        assert result["success"] is True
        assert result["id"] == "CUSTOM-001"
        assert result["entity"]["id"] == "CUSTOM-001"

    def test_create_entity_duplicate_id_raises_error(self, registry_with_projects):
        """Test that duplicate ID raises DuplicateIdError"""
        operation = CreateOperation(str(registry_with_projects))

        with pytest.raises(DuplicateIdError) as exc_info:
            operation.create_entity(
                entity_type=EntityType.PROJECT,
                title="Duplicate",
                entity_id="P-001",  # Already exists
                use_git=False,
            )

        assert "P-001" in str(exc_info.value)
        assert "already exists" in str(exc_info.value).lower()

    def test_create_entity_auto_resolves_id_collision(self, registry_with_projects):
        """Test that auto ID resolution handles collisions"""
        operation = CreateOperation(str(registry_with_projects))

        # Create entity with title that would generate "test_project" which exists
        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Test Project",  # Would generate "test_project" which exists
            use_git=False,
        )

        assert result["success"] is True
        # ID should have suffix to avoid collision
        assert result["id"] != "test_project"
        assert result["id"].startswith("test_project_")

    def test_create_entity_all_types(self, temp_registry):
        """Test creation of all entity types"""
        operation = CreateOperation(str(temp_registry))

        for entity_type in EntityType:
            result = operation.create_entity(
                entity_type=entity_type,
                title=f"Test {entity_type.value}",
                use_git=False,
            )

            assert result["success"] is True
            assert result["entity"]["type"] == entity_type.value

            # Verify correct directory
            folder_name = entity_type.get_folder_name()
            assert folder_name in result["file_path"]

    def test_create_entity_with_all_options(self, temp_registry):
        """Test creation with all optional fields"""
        operation = CreateOperation(str(temp_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Full Project",
            entity_id="P-FULL",
            description="A complete project",
            status=EntityStatus.PLANNED,
            start_date="2024-06-01",
            due_date="2024-12-31",
            category="software.dev/api",
            tags=["python", "api"],
            parent="parent-uid",
            template="python.default",
            use_git=False,
        )

        assert result["success"] is True
        entity = result["entity"]

        assert entity["id"] == "P-FULL"
        assert entity["description"] == "A complete project"
        assert entity["status"] == "planned"
        assert entity["start_date"] == "2024-06-01"
        assert entity["due_date"] == "2024-12-31"
        assert entity["category"] == "software.dev/api"
        assert entity["tags"] == ["python", "api"]
        assert entity["parent"] == "parent-uid"
        assert entity["template"] == "python.default"

    def test_create_entity_without_git(self, temp_registry):
        """Test that use_git=False skips git operations"""
        operation = CreateOperation(str(temp_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="No Git Project",
            use_git=False,
        )

        assert result["success"] is True
        assert result["git_committed"] is False

    def test_create_entity_uid_is_8_chars(self, temp_registry):
        """Test that generated UID is 8 characters"""
        operation = CreateOperation(str(temp_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="UID Test",
            use_git=False,
        )

        assert len(result["uid"]) == 8

    def test_create_entity_file_content_matches_return(self, temp_registry):
        """Test that file content matches returned entity"""
        operation = CreateOperation(str(temp_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Content Test",
            description="Test description",
            use_git=False,
        )

        with open(result["file_path"]) as f:
            on_disk = yaml.safe_load(f)

        assert on_disk == result["entity"]

    def test_create_entity_same_id_different_types_allowed(self, temp_registry):
        """Test that same ID can be used for different entity types"""
        operation = CreateOperation(str(temp_registry))

        # Create project with ID "SHARED-001"
        result1 = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Project",
            entity_id="SHARED-001",
            use_git=False,
        )
        assert result1["success"] is True

        # Create program with same ID should succeed
        result2 = operation.create_entity(
            entity_type=EntityType.PROGRAM,
            title="Program",
            entity_id="SHARED-001",
            use_git=False,
        )
        assert result2["success"] is True


class TestCreateEntityGitIntegration:
    """Tests for git integration in entity creation"""

    def test_create_entity_with_git(self, git_registry):
        """Test that use_git=True creates a commit"""
        operation = CreateOperation(str(git_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Git Project",
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
        assert "proj-" in log.stdout

    def test_create_entity_commit_message_format(self, git_registry):
        """Test that commit message follows expected format"""
        operation = CreateOperation(str(git_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Commit Format Test",
            entity_id="P-FORMAT",
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

        # Verify message components
        assert "Commit Format Test" in message
        assert "Entity type: project" in message
        assert "Entity ID: P-FORMAT" in message
        assert f"Entity UID: {result['uid']}" in message

    def test_create_entity_git_in_non_git_registry(self, temp_registry, capsys):
        """Test that git operations gracefully handle non-git registry"""
        operation = CreateOperation(str(temp_registry))

        result = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Non Git Project",
            use_git=True,  # Should gracefully fail
        )

        assert result["success"] is True
        assert result["git_committed"] is False

        out = capsys.readouterr().out
        assert "not inside a git repository" in out

    def test_create_entity_sequential_commits(self, git_registry):
        """Test that multiple creations produce separate commits"""
        operation = CreateOperation(str(git_registry))

        # Create first entity
        result1 = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="First Project",
            use_git=True,
        )

        # Create second entity
        result2 = operation.create_entity(
            entity_type=EntityType.PROJECT,
            title="Second Project",
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

        assert result1["uid"][:8] in log.stdout or "First Project" in log.stdout
        assert result2["uid"][:8] in log.stdout or "Second Project" in log.stdout

        # Count commits (initial + 2 new)
        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 3


class TestCreateEntityErrorHandling:
    """Tests for error handling in entity creation"""

    def test_create_entity_path_security_error(self, temp_registry):
        """Test that path security errors are propagated"""
        operation = CreateOperation(str(temp_registry))

        with patch(
            "hxc.core.operations.create.get_safe_entity_path",
            side_effect=PathSecurityError("Path traversal detected"),
        ):
            with pytest.raises(PathSecurityError):
                operation.create_entity(
                    entity_type=EntityType.PROJECT,
                    title="Security Test",
                    use_git=False,
                )

    def test_create_entity_invalid_entity_type_in_write(self, temp_registry):
        """Test that invalid entity type raises ValueError in write"""
        operation = CreateOperation(str(temp_registry))
        entity_data = {"type": "project", "uid": "test123"}

        with patch(
            "hxc.core.operations.create.get_safe_entity_path",
            side_effect=ValueError("Invalid entity type"),
        ):
            with pytest.raises(ValueError):
                operation.write_entity_file(
                    EntityType.PROJECT,
                    "test123",
                    entity_data,
                )

    def test_create_entity_cannot_resolve_auto_id(self, temp_registry):
        """Test error when auto ID cannot be resolved"""
        operation = CreateOperation(str(temp_registry))

        # Create many entities with same base ID
        base_id = "collision_test"
        uid = "ab"  # Very short UID for quick exhaustion

        # Pre-populate with colliding IDs
        existing = {base_id, f"{base_id}_a", f"{base_id}_ab"}

        with patch.object(operation, "load_existing_ids", return_value=existing):
            with patch.object(CreateOperation, "generate_uid", return_value=uid):
                with pytest.raises(CreateOperationError) as exc_info:
                    operation.create_entity(
                        entity_type=EntityType.PROJECT,
                        title="Collision Test",
                        use_git=False,
                    )

                assert "unique" in str(exc_info.value).lower()


class TestTruncateBaseForSuffix:
    """Tests for _truncate_base_for_suffix helper"""

    def test_truncate_no_truncation_needed(self):
        """Test that short base is not truncated"""
        result = CreateOperation._truncate_base_for_suffix("short", 10)
        assert result == "short"

    def test_truncate_long_base(self):
        """Test that long base is truncated"""
        long_base = "a" * 260
        result = CreateOperation._truncate_base_for_suffix(long_base, 10)
        expected_len = MAX_ID_LENGTH - 10
        assert len(result) == expected_len

    def test_truncate_exact_boundary(self):
        """Test truncation at exact boundary"""
        base = "a" * 250
        result = CreateOperation._truncate_base_for_suffix(base, 5)
        assert len(result) == 250  # MAX_ID_LENGTH - 5


class TestCreateOperationInit:
    """Tests for CreateOperation initialization"""

    def test_init_stores_registry_path(self, temp_registry):
        """Test that registry path is stored"""
        operation = CreateOperation(str(temp_registry))
        assert operation.registry_path == str(temp_registry)

    def test_init_with_path_object(self, temp_registry):
        """Test initialization with Path object"""
        operation = CreateOperation(str(temp_registry))
        assert isinstance(operation.registry_path, str)


class TestExceptionClasses:
    """Tests for custom exception classes"""

    def test_create_operation_error_is_exception(self):
        """Test that CreateOperationError is an Exception"""
        error = CreateOperationError("test error")
        assert isinstance(error, Exception)

    def test_duplicate_id_error_is_create_operation_error(self):
        """Test that DuplicateIdError inherits from CreateOperationError"""
        error = DuplicateIdError("duplicate id")
        assert isinstance(error, CreateOperationError)
        assert isinstance(error, Exception)

    def test_duplicate_id_error_message(self):
        """Test DuplicateIdError preserves message"""
        message = "ID 'P-001' already exists"
        error = DuplicateIdError(message)
        assert str(error) == message
