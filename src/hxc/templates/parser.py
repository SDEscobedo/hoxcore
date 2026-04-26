"""
HoxCore Template Parser.

This module provides template YAML file loading, parsing, and validation.
Templates are loaded from disk, parsed as YAML, and validated against
the template schema to ensure they are correct, complete, and secure.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from hxc.templates.schema import (
    InvalidTemplateError,
    MissingRequiredFieldError,
    PathTraversalError,
    TemplateSchemaError,
    validate_template,
)


class TemplateParserError(Exception):
    """Base exception for template parsing errors"""

    pass


class TemplateNotFoundError(TemplateParserError):
    """Raised when a template file cannot be found"""

    def __init__(self, path: Union[str, Path]):
        self.path = str(path)
        super().__init__(f"Template not found: {self.path}")


class TemplateLoadError(TemplateParserError):
    """Raised when a template file cannot be loaded or parsed"""

    def __init__(self, path: Union[str, Path], reason: Optional[str] = None):
        self.path = str(path)
        self.reason = reason
        message = f"Failed to load template: {self.path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message)


class TemplateParser:
    """
    Parser for HoxCore template definition files.

    This class handles loading, parsing, and validating template YAML files.
    Templates are validated against a strict schema to ensure they are
    declarative-only and secure.

    Example Usage:
        >>> parser = TemplateParser()
        >>> template = parser.parse("~/.hxc/templates/software.dev/cli-tool/default.yml")
        >>> print(template["name"])
        'cli-tool-default'

    Attributes:
        strict: Whether to raise exceptions on validation warnings (default: False)
    """

    def __init__(self, strict: bool = False):
        """
        Initialize the template parser.

        Args:
            strict: If True, treat validation warnings as errors
        """
        self.strict = strict

    def parse(self, template_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse a template file from disk.

        This method loads a YAML template file, parses its contents, and
        validates it against the template schema. The template must conform
        to the declarative-only security constraints.

        Args:
            template_path: Path to the template YAML file

        Returns:
            Parsed and validated template definition dictionary

        Raises:
            TemplateNotFoundError: If the template file does not exist
            TemplateLoadError: If the file cannot be read or parsed as YAML
            InvalidTemplateError: If the template fails schema validation
            MissingRequiredFieldError: If required fields are missing
            PathTraversalError: If template contains path traversal attempts
        """
        path = Path(template_path).expanduser().resolve()

        # Check file exists
        if not path.exists():
            raise TemplateNotFoundError(template_path)

        if not path.is_file():
            raise TemplateLoadError(template_path, "path is not a file")

        # Load file contents
        try:
            content = path.read_text(encoding="utf-8")
        except IOError as e:
            raise TemplateLoadError(template_path, f"cannot read file: {e}") from e
        except UnicodeDecodeError as e:
            raise TemplateLoadError(
                template_path, f"file is not valid UTF-8: {e}"
            ) from e

        # Parse YAML
        template_data = self.parse_string(content, source_path=str(template_path))

        # Add metadata about the source file
        template_data["_source_path"] = str(path)

        return template_data

    def parse_string(
        self, content: str, source_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Parse template content from a string.

        This method parses YAML content directly from a string and validates
        it against the template schema. Useful for testing or when template
        content is provided from sources other than files.

        Args:
            content: YAML content string
            source_path: Optional source path for error messages

        Returns:
            Parsed and validated template definition dictionary

        Raises:
            TemplateLoadError: If content cannot be parsed as YAML
            InvalidTemplateError: If the template fails schema validation
            MissingRequiredFieldError: If required fields are missing
            PathTraversalError: If template contains path traversal attempts
        """
        source_desc = source_path or "<string>"

        # Check for empty content
        if not content or not content.strip():
            raise TemplateLoadError(source_desc, "template content is empty")

        # Parse YAML
        try:
            template_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise TemplateLoadError(source_desc, f"invalid YAML: {e}") from e

        # Check we got a dictionary
        if template_data is None:
            raise TemplateLoadError(source_desc, "template content is empty or null")

        if not isinstance(template_data, dict):
            raise TemplateLoadError(
                source_desc,
                f"template must be a YAML mapping, got {type(template_data).__name__}",
            )

        # Validate against schema
        try:
            validate_template(template_data)
        except MissingRequiredFieldError:
            # Re-raise as-is for specific error handling
            raise
        except PathTraversalError:
            # Re-raise as-is for security error handling
            raise
        except TemplateSchemaError as e:
            # Wrap other schema errors with source context
            raise InvalidTemplateError(
                f"Invalid template{' at ' + source_desc if source_desc != '<string>' else ''}: {e}"
            ) from e

        return template_data

    def parse_dict(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a template definition dictionary.

        This method validates an already-parsed dictionary against the
        template schema. Useful when the template data comes from a source
        other than a YAML file (e.g., programmatically constructed).

        Args:
            template_data: Template definition dictionary

        Returns:
            Validated template definition dictionary (same as input if valid)

        Raises:
            InvalidTemplateError: If the template fails schema validation
            MissingRequiredFieldError: If required fields are missing
            PathTraversalError: If template contains path traversal attempts
        """
        validate_template(template_data)
        return template_data

    @staticmethod
    def get_template_metadata(template_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a parsed template.

        Returns a dictionary containing only the template metadata fields
        (name, version, description, author) without the structure, files,
        or other operational definitions.

        Args:
            template_data: Parsed template definition

        Returns:
            Dictionary containing template metadata
        """
        metadata_fields = ["name", "version", "description", "author"]
        return {
            key: template_data.get(key)
            for key in metadata_fields
            if key in template_data
        }

    @staticmethod
    def get_variables(template_data: Dict[str, Any]) -> list:
        """
        Extract variable definitions from a parsed template.

        Args:
            template_data: Parsed template definition

        Returns:
            List of variable definition dictionaries
        """
        return template_data.get("variables", [])

    @staticmethod
    def get_structure(template_data: Dict[str, Any]) -> list:
        """
        Extract directory structure definitions from a parsed template.

        Args:
            template_data: Parsed template definition

        Returns:
            List of structure entry dictionaries
        """
        return template_data.get("structure", [])

    @staticmethod
    def get_files(template_data: Dict[str, Any]) -> list:
        """
        Extract file definitions from a parsed template.

        Args:
            template_data: Parsed template definition

        Returns:
            List of file entry dictionaries
        """
        return template_data.get("files", [])

    @staticmethod
    def get_copy_entries(template_data: Dict[str, Any]) -> list:
        """
        Extract copy definitions from a parsed template.

        Args:
            template_data: Parsed template definition

        Returns:
            List of copy entry dictionaries
        """
        return template_data.get("copy", [])

    @staticmethod
    def get_git_config(template_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract git configuration from a parsed template.

        Args:
            template_data: Parsed template definition

        Returns:
            Git configuration dictionary or None if not specified
        """
        return template_data.get("git")

    @staticmethod
    def has_git_init(template_data: Dict[str, Any]) -> bool:
        """
        Check if template specifies git initialization.

        Args:
            template_data: Parsed template definition

        Returns:
            True if template specifies git init, False otherwise
        """
        git_config = template_data.get("git")
        if not git_config:
            return False
        return git_config.get("init", False) is True

    @staticmethod
    def has_initial_commit(template_data: Dict[str, Any]) -> bool:
        """
        Check if template specifies initial commit.

        Args:
            template_data: Parsed template definition

        Returns:
            True if template specifies initial commit, False otherwise
        """
        git_config = template_data.get("git")
        if not git_config:
            return False
        return git_config.get("initial_commit", False) is True

    @staticmethod
    def get_commit_message(template_data: Dict[str, Any]) -> Optional[str]:
        """
        Get the commit message template from git configuration.

        Args:
            template_data: Parsed template definition

        Returns:
            Commit message template string or None
        """
        git_config = template_data.get("git")
        if not git_config:
            return None
        return git_config.get("commit_message")

    def validate_template_file(self, template_path: Union[str, Path]) -> bool:
        """
        Validate a template file without fully loading it.

        This is a convenience method that returns True if the template
        is valid, or raises an appropriate exception if not.

        Args:
            template_path: Path to the template YAML file

        Returns:
            True if template is valid

        Raises:
            TemplateNotFoundError: If the template file does not exist
            TemplateLoadError: If the file cannot be read or parsed
            InvalidTemplateError: If the template fails validation
        """
        self.parse(template_path)
        return True

    def validate_template_string(self, content: str) -> bool:
        """
        Validate template content from a string.

        Args:
            content: YAML content string

        Returns:
            True if template is valid

        Raises:
            TemplateLoadError: If content cannot be parsed
            InvalidTemplateError: If the template fails validation
        """
        self.parse_string(content)
        return True