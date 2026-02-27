"""
Tests for MCP Server implementation.

This module tests the Model Context Protocol server that enables LLM access
to HoxCore registries through standardized protocol interfaces.
"""
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from hxc.mcp.server import MCPServer, create_server
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
    project_content = """
type: project
uid: proj-test-001
id: P-001
title: Test Project
description: A test project for MCP server testing
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
    (registry_path / "projects" / "proj-test-001.yml").write_text(project_content)
    
    program_content = """
type: program
uid: prog-test-001
id: PRG-001
title: Test Program
description: A test program
status: active
category: software.dev
tags: [test, program]
children: [proj-test-001]
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
"""
    (registry_path / "missions" / "miss-test-001.yml").write_text(mission_content)
    
    yield str(registry_path)
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def mcp_server(temp_registry):
    """Create an MCP server instance with test registry"""
    return create_server(registry_path=temp_registry)


class TestMCPServerInitialization:
    """Tests for MCP server initialization"""
    
    def test_create_server(self, temp_registry):
        """Test server creation"""
        server = create_server(registry_path=temp_registry)
        assert server is not None
        assert isinstance(server, MCPServer)
        assert server.registry_path == temp_registry
    
    def test_create_server_without_registry(self):
        """Test server creation without registry path"""
        server = create_server()
        assert server is not None
        assert isinstance(server, MCPServer)
    
    def test_server_capabilities(self, mcp_server):
        """Test server capabilities"""
        capabilities = mcp_server.get_capabilities()
        
        assert "tools" in capabilities
        assert "resources" in capabilities
        assert "prompts" in capabilities
        assert "registry_path" in capabilities
        
        assert len(capabilities["tools"]) > 0
        assert len(capabilities["resources"]) > 0
        assert len(capabilities["prompts"]) > 0
    
    def test_server_has_required_tools(self, mcp_server):
        """Test that server has all required tools"""
        capabilities = mcp_server.get_capabilities()
        tools = capabilities["tools"]
        
        required_tools = [
            "list_entities",
            "get_entity",
            "search_entities",
            "get_entity_property"
        ]
        
        for tool in required_tools:
            assert tool in tools
    
    def test_server_has_required_resources(self, mcp_server):
        """Test that server has all required resources"""
        capabilities = mcp_server.get_capabilities()
        resources = capabilities["resources"]
        
        required_resources = [
            "entity",
            "entities",
            "hierarchy",
            "stats",
            "search"
        ]
        
        for resource in required_resources:
            assert resource in resources
    
    def test_server_has_required_prompts(self, mcp_server):
        """Test that server has all required prompts"""
        capabilities = mcp_server.get_capabilities()
        prompts = capabilities["prompts"]
        
        required_prompts = [
            "get_entity",
            "search_entities",
            "list_entities",
            "get_entity_property"
        ]
        
        for prompt in required_prompts:
            assert prompt in prompts


class TestMCPServerInitializeRequest:
    """Tests for initialize request handling"""
    
    def test_initialize_request(self, mcp_server):
        """Test initialize request"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {}
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        result = response["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert "capabilities" in result
        assert "serverInfo" in result
        
        server_info = result["serverInfo"]
        assert server_info["name"] == "hoxcore-mcp-server"
        assert "version" in server_info
    
    def test_initialize_capabilities(self, mcp_server):
        """Test initialize response capabilities"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = mcp_server.handle_request(request)
        result = response["result"]
        capabilities = result["capabilities"]
        
        assert "tools" in capabilities
        assert "resources" in capabilities
        assert "prompts" in capabilities


class TestMCPServerToolsRequests:
    """Tests for tools-related requests"""
    
    def test_tools_list_request(self, mcp_server):
        """Test tools/list request"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        result = response["result"]
        assert "tools" in result
        assert len(result["tools"]) > 0
        
        # Check tool structure
        tool = result["tools"][0]
        assert "name" in tool
        assert "description" in tool
        assert "inputSchema" in tool
    
    def test_tools_call_list_entities(self, mcp_server):
        """Test tools/call for list_entities"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_entities",
                "arguments": {
                    "entity_type": "project"
                }
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        result = response["result"]
        assert "content" in result
        assert len(result["content"]) > 0
        
        content = result["content"][0]
        assert content["type"] == "text"
        
        # Parse the JSON response
        data = json.loads(content["text"])
        assert data["success"] is True
        assert "entities" in data
        assert len(data["entities"]) > 0
    
    def test_tools_call_get_entity(self, mcp_server):
        """Test tools/call for get_entity"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_entity",
                "arguments": {
                    "identifier": "P-001"
                }
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        content = result["content"][0]
        data = json.loads(content["text"])
        
        assert data["success"] is True
        assert "entity" in data
        assert data["entity"]["id"] == "P-001"
        assert data["entity"]["title"] == "Test Project"
    
    def test_tools_call_search_entities(self, mcp_server):
        """Test tools/call for search_entities"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_entities",
                "arguments": {
                    "query": "test",
                    "entity_type": "all"
                }
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        content = result["content"][0]
        data = json.loads(content["text"])
        
        assert data["success"] is True
        assert "entities" in data
        assert data["count"] > 0
    
    def test_tools_call_get_entity_property(self, mcp_server):
        """Test tools/call for get_entity_property"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_entity_property",
                "arguments": {
                    "identifier": "P-001",
                    "property": "title"
                }
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        content = result["content"][0]
        data = json.loads(content["text"])
        
        assert data["success"] is True
        assert data["value"] == "Test Project"
    
    def test_tools_call_unknown_tool(self, mcp_server):
        """Test tools/call with unknown tool"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "unknown_tool",
                "arguments": {}
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == -32603


class TestMCPServerResourcesRequests:
    """Tests for resources-related requests"""
    
    def test_resources_list_request(self, mcp_server):
        """Test resources/list request"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list",
            "params": {}
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        result = response["result"]
        assert "resources" in result
        assert len(result["resources"]) > 0
        
        # Check resource structure
        resource = result["resources"][0]
        assert "uri" in resource
        assert "name" in resource
        assert "description" in resource
        assert "mimeType" in resource
    
    def test_resources_read_entity(self, mcp_server):
        """Test resources/read for entity"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "hxc://entity/P-001"
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert "contents" in result
        assert len(result["contents"]) > 0
        
        content = result["contents"][0]
        assert content["uri"] == "hxc://entity/P-001"
        assert "text" in content
        
        # Parse the entity data
        data = json.loads(content["text"])
        assert data["id"] == "P-001"
        assert data["title"] == "Test Project"
    
    def test_resources_read_entities_list(self, mcp_server):
        """Test resources/read for entities list"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "hxc://entities/project"
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        content = result["contents"][0]
        data = json.loads(content["text"])
        
        assert "entities" in data
        assert "total" in data
        assert data["total"] > 0
    
    def test_resources_read_hierarchy(self, mcp_server):
        """Test resources/read for hierarchy"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "hxc://hierarchy/proj-test-001"
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        content = result["contents"][0]
        data = json.loads(content["text"])
        
        assert "root" in data
        assert "children" in data
        assert "related" in data
    
    def test_resources_read_stats(self, mcp_server):
        """Test resources/read for stats"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "hxc://registry/stats"
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        content = result["contents"][0]
        data = json.loads(content["text"])
        
        assert "total_entities" in data
        assert "by_type" in data
        assert "by_status" in data
        assert data["total_entities"] > 0
    
    def test_resources_read_search(self, mcp_server):
        """Test resources/read for search"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "hxc://search?q=test"
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        content = result["contents"][0]
        data = json.loads(content["text"])
        
        assert "query" in data
        assert "entities" in data
        assert "total" in data
        assert data["query"] == "test"
    
    def test_resources_read_invalid_uri(self, mcp_server):
        """Test resources/read with invalid URI"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {
                "uri": "invalid://uri"
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "error" in response


class TestMCPServerPromptsRequests:
    """Tests for prompts-related requests"""
    
    def test_prompts_list_request(self, mcp_server):
        """Test prompts/list request"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/list",
            "params": {}
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        
        result = response["result"]
        assert "prompts" in result
        assert len(result["prompts"]) > 0
        
        # Check prompt structure
        prompt = result["prompts"][0]
        assert "name" in prompt
        assert "description" in prompt
        assert "arguments" in prompt
    
    def test_prompts_get_request(self, mcp_server):
        """Test prompts/get request"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": "get_entity",
                "arguments": {
                    "identifier": "P-001"
                }
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "result" in response
        
        result = response["result"]
        assert "description" in result
        assert "messages" in result
        assert len(result["messages"]) > 0
        
        message = result["messages"][0]
        assert message["role"] == "user"
        assert "content" in message
    
    def test_prompts_get_unknown_prompt(self, mcp_server):
        """Test prompts/get with unknown prompt"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "prompts/get",
            "params": {
                "name": "unknown_prompt",
                "arguments": {}
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert "error" in response


class TestMCPServerErrorHandling:
    """Tests for error handling"""
    
    def test_unknown_method(self, mcp_server):
        """Test handling of unknown method"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "unknown/method",
            "params": {}
        }
        
        response = mcp_server.handle_request(request)
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert response["error"]["code"] == -32601
    
    def test_invalid_json_rpc(self, mcp_server):
        """Test handling of invalid JSON-RPC request"""
        request = {
            "invalid": "request"
        }
        
        response = mcp_server.handle_request(request)
        
        assert "error" in response
    
    def test_missing_params(self, mcp_server):
        """Test handling of missing required parameters"""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "get_entity"
                # Missing required 'arguments'
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert "error" in response or "result" in response


