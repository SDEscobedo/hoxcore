"""
Validate command implementation for checking registry integrity.
"""
import os
import yaml
import argparse
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import resolve_safe_path, PathSecurityError


@register_command
class ValidateCommand(BaseCommand):
    """Command for validating registry integrity"""
    
    name = "validate"
    help = "Validate registry integrity and consistency"
    
    # Entity types and their directories
    ENTITY_TYPES = {
        "program": "programs",
        "project": "projects",
        "mission": "missions",
        "action": "actions"
    }
    
    # Required fields for all entities
    REQUIRED_FIELDS = ["type", "uid", "title"]
    
    # Valid status values
    VALID_STATUSES = ["active", "completed", "on-hold", "cancelled", "planned"]
    
    @classmethod
    def register_subparser(cls, subparsers) -> argparse.ArgumentParser:
        parser = super().register_subparser(subparsers)
        
        parser.add_argument(
            "--registry",
            help="Path to registry (defaults to current or configured registry)"
        )
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Show detailed validation information"
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to fix issues (not implemented - read-only operation)"
        )
        
        return parser
    
    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        try:
            # Get registry path
            registry_path = cls._get_registry_path(args.registry)
            if not registry_path:
                print("❌ No registry found. Please specify with --registry or initialize one with 'hxc init'")
                return 1
            
            # Warn if --fix is used
            if args.fix:
                print("⚠️  --fix option is not implemented. Validation is read-only.")
                print()
            
            print(f"🔍 Validating registry at: {registry_path}")
            print()
            
            # Load all entities
            entities, load_errors = cls._load_all_entities(registry_path, args.verbose)
            
            # Track validation results
            errors = []
            warnings = []
            
            # Add load errors
            errors.extend(load_errors)
            
            # Validate required fields
            field_errors = cls._validate_required_fields(entities, args.verbose)
            errors.extend(field_errors)
            
            # Validate UIDs
            uid_errors = cls._validate_uids(entities, args.verbose)
            errors.extend(uid_errors)
            
            # Validate parent/child relationships
            relationship_errors, relationship_warnings = cls._validate_relationships(
                entities, args.verbose
            )
            errors.extend(relationship_errors)
            warnings.extend(relationship_warnings)
            
            # Validate status values
            status_errors = cls._validate_status(entities, args.verbose)
            errors.extend(status_errors)
            
            # Validate entity types
            type_errors = cls._validate_types(entities, args.verbose)
            errors.extend(type_errors)
            
            # Display results
            cls._display_results(entities, errors, warnings, args.verbose)
            
            # Return exit code
            return 0 if not errors else 1
            
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error validating registry: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
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
    def _load_all_entities(
        cls, 
        registry_path: str, 
        verbose: bool
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Load all entities from the registry
        
        Returns:
            Tuple of (entities list, load errors list)
        """
        entities = []
        errors = []
        
        if verbose:
            print("📂 Loading entities...")
        
        for entity_type, folder_name in cls.ENTITY_TYPES.items():
            try:
                type_dir = resolve_safe_path(registry_path, folder_name)
            except PathSecurityError as e:
                errors.append(f"Security error accessing {folder_name}: {e}")
                continue
            
            if not type_dir.exists():
                if verbose:
                    print(f"  ⚠️  Directory not found: {folder_name}")
                continue
            
            # Load all YAML files in the directory
            for file_path in type_dir.glob("*.yml"):
                try:
                    secure_file_path = resolve_safe_path(registry_path, file_path)
                    
                    with open(secure_file_path, 'r') as f:
                        entity_data = yaml.safe_load(f)
                        
                    if entity_data is None:
                        errors.append(f"Empty file: {file_path.name}")
                        continue
                    
                    if not isinstance(entity_data, dict):
                        errors.append(f"Invalid YAML structure in {file_path.name}")
                        continue
                    
                    # Add file metadata
                    entity_data['_file'] = {
                        'path': str(secure_file_path),
                        'name': secure_file_path.name,
                        'type': entity_type
                    }
                    
                    entities.append(entity_data)
                    
                    if verbose:
                        uid = entity_data.get('uid', 'NO_UID')
                        print(f"  ✓ Loaded {entity_type}: {uid} ({file_path.name})")
                        
                except PathSecurityError as e:
                    errors.append(f"Security error with {file_path.name}: {e}")
                except yaml.YAMLError as e:
                    errors.append(f"YAML parse error in {file_path.name}: {e}")
                except Exception as e:
                    errors.append(f"Error loading {file_path.name}: {e}")
        
        if verbose:
            print(f"\n📊 Loaded {len(entities)} entities")
            print()
        
        return entities, errors
    
    @classmethod
    def _validate_required_fields(
        cls, 
        entities: List[Dict[str, Any]], 
        verbose: bool
    ) -> List[str]:
        """Validate that all entities have required fields"""
        errors = []
        
        if verbose:
            print("🔍 Checking required fields...")
        
        for entity in entities:
            file_name = entity.get('_file', {}).get('name', 'unknown')
            
            for field in cls.REQUIRED_FIELDS:
                if field not in entity or not entity[field]:
                    error = f"Missing required field '{field}' in {file_name}"
                    errors.append(error)
                    if verbose:
                        print(f"  ❌ {error}")
        
        if verbose and not errors:
            print("  ✓ All required fields present")
        
        if verbose:
            print()
        
        return errors
    
    @classmethod
    def _validate_uids(
        cls, 
        entities: List[Dict[str, Any]], 
        verbose: bool
    ) -> List[str]:
        """Validate that all UIDs are unique"""
        errors = []
        uid_map = defaultdict(list)
        
        if verbose:
            print("🔍 Checking UID uniqueness...")
        
        # Build UID map
        for entity in entities:
            uid = entity.get('uid')
            if uid:
                file_name = entity.get('_file', {}).get('name', 'unknown')
                uid_map[uid].append(file_name)
        
        # Check for duplicates
        for uid, files in uid_map.items():
            if len(files) > 1:
                error = f"Duplicate UID '{uid}' found in files: {', '.join(files)}"
                errors.append(error)
                if verbose:
                    print(f"  ❌ {error}")
        
        if verbose and not errors:
            print(f"  ✓ All {len(uid_map)} UIDs are unique")
        
        if verbose:
            print()
        
        return errors
    
    @classmethod
    def _validate_relationships(
        cls, 
        entities: List[Dict[str, Any]], 
        verbose: bool
    ) -> Tuple[List[str], List[str]]:
        """Validate parent/child and related relationships"""
        errors = []
        warnings = []
        
        if verbose:
            print("🔍 Checking relationships...")
        
        # Build UID set for quick lookup
        valid_uids = {entity.get('uid') for entity in entities if entity.get('uid')}
        
        for entity in entities:
            file_name = entity.get('_file', {}).get('name', 'unknown')
            uid = entity.get('uid', 'NO_UID')
            
            # Check parent
            parent = entity.get('parent')
            if parent:
                if parent not in valid_uids:
                    error = f"Broken parent link in {file_name}: parent '{parent}' not found"
                    errors.append(error)
                    if verbose:
                        print(f"  ❌ {error}")
            
            # Check children
            children = entity.get('children', [])
            if children:
                if not isinstance(children, list):
                    error = f"Invalid children format in {file_name}: must be a list"
                    errors.append(error)
                    if verbose:
                        print(f"  ❌ {error}")
                else:
                    for child_uid in children:
                        if child_uid not in valid_uids:
                            error = f"Broken child link in {file_name}: child '{child_uid}' not found"
                            errors.append(error)
                            if verbose:
                                print(f"  ❌ {error}")
            
            # Check related
            related = entity.get('related', [])
            if related:
                if not isinstance(related, list):
                    warning = f"Invalid related format in {file_name}: must be a list"
                    warnings.append(warning)
                    if verbose:
                        print(f"  ⚠️  {warning}")
                else:
                    for related_uid in related:
                        if related_uid not in valid_uids:
                            warning = f"Broken related link in {file_name}: related '{related_uid}' not found"
                            warnings.append(warning)
                            if verbose:
                                print(f"  ⚠️  {warning}")
        
        if verbose and not errors and not warnings:
            print("  ✓ All relationships are valid")
        
        if verbose:
            print()
        
        return errors, warnings
    
    @classmethod
    def _validate_status(
        cls, 
        entities: List[Dict[str, Any]], 
        verbose: bool
    ) -> List[str]:
        """Validate status values"""
        errors = []
        
        if verbose:
            print("🔍 Checking status values...")
        
        for entity in entities:
            status = entity.get('status')
            if status and status not in cls.VALID_STATUSES:
                file_name = entity.get('_file', {}).get('name', 'unknown')
                error = f"Invalid status '{status}' in {file_name}. Valid values: {', '.join(cls.VALID_STATUSES)}"
                errors.append(error)
                if verbose:
                    print(f"  ❌ {error}")
        
        if verbose and not errors:
            print("  ✓ All status values are valid")
        
        if verbose:
            print()
        
        return errors
    
    @classmethod
    def _validate_types(
        cls, 
        entities: List[Dict[str, Any]], 
        verbose: bool
    ) -> List[str]:
        """Validate entity types match their directory"""
        errors = []
        
        if verbose:
            print("🔍 Checking entity types...")
        
        for entity in entities:
            declared_type = entity.get('type')
            file_type = entity.get('_file', {}).get('type')
            file_name = entity.get('_file', {}).get('name', 'unknown')
            
            if declared_type and file_type and declared_type != file_type:
                error = f"Type mismatch in {file_name}: declared as '{declared_type}' but in '{file_type}' directory"
                errors.append(error)
                if verbose:
                    print(f"  ❌ {error}")
        
        if verbose and not errors:
            print("  ✓ All entity types match their directories")
        
        if verbose:
            print()
        
        return errors
    
    @classmethod
    def _display_results(
        cls, 
        entities: List[Dict[str, Any]], 
        errors: List[str], 
        warnings: List[str],
        verbose: bool
    ) -> None:
        """Display validation results summary"""
        print("=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        print()
        
        print(f"📊 Total entities: {len(entities)}")
        print(f"❌ Errors: {len(errors)}")
        print(f"⚠️  Warnings: {len(warnings)}")
        print()
        
        if errors:
            print("ERRORS:")
            print("-" * 60)
            for error in errors:
                print(f"  ❌ {error}")
            print()
        
        if warnings:
            print("WARNINGS:")
            print("-" * 60)
            for warning in warnings:
                print(f"  ⚠️  {warning}")
            print()
        
        if not errors and not warnings:
            print("✅ Registry validation passed! No issues found.")
        elif not errors:
            print("✅ Registry validation passed with warnings.")
        else:
            print("❌ Registry validation failed. Please fix the errors above.")
        
        print()