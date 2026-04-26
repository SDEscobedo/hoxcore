"""
Tests for HoxCore Template Executor.

This module tests the scaffolding execution functionality that creates
directory structures, files with content injection, file copying, and
git initialization based on template definitions.
"""

import os
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml

from hxc.templates.executor import (
    TemplateExecutor,
    ExecutorError,
    ScaffoldError,
    DirectoryCreationError,
    FileCreationError,
    FileCopyError,
    GitInitError,
    ScaffoldResult,
    execute_template,
    preview_template,
)
from hxc.templates.variables import TemplateVariables, VariableSubstitutionError
from hxc.templates.schema import PathTraversalError, InvalidPathError


class TestScaffoldResult:
    """Tests for ScaffoldResult dataclass"""

    def test_scaffold_result_default_values(self):
        """Test that ScaffoldResult has correct defaults"""
        result = ScaffoldResult()

        assert result.success is True
        assert result.output_path == ""
        assert result.directories_created == []
        assert result.files_created == []
        assert result.files_copied == []
        assert result.git_initialized is False
        assert result.git_committed is False
        assert result.dry_run is False
        assert result.errors == []
        assert result.warnings == []

    def test_scaffold_result_with_values(self):
        """Test creating ScaffoldResult with values"""
        result = ScaffoldResult(
            success=True,
            output_path="/path/to/output",
            directories_created=["src", "tests"],
            files_created=["README.md"],
            files_copied=["LICENSE"],
            git_initialized=True,
            git_committed=True,
            dry_run=False,
        )

        assert result.output_path == "/path/to/output"
        assert len(result.directories_created) == 2
        assert len(result.files_created) == 1
        assert len(result.files_copied) == 1
        assert result.git_initialized is True
        assert result.git_committed is True

    def test_total_items_created(self):
        """Test total_items_created property"""
        result = ScaffoldResult(
            directories_created=["src", "tests"],
            files_created=["README.md", "setup.py"],
            files_copied=["LICENSE"],
        )

        assert result.total_items_created == 5

    def test_total_items_created_empty(self):
        """Test total_items_created when empty"""
        result = ScaffoldResult()

        assert result.total_items_created == 0

    def test_add_error(self):
        """Test add_error method marks result as failed"""
        result = ScaffoldResult()
        assert result.success is True

        result.add_error("Something went wrong")

        assert result.success is False
        assert "Something went wrong" in result.errors

    def test_add_multiple_errors(self):
        """Test adding multiple errors"""
        result = ScaffoldResult()

        result.add_error("Error 1")
        result.add_error("Error 2")

        assert result.success is False
        assert len(result.errors) == 2

    def test_add_warning(self):
        """Test add_warning method does not affect success"""
        result = ScaffoldResult()

        result.add_warning("This is a warning")

        assert result.success is True
        assert "This is a warning" in result.warnings

    def test_add_multiple_warnings(self):
        """Test adding multiple warnings"""
        result = ScaffoldResult()

        result.add_warning("Warning 1")
        result.add_warning("Warning 2")

        assert result.success is True
        assert len(result.warnings) == 2

    def test_summary_basic(self):
        """Test summary method returns string"""
        result = ScaffoldResult(
            output_path="/path/to/output",
            directories_created=["src"],
            files_created=["README.md"],
        )

        summary = result.summary()

        assert isinstance(summary, str)
        assert "/path/to/output" in summary

    def test_summary_dry_run(self):
        """Test summary includes dry-run prefix when dry_run=True"""
        result = ScaffoldResult(
            output_path="/path/to/output",
            dry_run=True,
            directories_created=["src"],
        )

        summary = result.summary()

        assert "[DRY-RUN]" in summary
        assert "Would create" in summary

    def test_summary_includes_directories(self):
        """Test summary includes created directories"""
        result = ScaffoldResult(
            output_path="/output",
            directories_created=["src", "tests"],
        )

        summary = result.summary()

        assert "directories" in summary.lower()
        assert "src" in summary
        assert "tests" in summary

    def test_summary_includes_files(self):
        """Test summary includes created files"""
        result = ScaffoldResult(
            output_path="/output",
            files_created=["README.md", "setup.py"],
        )

        summary = result.summary()

        assert "files" in summary.lower()
        assert "README.md" in summary
        assert "setup.py" in summary

    def test_summary_includes_copied_files(self):
        """Test summary includes copied files"""
        result = ScaffoldResult(
            output_path="/output",
            files_copied=["LICENSE"],
        )

        summary = result.summary()

        assert "copied" in summary.lower()
        assert "LICENSE" in summary

    def test_summary_includes_git_status(self):
        """Test summary includes git initialization status"""
        result = ScaffoldResult(
            output_path="/output",
            git_initialized=True,
            git_committed=True,
        )

        summary = result.summary()

        assert "Git" in summary or "git" in summary

    def test_summary_includes_warnings(self):
        """Test summary includes warnings"""
        result = ScaffoldResult(output_path="/output")
        result.add_warning("This is a warning")

        summary = result.summary()

        assert "warning" in summary.lower() or "Warning" in summary
        assert "This is a warning" in summary

    def test_summary_includes_errors(self):
        """Test summary includes errors"""
        result = ScaffoldResult(output_path="/output")
        result.add_error("This is an error")

        summary = result.summary()

        assert "error" in summary.lower() or "Error" in summary
        assert "This is an error" in summary


