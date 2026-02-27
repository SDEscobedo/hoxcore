"""
MCP Prompts for HoxCore Registry Access.

This module provides prompt templates that guide LLMs in interacting with
HoxCore registries through the MCP protocol.
"""
from typing import Dict, Any, List, Optional


def get_entity_prompt(entity_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate a prompt template for retrieving entity information.
    
    Args:
        entity_type: Optional entity type to filter (program, project, mission, action)
        
    Returns:
        MCP prompt definition
    """
    type_filter = f" of type '{entity_type}'" if entity_type else ""
    
    return {
        "name": "get_entity",
        "description": f"Retrieve detailed information about a specific entity{type_filter} from the HoxCore registry",
        "arguments": [
            {
                "name": "identifier",
                "description": "The ID or UID of the entity to retrieve",
                "required": True
            },
            {
                "name": "type",
                "description": "Entity type (program, project, mission, action). Optional if identifier is unique.",
                "required": False
            }
        ]
    }


def search_entities_prompt() -> Dict[str, Any]:
    """
    Generate a prompt template for searching entities.
    
    Returns:
        MCP prompt definition
    """
    return {
        "name": "search_entities",
        "description": "Search for entities in the HoxCore registry using various filters",
        "arguments": [
            {
                "name": "query",
                "description": "Text to search in title and description",
                "required": False
            },
            {
                "name": "type",
                "description": "Filter by entity type (program, project, mission, action, all)",
                "required": False
            },
            {
                "name": "status",
                "description": "Filter by status (active, completed, on-hold, cancelled, planned, any)",
                "required": False
            },
            {
                "name": "tags",
                "description": "Filter by tags (comma-separated list)",
                "required": False
            },
            {
                "name": "category",
                "description": "Filter by category",
                "required": False
            },
            {
                "name": "parent",
                "description": "Filter by parent ID",
                "required": False
            }
        ]
    }


def list_entities_prompt(entity_type: str = "all") -> Dict[str, Any]:
    """
    Generate a prompt template for listing entities.
    
    Args:
        entity_type: Type of entities to list (program, project, mission, action, all)
        
    Returns:
        MCP prompt definition
    """
    type_desc = f"{entity_type}s" if entity_type != "all" else "all entities"
    
    return {
        "name": "list_entities",
        "description": f"List {type_desc} from the HoxCore registry with optional filtering and sorting",
        "arguments": [
            {
                "name": "type",
                "description": "Entity type to list (program, project, mission, action, all)",
                "required": False,
                "default": entity_type
            },
            {
                "name": "status",
                "description": "Filter by status (active, completed, on-hold, cancelled, planned, any)",
                "required": False
            },
            {
                "name": "max",
                "description": "Maximum number of items to return (0 for all)",
                "required": False,
                "default": 0
            },
            {
                "name": "sort",
                "description": "Sort field (title, id, due_date, status, created, modified)",
                "required": False,
                "default": "title"
            },
            {
                "name": "desc",
                "description": "Sort in descending order (true/false)",
                "required": False,
                "default": False
            }
        ]
    }


def get_entity_property_prompt() -> Dict[str, Any]:
    """
    Generate a prompt template for retrieving specific entity properties.
    
    Returns:
        MCP prompt definition
    """
    return {
        "name": "get_entity_property",
        "description": "Retrieve a specific property value from an entity in the HoxCore registry",
        "arguments": [
            {
                "name": "identifier",
                "description": "The ID or UID of the entity",
                "required": True
            },
            {
                "name": "property",
                "description": "Property name (e.g., title, status, tags, repositories, all)",
                "required": True
            },
            {
                "name": "type",
                "description": "Entity type (program, project, mission, action). Optional if identifier is unique.",
                "required": False
            },
            {
                "name": "index",
                "description": "For list properties, get item at specific index",
                "required": False
            },
            {
                "name": "key",
                "description": "For complex properties, filter by key:value (e.g., name:github)",
                "required": False
            }
        ]
    }


def analyze_registry_prompt() -> Dict[str, Any]:
    """
    Generate a prompt template for analyzing registry structure and relationships.
    
    Returns:
        MCP prompt definition
    """
    return {
        "name": "analyze_registry",
        "description": "Analyze the HoxCore registry structure, relationships, and statistics",
        "arguments": [
            {
                "name": "include_hierarchy",
                "description": "Include parent-child relationships in analysis",
                "required": False,
                "default": True
            },
            {
                "name": "include_stats",
                "description": "Include statistical information (counts, status distribution)",
                "required": False,
                "default": True
            },
            {
                "name": "include_integrations",
                "description": "Include information about external integrations",
                "required": False,
                "default": False
            }
        ]
    }


def get_related_entities_prompt() -> Dict[str, Any]:
    """
    Generate a prompt template for finding related entities.
    
    Returns:
        MCP prompt definition
    """
    return {
        "name": "get_related_entities",
        "description": "Find entities related to a specific entity (parent, children, related)",
        "arguments": [
            {
                "name": "identifier",
                "description": "The ID or UID of the entity",
                "required": True
            },
            {
                "name": "relationship_type",
                "description": "Type of relationship (parent, children, related, all)",
                "required": False,
                "default": "all"
            },
            {
                "name": "recursive",
                "description": "Include relationships recursively (e.g., children of children)",
                "required": False,
                "default": False
            }
        ]
    }


def query_by_date_prompt() -> Dict[str, Any]:
    """
    Generate a prompt template for date-based queries.
    
    Returns:
        MCP prompt definition
    """
    return {
        "name": "query_by_date",
        "description": "Query entities based on date ranges (start_date, due_date, completion_date)",
        "arguments": [
            {
                "name": "date_field",
                "description": "Date field to query (start_date, due_date, completion_date)",
                "required": True
            },
            {
                "name": "before",
                "description": "Filter by dates before YYYY-MM-DD",
                "required": False
            },
            {
                "name": "after",
                "description": "Filter by dates after YYYY-MM-DD",
                "required": False
            },
            {
                "name": "type",
                "description": "Filter by entity type (program, project, mission, action, all)",
                "required": False,
                "default": "all"
            }
        ]
    }


def get_all_prompts() -> List[Dict[str, Any]]:
    """
    Get all available prompt templates.
    
    Returns:
        List of all MCP prompt definitions
    """
    return [
        get_entity_prompt(),
        search_entities_prompt(),
        list_entities_prompt(),
        get_entity_property_prompt(),
        analyze_registry_prompt(),
        get_related_entities_prompt(),
        query_by_date_prompt(),
    ]


def get_prompt_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific prompt template by name.
    
    Args:
        name: Name of the prompt
        
    Returns:
        Prompt definition or None if not found
    """
    prompt_map = {
        "get_entity": get_entity_prompt,
        "search_entities": search_entities_prompt,
        "list_entities": list_entities_prompt,
        "get_entity_property": get_entity_property_prompt,
        "analyze_registry": analyze_registry_prompt,
        "get_related_entities": get_related_entities_prompt,
        "query_by_date": query_by_date_prompt,
    }
    
    prompt_func = prompt_map.get(name)
    return prompt_func() if prompt_func else None


def format_prompt_for_llm(prompt: Dict[str, Any]) -> str:
    """
    Format a prompt definition into a human-readable string for LLM consumption.
    
    Args:
        prompt: Prompt definition dictionary
        
    Returns:
        Formatted prompt string
    """
    lines = [
        f"# {prompt['name']}",
        "",
        prompt['description'],
        "",
        "## Arguments:",
        ""
    ]
    
    for arg in prompt.get('arguments', []):
        required = "Required" if arg.get('required', False) else "Optional"
        default = f" (default: {arg['default']})" if 'default' in arg else ""
        lines.append(f"- **{arg['name']}** ({required}){default}")
        lines.append(f"  {arg['description']}")
        lines.append("")
    
    return "\n".join(lines)


def get_prompts_documentation() -> str:
    """
    Generate complete documentation for all available prompts.
    
    Returns:
        Formatted documentation string
    """
    doc_lines = [
        "# HoxCore MCP Prompts Documentation",
        "",
        "This document describes all available prompts for interacting with HoxCore registries through MCP.",
        "",
        "---",
        ""
    ]
    
    for prompt in get_all_prompts():
        doc_lines.append(format_prompt_for_llm(prompt))
        doc_lines.append("---")
        doc_lines.append("")
    
    return "\n".join(doc_lines)