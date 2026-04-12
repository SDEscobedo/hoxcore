"""
Initialize command implementation
"""

import argparse

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.core.config import Config
from hxc.core.operations.init import (
    DirectoryNotEmptyError,
    GitOperationError,
    InitOperation,
    InitOperationError,
)
from hxc.utils.path_security import PathSecurityError


@register_command
class InitCommand(BaseCommand):
    """Initialize a new project registry"""

    name = "init"
    help = "Initialize a new project registry"

    # Config key for storing registry path (same as in RegistryCommand)
    CONFIG_KEY = "registry_path"

    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        parser.add_argument(
            "path",
            nargs="?",
            default=".",
            help="Path to initialize registry (default: current directory)",
        )
        parser.add_argument(
            "--no-git", action="store_true", help="Skip Git repository initialization"
        )
        parser.add_argument(
            "--no-commit", action="store_true", help="Skip initial Git commit"
        )
        parser.add_argument(
            "--remote", metavar="URL", help="Set Git remote repository URL"
        )
        parser.add_argument(
            "--no-set-default",
            action="store_true",
            help="Do not set this registry as the default",
        )
        return parser

    @classmethod
    def execute(cls, args):
        path = args.path
        use_git = not args.no_git
        commit = not args.no_commit
        remote_url = args.remote if hasattr(args, "remote") else None
        set_default = (
            not args.no_set_default if hasattr(args, "no_set_default") else True
        )

        try:
            result = cls.initialize_registry(path, use_git, commit, remote_url)

            if result is None:
                # Non-empty directory warning was printed
                return 0

            registry_path = result.get("registry_path")

            # Store the registry path in config if requested
            if set_default and registry_path:
                config = Config()
                config.set(cls.CONFIG_KEY, str(registry_path))
                print("✅ Registry set as default")

            return 0

        except DirectoryNotEmptyError:
            print(
                "⚠️  Warning: Directory is not empty. Registry initialization aborted."
            )
            return 0
        except GitOperationError as e:
            print(f"❌ Git operation failed: {e}")
            return 1
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except InitOperationError as e:
            print(f"❌ Error initializing registry: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error initializing registry: {e}")
            return 1

    @staticmethod
    def initialize_registry(
        path: str,
        use_git: bool = True,
        commit: bool = True,
        remote_url: str = None,
    ):
        """
        Set up a new project registry at the given path.

        This method delegates to the shared InitOperation to ensure
        behavioral consistency between CLI and MCP interfaces.

        Args:
            path: Path where to initialize the registry
            use_git: Whether to initialize a git repository
            commit: Whether to create an initial commit (requires use_git)
            remote_url: Optional git remote URL to configure

        Returns:
            Dictionary with initialization results, or None if aborted

        Raises:
            DirectoryNotEmptyError: If directory is not empty
            GitOperationError: If git operations fail
            PathSecurityError: If path validation fails
            InitOperationError: If initialization fails
        """
        operation = InitOperation(path)

        result = operation.initialize_registry(
            use_git=use_git,
            commit=commit,
            remote_url=remote_url,
            force_empty_check=True,
        )

        registry_path = result.get("registry_path")
        print(f"✅ Registry initialized at: {registry_path}")

        return result