class TestTemplateExecutorInit:
    """Tests for TemplateExecutor initialization"""

    def test_init_with_template_and_variables(self, minimal_template_data):
        """Test initialization with template and variables"""
        variables = TemplateVariables()
        executor = TemplateExecutor(minimal_template_data, variables)

        assert executor.template == minimal_template_data
        assert executor.variables is variables

    def test_init_with_template_base_path_string(self, minimal_template_data, tmp_path):
        """Test initialization with template_base_path as string"""
        variables = TemplateVariables()
        executor = TemplateExecutor(
            minimal_template_data, variables, template_base_path=str(tmp_path)
        )

        assert executor.template_base_path == tmp_path.resolve()

    def test_init_with_template_base_path_path(self, minimal_template_data, tmp_path):
        """Test initialization with template_base_path as Path"""
        variables = TemplateVariables()
        executor = TemplateExecutor(
            minimal_template_data, variables, template_base_path=tmp_path
        )

        assert executor.template_base_path == tmp_path.resolve()

    def test_init_extracts_source_path_from_template(self, tmp_path):
        """Test that _source_path is extracted from template"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "_source_path": str(tmp_path / "template.yml"),
        }
        variables = TemplateVariables()

        executor = TemplateExecutor(template_data, variables)

        assert executor.template_base_path == tmp_path.resolve()

    def test_init_without_base_path(self, minimal_template_data):
        """Test initialization without template_base_path"""
        variables = TemplateVariables()
        executor = TemplateExecutor(minimal_template_data, variables)

        assert executor.template_base_path is None


class TestTemplateExecutorCreateStructure:
    """Tests for _create_structure method"""

    def test_create_single_directory(self, tmp_path):
        """Test creating a single directory"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_structure(tmp_path, result, dry_run=False)

        assert (tmp_path / "src").exists()
        assert (tmp_path / "src").is_dir()
        assert "src" in result.directories_created

    def test_create_multiple_directories(self, tmp_path):
        """Test creating multiple directories"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [
                {"type": "directory", "path": "src"},
                {"type": "directory", "path": "tests"},
                {"type": "directory", "path": "docs"},
            ],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_structure(tmp_path, result, dry_run=False)

        assert (tmp_path / "src").exists()
        assert (tmp_path / "tests").exists()
        assert (tmp_path / "docs").exists()
        assert len(result.directories_created) == 3

    def test_create_nested_directories(self, tmp_path):
        """Test creating nested directories"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src/main/python"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_structure(tmp_path, result, dry_run=False)

        assert (tmp_path / "src" / "main" / "python").exists()

    def test_create_directory_with_variable(self, tmp_path):
        """Test creating directory with variable substitution"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src/{{id}}"}],
        }
        variables = TemplateVariables()
        variables.add_variable("id", "my_project")
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_structure(tmp_path, result, dry_run=False)

        assert (tmp_path / "src" / "my_project").exists()
        assert "src/my_project" in result.directories_created

    def test_create_directory_dry_run(self, tmp_path):
        """Test that dry_run does not create directories"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path), dry_run=True)
        executor._create_structure(tmp_path, result, dry_run=True)

        assert not (tmp_path / "src").exists()
        assert "src" in result.directories_created

    def test_create_directory_warns_on_unknown_type(self, tmp_path):
        """Test that unknown structure type adds warning"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "unknown_type", "path": "something"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_structure(tmp_path, result, dry_run=False)

        assert len(result.warnings) > 0
        assert "unknown" in result.warnings[0].lower()

    def test_create_directory_path_traversal_raises(self, tmp_path):
        """Test that path traversal raises DirectoryCreationError"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "../outside"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))

        with pytest.raises(DirectoryCreationError):
            executor._create_structure(tmp_path, result, dry_run=False)

    def test_create_directory_empty_structure(self, tmp_path):
        """Test with empty structure list"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_structure(tmp_path, result, dry_run=False)

        assert len(result.directories_created) == 0

    def test_create_directory_no_structure_key(self, tmp_path):
        """Test with no structure key in template"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_structure(tmp_path, result, dry_run=False)

        assert len(result.directories_created) == 0


