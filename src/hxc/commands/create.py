"""
Create command implementation for generating new projects, programs, actions, or missions.
"""

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.enums import EntityStatus, EntityType
from hxc.core.operations.create import (
    CreateOperation,
    CreateOperationError,
    DuplicateIdError,
)
from hxc.core.operations.scaffold import (
    PromptRequiredError,
    ScaffoldExecutionError,
    ScaffoldOperation,
    ScaffoldSecurityError,
    TemplateNotFoundOperationError,
    TemplateValidationError,
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

        # Scaffolding arguments
        parser.add_argument(
            "--scaffold",
            action="store_true",
            help="Scaffold project structure from template (requires --template)",
        )
        parser.add_argument(
            "--output",
            "-o",
            dest="scaffold_output",
            help="Output directory for scaffolding (default: current directory)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview scaffolding without making changes",
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

        # Validate scaffolding options
        scaffold = getattr(args, "scaffold", False)
        dry_run = getattr(args, "dry_run", False)
        scaffold_output = getattr(args, "scaffold_output", None)
        template_ref = getattr(args, "template", None)

        if scaffold and not template_ref:
            # Check if category has a variant that can be used as template
            category = getattr(args, "category", None)
            if category:
                template_ref = cls._extract_template_from_category(
                    category, registry_path
                )
            if not template_ref:
                print("❌ --scaffold requires --template or a category with variant notation")
                return 1

        if dry_run and not scaffold:
            print("❌ --dry-run requires --scaffold flag")
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
                template=template_ref,
                use_git=not no_commit,
            )

            print(
                f"✅ Created {entity_type.value} '{result['entity']['title']}' at {result['file_path']}"
            )

            if no_commit:
                print("⚠️  Changes not committed (--no-commit flag used)")

            # Execute scaffolding if requested
            if scaffold and template_ref:
                scaffold_result = cls._execute_scaffolding(
                    template_ref=template_ref,
                    entity_data=result["entity"],
                    output_path=scaffold_output,
                    registry_path=registry_path,
                    dry_run=dry_run,
                )
                if scaffold_result != 0:
                    return scaffold_result

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

    @classmethod
    def _extract_template_from_category(
        cls, category: str, registry_path: str
    ) -> Optional[str]:
        """
        Extract template reference from category notation.

        Category notation format: `category-path.author/variant`
        Example: `software.dev/cli-tool.johndoe/latex-v2`
            -> template: `software.dev/cli-tool/johndoe/latex-v2`

        Args:
            category: Category string potentially containing variant notation
            registry_path: Registry path for template resolution

        Returns:
            Template reference string or None if no variant specified
        """
        try:
            scaffold_operation = ScaffoldOperation(registry_path=registry_path)
            parsed = scaffold_operation.parse_category_variant(category)

            if parsed.has_variant:
                return parsed.template_path

            return None
        except Exception:
            return None

    @classmethod
    def _execute_scaffolding(
        cls,
        template_ref: str,
        entity_data: Dict[str, Any],
        output_path: Optional[str],
        registry_path: str,
        dry_run: bool,
    ) -> int:
        """
        Execute scaffolding from a template.

        Args:
            template_ref: Template reference (path or identifier)
            entity_data: Entity data for variable substitution
            output_path: Output directory (defaults to current directory)
            registry_path: Registry path for template resolution
            dry_run: If True, preview without making changes

        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        # Determine output path
        if output_path:
            scaffold_path = Path(output_path).resolve()
        else:
            # Default to current directory with entity ID as subdirectory
            entity_id = entity_data.get("id", entity_data.get("uid", "project"))
            scaffold_path = Path.cwd() / entity_id

        try:
            scaffold_operation = ScaffoldOperation(registry_path=registry_path)

            if dry_run:
                result = scaffold_operation.preview(
                    template_ref=template_ref,
                    output_path=scaffold_path,
                    entity_data=entity_data,
                )
            else:
                result = scaffold_operation.scaffold(
                    template_ref=template_ref,
                    output_path=scaffold_path,
                    entity_data=entity_data,
                    dry_run=False,
                    allow_non_empty=False,
                    require_all_prompts=False,
                )

            # Print scaffolding results
            cls._print_scaffold_result(result, dry_run)

            if not result.success:
                return 1

            return 0

        except TemplateNotFoundOperationError as e:
            print(f"❌ Template not found: {e.template_ref}")
            if e.searched_paths:
                print("Searched locations:")
                for path in e.searched_paths:
                    print(f"  - {path}")
            return 1
        except TemplateValidationError as e:
            print(f"❌ Invalid template: {e}")
            return 1
        except ScaffoldSecurityError as e:
            print(f"❌ Security error during scaffolding: {e}")
            return 1
        except PromptRequiredError as e:
            print(f"❌ Prompt values required for scaffolding:")
            for prompt in e.required_prompts:
                prompt_name = prompt.get("name", "unknown")
                default = prompt.get("default")
                default_str = f" (default: {default})" if default else ""
                print(f"  - {prompt_name}{default_str}")
            print("")
            print("Tip: Prompt variables are not yet supported interactively.")
            print("     The entity was created, but scaffolding was skipped.")
            return 1
        except ScaffoldExecutionError as e:
            print(f"❌ Scaffolding failed: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error during scaffolding: {e}")
            return 1

    @classmethod
    def _print_scaffold_result(cls, result, dry_run: bool) -> None:
        """
        Print scaffolding result summary.

        Args:
            result: ScaffoldOperationResult instance
            dry_run: Whether this was a dry-run
        """
        if dry_run:
            prefix = "[DRY-RUN]"
            action_word = "Would create"
        else:
            prefix = "📁"
            action_word = "Scaffolded"

        template_name = result.template_name or "template"
        version_str = f" (v{result.template_version})" if result.template_version else ""

        print("")
        print(f"{prefix} {action_word} project structure from {template_name}{version_str}")
        print(f"   Output: {result.output_path}")
        print("")

        if result.directories_created:
            print("   Directories:")
            for directory in result.directories_created:
                print(f"     📁 {directory}/")

        if result.files_created:
            print("   Files:")
            for file in result.files_created:
                print(f"     📄 {file}")

        if result.files_copied:
            print("   Copied:")
            for file in result.files_copied:
                print(f"     📋 {file}")

        if result.git_initialized:
            print("")
            if dry_run:
                print("   🔧 Would initialize Git repository")
            else:
                print("   🔧 Initialized Git repository")

            if result.git_committed:
                if dry_run:
                    print("   📦 Would create initial commit")
                else:
                    print("   📦 Created initial commit")

        # Print pending prompts if any
        if result.pending_prompts:
            print("")
            print("   ⚠️  Prompt variables not resolved:")
            for prompt in result.pending_prompts:
                prompt_name = prompt.get("name", "unknown")
                default = prompt.get("default")
                default_str = f" (default: {default})" if default else ""
                print(f"     - {prompt_name}{default_str}")

        # Print warnings
        if hasattr(result, "scaffold_result") and result.scaffold_result:
            warnings = getattr(result.scaffold_result, "warnings", [])
            if warnings:
                print("")
                print("   ⚠️  Warnings:")
                for warning in warnings:
                    print(f"     - {warning}")

        print("")
        print(f"   Total: {result.total_items} item(s) {'would be ' if dry_run else ''}created")

        if not result.success and result.error:
            print("")
            print(f"   ❌ Error: {result.error}")