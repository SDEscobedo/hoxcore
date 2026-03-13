"""
Tests for MCP Tools implementation.

This module tests the tools that enable LLM interaction with HoxCore registries
through the Model Context Protocol.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List

from hxc.mcp.tools import (
    list_entities_tool,
    get_entity_tool,
    search_entities_tool,
    get_entity_property_tool,
    get_entity_hierarchy_tool,
    get_registry_stats_tool,
    create_entity_tool,
    edit_entity_tool,
    delete_entity_tool,
)
from hxc.core.enums import EntityType


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
    config_content = """
registry:
  version: "1.0"
  name: "Test Registry"
"""
    (registry_path / "config.yml").write_text(config_content)
    
    # Create test entities
    project1_content = """
type: project
uid: proj-test-001
id: P-001
title: Test Project One
description: A test project for MCP tools testing
status: active
category: software.dev/cli-tool
tags: [test, mcp, cli]
start_date: 2024-01-01
due_date: 2024-12-31
repositories:
  - name: github
    url: https://github.com/test/repo
storage:
  - name: gdrive
    provider: google-drive
    url: https://drive.google.com/test
"""
    (registry_path / "projects" / "proj-test-001.yml").write_text(project1_content)
    
    project2_content = """
type: project
uid: proj-test-002
id: P-002
title: Test Project Two
description: Another test project
status: completed
category: software.dev/web-app
tags: [test, web]
start_date: 2024-01-01
completion_date: 2024-06-30
"""
    (registry_path / "projects" / "proj-test-002.yml").write_text(project2_content)
    
    program_content = """
type: program
uid: prog-test-001
id: PRG-001
title: Test Program
description: A test program
status: active
category: software.dev
tags: [test, program]
children: [proj-test-001, proj-test-002]
"""
    (registry_path / "programs" / "prog-test-001.yml").write_text(program_content)
    
    mission_content = """
type: mission
uid: miss-test-001
id: M-001
title: Test Mission
description: A test mission
status: planned
category: research
tags: [test, mission]
parent: prog-test-001
"""
    (registry_path / "missions" / "miss-test-001.yml").write_text(mission_content)
    
    action_content = """