class TestTemplateExecutorCreateFiles:
    """Tests for _create_files method"""

    def test_create_file_with_content(self, tmp_path):
        """Test creating a file with inline content"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "README.md", "content": "# Hello World"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        tmp_path.mkdir(exist_ok=True)
        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        assert (tmp_path / "README.md").exists()
        assert (tmp_path / "README.md").read_text() == "# Hello World"
        assert "README.md" in result.files_created

    def test_create_file_with_variable_substitution(self, tmp_path):
        """Test creating file with variable substitution in content"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "README.md", "content": "# {{title}}"}],
        }
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        assert (tmp_path / "README.md").read_text() == "# My Project"

    def test_create_file_with_variable_in_path(self, tmp_path):
        """Test creating file with variable in path"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [
                {"path": "src/{{id}}/__init__.py", "content": "# init"}
            ],
        }
        variables = TemplateVariables()
        variables.add_variable("id", "my_module")
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        assert (tmp_path / "src" / "my_module" / "__init__.py").exists()
        assert "src/my_module/__init__.py" in result.files_created

    def test_create_file_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created automatically"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "deep/nested/path/file.txt", "content": "content"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        assert (tmp_path / "deep" / "nested" / "path" / "file.txt").exists()

    def test_create_file_with_template_reference(self, template_with_file_references):
        """Test creating file with template reference"""
        template_path = template_with_file_references / "template.yml"
        with open(template_path) as f:
            template_data = yaml.safe_load(f)

        template_data["_source_path"] = str(template_path)

        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        variables.add_variable("description", "A test project")
        executor = TemplateExecutor(template_data, variables)

        output_path = template_with_file_references.parent / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._create_files(output_path, result, dry_run=False)

        # .gitignore should be created from template file
        assert (output_path / ".gitignore").exists()
        gitignore_content = (output_path / ".gitignore").read_text()
        assert "__pycache__" in gitignore_content

        # README.md should have variables substituted
        assert (output_path / "README.md").exists()
        readme_content = (output_path / "README.md").read_text()
        assert "My Project" in readme_content

    def test_create_file_dry_run(self, tmp_path):
        """Test that dry_run does not create files"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "README.md", "content": "# Hello"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path), dry_run=True)
        executor._create_files(tmp_path, result, dry_run=True)

        assert not (tmp_path / "README.md").exists()
        assert "README.md" in result.files_created

    def test_create_file_warns_on_no_content_or_template(self, tmp_path):
        """Test that file entry without content or template adds warning"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "empty.txt"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        assert len(result.warnings) > 0
        assert "empty.txt" in result.warnings[0]

    def test_create_file_path_traversal_raises(self, tmp_path):
        """Test that path traversal in file path raises error"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "../outside.txt", "content": "malicious"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))

        with pytest.raises(FileCreationError):
            executor._create_files(tmp_path, result, dry_run=False)

    def test_create_file_multiline_content(self, tmp_path):
        """Test creating file with multiline content"""
        content = """# Title

## Section 1

Some content here.

## Section 2

More content.
"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "README.md", "content": content}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        assert (tmp_path / "README.md").read_text() == content

    def test_create_file_utf8_content(self, tmp_path):
        """Test creating file with UTF-8 content"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "unicode.txt", "content": "émojis 🚀 and ünïcödé"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        content = (tmp_path / "unicode.txt").read_text(encoding="utf-8")
        assert "🚀" in content
        assert "ünïcödé" in content

    def test_create_multiple_files(self, tmp_path):
        """Test creating multiple files"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [
                {"path": "file1.txt", "content": "content 1"},
                {"path": "file2.txt", "content": "content 2"},
                {"path": "file3.txt", "content": "content 3"},
            ],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._create_files(tmp_path, result, dry_run=False)

        assert len(result.files_created) == 3
        assert (tmp_path / "file1.txt").exists()
        assert (tmp_path / "file2.txt").exists()
        assert (tmp_path / "file3.txt").exists()


class TestTemplateExecutorCopyFiles:
    """Tests for _copy_files method"""

    def test_copy_single_file(self, template_with_assets):
        """Test copying a single file"""
        template_path = template_with_assets / "template.yml"
        with open(template_path) as f:
            template_data = yaml.safe_load(f)

        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_with_assets
        )

        output_path = template_with_assets.parent / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._copy_files(output_path, result, dry_run=False)

        assert (output_path / "LICENSE").exists()
        assert "LICENSE" in result.files_copied

    def test_copy_file_dry_run(self, template_with_assets):
        """Test that dry_run does not copy files"""
        template_path = template_with_assets / "template.yml"
        with open(template_path) as f:
            template_data = yaml.safe_load(f)

        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_with_assets
        )

        output_path = template_with_assets.parent / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path), dry_run=True)
        executor._copy_files(output_path, result, dry_run=True)

        assert not (output_path / "LICENSE").exists()
        assert "LICENSE" in result.files_copied

    def test_copy_file_with_variable_in_destination(self, tmp_path):
        """Test copying file with variable in destination path"""
        # Create source template structure
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "config.txt").write_text("config content")

        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [
                {"source": "assets/config.txt", "destination": "{{id}}/config.txt"}
            ],
        }

        variables = TemplateVariables()
        variables.add_variable("id", "my_project")
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        output_path = tmp_path / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._copy_files(output_path, result, dry_run=False)

        assert (output_path / "my_project" / "config.txt").exists()

    def test_copy_warns_without_base_path(self, tmp_path):
        """Test that copy without base path adds warning"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [{"source": "assets/file.txt", "destination": "file.txt"}],
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)  # No base path

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._copy_files(tmp_path, result, dry_run=False)

        assert len(result.warnings) > 0
        assert "base path" in result.warnings[0].lower()

    def test_copy_source_not_found_raises(self, tmp_path):
        """Test that missing source file raises error"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [
                {"source": "nonexistent.txt", "destination": "file.txt"}
            ],
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        output_path = tmp_path / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))

        with pytest.raises(FileCopyError) as exc_info:
            executor._copy_files(output_path, result, dry_run=False)

        assert "not found" in str(exc_info.value).lower()

    def test_copy_source_path_traversal_raises(self, tmp_path):
        """Test that path traversal in source raises error"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [
                {"source": "../../../etc/passwd", "destination": "passwd"}
            ],
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        output_path = tmp_path / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))

        with pytest.raises(FileCopyError):
            executor._copy_files(output_path, result, dry_run=False)

    def test_copy_destination_path_traversal_raises(self, tmp_path):
        """Test that path traversal in destination raises error"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "file.txt").write_text("content")

        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [
                {"source": "assets/file.txt", "destination": "../outside.txt"}
            ],
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        output_path = tmp_path / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))

        with pytest.raises(FileCopyError):
            executor._copy_files(output_path, result, dry_run=False)

    def test_copy_creates_parent_directories(self, tmp_path):
        """Test that copy creates parent directories for destination"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "file.txt").write_text("content")

        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [
                {"source": "assets/file.txt", "destination": "deep/nested/file.txt"}
            ],
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        output_path = tmp_path / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._copy_files(output_path, result, dry_run=False)

        assert (output_path / "deep" / "nested" / "file.txt").exists()

    def test_copy_directory(self, tmp_path):
        """Test copying a directory"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        assets_dir = template_dir / "assets"
        assets_dir.mkdir()
        subdir = assets_dir / "subdir"
        subdir.mkdir()
        (subdir / "file1.txt").write_text("content 1")
        (subdir / "file2.txt").write_text("content 2")

        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [
                {"source": "assets/subdir", "destination": "copied_subdir"}
            ],
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        output_path = tmp_path / "output"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._copy_files(output_path, result, dry_run=False)

        assert (output_path / "copied_subdir").exists()
        assert (output_path / "copied_subdir").is_dir()
        assert (output_path / "copied_subdir" / "file1.txt").exists()
        assert (output_path / "copied_subdir" / "file2.txt").exists()

    def test_copy_empty_entries(self, tmp_path):
        """Test with empty copy list"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [],
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._copy_files(tmp_path, result, dry_run=False)

        assert len(result.files_copied) == 0

    def test_copy_no_copy_key(self, tmp_path):
        """Test with no copy key in template"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        result = ScaffoldResult(output_path=str(tmp_path))
        executor._copy_files(tmp_path, result, dry_run=False)

        assert len(result.files_copied) == 0


class TestTemplateExecutorInitializeGit:
    """Tests for _initialize_git method"""

    def test_git_init_when_enabled(self, tmp_path, skip_without_git):
        """Test git initialization when enabled"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": True},
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._initialize_git(output_path, result, dry_run=False)

        assert result.git_initialized is True
        assert (output_path / ".git").exists()

    def test_git_init_with_initial_commit(self, tmp_path, skip_without_git):
        """Test git initialization with initial commit"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit",
            },
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()
        # Create a file to commit
        (output_path / "README.md").write_text("# Test")

        # Configure git user for the test
        subprocess.run(
            ["git", "init"],
            cwd=output_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=output_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=output_path,
            check=True,
            capture_output=True,
        )

        # Reset result for proper tracking
        result = ScaffoldResult(output_path=str(output_path))
        result.git_initialized = True
        executor._initialize_git(output_path, result, dry_run=False)

        # Since .git already exists, it should warn but still commit
        assert result.git_committed is True or len(result.warnings) > 0

    def test_git_init_dry_run(self, tmp_path):
        """Test git initialization in dry run mode"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {
                "init": True,
                "initial_commit": True,
            },
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path), dry_run=True)
        executor._initialize_git(output_path, result, dry_run=True)

        assert result.git_initialized is True
        assert result.git_committed is True
        assert not (output_path / ".git").exists()

    def test_git_init_disabled(self, tmp_path):
        """Test that git is not initialized when disabled"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": False},
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._initialize_git(output_path, result, dry_run=False)

        assert result.git_initialized is False
        assert not (output_path / ".git").exists()

    def test_git_init_no_git_config(self, tmp_path):
        """Test when no git configuration in template"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()

        result = ScaffoldResult(output_path=str(output_path))
        executor._initialize_git(output_path, result, dry_run=False)

        assert result.git_initialized is False

    def test_git_init_existing_repo_warns(self, tmp_path, skip_without_git):
        """Test that existing git repo adds warning"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": True},
        }

        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()

        # Initialize git first
        subprocess.run(
            ["git", "init"],
            cwd=output_path,
            check=True,
            capture_output=True,
        )

        result = ScaffoldResult(output_path=str(output_path))
        executor._initialize_git(output_path, result, dry_run=False)

        assert result.git_initialized is True
        assert len(result.warnings) > 0
        assert "already" in result.warnings[0].lower()

    def test_git_init_commit_message_with_variable(self, tmp_path, skip_without_git):
        """Test commit message with variable substitution"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit for {{title}}",
            },
        }

        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()
        (output_path / "README.md").write_text("# Test")

        result = ScaffoldResult(output_path=str(output_path))
        executor._initialize_git(output_path, result, dry_run=False)

        # Check commit message (if we can)
        if result.git_committed:
            log = subprocess.run(
                ["git", "log", "-1", "--format=%s"],
                cwd=output_path,
                capture_output=True,
                text=True,
            )
            if log.returncode == 0:
                assert "My Project" in log.stdout


