"""
Tests for HoxCore Template Variables.

This module tests the variable resolution and substitution functionality
for template scaffolding, including entity, system, and prompt-sourced
variables and safe string substitution.
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


class TestTemplateVariablesInit:
    """Tests for TemplateVariables initialization"""

    def test_init_creates_empty_variables(self):
        """Test that initialization creates empty variables dict"""
        variables = TemplateVariables()
        assert variables.variables == {}

    def test_init_creates_empty_prompt_definitions(self):
        """Test that initialization creates empty prompt definitions"""
        variables = TemplateVariables()
        assert variables._prompt_definitions == []

    def test_init_strict_mode_false_by_default(self):
        """Test that strict mode is False by default"""
        variables = TemplateVariables()
        assert variables._strict_mode is False

    def test_available_variables_empty(self):
        """Test that available_variables is empty initially"""
        variables = TemplateVariables()
        assert variables.available_variables == []

    def test_len_returns_zero_initially(self):
        """Test that len returns 0 initially"""
        variables = TemplateVariables()
        assert len(variables) == 0


class TestTemplateVariablesAddVariable:
    """Tests for adding individual variables"""

    def test_add_variable_string(self):
        """Test adding a string variable"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert variables.get_variable("title") == "My Project"

    def test_add_variable_integer(self):
        """Test adding an integer variable"""
        variables = TemplateVariables()
        variables.add_variable("count", 42)
        
        assert variables.get_variable("count") == 42

    def test_add_variable_none(self):
        """Test adding a None variable"""
        variables = TemplateVariables()
        variables.add_variable("empty", None)
        
        assert variables.get_variable("empty") is None

    def test_add_variable_overwrites_existing(self):
        """Test that adding a variable overwrites existing value"""
        variables = TemplateVariables()
        variables.add_variable("title", "Original")
        variables.add_variable("title", "Updated")
        
        assert variables.get_variable("title") == "Updated"

    def test_add_variable_updates_available_variables(self):
        """Test that adding variable updates available_variables list"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert "title" in variables.available_variables

    def test_add_variable_updates_len(self):
        """Test that adding variable updates length"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert len(variables) == 1


class TestTemplateVariablesAddVariables:
    """Tests for adding multiple variables at once"""

    def test_add_variables_dict(self):
        """Test adding multiple variables from dict"""
        variables = TemplateVariables()
        variables.add_variables({"title": "My Project", "id": "my-proj"})
        
        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my-proj"

    def test_add_variables_empty_dict(self):
        """Test adding empty dict does nothing"""
        variables = TemplateVariables()
        variables.add_variables({})
        
        assert len(variables) == 0

    def test_add_variables_updates_existing(self):
        """Test that add_variables updates existing values"""
        variables = TemplateVariables()
        variables.add_variable("title", "Original")
        variables.add_variables({"title": "Updated", "id": "new"})
        
        assert variables.get_variable("title") == "Updated"
        assert variables.get_variable("id") == "new"


class TestTemplateVariablesGetVariable:
    """Tests for getting variable values"""

    def test_get_variable_existing(self):
        """Test getting an existing variable"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert variables.get_variable("title") == "My Project"

    def test_get_variable_nonexistent_returns_none(self):
        """Test getting nonexistent variable returns None"""
        variables = TemplateVariables()
        
        assert variables.get_variable("nonexistent") is None

    def test_get_variable_nonexistent_with_default(self):
        """Test getting nonexistent variable with custom default"""
        variables = TemplateVariables()
        
        assert variables.get_variable("nonexistent", "default") == "default"

    def test_get_variable_existing_ignores_default(self):
        """Test that existing variable ignores default"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert variables.get_variable("title", "default") == "My Project"


class TestTemplateVariablesHasVariable:
    """Tests for checking variable existence"""

    def test_has_variable_true(self):
        """Test has_variable returns True for existing variable"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert variables.has_variable("title") is True

    def test_has_variable_false(self):
        """Test has_variable returns False for nonexistent variable"""
        variables = TemplateVariables()
        
        assert variables.has_variable("nonexistent") is False

    def test_contains_operator(self):
        """Test __contains__ (in operator) works"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert "title" in variables
        assert "nonexistent" not in variables


