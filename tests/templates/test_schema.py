"""
Tests for HoxCore Template Schema validation.

This module tests the template validation schema that ensures template
definitions are correct, complete, and secure.
"""

import pytest

from hxc.templates.schema import (
    TEMPLATE_SCHEMA,
    TemplateSchemaError,
    validate_template,
    validate_structure_entry,
    validate_file_entry,
    validate_copy_entry,
    validate_variable_entry,
    validate_git_config,
    validate_path_security,
    InvalidTemplateError,
    MissingRequiredFieldError,
    InvalidPathError,
    PathTraversalError,
)


class TestTemplateSchema:
    """Tests for the template JSON schema definition"""

    def test_schema_has_required_fields(self):
        """Test that schema defines required fields"""
        assert "required" in TEMPLATE_SCHEMA
        assert "name" in TEMPLATE_SCHEMA["required"]
        assert "version" in TEMPLATE_SCHEMA["required"]

    def test_schema_defines_properties(self):
        """Test that schema defines expected properties"""
        properties = TEMPLATE_SCHEMA.get("properties", {})
        expected_properties = [
            "name",
            "version",
            "description",
            "author",
            "variables",
            "structure",
            "files",
            "copy",
            "git",
        ]
        for prop in expected_properties:
            assert prop in properties, f"Missing property: {prop}"

    def test_schema_name_is_string(self):
        """Test that name property is defined as string"""
        properties = TEMPLATE_SCHEMA.get("properties", {})
        assert properties["name"]["type"] == "string"

    def test_schema_version_is_string(self):
        """Test that version property is defined as string"""
        properties = TEMPLATE_SCHEMA.get("properties", {})
        assert properties["version"]["type"] == "string"

    def test_schema_variables_is_array(self):
        """Test that variables property is defined as array"""
        properties = TEMPLATE_SCHEMA.get("properties", {})
        assert properties["variables"]["type"] == "array"

    def test_schema_structure_is_array(self):
        """Test that structure property is defined as array"""
        properties = TEMPLATE_SCHEMA.get("properties", {})
        assert properties["structure"]["type"] == "array"

    def test_schema_files_is_array(self):
        """Test that files property is defined as array"""
        properties = TEMPLATE_SCHEMA.get("properties", {})
        assert properties["files"]["type"] == "array"

    def test_schema_git_is_object(self):
        """Test that git property is defined as object"""
        properties = TEMPLATE_SCHEMA.get("properties", {})
        assert properties["git"]["type"] == "object"