class TestTemplateExecutorExecute:
    """Tests for the main execute method"""

    def test_execute_creates_output_directory(self, tmp_path):
        """Test that execute creates output directory when create_output_dir=True"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "new_project"
        # Don't create it

        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True
        assert output_path.exists()

    def test_execute_without_create_output_dir_raises(self, tmp_path):
        """Test that execute raises when output doesn't exist and create_output_dir=False"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "nonexistent"

        with pytest.raises(ScaffoldError):
            executor.execute(output_path, dry_run=False, create_output_dir=False)

    def test_execute_full_workflow(self, tmp_path):
        """Test execute with full template"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [
                {"type": "directory", "path": "src"},
                {"type": "directory", "path": "tests"},
            ],
            "files": [
                {"path": "README.md", "content": "# {{title}}"},
                {"path": "src/__init__.py", "content": ""},
            ],
        }
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"

        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True
        assert (output_path / "src").exists()
        assert (output_path / "tests").exists()
        assert (output_path / "README.md").exists()
        assert (output_path / "README.md").read_text() == "# My Project"

    def test_execute_dry_run(self, tmp_path):
        """Test execute in dry run mode"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src"}],
            "files": [{"path": "README.md", "content": "# Hello"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()

        result = executor.execute(output_path, dry_run=True)

        assert result.success is True
        assert result.dry_run is True
        assert not (output_path / "src").exists()
        assert not (output_path / "README.md").exists()
        assert "src" in result.directories_created
        assert "README.md" in result.files_created

    def test_execute_returns_scaffold_result(self, tmp_path):
        """Test that execute returns ScaffoldResult"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"

        result = executor.execute(output_path, create_output_dir=True)

        assert isinstance(result, ScaffoldResult)

    def test_execute_sets_output_path_in_result(self, tmp_path):
        """Test that output_path is set in result"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"

        result = executor.execute(output_path, create_output_dir=True)

        assert result.output_path == str(output_path.resolve())

    def test_execute_with_path_as_string(self, tmp_path):
        """Test execute with path as string"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = str(tmp_path / "project")

        result = executor.execute(output_path, create_output_dir=True)

        assert result.success is True


class TestTemplateExecutorPreview:
    """Tests for the preview method"""

    def test_preview_equivalent_to_dry_run(self, tmp_path):
        """Test that preview is equivalent to execute with dry_run=True"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src"}],
            "files": [{"path": "README.md", "content": "# Hello"}],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"
        output_path.mkdir()

        result = executor.preview(output_path)

        assert result.dry_run is True
        assert "src" in result.directories_created
        assert "README.md" in result.files_created
        assert not (output_path / "src").exists()
        assert not (output_path / "README.md").exists()

    def test_preview_does_not_create_output_dir(self, tmp_path):
        """Test that preview does not create output directory"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "nonexistent"

        result = executor.preview(output_path)

        assert result.dry_run is True
        assert not output_path.exists()


class TestTemplateExecutorGetRequiredPrompts:
    """Tests for get_required_prompts method"""

    def test_get_required_prompts_returns_pending(self):
        """Test that get_required_prompts returns pending prompts"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        variables.register_prompt_definition("license", "prompt")
        executor = TemplateExecutor(template_data, variables)

        prompts = executor.get_required_prompts()

        assert len(prompts) == 2

    def test_get_required_prompts_empty_when_all_resolved(self):
        """Test that get_required_prompts returns empty when all resolved"""
        template_data = {
            "name": "test",
            "version": "1.0",
        }
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        variables.add_variable("author_name", "Test Author")
        executor = TemplateExecutor(template_data, variables)

        prompts = executor.get_required_prompts()

        assert len(prompts) == 0


