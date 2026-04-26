"""
HoxCore Template Module.

This module provides the declarative template scaffolding system that allows
HoxCore to create folder structures, files, and initialize repositories when
creating new entities. Templates are purely declarative and secure - no scripts
or executable code is allowed.

The template system consists of:

- **Schema**: Template definition validation and security checks
- **Parser**: YAML template loading and parsing
- **Resolver**: Template path resolution from various sources
- **Variables**: Variable substitution for entity, system, and prompt sources
- **Executor**: Scaffolding execution with dry-run support

Template Definition Format:
    Templates are defined in YAML with a strict, declarative schema including:
    - name, version, description, author metadata
    - variables: entity, system, or prompt-sourced values
    - structure: directories to create
    - files: files to create with content or template references
    - copy: files to copy from template assets
    - git: repository initialization options

Security Constraints:
    Templates are declarative only with these restrictions:
    - No shell command execution
    - No script execution
    - No network access
    - No arbitrary file reading
    - No path traversal (../)
    - Only read from designated template directories

Example Usage:
    >>> from hxc.templates import (
    ...     validate_template,
    ...     TemplateParser,
    ...     TemplateResolver,
    ...     TemplateExecutor,
    ...     TemplateVariables,
    ... )
    >>>
    >>> # Validate a template definition
    >>> template_data = {"name": "my-template", "version": "1.0"}
    >>> validate_template(template_data)
    True
    >>>
    >>> # Parse a template file
    >>> parser = TemplateParser()
    >>> template = parser.parse("~/.hxc/templates/software.dev/cli-tool/default.yml")
    >>>
    >>> # Resolve a template reference
    >>> resolver = TemplateResolver(registry_path="/path/to/registry")
    >>> template_path = resolver.resolve("software.dev/cli-tool.default")
    >>>
    >>> # Execute scaffolding
    >>> executor = TemplateExecutor(template, variables)
    >>> executor.execute(output_path="/path/to/output", dry_run=False)
"""

from hxc.templates.schema import (
    # Schema definition
    TEMPLATE_SCHEMA,
    VALID_SOURCES,
    VALID_STRUCTURE_TYPES,
    VARIABLE_NAME_PATTERN,
    # Validation functions
    validate_template,
    validate_structure_entry,
    validate_file_entry,
    validate_copy_entry,
    validate_variable_entry,
    validate_git_config,
    validate_path_security,
    # Exception classes
    TemplateSchemaError,
    InvalidTemplateError,
    MissingRequiredFieldError,
    InvalidPathError,
    PathTraversalError,
)

from hxc.templates.parser import (
    TemplateParser,
    TemplateParserError,
    TemplateNotFoundError,
    TemplateLoadError,
)

from hxc.templates.resolver import (
    TemplateResolver,
    TemplateResolverError,
    TemplateResolutionError,
    CategoryVariant,
)

from hxc.templates.variables import (
    TemplateVariables,
    VariableError,
    UndefinedVariableError,
    VariableSubstitutionError,
)

from hxc.templates.executor import (
    TemplateExecutor,
    ExecutorError,
    ScaffoldError,
    DirectoryCreationError,
    FileCreationError,
    FileCopyError,
    GitInitError,
    ScaffoldResult,
)

__all__ = [
    # Schema constants
    "TEMPLATE_SCHEMA",
    "VALID_SOURCES",
    "VALID_STRUCTURE_TYPES",
    "VARIABLE_NAME_PATTERN",
    # Schema validation functions
    "validate_template",
    "validate_structure_entry",
    "validate_file_entry",
    "validate_copy_entry",
    "validate_variable_entry",
    "validate_git_config",
    "validate_path_security",
    # Schema exceptions
    "TemplateSchemaError",
    "InvalidTemplateError",
    "MissingRequiredFieldError",
    "InvalidPathError",
    "PathTraversalError",
    # Parser
    "TemplateParser",
    "TemplateParserError",
    "TemplateNotFoundError",
    "TemplateLoadError",
    # Resolver
    "TemplateResolver",
    "TemplateResolverError",
    "TemplateResolutionError",
    "CategoryVariant",
    # Variables
    "TemplateVariables",
    "VariableError",
    "UndefinedVariableError",
    "VariableSubstitutionError",
    # Executor
    "TemplateExecutor",
    "ExecutorError",
    "ScaffoldError",
    "DirectoryCreationError",
    "FileCreationError",
    "FileCopyError",
    "GitInitError",
    "ScaffoldResult",
]