class TestTemplateVariablesAddEntityVariables:
    """Tests for adding entity-sourced variables"""

    def test_add_entity_variables_basic(self, sample_entity_data):
        """Test adding entity variables from entity data"""
        variables = TemplateVariables()
        variables.add_entity_variables(sample_entity_data)
        
        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"
        assert variables.get_variable("uid") == "abc12345"

    def test_add_entity_variables_filters_to_valid_vars(self, sample_entity_data):
        """Test that only valid entity variables are extracted"""
        variables = TemplateVariables()
        variables.add_entity_variables(sample_entity_data)
        
        # These should be included
        assert "title" in variables
        assert "id" in variables
        assert "uid" in variables
        assert "description" in variables
        assert "status" in variables
        
        # start_date is in entity data but also in ENTITY_VARS
        # Check that unknown fields are not included
        # The entity type is included
        assert "type" in variables

    def test_add_entity_variables_converts_none_to_empty_string(self):
        """Test that None values are converted to empty string"""
        entity_data = {
            "title": "Test",
            "id": "test",
            "uid": "abc123",
            "description": None,
        }
        variables = TemplateVariables()
        variables.add_entity_variables(entity_data)
        
        assert variables.get_variable("description") == ""

    def test_add_entity_variables_empty_dict(self):
        """Test adding entity variables from empty dict"""
        variables = TemplateVariables()
        variables.add_entity_variables({})
        
        # No entity variables should be added
        for var in TemplateVariables.ENTITY_VARS:
            assert var not in variables

    def test_add_entity_variables_partial_data(self):
        """Test adding entity variables with partial data"""
        entity_data = {"title": "Test", "id": "test-id"}
        variables = TemplateVariables()
        variables.add_entity_variables(entity_data)
        
        assert variables.get_variable("title") == "Test"
        assert variables.get_variable("id") == "test-id"
        assert "uid" not in variables


class TestTemplateVariablesAddSystemVariables:
    """Tests for adding system-generated variables"""

    def test_add_system_variables_basic(self):
        """Test adding system variables with default time"""
        variables = TemplateVariables()
        variables.add_system_variables()
        
        assert "date" in variables
        assert "year" in variables
        assert "month" in variables
        assert "day" in variables
        assert "time" in variables
        assert "datetime" in variables
        assert "timestamp" in variables
        assert "iso_date" in variables
        assert "weekday" in variables

    def test_add_system_variables_with_fixed_time(self):
        """Test adding system variables with fixed datetime"""
        fixed_time = datetime(2024, 6, 15, 10, 30, 45)
        variables = TemplateVariables()
        variables.add_system_variables(now=fixed_time)
        
        assert variables.get_variable("date") == "2024-06-15"
        assert variables.get_variable("year") == "2024"
        assert variables.get_variable("month") == "06"
        assert variables.get_variable("day") == "15"
        assert variables.get_variable("time") == "10:30:45"
        assert variables.get_variable("weekday") == "Saturday"

    def test_add_system_variables_with_template_name(self):
        """Test adding template_name system variable"""
        variables = TemplateVariables()
        variables.add_system_variables(template_name="my-template")
        
        assert variables.get_variable("template_name") == "my-template"

    def test_add_system_variables_with_template_version(self):
        """Test adding template_version system variable"""
        variables = TemplateVariables()
        variables.add_system_variables(template_version="1.0")
        
        assert variables.get_variable("template_version") == "1.0"

    def test_add_system_variables_without_template_metadata(self):
        """Test that template metadata is not added when not provided"""
        variables = TemplateVariables()
        variables.add_system_variables()
        
        assert "template_name" not in variables
        assert "template_version" not in variables


class TestTemplateVariablesAddSystemVariableWithFormat:
    """Tests for adding custom-formatted system variables"""

    def test_add_system_variable_with_format(self):
        """Test adding custom-formatted system variable"""
        fixed_time = datetime(2024, 6, 15, 10, 30, 45)
        variables = TemplateVariables()
        variables.add_system_variable_with_format(
            "custom_date", "%B %d, %Y", now=fixed_time
        )
        
        assert variables.get_variable("custom_date") == "June 15, 2024"

    def test_add_system_variable_with_format_default_time(self):
        """Test that default time is used when not provided"""
        variables = TemplateVariables()
        variables.add_system_variable_with_format("year_only", "%Y")
        
        # Should have current year
        current_year = datetime.now().strftime("%Y")
        assert variables.get_variable("year_only") == current_year

    def test_add_system_variable_with_invalid_format(self):
        """Test that invalid format raises error"""
        variables = TemplateVariables()
        
        # This will raise ValueError from strftime
        with pytest.raises(VariableSubstitutionError) as exc_info:
            variables.add_system_variable_with_format("invalid", "%Q")
        
        assert "invalid" in str(exc_info.value)