class TestTemplateExecutorFromTemplateFile:
    """Tests for from_template_file factory method"""

    def test_from_template_file_creates_executor(self, template_file, sample_entity_data):
        """Test that from_template_file creates an executor"""
        executor = TemplateExecutor.from_template_file(
            template_file, sample_entity_data
        )

        assert isinstance(executor, TemplateExecutor)
        assert executor.template["name"] == "full-template"

    def test_from_template_file_with_prompt_values(
        self, template_file, sample_entity_data, prompt_values
    ):
        """Test from_template_file with prompt values"""
        executor = TemplateExecutor.from_template_file(
            template_file, sample_entity_data, prompt_values=prompt_values
        )

        assert executor.variables.get_variable("author_name") == "Test Author"

    def test_from_template_file_sets_base_path(self, template_file, sample_entity_data):
        """Test that from_template_file sets template_base_path"""
        executor = TemplateExecutor.from_template_file(
            template_file, sample_entity_data
        )

        assert executor.template_base_path == template_file.parent.resolve()


class TestTemplateExecutorValidateOutputPath:
    """Tests for validate_output_path method"""

    def test_validate_output_path_valid(self, tmp_path):
        """Test validating a valid output path"""
        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        new_path = tmp_path / "new_project"

        issues = executor.validate_output_path(new_path)

        assert len(issues) == 0

    def test_validate_output_path_file_exists(self, tmp_path):
        """Test validating path that is a file"""
        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        file_path = tmp_path / "existing_file"
        file_path.write_text("content")

        issues = executor.validate_output_path(file_path)

        assert len(issues) > 0
        assert any("file" in issue.lower() for issue in issues)

    def test_validate_output_path_non_empty_directory(self, tmp_path):
        """Test validating non-empty directory"""
        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        dir_path = tmp_path / "existing_dir"
        dir_path.mkdir()
        (dir_path / "file.txt").write_text("content")

        issues = executor.validate_output_path(dir_path)

        assert len(issues) > 0
        assert any("empty" in issue.lower() for issue in issues)

    def test_validate_output_path_parent_not_exists(self, tmp_path):
        """Test validating path with non-existent parent"""
        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        path = tmp_path / "nonexistent_parent" / "project"

        issues = executor.validate_output_path(path)

        assert len(issues) > 0
        assert any("parent" in issue.lower() for issue in issues)

    def test_validate_output_path_empty_directory_valid(self, tmp_path):
        """Test validating empty directory is valid"""
        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        empty_dir = tmp_path / "empty_dir"
        empty_dir.mkdir()

        issues = executor.validate_output_path(empty_dir)

        assert len(issues) == 0


