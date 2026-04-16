"""
Tests for MCP Tools implementation.

This module contains high-level integration tests and server-level tests
for MCP tools. Specific tool tests are organized in separate files:

- test_tools_init.py: Tests for init_registry_tool
- test_tools_list.py: Tests for list_entities_tool and search_entities_tool
- test_tools_get.py: Tests for get_entity_tool, get_entity_property_tool, etc.
- test_tools_create.py: Tests for create_entity_tool
- test_tools_edit.py: Tests for edit_entity_tool
- test_tools_delete.py: Tests for delete_entity_tool
- test_tools_registry.py: Tests for registry management tools
- test_tools_validate.py: Tests for validation functionality
- test_tools_show.py: Tests for show-related functionality
- test_tools_common.py: Common test utilities and helpers
- conftest.py: Shared pytest fixtures
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from hxc.mcp.server import create_server
from hxc.mcp.tools import (
    create_entity_tool,
    delete_entity_tool,
    edit_entity_tool,
    get_entity_hierarchy_tool,
    get_entity_property_tool,
    get_entity_tool,
    get_registry_stats_tool,
    list_entities_tool,
    search_entities_tool,
)


class TestReadOnlyServer:
    """Tests for the --read-only server mode"""

    def test_read_only_server_omits_write_tools(self, temp_registry):
        """Test that a read-only server does not expose write tools"""
        server = create_server(registry_path=temp_registry, read_only=True)
        capabilities = server.get_capabilities()
        tools = capabilities["tools"]

        assert "list_entities" in tools
        assert "get_entity" in tools
        assert "search_entities" in tools
        assert "get_entity_property" in tools

        assert "init_registry" not in tools
        assert "create_entity" not in tools
        assert "edit_entity" not in tools
        assert "delete_entity" not in tools

    def test_read_only_server_capabilities_flag(self, temp_registry):
        """Test that read_only is reflected in capabilities"""
        server = create_server(registry_path=temp_registry, read_only=True)
        assert server.get_capabilities()["read_only"] is True

    def test_non_read_only_server_exposes_write_tools(self, temp_registry):
        """Test that a normal server does expose write tools"""
        server = create_server(registry_path=temp_registry, read_only=False)
        tools = server.get_capabilities()["tools"]

        assert "init_registry" in tools
        assert "create_entity" in tools
        assert "edit_entity" in tools
        assert "delete_entity" in tools

    def test_read_only_server_rejects_write_tool_call(self, temp_registry):
        """Test that calling a write tool on a read-only server returns an error"""
        server = create_server(registry_path=temp_registry, read_only=True)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_entity",
                "arguments": {"type": "project", "title": "Blocked"},
            },
        }

        response = server.handle_request(request)
        assert "error" in response


class TestToolsIntegration:
    """Integration tests for MCP tools"""

    def test_list_then_get(self, temp_registry):
        """Test listing entities then getting specific one"""
        list_result = list_entities_tool(
            entity_type="project", registry_path=temp_registry
        )

        assert list_result["success"] is True
        assert len(list_result["entities"]) > 0

        entity_id = list_result["entities"][0]["id"]
        get_result = get_entity_tool(identifier=entity_id, registry_path=temp_registry)

        assert get_result["success"] is True
        assert get_result["entity"]["id"] == entity_id

    def test_search_then_get_property(self, temp_registry):
        """Test searching then getting property"""
        search_result = search_entities_tool(query="test", registry_path=temp_registry)

        assert search_result["success"] is True
        assert search_result["count"] > 0

        entity_id = search_result["entities"][0]["id"]
        property_result = get_entity_property_tool(
            identifier=entity_id, property_name="title", registry_path=temp_registry
        )

        assert property_result["success"] is True
        assert "value" in property_result

    def test_get_hierarchy_then_get_children(self, temp_registry):
        """Test getting hierarchy then getting children"""
        hierarchy_result = get_entity_hierarchy_tool(
            identifier="prog-test-001",
            include_children=True,
            registry_path=temp_registry,
        )

        assert hierarchy_result["success"] is True
        children = hierarchy_result["hierarchy"]["children"]
        assert len(children) > 0

        child_id = children[0]["id"]
        child_result = get_entity_tool(identifier=child_id, registry_path=temp_registry)

        assert child_result["success"] is True

    def test_stats_then_list_by_type(self, temp_registry):
        """Test getting stats then listing by type"""
        stats_result = get_registry_stats_tool(registry_path=temp_registry)

        assert stats_result["success"] is True
        by_type = stats_result["stats"]["by_type"]

        for entity_type, count in by_type.items():
            list_result = list_entities_tool(
                entity_type=entity_type, registry_path=temp_registry
            )

            assert list_result["success"] is True
            assert list_result["count"] == count


class TestWriteToolsIntegration:
    """Integration tests for the full create → edit → delete lifecycle"""

    def test_create_then_get(self, temp_registry):
        """Test creating an entity and then retrieving it"""
        create_result = create_entity_tool(
            type="project",
            title="Integration Project",
            use_git=False,
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
            use_git=False,
            registry_path=temp_registry,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]

        edit_result = edit_entity_tool(
            identifier=uid,
            set_title="Updated Mission",
            add_tags=["important"],
            use_git=False,
            registry_path=temp_registry,
        )

        assert edit_result["success"] is True
        assert edit_result["entity"]["title"] == "Updated Mission"
        assert "important" in edit_result["entity"]["tags"]

    def test_create_edit_delete_lifecycle(self, temp_registry):
        """Test the full entity lifecycle"""
        create_result = create_entity_tool(
            type="action",
            title="Lifecycle Action",
            use_git=False,
            registry_path=temp_registry,
        )
        assert create_result["success"] is True
        uid = create_result["uid"]
        file_path = Path(create_result["file_path"])
        assert file_path.exists()

        edit_result = edit_entity_tool(
            identifier=uid,
            set_status="completed",
            use_git=False,
            registry_path=temp_registry,
        )
        assert edit_result["success"] is True

        confirm_result = delete_entity_tool(
            identifier=uid,
            force=False,
            registry_path=temp_registry,
        )
        assert confirm_result.get("confirmation_required") is True
        assert file_path.exists()

        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=False,
            registry_path=temp_registry,
        )
        assert delete_result["success"] is True
        assert not file_path.exists()

    def test_create_with_git_then_verify_commit(self, git_registry):
        """Test creating with git and verifying the commit exists"""
        create_result = create_entity_tool(
            type="project",
            title="Git Integration Test",
            id="P-GIT-INT",
            use_git=True,
            registry_path=git_registry,
        )

        assert create_result["success"] is True
        assert create_result["git_committed"] is True

        get_result = get_entity_tool(
            identifier="P-GIT-INT",
            registry_path=git_registry,
        )

        assert get_result["success"] is True
        assert get_result["entity"]["title"] == "Git Integration Test"

        log = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Git Integration Test" in log.stdout
        assert "P-GIT-INT" in log.stdout

    def test_create_then_delete_with_git(self, git_registry):
        """Test creating and then deleting an entity with git integration"""
        create_result = create_entity_tool(
            type="project",
            title="Git Delete Test",
            id="P-GIT-DEL",
            use_git=True,
            registry_path=git_registry,
        )

        assert create_result["success"] is True
        uid = create_result["uid"]

        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=True,
            registry_path=git_registry,
        )

        assert delete_result["success"] is True
        assert delete_result["git_committed"] is True

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        assert "Create" in log.stdout or "Git Delete Test" in log.stdout
        assert "Delete" in log.stdout

    def test_full_lifecycle_with_git(self, git_registry):
        """Test full create -> edit -> delete lifecycle with git"""
        create_result = create_entity_tool(
            type="project",
            title="Lifecycle Git Test",
            id="P-LIFECYCLE",
            use_git=True,
            registry_path=git_registry,
        )
        assert create_result["success"] is True
        assert create_result["git_committed"] is True
        uid = create_result["uid"]

        edit_result = edit_entity_tool(
            identifier=uid,
            set_title="Lifecycle Git Test - Edited",
            use_git=True,
            registry_path=git_registry,
        )
        assert edit_result["success"] is True
        assert edit_result["git_committed"] is True

        delete_result = delete_entity_tool(
            identifier=uid,
            force=True,
            use_git=True,
            registry_path=git_registry,
        )
        assert delete_result["success"] is True
        assert delete_result["git_committed"] is True

        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=git_registry,
            capture_output=True,
            text=True,
            check=True,
        )

        commit_count = len(log.stdout.strip().splitlines())
        assert commit_count >= 4


class TestToolsErrorHandling:
    """Tests for error handling in tools"""

    def test_list_with_security_error(self):
        """Test list with path security error"""
        result = list_entities_tool(entity_type="all", registry_path="/etc/passwd")

        assert result["success"] is False
        assert "error" in result

    def test_get_with_security_error(self):
        """Test get with path security error"""
        result = get_entity_tool(identifier="test", registry_path="/etc/passwd")

        assert result["success"] is False
        assert "error" in result

    def test_search_with_empty_query(self, temp_registry):
        """Test search with empty query"""
        result = search_entities_tool(query="", registry_path=temp_registry)

        assert result["success"] is True
        assert result["count"] >= 0

    def test_property_with_none_value(self, temp_registry):
        """Test getting property with None value"""
        result = get_entity_property_tool(
            identifier="P-001",
            property_name="completion_date",
            registry_path=temp_registry,
        )

        assert result["success"] is False
        assert (
            "not found" in result["error"].lower()
            or "not set" in result["error"].lower()
        )


class TestServerToolsCall:
    """Tests for server tools/call functionality"""

    def test_server_list_entities_call(self, temp_registry):
        """Test calling list_entities through server"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_entities",
                "arguments": {"entity_type": "all"},
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert "entities" in data

    def test_server_get_entity_call(self, temp_registry):
        """Test calling get_entity through server"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_entity",
                "arguments": {"identifier": "P-001"},
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert data["entity"]["id"] == "P-001"

    def test_server_create_entity_call(self, temp_registry):
        """Test calling create_entity through server"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "create_entity",
                "arguments": {
                    "type": "project",
                    "title": "Server Created Project",
                },
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert "uid" in data

    def test_server_edit_entity_call(self, temp_registry):
        """Test calling edit_entity through server"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "edit_entity",
                "arguments": {
                    "identifier": "P-001",
                    "set_title": "Server Edited Title",
                },
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert data["entity"]["title"] == "Server Edited Title"

    def test_server_delete_entity_call(self, temp_registry):
        """Test calling delete_entity through server"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "delete_entity",
                "arguments": {
                    "identifier": "P-002",
                    "force": True,
                },
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert data["deleted_type"] == "project"

    def test_server_search_entities_call(self, temp_registry):
        """Test calling search_entities through server"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_entities",
                "arguments": {"query": "test"},
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert "entities" in data

    def test_server_get_entity_property_call(self, temp_registry):
        """Test calling get_entity_property through server"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_entity_property",
                "arguments": {
                    "identifier": "P-001",
                    "property": "title",
                },
            },
        }

        response = server.handle_request(request)

        assert "result" in response
        content = response["result"]["content"][0]
        data = json.loads(content["text"])

        assert data["success"] is True
        assert data["value"] == "Test Project One"


