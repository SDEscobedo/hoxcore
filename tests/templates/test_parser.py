"""
Tests for HoxCore Template Parser.

This module tests the template YAML file loading, parsing, and validation
functionality that ensures template definitions are correctly processed.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from hxc.templates.parser import (
    TemplateParser,
    TemplateParserError,
    TemplateNotFoundError,
    TemplateLoadError,
)
from hxc.templates.schema import (
    InvalidTemplateError,
    MissingRequiredFieldError,
    PathTraversalError,
)


class TestTemplateParserInit:
    """Tests for TemplateParser initialization"""

    def test_init_default_strict_mode(self):
        """Test that strict mode is False by default"""
        parser = TemplateParser()
        assert parser.strict is False

    def test_init_with_strict_mode_true(self):
        """Test initialization with strict=True"""
        parser = TemplateParser(strict=True)
        assert parser.strict is True

    def test_init_with_strict_mode_false(self):
        """Test initialization with strict=False"""
        parser = TemplateParser(strict=False)
        assert parser.strict is False


class TestTemplateParserParse:
    """Tests for the parse() method that loads template files from disk"""

    def test_parse_valid_template_file(self, template_file, full_template_data):
        """Test parsing a valid template file"""
        parser = TemplateParser()
        result = parser.parse(template_file)

        assert result["name"] == full_template_data["name"]
        assert result["version"] == full_template_data["version"]
        assert "_source_path" in result

    def test_parse_minimal_template(self, create_template_file):
        """Test parsing a minimal valid template"""
        template_data = {
            "name": "minimal-template",
            "version": "1.0",
        }
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        result = parser.parse(template_path)

        assert result["name"] == "minimal-template"
        assert result["version"] == "1.0"

    def test_parse_template_with_all_sections(self, create_template_file):
        """Test parsing a template with all optional sections"""
        template_data = {
            "name": "complete-template",
            "version": "2.0",
            "description": "A complete template",
            "author": "test-author",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "year", "source": "system"},
            ],
            "structure": [
                {"type": "directory", "path": "src"},
                {"type": "directory", "path": "tests"},
            ],
            "files": [
                {"path": "README.md", "content": "# {{title}}"},
            ],
            "copy": [
                {"source": "assets/LICENSE", "destination": "LICENSE"},
            ],
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit",
            },
        }
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        result = parser.parse(template_path)

        assert result["name"] == "complete-template"
        assert result["version"] == "2.0"
        assert result["description"] == "A complete template"
        assert result["author"] == "test-author"
        assert len(result["variables"]) == 2
        assert len(result["structure"]) == 2
        assert len(result["files"]) == 1
        assert len(result["copy"]) == 1
        assert result["git"]["init"] is True

    def test_parse_adds_source_path_metadata(self, create_template_file):
        """Test that parse adds _source_path to the result"""
        template_data = {"name": "test", "version": "1.0"}
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        result = parser.parse(template_path)

        assert "_source_path" in result
        assert result["_source_path"] == str(template_path.resolve())

    def test_parse_nonexistent_file(self, tmp_path):
        """Test that parsing nonexistent file raises TemplateNotFoundError"""
        nonexistent_path = tmp_path / "nonexistent.yml"

        parser = TemplateParser()
        with pytest.raises(TemplateNotFoundError) as exc_info:
            parser.parse(nonexistent_path)

        assert "nonexistent.yml" in str(exc_info.value.path)

    def test_parse_directory_instead_of_file(self, tmp_path):
        """Test that parsing a directory raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse(tmp_path)

        assert "not a file" in str(exc_info.value)

    def test_parse_empty_file(self, empty_template_file):
        """Test that parsing empty file raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse(empty_template_file)

        assert "empty" in str(exc_info.value).lower()

    def test_parse_invalid_yaml(self, invalid_yaml_file):
        """Test that parsing invalid YAML raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse(invalid_yaml_file)

        assert "invalid YAML" in str(exc_info.value)

    def test_parse_template_missing_name(self, create_template_file):
        """Test that template missing name raises MissingRequiredFieldError"""
        template_data = {"version": "1.0"}
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            parser.parse(template_path)

        assert "name" in str(exc_info.value)

    def test_parse_template_missing_version(self, create_template_file):
        """Test that template missing version raises MissingRequiredFieldError"""
        template_data = {"name": "test-template"}
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            parser.parse(template_path)

        assert "version" in str(exc_info.value)

    def test_parse_template_with_path_traversal(self, create_template_file):
        """Test that template with path traversal raises PathTraversalError"""
        template_data = {
            "name": "malicious",
            "version": "1.0",
            "structure": [
                {"type": "directory", "path": "../outside"},
            ],
        }
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        with pytest.raises(PathTraversalError):
            parser.parse(template_path)

    def test_parse_handles_expanduser_in_path(self, tmp_path, monkeypatch):
        """Test that parse handles ~ in paths"""
        # Create a mock home directory
        mock_home = tmp_path / "mock_home"
        mock_home.mkdir()

        template_file = mock_home / "template.yml"
        template_data = {"name": "test", "version": "1.0"}
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        # Mock expanduser to use our mock home
        original_expanduser = Path.expanduser

        def mock_expanduser(path):
            path_str = str(path)
            if path_str.startswith("~"):
                return Path(str(mock_home) + path_str[1:])
            return original_expanduser(path)

        monkeypatch.setattr(Path, "expanduser", mock_expanduser)

        parser = TemplateParser()
        result = parser.parse(template_file)

        assert result["name"] == "test"

    def test_parse_utf8_content(self, create_template_file):
        """Test parsing template with UTF-8 content"""
        template_data = {
            "name": "utf8-template",
            "version": "1.0",
            "description": "Template with émojis 🚀 and ünïcödé",
        }
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        result = parser.parse(template_path)

        assert "émojis" in result["description"]
        assert "🚀" in result["description"]

    def test_parse_file_with_read_error(self, tmp_path):
        """Test that IO errors during read raise TemplateLoadError"""
        template_path = tmp_path / "template.yml"
        template_path.write_text("name: test\nversion: '1.0'")

        parser = TemplateParser()

        with patch("pathlib.Path.read_text", side_effect=IOError("Read failed")):
            with pytest.raises(TemplateLoadError) as exc_info:
                parser.parse(template_path)

            assert "cannot read file" in str(exc_info.value)