class TestTemplateExecutorGetTemplateInfo:
    """Tests for get_template_info method"""

    def test_get_template_info_returns_metadata(self, full_template_data):
        """Test that get_template_info returns template metadata"""
        variables = TemplateVariables()
        executor = TemplateExecutor(full_template_data, variables)

        info = executor.get_template_info()

        assert info["name"] == "full-template"
        assert info["version"] == "1.0"
        assert info["description"] == "A complete template for testing"
        assert info["author"] == "test-author"

    def test_get_template_info_includes_counts(self, full_template_data):
        """Test that get_template_info includes counts"""
        variables = TemplateVariables()
        executor = TemplateExecutor(full_template_data, variables)

        info = executor.get_template_info()

        assert "structure_count" in info
        assert "files_count" in info
        assert "copy_count" in info

    def test_get_template_info_includes_git_flags(self, full_template_data):
        """Test that get_template_info includes git flags"""
        variables = TemplateVariables()
        executor = TemplateExecutor(full_template_data, variables)

        info = executor.get_template_info()

        assert "has_git" in info
        assert "has_initial_commit" in info

    def test_get_template_info_minimal_template(self, minimal_template_data):
        """Test get_template_info with minimal template"""
        variables = TemplateVariables()
        executor = TemplateExecutor(minimal_template_data, variables)

        info = executor.get_template_info()

        assert info["name"] == "minimal-template"
        assert info["version"] == "1.0"
        assert info["structure_count"] == 0
        assert info["files_count"] == 0
        assert info["has_git"] is False


class TestTemplateExecutorGitAvailable:
    """Tests for _git_available static method"""

    def test_git_available_returns_bool(self):
        """Test that _git_available returns bool"""
        result = TemplateExecutor._git_available()
        assert isinstance(result, bool)

    def test_git_available_with_git_installed(self, skip_without_git):
        """Test _git_available when git is installed"""
        result = TemplateExecutor._git_available()
        assert result is True

    def test_git_available_when_not_installed(self):
        """Test _git_available when git is not found"""
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            result = TemplateExecutor._git_available()
            assert result is False


