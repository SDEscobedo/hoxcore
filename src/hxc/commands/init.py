"""
Initialize command implementation
"""
import pathlib
import subprocess
import argparse
from hxc.commands import register_command
from hxc.commands.base import BaseCommand


@register_command
class InitCommand(BaseCommand):
    """Initialize a new project registry"""
    
    name = "init"
    help = "Initialize a new project registry"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        parser.add_argument('path', nargs='?', default='.', 
                          help='Path to initialize registry (default: current directory)')
        parser.add_argument('--no-git', action='store_true',
                          help='Skip Git repository initialization')
        parser.add_argument('--no-commit', action='store_true',
                          help='Skip initial Git commit')
        return parser
    
    @classmethod
    def execute(cls, args):
        path = args.path
        git = not args.no_git
        commit = not args.no_commit
        
        try:
            cls.initialize_registry(path, git, commit)
            return 0
        except Exception as e:
            print(f"❌ Error initializing registry: {e}")
            return 1
    
    @staticmethod
    def initialize_registry(path: str, git: bool = True, commit: bool = True):
        """Set up a new project registry at the given path"""
        base = pathlib.Path(path)
        base.mkdir(parents=True, exist_ok=True)

        # Create required subfolders
        for folder in ["programs", "projects", "missions", "actions"]:
            (base / folder).mkdir(exist_ok=True)

        # Create config file
        config_path = base / "config.yml"
        if not config_path.exists():
            config_path.write_text("# HoxCore Registry Configuration\n")

        # Create .gitignore
        gitignore = base / ".gitignore"
        gitignore.write_text("index.db\n")

        # Initialize Git repo
        if git and not (base / ".git").exists():
            subprocess.run(["git", "init"], cwd=base)
            if commit:
                subprocess.run(["git", "add", "."], cwd=base)
                subprocess.run(["git", "commit", "-m", "Initialize HoxCore registry"], cwd=base)

        print(f"✅ Registry initialized at: {base.resolve()}")