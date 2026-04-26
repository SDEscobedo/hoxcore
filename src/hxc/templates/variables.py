"""
HoxCore Template Variables.

This module provides variable resolution and substitution for template
scaffolding. Variables can be sourced from entity data, system information,
or user prompts. Substitution is performed safely without code execution.

Variable Sources:
    - entity: Values from the entity definition (title, id, uid, etc.)
    - system: Generated at scaffold time (date, year, timestamp, etc.)
    - prompt: User-provided values during scaffolding

Security:
    - No eval() or exec() - all substitution is string-based
    - Variables are escaped to prevent injection
    - Only predefined variable names are allowed
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union


class VariableError(Exception):
    """Base exception for variable-related errors"""

    pass


class UndefinedVariableError(VariableError):
    """Raised when a referenced variable is not defined"""

    def __init__(self, variable_name: str, available_variables: Optional[List[str]] = None):
        self.variable_name = variable_name
        self.available_variables = available_variables or []
        message = f"Undefined variable: {variable_name}"
        if available_variables:
            available_str = ", ".join(sorted(available_variables))
            message += f". Available variables: {available_str}"
        super().__init__(message)


class VariableSubstitutionError(VariableError):
    """Raised when variable substitution fails"""

    def __init__(self, message: str, variable_name: Optional[str] = None):
        self.variable_name = variable_name
        super().__init__(message)


class TemplateVariables:
    """
    Variable resolution and substitution for template scaffolding.

    This class handles collecting variables from multiple sources and
    performing safe string substitution in template content.

    Example Usage:
        >>> variables = TemplateVariables()
        >>> variables.add_entity_variables({"title": "My Project", "id": "my-proj"})
        >>> variables.add_system_variables()
        >>> result = variables.substitute("# {{title}}\n\nID: {{id}}")
        >>> print(result)
        # My Project

        ID: my-proj

    Attributes:
        ENTITY_VARS: Set of valid entity variable names
        SYSTEM_VARS: Set of valid system variable names
        VARIABLE_PATTERN: Regex pattern for variable placeholders
    """

    # Valid entity variables that can be sourced from entity data
    ENTITY_VARS: Set[str] = frozenset({
        "title",
        "id",
        "uid",
        "description",
        "category",
        "status",
        "type",
        "start_date",
        "due_date",
        "completion_date",
        "duration_estimate",
        "parent",
        "template",
    })

    # Valid system variables generated at scaffold time
    SYSTEM_VARS: Set[str] = frozenset({
        "date",
        "year",
        "month",
        "day",
        "timestamp",
        "template_name",
        "template_version",
        "datetime",
        "time",
        "weekday",
        "iso_date",
    })

    # Regex pattern for variable placeholders: {{variable_name}}
    # Allows alphanumeric characters and underscores
    VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")

    def __init__(self):
        """Initialize the template variables container."""
        self._variables: Dict[str, Any] = {}
        self._prompt_definitions: List[Dict[str, Any]] = []
        self._strict_mode: bool = False

    @property
    def variables(self) -> Dict[str, Any]:
        """Get all resolved variables."""
        return dict(self._variables)

    @property
    def available_variables(self) -> List[str]:
        """Get list of available variable names."""
        return sorted(self._variables.keys())

    def set_strict_mode(self, strict: bool) -> None:
        """
        Set strict mode for variable substitution.

        In strict mode, undefined variables raise UndefinedVariableError.
        In non-strict mode, undefined variables are left as-is.

        Args:
            strict: Whether to enable strict mode
        """
        self._strict_mode = strict

    def add_variable(self, name: str, value: Any) -> None:
        """
        Add a single variable.

        Args:
            name: Variable name
            value: Variable value (will be converted to string during substitution)
        """
        self._variables[name] = value

    def add_variables(self, variables: Dict[str, Any]) -> None:
        """
        Add multiple variables at once.

        Args:
            variables: Dictionary of variable names to values
        """
        self._variables.update(variables)

    def get_variable(self, name: str, default: Any = None) -> Any:
        """
        Get a variable value.

        Args:
            name: Variable name
            default: Default value if variable not found

        Returns:
            Variable value or default
        """
        return self._variables.get(name, default)

    def has_variable(self, name: str) -> bool:
        """
        Check if a variable is defined.

        Args:
            name: Variable name

        Returns:
            True if variable is defined
        """
        return name in self._variables

    def add_entity_variables(self, entity_data: Dict[str, Any]) -> None:
        """
        Add variables from entity data.

        Only recognized entity variable names are extracted from the entity
        data. Unknown fields are ignored for security.

        Args:
            entity_data: Entity data dictionary
        """
        for var_name in self.ENTITY_VARS:
            if var_name in entity_data:
                value = entity_data[var_name]
                # Convert None to empty string
                if value is None:
                    value = ""
                self._variables[var_name] = value

    def add_system_variables(
        self,
        template_name: Optional[str] = None,
        template_version: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> None:
        """
        Add system-generated variables.

        System variables are generated at scaffold time and include
        date/time information and template metadata.

        Args:
            template_name: Name of the template being applied
            template_version: Version of the template
            now: DateTime to use (defaults to current time)
        """
        if now is None:
            now = datetime.now()

        # Date and time variables
        self._variables["date"] = now.strftime("%Y-%m-%d")
        self._variables["year"] = now.strftime("%Y")
        self._variables["month"] = now.strftime("%m")
        self._variables["day"] = now.strftime("%d")
        self._variables["time"] = now.strftime("%H:%M:%S")
        self._variables["datetime"] = now.strftime("%Y-%m-%d %H:%M:%S")
        self._variables["timestamp"] = str(int(now.timestamp()))
        self._variables["iso_date"] = now.isoformat()
        self._variables["weekday"] = now.strftime("%A")

        # Template metadata
        if template_name:
            self._variables["template_name"] = template_name
        if template_version:
            self._variables["template_version"] = template_version

    def add_system_variable_with_format(
        self,
        name: str,
        format_string: str,
        now: Optional[datetime] = None,
    ) -> None:
        """
        Add a custom-formatted system variable.

        Args:
            name: Variable name
            format_string: strftime format string
            now: DateTime to use (defaults to current time)
        """
        if now is None:
            now = datetime.now()

        try:
            self._variables[name] = now.strftime(format_string)
        except ValueError as e:
            raise VariableSubstitutionError(
                f"Invalid format string '{format_string}' for variable '{name}': {e}",
                variable_name=name,
            )

    def add_prompt_variables(self, prompt_values: Dict[str, Any]) -> None:
        """
        Add user-provided prompt variables.

        Args:
            prompt_values: Dictionary of prompt variable names to values
        """
        self._variables.update(prompt_values)

    def register_prompt_definition(
        self,
        name: str,
        source: str = "prompt",
        default: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """
        Register a prompt variable definition for later resolution.

        This stores the definition without resolving the value. The value
        must be provided later via add_prompt_variables() or by using
        a default value.

        Args:
            name: Variable name
            source: Variable source (should be "prompt")
            default: Default value if user doesn't provide one
            **kwargs: Additional definition fields (ignored)
        """
        definition = {
            "name": name,
            "source": source,
            "default": default,
        }
        self._prompt_definitions.append(definition)

        # If there's a default and the variable isn't already set, use it
        if default is not None and name not in self._variables:
            self._variables[name] = default

    def get_pending_prompts(self) -> List[Dict[str, Any]]:
        """
        Get prompt definitions that don't have values yet.

        Returns:
            List of prompt definitions without resolved values
        """
        return [
            defn for defn in self._prompt_definitions
            if defn["name"] not in self._variables
        ]

    def resolve_from_template_definition(
        self,
        template_data: Dict[str, Any],
        entity_data: Dict[str, Any],
    ) -> None:
        """
        Resolve variables from a template definition.

        This processes the template's variable definitions and resolves
        values from appropriate sources (entity, system, prompt).

        Args:
            template_data: Parsed template definition
            entity_data: Entity data for entity-sourced variables
        """
        variables = template_data.get("variables", [])

        # Add template metadata as system variables
        template_name = template_data.get("name")
        template_version = template_data.get("version")
        self.add_system_variables(
            template_name=template_name,
            template_version=template_version,
        )

        # Process each variable definition
        for var_def in variables:
            name = var_def.get("name")
            source = var_def.get("source", "entity")
            default = var_def.get("default")
            format_string = var_def.get("format")

            if not name:
                continue

            if source == "entity":
                # Get from entity data
                if name in entity_data:
                    self._variables[name] = entity_data[name]
                elif default is not None:
                    self._variables[name] = default

            elif source == "system":
                # Generate system variable
                if format_string:
                    self.add_system_variable_with_format(name, format_string)
                elif name not in self._variables:
                    # Use standard system variable if already added
                    if default is not None:
                        self._variables[name] = default

            elif source == "prompt":
                # Register for prompting
                self.register_prompt_definition(name, source, default)

        # Also add entity variables for common fields
        self.add_entity_variables(entity_data)

    def substitute(self, content: str) -> str:
        """
        Substitute variables in content string.

        Variables are referenced using {{variable_name}} syntax.
        In strict mode, undefined variables raise UndefinedVariableError.
        In non-strict mode, undefined variables are left as-is.

        Args:
            content: Content string with variable placeholders

        Returns:
            Content with variables substituted

        Raises:
            UndefinedVariableError: In strict mode, if a variable is undefined
        """
        if not content:
            return content

        def replace_variable(match: re.Match) -> str:
            var_name = match.group(1)

            if var_name in self._variables:
                value = self._variables[var_name]
                # Convert to string safely
                if value is None:
                    return ""
                return str(value)
            elif self._strict_mode:
                raise UndefinedVariableError(var_name, self.available_variables)
            else:
                # Leave as-is in non-strict mode
                return match.group(0)

        return self.VARIABLE_PATTERN.sub(replace_variable, content)

    def substitute_path(self, path: str) -> str:
        """
        Substitute variables in a file path.

        Similar to substitute() but also validates the result doesn't
        contain path traversal sequences.

        Args:
            path: Path string with variable placeholders

        Returns:
            Path with variables substituted

        Raises:
            UndefinedVariableError: In strict mode, if a variable is undefined
            VariableSubstitutionError: If result contains path traversal
        """
        result = self.substitute(path)

        # Security check: no path traversal in result
        if ".." in result:
            raise VariableSubstitutionError(
                f"Path traversal detected after substitution: {result}"
            )

        return result

    def find_variables_in_content(self, content: str) -> List[str]:
        """
        Find all variable references in content.

        Args:
            content: Content string to search

        Returns:
            List of variable names found in content
        """
        if not content:
            return []

        matches = self.VARIABLE_PATTERN.findall(content)
        # Return unique variable names in order of first occurrence
        seen: Set[str] = set()
        result: List[str] = []
        for var_name in matches:
            if var_name not in seen:
                seen.add(var_name)
                result.append(var_name)
        return result

    def find_undefined_variables(self, content: str) -> List[str]:
        """
        Find variable references in content that are not defined.

        Args:
            content: Content string to search

        Returns:
            List of undefined variable names found in content
        """
        referenced = self.find_variables_in_content(content)
        return [var for var in referenced if var not in self._variables]

    def validate_content(self, content: str) -> List[str]:
        """
        Validate that all variables in content are defined.

        Args:
            content: Content string to validate

        Returns:
            List of undefined variable names (empty if all valid)
        """
        return self.find_undefined_variables(content)

    def clear(self) -> None:
        """Clear all variables."""
        self._variables.clear()
        self._prompt_definitions.clear()

    def copy(self) -> "TemplateVariables":
        """
        Create a copy of this TemplateVariables instance.

        Returns:
            New TemplateVariables with same variables
        """
        new_vars = TemplateVariables()
        new_vars._variables = dict(self._variables)
        new_vars._prompt_definitions = list(self._prompt_definitions)
        new_vars._strict_mode = self._strict_mode
        return new_vars

    @classmethod
    def from_entity_and_template(
        cls,
        entity_data: Dict[str, Any],
        template_data: Dict[str, Any],
        prompt_values: Optional[Dict[str, Any]] = None,
    ) -> "TemplateVariables":
        """
        Create TemplateVariables from entity and template data.

        This is a convenience factory method that sets up all variable
        sources in one call.

        Args:
            entity_data: Entity data dictionary
            template_data: Parsed template definition
            prompt_values: Optional user-provided prompt values

        Returns:
            Configured TemplateVariables instance
        """
        variables = cls()
        variables.resolve_from_template_definition(template_data, entity_data)

        if prompt_values:
            variables.add_prompt_variables(prompt_values)

        return variables

    @classmethod
    def from_entity(cls, entity_data: Dict[str, Any]) -> "TemplateVariables":
        """
        Create TemplateVariables from entity data only.

        This creates a minimal variable set with just entity and system
        variables, useful for simple substitutions.

        Args:
            entity_data: Entity data dictionary

        Returns:
            Configured TemplateVariables instance
        """
        variables = cls()
        variables.add_entity_variables(entity_data)
        variables.add_system_variables()
        return variables

    def __repr__(self) -> str:
        """String representation of TemplateVariables."""
        var_count = len(self._variables)
        prompt_count = len(self._prompt_definitions)
        return f"TemplateVariables(variables={var_count}, prompts={prompt_count})"

    def __contains__(self, name: str) -> bool:
        """Check if variable is defined using 'in' operator."""
        return name in self._variables

    def __getitem__(self, name: str) -> Any:
        """Get variable value using bracket notation."""
        if name not in self._variables:
            raise UndefinedVariableError(name, self.available_variables)
        return self._variables[name]

    def __setitem__(self, name: str, value: Any) -> None:
        """Set variable value using bracket notation."""
        self._variables[name] = value

    def __len__(self) -> int:
        """Return number of defined variables."""
        return len(self._variables)


def escape_for_substitution(value: str) -> str:
    """
    Escape a string value for safe substitution.

    This escapes characters that could be interpreted specially
    in template content.

    Args:
        value: String value to escape

    Returns:
        Escaped string safe for substitution
    """
    # Escape double braces to prevent nested substitution attempts
    return value.replace("{{", "{ {").replace("}}", "} }")


def validate_variable_name(name: str) -> bool:
    """
    Validate that a variable name is valid.

    Variable names must:
    - Start with a letter or underscore
    - Contain only letters, numbers, and underscores

    Args:
        name: Variable name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    return bool(pattern.match(name))


def extract_variables(content: str) -> List[str]:
    """
    Extract all variable names from content.

    This is a module-level convenience function that wraps
    TemplateVariables.find_variables_in_content().

    Args:
        content: Content string to search

    Returns:
        List of unique variable names in order of first occurrence
    """
    return TemplateVariables().find_variables_in_content(content)