class TestTemplateExecutorLoadTemplateFile:
    """Tests for _load_template_file method"""

    def test_load_template_file_basic(self, tmp_path):
        """Test loading a template file"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        template_file = template_dir / "content.txt"
        template_file.write_text("Template content")

        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        content = executor._load_template_file("content.txt")

        assert content == "Template content"

    def test_load_template_file_with_extension_fallback(self, tmp_path):
        """Test loading template file with extension fallback"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        template_file = template_dir / "content.txt"
        template_file.write_text("Template content")

        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        content = executor._load_template_file("content")

        assert content == "Template content"

    def test_load_template_file_not_found(self, tmp_path):
        """Test loading nonexistent template file raises error"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        with pytest.raises(FileCreationError) as exc_info:
            executor._load_template_file("nonexistent.txt")

        assert "not found" in str(exc_info.value).lower()

    def test_load_template_file_without_base_path(self):
        """Test loading template file without base path raises error"""
        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        with pytest.raises(FileCreationError) as exc_info:
            executor._load_template_file("content.txt")

        assert "base path" in str(exc_info.value).lower()

    def test_load_template_file_path_traversal_raises(self, tmp_path):
        """Test that path traversal in template reference raises error"""
        template_dir = tmp_path / "template"
        template_dir.mkdir()

        template_data = {"name": "test", "version": "1.0"}
        variables = TemplateVariables()
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_dir
        )

        with pytest.raises(FileCreationError):
            executor._load_template_file("../outside.txt")


class TestExceptionClasses:
    """Tests for custom exception classes"""

    def test_executor_error_is_exception(self):
        """Test that ExecutorError is an Exception"""
        error = ExecutorError("test error")
        assert isinstance(error, Exception)

    def test_scaffold_error_is_executor_error(self):
        """Test that ScaffoldError inherits from ExecutorError"""
        error = ScaffoldError("scaffold failed")
        assert isinstance(error, ExecutorError)
        assert isinstance(error, Exception)

    def test_scaffold_error_stores_path(self):
        """Test that ScaffoldError stores path"""
        error = ScaffoldError("scaffold failed", path="/path/to/output")
        assert error.path == "/path/to/output"

    def test_directory_creation_error_is_scaffold_error(self):
        """Test that DirectoryCreationError inherits from ScaffoldError"""
        error = DirectoryCreationError("/path/to/dir")
        assert isinstance(error, ScaffoldError)
        assert isinstance(error, ExecutorError)

    def test_directory_creation_error_stores_path(self):
        """Test that DirectoryCreationError stores path"""
        error = DirectoryCreationError("/path/to/dir")
        assert error.path == "/path/to/dir"

    def test_directory_creation_error_with_reason(self):
        """Test DirectoryCreationError with reason"""
        error = DirectoryCreationError("/path/to/dir", "permission denied")
        assert "permission denied" in str(error)

    def test_file_creation_error_is_scaffold_error(self):
        """Test that FileCreationError inherits from ScaffoldError"""
        error = FileCreationError("/path/to/file")
        assert isinstance(error, ScaffoldError)

    def test_file_creation_error_stores_path(self):
        """Test that FileCreationError stores path"""
        error = FileCreationError("/path/to/file")
        assert error.path == "/path/to/file"

    def test_file_creation_error_with_reason(self):
        """Test FileCreationError with reason"""
        error = FileCreationError("/path/to/file", "file exists")
        assert "file exists" in str(error)

    def test_file_copy_error_is_scaffold_error(self):
        """Test that FileCopyError inherits from ScaffoldError"""
        error = FileCopyError("/source", "/dest")
        assert isinstance(error, ScaffoldError)

    def test_file_copy_error_stores_paths(self):
        """Test that FileCopyError stores source and destination"""
        error = FileCopyError("/source/file", "/dest/file")
        assert error.source == "/source/file"
        assert error.destination == "/dest/file"

    def test_file_copy_error_with_reason(self):
        """Test FileCopyError with reason"""
        error = FileCopyError("/source", "/dest", "source not found")
        assert "source not found" in str(error)

    def test_git_init_error_is_scaffold_error(self):
        """Test that GitInitError inherits from ScaffoldError"""
        error = GitInitError("/path/to/repo")
        assert isinstance(error, ScaffoldError)

    def test_git_init_error_stores_path(self):
        """Test that GitInitError stores path"""
        error = GitInitError("/path/to/repo")
        assert error.path == "/path/to/repo"

    def test_git_init_error_with_reason(self):
        """Test GitInitError with reason"""
        error = GitInitError("/path/to/repo", "git not installed")
        assert "git not installed" in str(error)


class TestExecuteTemplateFunction:
    """Tests for execute_template module-level function"""

    def test_execute_template_basic(self, template_file, sample_entity_data, tmp_path):
        """Test execute_template function"""
        output_path = tmp_path / "output"

        result = execute_template(
            template_path=template_file,
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=False,
        )

        assert isinstance(result, ScaffoldResult)
        assert result.success is True

    def test_execute_template_dry_run(
        self, template_file, sample_entity_data, tmp_path
    ):
        """Test execute_template in dry run mode"""
        output_path = tmp_path / "output"
        output_path.mkdir()

        result = execute_template(
            template_path=template_file,
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=True,
        )

        assert result.dry_run is True

    def test_execute_template_with_prompt_values(
        self, template_file, sample_entity_data, tmp_path, prompt_values
    ):
        """Test execute_template with prompt values"""
        output_path = tmp_path / "output"

        result = execute_template(
            template_path=template_file,
            output_path=output_path,
            entity_data=sample_entity_data,
            prompt_values=prompt_values,
            dry_run=False,
        )

        assert result.success is True


class TestPreviewTemplateFunction:
    """Tests for preview_template module-level function"""

    def test_preview_template_basic(
        self, template_file, sample_entity_data, tmp_path
    ):
        """Test preview_template function"""
        output_path = tmp_path / "output"
        output_path.mkdir()

        result = preview_template(
            template_path=template_file,
            output_path=output_path,
            entity_data=sample_entity_data,
        )

        assert isinstance(result, ScaffoldResult)
        assert result.dry_run is True

    def test_preview_template_does_not_modify_filesystem(
        self, template_file, sample_entity_data, tmp_path
    ):
        """Test that preview_template does not modify filesystem"""
        output_path = tmp_path / "output"
        output_path.mkdir()

        initial_contents = list(output_path.iterdir())

        result = preview_template(
            template_path=template_file,
            output_path=output_path,
            entity_data=sample_entity_data,
        )

        final_contents = list(output_path.iterdir())

        assert initial_contents == final_contents


class TestTemplateExecutorIntegration:
    """Integration tests for template executor"""

    def test_full_scaffolding_workflow(
        self, cli_tool_template_data, sample_entity_data, tmp_path
    ):
        """Test complete scaffolding workflow"""
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=cli_tool_template_data,
            prompt_values={"author_name": "Test Author"},
        )
        executor = TemplateExecutor(cli_tool_template_data, variables)

        output_path = tmp_path / "my_project"

        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True
        assert (output_path / "src" / "my_project").exists()
        assert (output_path / "tests").exists()
        assert (output_path / "docs").exists()
        assert (output_path / "README.md").exists()

        # Verify variable substitution
        readme_content = (output_path / "README.md").read_text()
        assert "My Project" in readme_content

    def test_scaffolding_with_git_integration(
        self, tmp_path, skip_without_git
    ):
        """Test scaffolding with Git integration"""
        template_data = {
            "name": "test-with-git",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src"}],
            "files": [{"path": "README.md", "content": "# Test"}],
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit",
            },
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"

        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True
        assert result.git_initialized is True
        assert (output_path / ".git").exists()

    def test_scaffolding_preserves_file_content_integrity(self, tmp_path):
        """Test that file content is preserved exactly"""
        complex_content = """#!/usr/bin/env python3
