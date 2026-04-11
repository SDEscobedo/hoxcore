"""
Tests for the ListOperation class.

This module tests the shared list operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools.
"""
import os
import shutil
import tempfile
import datetime
from pathlib import Path
from typing import Dict, Any, List

import pytest
import yaml

from hxc.core.operations.list import ListOperation, ListOperationError
from hxc.core.enums import EntityType, EntityStatus, SortField


@pytest.fixture
def temp_registry():
    """Create a temporary test registry with sample entities."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)
    
    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()
    
    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)
    
    # Create test projects
    project1 = {
        "type": "project",
        "uid": "proj0001",
        "id": "P-001",
        "title": "Alpha Project",
        "description": "First test project for API development",
        "status": "active",
        "category": "software.dev/cli-tool",
        "tags": ["test", "alpha", "cli"],
        "start_date": "2024-01-01",
        "due_date": "2024-06-30",
        "parent": "prog0001",
        "children": [],
        "related": [],
    }
    (registry_path / "projects" / "proj-proj0001.yml").write_text(yaml.dump(project1))
    
    project2 = {
        "type": "project",
        "uid": "proj0002",
        "id": "P-002",
        "title": "Beta Project",
        "description": "Second test project for web development",
        "status": "completed",
        "category": "software.dev/web-app",
        "tags": ["test", "beta", "web"],
        "start_date": "2024-01-15",
        "due_date": "2024-12-31",
        "children": [],
        "related": [],
    }
    (registry_path / "projects" / "proj-proj0002.yml").write_text(yaml.dump(project2))
    
    project3 = {
        "type": "project",
        "uid": "proj0003",
        "id": "P-003",
        "title": "Gamma Project",
        "description": "Third test project",
        "status": "on-hold",
        "category": "research",
        "tags": ["test", "gamma"],
        "start_date": "2024-03-01",
        "due_date": "2024-09-15",
        "children": [],
        "related": [],
    }
    (registry_path / "projects" / "proj-proj0003.yml").write_text(yaml.dump(project3))
    
    # Create test program
    program1 = {
        "type": "program",
        "uid": "prog0001",
        "id": "PRG-001",
        "title": "Test Program",
        "description": "A test program containing projects",
        "status": "active",
        "category": "software.dev",
        "tags": ["test", "program"],
        "children": ["proj0001", "proj0002"],
        "related": [],
    }
    (registry_path / "programs" / "prog-prog0001.yml").write_text(yaml.dump(program1))
    
    # Create test mission
    mission1 = {
        "type": "mission",
        "uid": "miss0001",
        "id": "M-001",
        "title": "Test Mission",
        "description": "A test mission",
        "status": "planned",
        "category": "research",
        "tags": ["test", "mission"],
        "due_date": "2024-08-01",
        "children": [],
        "related": [],
    }
    (registry_path / "missions" / "miss-miss0001.yml").write_text(yaml.dump(mission1))
    
    # Create test actions
    action1 = {
        "type": "action",
        "uid": "act0001",
        "id": "A-001",
        "title": "Test Action One",
        "description": "First test action",
        "status": "active",
        "category": "maintenance",
        "tags": ["test", "action"],
        "children": [],
        "related": [],
    }
    (registry_path / "actions" / "act-act0001.yml").write_text(yaml.dump(action1))
    
    action2 = {
        "type": "action",
        "uid": "act0002",
        "id": "A-002",
        "title": "Test Action Two",
        "description": "Second test action",
        "status": "completed",
        "category": "maintenance",
        "tags": ["test", "action", "completed"],
        "children": [],
        "related": [],
    }
    (registry_path / "actions" / "act-act0002.yml").write_text(yaml.dump(action2))
    
    yield str(registry_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def empty_registry():
    """Create an empty temporary registry."""
    temp_dir = tempfile.mkdtemp()
    registry_path = Path(temp_dir)
    
    # Create registry structure
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()
    
    # Create config file
    config_content = """
registry:
  version: "1.0"
  name: "Empty Registry"
