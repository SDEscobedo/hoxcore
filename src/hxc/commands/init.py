"""
Initialize command implementation
"""
import argparse
from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.core.config import Config
from hxc.core.operations.init import initialize_registry
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
        parser.add_argument('path', nargs='?', default='.',
                          help='Path to initialize registry (default: current directory)')
        parser.add_argument('--no-git', action='store_true',
                          help='Skip Git repository initialization')
        parser.add_argument('--no-commit', action='store_true',
                          help='Skip initial Git commit')
        parser.add_argument('--remote', metavar='URL',
                          help='Set Git remote repository URL')
        parser.add_argument('--no-set-default', action='store_true',
                          help='Do not set this registry as the default')
        return parser

    @classmethod
    def execute(cls, args):
        path = args.path
        git = not args.no_git
        commit = not args.no_commit
        remote_url = args.remote if hasattr(args, 'remote') else None
        set_default = not args.no_set_default if hasattr(args, 'no_set_default') else True

        try:
            result = cls.initialize_registry(path, git, commit, remote_url)
            registry_path = result.get("registry_path")

            if not result.get("success"):
                print(f"⚠️  Warning: {result.get('error')}")
                return 0

            if set_default and registry_path:
                config = Config()
                config.set(cls.CONFIG_KEY, str(registry_path))
                print("✅ Registry set as default")

            print(f"✅ Registry initialized at: {registry_path}")
            return 0
        except PathSecurityError as e:
            print(f"❌ Security error: {e}")
            return 1
        except Exception as e:
            print(f"❌ Error initializing registry: {e}")
            return 1

    @staticmethod
    def initialize_registry(path: str, git: bool = True, commit: bool = True, remote_url: str = None):
        """Set up a new project registry at the given path"""
        return initialize_registry(path=path, git=git, commit=commit, remote_url=remote_url)