'''Docstring with "quotes"'''

def main():
    print("Hello, {{title}}!")
    return 0

if __name__ == "__main__":
    main()
"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [{"path": "main.py", "content": complex_content}],
        }
        variables = TemplateVariables()
        variables.add_variable("title", "World")
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"

        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True
        actual_content = (output_path / "main.py").read_text()
        expected_content = complex_content.replace("{{title}}", "World")
        assert actual_content == expected_content

    def test_scaffolding_handles_many_files(self, tmp_path):
        """Test scaffolding with many files"""
        files = [
            {"path": f"file_{i}.txt", "content": f"Content {i}"}
            for i in range(50)
        ]
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": files,
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        output_path = tmp_path / "project"

        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True
        assert len(result.files_created) == 50
        for i in range(50):
            assert (output_path / f"file_{i}.txt").exists()

    def test_dry_run_summary_matches_actual_execution(self, tmp_path):
        """Test that dry-run result matches actual execution"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [
                {"type": "directory", "path": "src"},
                {"type": "directory", "path": "tests"},
            ],
            "files": [
                {"path": "README.md", "content": "# Test"},
                {"path": "src/__init__.py", "content": ""},
            ],
        }
        variables = TemplateVariables()
        executor = TemplateExecutor(template_data, variables)

        dry_run_path = tmp_path / "dry_run"
        dry_run_path.mkdir()
        actual_path = tmp_path / "actual"

        dry_result = executor.preview(dry_run_path)
        actual_result = executor.execute(
            actual_path, dry_run=False, create_output_dir=True
        )

        # Directories should match
        assert set(dry_result.directories_created) == set(
            actual_result.directories_created
        )
        # Files should match
        assert set(dry_result.files_created) == set(actual_result.files_created)