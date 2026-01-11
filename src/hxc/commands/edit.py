"""
Edit command implementation for modifying entity properties.
"""
import os
import yaml
import argparse
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError
from hxc.core.enums import EntityType, EntityStatus


@register_command
class EditCommand(BaseCommand):
    """Command for editing entity properties"""
    
    name = "edit"
    help = "Edit properties of a program, project, action, or mission"
    
    # Define editable scalar fields
    SCALAR_FIELDS = {
        'title': str,
        'description': str,
        'status': str,
        'id': str,
        'start_date': str,
        'due_date': str,
        'completion_date': str,
        'duration_estimate': str,
        'category': str,
        'parent': str,
        'template': str,
    }
    
    # Define editable list fields
    LIST_FIELDS = {
        'tags': list,
        'children': list,
        'related': list,
    }
    
    # Define editable complex fields (list of dicts)
    COMPLEX_FIELDS = {
        'repositories': list,
        'storage': list,
        'databases': list,
        'tools': list,
        'models': list,
        'knowledge_bases': list,
    }
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        
        # Required argument: identifier
        parser.add_argument(
            'identifier',
            help='ID or UID of the entity to edit'
        )
        
        # Optional: entity type filter
        parser.add_argument(
            '--type', '-t',
            choices=EntityType.values(),
            help='Entity type (only needed if identifier is ambiguous)'
        )
        
        # Scalar field setters
        parser.add_argument('--set-title', metavar='VALUE', help='Set title')
        parser.add_argument('--set-description', metavar='VALUE', help='Set description')
        parser.add_argument('--set-status', metavar='VALUE', 
                          choices=EntityStatus.values(),
                          help='Set status')
        parser.add_argument('--set-id', metavar='VALUE', help='Set custom ID')
        parser.add_argument('--set-start-date', metavar='YYYY-MM-DD', help='Set start date')
        parser.add_argument('--set-due-date', metavar='YYYY-MM-DD', help='Set due date')
        parser.add_argument('--set-completion-date', metavar='YYYY-MM-DD', help='Set completion date')
        parser.add_argument('--set-duration-estimate', metavar='VALUE', help='Set duration estimate (e.g., 90d, 3w)')
        parser.add_argument('--set-category', metavar='VALUE', help='Set category')
        parser.add_argument('--set-parent', metavar='UID', help='Set parent UID')
        parser.add_argument('--set-template', metavar='VALUE', help='Set template')
        
        # List field operations
        parser.add_argument('--add-tag', metavar='TAG', action='append', help='Add a tag (can be used multiple times)')
        parser.add_argument('--remove-tag', metavar='TAG', action='append', help='Remove a tag (can be used multiple times)')
        parser.add_argument('--set-tags', metavar='TAG', nargs='+', help='Set tags (replaces all existing tags)')
        
        parser.add_argument('--add-child', metavar='UID', action='append', help='Add a child UID')
        parser.add_argument('--remove-child', metavar='UID', action='append', help='Remove a child UID')
        parser.add_argument('--set-children', metavar='UID', nargs='+', help='Set children UIDs (replaces all)')
        
        parser.add_argument('--add-related', metavar='UID', action='append', help='Add a related UID')
        parser.add_argument('--remove-related', metavar='UID', action='append', help='Remove a related UID')
        parser.add_argument('--set-related', metavar='UID', nargs='+', help='Set related UIDs (replaces all)')
        
        # Complex field operations (simplified - add/remove items)
        parser.add_argument('--add-repository', metavar='NAME:URL', help='Add repository (format: name:url)')
        parser.add_argument('--remove-repository', metavar='NAME', help='Remove repository by name')
        
        parser.add_argument('--add-storage', metavar='NAME:PROVIDER:URL', help='Add storage (format: name:provider:url)')
        parser.add_argument('--remove-storage', metavar='NAME', help='Remove storage by name')
        
        parser.add_argument('--add-database', metavar='NAME:TYPE:URL', help='Add database (format: name:type:url)')
        parser.add_argument('--remove-database', metavar='NAME', help='Remove database by name')
        
        parser.add_argument('--add-tool', metavar='NAME:PROVIDER:URL', help='Add tool (format: name:provider:url)')
        parser.add_argument('--remove-tool', metavar='NAME', help='Remove tool by name')
        
        parser.add_argument('--add-model', metavar='ID:PROVIDER:URL', help='Add model (format: id:provider:url)')
        parser.add_argument('--remove-model', metavar='ID', help='Remove model by ID')
        
        parser.add_argument('--add-kb', metavar='ID:URL', help='Add knowledge base (format: id:url)')
        parser.add_argument('--remove-kb', metavar='ID', help='Remove knowledge base by ID')
        
        # Other options
        parser.add_argument(
            '--registry',
            help='Path to registry (defaults to current or configured registry)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually modifying the file'
        )
        
        return parser
    
    @classmethod
    def execute(cls, args):
        try:
            # Convert entity type if provided
            entity_type = None
            if args.type:
                try:
                    entity_type = EntityType.from_string(args.type)
                except ValueError as e:
                    print(f"❌ Invalid argument: {e}")
                    return 1
            
            # Get registry path
            registry_path = cls._get_registry_path(args.registry)
            if not registry_path:
                print("❌ No registry found. Please specify with --registry or initialize one with 'hxc init'")
                return 1
            
            # Find the entity file
            file_path = cls._find_entity_file(registry_path, args.identifier, entity_type)
            if not file_path:
                print(f"❌ No entity found with identifier '{args.identifier}'")
                if entity_type:
                    print(f"   (search limited to type: {entity_type.value})")
                return 1
            
            # Load the entity
            try:
                secure_file_path = resolve_safe_path(registry_path, file_path)
                with open(secure_file_path, 'r') as f:
                    entity_data = yaml.safe_load(f)
            except PathSecurityError as e:
                print(f"❌ Security error: {e}")
                return 1
            except Exception as e:
                print(f"❌ Error loading entity: {e}")
                return 1
            
            if not entity_data or not isinstance(entity_data, dict):
                print(f"❌ Invalid entity data in {file_path}")
                return 1
            
            # Track changes
            changes = []
            original_data = yaml.dump(entity_data, default_flow_style=False, sort_keys=False)
            
            # Apply scalar field edits
            changes.extend(cls._apply_scalar_edits(entity_data, args))
            
            # Apply list field edits
            changes.extend(cls._apply_list_edits(entity_data, args))
            
            # Apply complex field edits
            changes.extend(cls._apply_complex_edits(entity_data, args))
            
            # Check if any changes were made
            if not changes:
                print("⚠️  No changes specified. Use --help to see available options.")
                return 0
            
            # Display changes
            print("📝 Changes to be applied:")
            for change in changes:
                print(f"  • {change}")
            print()
            
            # If dry-run, stop here
            if args.dry_run:
                print("🔍 Dry run - no changes written to file")
                return 0
            
            # Write the updated entity back to file
            try:
                with open(secure_file_path, 'w') as f:
                    yaml.dump(entity_data, f, default_flow_style=False, sort_keys=False)
                
                print(f"✅ Successfully updated entity at {secure_file_path}")
                return 0
            except Exception as e:
                print(f"❌ Error writing changes: {e}")
                return 1
                
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error editing entity: {e}")
            return 1
    
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
    def _find_entity_file(
        cls, 
        registry_path: str, 
        identifier: str, 
        entity_type: Optional[EntityType] = None
    ) -> Optional[Path]:
        """
        Find an entity file by ID or UID
        
        Args:
            registry_path: Root directory of the registry
            identifier: ID or UID to search for
            entity_type: Optional entity type to filter by
            
        Returns:
            Path to the entity file if found, None otherwise
        """
        types_to_search = [entity_type] if entity_type else list(EntityType)
        
        for entity_type_enum in types_to_search:
            folder_name = entity_type_enum.get_folder_name()
            file_prefix = entity_type_enum.get_file_prefix()
            
            try:
                type_dir = resolve_safe_path(registry_path, folder_name)
            except PathSecurityError:
                continue
            
            if not type_dir.exists():
                continue
            
            # First, try to match by filename (UID in filename)
            uid_pattern = f"{file_prefix}-{identifier}.yml"
            for file_path in type_dir.glob(uid_pattern):
                try:
                    secure_file_path = resolve_safe_path(registry_path, file_path)
                    return secure_file_path
                except PathSecurityError:
                    continue
            
            # If no match, search inside files for ID or UID field
            for file_path in type_dir.glob(f"{file_prefix}-*.yml"):
                try:
                    secure_file_path = resolve_safe_path(registry_path, file_path)
                    with open(secure_file_path, 'r') as f:
                        data = yaml.safe_load(f)
                        if data and isinstance(data, dict):
                            if data.get('id') == identifier or data.get('uid') == identifier:
                                return secure_file_path
                except PathSecurityError:
                    continue
                except Exception:
                    continue
        
        return None
    
    @classmethod
    def _apply_scalar_edits(cls, entity_data: Dict[str, Any], args: argparse.Namespace) -> List[str]:
        """Apply scalar field edits to entity data"""
        changes = []
        
        # Map of argument names to field names
        scalar_mappings = {
            'set_title': 'title',
            'set_description': 'description',
            'set_status': 'status',
            'set_id': 'id',
            'set_start_date': 'start_date',
            'set_due_date': 'due_date',
            'set_completion_date': 'completion_date',
            'set_duration_estimate': 'duration_estimate',
            'set_category': 'category',
            'set_parent': 'parent',
            'set_template': 'template',
        }
        
        for arg_name, field_name in scalar_mappings.items():
            value = getattr(args, arg_name, None)
            if value is not None:
                old_value = entity_data.get(field_name, '(not set)')
                entity_data[field_name] = value
                changes.append(f"Set {field_name}: '{old_value}' → '{value}'")
        
        return changes
    
    @classmethod
    def _apply_list_edits(cls, entity_data: Dict[str, Any], args: argparse.Namespace) -> List[str]:
        """Apply list field edits to entity data"""
        changes = []
        
        # Tags operations
        if args.set_tags is not None:
            old_tags = entity_data.get('tags', [])
            entity_data['tags'] = args.set_tags
            changes.append(f"Set tags: {old_tags} → {args.set_tags}")
        else:
            if args.add_tag:
                tags = entity_data.get('tags', [])
                for tag in args.add_tag:
                    if tag not in tags:
                        tags.append(tag)
                        changes.append(f"Added tag: '{tag}'")
                entity_data['tags'] = tags
            
            if args.remove_tag:
                tags = entity_data.get('tags', [])
                for tag in args.remove_tag:
                    if tag in tags:
                        tags.remove(tag)
                        changes.append(f"Removed tag: '{tag}'")
                entity_data['tags'] = tags
        
        # Children operations
        if args.set_children is not None:
            old_children = entity_data.get('children', [])
            entity_data['children'] = args.set_children
            changes.append(f"Set children: {old_children} → {args.set_children}")
        else:
            if args.add_child:
                children = entity_data.get('children', [])
                for child in args.add_child:
                    if child not in children:
                        children.append(child)
                        changes.append(f"Added child: '{child}'")
                entity_data['children'] = children
            
            if args.remove_child:
                children = entity_data.get('children', [])
                for child in args.remove_child:
                    if child in children:
                        children.remove(child)
                        changes.append(f"Removed child: '{child}'")
                entity_data['children'] = children
        
        # Related operations
        if args.set_related is not None:
            old_related = entity_data.get('related', [])
            entity_data['related'] = args.set_related
            changes.append(f"Set related: {old_related} → {args.set_related}")
        else:
            if args.add_related:
                related = entity_data.get('related', [])
                for rel in args.add_related:
                    if rel not in related:
                        related.append(rel)
                        changes.append(f"Added related: '{rel}'")
                entity_data['related'] = related
            
            if args.remove_related:
                related = entity_data.get('related', [])
                for rel in args.remove_related:
                    if rel in related:
                        related.remove(rel)
                        changes.append(f"Removed related: '{rel}'")
                entity_data['related'] = related
        
        return changes
    
    @classmethod
    def _apply_complex_edits(cls, entity_data: Dict[str, Any], args: argparse.Namespace) -> List[str]:
        """Apply complex field edits (lists of dicts) to entity data"""
        changes = []
        
        # Repository operations
        if args.add_repository:
            changes.extend(cls._add_complex_item(
                entity_data, 'repositories', args.add_repository,
                ['name', 'url'], 'repository'
            ))
        if args.remove_repository:
            changes.extend(cls._remove_complex_item(
                entity_data, 'repositories', args.remove_repository, 'name', 'repository'
            ))
        
        # Storage operations
        if args.add_storage:
            changes.extend(cls._add_complex_item(
                entity_data, 'storage', args.add_storage,
                ['name', 'provider', 'url'], 'storage'
            ))
        if args.remove_storage:
            changes.extend(cls._remove_complex_item(
                entity_data, 'storage', args.remove_storage, 'name', 'storage'
            ))
        
        # Database operations
        if args.add_database:
            changes.extend(cls._add_complex_item(
                entity_data, 'databases', args.add_database,
                ['name', 'type', 'url'], 'database'
            ))
        if args.remove_database:
            changes.extend(cls._remove_complex_item(
                entity_data, 'databases', args.remove_database, 'name', 'database'
            ))
        
        # Tool operations
        if args.add_tool:
            changes.extend(cls._add_complex_item(
                entity_data, 'tools', args.add_tool,
                ['name', 'provider', 'url'], 'tool'
            ))
        if args.remove_tool:
            changes.extend(cls._remove_complex_item(
                entity_data, 'tools', args.remove_tool, 'name', 'tool'
            ))
        
        # Model operations
        if args.add_model:
            changes.extend(cls._add_complex_item(
                entity_data, 'models', args.add_model,
                ['id', 'provider', 'url'], 'model'
            ))
        if args.remove_model:
            changes.extend(cls._remove_complex_item(
                entity_data, 'models', args.remove_model, 'id', 'model'
            ))
        
        # Knowledge base operations
        if args.add_kb:
            changes.extend(cls._add_complex_item(
                entity_data, 'knowledge_bases', args.add_kb,
                ['id', 'url'], 'knowledge base'
            ))
        if args.remove_kb:
            changes.extend(cls._remove_complex_item(
                entity_data, 'knowledge_bases', args.remove_kb, 'id', 'knowledge base'
            ))
        
        return changes
    
    @classmethod
    def _add_complex_item(
        cls,
        entity_data: Dict[str, Any],
        field_name: str,
        value_str: str,
        keys: List[str],
        item_type: str
    ) -> List[str]:
        """Add a complex item (dict) to a list field"""
        changes = []
        
        # Parse the value string (format: key1:key2:key3)
        parts = value_str.split(':')
        if len(parts) != len(keys):
            print(f"⚠️  Warning: Invalid format for {item_type}. Expected {':'.join(keys)}")
            return changes
        
        # Create the new item
        new_item = {key: part for key, part in zip(keys, parts)}
        
        # Get or create the list
        items = entity_data.get(field_name, [])
        if not isinstance(items, list):
            items = []
        
        # Add the item
        items.append(new_item)
        entity_data[field_name] = items
        
        changes.append(f"Added {item_type}: {new_item}")
        return changes
    
    @classmethod
    def _remove_complex_item(
        cls,
        entity_data: Dict[str, Any],
        field_name: str,
        identifier: str,
        key: str,
        item_type: str
    ) -> List[str]:
        """Remove a complex item from a list field by identifier"""
        changes = []
        
        items = entity_data.get(field_name, [])
        if not isinstance(items, list):
            return changes
        
        # Find and remove the item
        original_len = len(items)
        items = [item for item in items if item.get(key) != identifier]
        
        if len(items) < original_len:
            entity_data[field_name] = items
            changes.append(f"Removed {item_type}: {identifier}")
        else:
            print(f"⚠️  Warning: {item_type} '{identifier}' not found")
        
        return changes