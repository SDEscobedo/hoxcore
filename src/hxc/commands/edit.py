"""
Edit command implementation for modifying entity properties.

This module provides the CLI interface for editing entity properties. It delegates
core editing logic to the shared EditOperation class while handling CLI-specific
features like complex field editing (repositories, storage, etc.).
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.edit import (
    DuplicateIdError,
    EditOperation,
    EditOperationError,
    EntityNotFoundError,
    InvalidValueError,
    NoChangesError,
)
from hxc.utils.git import (
    commit_entity_change,
    find_git_root,
    git_available,
    parse_commit_hash,
    summarise_changes,
)
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError, resolve_safe_path


@register_command
class EditCommand(BaseCommand):
    """Command for editing entity properties"""

    name = "edit"
    help = "Edit properties of a program, project, action, or mission"

    # Define editable scalar fields
    SCALAR_FIELDS = {
        "title": str,
        "description": str,
        "status": str,
        "id": str,
        "start_date": str,
        "due_date": str,
        "completion_date": str,
        "duration_estimate": str,
        "category": str,
        "parent": str,
        "template": str,
    }

    # Define editable list fields
    LIST_FIELDS = {
        "tags": list,
        "children": list,
        "related": list,
    }

    # Define editable complex fields (list of dicts)
    COMPLEX_FIELDS = {
        "repositories": list,
        "storage": list,
        "databases": list,
        "tools": list,
        "models": list,
        "knowledge_bases": list,
    }

    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)

        # Required argument: identifier
        parser.add_argument("identifier", help="ID or UID of the entity to edit")

        # Optional: entity type filter
        parser.add_argument(
            "--type",
            "-t",
            choices=EntityType.values(),
            help="Entity type (only needed if identifier is ambiguous)",
        )

        # Scalar field setters
        parser.add_argument("--set-title", metavar="VALUE", help="Set title")
        parser.add_argument(
            "--set-description", metavar="VALUE", help="Set description"
        )
        parser.add_argument(
            "--set-status",
            metavar="VALUE",
            choices=EntityStatus.values(),
            help="Set status",
        )
        parser.add_argument("--set-id", metavar="VALUE", help="Set custom ID")
        parser.add_argument(
            "--set-start-date", metavar="YYYY-MM-DD", help="Set start date"
        )
        parser.add_argument("--set-due-date", metavar="YYYY-MM-DD", help="Set due date")
        parser.add_argument(
            "--set-completion-date", metavar="YYYY-MM-DD", help="Set completion date"
        )
        parser.add_argument(
            "--set-duration-estimate",
            metavar="VALUE",
            help="Set duration estimate (e.g., 90d, 3w)",
        )
        parser.add_argument("--set-category", metavar="VALUE", help="Set category")
        parser.add_argument("--set-parent", metavar="UID", help="Set parent UID")
        parser.add_argument("--set-template", metavar="VALUE", help="Set template")

        # List field operations
        parser.add_argument(
            "--add-tag",
            metavar="TAG",
            action="append",
            help="Add a tag (can be used multiple times)",
        )
        parser.add_argument(
            "--remove-tag",
            metavar="TAG",
            action="append",
            help="Remove a tag (can be used multiple times)",
        )
        parser.add_argument(
            "--set-tags",
            metavar="TAG",
            nargs="+",
            help="Set tags (replaces all existing tags)",
        )

        parser.add_argument(
            "--add-child", metavar="UID", action="append", help="Add a child UID"
        )
        parser.add_argument(
            "--remove-child", metavar="UID", action="append", help="Remove a child UID"
        )
        parser.add_argument(
            "--set-children",
            metavar="UID",
            nargs="+",
            help="Set children UIDs (replaces all)",
        )

        parser.add_argument(
            "--add-related", metavar="UID", action="append", help="Add a related UID"
        )
        parser.add_argument(
            "--remove-related",
            metavar="UID",
            action="append",
            help="Remove a related UID",
        )
        parser.add_argument(
            "--set-related",
            metavar="UID",
            nargs="+",
            help="Set related UIDs (replaces all)",
        )

        # Complex field operations (JSON object format)
        parser.add_argument(
            "--add-repository",
            metavar="JSON",
            action="append",
            help='Add repository as JSON object (can be used multiple times), e.g.: \'{"name": "myrepo", "url": "https://github.com/org/repo"}\'',
        )
        parser.add_argument(
            "--remove-repository",
            metavar="NAME",
            action="append",
            help="Remove repository by name (can be used multiple times)",
        )

        parser.add_argument(
            "--add-storage",
            metavar="JSON",
            action="append",
            help='Add storage as JSON object (can be used multiple times), e.g.: \'{"name": "docs", "provider": "gdrive", "url": "https://drive.google.com/..."}\'',
        )
        parser.add_argument(
            "--remove-storage",
            metavar="NAME",
            action="append",
            help="Remove storage by name (can be used multiple times)",
        )

        parser.add_argument(
            "--add-database",
            metavar="JSON",
            action="append",
            help='Add database as JSON object (can be used multiple times), e.g.: \'{"name": "main", "type": "postgres", "url": "postgres://..."}\'',
        )
        parser.add_argument(
            "--remove-database",
            metavar="NAME",
            action="append",
            help="Remove database by name (can be used multiple times)",
        )

        parser.add_argument(
            "--add-tool",
            metavar="JSON",
            action="append",
            help='Add tool as JSON object (can be used multiple times), e.g.: \'{"name": "jira", "provider": "atlassian", "url": "https://..."}\'',
        )
        parser.add_argument(
            "--remove-tool",
            metavar="NAME",
            action="append",
            help="Remove tool by name (can be used multiple times)",
        )

        parser.add_argument(
            "--add-model",
            metavar="JSON",
            action="append",
            help='Add model as JSON object (can be used multiple times), e.g.: \'{"id": "gpt-4", "provider": "openai", "url": "https://..."}\'',
        )
        parser.add_argument(
            "--remove-model",
            metavar="ID",
            action="append",
            help="Remove model by ID (can be used multiple times)",
        )

        parser.add_argument(
            "--add-kb",
            metavar="JSON",
            action="append",
            help='Add knowledge base as JSON object (can be used multiple times), e.g.: \'{"id": "kb-001", "url": "https://..."}\'',
        )
        parser.add_argument(
            "--remove-kb",
            metavar="ID",
            action="append",
            help="Remove knowledge base by ID (can be used multiple times)",
        )

        # Other options
        parser.add_argument(
            "--registry",
            help="Path to registry (defaults to current or configured registry)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without actually modifying the file",
        )
        parser.add_argument(
            "--no-commit",
            action="store_true",
            help="Skip automatic git commit after editing",
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
                print(
                    "❌ No registry found. Please specify with --registry or initialize one with 'hxc init'"
                )
                return 1

            # Check if we have any complex field edits (CLI-specific)
            has_complex_edits = cls._has_complex_edits(args)

            # Check if we have any core edits (handled by EditOperation)
            has_core_edits = cls._has_core_edits(args)

            # If no edits at all, show warning
            if not has_complex_edits and not has_core_edits:
                print("⚠️  No changes specified. Use --help to see available options.")
                return 0

            # Initialize the shared operation
            operation = EditOperation(registry_path)

            # Find the entity file
            result = operation.find_entity_file(args.identifier, entity_type)
            if result is None:
                print(f"❌ No entity found with identifier '{args.identifier}'")
                if entity_type:
                    print(f"   (search limited to type: {entity_type.value})")
                return 1

            file_path, found_entity_type = result

            # Load the entity
            try:
                entity_data = operation.load_entity(file_path)
            except EditOperationError as e:
                print(f"❌ {e}")
                return 1

            # Track all changes
            changes = []

            # Apply core edits using the shared operation
            if has_core_edits:
                try:
                    # Apply scalar edits
                    scalar_changes = operation.apply_scalar_edits(
                        entity_data,
                        set_title=getattr(args, "set_title", None),
                        set_description=getattr(args, "set_description", None),
                        set_status=getattr(args, "set_status", None),
                        set_id=getattr(args, "set_id", None),
                        set_start_date=getattr(args, "set_start_date", None),
                        set_due_date=getattr(args, "set_due_date", None),
                        set_completion_date=getattr(args, "set_completion_date", None),
                        set_duration_estimate=getattr(
                            args, "set_duration_estimate", None
                        ),
                        set_category=getattr(args, "set_category", None),
                        set_parent=getattr(args, "set_parent", None),
                        set_template=getattr(args, "set_template", None),
                    )
                    changes.extend(scalar_changes)

                    # Apply list edits
                    list_changes = operation.apply_list_edits(
                        entity_data,
                        set_tags=getattr(args, "set_tags", None),
                        add_tags=getattr(args, "add_tag", None),
                        remove_tags=getattr(args, "remove_tag", None),
                        set_children=getattr(args, "set_children", None),
                        add_children=getattr(args, "add_child", None),
                        remove_children=getattr(args, "remove_child", None),
                        set_related=getattr(args, "set_related", None),
                        add_related=getattr(args, "add_related", None),
                        remove_related=getattr(args, "remove_related", None),
                    )
                    changes.extend(list_changes)

                except DuplicateIdError as e:
                    print(f"❌ {e}")
                    return 1
                except InvalidValueError as e:
                    print(f"❌ Invalid value: {e}")
                    return 1

            # Apply complex field edits (CLI-specific)
            if has_complex_edits:
                complex_changes = cls._apply_complex_edits(entity_data, args)
                changes.extend(complex_changes)

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
                operation.write_entity_file(file_path, entity_data)
                print(f"✅ Successfully updated entity at {file_path}")
            except Exception as e:
                print(f"❌ Error writing changes: {e}")
                return 1

            # Git commit (unless --no-commit is specified)
            no_commit = getattr(args, "no_commit", False)
            if no_commit:
                print("⚠️  Changes not committed (--no-commit flag used)")
            else:
                commit_entity_change(
                    registry_path=registry_path,
                    file_path=file_path,
                    action="Edit",
                    entity_data=entity_data,
                    changes=changes,
                )

            return 0

        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error editing entity: {e}")
            return 1

    # ------------------------------------------------------------------ #
    #  Helper methods for checking edit types                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def _has_core_edits(cls, args: argparse.Namespace) -> bool:
        """Check if any core edits (handled by EditOperation) are specified."""
        core_args = [
            "set_title",
            "set_description",
            "set_status",
            "set_id",
            "set_start_date",
            "set_due_date",
            "set_completion_date",
            "set_duration_estimate",
            "set_category",
            "set_parent",
            "set_template",
            "set_tags",
            "add_tag",
            "remove_tag",
            "set_children",
            "add_child",
            "remove_child",
            "set_related",
            "add_related",
            "remove_related",
        ]
        for arg_name in core_args:
            value = getattr(args, arg_name, None)
            if value is not None:
                # For set_tags, set_children, set_related: None means not specified
                # For add/remove lists: None or empty list means not specified
                if isinstance(value, list) and len(value) == 0:
                    continue
                return True
        return False

    @classmethod
    def _has_complex_edits(cls, args: argparse.Namespace) -> bool:
        """Check if any complex field edits (CLI-specific) are specified."""
        complex_args = [
            "add_repository",
            "remove_repository",
            "add_storage",
            "remove_storage",
            "add_database",
            "remove_database",
            "add_tool",
            "remove_tool",
            "add_model",
            "remove_model",
            "add_kb",
            "remove_kb",
        ]
        for arg_name in complex_args:
            value = getattr(args, arg_name, None)
            if value:
                return True
        return False

    # ------------------------------------------------------------------ #
    #  Git integration (delegates to shared utilities)                     #
    # ------------------------------------------------------------------ #

    @classmethod
    def _commit_changes(
        cls,
        registry_path: str,
        file_path: Path,
        entity_data: Dict[str, Any],
        changes: List[str],
    ) -> None:
        """
        Stage the edited file and create a git commit.

        Delegates to the shared git utility module for consistent behavior
        across create, edit, and delete commands.

        Failures are non-fatal: a warning is printed and the method returns
        without raising so the edit operation is still considered successful.
        """
        commit_entity_change(
            registry_path=registry_path,
            file_path=file_path,
            action="Edit",
            entity_data=entity_data,
            changes=changes,
        )

    @classmethod
    def _find_git_root(cls, start_path: str) -> Optional[str]:
        """Walk up from *start_path* looking for a .git directory."""
        return find_git_root(start_path)

    @classmethod
    def _git_available(cls) -> bool:
        """Return True if the git executable can be found."""
        return git_available()

    @classmethod
    def _summarise_changes(cls, changes: List[str]) -> str:
        """Build a short one-line summary from the changes list."""
        return summarise_changes(changes)

    @classmethod
    def _parse_commit_hash(cls, git_output: str) -> Optional[str]:
        """Extract the short commit hash from git commit stdout."""
        return parse_commit_hash(git_output)

    # ------------------------------------------------------------------ #
    #  Registry path helper                                                #
    # ------------------------------------------------------------------ #

    @classmethod
    def _get_registry_path(cls, specified_path: Optional[str] = None) -> Optional[str]:
        if specified_path:
            return specified_path
        registry_path = RegistryCommand.get_registry_path()
        if registry_path:
            return registry_path
        return get_project_root()

    # ------------------------------------------------------------------ #
    #  Complex field operations (CLI-specific)                             #
    # ------------------------------------------------------------------ #

    @classmethod
    def _apply_complex_edits(
        cls, entity_data: Dict[str, Any], args: argparse.Namespace
    ) -> List[str]:
        changes = []
        # Repository operations
        if args.add_repository:
            for repo_json in args.add_repository:
                changes.extend(
                    cls._add_complex_item(
                        entity_data, "repositories", repo_json, "repository"
                    )
                )
        if args.remove_repository:
            for repo_name in args.remove_repository:
                changes.extend(
                    cls._remove_complex_item(
                        entity_data, "repositories", repo_name, "name", "repository"
                    )
                )

        # Storage operations
        if args.add_storage:
            for storage_json in args.add_storage:
                changes.extend(
                    cls._add_complex_item(
                        entity_data, "storage", storage_json, "storage"
                    )
                )
        if args.remove_storage:
            for storage_name in args.remove_storage:
                changes.extend(
                    cls._remove_complex_item(
                        entity_data, "storage", storage_name, "name", "storage"
                    )
                )

        # Database operations
        if args.add_database:
            for db_json in args.add_database:
                changes.extend(
                    cls._add_complex_item(entity_data, "databases", db_json, "database")
                )
        if args.remove_database:
            for db_name in args.remove_database:
                changes.extend(
                    cls._remove_complex_item(
                        entity_data, "databases", db_name, "name", "database"
                    )
                )

        # Tool operations
        if args.add_tool:
            for tool_json in args.add_tool:
                changes.extend(
                    cls._add_complex_item(entity_data, "tools", tool_json, "tool")
                )
        if args.remove_tool:
            for tool_name in args.remove_tool:
                changes.extend(
                    cls._remove_complex_item(
                        entity_data, "tools", tool_name, "name", "tool"
                    )
                )

        # Model operations
        if args.add_model:
            for model_json in args.add_model:
                changes.extend(
                    cls._add_complex_item(entity_data, "models", model_json, "model")
                )
        if args.remove_model:
            for model_id in args.remove_model:
                changes.extend(
                    cls._remove_complex_item(
                        entity_data, "models", model_id, "id", "model"
                    )
                )

        # Knowledge base operations
        if args.add_kb:
            for kb_json in args.add_kb:
                changes.extend(
                    cls._add_complex_item(
                        entity_data, "knowledge_bases", kb_json, "knowledge base"
                    )
                )
        if args.remove_kb:
            for kb_id in args.remove_kb:
                changes.extend(
                    cls._remove_complex_item(
                        entity_data, "knowledge_bases", kb_id, "id", "knowledge base"
                    )
                )

        return changes

    @classmethod
    def _add_complex_item(
        cls,
        entity_data: Dict[str, Any],
        field_name: str,
        value_str: str,
        item_type: str,
    ) -> List[str]:
        """
        Add a complex item to a list field by parsing JSON.

        Args:
            entity_data: The entity data dictionary to modify
            field_name: The name of the field (e.g., 'repositories')
            value_str: JSON string representing the item to add
            item_type: Human-readable name for error messages (e.g., 'repository')

        Returns:
            List of change descriptions
        """
        changes = []

        # Parse the JSON object
        try:
            new_item = json.loads(value_str)
            if not isinstance(new_item, dict):
                raise ValueError("Expected a JSON object")
        except (json.JSONDecodeError, ValueError) as e:
            print(
                f"⚠️  Warning: Invalid format for {item_type}. Expected a JSON object."
            )
            print(f'   Example: \'{{"name": "example", "url": "https://..."}}\'')
            return changes

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
        item_type: str,
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