class TestMCPServerCustomRegistration:
    """Tests for custom tool/resource/prompt registration"""
    
    def test_register_custom_tool(self, mcp_server):
        """Test registering a custom tool"""
        def custom_tool(**kwargs):
            return {"custom": "result"}
        
        mcp_server.register_tool("custom_tool", custom_tool)
        
        capabilities = mcp_server.get_capabilities()
        assert "custom_tool" in capabilities["tools"]
    
    def test_register_custom_resource(self, mcp_server):
        """Test registering a custom resource"""
        def custom_resource(**kwargs):
            return {"uri": "custom://resource", "content": {}}
        
        mcp_server.register_resource("custom_resource", custom_resource)
        
        capabilities = mcp_server.get_capabilities()
        assert "custom_resource" in capabilities["resources"]
    
    def test_register_custom_prompt(self, mcp_server):
        """Test registering a custom prompt"""
        custom_prompt = {
            "name": "custom_prompt",
            "description": "A custom prompt",
            "arguments": []
        }
        
        mcp_server.register_prompt(custom_prompt)
        
        capabilities = mcp_server.get_capabilities()
        assert "custom_prompt" in capabilities["prompts"]
    
    def test_call_custom_tool(self, mcp_server):
        """Test calling a registered custom tool"""
        def custom_tool(**kwargs):
            return {"custom": "result", "args": kwargs}
        
        mcp_server.register_tool("custom_tool", custom_tool)
        
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "custom_tool",
                "arguments": {"test": "value"}
            }
        }
        
        response = mcp_server.handle_request(request)
        
        assert "result" in response
        result = response["result"]
        content = result["content"][0]
        data = json.loads(content["text"])
        
        assert data["custom"] == "result"
        assert "args" in data


