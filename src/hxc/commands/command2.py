# src/hxc/commands/command2.py
"""
Another example command implementation
"""
import argparse
from hxc.commands import register_command
from hxc.commands.base import BaseCommand


@register_command
class Command2(BaseCommand):
    """Another example command implementation"""
    
    name = "command2"
    help = "Another example command"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        parser.add_argument('--flag', action='store_true', help='Example flag')
        parser.add_argument('input', nargs='?', help='Input argument')
        return parser
    
    @classmethod
    def execute(cls, args):
        print(f"Executing command2 with flag: {args.flag}, input: {args.input}")
        return 0