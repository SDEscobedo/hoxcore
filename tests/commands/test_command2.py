
import pytest
from unittest.mock import patch

from hxc.cli import main
from hxc.commands.command2 import Command2


def test_command2_execution():
    """Test command2 execution"""
    with patch('builtins.print') as mock_print:
        result = main(['command2', '--flag', 'input-value'])
        assert result == 0
        mock_print.assert_called_once()
        assert 'input-value' in mock_print.call_args[0][0]
        assert 'True' in mock_print.call_args[0][0]


def test_command2_register_parser():
    """Test command2 parser registration"""
    from argparse import ArgumentParser, _SubParsersAction
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = Command2.register_subparser(subparsers)
    
    # Verify parser has the expected arguments
    has_flag_arg = any(action.dest == 'flag' for action in cmd_parser._actions)
    has_input_arg = any(action.dest == 'input' for action in cmd_parser._actions)
    
    assert has_flag_arg, "command2 parser should have 'flag' argument"
    assert has_input_arg, "command2 parser should have 'input' argument"