class TestTemplateVariablesAddPromptVariables:
    """Tests for adding prompt-sourced variables"""

    def test_add_prompt_variables(self, prompt_values):
        """Test adding prompt variables"""
        variables = TemplateVariables()
        variables.add_prompt_variables(prompt_values)
        
        assert variables.get_variable("author_name") == "Test Author"
        assert variables.get_variable("license_type") == "Apache-2.0"

    def test_add_prompt_variables_empty_dict(self):
        """Test adding empty prompt values"""
        variables = TemplateVariables()
        variables.add_prompt_variables({})
        
        assert len(variables) == 0

    def test_add_prompt_variables_overwrites_existing(self):
        """Test that prompt values overwrite existing variables"""
        variables = TemplateVariables()
        variables.add_variable("author_name", "Original Author")
        variables.add_prompt_variables({"author_name": "New Author"})
        
        assert variables.get_variable("author_name") == "New Author"


class TestTemplateVariablesRegisterPromptDefinition:
    """Tests for registering prompt variable definitions"""

    def test_register_prompt_definition_basic(self):
        """Test registering a prompt definition"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        
        assert len(variables._prompt_definitions) == 1
        assert variables._prompt_definitions[0]["name"] == "author_name"

    def test_register_prompt_definition_with_default(self):
        """Test registering prompt with default value"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt", default="Unknown")
        
        # Default should be added to variables
        assert variables.get_variable("author_name") == "Unknown"

    def test_register_prompt_definition_no_default_no_variable(self):
        """Test that prompt without default doesn't add variable"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        
        assert "author_name" not in variables

    def test_register_prompt_definition_existing_variable_not_overwritten(self):
        """Test that existing variable is not overwritten by default"""
        variables = TemplateVariables()
        variables.add_variable("author_name", "Existing")
        variables.register_prompt_definition("author_name", "prompt", default="Default")
        
        assert variables.get_variable("author_name") == "Existing"


class TestTemplateVariablesGetPendingPrompts:
    """Tests for getting pending prompt definitions"""

    def test_get_pending_prompts_all_pending(self):
        """Test getting prompts when none are resolved"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        variables.register_prompt_definition("license", "prompt")
        
        pending = variables.get_pending_prompts()
        
        assert len(pending) == 2
        assert any(p["name"] == "author_name" for p in pending)
        assert any(p["name"] == "license" for p in pending)

    def test_get_pending_prompts_some_resolved(self):
        """Test getting prompts when some are resolved"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        variables.register_prompt_definition("license", "prompt")
        variables.add_variable("author_name", "Test Author")
        
        pending = variables.get_pending_prompts()
        
        assert len(pending) == 1
        assert pending[0]["name"] == "license"

    def test_get_pending_prompts_all_resolved(self):
        """Test getting prompts when all are resolved"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt")
        variables.add_variable("author_name", "Test Author")
        
        pending = variables.get_pending_prompts()
        
        assert len(pending) == 0

    def test_get_pending_prompts_with_defaults(self):
        """Test that prompts with defaults that set variables are not pending"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author_name", "prompt", default="Unknown")
        
        pending = variables.get_pending_prompts()
        
        # Should not be pending because default was applied
        assert len(pending) == 0


class TestTemplateVariablesResolveFromTemplateDefinition:
    """Tests for resolving variables from template definition"""

    def test_resolve_entity_variables(self, sample_entity_data):
        """Test resolving entity-sourced variables"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "id", "source": "entity"},
            ],
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"

    def test_resolve_system_variables(self, sample_entity_data):
        """Test resolving system-sourced variables"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "year", "source": "system"},
                {"name": "date", "source": "system"},
            ],
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        assert "year" in variables
        assert "date" in variables

    def test_resolve_system_variable_with_format(self, sample_entity_data):
        """Test resolving system variable with custom format"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "custom_date", "source": "system", "format": "%Y-%m-%d"},
            ],
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        assert "custom_date" in variables

    def test_resolve_prompt_variables(self, sample_entity_data):
        """Test resolving prompt-sourced variables"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "author_name", "source": "prompt", "default": "Unknown"},
            ],
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        # Default should be applied
        assert variables.get_variable("author_name") == "Unknown"

    def test_resolve_adds_template_metadata(self, sample_entity_data):
        """Test that template name and version are added as system variables"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        assert variables.get_variable("template_name") == "test-template"
        assert variables.get_variable("template_version") == "1.0"

    def test_resolve_also_adds_entity_variables(self, sample_entity_data):
        """Test that entity variables are also added directly"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        # Entity variables should be added even without explicit definitions
        assert "title" in variables
        assert "id" in variables

    def test_resolve_entity_variable_with_default_fallback(self, sample_entity_data_minimal):
        """Test that default is used when entity field is missing"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "description", "source": "entity", "default": "No description"},
            ],
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(
            template_data, sample_entity_data_minimal
        )
        
        assert variables.get_variable("description") == "No description"

    def test_resolve_empty_variables_list(self, sample_entity_data):
        """Test resolving with empty variables list"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [],
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        # Should still have entity and system variables
        assert "title" in variables
        assert "date" in variables

    def test_resolve_no_variables_key(self, sample_entity_data):
        """Test resolving when variables key is missing"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
        }
        
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        # Should still work
        assert "title" in variables


