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
            
            # Create server instance
            server = create_server(registry_path=registry_path)
            
            # Show capabilities if requested
            if args.capabilities:
                cls._show_capabilities(server)
                return 0
            
            # Start server with specified transport
            print(f"🚀 Starting MCP server...", file=sys.stderr)
            print(f"📁 Registry: {registry_path}", file=sys.stderr)
            print(f"🔌 Transport: {args.transport}", file=sys.stderr)
            print(f"", file=sys.stderr)
            print(f"Server is ready to accept requests.", file=sys.stderr)
            print(f"", file=sys.stderr)
            
            if args.transport == "stdio":
                server.run_stdio()
            
            return 0
            
        except KeyboardInterrupt:
            print("\n⚠️  Server stopped by user", file=sys.stderr)
            return 0
        except Exception as e:
            print(f"❌ Error starting MCP server: {e}", file=sys.stderr)
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
        
        print("═══════════════════════════════════════════════════════")
        print("  MCP Server Capabilities")
        print("═══════════════════════════════════════════════════════")
        print()
        
        print(f"📁 Registry Path: {capabilities.get('registry_path', 'Not set')}")
        print()
        
        print("🔧 Available Tools:")
        for tool in capabilities.get('tools', []):
            print(f"  • {tool}")
        print()
        
        print("📚 Available Resources:")
        for resource in capabilities.get('resources', []):
            print(f"  • {resource}")
        print()
        
        print("💬 Available Prompts:")
        for prompt in capabilities.get('prompts', []):
            print(f"  • {prompt}")
        print()
        
        print("─" * 60)