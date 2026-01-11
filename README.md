# HoxCore Command Line Tool

A robust, scalable, and distributable command-line interface tool with a git-like command structure.

## Installation

### From PyPI (when published)

```bash
pip install hxc
```

### For Development

```bash
# Clone the repository
git clone https://github.com/SDEscobedo/hoxcore
cd hoxcore

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .
```

## Usage

```bash
$ hxc [command] [options]
```

### Available Commands

- `command1`: Example command
- `command2`: Another example command

### Examples

```bash
# Get help
$ hxc --help

# Get version information
$ hxc --version

# Get command-specific help
$ hxc command1 --help

# Execute commands
$ hxc command1 --option value
$ hxc command2 --flag input-value
```

## Development

### Project Structure

```
project/
├── LICENSE
├── README.md
├── pyproject.toml
├── setup.py
├── src/
│   └── hxc/
│       ├── __init__.py
│       ├── cli.py
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── command1.py
│       │   └── command2.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── config.py
│       └── utils/
│           ├── __init__.py
│           └── helpers.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_cli.py
    └── commands/
        ├── __init__.py
        ├── test_command1.py
        └── test_command2.py
```

### Adding New Commands

To add a new command to the CLI:

1. Create a new file in `src/hxc/commands/` (e.g., `mycommand.py`)
2. Define a class that inherits from `BaseCommand`
3. Use the `@register_command` decorator to register it
4. Implement `register_subparser` and `execute` methods

Example:

```python
from hxc.commands import register_command
from hxc.commands.base import BaseCommand

@register_command
class MyCommand(BaseCommand):
    name = "mycommand"
    help = "My custom command"
    
    @classmethod
    def register_subparser(cls, subparsers):
        parser = super().register_subparser(subparsers)
        parser.add_argument('--myflag', help='My flag')
        return parser
    
    @classmethod
    def execute(cls, args):
        # Implement command logic here
        return 0
```

### Running Tests

Make sure you have development dependencies installed:

```bash
pip install -e ".[dev]"
```

Run the tests:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=hxc

# Run specific tests
pytest tests/test_cli.py
```

### Important Test Setup

The project uses a `src/` layout for better package organization. Make sure you have a `conftest.py` file in your tests directory with the following content to ensure tests can import the package correctly:

```python
# tests/conftest.py
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
```

## Distribution

### Building the package

```bash
python -m build
```

### Publishing to PyPI

```bash
python -m twine upload dist/*
```

## License

MIT