class TestValidateTemplate:
    """Tests for the validate_template function"""

    def test_validate_minimal_valid_template(self):
        """Test validating a minimal valid template"""
        template = {
            "name": "test-template",
            "version": "1.0",
        }
        result = validate_template(template)
        assert result is True

    def test_validate_full_template(self):
        """Test validating a complete template with all fields"""
        template = {
            "name": "full-template",
            "version": "1.0",
            "description": "A full template for testing",
            "author": "test-author",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "year", "source": "system", "format": "%Y"},
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
        result = validate_template(template)
        assert result is True

    def test_validate_template_missing_name(self):
        """Test that missing name field raises error"""
        template = {
            "version": "1.0",
        }
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_template(template)
        assert "name" in str(exc_info.value)

    def test_validate_template_missing_version(self):
        """Test that missing version field raises error"""
        template = {
            "name": "test-template",
        }
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_template(template)
        assert "version" in str(exc_info.value)

    def test_validate_template_empty_name(self):
        """Test that empty name raises error"""
        template = {
            "name": "",
            "version": "1.0",
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_template(template)
        assert "name" in str(exc_info.value).lower()

    def test_validate_template_invalid_name_type(self):
        """Test that non-string name raises error"""
        template = {
            "name": 123,
            "version": "1.0",
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_template(template)
        assert "name" in str(exc_info.value).lower()

    def test_validate_template_invalid_version_type(self):
        """Test that non-string version raises error"""
        template = {
            "name": "test-template",
            "version": 1.0,  # Should be string
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_template(template)
        assert "version" in str(exc_info.value).lower()

    def test_validate_template_invalid_variables_type(self):
        """Test that non-array variables raises error"""
        template = {
            "name": "test-template",
            "version": "1.0",
            "variables": "not-an-array",
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_template(template)
        assert "variables" in str(exc_info.value).lower()

    def test_validate_template_invalid_structure_type(self):
        """Test that non-array structure raises error"""
        template = {
            "name": "test-template",
            "version": "1.0",
            "structure": {"type": "directory"},
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_template(template)
        assert "structure" in str(exc_info.value).lower()

    def test_validate_template_invalid_files_type(self):
        """Test that non-array files raises error"""
        template = {
            "name": "test-template",
            "version": "1.0",
            "files": "not-an-array",
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_template(template)
        assert "files" in str(exc_info.value).lower()

    def test_validate_template_invalid_git_type(self):
        """Test that non-object git raises error"""
        template = {
            "name": "test-template",
            "version": "1.0",
            "git": True,
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_template(template)
        assert "git" in str(exc_info.value).lower()

    def test_validate_template_none_input(self):
        """Test that None input raises error"""
        with pytest.raises(InvalidTemplateError):
            validate_template(None)

    def test_validate_template_non_dict_input(self):
        """Test that non-dict input raises error"""
        with pytest.raises(InvalidTemplateError):
            validate_template("not a dict")

    def test_validate_template_empty_dict(self):
        """Test that empty dict raises error for missing required fields"""
        with pytest.raises(MissingRequiredFieldError):
            validate_template({})


class TestValidateStructureEntry:
    """Tests for structure entry validation"""

    def test_validate_directory_entry(self):
        """Test validating a directory structure entry"""
        entry = {"type": "directory", "path": "src/myproject"}
        result = validate_structure_entry(entry)
        assert result is True

    def test_validate_structure_missing_type(self):
        """Test that missing type raises error"""
        entry = {"path": "src"}
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_structure_entry(entry)
        assert "type" in str(exc_info.value)

    def test_validate_structure_missing_path(self):
        """Test that missing path raises error"""
        entry = {"type": "directory"}
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_structure_entry(entry)
        assert "path" in str(exc_info.value)

    def test_validate_structure_invalid_type_value(self):
        """Test that invalid type value raises error"""
        entry = {"type": "invalid", "path": "src"}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_structure_entry(entry)
        assert "type" in str(exc_info.value).lower()

    def test_validate_structure_empty_path(self):
        """Test that empty path raises error"""
        entry = {"type": "directory", "path": ""}
        with pytest.raises(InvalidPathError):
            validate_structure_entry(entry)

    def test_validate_structure_path_traversal(self):
        """Test that path traversal is rejected"""
        entry = {"type": "directory", "path": "../outside"}
        with pytest.raises(PathTraversalError):
            validate_structure_entry(entry)

    def test_validate_structure_absolute_path_rejected(self):
        """Test that absolute paths are rejected"""
        entry = {"type": "directory", "path": "/etc/passwd"}
        with pytest.raises(InvalidPathError):
            validate_structure_entry(entry)

    def test_validate_structure_with_variables(self):
        """Test that paths with variables are allowed"""
        entry = {"type": "directory", "path": "src/{{id}}"}
        result = validate_structure_entry(entry)
        assert result is True

    def test_validate_structure_nested_path(self):
        """Test validating nested directory paths"""
        entry = {"type": "directory", "path": "src/main/python/mypackage"}
        result = validate_structure_entry(entry)
        assert result is True


class TestValidateFileEntry:
    """Tests for file entry validation"""

    def test_validate_file_with_content(self):
        """Test validating a file entry with content"""
        entry = {"path": "README.md", "content": "# My Project"}
        result = validate_file_entry(entry)
        assert result is True

    def test_validate_file_with_template_reference(self):
        """Test validating a file entry with template reference"""
        entry = {"path": ".gitignore", "template": "gitignore/python"}
        result = validate_file_entry(entry)
        assert result is True

    def test_validate_file_missing_path(self):
        """Test that missing path raises error"""
        entry = {"content": "# My Project"}
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_file_entry(entry)
        assert "path" in str(exc_info.value)

    def test_validate_file_no_content_or_template(self):
        """Test that file without content or template raises error"""
        entry = {"path": "README.md"}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_file_entry(entry)
        assert "content" in str(exc_info.value).lower() or "template" in str(exc_info.value).lower()

    def test_validate_file_both_content_and_template(self):
        """Test that file with both content and template raises error"""
        entry = {
            "path": "README.md",
            "content": "# My Project",
            "template": "readme/default",
        }
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_file_entry(entry)
        assert "content" in str(exc_info.value).lower() or "template" in str(exc_info.value).lower()

    def test_validate_file_empty_path(self):
        """Test that empty path raises error"""
        entry = {"path": "", "content": "content"}
        with pytest.raises(InvalidPathError):
            validate_file_entry(entry)

    def test_validate_file_path_traversal(self):
        """Test that path traversal is rejected"""
        entry = {"path": "../outside/secret.txt", "content": "secret"}
        with pytest.raises(PathTraversalError):
            validate_file_entry(entry)

    def test_validate_file_absolute_path_rejected(self):
        """Test that absolute paths are rejected"""
        entry = {"path": "/etc/passwd", "content": "root:x:0:0"}
        with pytest.raises(InvalidPathError):
            validate_file_entry(entry)

    def test_validate_file_with_variables_in_path(self):
        """Test that paths with variables are allowed"""
        entry = {"path": "src/{{id}}/__init__.py", "content": "# init"}
        result = validate_file_entry(entry)
        assert result is True

    def test_validate_file_with_variables_in_content(self):
        """Test that content with variables is allowed"""
        entry = {"path": "README.md", "content": "# {{title}}\n\nBy {{author}}"}
        result = validate_file_entry(entry)
        assert result is True

    def test_validate_file_multiline_content(self):
        """Test validating file with multiline content"""
        entry = {
            "path": "README.md",
            "content": """# {{title}}

## Description

{{description}}

## License

MIT
""",
        }
        result = validate_file_entry(entry)
        assert result is True


class TestValidateCopyEntry:
    """Tests for copy entry validation"""

    def test_validate_copy_entry(self):
        """Test validating a copy entry"""
        entry = {"source": "assets/LICENSE", "destination": "LICENSE"}
        result = validate_copy_entry(entry)
        assert result is True

    def test_validate_copy_missing_source(self):
        """Test that missing source raises error"""
        entry = {"destination": "LICENSE"}
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_copy_entry(entry)
        assert "source" in str(exc_info.value)

    def test_validate_copy_missing_destination(self):
        """Test that missing destination raises error"""
        entry = {"source": "assets/LICENSE"}
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_copy_entry(entry)
        assert "destination" in str(exc_info.value)

    def test_validate_copy_empty_source(self):
        """Test that empty source raises error"""
        entry = {"source": "", "destination": "LICENSE"}
        with pytest.raises(InvalidPathError):
            validate_copy_entry(entry)

    def test_validate_copy_empty_destination(self):
        """Test that empty destination raises error"""
        entry = {"source": "assets/LICENSE", "destination": ""}
        with pytest.raises(InvalidPathError):
            validate_copy_entry(entry)

    def test_validate_copy_source_path_traversal(self):
        """Test that source path traversal is rejected"""
        entry = {"source": "../../../etc/passwd", "destination": "passwd"}
        with pytest.raises(PathTraversalError):
            validate_copy_entry(entry)

    def test_validate_copy_destination_path_traversal(self):
        """Test that destination path traversal is rejected"""
        entry = {"source": "assets/file.txt", "destination": "../outside/file.txt"}
        with pytest.raises(PathTraversalError):
            validate_copy_entry(entry)

    def test_validate_copy_absolute_source_rejected(self):
        """Test that absolute source paths are rejected"""
        entry = {"source": "/etc/passwd", "destination": "passwd"}
        with pytest.raises(InvalidPathError):
            validate_copy_entry(entry)

    def test_validate_copy_absolute_destination_rejected(self):
        """Test that absolute destination paths are rejected"""
        entry = {"source": "assets/file.txt", "destination": "/tmp/file.txt"}
        with pytest.raises(InvalidPathError):
            validate_copy_entry(entry)

    def test_validate_copy_nested_paths(self):
        """Test validating copy with nested paths"""
        entry = {
            "source": "assets/templates/config.toml",
            "destination": "config/settings.toml",
        }
        result = validate_copy_entry(entry)
        assert result is True


class TestValidateVariableEntry:
    """Tests for variable entry validation"""

    def test_validate_entity_variable(self):
        """Test validating an entity-sourced variable"""
        entry = {"name": "title", "source": "entity"}
        result = validate_variable_entry(entry)
        assert result is True

    def test_validate_system_variable(self):
        """Test validating a system-sourced variable"""
        entry = {"name": "year", "source": "system", "format": "%Y"}
        result = validate_variable_entry(entry)
        assert result is True

    def test_validate_prompt_variable(self):
        """Test validating a prompt-sourced variable"""
        entry = {"name": "author_name", "source": "prompt", "default": "Unknown"}
        result = validate_variable_entry(entry)
        assert result is True

    def test_validate_variable_missing_name(self):
        """Test that missing name raises error"""
        entry = {"source": "entity"}
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_variable_entry(entry)
        assert "name" in str(exc_info.value)

    def test_validate_variable_missing_source(self):
        """Test that missing source raises error"""
        entry = {"name": "title"}
        with pytest.raises(MissingRequiredFieldError) as exc_info:
            validate_variable_entry(entry)
        assert "source" in str(exc_info.value)

    def test_validate_variable_invalid_source(self):
        """Test that invalid source raises error"""
        entry = {"name": "title", "source": "invalid_source"}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_variable_entry(entry)
        assert "source" in str(exc_info.value).lower()

    def test_validate_variable_empty_name(self):
        """Test that empty name raises error"""
        entry = {"name": "", "source": "entity"}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_variable_entry(entry)
        assert "name" in str(exc_info.value).lower()

    def test_validate_variable_name_with_special_chars(self):
        """Test that variable names with special characters are rejected"""
        entry = {"name": "invalid-name!", "source": "entity"}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_variable_entry(entry)
        assert "name" in str(exc_info.value).lower()

    def test_validate_variable_valid_name_patterns(self):
        """Test that valid variable name patterns are accepted"""
        valid_names = ["title", "author_name", "myVar", "var123", "_private"]
        for name in valid_names:
            entry = {"name": name, "source": "entity"}
            result = validate_variable_entry(entry)
            assert result is True, f"Valid name '{name}' was rejected"

    def test_validate_variable_with_optional_default(self):
        """Test that default is optional but allowed"""
        entry = {"name": "author", "source": "prompt", "default": "Anonymous"}
        result = validate_variable_entry(entry)
        assert result is True

    def test_validate_variable_with_optional_format(self):
        """Test that format is optional but allowed for system variables"""
        entry = {"name": "date", "source": "system", "format": "%Y-%m-%d"}
        result = validate_variable_entry(entry)
        assert result is True


class TestValidateGitConfig:
    """Tests for git configuration validation"""

    def test_validate_git_config_minimal(self):
        """Test validating minimal git config"""
        config = {"init": True}
        result = validate_git_config(config)
        assert result is True

    def test_validate_git_config_full(self):
        """Test validating full git config"""
        config = {
            "init": True,
            "initial_commit": True,
            "commit_message": "Initial commit from template",
        }
        result = validate_git_config(config)
        assert result is True

    def test_validate_git_config_init_false(self):
        """Test validating git config with init=False"""
        config = {"init": False}
        result = validate_git_config(config)
        assert result is True

    def test_validate_git_config_invalid_init_type(self):
        """Test that non-boolean init raises error"""
        config = {"init": "yes"}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_git_config(config)
        assert "init" in str(exc_info.value).lower()

    def test_validate_git_config_invalid_initial_commit_type(self):
        """Test that non-boolean initial_commit raises error"""
        config = {"init": True, "initial_commit": "yes"}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_git_config(config)
        assert "initial_commit" in str(exc_info.value).lower()

    def test_validate_git_config_invalid_commit_message_type(self):
        """Test that non-string commit_message raises error"""
        config = {"init": True, "initial_commit": True, "commit_message": 123}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_git_config(config)
        assert "commit_message" in str(exc_info.value).lower()

    def test_validate_git_config_empty_commit_message(self):
        """Test that empty commit message raises error when initial_commit is True"""
        config = {"init": True, "initial_commit": True, "commit_message": ""}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_git_config(config)
        assert "commit_message" in str(exc_info.value).lower()

    def test_validate_git_config_commit_without_init(self):
        """Test that initial_commit without init raises error"""
        config = {"init": False, "initial_commit": True}
        with pytest.raises(InvalidTemplateError) as exc_info:
            validate_git_config(config)
        # Should warn that commit requires init

    def test_validate_git_config_commit_message_with_variables(self):
        """Test that commit message with variables is allowed"""
        config = {
            "init": True,
            "initial_commit": True,
            "commit_message": "Initial commit for {{title}}",
        }
        result = validate_git_config(config)
        assert result is True

    def test_validate_git_config_none(self):
        """Test that None git config is valid (no git initialization)"""
        result = validate_git_config(None)
        assert result is True

    def test_validate_git_config_empty_dict(self):
        """Test that empty git config dict is valid"""
        result = validate_git_config({})
        assert result is True


class TestValidatePathSecurity:
    """Tests for path security validation"""

    def test_validate_simple_path(self):
        """Test that simple paths are valid"""
        result = validate_path_security("src/myproject")
        assert result is True

    def test_validate_path_with_variable(self):
        """Test that paths with variables are valid"""
        result = validate_path_security("src/{{id}}/main.py")
        assert result is True

    def test_validate_path_traversal_rejected(self):
        """Test that path traversal is rejected"""
        with pytest.raises(PathTraversalError):
            validate_path_security("../outside")

    def test_validate_path_traversal_middle_rejected(self):
        """Test that path traversal in middle is rejected"""
        with pytest.raises(PathTraversalError):
            validate_path_security("src/../outside/file.txt")

    def test_validate_path_traversal_encoded_rejected(self):
        """Test that encoded path traversal is rejected"""
        with pytest.raises(PathTraversalError):
            validate_path_security("src/..%2f..%2fetc/passwd")

    def test_validate_absolute_path_rejected(self):
        """Test that absolute paths are rejected"""
        with pytest.raises(InvalidPathError):
            validate_path_security("/etc/passwd")

    def test_validate_windows_absolute_path_rejected(self):
        """Test that Windows absolute paths are rejected"""
        with pytest.raises(InvalidPathError):
            validate_path_security("C:\\Windows\\System32")

    def test_validate_empty_path_rejected(self):
        """Test that empty paths are rejected"""
        with pytest.raises(InvalidPathError):
            validate_path_security("")

    def test_validate_whitespace_path_rejected(self):
        """Test that whitespace-only paths are rejected"""
        with pytest.raises(InvalidPathError):
            validate_path_security("   ")

    def test_validate_hidden_file_allowed(self):
        """Test that hidden files (starting with .) are allowed"""
        result = validate_path_security(".gitignore")
        assert result is True

    def test_validate_deeply_nested_path(self):
        """Test that deeply nested paths are valid"""
        result = validate_path_security("src/main/python/mypackage/submodule/file.py")
        assert result is True

    def test_validate_path_with_dots_in_name(self):
        """Test that dots in file names are valid"""
        result = validate_path_security("config.dev.yml")
        assert result is True

    def test_validate_path_dot_directory_name(self):
        """Test that single dot directory is rejected"""
        with pytest.raises(PathTraversalError):
            validate_path_security("src/./file.txt")

    def test_validate_null_bytes_rejected(self):
        """Test that null bytes in paths are rejected"""
        with pytest.raises(InvalidPathError):
            validate_path_security("file\x00.txt")


class TestExceptionClasses:
    """Tests for custom exception classes"""

    def test_template_schema_error_is_exception(self):
        """Test that TemplateSchemaError is an Exception"""
        error = TemplateSchemaError("test error")
        assert isinstance(error, Exception)

    def test_invalid_template_error_is_schema_error(self):
        """Test that InvalidTemplateError inherits from TemplateSchemaError"""
        error = InvalidTemplateError("invalid template")
        assert isinstance(error, TemplateSchemaError)
        assert isinstance(error, Exception)

    def test_missing_required_field_error_is_schema_error(self):
        """Test that MissingRequiredFieldError inherits from TemplateSchemaError"""
        error = MissingRequiredFieldError("name")
        assert isinstance(error, TemplateSchemaError)
        assert isinstance(error, Exception)

    def test_invalid_path_error_is_schema_error(self):
        """Test that InvalidPathError inherits from TemplateSchemaError"""
        error = InvalidPathError("/etc/passwd")
        assert isinstance(error, TemplateSchemaError)
        assert isinstance(error, Exception)

    def test_path_traversal_error_is_invalid_path_error(self):
        """Test that PathTraversalError inherits from InvalidPathError"""
        error = PathTraversalError("../outside")
        assert isinstance(error, InvalidPathError)
        assert isinstance(error, TemplateSchemaError)
        assert isinstance(error, Exception)

    def test_missing_required_field_error_message(self):
        """Test MissingRequiredFieldError preserves field name in message"""
        error = MissingRequiredFieldError("name")
        assert "name" in str(error)

    def test_invalid_path_error_message(self):
        """Test InvalidPathError preserves path in message"""
        error = InvalidPathError("/etc/passwd")
        assert "/etc/passwd" in str(error)

    def test_path_traversal_error_message(self):
        """Test PathTraversalError preserves path in message"""
        error = PathTraversalError("../outside")
        assert "../outside" in str(error)


class TestTemplateValidationIntegration:
    """Integration tests for complete template validation"""

    def test_validate_realistic_cli_template(self):
        """Test validating a realistic CLI tool template"""
        template = {
            "name": "cli-tool-default",
            "version": "1.0",
            "description": "Standard CLI tool project structure",
            "author": "hoxcore",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "id", "source": "entity"},
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
                    "content": "# {{title}}\n\nCreated: {{year}}\nAuthor: {{author_name}}",
                },
                {
                    "path": "src/{{id}}/__init__.py",
                    "content": '"""{{title}} - Main module"""\n__version__ = "0.1.0"',
                },
                {"path": ".gitignore", "template": "gitignore/python"},
            ],
            "copy": [
                {"source": "assets/LICENSE-MIT", "destination": "LICENSE"},
                {"source": "assets/pyproject.toml.tmpl", "destination": "pyproject.toml"},
            ],
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit from HoxCore template: {{template_name}}",
            },
        }
        result = validate_template(template)
        assert result is True

    def test_validate_academic_paper_template(self):
        """Test validating an academic paper template"""
        template = {
            "name": "academic-paper-latex",
            "version": "1.0",
            "description": "LaTeX academic paper template",
            "author": "academic-templates",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "author", "source": "prompt", "default": "Author Name"},
                {"name": "institution", "source": "prompt", "default": "University"},
            ],
            "structure": [
                {"type": "directory", "path": "sections"},
                {"type": "directory", "path": "figures"},
                {"type": "directory", "path": "bibliography"},
            ],
            "files": [
                {
                    "path": "main.tex",
                    "content": "\\documentclass{article}\n\\title{{{title}}}\n\\author{{{author}}}\n\\begin{document}\n\\maketitle\n\\end{document}",
                },
                {"path": "bibliography/refs.bib", "content": "% Bibliography\n"},
            ],
            "git": {"init": True},
        }
        result = validate_template(template)
        assert result is True

    def test_validate_template_with_all_security_violations(self):
        """Test that template with multiple security violations fails.

        Note: validate_template wraps security errors in InvalidTemplateError,
        so we need to accept both the wrapper and the underlying error types.
        """
        template = {
            "name": "malicious-template",
            "version": "1.0",
            "structure": [
                {"type": "directory", "path": "../../../etc"},  # Path traversal
            ],
            "files": [
                {"path": "/etc/passwd", "content": "malicious"},  # Absolute path
            ],
            "copy": [
                {"source": "../secrets", "destination": "stolen"},  # Path traversal in source
            ],
        }
        # Should fail on first security violation encountered
        # validate_template wraps these errors in InvalidTemplateError
        with pytest.raises((PathTraversalError, InvalidPathError, InvalidTemplateError)):
            validate_template(template)

    def test_validate_template_with_nested_variables(self):
        """Test template with variables in multiple places"""
        template = {
            "name": "variable-heavy",
            "version": "1.0",
            "variables": [
                {"name": "id", "source": "entity"},
                {"name": "module_name", "source": "entity"},
            ],
            "structure": [
                {"type": "directory", "path": "{{id}}"},
                {"type": "directory", "path": "{{id}}/{{module_name}}"},
            ],
            "files": [
                {
                    "path": "{{id}}/{{module_name}}/__init__.py",
                    "content": "# Module: {{module_name}}\n",
                },
            ],
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Create {{id}}/{{module_name}}",
            },
        }
        result = validate_template(template)
        assert result is True


class TestSchemaConstants:
    """Tests for schema constants and allowed values"""

    def test_valid_sources(self):
        """Test that VALID_SOURCES contains expected values"""
        from hxc.templates.schema import VALID_SOURCES

        assert "entity" in VALID_SOURCES
        assert "system" in VALID_SOURCES
        assert "prompt" in VALID_SOURCES

    def test_valid_structure_types(self):
        """Test that VALID_STRUCTURE_TYPES contains expected values"""
        from hxc.templates.schema import VALID_STRUCTURE_TYPES

        assert "directory" in VALID_STRUCTURE_TYPES

    def test_variable_name_pattern(self):
        """Test that VARIABLE_NAME_PATTERN is defined"""
        from hxc.templates.schema import VARIABLE_NAME_PATTERN

        import re

        pattern = re.compile(VARIABLE_NAME_PATTERN)

        # Valid names
        assert pattern.match("title")
        assert pattern.match("my_var")
        assert pattern.match("_private")
        assert pattern.match("var123")

        # Invalid names
        assert not pattern.match("123var")
        assert not pattern.match("my-var")
        assert not pattern.match("var!")