class TestTemplateVariablesSubstitute:
    """Tests for variable substitution in content"""

    def test_substitute_single_variable(self):
        """Test substituting a single variable"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        result = variables.substitute("# {{title}}")
        
        assert result == "# My Project"

    def test_substitute_multiple_variables(self):
        """Test substituting multiple variables"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        variables.add_variable("author", "Test Author")
        
        result = variables.substitute("# {{title}}\n\nBy {{author}}")
        
        assert result == "# My Project\n\nBy Test Author"

    def test_substitute_same_variable_multiple_times(self):
        """Test substituting same variable multiple times"""
        variables = TemplateVariables()
        variables.add_variable("name", "Test")
        
        result = variables.substitute("{{name}} is {{name}}")
        
        assert result == "Test is Test"

    def test_substitute_with_spaces_in_braces(self):
        """Test substituting with spaces around variable name"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        result = variables.substitute("# {{ title }}")
        
        assert result == "# My Project"

    def test_substitute_none_value(self):
        """Test substituting None value becomes empty string"""
        variables = TemplateVariables()
        variables.add_variable("empty", None)
        
        result = variables.substitute("Value: {{empty}}")
        
        assert result == "Value: "

    def test_substitute_integer_value(self):
        """Test substituting integer value"""
        variables = TemplateVariables()
        variables.add_variable("count", 42)
        
        result = variables.substitute("Count: {{count}}")
        
        assert result == "Count: 42"

    def test_substitute_undefined_variable_non_strict(self):
        """Test that undefined variable is left as-is in non-strict mode"""
        variables = TemplateVariables()
        
        result = variables.substitute("# {{undefined}}")
        
        assert result == "# {{undefined}}"

    def test_substitute_undefined_variable_strict_mode(self):
        """Test that undefined variable raises error in strict mode"""
        variables = TemplateVariables()
        variables.set_strict_mode(True)
        
        with pytest.raises(UndefinedVariableError) as exc_info:
            variables.substitute("# {{undefined}}")
        
        assert "undefined" in str(exc_info.value)

    def test_substitute_empty_content(self):
        """Test substituting in empty content"""
        variables = TemplateVariables()
        
        result = variables.substitute("")
        
        assert result == ""

    def test_substitute_no_variables(self):
        """Test substituting content with no variables"""
        variables = TemplateVariables()
        
        result = variables.substitute("No variables here")
        
        assert result == "No variables here"

    def test_substitute_multiline_content(self):
        """Test substituting in multiline content"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        variables.add_variable("description", "A great project")
        
        content = """# {{title}}

## Description

{{description}}
"""
        result = variables.substitute(content)
        
        assert "# My Project" in result
        assert "A great project" in result


class TestTemplateVariablesSubstitutePath:
    """Tests for variable substitution in paths"""

    def test_substitute_path_basic(self):
        """Test basic path substitution"""
        variables = TemplateVariables()
        variables.add_variable("id", "my_project")
        
        result = variables.substitute_path("src/{{id}}")
        
        assert result == "src/my_project"

    def test_substitute_path_multiple_variables(self):
        """Test path substitution with multiple variables"""
        variables = TemplateVariables()
        variables.add_variable("org", "myorg")
        variables.add_variable("project", "myproject")
        
        result = variables.substitute_path("src/{{org}}/{{project}}")
        
        assert result == "src/myorg/myproject"

    def test_substitute_path_rejects_traversal(self):
        """Test that path traversal in result is rejected"""
        variables = TemplateVariables()
        variables.add_variable("dir", "../outside")
        
        with pytest.raises(VariableSubstitutionError) as exc_info:
            variables.substitute_path("src/{{dir}}")
        
        assert "traversal" in str(exc_info.value).lower()

    def test_substitute_path_undefined_non_strict(self):
        """Test that undefined variable in path is left as-is in non-strict"""
        variables = TemplateVariables()
        
        result = variables.substitute_path("src/{{undefined}}")
        
        assert result == "src/{{undefined}}"

    def test_substitute_path_undefined_strict(self):
        """Test that undefined variable in path raises error in strict mode"""
        variables = TemplateVariables()
        variables.set_strict_mode(True)
        
        with pytest.raises(UndefinedVariableError):
            variables.substitute_path("src/{{undefined}}")