class TestTemplateParserParseString:
    """Tests for the parse_string() method"""

    def test_parse_string_valid_yaml(self):
        """Test parsing valid YAML string"""
        content = """
name: string-template
version: "1.0"
description: Parsed from string
"""
        parser = TemplateParser()
        result = parser.parse_string(content)

        assert result["name"] == "string-template"
        assert result["version"] == "1.0"
        assert result["description"] == "Parsed from string"

    def test_parse_string_with_source_path(self):
        """Test that source_path is used in error messages"""
        content = "name: test"  # Missing version

        parser = TemplateParser()
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            parser.parse_string(content, source_path="/path/to/template.yml")

        assert "version" in str(exc_info.value)

    def test_parse_string_empty_content(self):
        """Test parsing empty string raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse_string("")

        assert "empty" in str(exc_info.value).lower()

    def test_parse_string_whitespace_only(self):
        """Test parsing whitespace-only string raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse_string("   \n\n   ")

        assert "empty" in str(exc_info.value).lower()

    def test_parse_string_null_yaml(self):
        """Test parsing YAML that evaluates to null raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse_string("null")

        assert "empty" in str(exc_info.value).lower() or "null" in str(exc_info.value).lower()

    def test_parse_string_invalid_yaml(self):
        """Test parsing invalid YAML string raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse_string("{ invalid yaml [content")

        assert "invalid YAML" in str(exc_info.value)

    def test_parse_string_non_dict_yaml(self):
        """Test parsing YAML that is not a dict raises TemplateLoadError"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError) as exc_info:
            parser.parse_string("- item1\n- item2")

        assert "mapping" in str(exc_info.value).lower()

    def test_parse_string_validates_template(self):
        """Test that parse_string validates the template"""
        content = """
name: invalid-template
version: "1.0"
structure:
  - type: directory
    path: "../outside"
"""
        parser = TemplateParser()
        with pytest.raises(PathTraversalError):
            parser.parse_string(content)

    def test_parse_string_minimal_valid(self):
        """Test parsing minimal valid template string"""
        content = "name: minimal\nversion: '1.0'"

        parser = TemplateParser()
        result = parser.parse_string(content)

        assert result["name"] == "minimal"
        assert result["version"] == "1.0"

    def test_parse_string_with_all_sections(self):
        """Test parsing complete template from string"""
        content = """
name: complete
version: "1.0"
description: Complete template
author: tester
variables:
  - name: title
    source: entity
structure:
  - type: directory
    path: src
files:
  - path: README.md
    content: "# Hello"
copy:
  - source: assets/file.txt
    destination: file.txt
git:
  init: true
