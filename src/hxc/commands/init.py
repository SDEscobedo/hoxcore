"""
Initialize command implementation
"""
import os
import pathlib
import sqlite3
import subprocess
import argparse
from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.core.config import Config
from hxc.utils.path_security import resolve_safe_path, PathSecurityError


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
            registry_path = cls.initialize_registry(path, git, commit, remote_url)
            
            # Store the registry path in config if requested
            if set_default and registry_path:
                config = Config()
                config.set(cls.CONFIG_KEY, str(registry_path))
                print(f"✅ Registry set as default")
                
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
        # Resolve the base path to absolute path
        base = pathlib.Path(path).resolve()
        base.mkdir(parents=True, exist_ok=True)
        
        # Check if directory is empty (excluding hidden files/directories)
        existing_files = [f for f in os.listdir(base) if not f.startswith('.')]
        if existing_files:
            print(f"⚠️  Warning: Directory is not empty. Registry initialization aborted.")
            return None
        
        # From this point on, all paths must be validated against the registry root
        try:
            # Create required subfolders
            for folder in ["programs", "projects", "missions", "actions"]:
                folder_path = resolve_safe_path(base, folder)
                folder_path.mkdir(exist_ok=True)

            # Create config file
            config_path = resolve_safe_path(base, "config.yml")
            if not config_path.exists():
                config_path.write_text("# HoxCore Registry Configuration\n")

            # Create .hxc directory as a marker for the registry root
            hxc_dir = resolve_safe_path(base, ".hxc")
            hxc_dir.mkdir(exist_ok=True)
            
            # Create .gitignore
            gitignore = resolve_safe_path(base, ".gitignore")
            gitignore.write_text("index.db\n")
            
            # Create index.db file
            db_path = resolve_safe_path(base, "index.db")
            if not db_path.exists():
                conn = sqlite3.connect(db_path)
                try:
                    cursor = conn.cursor()
                    # Create basic table structure
                    cursor.execute('''
                    CREATE TABLE registry_info (
                        key TEXT PRIMARY KEY,
                        value TEXT
                    )
                    ''')
                    # Add creation timestamp
                    cursor.execute('''
                    INSERT INTO registry_info (key, value) 
                    VALUES ('created_at', datetime('now'))
                    ''')
                    conn.commit()
                finally:
                    conn.close()

            # Initialize Git repo
            git_dir = resolve_safe_path(base, ".git")
            if git and not git_dir.exists():
                subprocess.run(["git", "init"], cwd=base)
                
                # Add remote if specified
                if remote_url:
                    subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=base)
                    
                # Commit if requested
                if commit:
                    subprocess.run(["git", "add", "."], cwd=base)
                    subprocess.run(["git", "commit", "-m", "Initialize HoxCore registry"], cwd=base)
                    
                    # Push to remote if provided
                    if remote_url:
                        subprocess.run(["git", "push", "-u", "origin", "master"], cwd=base)

            absolute_path = base.resolve()
            print(f"✅ Registry initialized at: {absolute_path}")
            return str(absolute_path)
            
        except PathSecurityError as e:
            # Clean up if path security error occurs during initialization
            print(f"❌ Security error during initialization: {e}")
            raise