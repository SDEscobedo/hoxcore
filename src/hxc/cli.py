#!/usr/bin/env python3
"""
hxc - Main CLI entry point
"""

import argparse
import sys
from typing import List, Optional

from hxc.commands import get_available_commands, load_command


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the command line interface.

    Args:
        args: Command line arguments (uses sys.argv if not provided)

    Returns:
        Exit code
    """
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="hxc", description="HXC command line tool", usage="hxc [command] [options]"
    )

    available_commands = get_available_commands()

    # Add command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    for cmd_name in available_commands:
        cmd_class = load_command(cmd_name)
        cmd_class.register_subparser(subparsers)

    # Add version argument
    parser.add_argument(
        "--version", action="store_true", help="Show version information"
    )

    # Parse arguments
    if not args:
        parser.print_help()
        return 0

    parsed_args = parser.parse_args(args)

    # Handle version
    if hasattr(parsed_args, "version") and parsed_args.version:
        from hxc import __version__

        print(f"hxc version {__version__}")
        return 0

    # Execute command if specified
    if parsed_args.command:
        cmd_class = load_command(parsed_args.command)
        return cmd_class.execute(parsed_args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