class TestTemplateVariablesFindVariables:
    """Tests for finding variables in content"""

    def test_find_variables_single(self):
        """Test finding a single variable"""
        variables = TemplateVariables()
        
        result = variables.find_variables_in_content("# {{title}}")
        
        assert result == ["title"]

    def test_find_variables_multiple(self):
        """Test finding multiple variables"""
        variables = TemplateVariables()
        
        result = variables.find_variables_in_content("{{title}} by {{author}}")
        
        assert "title" in result
        assert "author" in result

    def test_find_variables_duplicate_returns_unique(self):
        """Test that duplicate variables are returned once"""
        variables = TemplateVariables()
        
        result = variables.find_variables_in_content("{{name}} is {{name}}")
        
        assert result == ["name"]

    def test_find_variables_preserves_order(self):
        """Test that variables are returned in order of first occurrence"""
        variables = TemplateVariables()
        
        result = variables.find_variables_in_content("{{first}} {{second}} {{first}}")
        
        assert result == ["first", "second"]

    def test_find_variables_empty_content(self):
        """Test finding variables in empty content"""
        variables = TemplateVariables()
        
        result = variables.find_variables_in_content("")
        
        assert result == []

    def test_find_variables_no_variables(self):
        """Test finding variables when none present"""
        variables = TemplateVariables()
        
        result = variables.find_variables_in_content("No variables here")
        
        assert result == []


class TestTemplateVariablesFindUndefined:
    """Tests for finding undefined variables"""

    def test_find_undefined_all_undefined(self):
        """Test finding undefined when all are undefined"""
        variables = TemplateVariables()
        
        result = variables.find_undefined_variables("{{title}} {{author}}")
        
        assert "title" in result
        assert "author" in result

    def test_find_undefined_some_defined(self):
        """Test finding undefined when some are defined"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        result = variables.find_undefined_variables("{{title}} {{author}}")
        
        assert "title" not in result
        assert "author" in result

    def test_find_undefined_all_defined(self):
        """Test finding undefined when all are defined"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        variables.add_variable("author", "Test Author")
        
        result = variables.find_undefined_variables("{{title}} {{author}}")
        
        assert result == []

    def test_find_undefined_empty_content(self):
        """Test finding undefined in empty content"""
        variables = TemplateVariables()
        
        result = variables.find_undefined_variables("")
        
        assert result == []


class TestTemplateVariablesValidateContent:
    """Tests for validate_content method"""

    def test_validate_content_all_defined(self):
        """Test validation when all variables are defined"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        result = variables.validate_content("# {{title}}")
        
        assert result == []

    def test_validate_content_some_undefined(self):
        """Test validation when some variables are undefined"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        result = variables.validate_content("{{title}} {{undefined}}")
        
        assert "undefined" in result
        assert "title" not in result

    def test_validate_content_empty(self):
        """Test validation of empty content"""
        variables = TemplateVariables()
        
        result = variables.validate_content("")
        
        assert result == []


class TestTemplateVariablesStrictMode:
    """Tests for strict mode behavior"""

    def test_set_strict_mode_true(self):
        """Test setting strict mode to True"""
        variables = TemplateVariables()
        variables.set_strict_mode(True)
        
        assert variables._strict_mode is True

    def test_set_strict_mode_false(self):
        """Test setting strict mode to False"""
        variables = TemplateVariables()
        variables.set_strict_mode(True)
        variables.set_strict_mode(False)
        
        assert variables._strict_mode is False

    def test_strict_mode_affects_substitution(self):
        """Test that strict mode affects substitution behavior"""
        variables = TemplateVariables()
        
        # Non-strict - should not raise
        result = variables.substitute("{{undefined}}")
        assert result == "{{undefined}}"
        
        # Strict - should raise
        variables.set_strict_mode(True)
        with pytest.raises(UndefinedVariableError):
            variables.substitute("{{undefined}}")


class TestTemplateVariablesClear:
    """Tests for clear method"""

    def test_clear_removes_all_variables(self):
        """Test that clear removes all variables"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        variables.add_variable("author", "Test Author")
        
        variables.clear()
        
        assert len(variables) == 0
        assert variables.available_variables == []

    def test_clear_removes_prompt_definitions(self):
        """Test that clear removes prompt definitions"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author", "prompt")
        
        variables.clear()
        
        assert variables._prompt_definitions == []