"""
    (registry_path / "config.yml").write_text(config_content)
    
    yield str(registry_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestListOperationInit:
    """Tests for ListOperation initialization."""
    
    def test_init_with_valid_path(self, temp_registry):
        """Test initialization with a valid registry path."""
        operation = ListOperation(temp_registry)
        assert operation.registry_path == temp_registry
    
    def test_init_with_nonexistent_path(self):
        """Test initialization with a nonexistent path."""
        operation = ListOperation("/nonexistent/path")
        assert operation.registry_path == "/nonexistent/path"


class TestLoadEntities:
    """Tests for the load_entities method."""
    
    def test_load_projects(self, temp_registry):
        """Test loading project entities."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        assert len(entities) == 3
        types = [e["type"] for e in entities]
        assert all(t == "project" for t in types)
    
    def test_load_programs(self, temp_registry):
        """Test loading program entities."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROGRAM)
        
        assert len(entities) == 1
        assert entities[0]["type"] == "program"
        assert entities[0]["id"] == "PRG-001"
    
    def test_load_missions(self, temp_registry):
        """Test loading mission entities."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.MISSION)
        
        assert len(entities) == 1
        assert entities[0]["type"] == "mission"
        assert entities[0]["id"] == "M-001"
    
    def test_load_actions(self, temp_registry):
        """Test loading action entities."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.ACTION)
        
        assert len(entities) == 2
        types = [e["type"] for e in entities]
        assert all(t == "action" for t in types)
    
    def test_load_with_file_metadata(self, temp_registry):
        """Test loading entities with file metadata included."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT, include_file_metadata=True)
        
        assert len(entities) > 0
        for entity in entities:
            assert "_file" in entity
            assert "path" in entity["_file"]
            assert "name" in entity["_file"]
            assert "created" in entity["_file"]
            assert "modified" in entity["_file"]
    
    def test_load_without_file_metadata(self, temp_registry):
        """Test loading entities without file metadata."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT, include_file_metadata=False)
        
        assert len(entities) > 0
        for entity in entities:
            assert "_file" not in entity
    
    def test_load_from_empty_registry(self, empty_registry):
        """Test loading from an empty registry."""
        operation = ListOperation(empty_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        assert len(entities) == 0
    
    def test_load_from_nonexistent_type_folder(self, temp_registry):
        """Test loading when the type folder doesn't exist."""
        # Remove the actions folder
        actions_path = Path(temp_registry) / "actions"
        shutil.rmtree(actions_path)
        
        operation = ListOperation(temp_registry)
        # Should not raise, just return empty list
        entities = operation.load_entities(EntityType.ACTION)
        
        assert len(entities) == 0
    
    def test_load_file_metadata_date_format(self, temp_registry):
        """Test that file metadata dates are in YYYY-MM-DD format."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT, include_file_metadata=True)
        
        assert len(entities) > 0
        entity = entities[0]
        
        # Check date format (YYYY-MM-DD)
        created = entity["_file"]["created"]
        modified = entity["_file"]["modified"]
        
        # Should be parseable as dates
        datetime.datetime.strptime(created, "%Y-%m-%d")
        datetime.datetime.strptime(modified, "%Y-%m-%d")


class TestFilterEntities:
    """Tests for the filter_entities method."""
    
    def test_filter_by_status(self, temp_registry):
        """Test filtering by status."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, status=EntityStatus.ACTIVE)
        
        assert len(filtered) == 1
        assert filtered[0]["status"] == "active"
        assert filtered[0]["id"] == "P-001"
    
    def test_filter_by_completed_status(self, temp_registry):
        """Test filtering by completed status."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, status=EntityStatus.COMPLETED)
        
        assert len(filtered) == 1
        assert filtered[0]["status"] == "completed"
        assert filtered[0]["id"] == "P-002"
    
    def test_filter_by_single_tag(self, temp_registry):
        """Test filtering by a single tag."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, tags=["alpha"])
        
        assert len(filtered) == 1
        assert "alpha" in filtered[0]["tags"]
    
    def test_filter_by_multiple_tags_and_logic(self, temp_registry):
        """Test filtering by multiple tags with AND logic."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        # Both "test" and "alpha" must be present
        filtered = operation.filter_entities(entities, tags=["test", "alpha"])
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "P-001"
    
    def test_filter_by_tags_no_match(self, temp_registry):
        """Test filtering by tags with no matches."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, tags=["nonexistent"])
        
        assert len(filtered) == 0
    
    def test_filter_by_category(self, temp_registry):
        """Test filtering by category."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, category="software.dev/cli-tool")
        
        assert len(filtered) == 1
        assert filtered[0]["category"] == "software.dev/cli-tool"
    
    def test_filter_by_parent(self, temp_registry):
        """Test filtering by parent ID."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, parent="prog0001")
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "P-001"
    
    def test_filter_by_identifier_id(self, temp_registry):
        """Test filtering by entity ID."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, identifier="P-001")
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "P-001"
    
    def test_filter_by_identifier_uid(self, temp_registry):
        """Test filtering by entity UID."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, identifier="proj0002")
        
        assert len(filtered) == 1
        assert filtered[0]["uid"] == "proj0002"
    
    def test_filter_by_query_title(self, temp_registry):
        """Test filtering by query in title."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, query="Alpha")
        
        assert len(filtered) == 1
        assert "Alpha" in filtered[0]["title"]
    
    def test_filter_by_query_description(self, temp_registry):
        """Test filtering by query in description."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, query="API development")
        
        assert len(filtered) == 1
        assert "API" in filtered[0]["description"]
    
    def test_filter_by_query_case_insensitive(self, temp_registry):
        """Test that query filtering is case-insensitive."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered1 = operation.filter_entities(entities, query="alpha")
        filtered2 = operation.filter_entities(entities, query="ALPHA")
        filtered3 = operation.filter_entities(entities, query="Alpha")
        
        assert len(filtered1) == len(filtered2) == len(filtered3) == 1
    
    def test_filter_by_due_before(self, temp_registry):
        """Test filtering by due date before."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, due_before="2024-07-01")
        
        # P-001 has due_date 2024-06-30, which is before 2024-07-01
        assert len(filtered) == 1
        assert filtered[0]["id"] == "P-001"
    
    def test_filter_by_due_after(self, temp_registry):
        """Test filtering by due date after."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities, due_after="2024-10-01")
        
        # P-002 has due_date 2024-12-31, which is after 2024-10-01
        assert len(filtered) == 1
        assert filtered[0]["id"] == "P-002"
    
    def test_filter_by_due_date_range(self, temp_registry):
        """Test filtering by due date range."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(
            entities, 
            due_after="2024-07-01",
            due_before="2024-10-01"
        )
        
        # P-003 has due_date 2024-09-15, which is in the range
        assert len(filtered) == 1
        assert filtered[0]["id"] == "P-003"
    
    def test_filter_by_due_after_excludes_no_due_date(self, temp_registry):
        """Test that entities without due_date are excluded by due_after filter."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROGRAM)
        
        # Program has no due_date
        filtered = operation.filter_entities(entities, due_after="2024-01-01")
        
        assert len(filtered) == 0
    
    def test_filter_combined_status_and_tags(self, temp_registry):
        """Test combining status and tags filters."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(
            entities,
            status=EntityStatus.ACTIVE,
            tags=["test"]
        )
        
        assert len(filtered) == 1
        assert filtered[0]["status"] == "active"
        assert "test" in filtered[0]["tags"]
    
    def test_filter_combined_multiple_criteria(self, temp_registry):
        """Test combining multiple filter criteria."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(
            entities,
            status=EntityStatus.ACTIVE,
            tags=["cli"],
            category="software.dev/cli-tool",
            query="Alpha"
        )
        
        assert len(filtered) == 1
        assert filtered[0]["id"] == "P-001"
    
    def test_filter_no_criteria_returns_all(self, temp_registry):
        """Test that no filter criteria returns all entities."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        filtered = operation.filter_entities(entities)
        
        assert len(filtered) == len(entities)
    
    def test_filter_empty_list(self, temp_registry):
        """Test filtering an empty list."""
        operation = ListOperation(temp_registry)
        
        filtered = operation.filter_entities([], status=EntityStatus.ACTIVE)
        
        assert len(filtered) == 0