class TestMCPServerIntegration:
    """Integration tests for MCP server"""
    
    def test_full_workflow_list_and_get(self, mcp_server):
        """Test full workflow: list entities then get specific entity"""
        # First, list entities
        list_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "list_entities",
                "arguments": {"entity_type": "project"}
            }
        }
        
        list_response = mcp_server.handle_request(list_request)
        assert "result" in list_response
        
        list_data = json.loads(list_response["result"]["content"][0]["text"])
        assert list_data["success"] is True
        assert len(list_data["entities"]) > 0
        
        # Get first entity's ID
        entity_id = list_data["entities"][0]["id"]
        
        # Then, get specific entity
        get_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_entity",
                "arguments": {"identifier": entity_id}
            }
        }
        
        get_response = mcp_server.handle_request(get_request)
        assert "result" in get_response
        
        get_data = json.loads(get_response["result"]["content"][0]["text"])
        assert get_data["success"] is True
        assert get_data["entity"]["id"] == entity_id
    
    def test_full_workflow_search_and_property(self, mcp_server):
        """Test full workflow: search entities then get property"""
        # First, search entities
        search_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "search_entities",
                "arguments": {
                    "query": "test",
                    "entity_type": "all"
                }
            }
        }
        
        search_response = mcp_server.handle_request(search_request)
        assert "result" in search_response
        
        search_data = json.loads(search_response["result"]["content"][0]["text"])
        assert search_data["success"] is True
        assert search_data["count"] > 0
        
        # Get first entity's ID
        entity_id = search_data["entities"][0]["id"]
        
        # Then, get entity property
        property_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_entity_property",
                "arguments": {
                    "identifier": entity_id,
                    "property": "title"
                }
            }
        }
        
        property_response = mcp_server.handle_request(property_request)
        assert "result" in property_response
        
        property_data = json.loads(property_response["result"]["content"][0]["text"])
        assert property_data["success"] is True
        assert "value" in property_data
    
    def test_multiple_sequential_requests(self, mcp_server):
        """Test handling multiple sequential requests"""
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/list",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "prompts/list",
                "params": {}
            }
        ]
        
        for request in requests:
            response = mcp_server.handle_request(request)
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == request["id"]
            assert "result" in response