class TestTemplateVariablesCopy:
    """Tests for copy method"""

    def test_copy_creates_new_instance(self):
        """Test that copy creates a new instance"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        copied = variables.copy()
        
        assert copied is not variables
        assert copied.get_variable("title") == "My Project"

    def test_copy_independent_variables(self):
        """Test that copied variables are independent"""
        variables = TemplateVariables()
        variables.add_variable("title", "Original")
        
        copied = variables.copy()
        copied.add_variable("title", "Modified")
        
        assert variables.get_variable("title") == "Original"
        assert copied.get_variable("title") == "Modified"

    def test_copy_preserves_strict_mode(self):
        """Test that copy preserves strict mode setting"""
        variables = TemplateVariables()
        variables.set_strict_mode(True)
        
        copied = variables.copy()
        
        assert copied._strict_mode is True

    def test_copy_preserves_prompt_definitions(self):
        """Test that copy preserves prompt definitions"""
        variables = TemplateVariables()
        variables.register_prompt_definition("author", "prompt")
        
        copied = variables.copy()
        
        assert len(copied._prompt_definitions) == 1


class TestTemplateVariablesFactoryMethods:
    """Tests for factory class methods"""

    def test_from_entity_and_template(
        self, sample_entity_data, full_template_data, prompt_values
    ):
        """Test from_entity_and_template factory method"""
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=full_template_data,
            prompt_values=prompt_values,
        )
        
        # Should have entity variables
        assert variables.get_variable("title") == "My Project"
        
        # Should have system variables
        assert "date" in variables
        assert "year" in variables
        
        # Should have prompt values
        assert variables.get_variable("author_name") == "Test Author"

    def test_from_entity_and_template_without_prompts(
        self, sample_entity_data, minimal_template_data
    ):
        """Test factory method without prompt values"""
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=minimal_template_data,
            prompt_values=None,
        )
        
        assert "title" in variables
        assert "date" in variables

    def test_from_entity(self, sample_entity_data):
        """Test from_entity factory method"""
        variables = TemplateVariables.from_entity(sample_entity_data)
        
        # Should have entity variables
        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"
        
        # Should have system variables
        assert "date" in variables
        assert "year" in variables


class TestTemplateVariablesDunderMethods:
    """Tests for special (dunder) methods"""

    def test_repr(self):
        """Test __repr__ method"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        variables.register_prompt_definition("author", "prompt")
        
        repr_str = repr(variables)
        
        assert "TemplateVariables" in repr_str
        assert "variables=1" in repr_str
        assert "prompts=1" in repr_str

    def test_getitem(self):
        """Test __getitem__ (bracket notation) for existing variable"""
        variables = TemplateVariables()
        variables.add_variable("title", "My Project")
        
        assert variables["title"] == "My Project"

    def test_getitem_undefined_raises(self):
        """Test __getitem__ raises for undefined variable"""
        variables = TemplateVariables()
        
        with pytest.raises(UndefinedVariableError):
            _ = variables["undefined"]

    def test_setitem(self):
        """Test __setitem__ (bracket notation)"""
        variables = TemplateVariables()
        variables["title"] = "My Project"
        
        assert variables.get_variable("title") == "My Project"


class TestEscapeForSubstitution:
    """Tests for escape_for_substitution helper function"""

    def test_escape_double_braces(self):
        """Test escaping double braces"""
        result = escape_for_substitution("{{variable}}")
        
        assert result == "{ {variable} }"

    def test_escape_no_braces(self):
        """Test string without braces is unchanged"""
        result = escape_for_substitution("no braces here")
        
        assert result == "no braces here"

    def test_escape_single_braces(self):
        """Test single braces are not escaped"""
        result = escape_for_substitution("{single}")
        
        assert result == "{single}"

    def test_escape_empty_string(self):
        """Test escaping empty string"""
        result = escape_for_substitution("")
        
        assert result == ""


