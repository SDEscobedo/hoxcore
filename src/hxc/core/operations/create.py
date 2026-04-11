"""
Create Operation for HoxCore Registry.

This module provides the shared create operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Entity creation with git integration
- ID uniqueness validation
- Path security enforcement
- Structured commit message generation
"""
import uuid
import datetime
import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import yaml

from hxc.core.enums import EntityType, EntityStatus
from hxc.utils.path_security import get_safe_entity_path, resolve_safe_path, PathSecurityError
from hxc.utils.git import commit_entity_change


MAX_ID_LENGTH = 255
_ID_ALLOWED_RE = re.compile(r"[^a-z0-9_]+")
_ID_SPACES_RE = re.compile(r"\s+")
_UNDERSCORE_RE = re.compile(r"_+")


class CreateOperationError(Exception):
    """Base exception for create operation errors"""
    pass


class DuplicateIdError(CreateOperationError):
    """Raised when attempting to create an entity with a duplicate ID"""
    pass


class CreateOperation:
    """
    Shared create operation for CLI and MCP interfaces.
    
    This class provides the core entity creation logic including:
    - UID generation
    - ID uniqueness validation
    - Entity data construction
    - File writing with path security
    - Optional git integration
    """
    
    def __init__(self, registry_path: str):
        """
        Initialize the create operation.
        
        Args:
            registry_path: Path to the registry root directory
        """
        self.registry_path = registry_path
    
    @staticmethod
    def generate_uid() -> str:
        """
        Generate a unique identifier for an entity.
        
        Returns:
            8-character unique identifier string
        """
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def _transliterate_to_ascii(text: str) -> str:
        """
        Convert non-ASCII characters to their closest ASCII representation.
        
        Args:
            text: Input text with potentially non-ASCII characters
            
        Returns:
            ASCII-only string
        """
        normalized = unicodedata.normalize("NFKD", text)
        return normalized.encode("ascii", "ignore").decode("ascii")
    
    @classmethod
    def title_to_id(cls, title: str, entity_type: str) -> str:
        """
        Deterministically generate a human-readable, filesystem/URL-safe base ID from a title.

        Rules:
        - Allowed characters: [a-z0-9_]
        - Spaces/special characters become underscores
        - Consecutive underscores collapse; leading/trailing underscores removed
        - Non-ASCII is transliterated/removed via NFKD -> ascii ignore
        - Result length is capped to 255 chars
        
        Args:
            title: The entity title
            entity_type: The entity type (used as fallback if title is empty)
            
        Returns:
            Generated ID string
        """
        raw_title = title if title is not None else ""
        canonical = cls._transliterate_to_ascii(raw_title.strip()).lower()

        slug = _ID_SPACES_RE.sub("_", canonical)
        slug = _ID_ALLOWED_RE.sub("_", slug)
        slug = _UNDERSCORE_RE.sub("_", slug).strip("_")

        if not slug:
            slug = entity_type

        return slug[:MAX_ID_LENGTH]
    
    def load_existing_ids(self, entity_type: EntityType) -> Set[str]:
        """
        Load all `id` fields for existing entities of a given type.
        
        Args:
            entity_type: The entity type to load IDs for
            
        Returns:
            Set of existing IDs (strings). Missing/invalid ids are ignored.
        """
        ids: Set[str] = set()
        try:
            type_dir = resolve_safe_path(self.registry_path, entity_type.get_folder_name())
        except PathSecurityError:
            return ids
            
        if not type_dir.exists():
            return ids

        file_prefix = entity_type.get_file_prefix()
        for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
            try:
                secure_file_path = resolve_safe_path(self.registry_path, file_path)
                with open(secure_file_path, "r") as f:
                    data = yaml.safe_load(f)
                if isinstance(data, dict):
                    existing_id = data.get("id")
                    if isinstance(existing_id, str):
                        ids.add(existing_id)
            except PathSecurityError:
                continue
            except Exception:
                continue

        return ids
    
    def validate_id_uniqueness(
        self,
        entity_type: EntityType,
        entity_id: str,
        existing_ids: Optional[Set[str]] = None
    ) -> bool:
        """
        Validate that an ID is unique within the entity type.
        
        Args:
            entity_type: The entity type to check against
            entity_id: The ID to validate
            existing_ids: Optional pre-loaded set of existing IDs
            
        Returns:
            True if ID is unique, False if it already exists
        """
        if existing_ids is None:
            existing_ids = self.load_existing_ids(entity_type)
        return entity_id not in existing_ids
    
    @classmethod
    def _truncate_base_for_suffix(cls, base_id: str, suffix_len: int) -> str:
        """
        Truncate base_id to ensure (base_id + suffix) stays within MAX_ID_LENGTH.
        
        Args:
            base_id: The base ID to potentially truncate
            suffix_len: Length of the suffix to be added
            
        Returns:
            Truncated base ID
        """
        max_base_len = MAX_ID_LENGTH - suffix_len
        return base_id[:max_base_len]
    
    @classmethod
    def resolve_auto_id(
        cls,
        existing_ids: Set[str],
        base_id: str,
        uid: str
    ) -> Optional[str]:
        """
        Resolve a unique ID using collision avoidance strategy.
        
        Strategy:
        1. base_id (no suffix) if unique
        2. base_id + '_' + first 3 chars of uid
        3. if still not unique: increase the chars of uid to append
        4. if still not unique: return None
        
        Args:
            existing_ids: Set of existing IDs
            base_id: The base ID to try
            uid: The entity UID for suffix generation
            
        Returns:
            Unique ID string, or None if no unique ID could be generated
        """
        base_id = base_id or "untitled"

        if base_id not in existing_ids:
            return base_id

        for i in range(3, len(uid) + 1):
            partial_uid = uid[:i]
            suffix = f"_{partial_uid}"
            truncated_base = cls._truncate_base_for_suffix(base_id, len(suffix))
            candidate = f"{truncated_base}{suffix}"

            if candidate not in existing_ids:
                return candidate

        return None
    
    def build_entity_data(
        self,
        entity_type: EntityType,
        title: str,
        uid: str,
        *,
        entity_id: Optional[str] = None,
        description: Optional[str] = None,
        status: EntityStatus = EntityStatus.ACTIVE,
        start_date: Optional[str] = None,
        due_date: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent: Optional[str] = None,
        template: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Build entity data dictionary from parameters.
        
        Args:
            entity_type: Type of entity
            title: Entity title
            uid: Unique identifier
            entity_id: Optional custom ID
            description: Optional description
            status: Entity status (default: active)
            start_date: Optional start date (default: today)
            due_date: Optional due date
            category: Optional category path
            tags: Optional list of tags
            parent: Optional parent entity ID/UID
            template: Optional template reference
            
        Returns:
            Entity data dictionary ready for YAML serialization
        """
        today = datetime.date.today().isoformat()
        
        entity: Dict[str, Any] = {
            "type": entity_type.value,
            "uid": uid,
            "title": title,
            "status": status.value,
            "start_date": start_date or today,
        }
        
        if entity_id:
            entity["id"] = entity_id
        else:
            entity["id"] = self.title_to_id(title, entity_type.value)
        
        if description:
            entity["description"] = description
            
        if due_date:
            entity["due_date"] = due_date
            
        if category:
            entity["category"] = category
            
        if tags:
            entity["tags"] = tags
            
        if parent:
            entity["parent"] = parent
            
        if template:
            entity["template"] = template
            
        entity["children"] = []
        entity["related"] = []
        entity["repositories"] = []
        entity["storage"] = []
        entity["databases"] = []
        entity["tools"] = []
        entity["models"] = []
        entity["knowledge_bases"] = []
        
        return entity
    
    def write_entity_file(
        self,
        entity_type: EntityType,
        uid: str,
        entity_data: Dict[str, Any]
    ) -> Path:
        """
        Write entity data to a YAML file.
        
        Args:
            entity_type: Type of entity
            uid: Unique identifier
            entity_data: Entity data dictionary
            
        Returns:
            Path to the created file
            
        Raises:
            PathSecurityError: If path validation fails
            ValueError: If entity type is invalid
            IOError: If file writing fails
        """
        file_prefix = entity_type.get_file_prefix()
        file_name = f"{file_prefix}-{uid}.yml"
        
        file_path = get_safe_entity_path(self.registry_path, entity_type.value, file_name)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            yaml.dump(entity_data, f, default_flow_style=False, sort_keys=False)
        
        return file_path
    
    def create_entity(
        self,
        entity_type: EntityType,
        title: str,
        *,
        entity_id: Optional[str] = None,
        description: Optional[str] = None,
        status: EntityStatus = EntityStatus.ACTIVE,
        start_date: Optional[str] = None,
        due_date: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        parent: Optional[str] = None,
        template: Optional[str] = None,
        use_git: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new entity in the registry.
        
        This is the main entry point for entity creation, handling:
        - UID generation
        - ID uniqueness validation
        - Entity data construction
        - File writing with path security
        - Optional git integration
        
        Args:
            entity_type: Type of entity to create
            title: Entity title
            entity_id: Optional custom ID (validated for uniqueness)
            description: Optional description
            status: Entity status (default: active)
            start_date: Optional start date (default: today)
            due_date: Optional due date
            category: Optional category path
            tags: Optional list of tags
            parent: Optional parent entity ID/UID
            template: Optional template reference
            use_git: Whether to commit the change to git (default: True)
            
        Returns:
            Dictionary containing:
            - success: bool
            - uid: str (on success)
            - id: str (on success)
            - file_path: str (on success)
            - entity: dict (on success)
            - git_committed: bool (on success, if use_git=True)
            
        Raises:
            DuplicateIdError: If entity_id is provided and already exists
            CreateOperationError: If a unique ID cannot be generated
            PathSecurityError: If path validation fails
            ValueError: If entity type is invalid
        """
        uid = self.generate_uid()
        
        existing_ids = self.load_existing_ids(entity_type)
        
        if entity_id is not None:
            if entity_id in existing_ids:
                raise DuplicateIdError(
                    f"{entity_type.value} with id '{entity_id}' already exists in this registry"
                )
            final_id = entity_id
        else:
            base_id = self.title_to_id(title, entity_type.value)
            final_id = self.resolve_auto_id(existing_ids, base_id, uid)
            if final_id is None:
                raise CreateOperationError(
                    f"Could not generate a unique {entity_type.value} id for title '{title}'"
                )
        
        entity_data = self.build_entity_data(
            entity_type=entity_type,
            title=title,
            uid=uid,
            entity_id=final_id,
            description=description,
            status=status,
            start_date=start_date,
            due_date=due_date,
            category=category,
            tags=tags,
            parent=parent,
            template=template,
        )
        
        file_path = self.write_entity_file(entity_type, uid, entity_data)
        
        git_committed = False
        if use_git:
            git_committed = commit_entity_change(
                registry_path=self.registry_path,
                file_path=file_path,
                action="Create",
                entity_data=entity_data,
            )
        
        return {
            "success": True,
            "uid": uid,
            "id": final_id,
            "file_path": str(file_path),
            "entity": entity_data,
            "git_committed": git_committed,
        }