class TestAllToolsAvailability:
    """Tests for verifying all tools are properly registered"""

    def test_all_read_tools_registered(self, temp_registry):
        """Test that all read tools are registered"""
        server = create_server(registry_path=temp_registry, read_only=True)
        tools = server.get_capabilities()["tools"]

        read_tools = [
            "list_entities",
            "get_entity",
            "search_entities",
            "get_entity_property",
            "get_registry_path",
            "validate_registry_path",
            "list_registries",
            "discover_registry",
        ]

        for tool in read_tools:
            assert tool in tools, f"Read tool '{tool}' should be available"

    def test_all_write_tools_registered(self, temp_registry):
        """Test that all write tools are registered"""
        server = create_server(registry_path=temp_registry, read_only=False)
        tools = server.get_capabilities()["tools"]

        write_tools = [
            "init_registry",
            "create_entity",
            "edit_entity",
            "delete_entity",
            "set_registry_path",
            "clear_registry_path",
        ]

        for tool in write_tools:
            assert tool in tools, f"Write tool '{tool}' should be available"

    def test_tool_schemas_defined(self, temp_registry):
        """Test that all tools have schemas defined"""
        server = create_server(registry_path=temp_registry, read_only=False)

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }

        response = server.handle_request(request)

        assert "result" in response
        tools = response["result"]["tools"]

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["inputSchema"]["type"] == "object"
            assert "properties" in tool["inputSchema"]