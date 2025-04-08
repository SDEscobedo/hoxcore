# src/hxc/commands/command1.py
"""
Example command implementation
"""
import argparse
from hxc.commands import register_command
from hxc.commands.base import BaseCommand


@register_command
class Command1(BaseCommand):
    """Example command implementation"""
    
    name = "command1"
    help = "Example command"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        parser.add_argument('--option', help='Example option')
        return parser
    
    @classmethod
    def execute(cls, args):
        print(f"Executing command1 with option: {args.option}")
        return 0
