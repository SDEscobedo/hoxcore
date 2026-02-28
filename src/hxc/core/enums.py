# src/hxc/core/enums.py
"""
Core enumerations for HXC entity types and statuses
"""
from enum import Enum


class EntityType(Enum):
    """Valid entity types in the registry"""
    PROGRAM = "program"
    PROJECT = "project"
    MISSION = "mission"
    ACTION = "action"
    
    @classmethod
    def values(cls):
        """Get list of all valid entity type values"""
        return [member.value for member in cls]
    
    @classmethod
    def from_string(cls, value: str):
        """
        Convert string to EntityType enum
        
        Args:
            value: String representation of entity type
            
        Returns:
            EntityType enum member
            
        Raises:
            ValueError: If value is not a valid entity type
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = ", ".join(cls.values())
            raise ValueError(f"Invalid entity type '{value}'. Valid types: {valid_values}")
    
    def get_folder_name(self) -> str:
        """Get the folder name for this entity type"""
        folder_map = {
            EntityType.PROGRAM: "programs",
            EntityType.PROJECT: "projects",
            EntityType.MISSION: "missions",
            EntityType.ACTION: "actions"
        }
        return folder_map[self]
    
    def get_file_prefix(self) -> str:
        """Get the file prefix for this entity type"""
        prefix_map = {
            EntityType.PROGRAM: "prog",
            EntityType.PROJECT: "proj",
            EntityType.MISSION: "miss",
            EntityType.ACTION: "act"
        }
        return prefix_map[self]


class EntityStatus(Enum):
    """Valid status values for entities"""
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on-hold"
    CANCELLED = "cancelled"
    PLANNED = "planned"
    
    @classmethod
    def values(cls):
        """Get list of all valid status values"""
        return [member.value for member in cls]
    
    @classmethod
    def from_string(cls, value: str):
        """
        Convert string to EntityStatus enum
        
        Args:
            value: String representation of status
            
        Returns:
            EntityStatus enum member
            
        Raises:
            ValueError: If value is not a valid status
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = ", ".join(cls.values())
            raise ValueError(f"Invalid status '{value}'. Valid statuses: {valid_values}")


class OutputFormat(Enum):
    """Valid output formats for display commands"""
    TABLE = "table"
    YAML = "yaml"
    JSON = "json"
    ID = "id"
    PRETTY = "pretty"
    
    @classmethod
    def values(cls):
        """Get list of all valid output format values"""
        return [member.value for member in cls]
    
    @classmethod
    def from_string(cls, value: str):
        """
        Convert string to OutputFormat enum
        
        Args:
            value: String representation of output format
            
        Returns:
            OutputFormat enum member
            
        Raises:
            ValueError: If value is not a valid output format
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = ", ".join(cls.values())
            raise ValueError(f"Invalid output format '{value}'. Valid formats: {valid_values}")


class SortField(Enum):
    """Valid sort fields for list command"""
    TITLE = "title"
    ID = "id"
    DUE_DATE = "due_date"
    STATUS = "status"
    CREATED = "created"
    MODIFIED = "modified"
    
    @classmethod
    def values(cls):
        """Get list of all valid sort field values"""
        return [member.value for member in cls]
    
    @classmethod
    def from_string(cls, value: str):
        """
        Convert string to SortField enum
        
        Args:
            value: String representation of sort field
            
        Returns:
            SortField enum member
            
        Raises:
            ValueError: If value is not a valid sort field
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = ", ".join(cls.values())
            raise ValueError(f"Invalid sort field '{value}'. Valid fields: {valid_values}")