type: action
uid: act-test-001
id: A-001
title: Test Action
description: A test action
status: active
category: maintenance
tags: [test, action]
"""
    (registry_path / "actions" / "act-test-001.yml").write_text(action_content)
    
    yield str(registry_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


class TestListEntitiesTool:
    """Tests for list_entities_tool"""
    
    def test_list_all_entities(self, temp_registry):
        """Test listing all entities"""
        result = list_entities_tool(
            entity_type="all",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "entities" in result
        assert result["count"] > 0
        assert len(result["entities"]) >= 5
    
    def test_list_projects_only(self, temp_registry):
        """Test listing only projects"""
        result = list_entities_tool(
            entity_type="project",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] == 2
        
        for entity in result["entities"]:
            assert entity["type"] == "project"
    
    def test_list_programs_only(self, temp_registry):
        """Test listing only programs"""
        result = list_entities_tool(
            entity_type="program",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["type"] == "program"
    
    def test_list_missions_only(self, temp_registry):
        """Test listing only missions"""
        result = list_entities_tool(
            entity_type="mission",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["type"] == "mission"
    
    def test_list_actions_only(self, temp_registry):
        """Test listing only actions"""
        result = list_entities_tool(
            entity_type="action",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["entities"][0]["type"] == "action"
    
    def test_list_with_status_filter(self, temp_registry):
        """Test listing with status filter"""
        result = list_entities_tool(
            entity_type="all",
            status="active",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 0
        
        for entity in result["entities"]:
            assert entity["status"] == "active"
    
    def test_list_with_tags_filter(self, temp_registry):
        """Test listing with tags filter"""
        result = list_entities_tool(
            entity_type="all",
            tags=["test"],
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 0
        
        for entity in result["entities"]:
            assert "test" in entity.get("tags", [])
    
    def test_list_with_multiple_tags_filter(self, temp_registry):
        """Test listing with multiple tags filter"""
        result = list_entities_tool(
            entity_type="all",
            tags=["test", "mcp"],
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            entity_tags = entity.get("tags", [])
            assert "test" in entity_tags
            assert "mcp" in entity_tags
    
    def test_list_with_category_filter(self, temp_registry):
        """Test listing with category filter"""
        result = list_entities_tool(
            entity_type="all",
            category="software.dev/cli-tool",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 0
        
        for entity in result["entities"]:
            assert entity["category"] == "software.dev/cli-tool"
    
    def test_list_with_parent_filter(self, temp_registry):
        """Test listing with parent filter"""
        result = list_entities_tool(
            entity_type="all",
            parent="prog-test-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 0
        
        for entity in result["entities"]:
            assert entity.get("parent") == "prog-test-001"
    
    def test_list_with_max_items(self, temp_registry):
        """Test listing with max items limit"""
        result = list_entities_tool(
            entity_type="all",
            max_items=2,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] <= 2
        assert len(result["entities"]) <= 2
    
    def test_list_with_sort_by_title(self, temp_registry):
        """Test listing with sort by title"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="title",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 1
        
        titles = [e["title"] for e in result["entities"]]
        assert titles == sorted(titles)
    
    def test_list_with_sort_descending(self, temp_registry):
        """Test listing with descending sort"""
        result = list_entities_tool(
            entity_type="project",
            sort_by="title",
            descending=True,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 1
        
        titles = [e["title"] for e in result["entities"]]
        assert titles == sorted(titles, reverse=True)
    
    def test_list_with_invalid_entity_type(self, temp_registry):
        """Test listing with invalid entity type"""
        result = list_entities_tool(
            entity_type="invalid",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_list_with_invalid_status(self, temp_registry):
        """Test listing with invalid status"""
        result = list_entities_tool(
            entity_type="all",
            status="invalid",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_list_with_no_registry(self):
        """Test listing with no registry"""
        result = list_entities_tool(
            entity_type="all",
            registry_path="/nonexistent/path"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_list_filters_metadata(self, temp_registry):
        """Test that filters metadata is included in result"""
        result = list_entities_tool(
            entity_type="project",
            status="active",
            tags=["test"],
            category="software.dev/cli-tool",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["type"] == "project"
        assert result["filters"]["status"] == "active"
        assert result["filters"]["tags"] == ["test"]
        assert result["filters"]["category"] == "software.dev/cli-tool"
    
    def test_list_sort_metadata(self, temp_registry):
        """Test that sort metadata is included in result"""
        result = list_entities_tool(
            entity_type="all",
            sort_by="title",
            descending=True,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "sort" in result
        assert result["sort"]["field"] == "title"
        assert result["sort"]["descending"] is True


class TestGetEntityTool:
    """Tests for get_entity_tool"""
    
    def test_get_entity_by_id(self, temp_registry):
        """Test getting entity by ID"""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "entity" in result
        assert result["entity"]["id"] == "P-001"
        assert result["entity"]["title"] == "Test Project One"
    
    def test_get_entity_by_uid(self, temp_registry):
        """Test getting entity by UID"""
        result = get_entity_tool(
            identifier="proj-test-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["entity"]["uid"] == "proj-test-001"
        assert result["entity"]["id"] == "P-001"
    
    def test_get_entity_with_type_filter(self, temp_registry):
        """Test getting entity with type filter"""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="project",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["entity"]["type"] == "project"
    
    def test_get_entity_program(self, temp_registry):
        """Test getting a program entity"""
        result = get_entity_tool(
            identifier="PRG-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["entity"]["type"] == "program"
        assert result["entity"]["title"] == "Test Program"
    
    def test_get_entity_mission(self, temp_registry):
        """Test getting a mission entity"""
        result = get_entity_tool(
            identifier="M-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["entity"]["type"] == "mission"
        assert result["entity"]["title"] == "Test Mission"
    
    def test_get_entity_action(self, temp_registry):
        """Test getting an action entity"""
        result = get_entity_tool(
            identifier="A-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["entity"]["type"] == "action"
        assert result["entity"]["title"] == "Test Action"
    
    def test_get_entity_not_found(self, temp_registry):
        """Test getting non-existent entity"""
        result = get_entity_tool(
            identifier="NONEXISTENT",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()
    
    def test_get_entity_with_invalid_type(self, temp_registry):
        """Test getting entity with invalid type"""
        result = get_entity_tool(
            identifier="P-001",
            entity_type="invalid",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_entity_includes_file_path(self, temp_registry):
        """Test that result includes file path"""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "file_path" in result
        assert "proj-test-001.yml" in result["file_path"]
    
    def test_get_entity_includes_identifier(self, temp_registry):
        """Test that result includes identifier"""
        result = get_entity_tool(
            identifier="P-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "identifier" in result
        assert result["identifier"] == "P-001"


class TestSearchEntitiesTool:
    """Tests for search_entities_tool"""
    
    def test_search_by_title(self, temp_registry):
        """Test searching by title"""
        result = search_entities_tool(
            query="Project One",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 0
        
        found = False
        for entity in result["entities"]:
            if "Project One" in entity["title"]:
                found = True
                break
        assert found
    
    def test_search_by_description(self, temp_registry):
        """Test searching by description"""
        result = search_entities_tool(
            query="MCP tools testing",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] > 0
    
    def test_search_case_insensitive(self, temp_registry):
        """Test that search is case insensitive"""
        result1 = search_entities_tool(
            query="test",
            registry_path=temp_registry
        )
        
        result2 = search_entities_tool(
            query="TEST",
            registry_path=temp_registry
        )
        
        assert result1["success"] is True
        assert result2["success"] is True
        assert result1["count"] == result2["count"]
    
    def test_search_with_entity_type_filter(self, temp_registry):
        """Test searching with entity type filter"""
        result = search_entities_tool(
            query="test",
            entity_type="project",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert entity["type"] == "project"
    
    def test_search_with_status_filter(self, temp_registry):
        """Test searching with status filter"""
        result = search_entities_tool(
            query="test",
            status="active",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert entity["status"] == "active"
    
    def test_search_with_tags_filter(self, temp_registry):
        """Test searching with tags filter"""
        result = search_entities_tool(
            query="test",
            tags=["mcp"],
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert "mcp" in entity.get("tags", [])
    
    def test_search_with_category_filter(self, temp_registry):
        """Test searching with category filter"""
        result = search_entities_tool(
            query="test",
            category="software.dev/cli-tool",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        
        for entity in result["entities"]:
            assert entity["category"] == "software.dev/cli-tool"
    
    def test_search_with_max_items(self, temp_registry):
        """Test searching with max items limit"""
        result = search_entities_tool(
            query="test",
            max_items=2,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] <= 2
    
    def test_search_no_results(self, temp_registry):
        """Test searching with no results"""
        result = search_entities_tool(
            query="nonexistent query string",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] == 0
        assert len(result["entities"]) == 0
    
    def test_search_includes_query(self, temp_registry):
        """Test that result includes query"""
        result = search_entities_tool(
            query="test",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "query" in result
        assert result["query"] == "test"
    
    def test_search_includes_filters(self, temp_registry):
        """Test that result includes filters"""
        result = search_entities_tool(
            query="test",
            entity_type="project",
            status="active",
            tags=["test"],
            category="software.dev/cli-tool",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "filters" in result
        assert result["filters"]["type"] == "project"
        assert result["filters"]["status"] == "active"


class TestGetEntityPropertyTool:
    """Tests for get_entity_property_tool"""
    
    def test_get_scalar_property(self, temp_registry):
        """Test getting a scalar property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["value"] == "Test Project One"
        assert result["property"] == "title"
    
    def test_get_status_property(self, temp_registry):
        """Test getting status property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="status",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["value"] == "active"
    
    def test_get_list_property(self, temp_registry):
        """Test getting a list property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert "test" in result["value"]
    
    def test_get_list_property_with_index(self, temp_registry):
        """Test getting list property with index"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            index=0,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert isinstance(result["value"], str)
    
    def test_get_list_property_invalid_index(self, temp_registry):
        """Test getting list property with invalid index"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="tags",
            index=999,
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "out of range" in result["error"].lower()
    
    def test_get_complex_property(self, temp_registry):
        """Test getting a complex property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert isinstance(result["value"], list)
        assert len(result["value"]) > 0
    
    def test_get_complex_property_with_key_filter(self, temp_registry):
        """Test getting complex property with key filter"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="name:github",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert result["value"]["name"] == "github"
    
    def test_get_complex_property_invalid_key_format(self, temp_registry):
        """Test getting complex property with invalid key format"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="invalid",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "invalid key filter" in result["error"].lower()
    
    def test_get_complex_property_key_not_found(self, temp_registry):
        """Test getting complex property with key not found"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="repositories",
            key="name:nonexistent",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "no items found" in result["error"].lower()
    
    def test_get_all_properties(self, temp_registry):
        """Test getting all properties"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="all",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert isinstance(result["value"], dict)
        assert "title" in result["value"]
        assert "status" in result["value"]
    
    def test_get_path_property(self, temp_registry):
        """Test getting path property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="path",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "proj-test-001.yml" in result["value"]
    
    def test_get_nonexistent_property(self, temp_registry):
        """Test getting non-existent property"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="nonexistent",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    def test_get_property_from_nonexistent_entity(self, temp_registry):
        """Test getting property from non-existent entity"""
        result = get_entity_property_tool(
            identifier="NONEXISTENT",
            property_name="title",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_property_includes_identifier(self, temp_registry):
        """Test that result includes identifier"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="title",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "identifier" in result
        assert result["identifier"] == "P-001"


class TestGetEntityHierarchyTool:
    """Tests for get_entity_hierarchy_tool"""
    
    def test_get_hierarchy_basic(self, temp_registry):
        """Test getting basic hierarchy"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "hierarchy" in result
        assert "root" in result["hierarchy"]
        assert result["hierarchy"]["root"]["id"] == "PRG-001"
    
    def test_get_hierarchy_with_children(self, temp_registry):
        """Test getting hierarchy with children"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "children" in hierarchy
        assert len(hierarchy["children"]) > 0
    
    def test_get_hierarchy_without_children(self, temp_registry):
        """Test getting hierarchy without children"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=False,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "children" in hierarchy
        assert len(hierarchy["children"]) == 0
    
    def test_get_hierarchy_with_parent(self, temp_registry):
        """Test getting hierarchy with parent"""
        result = get_entity_hierarchy_tool(
            identifier="miss-test-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "parent" in hierarchy
        assert hierarchy["parent"] is not None
    
    def test_get_hierarchy_without_parent(self, temp_registry):
        """Test getting hierarchy without parent"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        hierarchy = result["hierarchy"]
        assert "parent" in hierarchy
        assert hierarchy["parent"] is None
    
    def test_get_hierarchy_recursive(self, temp_registry):
        """Test getting hierarchy recursively"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            recursive=True,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "hierarchy" in result
    
    def test_get_hierarchy_includes_options(self, temp_registry):
        """Test that result includes options"""
        result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            include_related=False,
            recursive=True,
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "options" in result
        assert result["options"]["include_children"] is True
        assert result["options"]["include_related"] is False
        assert result["options"]["recursive"] is True
    
    def test_get_hierarchy_nonexistent_entity(self, temp_registry):
        """Test getting hierarchy for non-existent entity"""
        result = get_entity_hierarchy_tool(
            identifier="NONEXISTENT",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "error" in result


class TestGetRegistryStatsTool:
    """Tests for get_registry_stats_tool"""
    
    def test_get_stats_basic(self, temp_registry):
        """Test getting basic registry stats"""
        result = get_registry_stats_tool(
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "stats" in result
        assert "total_entities" in result["stats"]
        assert result["stats"]["total_entities"] > 0
    
    def test_get_stats_by_type(self, temp_registry):
        """Test stats by type"""
        result = get_registry_stats_tool(
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        stats = result["stats"]
        assert "by_type" in stats
        assert "project" in stats["by_type"]
        assert "program" in stats["by_type"]
        assert "mission" in stats["by_type"]
        assert "action" in stats["by_type"]
    
    def test_get_stats_by_status(self, temp_registry):
        """Test stats by status"""
        result = get_registry_stats_tool(
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        stats = result["stats"]
        assert "by_status" in stats
        assert "active" in stats["by_status"]
    
    def test_get_stats_by_category(self, temp_registry):
        """Test stats by category"""
        result = get_registry_stats_tool(
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        stats = result["stats"]
        assert "by_category" in stats
        assert len(stats["by_category"]) > 0
    
    def test_get_stats_tags(self, temp_registry):
        """Test stats for tags"""
        result = get_registry_stats_tool(
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        stats = result["stats"]
        assert "tags" in stats
        assert "test" in stats["tags"]
        assert stats["tags"]["test"] > 0
    
    def test_get_stats_includes_registry_path(self, temp_registry):
        """Test that result includes registry path"""
        result = get_registry_stats_tool(
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert "registry_path" in result
        assert result["registry_path"] == temp_registry
    
    def test_get_stats_no_registry(self):
        """Test getting stats with no registry"""
        result = get_registry_stats_tool(
            registry_path="/nonexistent/path"
        )
        
        assert result["success"] is False
        assert "error" in result


class TestToolsIntegration:
    """Integration tests for MCP tools"""
    
    def test_list_then_get(self, temp_registry):
        """Test listing entities then getting specific one"""
        # First list
        list_result = list_entities_tool(
            entity_type="project",
            registry_path=temp_registry
        )
        
        assert list_result["success"] is True
        assert len(list_result["entities"]) > 0
        
        # Get first entity
        entity_id = list_result["entities"][0]["id"]
        get_result = get_entity_tool(
            identifier=entity_id,
            registry_path=temp_registry
        )
        
        assert get_result["success"] is True
        assert get_result["entity"]["id"] == entity_id
    
    def test_search_then_get_property(self, temp_registry):
        """Test searching then getting property"""
        # First search
        search_result = search_entities_tool(
            query="test",
            registry_path=temp_registry
        )
        
        assert search_result["success"] is True
        assert search_result["count"] > 0
        
        # Get property from first result
        entity_id = search_result["entities"][0]["id"]
        property_result = get_entity_property_tool(
            identifier=entity_id,
            property_name="title",
            registry_path=temp_registry
        )
        
        assert property_result["success"] is True
        assert "value" in property_result
    
    def test_get_hierarchy_then_get_children(self, temp_registry):
        """Test getting hierarchy then getting children"""
        # Get hierarchy
        hierarchy_result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            registry_path=temp_registry
        )
        
        assert hierarchy_result["success"] is True
        children = hierarchy_result["hierarchy"]["children"]
        assert len(children) > 0
        
        # Get first child
        child_id = children[0]["id"]
        child_result = get_entity_tool(
            identifier=child_id,
            registry_path=temp_registry
        )
        
        assert child_result["success"] is True
    
    def test_stats_then_list_by_type(self, temp_registry):
        """Test getting stats then listing by type"""
        # Get stats
        stats_result = get_registry_stats_tool(
            registry_path=temp_registry
        )
        
        assert stats_result["success"] is True
        by_type = stats_result["stats"]["by_type"]
        
        # List each type
        for entity_type, count in by_type.items():
            list_result = list_entities_tool(
                entity_type=entity_type,
                registry_path=temp_registry
            )
            
            assert list_result["success"] is True
            assert list_result["count"] == count


class TestToolsErrorHandling:
    """Tests for error handling in tools"""
    
    def test_list_with_security_error(self):
        """Test list with path security error"""
        result = list_entities_tool(
            entity_type="all",
            registry_path="/etc/passwd"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_get_with_security_error(self):
        """Test get with path security error"""
        result = get_entity_tool(
            identifier="test",
            registry_path="/etc/passwd"
        )
        
        assert result["success"] is False
        assert "error" in result
    
    def test_search_with_empty_query(self, temp_registry):
        """Test search with empty query"""
        result = search_entities_tool(
            query="",
            registry_path=temp_registry
        )
        
        assert result["success"] is True
        assert result["count"] >= 0
    
    def test_property_with_none_value(self, temp_registry):
        """Test getting property with None value"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="completion_date",
            registry_path=temp_registry
        )
        
        assert result["success"] is False
        assert "not found" in result["error"].lower() or "not set" in result["error"].lower()

class TestCreateEntityTool:
    """Tests for create_entity_tool"""
 
    def test_create_project(self, temp_registry):
        """Test creating a project entity"""
        result = create_entity_tool(
            type="project",
            title="New Test Project",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert "uid" in result
        assert "file_path" in result
 
        # Verify file was created
        from pathlib import Path
        file_path = Path(result["file_path"])
        assert file_path.exists()
 
        import yaml
        with open(file_path) as f:
            data = yaml.safe_load(f)
 
        assert data["type"] == "project"
        assert data["title"] == "New Test Project"
        assert data["status"] == "active"
 
    def test_create_with_all_optional_fields(self, temp_registry):
        """Test creating an entity with all optional fields populated"""
        result = create_entity_tool(
            type="project",
            title="Full Project",
            description="A fully specified project",
            status="on-hold",
            id="P-999",
            category="software.dev/api",
            tags=["python", "api"],
            parent="prog-test-001",
            start_date="2025-01-01",
            due_date="2025-12-31",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        entity = result["entity"]
        assert entity["title"] == "Full Project"
        assert entity["description"] == "A fully specified project"
        assert entity["status"] == "on-hold"
        assert entity["id"] == "P-999"
        assert entity["category"] == "software.dev/api"
        assert entity["tags"] == ["python", "api"]
        assert entity["parent"] == "prog-test-001"
        assert entity["start_date"] == "2025-01-01"
        assert entity["due_date"] == "2025-12-31"
 
    def test_create_all_entity_types(self, temp_registry):
        """Test creating each entity type"""
        for entity_type in ["program", "project", "mission", "action"]:
            result = create_entity_tool(
                type=entity_type,
                title=f"Test {entity_type.title()}",
                registry_path=temp_registry,
            )
            assert result["success"] is True, f"Failed for type {entity_type}: {result.get('error')}"
 
    def test_create_default_start_date_is_today(self, temp_registry):
        """Test that start_date defaults to today"""
        import datetime
        today = datetime.date.today().isoformat()
 
        result = create_entity_tool(
            type="project",
            title="Date Test",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert result["entity"]["start_date"] == today
 
    def test_create_invalid_type(self, temp_registry):
        """Test creating with an invalid entity type"""
        result = create_entity_tool(
            type="invalid_type",
            title="Should Fail",
            registry_path=temp_registry,
        )
 
        assert result["success"] is False
        assert "error" in result
 
    def test_create_invalid_status(self, temp_registry):
        """Test creating with an invalid status"""
        result = create_entity_tool(
            type="project",
            title="Bad Status",
            status="not-a-status",
            registry_path=temp_registry,
        )
 
        assert result["success"] is False
        assert "error" in result
 
    def test_create_with_no_registry(self):
        """Test creating with a nonexistent registry path"""
        result = create_entity_tool(
            type="project",
            title="No Registry",
            registry_path="/nonexistent/path",
        )
 
        assert result["success"] is False
        assert "error" in result
 
    def test_create_file_in_correct_subfolder(self, temp_registry):
        """Test that each entity type lands in its correct subfolder"""
        from pathlib import Path
 
        type_folder_map = {
            "program": "programs",
            "project": "projects",
            "mission": "missions",
            "action": "actions",
        }
 
        for entity_type, folder in type_folder_map.items():
            result = create_entity_tool(
                type=entity_type,
                title=f"Folder Test {entity_type}",
                registry_path=temp_registry,
            )
 
            assert result["success"] is True
            file_path = Path(result["file_path"])
            assert file_path.parent.name == folder, (
                f"Expected {folder}, got {file_path.parent.name}"
            )
 
    def test_create_returns_uid_and_file_path(self, temp_registry):
        """Test that create returns uid and file_path"""
        result = create_entity_tool(
            type="project",
            title="Return Fields Test",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert isinstance(result["uid"], str)
        assert len(result["uid"]) > 0
        assert isinstance(result["file_path"], str)
 
 
class TestEditEntityTool:
    """Tests for edit_entity_tool"""
 
    def test_edit_title(self, temp_registry):
        """Test editing an entity's title"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Renamed Project",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert result["entity"]["title"] == "Renamed Project"
        assert any("title" in c for c in result["changes"])
 
    def test_edit_status(self, temp_registry):
        """Test editing an entity's status"""
        result = edit_entity_tool(
            identifier="P-001",
            set_status="completed",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert result["entity"]["status"] == "completed"
 
    def test_edit_add_tags(self, temp_registry):
        """Test adding tags to an entity"""
        result = edit_entity_tool(
            identifier="P-001",
            add_tags=["new-tag", "another-tag"],
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        tags = result["entity"]["tags"]
        assert "new-tag" in tags
        assert "another-tag" in tags
 
    def test_edit_remove_tags(self, temp_registry):
        """Test removing tags from an entity"""
        # First confirm the tag exists (fixture project has "mcp" tag)
        result = edit_entity_tool(
            identifier="P-001",
            remove_tags=["mcp"],
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert "mcp" not in result["entity"].get("tags", [])
 
    def test_edit_add_duplicate_tag_is_idempotent(self, temp_registry):
        """Test that adding an existing tag doesn't duplicate it"""
        result = edit_entity_tool(
            identifier="P-001",
            add_tags=["test"],  # "test" already exists in fixture
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        tags = result["entity"]["tags"]
        assert tags.count("test") == 1
 
    def test_edit_multiple_scalar_fields(self, temp_registry):
        """Test editing multiple scalar fields at once"""
        result = edit_entity_tool(
            identifier="P-001",
            set_title="Updated Title",
            set_description="Updated description",
            set_category="research/new",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        entity = result["entity"]
        assert entity["title"] == "Updated Title"
        assert entity["description"] == "Updated description"
        assert entity["category"] == "research/new"
        assert len(result["changes"]) == 3
 
    def test_edit_invalid_status(self, temp_registry):
        """Test editing with an invalid status value"""
        result = edit_entity_tool(
            identifier="P-001",
            set_status="not-valid",
            registry_path=temp_registry,
        )
 
        assert result["success"] is False
        assert "error" in result
 
    def test_edit_no_changes_specified(self, temp_registry):
        """Test that providing no changes returns an error"""
        result = edit_entity_tool(
            identifier="P-001",
            registry_path=temp_registry,
        )
 
        assert result["success"] is False
        assert "no changes" in result["error"].lower()
 
    def test_edit_nonexistent_entity(self, temp_registry):
        """Test editing an entity that does not exist"""
        result = edit_entity_tool(
            identifier="P-DOES-NOT-EXIST",
            set_title="Ghost",
            registry_path=temp_registry,
        )
 
        assert result["success"] is False
        assert "not found" in result["error"].lower()
 
    def test_edit_persists_to_file(self, temp_registry):
        """Test that edits are actually written to disk"""
        import yaml
        from pathlib import Path
 
        edit_result = edit_entity_tool(
            identifier="P-001",
            set_title="Persisted Title",
            registry_path=temp_registry,
        )
 
        assert edit_result["success"] is True
 
        file_path = edit_result["file_path"]
        with open(file_path) as f:
            on_disk = yaml.safe_load(f)
 
        assert on_disk["title"] == "Persisted Title"
 
    def test_edit_by_uid(self, temp_registry):
        """Test editing an entity by its UID"""
        result = edit_entity_tool(
            identifier="proj-test-001",
            set_title="UID Edit Test",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert result["entity"]["title"] == "UID Edit Test"
 
    def test_edit_returns_updated_entity(self, temp_registry):
        """Test that edit returns the full updated entity"""
        result = edit_entity_tool(
            identifier="P-001",
            set_due_date="2026-06-30",
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert "entity" in result
        assert result["entity"]["due_date"] == "2026-06-30"
        assert "identifier" in result
        assert "file_path" in result
 
 
class TestDeleteEntityTool:
    """Tests for delete_entity_tool"""
 
    def test_delete_without_force_returns_confirmation(self, temp_registry):
        """Test that calling without force=True returns a confirmation prompt"""
        result = delete_entity_tool(
            identifier="P-001",
            force=False,
            registry_path=temp_registry,
        )
 
        assert result["success"] is False
        assert result.get("confirmation_required") is True
        assert "message" in result
        assert "force=True" in result["message"]
 
        # File must still exist
        from pathlib import Path
        assert Path(temp_registry, "projects", "proj-test-001.yml").exists()
 
    def test_delete_without_force_does_not_delete(self, temp_registry):
        """Test that the entity file is NOT removed when force is False"""
        from pathlib import Path
 
        delete_entity_tool(identifier="P-001", force=False, registry_path=temp_registry)
 
        assert Path(temp_registry, "projects", "proj-test-001.yml").exists()
 
    def test_delete_with_force_removes_file(self, temp_registry):
        """Test that force=True actually deletes the file"""
        from pathlib import Path
 
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert not Path(temp_registry, "projects", "proj-test-001.yml").exists()
 
    def test_delete_returns_entity_info(self, temp_registry):
        """Test that delete returns the deleted entity's title and type"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert result["deleted_title"] == "Test Project One"
        assert result["deleted_type"] == "project"
        assert "file_path" in result
 
    def test_delete_nonexistent_entity(self, temp_registry):
        """Test deleting an entity that does not exist"""
        result = delete_entity_tool(
            identifier="P-DOES-NOT-EXIST",
            force=True,
            registry_path=temp_registry,
        )
 
        assert result["success"] is False
        assert "not found" in result["error"].lower()
 
    def test_delete_by_uid(self, temp_registry):
        """Test deleting an entity by UID"""
        from pathlib import Path
 
        result = delete_entity_tool(
            identifier="proj-test-002",
            force=True,
            registry_path=temp_registry,
        )
 
        assert result["success"] is True
        assert not Path(temp_registry, "projects", "proj-test-002.yml").exists()
 
    def test_delete_with_no_registry(self):
        """Test delete with a nonexistent registry path"""
        result = delete_entity_tool(
            identifier="P-001",
            force=True,
            registry_path="/nonexistent/path",
        )
 
        assert result["success"] is False
        assert "error" in result
 
    def test_delete_confirmation_includes_entity_details(self, temp_registry):
        """Test that the confirmation response includes entity details"""
        result = delete_entity_tool(
            identifier="P-001",
            force=False,
            registry_path=temp_registry,
        )
 
        assert result.get("confirmation_required") is True
        assert result["entity_title"] == "Test Project One"
        assert result["entity_type"] == "project"
        assert "file_path" in result
 
 
class TestReadOnlyServer:
    """Tests for the --read-only server mode"""
 
    def test_read_only_server_omits_write_tools(self, temp_registry):
        """Test that a read-only server does not expose write tools"""
        from hxc.mcp.server import create_server
 
        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]
 
        assert "list_entities" in tools
        assert "get_entity" in tools
        assert "search_entities" in tools
        assert "get_entity_property" in tools
 
        assert "create_entity" not in tools
        assert "edit_entity" not in tools
        assert "delete_entity" not in tools
 
    def test_read_only_server_capabilities_flag(self, temp_registry):
        """Test that read_only is reflected in capabilities"""
        from hxc.mcp.server import create_server
 
        server = create_server(registry_path=temp_registry, read_only=True)
        assert server.get_capabilities()["read_only"] is True
 
    def test_non_read_only_server_exposes_write_tools(self, temp_registry):
        """Test that a normal server does expose write tools"""
        from hxc.mcp.server import create_server
 
        server = create_server(registry_path=temp_registry, read_only=False)
        tools = server.get_capabilities()["tools"]
 
        assert "create_entity" in tools
        assert "edit_entity" in tools
        assert "delete_entity" in tools
 
    def test_read_only_server_rejects_write_tool_call(self, temp_registry):
        """Test that calling a write tool on a read-only server returns an error"""
        from hxc.mcp.server import create_server
 
        server = create_server(registry_path=temp_registry, read_only=True)
 
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_entity",
                "arguments": {"type": "project", "title": "Blocked"}
            }
        }
 
        response = server.handle_request(request)
        # Should return an error because the tool is not registered
        assert "error" in response
 
 
class TestWriteToolsIntegration:
    """Integration tests for the full create → edit → delete lifecycle"""
 
    def test_create_then_get(self, temp_registry):
        """Test creating an entity and then retrieving it"""
        create_result = create_entity_tool(
            type="project",
            title="Integration Project",
            registry_path=temp_registry,
        )
 
        assert create_result["success"] is True
        uid = create_result["uid"]
 
        get_result = get_entity_tool(
            identifier=uid,
            registry_path=temp_registry,
        )
 
        assert get_result["success"] is True
        assert get_result["entity"]["title"] == "Integration Project"
 
    def test_create_then_edit(self, temp_registry):
        """Test creating an entity and then editing it"""
        create_result = create_entity_tool(
            type="mission",
            title="Original Mission",
            registry_path=temp_registry,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]
 
        edit_result = edit_entity_tool(
            identifier=uid,
            set_title="Updated Mission",
            add_tags=["important"],
            registry_path=temp_registry,
        )
 
        assert edit_result["success"] is True
        assert edit_result["entity"]["title"] == "Updated Mission"
        assert "important" in edit_result["entity"]["tags"]
 
    def test_create_edit_delete_lifecycle(self, temp_registry):
        """Test the full entity lifecycle"""
        from pathlib import Path
 
        # Create
        create_result = create_entity_tool(
            type="action",
            title="Lifecycle Action",
            registry_path=temp_registry,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]
        file_path = Path(create_result["file_path"])
        assert file_path.exists()
 
        # Edit
        edit_result = edit_entity_tool(
            identifier=uid,
            set_status="completed",
            registry_path=temp_registry,
        )
        assert edit_result["success"] is True
 
        # Confirm before delete
        confirm_result = delete_entity_tool(
            identifier=uid,
            force=False,
            registry_path=temp_registry,
        )
        assert confirm_result.get("confirmation_required") is True
        assert file_path.exists()  # not deleted yet
 
        # Delete with force
        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            registry_path=temp_registry,
        )
        assert delete_result["success"] is True
        assert not file_path.exists()
