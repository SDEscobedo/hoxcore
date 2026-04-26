"""
Pytest fixtures for HoxCore Template Module tests.

This module provides shared fixtures for testing the declarative template
scaffolding system including:

- Temporary registry directories with template structures
- Sample template definitions (valid and invalid)
- Sample entity data for variable substitution
- Template files in various locations (user, registry, explicit paths)
- Git-enabled test directories for scaffolding tests
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator

import pytest
import yaml


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def temp_registry(tmp_path) -> Generator[Path, None, None]:
    """
    Create a temporary registry structure for testing.

    Includes:
    - .hxc/ marker directory
    - config.yml configuration file
    - Entity directories (programs, projects, missions, actions)
    - .hxc/templates/ directory for registry-local templates
    """
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)

    # Create marker files and directories
    (registry_path / ".hxc").mkdir()
    (registry_path / ".hxc" / "templates").mkdir()
    (registry_path / "config.yml").write_text("# Test config\n")

    # Create entity directories
    (registry_path / "programs").mkdir()
    (registry_path / "projects").mkdir()
    (registry_path / "missions").mkdir()
    (registry_path / "actions").mkdir()

    yield registry_path

    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


@pytest.fixture
def user_templates_dir(tmp_path) -> Generator[Path, None, None]:
    """
    Create a temporary user templates directory (~/.hxc/templates/ equivalent).

    This simulates the user-global templates directory.
    """
    templates_dir = tmp_path / "user_templates"
    templates_dir.mkdir(parents=True)

    yield templates_dir

    # Clean up
    if templates_dir.exists():
        shutil.rmtree(templates_dir)


@pytest.fixture
def git_enabled_dir(tmp_path) -> Generator[Path, None, None]:
    """
    Create a temporary directory with Git initialized.

    Useful for testing scaffolding operations that include Git initialization.
    """
    git_dir = tmp_path / "git_test"
    git_dir.mkdir(parents=True)

    # Initialize git repository
    try:
        subprocess.run(
            ["git", "init"],
            cwd=git_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=git_dir,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=git_dir,
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available - tests using this fixture should skip
        pytest.skip("Git is not available")

    yield git_dir

    # Clean up
    if git_dir.exists():
        shutil.rmtree(git_dir)


@pytest.fixture
def output_dir(tmp_path) -> Generator[Path, None, None]:
    """
    Create a clean temporary directory for scaffolding output.

    Used as the destination for scaffolding operations.
    """
    output_path = tmp_path / "scaffold_output"
    # Don't create it - let the scaffolding operation create it
    yield output_path

    # Clean up
    if output_path.exists():
        shutil.rmtree(output_path)


@pytest.fixture
def minimal_template_data() -> Dict[str, Any]:
    """
    Return a minimal valid template definition.

    Contains only required fields (name, version).
    """
    return {
        "name": "minimal-template",
        "version": "1.0",
    }


@pytest.fixture
def full_template_data() -> Dict[str, Any]:
    """
    Return a complete template definition with all supported fields.

    Useful for testing full template parsing and validation.
    """
    return {
        "name": "full-template",
        "version": "1.0",
        "description": "A complete template for testing",
        "author": "test-author",
        "variables": [
            {"name": "title", "source": "entity"},
            {"name": "id", "source": "entity"},
            {"name": "description", "source": "entity"},
            {"name": "year", "source": "system", "format": "%Y"},
            {"name": "date", "source": "system"},
            {"name": "author_name", "source": "prompt", "default": "Unknown Author"},
        ],
        "structure": [
            {"type": "directory", "path": "src/{{id}}"},
            {"type": "directory", "path": "tests"},
            {"type": "directory", "path": "docs"},
        ],
        "files": [
            {
                "path": "README.md",
                "content": "# {{title}}\n\nCreated: {{year}}\nAuthor: {{author_name}}\n\n{{description}}",
            },
            {
                "path": "src/{{id}}/__init__.py",
                "content": '"""{{title}} - Main module"""\n__version__ = "0.1.0"',
            },
        ],
        "copy": [
            {"source": "assets/LICENSE", "destination": "LICENSE"},
        ],
        "git": {
            "init": True,
            "initial_commit": True,
            "commit_message": "Initial commit from template: {{title}}",
        },
    }


@pytest.fixture
def cli_tool_template_data() -> Dict[str, Any]:
    """
    Return a realistic CLI tool template definition.

    Simulates the software.dev/cli-tool/default template.
    """
    return {
        "name": "cli-tool-default",
        "version": "1.0",
        "description": "Standard CLI tool project structure",
        "author": "hoxcore",
        "variables": [
            {"name": "title", "source": "entity"},
            {"name": "id", "source": "entity"},
            {"name": "uid", "source": "entity"},
            {"name": "description", "source": "entity"},
            {"name": "year", "source": "system", "format": "%Y"},
            {"name": "author_name", "source": "prompt", "default": "Unknown"},
        ],
        "structure": [
            {"type": "directory", "path": "src/{{id}}"},
            {"type": "directory", "path": "tests"},
            {"type": "directory", "path": "docs"},
        ],
        "files": [
            {
                "path": "README.md",
                "content": "# {{title}}\n\nA CLI tool created with HoxCore.\n\n## Installation\n\nbash\npip install {{id}}\n\n",
            },
            {
                "path": "src/{{id}}/__init__.py",
                "content": '"""{{title}}"""\n\n__version__ = "0.1.0"\n',
            },
            {
                "path": "src/{{id}}/cli.py",
                "content": '"""{{title}} CLI entry point"""\n\nimport sys\n\ndef main():\n    print("Hello from {{title}}")\n    return 0\n\nif __name__ == "__main__":\n    sys.exit(main())\n',
            },
            {
                "path": "tests/__init__.py",
                "content": '"""Tests for {{title}}"""\n',
            },
            {
                "path": "pyproject.toml",
                "content": '[project]\nname = "{{id}}"\nversion = "0.1.0"\ndescription = "{{description}}"\n\n[project.scripts]\n{{id}} = "{{id}}.cli:main"\n',
            },
        ],
        "git": {
            "init": True,
            "initial_commit": True,
            "commit_message": "Initial commit: {{title}}",
        },
    }


@pytest.fixture
def sample_entity_data() -> Dict[str, Any]:
    """
    Return sample entity data for variable substitution tests.

    Simulates a typical project entity.
    """
    return {
        "type": "project",
        "uid": "abc12345",
        "id": "my_project",
        "title": "My Project",
        "description": "A sample project for testing",
        "status": "active",
        "category": "software.dev/cli-tool",
        "start_date": "2024-01-15",
    }


@pytest.fixture
def sample_entity_data_minimal() -> Dict[str, Any]:
    """
    Return minimal entity data for variable substitution tests.

    Contains only the most essential fields.
    """
    return {
        "type": "project",
        "uid": "xyz98765",
        "id": "minimal_proj",
        "title": "Minimal Project",
        "status": "active",
    }


@pytest.fixture
def template_with_prompts_data() -> Dict[str, Any]:
    """
    Return a template definition that requires prompt variables.

    Useful for testing prompt variable handling.
    """
    return {
        "name": "prompt-template",
        "version": "1.0",
        "description": "Template requiring user prompts",
        "variables": [
            {"name": "title", "source": "entity"},
            {"name": "id", "source": "entity"},
            {"name": "author_name", "source": "prompt"},  # No default - required
            {"name": "license_type", "source": "prompt", "default": "MIT"},
            {"name": "copyright_year", "source": "prompt", "default": "2024"},
        ],
        "structure": [
            {"type": "directory", "path": "src"},
        ],
        "files": [
            {
                "path": "LICENSE",
                "content": "{{license_type}} License\n\nCopyright (c) {{copyright_year}} {{author_name}}\n",
            },
        ],
    }


@pytest.fixture
def invalid_template_missing_name() -> Dict[str, Any]:
    """Return a template definition missing the required 'name' field."""
    return {
        "version": "1.0",
        "description": "Invalid template - no name",
    }


@pytest.fixture
def invalid_template_missing_version() -> Dict[str, Any]:
    """Return a template definition missing the required 'version' field."""
    return {
        "name": "invalid-template",
        "description": "Invalid template - no version",
    }


@pytest.fixture
def invalid_template_path_traversal() -> Dict[str, Any]:
    """Return a template definition with path traversal attempt."""
    return {
        "name": "malicious-template",
        "version": "1.0",
        "structure": [
            {"type": "directory", "path": "../../../etc"},  # Path traversal
        ],
    }


@pytest.fixture
def invalid_template_absolute_path() -> Dict[str, Any]:
    """Return a template definition with absolute path."""
    return {
        "name": "malicious-template",
        "version": "1.0",
        "files": [
            {"path": "/etc/passwd", "content": "malicious"},
        ],
    }


@pytest.fixture
def template_file(tmp_path, full_template_data) -> Generator[Path, None, None]:
    """
    Create a temporary template YAML file.

    Returns the path to a valid template file.
    """
    template_path = tmp_path / "template.yml"
    with open(template_path, "w") as f:
        yaml.dump(full_template_data, f, default_flow_style=False)

    yield template_path

    # Clean up
    if template_path.exists():
        template_path.unlink()


@pytest.fixture
def cli_tool_template_file(tmp_path, cli_tool_template_data) -> Generator[Path, None, None]:
    """
    Create a temporary CLI tool template YAML file.

    Returns the path to a realistic CLI tool template.
    """
    template_path = tmp_path / "cli-tool-default.yml"
    with open(template_path, "w") as f:
        yaml.dump(cli_tool_template_data, f, default_flow_style=False)

    yield template_path

    # Clean up
    if template_path.exists():
        template_path.unlink()


@pytest.fixture
def registry_with_templates(temp_registry, cli_tool_template_data) -> Path:
    """
    Create a registry with template files in .hxc/templates/.

    Includes:
    - software.dev/cli-tool/default.yml
    - generic/project.yml
    """
    templates_dir = temp_registry / ".hxc" / "templates"

    # Create nested template directories
    (templates_dir / "software.dev" / "cli-tool").mkdir(parents=True)
    (templates_dir / "generic").mkdir(parents=True)

    # Write CLI tool template
    cli_template_path = templates_dir / "software.dev" / "cli-tool" / "default.yml"
    with open(cli_template_path, "w") as f:
        yaml.dump(cli_tool_template_data, f, default_flow_style=False)

    # Write generic project template
    generic_template = {
        "name": "generic-project",
        "version": "1.0",
        "description": "Generic project template",
        "structure": [
            {"type": "directory", "path": "src"},
            {"type": "directory", "path": "docs"},
        ],
        "files": [
            {"path": "README.md", "content": "# {{title}}\n"},
        ],
    }
    generic_path = templates_dir / "generic" / "project.yml"
    with open(generic_path, "w") as f:
        yaml.dump(generic_template, f, default_flow_style=False)

    return temp_registry


@pytest.fixture
def user_templates_with_content(user_templates_dir, full_template_data) -> Path:
    """
    Create a user templates directory with template files.

    Includes:
    - custom/my-template.yml
    - academic/paper/latex.yml
    """
    # Create custom template
    (user_templates_dir / "custom").mkdir(parents=True)
    custom_path = user_templates_dir / "custom" / "my-template.yml"
    with open(custom_path, "w") as f:
        yaml.dump(full_template_data, f, default_flow_style=False)

    # Create academic paper template
    (user_templates_dir / "academic" / "paper").mkdir(parents=True)
    academic_template = {
        "name": "academic-paper-latex",
        "version": "1.0",
        "description": "LaTeX academic paper template",
        "author": "academic-templates",
        "variables": [
            {"name": "title", "source": "entity"},
            {"name": "author", "source": "prompt", "default": "Author Name"},
        ],
        "structure": [
            {"type": "directory", "path": "sections"},
            {"type": "directory", "path": "figures"},
        ],
        "files": [
            {
                "path": "main.tex",
                "content": "\\documentclass{article}\n\\title{{{title}}}\n\\begin{document}\n\\maketitle\n\\end{document}\n",
            },
        ],
    }
    academic_path = user_templates_dir / "academic" / "paper" / "latex.yml"
    with open(academic_path, "w") as f:
        yaml.dump(academic_template, f, default_flow_style=False)

    return user_templates_dir


@pytest.fixture
def template_with_assets(tmp_path, full_template_data) -> Generator[Path, None, None]:
    """
    Create a template directory with template file and assets.

    Useful for testing copy operations.
    """
    template_dir = tmp_path / "template_with_assets"
    template_dir.mkdir(parents=True)

    # Create assets directory
    assets_dir = template_dir / "assets"
    assets_dir.mkdir()

    # Create LICENSE asset
    (assets_dir / "LICENSE").write_text("MIT License\n\nCopyright (c) 2024\n")

    # Create another asset
    (assets_dir / "config.toml.tmpl").write_text(
        "[project]\nname = \"{{id}}\"\nversion = \"0.1.0\"\n"
    )

    # Update template data to reference assets
    template_data = full_template_data.copy()
    template_data["copy"] = [
        {"source": "assets/LICENSE", "destination": "LICENSE"},
        {"source": "assets/config.toml.tmpl", "destination": "config.toml"},
    ]

    # Write template file
    template_path = template_dir / "template.yml"
    with open(template_path, "w") as f:
        yaml.dump(template_data, f, default_flow_style=False)

    yield template_dir

    # Clean up
    if template_dir.exists():
        shutil.rmtree(template_dir)


@pytest.fixture
def template_with_file_references(tmp_path) -> Generator[Path, None, None]:
    """
    Create a template that references external template files for content.

    Useful for testing the 'template' field in file entries.
    """
    template_dir = tmp_path / "template_with_refs"
    template_dir.mkdir(parents=True)

    # Create template content files
    (template_dir / "gitignore" / "python.txt").mkdir(parents=True, exist_ok=False)
    # Correct the path - gitignore directory then file
    gitignore_dir = template_dir / "gitignore"
    gitignore_dir.mkdir(parents=True, exist_ok=True)
    (gitignore_dir / "python.txt").write_text(
        "__pycache__/\n*.py[cod]\n*.egg-info/\ndist/\nbuild/\n.venv/\n"
    )

    (template_dir / "readme.txt").write_text(
        "# {{title}}\n\n{{description}}\n\n## Usage\n\nTODO\n"
    )

    # Create template definition that references these files
    template_data = {
        "name": "template-with-refs",
        "version": "1.0",
        "variables": [
            {"name": "title", "source": "entity"},
            {"name": "description", "source": "entity"},
        ],
        "structure": [
            {"type": "directory", "path": "src"},
        ],
        "files": [
            {"path": ".gitignore", "template": "gitignore/python.txt"},
            {"path": "README.md", "template": "readme.txt"},
        ],
    }

    template_path = template_dir / "template.yml"
    with open(template_path, "w") as f:
        yaml.dump(template_data, f, default_flow_style=False)

    yield template_dir

    # Clean up
    if template_dir.exists():
        shutil.rmtree(template_dir)


@pytest.fixture
def empty_template_file(tmp_path) -> Generator[Path, None, None]:
    """Create an empty template YAML file for error testing."""
    template_path = tmp_path / "empty_template.yml"
    template_path.write_text("")

    yield template_path

    if template_path.exists():
        template_path.unlink()


@pytest.fixture
def invalid_yaml_file(tmp_path) -> Generator[Path, None, None]:
    """Create a file with invalid YAML content for error testing."""
    invalid_path = tmp_path / "invalid.yml"
    invalid_path.write_text("{ invalid yaml [content")

    yield invalid_path

    if invalid_path.exists():
        invalid_path.unlink()


@pytest.fixture
def category_with_variant() -> str:
    """Return a category string with variant notation."""
    return "software.dev/cli-tool.johndoe/latex-v2"


@pytest.fixture
def category_without_variant() -> str:
    """Return a category string without variant notation."""
    return "software.dev/cli-tool"


@pytest.fixture
def prompt_values() -> Dict[str, Any]:
    """Return sample prompt values for testing prompt variable resolution."""
    return {
        "author_name": "Test Author",
        "license_type": "Apache-2.0",
        "copyright_year": "2024",
    }


# Helper function fixtures for common test operations


@pytest.fixture
def create_template_file(tmp_path):
    """
    Factory fixture to create template files with custom data.

    Usage:
        def test_something(create_template_file):
            template_path = create_template_file({"name": "test", "version": "1.0"})
    """

    def _create_template_file(
        template_data: Dict[str, Any],
        filename: str = "template.yml",
        subdir: str = None,
    ) -> Path:
        if subdir:
            target_dir = tmp_path / subdir
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = tmp_path

        template_path = target_dir / filename
        with open(template_path, "w") as f:
            yaml.dump(template_data, f, default_flow_style=False)

        return template_path

    return _create_template_file


@pytest.fixture
def verify_scaffold_output():
    """
    Factory fixture to verify scaffolded output structure.

    Usage:
        def test_scaffold(verify_scaffold_output, output_dir):
            # ... perform scaffolding ...
            verify_scaffold_output(
                output_dir,
                expected_dirs=["src", "tests"],
                expected_files=["README.md", "pyproject.toml"]
            )
    """

    def _verify_scaffold_output(
        output_path: Path,
        expected_dirs: list = None,
        expected_files: list = None,
        unexpected_paths: list = None,
    ):
        expected_dirs = expected_dirs or []
        expected_files = expected_files or []
        unexpected_paths = unexpected_paths or []

        # Check expected directories exist
        for dir_path in expected_dirs:
            full_path = output_path / dir_path
            assert full_path.exists(), f"Expected directory not found: {dir_path}"
            assert full_path.is_dir(), f"Path is not a directory: {dir_path}"

        # Check expected files exist
        for file_path in expected_files:
            full_path = output_path / file_path
            assert full_path.exists(), f"Expected file not found: {file_path}"
            assert full_path.is_file(), f"Path is not a file: {file_path}"

        # Check unexpected paths don't exist
        for path in unexpected_paths:
            full_path = output_path / path
            assert not full_path.exists(), f"Unexpected path found: {path}"

    return _verify_scaffold_output


@pytest.fixture
def git_is_available() -> bool:
    """Check if Git is available on the system."""
    try:
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@pytest.fixture
def skip_without_git(git_is_available):
    """Skip test if Git is not available."""
    if not git_is_available:
        pytest.skip("Git is not available")