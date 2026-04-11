from argparse import ArgumentParser
from unittest.mock import patch

import pytest

from hxc.cli import main
from hxc.commands.base import BaseCommand


def test_main_no_args():
    """Test main function with no arguments"""
    with patch("argparse.ArgumentParser.print_help") as mock_print_help:
        result = main([])
        assert result == 0
        mock_print_help.assert_called_once()


def test_main_version():
    """Test main function with --version argument"""
    with patch("builtins.print") as mock_print:
        result = main(["--version"])
        assert result == 0
        mock_print.assert_called_once()
        assert "version" in mock_print.call_args[0][0]