class TestValidateVariableName:
    """Tests for validate_variable_name helper function"""

    def test_validate_simple_name(self):
        """Test validating simple variable name"""
        assert validate_variable_name("title") is True

    def test_validate_name_with_underscore(self):
        """Test validating name with underscore"""
        assert validate_variable_name("my_variable") is True

    def test_validate_name_starting_with_underscore(self):
        """Test validating name starting with underscore"""
        assert validate_variable_name("_private") is True

    def test_validate_name_with_numbers(self):
        """Test validating name with numbers"""
        assert validate_variable_name("var123") is True

    def test_validate_name_starting_with_number(self):
        """Test that name starting with number is invalid"""
        assert validate_variable_name("123var") is False

    def test_validate_name_with_dash(self):
        """Test that name with dash is invalid"""
        assert validate_variable_name("my-variable") is False

    def test_validate_name_with_special_chars(self):
        """Test that name with special characters is invalid"""
        assert validate_variable_name("var!") is False
        assert validate_variable_name("var@name") is False

    def test_validate_empty_name(self):
        """Test that empty name is invalid"""
        assert validate_variable_name("") is False

    def test_validate_name_with_spaces(self):
        """Test that name with spaces is invalid"""
        assert validate_variable_name("my variable") is False


class TestExtractVariables:
    """Tests for extract_variables module-level function"""

    def test_extract_single_variable(self):
        """Test extracting a single variable"""
        result = extract_variables("# {{title}}")
        
        assert result == ["title"]

    def test_extract_multiple_variables(self):
        """Test extracting multiple variables"""
        result = extract_variables("{{title}} by {{author}}")
        
        assert "title" in result
        assert "author" in result

    def test_extract_empty_content(self):
        """Test extracting from empty content"""
        result = extract_variables("")
        
        assert result == []

    def test_extract_no_variables(self):
        """Test extracting when no variables present"""
        result = extract_variables("No variables here")
        
        assert result == []


class TestExceptionClasses:
    """Tests for custom exception classes"""

    def test_variable_error_is_exception(self):
        """Test that VariableError is an Exception"""
        error = VariableError("test error")
        assert isinstance(error, Exception)

    def test_undefined_variable_error_is_variable_error(self):
        """Test that UndefinedVariableError inherits from VariableError"""
        error = UndefinedVariableError("undefined")
        assert isinstance(error, VariableError)
        assert isinstance(error, Exception)

    def test_undefined_variable_error_stores_name(self):
        """Test that UndefinedVariableError stores variable name"""
        error = UndefinedVariableError("my_var")
        assert error.variable_name == "my_var"

    def test_undefined_variable_error_stores_available(self):
        """Test that UndefinedVariableError stores available variables"""
        available = ["title", "author"]
        error = UndefinedVariableError("undefined", available_variables=available)
        
        assert error.available_variables == available

    def test_undefined_variable_error_message(self):
        """Test UndefinedVariableError message format"""
        error = UndefinedVariableError("undefined")
        
        assert "undefined" in str(error)
        assert "Undefined" in str(error)

    def test_undefined_variable_error_message_with_available(self):
        """Test UndefinedVariableError message includes available variables"""
        error = UndefinedVariableError("undefined", available_variables=["title"])
        
        assert "undefined" in str(error)
        assert "title" in str(error)

    def test_variable_substitution_error_is_variable_error(self):
        """Test that VariableSubstitutionError inherits from VariableError"""
        error = VariableSubstitutionError("substitution failed")
        assert isinstance(error, VariableError)
        assert isinstance(error, Exception)

    def test_variable_substitution_error_stores_name(self):
        """Test that VariableSubstitutionError stores variable name"""
        error = VariableSubstitutionError("failed", variable_name="my_var")
        assert error.variable_name == "my_var"


class TestTemplateVariablesEntityVarsConstant:
    """Tests for ENTITY_VARS constant"""

    def test_entity_vars_contains_expected_fields(self):
        """Test that ENTITY_VARS contains expected entity fields"""
        expected_fields = [
            "title",
            "id",
            "uid",
            "description",
            "category",
            "status",
            "type",
        ]
        for field in expected_fields:
            assert field in TemplateVariables.ENTITY_VARS

    def test_entity_vars_is_frozenset(self):
        """Test that ENTITY_VARS is a frozenset (immutable)"""
        assert isinstance(TemplateVariables.ENTITY_VARS, frozenset)


class TestTemplateVariablesSystemVarsConstant:
    """Tests for SYSTEM_VARS constant"""

    def test_system_vars_contains_expected_fields(self):
        """Test that SYSTEM_VARS contains expected system fields"""
        expected_fields = [
            "date",
            "year",
            "month",
            "day",
            "timestamp",
            "template_name",
            "template_version",
        ]
        for field in expected_fields:
            assert field in TemplateVariables.SYSTEM_VARS

    def test_system_vars_is_frozenset(self):
        """Test that SYSTEM_VARS is a frozenset (immutable)"""
        assert isinstance(TemplateVariables.SYSTEM_VARS, frozenset)