class TestSortEntities:
    """Tests for the sort_entities method."""
    
    def test_sort_by_title_ascending(self, temp_registry):
        """Test sorting by title in ascending order."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        sorted_entities = operation.sort_entities(entities, SortField.TITLE)
        
        titles = [e["title"] for e in sorted_entities]
        assert titles == sorted(titles)
    
    def test_sort_by_title_descending(self, temp_registry):
        """Test sorting by title in descending order."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        sorted_entities = operation.sort_entities(entities, SortField.TITLE, descending=True)
        
        titles = [e["title"] for e in sorted_entities]
        assert titles == sorted(titles, reverse=True)
    
    def test_sort_by_id(self, temp_registry):
        """Test sorting by ID."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        sorted_entities = operation.sort_entities(entities, SortField.ID)
        
        ids = [e["id"] for e in sorted_entities]
        assert ids == sorted(ids)
    
    def test_sort_by_status(self, temp_registry):
        """Test sorting by status."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        sorted_entities = operation.sort_entities(entities, SortField.STATUS)
        
        statuses = [e["status"] for e in sorted_entities]
        assert statuses == sorted(statuses)
    
    def test_sort_by_due_date(self, temp_registry):
        """Test sorting by due date."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        sorted_entities = operation.sort_entities(entities, SortField.DUE_DATE)
        
        # All projects in fixture have due_date
        due_dates = [e.get("due_date", "") for e in sorted_entities]
        assert due_dates == sorted(due_dates)
    
    def test_sort_by_created_with_file_metadata(self, temp_registry):
        """Test sorting by created date when file metadata is included."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT, include_file_metadata=True)
        
        sorted_entities = operation.sort_entities(entities, SortField.CREATED)
        
        # Created dates should be sorted
        created_dates = [e.get("_file", {}).get("created", "") for e in sorted_entities]
        assert created_dates == sorted(created_dates)
    
    def test_sort_by_modified_with_file_metadata(self, temp_registry):
        """Test sorting by modified date when file metadata is included."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT, include_file_metadata=True)
        
        sorted_entities = operation.sort_entities(entities, SortField.MODIFIED)
        
        # Modified dates should be sorted
        modified_dates = [e.get("_file", {}).get("modified", "") for e in sorted_entities]
        assert modified_dates == sorted(modified_dates)
    
    def test_sort_by_created_without_file_metadata(self, temp_registry):
        """Test sorting by created date when file metadata is not included."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT, include_file_metadata=False)
        
        # Should not raise, will sort by empty string
        sorted_entities = operation.sort_entities(entities, SortField.CREATED)
        
        assert len(sorted_entities) == len(entities)
    
    def test_sort_empty_list(self, temp_registry):
        """Test sorting an empty list."""
        operation = ListOperation(temp_registry)
        
        sorted_entities = operation.sort_entities([], SortField.TITLE)
        
        assert len(sorted_entities) == 0
    
    def test_sort_single_entity(self, temp_registry):
        """Test sorting a list with a single entity."""
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.MISSION)
        
        assert len(entities) == 1
        
        sorted_entities = operation.sort_entities(entities, SortField.TITLE)
        
        assert len(sorted_entities) == 1
        assert sorted_entities[0]["title"] == entities[0]["title"]


