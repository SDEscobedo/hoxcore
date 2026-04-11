"""
List Operation for HoxCore Registry.

This module provides the shared list operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Entity loading with optional file metadata
- Unified filtering logic (status, tags, category, parent, ID, query, date ranges)
- Unified sorting logic with support for file metadata fields
- Path security enforcement
"""
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import yaml

from hxc.core.enums import EntityType, EntityStatus, SortField
from hxc.utils.path_security import resolve_safe_path, PathSecurityError


class ListOperationError(Exception):
    """Base exception for list operation errors"""
    pass


class ListOperation:
    """
    Shared list operation for CLI and MCP interfaces.
    
    This class provides the core entity listing logic including:
    - Entity loading with optional file metadata
    - Unified filtering (status, tags, category, parent, ID, query, date ranges)
    - Unified sorting with support for created/modified timestamps
    - Path security enforcement
    """
    
    def __init__(self, registry_path: str):
        """
        Initialize the list operation.
        
        Args:
            registry_path: Path to the registry root directory
        """
        self.registry_path = registry_path
    
    def load_entities(
        self,
        entity_type: EntityType,
        include_file_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Load all entities of a specific type from the registry.
        
        Args:
            entity_type: The type of entities to load
            include_file_metadata: Whether to include file metadata (_file field)
            
        Returns:
            List of entity data dictionaries
            
        Raises:
            PathSecurityError: If path validation fails
        """
        entities: List[Dict[str, Any]] = []
        
        folder_name = entity_type.get_folder_name()
        file_prefix = entity_type.get_file_prefix() + "-"
        
        try:
            type_dir = resolve_safe_path(self.registry_path, folder_name)
        except PathSecurityError:
            return entities
        
        if not type_dir.exists():
            return entities
        
        for file_path in type_dir.glob(f"{file_prefix}*.yml"):
            try:
                secure_file_path = resolve_safe_path(self.registry_path, file_path)
                
                with open(secure_file_path, 'r') as f:
                    entity_data = yaml.safe_load(f)
                
                if not entity_data or not isinstance(entity_data, dict):
                    continue
                
                if include_file_metadata:
                    file_stat = secure_file_path.stat()
                    entity_data['_file'] = {
                        'path': str(secure_file_path),
                        'name': secure_file_path.name,
                        'created': datetime.datetime.fromtimestamp(
                            file_stat.st_ctime
                        ).strftime('%Y-%m-%d'),
                        'modified': datetime.datetime.fromtimestamp(
                            file_stat.st_mtime
                        ).strftime('%Y-%m-%d'),
                    }
                
                entities.append(entity_data)
                
            except PathSecurityError:
                continue
            except Exception:
                continue
        
        return entities
    
    def filter_entities(
        self,
        entities: List[Dict[str, Any]],
        *,
        status: Optional[EntityStatus] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        parent: Optional[str] = None,
        identifier: Optional[str] = None,
        query: Optional[str] = None,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter entities based on specified criteria.
        
        All filters use AND logic - an entity must match all specified filters.
        
        Args:
            entities: List of entity dictionaries to filter
            status: Filter by status (exact match)
            tags: Filter by tags (entity must have ALL specified tags)
            category: Filter by category (exact match)
            parent: Filter by parent ID (exact match)
            identifier: Filter by ID or UID (exact match)
            query: Text search in title and description (case-insensitive)
            due_before: Filter by due date before YYYY-MM-DD (inclusive)
            due_after: Filter by due date after YYYY-MM-DD (inclusive)
            
        Returns:
            Filtered list of entity dictionaries
        """
        filtered: List[Dict[str, Any]] = []
        
        for entity in entities:
            # Filter by status
            if status is not None:
                entity_status = entity.get("status")
                if entity_status != status.value:
                    continue
            
            # Filter by tags (AND logic - must have ALL specified tags)
            if tags:
                entity_tags = entity.get("tags", [])
                if not all(tag in entity_tags for tag in tags):
                    continue
            
            # Filter by category (exact match)
            if category and entity.get("category") != category:
                continue
            
            # Filter by parent (exact match)
            if parent and entity.get("parent") != parent:
                continue
            
            # Filter by ID or UID (exact match)
            if identifier:
                entity_id = entity.get("id", "")
                entity_uid = entity.get("uid", "")
                if identifier != entity_id and identifier != entity_uid:
                    continue
            
            # Filter by query (case-insensitive search in title and description)
            if query:
                query_lower = query.lower()
                title = entity.get("title", "").lower()
                description = entity.get("description", "").lower()
                if query_lower not in title and query_lower not in description:
                    continue
            
            # Filter by due date range
            if due_before:
                due_date = entity.get("due_date")
                if due_date and due_date > due_before:
                    continue
            
            if due_after:
                due_date = entity.get("due_date")
                if not due_date or due_date < due_after:
                    continue
            
            filtered.append(entity)
        
        return filtered
    
    def sort_entities(
        self,
        entities: List[Dict[str, Any]],
        sort_field: SortField,
        descending: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Sort entities by specified field.
        
        Args:
            entities: List of entity dictionaries to sort
            sort_field: Field to sort by
            descending: Sort in descending order
            
        Returns:
            Sorted list of entity dictionaries
        """
        if sort_field == SortField.CREATED:
            return sorted(
                entities,
                key=lambda x: x.get("_file", {}).get("created", ""),
                reverse=descending
            )
        elif sort_field == SortField.MODIFIED:
            return sorted(
                entities,
                key=lambda x: x.get("_file", {}).get("modified", ""),
                reverse=descending
            )
        else:
            return sorted(
                entities,
                key=lambda x: x.get(sort_field.value, "") or "",
                reverse=descending
            )
    
    def list_entities(
        self,
        entity_types: Optional[List[EntityType]] = None,
        *,
        status: Optional[EntityStatus] = None,
        tags: Optional[List[str]] = None,
        category: Optional[str] = None,
        parent: Optional[str] = None,
        identifier: Optional[str] = None,
        query: Optional[str] = None,
        due_before: Optional[str] = None,
        due_after: Optional[str] = None,
        sort_field: SortField = SortField.TITLE,
        descending: bool = False,
        max_items: int = 0,
        include_file_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        List entities with filtering, sorting, and pagination.
        
        This is the main entry point for entity listing, handling:
        - Loading entities from multiple types
        - Applying all filters
        - Sorting results
        - Limiting results
        
        Args:
            entity_types: Types of entities to list (None or empty = all types)
            status: Filter by status
            tags: Filter by tags (AND logic)
            category: Filter by category
            parent: Filter by parent ID
            identifier: Filter by ID or UID
            query: Text search in title/description
            due_before: Filter by due date before YYYY-MM-DD
            due_after: Filter by due date after YYYY-MM-DD
            sort_field: Field to sort by (default: title)
            descending: Sort in descending order (default: False)
            max_items: Maximum number of items to return (0 = all)
            include_file_metadata: Include file metadata in results
            
        Returns:
            Dictionary containing:
            - success: bool
            - entities: list of entity dictionaries
            - count: number of entities returned
            - filters: applied filter values
            - sort: sort configuration
        """
        # Default to all entity types if not specified
        if not entity_types:
            entity_types = list(EntityType)
        
        # Load entities from all specified types
        all_entities: List[Dict[str, Any]] = []
        for entity_type in entity_types:
            entities = self.load_entities(entity_type, include_file_metadata)
            all_entities.extend(entities)
        
        # Apply filters
        filtered_entities = self.filter_entities(
            all_entities,
            status=status,
            tags=tags,
            category=category,
            parent=parent,
            identifier=identifier,
            query=query,
            due_before=due_before,
            due_after=due_after,
        )
        
        # Sort entities
        sorted_entities = self.sort_entities(
            filtered_entities,
            sort_field,
            descending
        )
        
        # Apply max items limit
        if max_items > 0:
            sorted_entities = sorted_entities[:max_items]
        
        # Build filter metadata for response
        filters = {
            "types": [et.value for et in entity_types],
            "status": status.value if status else None,
            "tags": tags,
            "category": category,
            "parent": parent,
            "identifier": identifier,
            "query": query,
            "due_before": due_before,
            "due_after": due_after,
        }
        
        return {
            "success": True,
            "entities": sorted_entities,
            "count": len(sorted_entities),
            "filters": filters,
            "sort": {
                "field": sort_field.value,
                "descending": descending,
            },
        }
    
    def get_entity_by_identifier(
        self,
        identifier: str,
        entity_type: Optional[EntityType] = None,
        include_file_metadata: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single entity by ID or UID.
        
        Args:
            identifier: ID or UID of the entity
            entity_type: Optional type filter
            include_file_metadata: Include file metadata in result
            
        Returns:
            Entity dictionary if found, None otherwise
        """
        entity_types = [entity_type] if entity_type else list(EntityType)
        
        for et in entity_types:
            entities = self.load_entities(et, include_file_metadata)
            for entity in entities:
                if entity.get("id") == identifier or entity.get("uid") == identifier:
                    return entity
        
        return None
    
    @staticmethod
    def clean_entities_for_output(
        entities: List[Dict[str, Any]],
        remove_file_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Clean entities for output by removing internal metadata.
        
        Args:
            entities: List of entity dictionaries
            remove_file_metadata: Whether to remove _file metadata
            
        Returns:
            Cleaned list of entity dictionaries
        """
        if not remove_file_metadata:
            return entities
        
        cleaned: List[Dict[str, Any]] = []
        for entity in entities:
            clean_entity = {
                k: v for k, v in entity.items() 
                if not k.startswith('_')
            }
            cleaned.append(clean_entity)
        
        return cleaned