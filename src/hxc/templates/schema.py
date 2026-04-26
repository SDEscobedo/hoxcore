"""
HoxCore Template Schema validation.

This module provides the declarative template schema definition and validation
functions that ensure template definitions are correct, complete, and secure.
Templates are purely declarative with no script or executable code allowed.

Security Constraints:
    - No shell command execution
    - No script execution
    - No network access
    - No arbitrary file reading
    - No path traversal (../)
    - Only read from designated template directories
"""

import re
from typing import Any, Dict, List, Optional, Union


# Valid variable sources
VALID_SOURCES = frozenset({"entity", "system", "prompt"})

# Valid structure entry types
VALID_STRUCTURE_TYPES = frozenset({"directory"})

# Pattern for valid variable names (alphanumeric, underscore, must start with letter or underscore)
VARIABLE_NAME_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"

# Compiled regex for variable name validation
_VARIABLE_NAME_RE = re.compile(VARIABLE_NAME_PATTERN)

# Pattern to detect path traversal attempts
_PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",  # Unix parent directory
    r"\.\.\\",  # Windows parent directory
    r"^\.\.($|/|\\)",  # Starts with ..
    r"/\.\./",  # Contains /../
    r"\\\.\\.\\",  # Contains \..\
    r"\.\./",  # Contains ../
    r"\.\.%2[fF]",  # URL-encoded path traversal
    r"%2[fF]\.\.",  # URL-encoded path traversal
    r"/\./",  # Contains /./
    r"\\\.\\"  # Contains \.\
]

_PATH_TRAVERSAL_RE = re.compile("|".join(_PATH_TRAVERSAL_PATTERNS))

# JSON Schema for template validation
TEMPLATE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "version"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Template name identifier",
        },
        "version": {
            "type": "string",
            "description": "Template version (semver recommended)",
        },
        "description": {
            "type": "string",
            "description": "Human-readable template description",
        },
        "author": {
            "type": "string",
            "description": "Template author name or identifier",
        },
        "variables": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "source"],
                "properties": {
                    "name": {"type": "string"},
                    "source": {"type": "string", "enum": list(VALID_SOURCES)},
                    "format": {"type": "string"},
                    "default": {},
                },
            },
            "description": "Variables available for substitution",
        },
        "structure": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["type", "path"],
                "properties": {
                    "type": {"type": "string", "enum": list(VALID_STRUCTURE_TYPES)},
                    "path": {"type": "string"},
                },
            },
            "description": "Directory structure to create",
        },
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path"],
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "template": {"type": "string"},
                },
            },
            "description": "Files to create with content or template reference",
        },
        "copy": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "destination"],
                "properties": {
                    "source": {"type": "string"},
                    "destination": {"type": "string"},
                },
            },
            "description": "Files to copy from template assets",
        },
        "git": {
            "type": "object",
            "properties": {
                "init": {"type": "boolean"},
                "initial_commit": {"type": "boolean"},
                "commit_message": {"type": "string"},
            },
            "description": "Git initialization options",
        },
    },
}


class TemplateSchemaError(Exception):
    """Base exception for template schema errors"""

    pass


class InvalidTemplateError(TemplateSchemaError):
    """Raised when a template definition is invalid"""

    pass


class MissingRequiredFieldError(TemplateSchemaError):
    """Raised when a required field is missing from the template"""

    def __init__(self, field_name: str):
        self.field_name = field_name
        super().__init__(f"Missing required field '{field_name}'")


class InvalidPathError(TemplateSchemaError):
    """Raised when a path in the template is invalid"""

    def __init__(self, path: str, reason: Optional[str] = None):
        self.path = path
        self.reason = reason
        message = f"Invalid path '{path}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class PathTraversalError(InvalidPathError):
    """Raised when path traversal is detected"""

    def __init__(self, path: str):
        super().__init__(path, "path traversal detected")


def validate_path_security(path: str) -> bool:
    """
    Validate that a path is secure and does not contain traversal attacks.

    Args:
        path: The path to validate

    Returns:
        True if path is valid

    Raises:
        InvalidPathError: If path is empty, whitespace, or absolute
        PathTraversalError: If path contains traversal sequences
    """
    if not path or not path.strip():
        raise InvalidPathError(path, "path cannot be empty or whitespace")

    # Check for null bytes
    if "\x00" in path:
        raise InvalidPathError(path, "null bytes not allowed in path")

    # Check for absolute paths (Unix)
    if path.startswith("/"):
        raise InvalidPathError(path, "absolute paths not allowed")

    # Check for absolute paths (Windows)
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        raise InvalidPathError(path, "absolute paths not allowed")

    # Check for Windows UNC paths
    if path.startswith("\\\\"):
        raise InvalidPathError(path, "absolute paths not allowed")

    # Check for path traversal patterns
    if _PATH_TRAVERSAL_RE.search(path):
        raise PathTraversalError(path)

    # Check for parent directory references
    if ".." in path:
        raise PathTraversalError(path)

    # Check for single dot directory (current directory reference in path)
    path_parts = path.replace("\\", "/").split("/")
    for part in path_parts:
        if part == ".":
            raise PathTraversalError(path)

    return True


