"""
Create command implementation for generating new projects, programs, actions, or missions.
"""
import os
import uuid
import yaml
import datetime
from pathlib import Path
import argparse
from typing import Dict, Any, List, Optional
import re
import unicodedata
import random
import string

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import get_safe_entity_path, resolve_safe_path, PathSecurityError
from hxc.utils.git import commit_entity_change, print_commit_result
from hxc.core.enums import EntityType, EntityStatus


MAX_ID_LENGTH = 255
_ID_ALLOWED_RE = re.compile(r"[^a-z0-9_]+")
_ID_SPACES_RE = re.compile(r"\s+")
_UNDERSCORE_RE = re.compile(r"_+")


def _transliterate_to_ascii(text: str) -> str:
    """
    Convert non-ASCII characters to their closest ASCII representation (or drop them).
    """
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def title_to_id(title: str, entity_type:str) -> str:
    """
    Deterministically generate a human-readable, filesystem/URL-safe base ID from a title.

    Rules:
    - Allowed characters: [a-z0-9_]
    - Spaces/special characters become underscores
    - Consecutive underscores collapse; leading/trailing underscores removed
    - Non-ASCII is transliterated/removal via NFKD -> ascii ignore
    - Result length is capped to 255 chars
    """
    raw_title = title if title is not None else ""
    canonical = _transliterate_to_ascii(raw_title.strip()).lower()

    # Human-readable slug base: map spaces/special chars to underscores, keep [a-z0-9_]
    slug = _ID_SPACES_RE.sub("_", canonical)
    slug = _ID_ALLOWED_RE.sub("_", slug)
    slug = _UNDERSCORE_RE.sub("_", slug).strip("_")

    if not slug:
        slug = entity_type

    return slug[:MAX_ID_LENGTH]

