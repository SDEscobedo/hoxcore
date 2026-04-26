"""
Template command implementation for managing HoxCore templates.

This module provides commands for listing, showing, validating, and previewing
templates used for scaffolding new entities.
"""

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.operations.scaffold import (
    PromptRequiredError,
    ScaffoldExecutionError,
    ScaffoldOperation,
    ScaffoldSecurityError,
    TemplateNotFoundOperationError,
    TemplateValidationError,
)
from hxc.utils.helpers import get_project_root


@register_command
class TemplateCommand(BaseCommand):
    """Manage HoxCore templates for project scaffolding"""

    name = "template"
    help = "List, show, validate, and preview templates"

    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)

        # Add template subcommands
        template_subparsers = parser.add_subparsers(
            dest="template_command",
            help="Template commands",
            metavar="<subcommand>",
        )

        # list subcommand
        list_parser = template_subparsers.add_parser(
            "list",
            help="List available templates",
        )
        list_parser.add_argument(
            "--registry-only",
            action="store_true",
            help="Only show registry-local templates",
        )
        list_parser.add_argument(
            "--user-only",
            action="store_true",
            help="Only show user templates",
        )
        list_parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON",
        )
        list_parser.add_argument(
            "--registry",
            help="Path to registry (uses default if not provided)",
        )

        # show subcommand
        show_parser = template_subparsers.add_parser(
            "show",
            help="Show template details",
        )
        show_parser.add_argument(
            "template_ref",
            help="Template reference (path or identifier)",
        )
        show_parser.add_argument(
            "--json",
            action="store_true",
            help="Output as JSON",
        )
        show_parser.add_argument(
            "--registry",
            help="Path to registry (uses default if not provided)",
        )

        # validate subcommand
        validate_parser = template_subparsers.add_parser(
            "validate",
            help="Validate a template file",
        )
        validate_parser.add_argument(
            "template_ref",
            help="Template reference (path or identifier)",
        )
        validate_parser.add_argument(
            "--registry",
            help="Path to registry (uses default if not provided)",
        )

        # preview subcommand
        preview_parser = template_subparsers.add_parser(
            "preview",
            help="Preview what scaffolding would create",
        )
        preview_parser.add_argument(
            "template_ref",
            help="Template reference (path or identifier)",
        )
        preview_parser.add_argument(
            "--output",
            "-o",
            default=".",
            help="Output directory for preview (default: current directory)",
        )
        preview_parser.add_argument(
            "--title",
            help="Entity title for variable substitution",
        )
        preview_parser.add_argument(
            "--id",
            dest="entity_id",
            help="Entity ID for variable substitution",
        )
        preview_parser.add_argument(
            "--registry",
            help="Path to registry (uses default if not provided)",
        )

        # init-dirs subcommand
        init_dirs_parser = template_subparsers.add_parser(
            "init-dirs",
            help="Initialize template directories",
        )
        init_dirs_parser.add_argument(
            "--registry",
            help="Path to registry (uses default if not provided)",
        )

        return parser

    @classmethod
    def execute(cls, args):
        template_command = getattr(args, "template_command", None)

        if not template_command:
            print("Usage: hxc template <subcommand>")
            print("")
            print("Available subcommands:")
            print("  list      List available templates")
            print("  show      Show template details")
            print("  validate  Validate a template file")
            print("  preview   Preview what scaffolding would create")
            print("  init-dirs Initialize template directories")
            print("")
            print("Run 'hxc template <subcommand> --help' for more information.")
            return 0

        if template_command == "list":
            return cls._execute_list(args)
        elif template_command == "show":
            return cls._execute_show(args)
        elif template_command == "validate":
            return cls._execute_validate(args)
        elif template_command == "preview":
            return cls._execute_preview(args)
        elif template_command == "init-dirs":
            return cls._execute_init_dirs(args)
        else:
            print(f"❌ Unknown template command: {template_command}")
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
    def _execute_list(cls, args) -> int:
        """Execute the list subcommand"""
        registry_path = cls._get_registry_path(getattr(args, "registry", None))

        include_registry = not getattr(args, "user_only", False)
        include_user = not getattr(args, "registry_only", False)
        output_json = getattr(args, "json", False)

        try:
            operation = ScaffoldOperation(registry_path=registry_path)
            templates = operation.list_templates(
                include_registry=include_registry,
                include_user=include_user,
            )

            if output_json:
                import json
                print(json.dumps(templates, indent=2))
                return 0

            if not templates:
                print("No templates found.")
                if not registry_path and include_registry:
                    print("  Tip: Specify --registry to search in a registry's templates.")
                print("")
                print("Template directories:")
                print(f"  User: ~/.hxc/templates/")
                if registry_path:
                    print(f"  Registry: {registry_path}/.hxc/templates/")
                return 0

            print("Available templates:")
            print("")

            # Group by source
            registry_templates = [t for t in templates if t.get("source") == "registry"]
            user_templates = [t for t in templates if t.get("source") == "user"]

            if registry_templates and include_registry:
                print("Registry templates:")
                cls._print_template_list(registry_templates)
                print("")

            if user_templates and include_user:
                print("User templates:")
                cls._print_template_list(user_templates)
                print("")

            print(f"Total: {len(templates)} template(s)")
            return 0

        except Exception as e:
            print(f"❌ Error listing templates: {e}")
            return 1

    @classmethod
    def _print_template_list(cls, templates: List[Dict[str, Any]]) -> None:
        """Print a formatted list of templates"""
        for template in templates:
            template_id = template.get("id", "unknown")
            valid = template.get("valid", False)
            name = template.get("name") or template_id
            version = template.get("version", "")
            description = template.get("description", "")

            status_icon = "✓" if valid else "✗"
            version_str = f" (v{version})" if version else ""

            print(f"  {status_icon} {template_id}{version_str}")

            if name and name != template_id:
                print(f"      Name: {name}")

            if description:
                # Truncate long descriptions
                if len(description) > 60:
                    description = description[:57] + "..."
                print(f"      {description}")

    @classmethod
    def _execute_show(cls, args) -> int:
        """Execute the show subcommand"""
        template_ref = args.template_ref
        registry_path = cls._get_registry_path(getattr(args, "registry", None))
        output_json = getattr(args, "json", False)

        try:
            operation = ScaffoldOperation(registry_path=registry_path)
            info = operation.get_template_info(template_ref)

            if output_json:
                import json
                print(json.dumps(info, indent=2, default=str))
                return 0

            # Print formatted template info
            print(f"Template: {template_ref}")
            print("")

            if info.get("name"):
                print(f"  Name: {info['name']}")
            if info.get("version"):
                print(f"  Version: {info['version']}")
            if info.get("author"):
                print(f"  Author: {info['author']}")
            if info.get("description"):
                print(f"  Description: {info['description']}")
            if info.get("source"):
                print(f"  Source: {info['source']}")
            if info.get("path"):
                print(f"  Path: {info['path']}")

            print("")

            # Print structure
            structure = info.get("structure", [])
            if structure:
                print("Structure:")
                for entry in structure:
                    entry_type = entry.get("type", "unknown")
                    path = entry.get("path", "")
                    icon = "📁" if entry_type == "directory" else "📄"
                    print(f"  {icon} {path}/")

            # Print files
            files = info.get("files", [])
            if files:
                print("")
                print("Files:")
                for entry in files:
                    path = entry.get("path", "")
                    has_content = "content" in entry
                    has_template = "template" in entry
                    source_info = ""
                    if has_template:
                        source_info = f" (from template: {entry['template']})"
                    print(f"  📄 {path}{source_info}")

            # Print copy entries
            copy_entries = info.get("copy", [])
            if copy_entries:
                print("")
                print("Copy:")
                for entry in copy_entries:
                    source = entry.get("source", "")
                    destination = entry.get("destination", "")
                    print(f"  📋 {source} → {destination}")

            # Print git config
            git_config = info.get("git")
            if git_config:
                print("")
                print("Git:")
                if git_config.get("init"):
                    print("  🔧 Initialize repository")
                if git_config.get("initial_commit"):
                    commit_msg = git_config.get("commit_message", "Initial commit")
                    print(f"  📦 Initial commit: \"{commit_msg}\"")

            # Print variables
            variables = info.get("variables", [])
            if variables:
                print("")
                print("Variables:")
                for var in variables:
                    var_name = var.get("name", "")
                    var_source = var.get("source", "entity")
                    var_default = var.get("default")
                    default_str = f" (default: {var_default})" if var_default else ""
                    print(f"  {{{{ {var_name} }}}} - {var_source}{default_str}")

            return 0

        except TemplateNotFoundOperationError as e:
            print(f"❌ Template not found: {template_ref}")
            if e.searched_paths:
                print("Searched locations:")
                for path in e.searched_paths:
                    print(f"  - {path}")
            return 1
        except TemplateValidationError as e:
            print(f"❌ Invalid template: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error showing template: {e}")
            return 1

    @classmethod
    def _execute_validate(cls, args) -> int:
        """Execute the validate subcommand"""
        template_ref = args.template_ref
        registry_path = cls._get_registry_path(getattr(args, "registry", None))

        try:
            operation = ScaffoldOperation(registry_path=registry_path)

            # Resolve and parse template (validation happens during parse)
            template_path = operation.resolve_template(template_ref)
            template_data = operation.parse_template(template_path)

            print(f"✅ Template is valid: {template_ref}")
            print(f"   Path: {template_path}")

            if template_data.get("name"):
                print(f"   Name: {template_data['name']}")
            if template_data.get("version"):
                print(f"   Version: {template_data['version']}")

            return 0

        except TemplateNotFoundOperationError as e:
            print(f"❌ Template not found: {template_ref}")
            if e.searched_paths:
                print("Searched locations:")
                for path in e.searched_paths:
                    print(f"  - {path}")
            return 1
        except TemplateValidationError as e:
            print(f"❌ Template validation failed: {e}")
            return 1
        except ScaffoldSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error validating template: {e}")
            return 1

    @classmethod
    def _execute_preview(cls, args) -> int:
        """Execute the preview subcommand"""
        template_ref = args.template_ref
        output_path = getattr(args, "output", ".")
        title = getattr(args, "title", None)
        entity_id = getattr(args, "entity_id", None)
        registry_path = cls._get_registry_path(getattr(args, "registry", None))

        # Build entity data from provided arguments
        entity_data: Dict[str, Any] = {}
        if title:
            entity_data["title"] = title
        if entity_id:
            entity_data["id"] = entity_id

        # Add some defaults if not provided
        if "title" not in entity_data:
            entity_data["title"] = "Untitled Project"
        if "id" not in entity_data:
            entity_data["id"] = "untitled_project"

        try:
            operation = ScaffoldOperation(registry_path=registry_path)

            result = operation.preview(
                template_ref=template_ref,
                output_path=output_path,
                entity_data=entity_data,
            )

            if not result.success:
                print(f"❌ Preview failed: {result.error}")
                return 1

            # Print preview summary
            print(f"Template: {result.template_name or template_ref}")
            if result.template_version:
                print(f"Version: {result.template_version}")
            print(f"Output: {result.output_path}")
            print("")
            print("[DRY-RUN] Would create:")
            print("")

            if result.directories_created:
                print("Directories:")
                for directory in result.directories_created:
                    print(f"  📁 {directory}/")

            if result.files_created:
                print("")
                print("Files:")
                for file in result.files_created:
                    print(f"  📄 {file}")

            if result.files_copied:
                print("")
                print("Copied:")
                for file in result.files_copied:
                    print(f"  📋 {file}")

            if result.git_initialized:
                print("")
                print("Git:")
                print("  🔧 Would initialize repository")
                if result.git_committed:
                    print("  📦 Would create initial commit")

            # Print pending prompts if any
            if result.pending_prompts:
                print("")
                print("⚠️  Prompt variables required:")
                for prompt in result.pending_prompts:
                    prompt_name = prompt.get("name", "unknown")
                    default = prompt.get("default")
                    default_str = f" (default: {default})" if default else ""
                    print(f"  - {prompt_name}{default_str}")

            print("")
            print(f"Total: {result.total_items} item(s) would be created")

            return 0

        except TemplateNotFoundOperationError as e:
            print(f"❌ Template not found: {template_ref}")
            if e.searched_paths:
                print("Searched locations:")
                for path in e.searched_paths:
                    print(f"  - {path}")
            return 1
        except TemplateValidationError as e:
            print(f"❌ Invalid template: {e}")
            return 1
        except ScaffoldSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except PromptRequiredError as e:
            print(f"❌ Prompt values required: {e}")
            print("")
            print("Required prompt variables:")
            for prompt in e.required_prompts:
                prompt_name = prompt.get("name", "unknown")
                default = prompt.get("default")
                default_str = f" (default: {default})" if default else ""
                print(f"  - {prompt_name}{default_str}")
            return 1
        except ScaffoldExecutionError as e:
            print(f"❌ Preview failed: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error previewing template: {e}")
            return 1

    @classmethod
    def _execute_init_dirs(cls, args) -> int:
        """Execute the init-dirs subcommand"""
        registry_path = cls._get_registry_path(getattr(args, "registry", None))

        try:
            operation = ScaffoldOperation(registry_path=registry_path)
            result = operation.ensure_template_directories()

            print("Template directories initialized:")

            if result.get("user"):
                print(f"  ✅ User: {result['user']}")
            else:
                print("  ⚠️  User: Could not create")

            if registry_path:
                if result.get("registry"):
                    print(f"  ✅ Registry: {result['registry']}")
                else:
                    print("  ⚠️  Registry: Could not create")
            else:
                print("  ℹ️  Registry: No registry specified")

            return 0

        except Exception as e:
            print(f"❌ Error initializing template directories: {e}")
            return 1