def validate_variable_entry(entry: Dict[str, Any]) -> bool:
    """
    Validate a variable definition entry.

    Args:
        entry: Variable entry dictionary

    Returns:
        True if valid

    Raises:
        MissingRequiredFieldError: If required field is missing
        InvalidTemplateError: If entry is invalid
    """
    if not isinstance(entry, dict):
        raise InvalidTemplateError("Variable entry must be a dictionary")

    # Check required fields
    if "name" not in entry:
        raise MissingRequiredFieldError("name")
    if "source" not in entry:
        raise MissingRequiredFieldError("source")

    name = entry["name"]
    source = entry["source"]

    # Validate name
    if not isinstance(name, str) or not name:
        raise InvalidTemplateError("Variable 'name' must be a non-empty string")

    if not _VARIABLE_NAME_RE.match(name):
        raise InvalidTemplateError(
            f"Variable 'name' '{name}' contains invalid characters. "
            "Must match pattern: [a-zA-Z_][a-zA-Z0-9_]*"
        )

    # Validate source
    if not isinstance(source, str):
        raise InvalidTemplateError("Variable 'source' must be a string")

    if source not in VALID_SOURCES:
        valid_sources_str = ", ".join(sorted(VALID_SOURCES))
        raise InvalidTemplateError(
            f"Invalid variable source '{source}'. Valid sources: {valid_sources_str}"
        )

    return True


def validate_structure_entry(entry: Dict[str, Any]) -> bool:
    """
    Validate a structure definition entry.

    Args:
        entry: Structure entry dictionary

    Returns:
        True if valid

    Raises:
        MissingRequiredFieldError: If required field is missing
        InvalidTemplateError: If entry is invalid
        InvalidPathError: If path is invalid
        PathTraversalError: If path traversal detected
    """
    if not isinstance(entry, dict):
        raise InvalidTemplateError("Structure entry must be a dictionary")

    # Check required fields
    if "type" not in entry:
        raise MissingRequiredFieldError("type")
    if "path" not in entry:
        raise MissingRequiredFieldError("path")

    entry_type = entry["type"]
    path = entry["path"]

    # Validate type
    if not isinstance(entry_type, str):
        raise InvalidTemplateError("Structure 'type' must be a string")

    if entry_type not in VALID_STRUCTURE_TYPES:
        valid_types_str = ", ".join(sorted(VALID_STRUCTURE_TYPES))
        raise InvalidTemplateError(
            f"Invalid structure type '{entry_type}'. Valid types: {valid_types_str}"
        )

    # Validate path
    if not isinstance(path, str):
        raise InvalidTemplateError("Structure 'path' must be a string")

    validate_path_security(path)

    return True


def validate_file_entry(entry: Dict[str, Any]) -> bool:
    """
    Validate a file definition entry.

    Args:
        entry: File entry dictionary

    Returns:
        True if valid

    Raises:
        MissingRequiredFieldError: If required field is missing
        InvalidTemplateError: If entry is invalid
        InvalidPathError: If path is invalid
        PathTraversalError: If path traversal detected
    """
    if not isinstance(entry, dict):
        raise InvalidTemplateError("File entry must be a dictionary")

    # Check required fields
    if "path" not in entry:
        raise MissingRequiredFieldError("path")

    path = entry["path"]
    content = entry.get("content")
    template = entry.get("template")

    # Validate path
    if not isinstance(path, str):
        raise InvalidTemplateError("File 'path' must be a string")

    validate_path_security(path)

    # Must have exactly one of content or template
    has_content = content is not None
    has_template = template is not None

    if not has_content and not has_template:
        raise InvalidTemplateError(
            "File entry must have either 'content' or 'template' field"
        )

    if has_content and has_template:
        raise InvalidTemplateError(
            "File entry cannot have both 'content' and 'template' fields"
        )

    return True


def validate_copy_entry(entry: Dict[str, Any]) -> bool:
    """
    Validate a copy definition entry.

    Args:
        entry: Copy entry dictionary

    Returns:
        True if valid

    Raises:
        MissingRequiredFieldError: If required field is missing
        InvalidTemplateError: If entry is invalid
        InvalidPathError: If path is invalid
        PathTraversalError: If path traversal detected
    """
    if not isinstance(entry, dict):
        raise InvalidTemplateError("Copy entry must be a dictionary")

    # Check required fields
    if "source" not in entry:
        raise MissingRequiredFieldError("source")
    if "destination" not in entry:
        raise MissingRequiredFieldError("destination")

    source = entry["source"]
    destination = entry["destination"]

    # Validate source
    if not isinstance(source, str):
        raise InvalidTemplateError("Copy 'source' must be a string")

    validate_path_security(source)

    # Validate destination
    if not isinstance(destination, str):
        raise InvalidTemplateError("Copy 'destination' must be a string")

    validate_path_security(destination)

    return True


