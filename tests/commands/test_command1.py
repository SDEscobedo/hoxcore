
import pytest
from unittest.mock import patch

from hxc.cli import main
from hxc.commands.command1 import Command1


def test_command1_execution():
    """Test command1 execution"""
    with patch('builtins.print') as mock_print:
        result = main(['command1', '--option', 'test-value'])
        assert result == 0
        mock_print.assert_called_once()
        assert 'test-value' in mock_print.call_args[0][0]


def test_command1_register_parser():
    """Test command1 parser registration"""
    from argparse import ArgumentParser, _SubParsersAction
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = Command1.register_subparser(subparsers)
    
    # Verify parser has the expected arguments
    has_option_arg = any(action.dest == 'option' for action in cmd_parser._actions)
    assert has_option_arg, "command1 parser should have 'option' argument"

