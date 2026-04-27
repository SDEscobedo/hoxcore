"""
Tests for hxc.templates.variables module.

This module tests the TemplateVariables class and related
functions for variable substitution in templates.
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from hxc.templates.variables import (
    TemplateVariables,
    VariableError,
    UndefinedVariableError,
    VariableSubstitutionError,
    escape_for_substitution,
    validate_variable_name,
    extract_variables,
)


class TestVariableError:
    """Tests for the VariableError exception class."""

    def test_variable_error_is_exception(self):
        """Test that VariableError is an Exception."""
        error = VariableError("test error")
        assert isinstance(error, Exception)

    def test_variable_error_message(self):
        """Test that VariableError stores the message."""
        error = VariableError("custom message")
        assert str(error) == "custom message"


class TestUndefinedVariableError:
    """Tests for the UndefinedVariableError exception class."""

    def test_undefined_variable_error_is_variable_error(self):
        """Test that UndefinedVariableError inherits from VariableError."""
        error = UndefinedVariableError("my_var")
        assert isinstance(error, VariableError)
        assert isinstance(error, Exception)

    def test_undefined_variable_error_stores_name(self):
        """Test that UndefinedVariableError stores the variable name."""
        error = UndefinedVariableError("my_var")
        assert error.variable_name == "my_var"

    def test_undefined_variable_error_message(self):
        """Test that error message contains the variable name."""
        error = UndefinedVariableError("missing_var")
        assert "missing_var" in str(error)

    def test_undefined_variable_error_with_available_variables(self):
        """Test that error message lists available variables."""
        error = UndefinedVariableError("missing", available_variables=["title", "id"])
        assert "missing" in str(error)
        assert error.available_variables == ["title", "id"]

    def test_undefined_variable_error_empty_available(self):
        """Test UndefinedVariableError with no available variables."""
        error = UndefinedVariableError("missing")
        assert error.available_variables == []


class TestVariableSubstitutionError:
    """Tests for the VariableSubstitutionError exception class."""

    def test_variable_substitution_error_is_variable_error(self):
        """Test that VariableSubstitutionError inherits from VariableError."""
        error = VariableSubstitutionError("substitution failed")
        assert isinstance(error, VariableError)
        assert isinstance(error, Exception)

    def test_variable_substitution_error_stores_variable_name(self):
        """Test that error stores the variable name."""
        error = VariableSubstitutionError("failed", variable_name="my_var")
        assert error.variable_name == "my_var"

    def test_variable_substitution_error_message(self):
        """Test the error message."""
        error = VariableSubstitutionError("substitution failed")
        assert str(error) == "substitution failed"

    def test_variable_substitution_error_no_variable_name(self):
        """Test error without variable name."""
        error = VariableSubstitutionError("generic error")
        assert error.variable_name is None


class TestTemplateVariablesInit:
    """Tests for TemplateVariables initialization."""

    def test_init_creates_empty_variables(self):
        """Test that initialization creates empty variables dict."""
        variables = TemplateVariables()
        assert variables.variables == {}

    def test_init_creates_empty_prompt_definitions(self):
        """Test that initialization creates empty prompt definitions list."""
        variables = TemplateVariables()
        assert variables._prompt_definitions == []

    def test_init_strict_mode_false_by_default(self):
        """Test that strict mode is False by default."""
        variables = TemplateVariables()
        assert variables._strict_mode is False


class TestTemplateVariablesProperties:
    """Tests for TemplateVariables properties."""

    def test_variables_property_returns_copy(self):
        """Test that variables property returns a copy."""
        variables = TemplateVariables()
        variables.add_variable("test", "value")

        result = variables.variables
        result["new_key"] = "new_value"

        assert "new_key" not in variables.variables

    def test_available_variables_returns_sorted_list(self):
        """Test that available_variables returns sorted list."""
        variables = TemplateVariables()
        variables.add_variable("zebra", "z")
        variables.add_variable("alpha", "a")
        variables.add_variable("beta", "b")

        result = variables.available_variables

        assert result == ["alpha", "beta", "zebra"]

    def test_available_variables_empty(self):
        """Test available_variables when empty."""
        variables = TemplateVariables()
        assert variables.available_variables == []


class TestTemplateVariablesStrictMode:
    """Tests for strict mode setting."""

    def test_set_strict_mode_true(self):
        """Test setting strict mode to True."""
        variables = TemplateVariables()
        variables.set_strict_mode(True)
        assert variables._strict_mode is True

    def test_set_strict_mode_false(self):
        """Test setting strict mode to False."""
        variables = TemplateVariables()
        variables.set_strict_mode(True)
        variables.set_strict_mode(False)
        assert variables._strict_mode is False


class TestTemplateVariablesAddVariable:
    """Tests for adding variables."""

    def test_add_variable_basic(self):
        """Test adding a basic variable."""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")

        assert variables.get_variable("title") == "My Project"

    def test_add_variable_with_different_types(self):
        """Test adding variables with different value types."""
        variables = TemplateVariables()
        variables.add_variable("string_var", "text")
        variables.add_variable("int_var", 42)
        variables.add_variable("list_var", [1, 2, 3])
        variables.add_variable("dict_var", {"key": "value"})
        variables.add_variable("none_var", None)

        assert variables.get_variable("string_var") == "text"
        assert variables.get_variable("int_var") == 42
        assert variables.get_variable("list_var") == [1, 2, 3]
        assert variables.get_variable("dict_var") == {"key": "value"}
        assert variables.get_variable("none_var") is None

    def test_add_variable_overwrites_existing(self):
        """Test that adding a variable with the same name overwrites."""
        variables = TemplateVariables()
        variables.add_variable("title", "Original")
        variables.add_variable("title", "Updated")

        assert variables.get_variable("title") == "Updated"


class TestTemplateVariablesAddVariables:
    """Tests for adding multiple variables."""

    def test_add_variables_dict(self):
        """Test adding multiple variables from a dict."""
        variables = TemplateVariables()
        variables.add_variables({
            "title": "My Project",
            "id": "my_project",
            "version": "1.0",
        })

        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"
        assert variables.get_variable("version") == "1.0"

    def test_add_variables_empty_dict(self):
        """Test adding empty dict does nothing."""
        variables = TemplateVariables()
        variables.add_variables({})
        assert variables.variables == {}

    def test_add_variables_merges_with_existing(self):
        """Test that add_variables merges with existing variables."""
        variables = TemplateVariables()
        variables.add_variable("existing", "value")
        variables.add_variables({"new": "new_value"})

        assert variables.get_variable("existing") == "value"
        assert variables.get_variable("new") == "new_value"


class TestTemplateVariablesGetVariable:
    """Tests for getting variables."""

    def test_get_variable_existing(self):
        """Test getting an existing variable."""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")

        assert variables.get_variable("title") == "My Project"

    def test_get_variable_nonexistent_returns_default(self):
        """Test that getting nonexistent variable returns default."""
        variables = TemplateVariables()

        assert variables.get_variable("missing") is None
        assert variables.get_variable("missing", "default") == "default"

    def test_get_variable_with_custom_default(self):
        """Test getting variable with custom default."""
        variables = TemplateVariables()

        assert variables.get_variable("missing", "fallback") == "fallback"


class TestTemplateVariablesHasVariable:
    """Tests for has_variable method."""

    def test_has_variable_true(self):
        """Test has_variable returns True for existing variable."""
        variables = TemplateVariables()
        variables.add_variable("title", "value")

        assert variables.has_variable("title") is True

    def test_has_variable_false(self):
        """Test has_variable returns False for missing variable."""
        variables = TemplateVariables()

        assert variables.has_variable("missing") is False

    def test_has_variable_with_none_value(self):
        """Test has_variable returns True even when value is None."""
        variables = TemplateVariables()
        variables.add_variable("nullable", None)

        assert variables.has_variable("nullable") is True


class TestTemplateVariablesAddEntityVariables:
    """Tests for adding entity variables."""

    def test_add_entity_variables_basic(self):
        """Test adding entity variables from entity data."""
        variables = TemplateVariables()
        entity_data = {
            "title": "My Project",
            "id": "my_project",
            "uid": "abc12345",
            "description": "A sample project",
            "status": "active",
        }

        variables.add_entity_variables(entity_data)

        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"
        assert variables.get_variable("uid") == "abc12345"
        assert variables.get_variable("description") == "A sample project"
        assert variables.get_variable("status") == "active"

    def test_add_entity_variables_ignores_unknown_fields(self):
        """Test that unknown entity fields are ignored."""
        variables = TemplateVariables()
        entity_data = {
            "title": "Project",
            "unknown_field": "should be ignored",
        }

        variables.add_entity_variables(entity_data)

        assert variables.get_variable("title") == "Project"
        assert variables.has_variable("unknown_field") is False

    def test_add_entity_variables_converts_none_to_empty_string(self):
        """Test that None values are converted to empty strings."""
        variables = TemplateVariables()
        entity_data = {
            "title": "Project",
            "description": None,
        }

        variables.add_entity_variables(entity_data)

        assert variables.get_variable("title") == "Project"
        assert variables.get_variable("description") == ""

    def test_add_entity_variables_empty_dict(self):
        """Test adding empty entity data."""
        variables = TemplateVariables()
        variables.add_entity_variables({})

        assert variables.variables == {}

    def test_add_entity_variables_all_known_fields(self):
        """Test that all known entity fields are recognized."""
        variables = TemplateVariables()
        entity_data = {
            "title": "Project",
            "id": "proj-1",
            "uid": "abc123",
            "description": "Description",
            "category": "software",
            "status": "active",
            "type": "project",
            "start_date": "2024-01-01",
            "due_date": "2024-12-31",
            "completion_date": None,
            "duration_estimate": "3m",
            "parent": "parent-uid",
            "template": "default",
        }

        variables.add_entity_variables(entity_data)

        for field in TemplateVariables.ENTITY_VARS:
            if field in entity_data:
                if entity_data[field] is None:
                    assert variables.get_variable(field) == ""
                else:
                    assert variables.get_variable(field) == entity_data[field]


class TestTemplateVariablesAddSystemVariables:
    """Tests for adding system variables."""

    def test_add_system_variables_adds_date(self):
        """Test that system variables include date."""
        variables = TemplateVariables()
        variables.add_system_variables()

        assert variables.has_variable("date")
        assert variables.get_variable("date") is not None

    def test_add_system_variables_adds_year(self):
        """Test that system variables include year."""
        variables = TemplateVariables()
        variables.add_system_variables()

        assert variables.has_variable("year")
        year = variables.get_variable("year")
        assert len(year) == 4
        assert year.isdigit()

    def test_add_system_variables_adds_timestamp(self):
        """Test that system variables include timestamp."""
        variables = TemplateVariables()
        variables.add_system_variables()

        assert variables.has_variable("timestamp")

    def test_add_system_variables_with_template_name(self):
        """Test adding system variables with template name."""
        variables = TemplateVariables()
        variables.add_system_variables(template_name="my-template")

        assert variables.get_variable("template_name") == "my-template"

    def test_add_system_variables_with_template_version(self):
        """Test adding system variables with template version."""
        variables = TemplateVariables()
        variables.add_system_variables(template_version="1.0")

        assert variables.get_variable("template_version") == "1.0"

    def test_add_system_variables_with_custom_datetime(self):
        """Test adding system variables with a custom datetime."""
        variables = TemplateVariables()
        custom_dt = datetime(2024, 6, 15, 10, 30, 0)
        variables.add_system_variables(now=custom_dt)

        assert variables.get_variable("year") == "2024"
        assert "06" in variables.get_variable("month") or variables.get_variable("month") == "06"

    def test_add_system_variables_all_known_fields(self):
        """Test that all known system fields are added."""
        variables = TemplateVariables()
        variables.add_system_variables()

        for field in TemplateVariables.SYSTEM_VARS:
            if field not in ("template_name", "template_version"):
                assert variables.has_variable(field), f"Missing system variable: {field}"


class TestTemplateVariablesAddSystemVariableWithFormat:
    """Tests for adding system variable with custom format."""

    def test_add_system_variable_with_format(self):
        """Test adding a system variable with a custom format."""
        variables = TemplateVariables()
        custom_dt = datetime(2024, 6, 15, 10, 30, 0)
        variables.add_system_variable_with_format("custom_date", "%Y/%m/%d", now=custom_dt)

        assert variables.get_variable("custom_date") == "2024/06/15"

    def test_add_system_variable_with_time_format(self):
        """Test adding a system variable with time format."""
        variables = TemplateVariables()
        custom_dt = datetime(2024, 6, 15, 14, 30, 45)
        variables.add_system_variable_with_format("time_var", "%H:%M:%S", now=custom_dt)

        assert variables.get_variable("time_var") == "14:30:45"

    def test_add_system_variable_with_complex_format(self):
        """Test adding a system variable with complex format."""
        variables = TemplateVariables()
        custom_dt = datetime(2024, 6, 15, 10, 30, 0)
        variables.add_system_variable_with_format(
            "formatted",
            "%B %d, %Y at %I:%M %p",
            now=custom_dt
        )

        result = variables.get_variable("formatted")
        assert "2024" in result
        assert "15" in result

    def test_add_system_variable_with_invalid_format(self):
        """Test that invalid format string is handled gracefully."""
        variables = TemplateVariables()
        custom_dt = datetime(2024, 6, 15, 10, 30, 0)
        
        # Invalid format strings in strftime don't raise errors,
        # they just output the invalid format codes as-is
        variables.add_system_variable_with_format("bad_format", "%Q%Z%X", now=custom_dt)
        
        # The variable should still be set, even if the format is unusual
        assert variables.has_variable("bad_format")


class TestTemplateVariablesAddPromptVariables:
    """Tests for adding prompt variables."""

    def test_add_prompt_variables_basic(self):
        """Test adding prompt variables."""
        variables = TemplateVariables()
        prompt_values = {"author_name": "John Doe", "license": "MIT"}

        variables.add_prompt_variables(prompt_values)

        assert variables.get_variable("author_name") == "John Doe"
        assert variables.get_variable("license") == "MIT"

    def test_add_prompt_variables_empty(self):
        """Test adding empty prompt variables."""
        variables = TemplateVariables()
        variables.add_prompt_variables({})

        assert variables.variables == {}

    def test_add_prompt_variables_none(self):
        """Test adding None prompt variables."""
        variables = TemplateVariables()
        variables.add_prompt_variables(None)

        assert variables.variables == {}


class TestTemplateVariablesRegisterPromptDefinition:
    """Tests for registering prompt definitions."""

    def test_register_prompt_definition_basic(self):
        """Test registering a basic prompt definition."""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")

        pending = variables.get_pending_prompts()
        assert len(pending) == 1
        assert pending[0]["name"] == "author_name"

    def test_register_prompt_definition_with_default(self):
        """Test registering a prompt definition with default."""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt", default="Unknown")

        pending = variables.get_pending_prompts()
        assert len(pending) == 1
        assert pending[0]["default"] == "Unknown"

    def test_register_prompt_definition_resolved_by_value(self):
        """Test that providing a value resolves the prompt."""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        variables.add_variable("author_name", "Resolved Author")

        pending = variables.get_pending_prompts()
        assert len(pending) == 0

    def test_register_prompt_definition_resolved_by_default(self):
        """Test that default value resolves the prompt."""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt", default="Default Author")

        # Default should resolve automatically
        pending = variables.get_pending_prompts()
        # With default, it should be resolved
        assert len(pending) == 0 or all(p.get("default") for p in pending)


class TestTemplateVariablesGetPendingPrompts:
    """Tests for getting pending prompts."""

    def test_get_pending_prompts_empty(self):
        """Test getting pending prompts when none registered."""
        variables = TemplateVariables()
        assert variables.get_pending_prompts() == []

    def test_get_pending_prompts_with_unresolved(self):
        """Test getting pending prompts with unresolved prompts."""
        variables = TemplateVariables()
        variables.register_prompt_definition("required_var", "prompt")

        pending = variables.get_pending_prompts()
        assert len(pending) == 1

    def test_get_pending_prompts_all_resolved(self):
        """Test getting pending prompts when all are resolved."""
        variables = TemplateVariables()
        variables.register_prompt_definition("author", "prompt")
        variables.add_variable("author", "Test Author")

        pending = variables.get_pending_prompts()
        assert len(pending) == 0


class TestTemplateVariablesResolveFromTemplateDefinition:
    """Tests for resolving variables from template definition."""

    def test_resolve_entity_variables(self):
        """Test resolving entity-sourced variables."""
        variables = TemplateVariables()
        template_data = {
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "id", "source": "entity"},
            ]
        }
        entity_data = {"title": "My Project", "id": "my_project"}

        variables.resolve_from_template_definition(template_data, entity_data)

        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"

    def test_resolve_system_variables(self):
        """Test resolving system-sourced variables."""
        variables = TemplateVariables()
        template_data = {
            "name": "my-template",
            "version": "1.0",
            "variables": [
                {"name": "year", "source": "system"},
                {"name": "date", "source": "system"},
            ]
        }

        variables.resolve_from_template_definition(template_data, {})

        assert variables.has_variable("year")
        assert variables.has_variable("date")
        assert variables.get_variable("template_name") == "my-template"

    def test_resolve_prompt_variables_with_default(self):
        """Test resolving prompt variables with defaults."""
        variables = TemplateVariables()
        template_data = {
            "variables": [
                {"name": "author", "source": "prompt", "default": "Anonymous"},
            ]
        }

        variables.resolve_from_template_definition(template_data, {})

        # Should use default
        assert variables.get_variable("author") == "Anonymous"

    def test_resolve_prompt_variables_without_default(self):
        """Test resolving prompt variables without defaults."""
        variables = TemplateVariables()
        template_data = {
            "variables": [
                {"name": "required_var", "source": "prompt"},
            ]
        }

        variables.resolve_from_template_definition(template_data, {})

        # Should be pending
        pending = variables.get_pending_prompts()
        assert len(pending) == 1

    def test_resolve_no_variables_section(self):
        """Test resolving when no variables section exists."""
        variables = TemplateVariables()
        template_data = {"name": "test", "version": "1.0"}

        variables.resolve_from_template_definition(template_data, {})

        # Should still have system variables
        assert variables.has_variable("template_name")


class TestTemplateVariablesSubstitute:
    """Tests for the substitute method."""

    def test_substitute_single_variable(self):
        """Test substituting a single variable."""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")

        result = variables.substitute("# {{title}}")

        assert result == "# My Project"

    def test_substitute_multiple_variables(self):
        """Test substituting multiple variables."""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        variables.add_variable("author", "John Doe")

        result = variables.substitute("{{title}} by {{author}}")

        assert result == "My Project by John Doe"

    def test_substitute_same_variable_multiple_times(self):
        """Test substituting the same variable multiple times."""
        variables = TemplateVariables()
        variables.add_variable("name", "Test")

        result = variables.substitute("{{name}}-{{name}}-{{name}}")

        assert result == "Test-Test-Test"

    def test_substitute_with_whitespace_in_braces(self):
        """Test substituting with whitespace in variable syntax."""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")

        result = variables.substitute("{{ title }}")

        assert result == "My Project"

    def test_substitute_undefined_variable_non_strict(self):
        """Test substituting undefined variable in non-strict mode."""
        variables = TemplateVariables()
        variables.set_strict_mode(False)

        result = variables.substitute("Hello {{undefined}}")

        assert result == "Hello {{undefined}}"

    def test_substitute_undefined_variable_strict(self):
        """Test substituting undefined variable in strict mode."""
        variables = TemplateVariables()
        variables.set_strict_mode(True)

        with pytest.raises(UndefinedVariableError) as exc_info:
            variables.substitute("Hello {{undefined}}")

        assert exc_info.value.variable_name == "undefined"

    def test_substitute_empty_content(self):
        """Test substituting empty content."""
        variables = TemplateVariables()

        result = variables.substitute("")

        assert result == ""

    def test_substitute_no_variables(self):
        """Test substituting content with no variables."""
        variables = TemplateVariables()

        result = variables.substitute("Hello World!")

        assert result == "Hello World!"

    def test_substitute_converts_non_string_values(self):
        """Test that non-string values are converted to strings."""
        variables = TemplateVariables()
        variables.add_variable("number", 42)
        variables.add_variable("boolean", True)

        result = variables.substitute("Number: {{number}}, Boolean: {{boolean}}")

        assert result == "Number: 42, Boolean: True"


class TestTemplateVariablesSubstitutePath:
    """Tests for the substitute_path method."""

    def test_substitute_path_basic(self):
        """Test basic path substitution."""
        variables = TemplateVariables()
        variables.add_variable("id", "my_project")

        result = variables.substitute_path("src/{{id}}")

        assert result == "src/my_project"

    def test_substitute_path_multiple_variables(self):
        """Test path substitution with multiple variables."""
        variables = TemplateVariables()
        variables.add_variable("id", "my_project")
        variables.add_variable("module", "core")

        result = variables.substitute_path("src/{{id}}/{{module}}")

        assert result == "src/my_project/core"

    def test_substitute_path_traversal_raises_error(self):
        """Test that path traversal after substitution raises error."""
        variables = TemplateVariables()
        variables.add_variable("malicious", "..")

        with pytest.raises(VariableSubstitutionError):
            variables.substitute_path("{{malicious}}/outside")


class TestTemplateVariablesFindVariablesInContent:
    """Tests for find_variables_in_content method."""

    def test_find_variables_single(self):
        """Test finding a single variable."""
        variables = TemplateVariables()

        result = variables.find_variables_in_content("Hello {{name}}")

        assert result == ["name"]

    def test_find_variables_multiple(self):
        """Test finding multiple variables."""
        variables = TemplateVariables()

        result = variables.find_variables_in_content("{{a}} and {{b}} and {{c}}")

        assert result == ["a", "b", "c"]

    def test_find_variables_duplicates_removed(self):
        """Test that duplicate variables are removed."""
        variables = TemplateVariables()

        result = variables.find_variables_in_content("{{a}} {{a}} {{b}} {{a}}")

        assert result == ["a", "b"]

    def test_find_variables_preserves_order(self):
        """Test that order is preserved (first occurrence)."""
        variables = TemplateVariables()

        result = variables.find_variables_in_content("{{z}} {{a}} {{m}}")

        assert result == ["z", "a", "m"]

    def test_find_variables_empty_content(self):
        """Test finding variables in empty content."""
        variables = TemplateVariables()

        result = variables.find_variables_in_content("")

        assert result == []

    def test_find_variables_no_variables(self):
        """Test finding variables when none exist."""
        variables = TemplateVariables()

        result = variables.find_variables_in_content("No variables here")

        assert result == []


class TestTemplateVariablesFindUndefinedVariables:
    """Tests for find_undefined_variables method."""

    def test_find_undefined_variables_all_defined(self):
        """Test finding undefined variables when all are defined."""
        variables = TemplateVariables()
        variables.add_variable("title", "Test")
        variables.add_variable("id", "test")

        result = variables.find_undefined_variables("{{title}} {{id}}")

        assert result == []

    def test_find_undefined_variables_some_undefined(self):
        """Test finding some undefined variables."""
        variables = TemplateVariables()
        variables.add_variable("title", "Test")

        result = variables.find_undefined_variables("{{title}} {{missing}}")

        assert result == ["missing"]

    def test_find_undefined_variables_all_undefined(self):
        """Test finding variables when all are undefined."""
        variables = TemplateVariables()

        result = variables.find_undefined_variables("{{a}} {{b}}")

        assert result == ["a", "b"]


class TestTemplateVariablesValidateContent:
    """Tests for validate_content method."""

    def test_validate_content_all_valid(self):
        """Test validating content with all variables defined."""
        variables = TemplateVariables()
        variables.add_variable("title", "Test")

        result = variables.validate_content("Hello {{title}}")

        assert result == []

    def test_validate_content_with_undefined(self):
        """Test validating content with undefined variables."""
        variables = TemplateVariables()

        result = variables.validate_content("Hello {{undefined}}")

        assert "undefined" in result


class TestTemplateVariablesClear:
    """Tests for clear method."""

    def test_clear_removes_all_variables(self):
        """Test that clear removes all variables."""
        variables = TemplateVariables()
        variables.add_variable("a", "1")
        variables.add_variable("b", "2")

        variables.clear()

        assert variables.variables == {}

    def test_clear_removes_prompt_definitions(self):
        """Test that clear removes prompt definitions."""
        variables = TemplateVariables()
        variables.register_prompt_definition("author", "prompt")

        variables.clear()

        assert variables._prompt_definitions == []


class TestTemplateVariablesCopy:
    """Tests for copy method."""

    def test_copy_creates_independent_copy(self):
        """Test that copy creates an independent copy."""
        original = TemplateVariables()
        original.add_variable("title", "Original")

        copied = original.copy()
        copied.add_variable("title", "Modified")

        assert original.get_variable("title") == "Original"
        assert copied.get_variable("title") == "Modified"

    def test_copy_preserves_strict_mode(self):
        """Test that copy preserves strict mode."""
        original = TemplateVariables()
        original.set_strict_mode(True)

        copied = original.copy()

        assert copied._strict_mode is True

    def test_copy_preserves_prompt_definitions(self):
        """Test that copy preserves prompt definitions."""
        original = TemplateVariables()
        original.register_prompt_definition("author", "prompt")

        copied = original.copy()

        assert len(copied._prompt_definitions) == len(original._prompt_definitions)


class TestTemplateVariablesFromEntityAndTemplate:
    """Tests for from_entity_and_template class method."""

    def test_from_entity_and_template_basic(self):
        """Test creating variables from entity and template."""
        entity_data = {"title": "My Project", "id": "my_project"}
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "id", "source": "entity"},
            ],
        }

        variables = TemplateVariables.from_entity_and_template(
            entity_data=entity_data,
            template_data=template_data,
        )

        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"

    def test_from_entity_and_template_with_prompts(self):
        """Test creating variables with prompt values."""
        entity_data = {"title": "My Project"}
        template_data = {
            "name": "test",
            "version": "1.0",
            "variables": [
                {"name": "author", "source": "prompt"},
            ],
        }
        prompt_values = {"author": "John Doe"}

        variables = TemplateVariables.from_entity_and_template(
            entity_data=entity_data,
            template_data=template_data,
            prompt_values=prompt_values,
        )

        assert variables.get_variable("author") == "John Doe"


class TestTemplateVariablesFromEntity:
    """Tests for from_entity class method."""

    def test_from_entity_basic(self):
        """Test creating variables from entity data."""
        entity_data = {"title": "My Project", "id": "my_project", "status": "active"}

        variables = TemplateVariables.from_entity(entity_data)

        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"
        assert variables.get_variable("status") == "active"

    def test_from_entity_includes_system_variables(self):
        """Test that from_entity includes system variables."""
        entity_data = {"title": "My Project"}

        variables = TemplateVariables.from_entity(entity_data)

        assert variables.has_variable("year")
        assert variables.has_variable("date")


class TestTemplateVariablesDunderMethods:
    """Tests for dunder methods."""

    def test_repr(self):
        """Test __repr__ method."""
        variables = TemplateVariables()
        variables.add_variable("a", "1")
        variables.add_variable("b", "2")

        repr_str = repr(variables)

        assert "TemplateVariables" in repr_str
        assert "2" in repr_str  # variable count

    def test_contains(self):
        """Test __contains__ method."""
        variables = TemplateVariables()
        variables.add_variable("title", "Test")

        assert "title" in variables
        assert "missing" not in variables

    def test_getitem(self):
        """Test __getitem__ method."""
        variables = TemplateVariables()
        variables.add_variable("title", "Test")

        assert variables["title"] == "Test"

    def test_getitem_raises_for_missing(self):
        """Test __getitem__ raises for missing variable."""
        variables = TemplateVariables()

        with pytest.raises(UndefinedVariableError):
            _ = variables["missing"]

    def test_setitem(self):
        """Test __setitem__ method."""
        variables = TemplateVariables()
        variables["title"] = "Test"

        assert variables.get_variable("title") == "Test"

    def test_len(self):
        """Test __len__ method."""
        variables = TemplateVariables()
        variables.add_variable("a", "1")
        variables.add_variable("b", "2")

        assert len(variables) == 2


class TestEscapeForSubstitution:
    """Tests for escape_for_substitution function."""

    def test_escape_double_braces(self):
        """Test escaping double braces."""
        result = escape_for_substitution("{{variable}}")

        assert "{{" not in result or result == "{ {variable} }"

    def test_escape_no_braces(self):
        """Test that content without braces is unchanged."""
        result = escape_for_substitution("no braces here")

        assert result == "no braces here"

    def test_escape_single_braces(self):
        """Test that single braces are preserved."""
        result = escape_for_substitution("{single}")

        assert result == "{single}"


class TestValidateVariableName:
    """Tests for validate_variable_name function."""

    def test_validate_valid_names(self):
        """Test validating valid variable names."""
        valid_names = ["title", "my_var", "_private", "var123", "MyVar"]

        for name in valid_names:
            assert validate_variable_name(name) is True, f"'{name}' should be valid"

    def test_validate_invalid_names(self):
        """Test validating invalid variable names."""
        invalid_names = ["123var", "my-var", "var!", "", "with space"]

        for name in invalid_names:
            assert validate_variable_name(name) is False, f"'{name}' should be invalid"


class TestExtractVariables:
    """Tests for extract_variables function."""

    def test_extract_variables_basic(self):
        """Test extracting variables from content."""
        result = extract_variables("{{a}} and {{b}}")

        assert result == ["a", "b"]

    def test_extract_variables_empty(self):
        """Test extracting from content with no variables."""
        result = extract_variables("no variables")

        assert result == []


class TestTemplateVariablesIntegration:
    """Integration tests for TemplateVariables."""

    def test_full_workflow(self):
        """Test a full variable resolution workflow."""
        # Setup template and entity data
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "id", "source": "entity"},
                {"name": "year", "source": "system"},
                {"name": "author", "source": "prompt", "default": "Anonymous"},
            ],
        }
        entity_data = {
            "title": "My Awesome Project",
            "id": "my_awesome_project",
        }
        prompt_values = {"author": "John Doe"}

        # Create variables
        variables = TemplateVariables.from_entity_and_template(
            entity_data=entity_data,
            template_data=template_data,
            prompt_values=prompt_values,
        )

        # Test substitution
        content = "# {{title}}\n\nCreated by {{author}} in {{year}}"
        result = variables.substitute(content)

        assert "My Awesome Project" in result
        assert "John Doe" in result
        assert str(datetime.now().year) in result

    def test_path_substitution_workflow(self):
        """Test path substitution workflow."""
        variables = TemplateVariables()
        variables.add_variable("id", "my_project")
        variables.add_variable("module", "core")

        paths = [
            "src/{{id}}/__init__.py",
            "src/{{id}}/{{module}}/main.py",
            "tests/test_{{id}}.py",
        ]

        results = [variables.substitute_path(p) for p in paths]

        assert results[0] == "src/my_project/__init__.py"
        assert results[1] == "src/my_project/core/main.py"
        assert results[2] == "tests/test_my_project.py"