class TestListEntities:
    """Tests for the main list_entities method."""
    
    def test_list_all_entity_types(self, temp_registry):
        """Test listing all entity types."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities()
        
        assert result["success"] is True
        # 3 projects + 1 program + 1 mission + 2 actions = 7
        assert result["count"] == 7
        assert len(result["entities"]) == 7
    
    def test_list_specific_entity_type(self, temp_registry):
        """Test listing a specific entity type."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(entity_types=[EntityType.PROJECT])
        
        assert result["success"] is True
        assert result["count"] == 3
        
        for entity in result["entities"]:
            assert entity["type"] == "project"
    
    def test_list_multiple_entity_types(self, temp_registry):
        """Test listing multiple specific entity types."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT, EntityType.MISSION]
        )
        
        assert result["success"] is True
        # 3 projects + 1 mission = 4
        assert result["count"] == 4
        
        types = {e["type"] for e in result["entities"]}
        assert types == {"project", "mission"}
    
    def test_list_with_status_filter(self, temp_registry):
        """Test listing with status filter."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.ACTIVE
        )
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["status"] == "active"
    
    def test_list_with_tags_filter(self, temp_registry):
        """Test listing with tags filter."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(tags=["cli"])
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert "cli" in entity["tags"]
    
    def test_list_with_category_filter(self, temp_registry):
        """Test listing with category filter."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(category="research")
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert entity["category"] == "research"
    
    def test_list_with_parent_filter(self, temp_registry):
        """Test listing with parent filter."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(parent="prog0001")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["parent"] == "prog0001"
    
    def test_list_with_identifier_filter(self, temp_registry):
        """Test listing with identifier filter."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(identifier="P-002")
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["id"] == "P-002"
    
    def test_list_with_query_filter(self, temp_registry):
        """Test listing with query filter."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(query="web")
        
        assert result["success"] is True
        
        # Should find entities with "web" in title or description
        for entity in result["entities"]:
            has_web = (
                "web" in entity.get("title", "").lower() or
                "web" in entity.get("description", "").lower()
            )
            assert has_web
    
    def test_list_with_due_date_filters(self, temp_registry):
        """Test listing with due date filters."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            due_after="2024-08-01",
            due_before="2025-01-01"
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert entity["due_date"] >= "2024-08-01"
            assert entity["due_date"] <= "2025-01-01"
    
    def test_list_with_sort_by_title(self, temp_registry):
        """Test listing with sort by title."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            sort_field=SortField.TITLE
        )
        
        assert result["success"] is True
        
        titles = [e["title"] for e in result["entities"]]
        assert titles == sorted(titles)
    
    def test_list_with_descending_sort(self, temp_registry):
        """Test listing with descending sort."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            sort_field=SortField.TITLE,
            descending=True
        )
        
        assert result["success"] is True
        
        titles = [e["title"] for e in result["entities"]]
        assert titles == sorted(titles, reverse=True)
    
    def test_list_with_max_items(self, temp_registry):
        """Test listing with max items limit."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(max_items=2)
        
        assert result["success"] is True
        assert result["count"] == 2
        assert len(result["entities"]) == 2
    
    def test_list_with_max_items_zero_returns_all(self, temp_registry):
        """Test that max_items=0 returns all items."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(max_items=0)
        
        assert result["success"] is True
        assert result["count"] == 7  # All entities
    
    def test_list_with_file_metadata(self, temp_registry):
        """Test listing with file metadata included."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            include_file_metadata=True
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert "_file" in entity
    
    def test_list_without_file_metadata(self, temp_registry):
        """Test listing without file metadata."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            include_file_metadata=False
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert "_file" not in entity
    
    def test_list_returns_filters_metadata(self, temp_registry):
        """Test that result includes filters metadata."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.ACTIVE,
            tags=["test"],
            category="software.dev/cli-tool"
        )
        
        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["types"] == ["project"]
        assert result["filters"]["status"] == "active"
        assert result["filters"]["tags"] == ["test"]
        assert result["filters"]["category"] == "software.dev/cli-tool"
    
    def test_list_returns_sort_metadata(self, temp_registry):
        """Test that result includes sort metadata."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            sort_field=SortField.DUE_DATE,
            descending=True
        )
        
        assert result["success"] is True
        assert "sort" in result
        assert result["sort"]["field"] == "due_date"
        assert result["sort"]["descending"] is True
    
    def test_list_combined_filters_and_sort(self, temp_registry):
        """Test listing with combined filters and sort."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.ACTIVE,
            tags=["test"],
            sort_field=SortField.TITLE,
            descending=False,
            max_items=10
        )
        
        assert result["success"] is True
        
        # Should filter first, then sort
        for entity in result["entities"]:
            assert entity["status"] == "active"
            assert "test" in entity["tags"]
        
        # Should be sorted by title
        titles = [e["title"] for e in result["entities"]]
        assert titles == sorted(titles)
    
    def test_list_empty_registry(self, empty_registry):
        """Test listing from an empty registry."""
        operation = ListOperation(empty_registry)
        
        result = operation.list_entities()
        
        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["entities"]) == 0


class TestGetEntityByIdentifier:
    """Tests for the get_entity_by_identifier method."""
    
    def test_get_by_id(self, temp_registry):
        """Test getting entity by ID."""
        operation = ListOperation(temp_registry)
        
        entity = operation.get_entity_by_identifier("P-001")
        
        assert entity is not None
        assert entity["id"] == "P-001"
        assert entity["title"] == "Alpha Project"
    
    def test_get_by_uid(self, temp_registry):
        """Test getting entity by UID."""
        operation = ListOperation(temp_registry)
        
        entity = operation.get_entity_by_identifier("proj0002")
        
        assert entity is not None
        assert entity["uid"] == "proj0002"
        assert entity["id"] == "P-002"
    
    def test_get_with_entity_type_filter(self, temp_registry):
        """Test getting entity with type filter."""
        operation = ListOperation(temp_registry)
        
        entity = operation.get_entity_by_identifier(
            "P-001",
            entity_type=EntityType.PROJECT
        )
        
        assert entity is not None
        assert entity["type"] == "project"
    
    def test_get_with_wrong_entity_type_filter(self, temp_registry):
        """Test getting entity with wrong type filter returns None."""
        operation = ListOperation(temp_registry)
        
        entity = operation.get_entity_by_identifier(
            "P-001",
            entity_type=EntityType.PROGRAM  # P-001 is a project, not a program
        )
        
        assert entity is None
    
    def test_get_nonexistent_entity(self, temp_registry):
        """Test getting nonexistent entity returns None."""
        operation = ListOperation(temp_registry)
        
        entity = operation.get_entity_by_identifier("NONEXISTENT")
        
        assert entity is None
    
    def test_get_with_file_metadata(self, temp_registry):
        """Test getting entity with file metadata."""
        operation = ListOperation(temp_registry)
        
        entity = operation.get_entity_by_identifier(
            "P-001",
            include_file_metadata=True
        )
        
        assert entity is not None
        assert "_file" in entity
    
    def test_get_without_file_metadata(self, temp_registry):
        """Test getting entity without file metadata."""
        operation = ListOperation(temp_registry)
        
        entity = operation.get_entity_by_identifier(
            "P-001",
            include_file_metadata=False
        )
        
        assert entity is not None
        assert "_file" not in entity
    
    def test_get_from_different_entity_types(self, temp_registry):
        """Test getting entities from different types."""
        operation = ListOperation(temp_registry)
        
        # Get project
        project = operation.get_entity_by_identifier("P-001")
        assert project is not None
        assert project["type"] == "project"
        
        # Get program
        program = operation.get_entity_by_identifier("PRG-001")
        assert program is not None
        assert program["type"] == "program"
        
        # Get mission
        mission = operation.get_entity_by_identifier("M-001")
        assert mission is not None
        assert mission["type"] == "mission"
        
        # Get action
        action = operation.get_entity_by_identifier("A-001")
        assert action is not None
        assert action["type"] == "action"


class TestCleanEntitiesForOutput:
    """Tests for the clean_entities_for_output static method."""
    
    def test_clean_removes_file_metadata(self):
        """Test that cleaning removes _file metadata."""
        entities = [
            {
                "id": "P-001",
                "title": "Test",
                "_file": {"path": "/test/path", "name": "test.yml"}
            }
        ]
        
        cleaned = ListOperation.clean_entities_for_output(entities, remove_file_metadata=True)
        
        assert len(cleaned) == 1
        assert "_file" not in cleaned[0]
        assert cleaned[0]["id"] == "P-001"
        assert cleaned[0]["title"] == "Test"
    
    def test_clean_keeps_file_metadata_when_disabled(self):
        """Test that cleaning keeps _file metadata when disabled."""
        entities = [
            {
                "id": "P-001",
                "title": "Test",
                "_file": {"path": "/test/path", "name": "test.yml"}
            }
        ]
        
        cleaned = ListOperation.clean_entities_for_output(entities, remove_file_metadata=False)
        
        assert len(cleaned) == 1
        assert "_file" in cleaned[0]
    
    def test_clean_removes_all_underscore_prefixed_fields(self):
        """Test that cleaning removes all underscore-prefixed fields."""
        entities = [
            {
                "id": "P-001",
                "title": "Test",
                "_file": {"path": "/test"},
                "_internal": "hidden",
                "_other": {"data": "value"}
            }
        ]
        
        cleaned = ListOperation.clean_entities_for_output(entities, remove_file_metadata=True)
        
        assert len(cleaned) == 1
        assert "_file" not in cleaned[0]
        assert "_internal" not in cleaned[0]
        assert "_other" not in cleaned[0]
    
    def test_clean_empty_list(self):
        """Test cleaning an empty list."""
        cleaned = ListOperation.clean_entities_for_output([], remove_file_metadata=True)
        
        assert len(cleaned) == 0
    
    def test_clean_preserves_regular_fields(self):
        """Test that cleaning preserves non-underscore fields."""
        entities = [
            {
                "id": "P-001",
                "uid": "proj0001",
                "title": "Test Project",
                "description": "A test",
                "status": "active",
                "tags": ["test"],
                "_file": {"path": "/test"}
            }
        ]
        
        cleaned = ListOperation.clean_entities_for_output(entities, remove_file_metadata=True)
        
        assert cleaned[0]["id"] == "P-001"
        assert cleaned[0]["uid"] == "proj0001"
        assert cleaned[0]["title"] == "Test Project"
        assert cleaned[0]["description"] == "A test"
        assert cleaned[0]["status"] == "active"
        assert cleaned[0]["tags"] == ["test"]


class TestListOperationBehavioralParity:
    """Tests to verify behavioral parity between CLI and MCP usage."""
    
    def test_filter_combination_produces_consistent_results(self, temp_registry):
        """Test that filter combinations produce consistent results."""
        operation = ListOperation(temp_registry)
        
        # Apply filters in different ways, should get same result
        result1 = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.ACTIVE,
            tags=["test", "cli"],
            category="software.dev/cli-tool"
        )
        
        # Load, then filter manually
        entities = operation.load_entities(EntityType.PROJECT)
        filtered = operation.filter_entities(
            entities,
            status=EntityStatus.ACTIVE,
            tags=["test", "cli"],
            category="software.dev/cli-tool"
        )
        
        assert result1["count"] == len(filtered)
        assert result1["entities"][0]["id"] == filtered[0]["id"] if filtered else True
    
    def test_sort_then_limit_order(self, temp_registry):
        """Test that sorting happens before limiting."""
        operation = ListOperation(temp_registry)
        
        # Get sorted results with max items
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            sort_field=SortField.TITLE,
            descending=False,
            max_items=2
        )
        
        # Should have the first 2 alphabetically
        assert result["count"] == 2
        assert result["entities"][0]["title"] == "Alpha Project"
        assert result["entities"][1]["title"] == "Beta Project"
    
    def test_all_filters_work_together(self, temp_registry):
        """Test that all filter types can be combined."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.ACTIVE,
            tags=["test"],
            category="software.dev/cli-tool",
            parent="prog0001",
            identifier=None,  # Not filtering by ID here
            query="Alpha",
            due_before="2024-12-31",
            due_after="2024-01-01"
        )
        
        assert result["success"] is True
        # Should find P-001 which matches all criteria
        assert result["count"] == 1
        assert result["entities"][0]["id"] == "P-001"
    
    def test_empty_filter_values_ignored(self, temp_registry):
        """Test that empty/None filter values are properly ignored."""
        operation = ListOperation(temp_registry)
        
        result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=None,
            tags=None,
            category=None,
            parent=None,
            identifier=None,
            query=None,
            due_before=None,
            due_after=None
        )
        
        # Should return all projects
        assert result["success"] is True
        assert result["count"] == 3


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_invalid_yaml_file_skipped(self, temp_registry):
        """Test that invalid YAML files are skipped gracefully."""
        # Create an invalid YAML file
        invalid_path = Path(temp_registry) / "projects" / "proj-invalid.yml"
        invalid_path.write_text("invalid: yaml: content: [")
        
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        # Should still load valid entities
        assert len(entities) >= 3
    
    def test_empty_yaml_file_skipped(self, temp_registry):
        """Test that empty YAML files are skipped gracefully."""
        # Create an empty YAML file
        empty_path = Path(temp_registry) / "projects" / "proj-empty.yml"
        empty_path.write_text("")
        
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        # Should still load valid entities
        assert len(entities) >= 3
    
    def test_non_dict_yaml_file_skipped(self, temp_registry):
        """Test that YAML files with non-dict content are skipped."""
        # Create a YAML file with a list instead of dict
        list_path = Path(temp_registry) / "projects" / "proj-list.yml"
        list_path.write_text("- item1\n- item2\n")
        
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        # Should still load valid entities
        assert len(entities) >= 3
    
    def test_entity_without_optional_fields(self, temp_registry):
        """Test loading entity that lacks optional fields."""
        # Create a minimal entity
        minimal_entity = {
            "type": "project",
            "uid": "proj-minimal",
            "id": "P-MIN",
            "title": "Minimal Project",
            "status": "active"
        }
        minimal_path = Path(temp_registry) / "projects" / "proj-proj-minimal.yml"
        minimal_path.write_text(yaml.dump(minimal_entity))
        
        operation = ListOperation(temp_registry)
        
        # Should be able to filter without errors
        entities = operation.load_entities(EntityType.PROJECT)
        filtered = operation.filter_entities(entities, tags=["nonexistent"])
        
        # Minimal entity has no tags, should be excluded
        assert all(e["id"] != "P-MIN" for e in filtered)
    
    def test_filter_entities_with_missing_status(self, temp_registry):
        """Test filtering entities that lack status field."""
        # Create entity without status
        no_status = {
            "type": "project",
            "uid": "proj-nostatus",
            "id": "P-NOSTAT",
            "title": "No Status Project"
        }
        no_status_path = Path(temp_registry) / "projects" / "proj-proj-nostatus.yml"
        no_status_path.write_text(yaml.dump(no_status))
        
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        # Filter by status should exclude entity without status
        filtered = operation.filter_entities(entities, status=EntityStatus.ACTIVE)
        
        assert all(e["id"] != "P-NOSTAT" for e in filtered)
    
    def test_sort_handles_missing_sort_field(self, temp_registry):
        """Test sorting when some entities lack the sort field."""
        # Create entity without due_date
        no_due = {
            "type": "project",
            "uid": "proj-nodue",
            "id": "P-NODUE",
            "title": "No Due Date Project",
            "status": "active"
        }
        no_due_path = Path(temp_registry) / "projects" / "proj-proj-nodue.yml"
        no_due_path.write_text(yaml.dump(no_due))
        
        operation = ListOperation(temp_registry)
        entities = operation.load_entities(EntityType.PROJECT)
        
        # Sort by due_date should not raise
        sorted_entities = operation.sort_entities(entities, SortField.DUE_DATE)
        
        assert len(sorted_entities) >= 4  # Original 3 + new one