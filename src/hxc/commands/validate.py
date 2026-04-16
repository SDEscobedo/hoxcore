"""
Validate command implementation for checking registry integrity.

This command uses the shared ValidateOperation to ensure behavioral
consistency with MCP tools.
"""

import argparse
from typing import Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.operations.validate import ValidateOperation, ValidationResult
from hxc.utils.helpers import get_project_root
from hxc.utils.path_security import PathSecurityError


@register_command
class ValidateCommand(BaseCommand):
    """Command for validating registry integrity"""

    name = "validate"
    help = "Validate registry integrity and consistency"

    @classmethod
    def register_subparser(cls, subparsers) -> argparse.ArgumentParser:
        parser = super().register_subparser(subparsers)

        parser.add_argument(
            "--registry",
            help="Path to registry (defaults to current or configured registry)",
        )
        parser.add_argument(
            "--verbose",
            "-v",
            action="store_true",
            help="Show detailed validation information",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to fix issues (not implemented - read-only operation)",
        )

        return parser

    @classmethod
    def execute(cls, args: argparse.Namespace) -> int:
        try:
            # Get registry path
            registry_path = cls._get_registry_path(args.registry)
            if not registry_path:
                print(
                    "❌ No registry found. Please specify with --registry or initialize one with 'hxc init'"
                )
                return 1

            # Warn if --fix is used
            if args.fix:
                print("⚠️  --fix option is not implemented. Validation is read-only.")
                print()

            print(f"🔍 Validating registry at: {registry_path}")
            print()

            # Use shared ValidateOperation
            operation = ValidateOperation(registry_path)

            # Print verbose progress if requested
            if args.verbose:
                cls._print_verbose_progress()

            # Execute validation
            result = operation.validate_registry(verbose=args.verbose)

            # Display results
            cls._display_results(result, args.verbose)

            # Return exit code
            return 0 if result.valid else 1

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
    def _print_verbose_progress(cls) -> None:
        """Print verbose progress headers for validation steps"""
        print("📂 Loading entities...")
        print()
        print("🔍 Checking required fields...")
        print()
        print("🔍 Checking UID uniqueness...")
        print()
        print("🔍 Checking ID uniqueness (per entity type)...")
        print()
        print("🔍 Checking relationships...")
        print()
        print("🔍 Checking status values...")
        print()
        print("🔍 Checking entity types...")
        print()

    @classmethod
    def _display_results(
        cls,
        result: ValidationResult,
        verbose: bool,
    ) -> None:
        """Display validation results summary"""
        # Print verbose details if requested
        if verbose:
            if not result.errors and not result.warnings:
                print("  ✓ All required fields present")
                print()

                uid_count = result.entities_checked
                print(f"  ✓ All {uid_count} UIDs are unique")
                print()

                print(f"  ✓ All {uid_count} IDs are unique within their entity types")
                print()

                print("  ✓ All relationships are valid")
                print()

                print("  ✓ All status values are valid")
                print()

                print("  ✓ All entity types match their directories")
                print()
            else:
                # Print errors with verbose formatting
                for error in result.errors:
                    print(f"  ❌ {error}")

                for warning in result.warnings:
                    print(f"  ⚠️  {warning}")

                print()

        print("=" * 60)
        print("VALIDATION RESULTS")
        print("=" * 60)
        print()

        print(f"📊 Total entities: {result.entities_checked}")
        print(f"❌ Errors: {result.error_count}")
        print(f"⚠️  Warnings: {result.warning_count}")
        print()

        if result.errors:
            print("ERRORS:")
            print("-" * 60)
            for error in result.errors:
                print(f"  ❌ {error}")
            print()

        if result.warnings:
            print("WARNINGS:")
            print("-" * 60)
            for warning in result.warnings:
                print(f"  ⚠️  {warning}")
            print()

        if result.valid and not result.warnings:
            print("✅ Registry validation passed! No issues found.")
        elif result.valid:
            print("✅ Registry validation passed with warnings.")
        else:
            print("❌ Registry validation failed. Please fix the errors above.")

        print()