"""
        parser = TemplateParser()
        result = parser.parse_string(content)

        assert result["name"] == "complete"
        assert len(result["variables"]) == 1
        assert len(result["structure"]) == 1
        assert len(result["files"]) == 1
        assert len(result["copy"]) == 1
        assert result["git"]["init"] is True


class TestTemplateParserParseDict:
    """Tests for the parse_dict() method"""

    def test_parse_dict_valid(self):
        """Test validating a valid template dictionary"""
        template_data = {
            "name": "dict-template",
            "version": "1.0",
            "description": "From dictionary",
        }

        parser = TemplateParser()
        result = parser.parse_dict(template_data)

        assert result == template_data

    def test_parse_dict_returns_same_object(self):
        """Test that parse_dict returns the same dictionary"""
        template_data = {"name": "test", "version": "1.0"}

        parser = TemplateParser()
        result = parser.parse_dict(template_data)

        assert result is template_data

    def test_parse_dict_missing_name(self):
        """Test that missing name raises MissingRequiredFieldError"""
        template_data = {"version": "1.0"}

        parser = TemplateParser()
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            parser.parse_dict(template_data)

        assert "name" in str(exc_info.value)

    def test_parse_dict_missing_version(self):
        """Test that missing version raises MissingRequiredFieldError"""
        template_data = {"name": "test"}

        parser = TemplateParser()
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            parser.parse_dict(template_data)

        assert "version" in str(exc_info.value)

    def test_parse_dict_invalid_template(self):
        """Test that invalid template raises InvalidTemplateError"""
        template_data = {
            "name": "",  # Empty name
            "version": "1.0",
        }

        parser = TemplateParser()
        with pytest.raises(InvalidTemplateError):
            parser.parse_dict(template_data)

    def test_parse_dict_with_path_traversal(self):
        """Test that path traversal raises PathTraversalError"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [
                {"path": "../outside.txt", "content": "malicious"},
            ],
        }

        parser = TemplateParser()
        with pytest.raises(PathTraversalError):
            parser.parse_dict(template_data)


