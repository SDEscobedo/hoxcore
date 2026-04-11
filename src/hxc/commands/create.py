"""
Create command implementation for generating new projects, programs, actions, or missions.
"""

import argparse
from typing import Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.create import (
    CreateOperation,
    CreateOperationError,
    DuplicateIdError,
)
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError


def title_to_id(title: str, entity_type: str) -> str:
    """
    Deterministically generate a human-readable, filesystem/URL-safe base ID from a title.

    This is a module-level wrapper around CreateOperation.title_to_id() for backward
    compatibility with existing code and tests.

    Rules:
    - Allowed characters: [a-z0-9_]
    - Spaces/special characters become underscores
    - Consecutive underscores collapse; leading/trailing underscores removed
    - Non-ASCII is transliterated/removed via NFKD -> ascii ignore
    - Result length is capped to 255 chars
    """
    return CreateOperation.title_to_id(title, entity_type)


@register_command
class CreateCommand(BaseCommand):
    """Create a new entity (program, project, action, mission) in the registry"""

    name = "create"
    help = "Create a new program, project, action, or mission"

    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)

        # Required arguments
        parser.add_argument(
            "type", choices=EntityType.values(), help="Type of entity to create"
        )
        parser.add_argument("title", help="Title of the entity")

        # Optional arguments
        parser.add_argument(
            "--id", dest="custom_id", help="Custom ID for the entity (e.g., P-001)"
        )
        parser.add_argument("--description", "-d", help="Description of the entity")
        parser.add_argument(
            "--status",
            default="active",
            choices=EntityStatus.values(),
            help="Status of the entity (default: active)",
        )
        parser.add_argument(
            "--start-date", help="Start date in YYYY-MM-DD format (default: today)"
        )
        parser.add_argument("--due-date", help="Due date in YYYY-MM-DD format")
        parser.add_argument(
            "--category", help="Category path (e.g., software.dev/cli-tool)"
        )
        parser.add_argument("--tags", nargs="+", help="List of tags (space separated)")
        parser.add_argument("--parent", help="Parent entity UID or ID")
        parser.add_argument(
            "--template", help="Template to use (e.g., software.dev/cli-tool.default)"
        )
        parser.add_argument(
            "--registry",
            help="Path to registry (defaults to current or configured registry)",
        )
        parser.add_argument(
            "--no-commit",
            action="store_true",
            help="Skip automatic git commit after creating",
        )

        return parser

    @classmethod
    def execute(cls, args):
        try:
            entity_type = EntityType.from_string(args.type)
            entity_status = EntityStatus.from_string(args.status)
        except ValueError as e:
            print(f"❌ Invalid argument: {e}")
            return 1

        registry_path = cls._get_registry_path(args.registry)
        if not registry_path:
            print(
                "❌ No registry found. Please specify with --registry or initialize one with 'hxc init'"
            )
            return 1

        operation = CreateOperation(registry_path)

        no_commit = getattr(args, "no_commit", False)

        try:
            result = operation.create_entity(
                entity_type=entity_type,
                title=args.title,
                entity_id=args.custom_id,
                description=args.description,
                status=entity_status,
                start_date=args.start_date,
                due_date=args.due_date,
                category=args.category,
                tags=args.tags,
                parent=args.parent,
                template=args.template,
                use_git=not no_commit,
            )

            print(
                f"✅ Created {entity_type.value} '{result['entity']['title']}' at {result['file_path']}"
            )

            if no_commit:
                print("⚠️  Changes not committed (--no-commit flag used)")

            return 0

        except DuplicateIdError as e:
            print(f"❌ {e}")
            return 1
        except CreateOperationError as e:
            print(f"❌ {e}")
            return 1
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except ValueError as e:
            print(f"❌ Invalid entity type: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error creating {entity_type.value}: {e}")
            return 1

    @classmethod
    def _get_registry_path(cls, specified_path: Optional[str] = None) -> Optional[str]:
        """Get registry path from specified path, config, or current directory"""
        if specified_path:
            return specified_path

        registry_path = RegistryCommand.get_registry_path()
        if registry_path:
            return registry_path

        return get_project_root()