class TestTemplateVariablesVariablePattern:
    """Tests for VARIABLE_PATTERN regex"""

    def test_pattern_matches_simple_variable(self):
        """Test pattern matches simple variable"""
        import re
        match = TemplateVariables.VARIABLE_PATTERN.search("{{title}}")
        
        assert match is not None
        assert match.group(1) == "title"

    def test_pattern_matches_with_spaces(self):
        """Test pattern matches with spaces"""
        match = TemplateVariables.VARIABLE_PATTERN.search("{{ title }}")
        
        assert match is not None
        assert match.group(1) == "title"

    def test_pattern_matches_underscore_variable(self):
        """Test pattern matches variable with underscore"""
        match = TemplateVariables.VARIABLE_PATTERN.search("{{my_variable}}")
        
        assert match is not None
        assert match.group(1) == "my_variable"

    def test_pattern_matches_variable_with_numbers(self):
        """Test pattern matches variable with numbers"""
        match = TemplateVariables.VARIABLE_PATTERN.search("{{var123}}")
        
        assert match is not None
        assert match.group(1) == "var123"

    def test_pattern_does_not_match_invalid_names(self):
        """Test pattern does not match invalid variable names"""
        # Starting with number
        match = TemplateVariables.VARIABLE_PATTERN.search("{{123var}}")
        assert match is None
        
        # With dash
        match = TemplateVariables.VARIABLE_PATTERN.search("{{my-var}}")
        assert match is None

    def test_pattern_finds_all_variables(self):
        """Test pattern findall finds all variables"""
        matches = TemplateVariables.VARIABLE_PATTERN.findall(
            "{{title}} and {{author}}"
        )
        
        assert "title" in matches
        assert "author" in matches


class TestTemplateVariablesIntegration:
    """Integration tests for template variables"""

    def test_full_workflow(
        self, sample_entity_data, full_template_data, prompt_values
    ):
        """Test full variable resolution and substitution workflow"""
        # Create variables from template
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=full_template_data,
            prompt_values=prompt_values,
        )
        
        # Substitute in content
        content = "# {{title}}\n\nBy: {{author_name}}\nYear: {{year}}"
        result = variables.substitute(content)
        
        assert "My Project" in result
        assert "Test Author" in result
        # Year should be current or from system
        assert "{{year}}" not in result

    def test_path_substitution_workflow(self, sample_entity_data):
        """Test path substitution workflow"""
        variables = TemplateVariables.from_entity(sample_entity_data)
        
        path = "src/{{id}}/__init__.py"
        result = variables.substitute_path(path)
        
        assert result == "src/my_project/__init__.py"

    def test_validate_before_substitute(self, sample_entity_data):
        """Test validating content before substituting"""
        variables = TemplateVariables.from_entity(sample_entity_data)
        
        content = "{{title}} {{undefined_var}}"
        
        # Validate first
        issues = variables.validate_content(content)
        assert "undefined_var" in issues
        
        # Non-strict substitution still works
        result = variables.substitute(content)
        assert "My Project" in result
        assert "{{undefined_var}}" in result

    def test_prompt_resolution_workflow(self, sample_entity_data):
        """Test prompt variable resolution workflow"""
        template_data = {
            "name": "test-template",
            "version": "1.0",
            "variables": [
                {"name": "author_name", "source": "prompt"},
                {"name": "license", "source": "prompt", "default": "MIT"},
            ],
        }
        
        # Create variables without prompt values
        variables = TemplateVariables()
        variables.resolve_from_template_definition(template_data, sample_entity_data)
        
        # Check pending prompts
        pending = variables.get_pending_prompts()
        assert len(pending) == 1  # Only author_name (license has default)
        assert pending[0]["name"] == "author_name"
        
        # Provide prompt values
        variables.add_prompt_variables({"author_name": "Test Author"})
        
        # No more pending prompts
        pending = variables.get_pending_prompts()
        assert len(pending) == 0

    def test_multiline_file_content(self, sample_entity_data):
        """Test substitution in multiline file content"""
        variables = TemplateVariables.from_entity(sample_entity_data)
        
        content = """# {{title}}

## Description

{{description}}

## Details

- ID: {{id}}
- UID: {{uid}}
- Status: {{status}}
"""
        result = variables.substitute(content)
        
        assert "# My Project" in result
        assert "A sample project for testing" in result
        assert "my_project" in result
        assert "abc12345" in result
        assert "active" in result


# Additional fixtures specific to these tests
@pytest.fixture
def minimal_template_data():
    """Return a minimal template definition for testing."""
    return {
        "name": "minimal-template",
        "version": "1.0",
    }