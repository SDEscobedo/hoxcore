"""
MCP command implementation for starting the Model Context Protocol server.
"""
import argparse
import sys
from typing import Optional

from hxc.commands import register_command
from hxc.commands.base import BaseCommand
from hxc.commands.registry import RegistryCommand
from hxc.utils.helpers import get_project_root


@register_command
class MCPCommand(BaseCommand):
    """Command for starting the MCP server"""

    name = "mcp"
    help = "Start the Model Context Protocol (MCP) server for LLM access"

    @classmethod
    def register_subparser(cls, subparsers) -> argparse.ArgumentParser:
        parser = super().register_subparser(subparsers)

        # Server configuration
        parser.add_argument(
            "--registry",
            help="Path to the registry (defaults to current or configured registry)"
        )
        parser.add_argument(
            "--transport",
            choices=["stdio"],
            default="stdio",
            help="Transport protocol (default: stdio)"
        )
        parser.add_argument(
            "--capabilities",
            action="store_true",
            help="Show server capabilities and exit"
        )
        parser.add_argument(
            "--read-only",
            action="store_true",
            dest="read_only",
            help=(
                "Start in read-only mode: only read tools are registered. "
                "Write tools (create_entity, edit_entity, delete_entity) are omitted."
            )
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

            # Import MCP server (lazy import to avoid loading if not needed)
            from hxc.mcp.server import create_server

            read_only = getattr(args, "read_only", False)

            # Create server instance
            server = create_server(registry_path=registry_path, read_only=read_only)

            # Show capabilities if requested
            if args.capabilities:
                cls._show_capabilities(server)
                return 0

            # Start server with specified transport
            print(f"🚀 Starting MCP server...", file=sys.stderr)
            print(f"📁 Registry: {registry_path}", file=sys.stderr)
            print(f"🔌 Transport: {args.transport}", file=sys.stderr)
            if read_only:
                print(f"🔒 Mode: read-only (write tools disabled)", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"Server is ready to accept requests.", file=sys.stderr)

            if args.transport == "stdio":
                server.run_stdio()

            return 0

        except Exception as e:
            print(f"❌ Error starting MCP server: {e}")
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
    def _show_capabilities(cls, server) -> None:
        """Display server capabilities"""
        capabilities = server.get_capabilities()

        print("\n🔧 MCP Server Capabilities")
        print("=" * 40)
        print(f"\n📁 Registry: {capabilities.get('registry_path', 'Unknown')}")
        if capabilities.get("read_only"):
            print("🔒 Mode: read-only")

        print(f"\n🛠️  Tools ({len(capabilities.get('tools', []))}):")
        for tool in sorted(capabilities.get("tools", [])):
            print(f"  • {tool}")

        print(f"\n📚 Resources ({len(capabilities.get('resources', []))}):")
        for resource in sorted(capabilities.get("resources", [])):
            print(f"  • {resource}")

        print(f"\n💬 Prompts ({len(capabilities.get('prompts', []))}):")
        for prompt in sorted(capabilities.get("prompts", [])):
            print(f"  • {prompt}")

        print()