class TestTemplateParserStaticMethods:
    """Tests for static helper methods"""

    def test_get_template_metadata(self):
        """Test extracting metadata from template"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "description": "A test template",
            "author": "test-author",
            "structure": [{"type": "directory", "path": "src"}],
        }

        metadata = TemplateParser.get_template_metadata(template_data)

        assert metadata["name"] == "test-template"
        assert metadata["version"] == "1.0"
        assert metadata["description"] == "A test template"
        assert metadata["author"] == "test-author"
        assert "structure" not in metadata

    def test_get_template_metadata_partial(self):
        """Test extracting metadata when some fields missing"""
        template_data = {
            "name": "minimal",
            "version": "1.0",
        }

        metadata = TemplateParser.get_template_metadata(template_data)

        assert metadata["name"] == "minimal"
        assert metadata["version"] == "1.0"
        assert "description" not in metadata
        assert "author" not in metadata

    def test_get_variables(self):
        """Test extracting variables from template"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "year", "source": "system"},
            ],
        }

        variables = TemplateParser.get_variables(template_data)

        assert len(variables) == 2
        assert variables[0]["name"] == "title"
        assert variables[1]["name"] == "year"

    def test_get_variables_empty(self):
        """Test extracting variables when none defined"""
        template_data = {"name": "test", "version": "1.0"}

        variables = TemplateParser.get_variables(template_data)

        assert variables == []

    def test_get_structure(self):
        """Test extracting structure from template"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "structure": [
                {"type": "directory", "path": "src"},
                {"type": "directory", "path": "tests"},
            ],
        }

        structure = TemplateParser.get_structure(template_data)

        assert len(structure) == 2
        assert structure[0]["path"] == "src"
        assert structure[1]["path"] == "tests"

    def test_get_structure_empty(self):
        """Test extracting structure when none defined"""
        template_data = {"name": "test", "version": "1.0"}

        structure = TemplateParser.get_structure(template_data)

        assert structure == []

    def test_get_files(self):
        """Test extracting files from template"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "files": [
                {"path": "README.md", "content": "# Hello"},
                {"path": "setup.py", "template": "setup_template"},
            ],
        }

        files = TemplateParser.get_files(template_data)

        assert len(files) == 2
        assert files[0]["path"] == "README.md"
        assert files[1]["path"] == "setup.py"

    def test_get_files_empty(self):
        """Test extracting files when none defined"""
        template_data = {"name": "test", "version": "1.0"}

        files = TemplateParser.get_files(template_data)

        assert files == []

    def test_get_copy_entries(self):
        """Test extracting copy entries from template"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "copy": [
                {"source": "assets/LICENSE", "destination": "LICENSE"},
                {"source": "assets/config.toml", "destination": "config.toml"},
            ],
        }

        copy_entries = TemplateParser.get_copy_entries(template_data)

        assert len(copy_entries) == 2
        assert copy_entries[0]["source"] == "assets/LICENSE"
        assert copy_entries[1]["destination"] == "config.toml"

    def test_get_copy_entries_empty(self):
        """Test extracting copy entries when none defined"""
        template_data = {"name": "test", "version": "1.0"}

        copy_entries = TemplateParser.get_copy_entries(template_data)

        assert copy_entries == []

    def test_get_git_config(self):
        """Test extracting git config from template"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit",
            },
        }

        git_config = TemplateParser.get_git_config(template_data)

        assert git_config["init"] is True
        assert git_config["initial_commit"] is True
        assert git_config["commit_message"] == "Initial commit"

    def test_get_git_config_none(self):
        """Test extracting git config when not defined"""
        template_data = {"name": "test", "version": "1.0"}

        git_config = TemplateParser.get_git_config(template_data)

        assert git_config is None

    def test_has_git_init_true(self):
        """Test has_git_init returns True when init is True"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": True},
        }

        assert TemplateParser.has_git_init(template_data) is True

    def test_has_git_init_false(self):
        """Test has_git_init returns False when init is False"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": False},
        }

        assert TemplateParser.has_git_init(template_data) is False

    def test_has_git_init_no_git_section(self):
        """Test has_git_init returns False when no git section"""
        template_data = {"name": "test", "version": "1.0"}

        assert TemplateParser.has_git_init(template_data) is False

    def test_has_git_init_no_init_key(self):
        """Test has_git_init returns False when init key missing"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"initial_commit": True},
        }

        assert TemplateParser.has_git_init(template_data) is False

    def test_has_initial_commit_true(self):
        """Test has_initial_commit returns True when initial_commit is True"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": True, "initial_commit": True},
        }

        assert TemplateParser.has_initial_commit(template_data) is True

    def test_has_initial_commit_false(self):
        """Test has_initial_commit returns False when initial_commit is False"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": True, "initial_commit": False},
        }

        assert TemplateParser.has_initial_commit(template_data) is False

    def test_has_initial_commit_no_git_section(self):
        """Test has_initial_commit returns False when no git section"""
        template_data = {"name": "test", "version": "1.0"}

        assert TemplateParser.has_initial_commit(template_data) is False

    def test_get_commit_message(self):
        """Test extracting commit message from git config"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit from {{template_name}}",
            },
        }

        commit_message = TemplateParser.get_commit_message(template_data)

        assert commit_message == "Initial commit from {{template_name}}"

    def test_get_commit_message_none(self):
        """Test get_commit_message returns None when not defined"""
        template_data = {
            "name": "test",
            "version": "1.0",
            "git": {"init": True},
        }

        commit_message = TemplateParser.get_commit_message(template_data)

        assert commit_message is None

    def test_get_commit_message_no_git_section(self):
        """Test get_commit_message returns None when no git section"""
        template_data = {"name": "test", "version": "1.0"}

        commit_message = TemplateParser.get_commit_message(template_data)

        assert commit_message is None


class TestTemplateParserValidateMethods:
    """Tests for validation helper methods"""

    def test_validate_template_file_valid(self, template_file):
        """Test validating a valid template file returns True"""
        parser = TemplateParser()
        result = parser.validate_template_file(template_file)

        assert result is True

    def test_validate_template_file_not_found(self, tmp_path):
        """Test validating nonexistent file raises error"""
        parser = TemplateParser()
        with pytest.raises(TemplateNotFoundError):
            parser.validate_template_file(tmp_path / "nonexistent.yml")

    def test_validate_template_file_invalid(self, create_template_file):
        """Test validating invalid template raises error"""
        template_data = {"name": "test"}  # Missing version
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        with pytest.raises(MissingRequiredFieldError):
            parser.validate_template_file(template_path)

    def test_validate_template_string_valid(self):
        """Test validating valid template string returns True"""
        content = "name: test\nversion: '1.0'"

        parser = TemplateParser()
        result = parser.validate_template_string(content)

        assert result is True

    def test_validate_template_string_invalid(self):
        """Test validating invalid template string raises error"""
        content = "name: test"  # Missing version

        parser = TemplateParser()
        with pytest.raises(MissingRequiredFieldError):
            parser.validate_template_string(content)

    def test_validate_template_string_empty(self):
        """Test validating empty string raises error"""
        parser = TemplateParser()
        with pytest.raises(TemplateLoadError):
            parser.validate_template_string("")