@register_command
class CreateCommand(BaseCommand):
    """Create a new entity (program, project, action, mission) in the registry"""
    
    name = "create"
    help = "Create a new program, project, action, or mission"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        
        # Required arguments
        parser.add_argument('type', choices=EntityType.values(),
                          help='Type of entity to create')
        parser.add_argument('title', 
                          help='Title of the entity')
        
        # Optional arguments
        parser.add_argument('--id', dest='custom_id',
                          help='Custom ID for the entity (e.g., P-001)')
        parser.add_argument('--description', '-d',
                          help='Description of the entity')
        parser.add_argument('--status', default='active',
                          choices=EntityStatus.values(),
                          help='Status of the entity (default: active)')
        parser.add_argument('--start-date',
                          help='Start date in YYYY-MM-DD format (default: today)')
        parser.add_argument('--due-date',
                          help='Due date in YYYY-MM-DD format')
        parser.add_argument('--category',
                          help='Category path (e.g., software.dev/cli-tool)')
        parser.add_argument('--tags', nargs='+',
                          help='List of tags (space separated)')
        parser.add_argument('--parent',
                          help='Parent entity UID or ID')
        parser.add_argument('--template',
                          help='Template to use (e.g., software.dev/cli-tool.default)')
        parser.add_argument('--registry',
                          help='Path to registry (defaults to current or configured registry)')
        parser.add_argument('--no-commit',
                          action='store_true',
                          help='Skip automatic git commit after creating the entity')
        
        return parser
    
    @classmethod
    def execute(cls, args):
        try:
            # Convert string arguments to enums early
            entity_type = EntityType.from_string(args.type)
            entity_status = EntityStatus.from_string(args.status)
        except ValueError as e:
            print(f"❌ Invalid argument: {e}")
            return 1
        
        # Get registry path
        registry_path = cls._get_registry_path(args.registry)
        if not registry_path:
            print("❌ No registry found. Please specify with --registry or initialize one with 'hxc init'")
            return 1

        # Load all existing IDs for this entity type once.
        # This avoids re-opening multiple YAML files during suffix resolution.
        existing_ids = cls._load_existing_ids(registry_path, entity_type)

        # Generate entity data based on arguments (includes uid and base id).
        entity_data = cls._build_entity_data(args, entity_type, entity_status)

        # Resolve ID uniqueness.
        # - If --id is provided: preserve it, but fail if it already exists.
        # - If --id is omitted: try base id; if taken use uid3; if still taken use random letter.
        if args.custom_id:
            candidate = entity_data.get("id")
            if isinstance(candidate, str) and candidate in existing_ids:
                print(
                    f"❌ {entity_type.value} with id '{candidate}' already exists in this registry"
                )
                return 1
        else:
            base_id = entity_data.get("id", "")
            uid = entity_data.get("uid", "")
            resolved = cls._resolve_auto_id(existing_ids, base_id, uid)
            if not resolved:
                print(
                    f"❌ Could not generate a unique {entity_type.value} id for title '{entity_data.get('title', '')}'"
                )
                return 1
            entity_data["id"] = resolved

        # Determine file name
        uid = entity_data.get('uid', str(uuid.uuid4())[:8])
        file_prefix = entity_type.get_file_prefix()
        file_name = f"{file_prefix}-{uid}.yml"
        
        # Get safe path using path security utilities
        try:
            file_path = get_safe_entity_path(registry_path, entity_type.value, file_name)
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except ValueError as e:
            print(f"❌ Invalid entity type: {e}")
            return 1
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to file
        try:
            with open(file_path, 'w') as f:
                yaml.dump(entity_data, f, default_flow_style=False, sort_keys=False)
            
            print(f"✅ Created {entity_type.value} '{entity_data['title']}' at {file_path}")
        except Exception as e:
            print(f"❌ Error creating {entity_type.value}: {e}")
            return 1
        
        # Git commit (unless --no-commit is specified)
        no_commit = getattr(args, 'no_commit', False)
        if no_commit:
            print("⚠️  Changes not committed (--no-commit flag used)")
        else:
            result = commit_entity_change(
                registry_path=registry_path,
                file_path=file_path,
                action="Create",
                entity_data=entity_data,
            )
            print_commit_result(result, no_commit_flag=False)
        
        return 0
    
    @classmethod
    def _get_registry_path(cls, specified_path: Optional[str] = None) -> Optional[str]:
        """Get registry path from specified path, config, or current directory"""
        if specified_path:
            return specified_path
            
        # Try from config
        registry_path = RegistryCommand.get_registry_path()
        if registry_path:
            return registry_path
            
        # Try to find in current directory or parent directories
        return get_project_root()
    
    @classmethod
    def _build_entity_data(cls, args, entity_type: EntityType, entity_status: EntityStatus) -> Dict[str, Any]:
        """Build entity data dictionary from arguments"""
        # Generate or use provided UID
        uid = str(uuid.uuid4())[:8]  # Use first 8 chars of a UUID
        
        # Set default dates
        today = datetime.date.today().isoformat()
        
        # Basic entity data
        entity = {
            # Basic Metadata
            "type": entity_type.value,
            "uid": uid,
            "title": args.title,
            
            # Status & Lifecycle 
            "status": entity_status.value,
            "start_date": args.start_date or today,
        }
        
        # Add optional fields if provided
        if args.custom_id:
            entity["id"] = args.custom_id
        else:
            entity["id"] = title_to_id(args.title, entity_type.value)
        
        if args.description:
            entity["description"] = args.description
            
        if args.due_date:
            entity["due_date"] = args.due_date
            
        if args.category:
            entity["category"] = args.category
            
        if args.tags:
            entity["tags"] = args.tags
            
        if args.parent:
            entity["parent"] = args.parent
            
        if args.template:
            entity["template"] = args.template
            
        # Add default empty sections for structure
        entity["children"] = []
        entity["related"] = []
        entity["repositories"] = []
        entity["storage"] = []
        entity["databases"] = []
        entity["tools"] = []
        entity["models"] = []
        entity["knowledge_bases"] = []
        
        return entity

    @classmethod
    def _load_existing_ids(cls, registry_path: str, entity_type: EntityType) -> set:
        """
        Load all `id` fields for existing entities of this type into a set.

        Returns:
            Set of existing IDs (strings). Missing/invalid ids are ignored.
        """
        ids = set()
        type_dir = resolve_safe_path(registry_path, entity_type.get_folder_name())
        if not type_dir.exists():
            return ids

        file_prefix = entity_type.get_file_prefix()
        for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
            try:
                secure_file_path = resolve_safe_path(registry_path, file_path)
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

    @classmethod
    def _truncate_base_for_suffix(cls, base_id: str, suffix_len: int) -> str:
        """
        Truncate base_id to ensure (base_id + suffix) stays within MAX_ID_LENGTH.
        """
        max_base_len = MAX_ID_LENGTH - suffix_len
        return base_id[:max_base_len]

    @classmethod
    def _resolve_auto_id(cls, existing_ids: set, base_id: str, uid: str) -> Optional[str]:
        """
        Resolve a unique ID using the requested collision strategy:
        1. base_id (no suffix) if unique
        2. base_id + '_' + first 3 chars of uid
        3. if still not unique: increase the chars of uid to append
        4. if still not unique: return None (caller prints an error)
        """
        base_id = base_id or "untitled"

        if base_id not in existing_ids:
            return base_id

        for i in range(3, len(uid)):
            partial_uid = uid[:i]
            suffix = f"_{partial_uid}"
            truncated_base = cls._truncate_base_for_suffix(base_id, len(suffix))
            candidate = f"{truncated_base}{suffix}"

            if candidate not in existing_ids:
                return candidate

        return None