def validate_git_config(config: Optional[Dict[str, Any]]) -> bool:
    """
    Validate git configuration section.

    Args:
        config: Git configuration dictionary or None

    Returns:
        True if valid

    Raises:
        InvalidTemplateError: If configuration is invalid
    """
    # None or empty config is valid (no git initialization)
    if config is None:
        return True

    if not isinstance(config, dict):
        raise InvalidTemplateError("Git configuration must be an object/dictionary")

    if not config:
        return True

    init = config.get("init")
    initial_commit = config.get("initial_commit")
    commit_message = config.get("commit_message")

    # Validate init
    if init is not None and not isinstance(init, bool):
        raise InvalidTemplateError("Git 'init' must be a boolean")

    # Validate initial_commit
    if initial_commit is not None and not isinstance(initial_commit, bool):
        raise InvalidTemplateError("Git 'initial_commit' must be a boolean")

    # Validate commit_message
    if commit_message is not None:
        if not isinstance(commit_message, str):
            raise InvalidTemplateError("Git 'commit_message' must be a string")

        # If initial_commit is True, commit_message should not be empty
        if initial_commit is True and not commit_message.strip():
            raise InvalidTemplateError(
                "Git 'commit_message' cannot be empty when 'initial_commit' is True"
            )

    # Validate logical consistency: initial_commit requires init
    if initial_commit is True and init is False:
        raise InvalidTemplateError(
            "Git 'initial_commit' requires 'init' to be True"
        )

    return True


def validate_template(template: Any) -> bool:
    """
    Validate a complete template definition.

    This function performs comprehensive validation including:
    - Required fields check (name, version)
    - Type validation for all fields
    - Path security validation
    - Nested entry validation (variables, structure, files, copy, git)

    Args:
        template: Template definition dictionary

    Returns:
        True if template is valid

    Raises:
        InvalidTemplateError: If template is invalid or wrong type
        MissingRequiredFieldError: If required field is missing
        InvalidPathError: If any path is invalid
        PathTraversalError: If path traversal detected
    """
    # Check input type
    if template is None:
        raise InvalidTemplateError("Template cannot be None")

    if not isinstance(template, dict):
        raise InvalidTemplateError("Template must be a dictionary")

    # Check required fields
    if "name" not in template:
        raise MissingRequiredFieldError("name")
    if "version" not in template:
        raise MissingRequiredFieldError("version")

    # Validate name
    name = template["name"]
    if not isinstance(name, str):
        raise InvalidTemplateError("Template 'name' must be a string")
    if not name.strip():
        raise InvalidTemplateError("Template 'name' cannot be empty")

    # Validate version
    version = template["version"]
    if not isinstance(version, str):
        raise InvalidTemplateError("Template 'version' must be a string")

    # Validate optional description
    description = template.get("description")
    if description is not None and not isinstance(description, str):
        raise InvalidTemplateError("Template 'description' must be a string")

    # Validate optional author
    author = template.get("author")
    if author is not None and not isinstance(author, str):
        raise InvalidTemplateError("Template 'author' must be a string")

    # Validate variables array
    variables = template.get("variables")
    if variables is not None:
        if not isinstance(variables, list):
            raise InvalidTemplateError("Template 'variables' must be an array")
        for i, var_entry in enumerate(variables):
            try:
                validate_variable_entry(var_entry)
            except TemplateSchemaError as e:
                raise InvalidTemplateError(
                    f"Invalid variable entry at index {i}: {e}"
                ) from e

    # Validate structure array
    structure = template.get("structure")
    if structure is not None:
        if not isinstance(structure, list):
            raise InvalidTemplateError("Template 'structure' must be an array")
        for i, struct_entry in enumerate(structure):
            try:
                validate_structure_entry(struct_entry)
            except TemplateSchemaError as e:
                raise InvalidTemplateError(
                    f"Invalid structure entry at index {i}: {e}"
                ) from e

    # Validate files array
    files = template.get("files")
    if files is not None:
        if not isinstance(files, list):
            raise InvalidTemplateError("Template 'files' must be an array")
        for i, file_entry in enumerate(files):
            try:
                validate_file_entry(file_entry)
            except TemplateSchemaError as e:
                raise InvalidTemplateError(
                    f"Invalid file entry at index {i}: {e}"
                ) from e

    # Validate copy array
    copy = template.get("copy")
    if copy is not None:
        if not isinstance(copy, list):
            raise InvalidTemplateError("Template 'copy' must be an array")
        for i, copy_entry in enumerate(copy):
            try:
                validate_copy_entry(copy_entry)
            except TemplateSchemaError as e:
                raise InvalidTemplateError(
                    f"Invalid copy entry at index {i}: {e}"
                ) from e

    # Validate git configuration
    git = template.get("git")
    if git is not None:
        if not isinstance(git, dict):
            raise InvalidTemplateError("Template 'git' must be an object/dictionary")
        try:
            validate_git_config(git)
        except TemplateSchemaError as e:
            raise InvalidTemplateError(f"Invalid git configuration: {e}") from e

    return True