class TestExceptionClasses:
    """Tests for custom exception classes"""

    def test_template_parser_error_is_exception(self):
        """Test that TemplateParserError is an Exception"""
        error = TemplateParserError("test error")
        assert isinstance(error, Exception)

    def test_template_not_found_error_is_parser_error(self):
        """Test that TemplateNotFoundError inherits from TemplateParserError"""
        error = TemplateNotFoundError("/path/to/template.yml")
        assert isinstance(error, TemplateParserError)
        assert isinstance(error, Exception)

    def test_template_not_found_error_stores_path(self):
        """Test that TemplateNotFoundError stores the path"""
        error = TemplateNotFoundError("/path/to/template.yml")
        assert error.path == "/path/to/template.yml"

    def test_template_not_found_error_message(self):
        """Test TemplateNotFoundError message includes path"""
        error = TemplateNotFoundError("/path/to/template.yml")
        assert "/path/to/template.yml" in str(error)
        assert "not found" in str(error).lower()

    def test_template_load_error_is_parser_error(self):
        """Test that TemplateLoadError inherits from TemplateParserError"""
        error = TemplateLoadError("/path/to/template.yml")
        assert isinstance(error, TemplateParserError)
        assert isinstance(error, Exception)

    def test_template_load_error_stores_path_and_reason(self):
        """Test that TemplateLoadError stores path and reason"""
        error = TemplateLoadError("/path/to/template.yml", "invalid YAML")
        assert error.path == "/path/to/template.yml"
        assert error.reason == "invalid YAML"

    def test_template_load_error_message_without_reason(self):
        """Test TemplateLoadError message without reason"""
        error = TemplateLoadError("/path/to/template.yml")
        assert "/path/to/template.yml" in str(error)
        assert "Failed to load" in str(error)

    def test_template_load_error_message_with_reason(self):
        """Test TemplateLoadError message with reason"""
        error = TemplateLoadError("/path/to/template.yml", "file is corrupted")
        assert "/path/to/template.yml" in str(error)
        assert "file is corrupted" in str(error)


class TestTemplateParserIntegration:
    """Integration tests for template parsing"""

    def test_parse_cli_tool_template(self, cli_tool_template_file, cli_tool_template_data):
        """Test parsing a realistic CLI tool template"""
        parser = TemplateParser()
        result = parser.parse(cli_tool_template_file)

        assert result["name"] == cli_tool_template_data["name"]
        assert result["version"] == cli_tool_template_data["version"]
        assert len(result["structure"]) == len(cli_tool_template_data["structure"])
        assert len(result["files"]) == len(cli_tool_template_data["files"])
        assert result["git"]["init"] is True

    def test_parse_template_from_registry(self, registry_with_templates):
        """Test parsing template from registry .hxc/templates/"""
        template_path = (
            registry_with_templates
            / ".hxc"
            / "templates"
            / "software.dev"
            / "cli-tool"
            / "default.yml"
        )

        parser = TemplateParser()
        result = parser.parse(template_path)

        assert result["name"] == "cli-tool-default"
        assert "structure" in result
        assert "files" in result

    def test_parse_template_with_variables_in_content(self, create_template_file):
        """Test parsing template with variables in file content"""
        template_data = {
            "name": "variable-template",
            "version": "1.0",
            "files": [
                {
                    "path": "README.md",
                    "content": "# {{title}}\n\nCreated by {{author_name}} on {{date}}",
                },
                {
                    "path": "src/{{id}}/__init__.py",
                    "content": '"""{{title}}"""\n__version__ = "{{version}}"',
                },
            ],
        }
        template_path = create_template_file(template_data)

        parser = TemplateParser()
        result = parser.parse(template_path)

        # Variables in content should be preserved as-is (not validated by parser)
        assert "{{title}}" in result["files"][0]["content"]
        assert "{{author_name}}" in result["files"][0]["content"]
        assert "{{id}}" in result["files"][1]["path"]

    def test_parse_template_with_multiline_content(self, create_template_file):
        """Test parsing template with multiline file content"""
        template_data = {
            "name": "multiline-template",
            "version": "1.0",
            "files": [
                {
                    "path": "README.md",
                    "content": """# {{title}}

## Description

{{description}}

## Installation