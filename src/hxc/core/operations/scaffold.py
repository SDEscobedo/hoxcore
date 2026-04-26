"""
HoxCore Scaffold Operation.

This module provides the shared scaffolding operation implementation that ensures
behavioral consistency between the CLI commands and MCP tools. It handles:

- Template resolution from various sources
- Template parsing and validation
- Variable resolution and substitution
- Directory and file creation
- Git repository initialization
- Dry-run preview mode
- Security enforcement
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from hxc.templates.executor import (
    DirectoryCreationError,
    ExecutorError,
    FileCopyError,
    FileCreationError,
    GitInitError,
    ScaffoldError,
    ScaffoldResult,
    TemplateExecutor,
)
from hxc.templates.parser import (
    TemplateLoadError,
    TemplateNotFoundError,
    TemplateParser,
    TemplateParserError,
)
from hxc.templates.resolver import (
    CategoryVariant,
    TemplateResolutionError,
    TemplateResolver,
    TemplateResolverError,
)
from hxc.templates.schema import (
    InvalidPathError,
    InvalidTemplateError,
    MissingRequiredFieldError,
    PathTraversalError,
    TemplateSchemaError,
)
from hxc.templates.variables import (
    TemplateVariables,
    UndefinedVariableError,
    VariableError,
    VariableSubstitutionError,
)


class ScaffoldOperationError(Exception):
    """Base exception for scaffold operation errors"""

    pass


class TemplateNotFoundOperationError(ScaffoldOperationError):
    """Raised when a template cannot be found"""

    def __init__(self, template_ref: str, searched_paths: Optional[List[str]] = None):
        self.template_ref = template_ref
        self.searched_paths = searched_paths or []
        message = f"Template not found: {template_ref}"
        if searched_paths:
            paths_str = ", ".join(searched_paths)
            message += f" (searched: {paths_str})"
        super().__init__(message)


class TemplateValidationError(ScaffoldOperationError):
    """Raised when a template fails validation"""

    def __init__(self, template_ref: str, reason: str):
        self.template_ref = template_ref
        self.reason = reason
        super().__init__(f"Invalid template '{template_ref}': {reason}")


class ScaffoldSecurityError(ScaffoldOperationError):
    """Raised when a security violation is detected during scaffolding"""

    def __init__(self, message: str, path: Optional[str] = None):
        self.path = path
        super().__init__(message)


class ScaffoldExecutionError(ScaffoldOperationError):
    """Raised when scaffolding execution fails"""

    def __init__(self, message: str, partial_result: Optional[ScaffoldResult] = None):
        self.partial_result = partial_result
        super().__init__(message)


class PromptRequiredError(ScaffoldOperationError):
    """Raised when prompt variables are required but not provided"""

    def __init__(self, required_prompts: List[Dict[str, Any]]):
        self.required_prompts = required_prompts
        prompt_names = [p.get("name", "unknown") for p in required_prompts]
        super().__init__(
            f"Prompt values required for variables: {', '.join(prompt_names)}"
        )


@dataclass
class ScaffoldOperationResult:
    """
    Result of a scaffold operation.

    Attributes:
        success: Whether the operation completed successfully
        template_path: Resolved path to the template file
        template_name: Name of the template
        template_version: Version of the template
        output_path: Path where scaffolding was performed
        scaffold_result: Detailed scaffolding result from executor
        dry_run: Whether this was a dry-run
        error: Error message if operation failed
        pending_prompts: List of prompt variables that need values
    """

    success: bool = True
    template_path: Optional[str] = None
    template_name: Optional[str] = None
    template_version: Optional[str] = None
    output_path: Optional[str] = None
    scaffold_result: Optional[ScaffoldResult] = None
    dry_run: bool = False
    error: Optional[str] = None
    pending_prompts: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def directories_created(self) -> List[str]:
        """Get list of directories created"""
        if self.scaffold_result:
            return self.scaffold_result.directories_created
        return []

    @property
    def files_created(self) -> List[str]:
        """Get list of files created"""
        if self.scaffold_result:
            return self.scaffold_result.files_created
        return []

    @property
    def files_copied(self) -> List[str]:
        """Get list of files copied"""
        if self.scaffold_result:
            return self.scaffold_result.files_copied
        return []

    @property
    def git_initialized(self) -> bool:
        """Whether git was initialized"""
        if self.scaffold_result:
            return self.scaffold_result.git_initialized
        return False

    @property
    def git_committed(self) -> bool:
        """Whether initial commit was created"""
        if self.scaffold_result:
            return self.scaffold_result.git_committed
        return False

    @property
    def total_items(self) -> int:
        """Total number of items created"""
        if self.scaffold_result:
            return self.scaffold_result.total_items_created
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses"""
        result: Dict[str, Any] = {
            "success": self.success,
            "dry_run": self.dry_run,
        }

        if self.success:
            result["template_path"] = self.template_path
            result["template_name"] = self.template_name
            result["template_version"] = self.template_version
            result["output_path"] = self.output_path
            result["directories_created"] = self.directories_created
            result["files_created"] = self.files_created
            result["files_copied"] = self.files_copied
            result["git_initialized"] = self.git_initialized
            result["git_committed"] = self.git_committed
            result["total_items"] = self.total_items

            if self.scaffold_result and self.scaffold_result.warnings:
                result["warnings"] = self.scaffold_result.warnings
        else:
            result["error"] = self.error

        if self.pending_prompts:
            result["pending_prompts"] = self.pending_prompts

        return result


class ScaffoldOperation:
    """
    Shared scaffold operation for CLI and MCP interfaces.

    This class provides the core scaffolding logic including:
    - Template resolution from multiple sources
    - Template parsing and validation
    - Variable resolution from entity data, system, and prompts
    - Scaffolding execution with security enforcement
    - Dry-run preview mode
    - Git initialization integration

    Example Usage:
        >>> operation = ScaffoldOperation(registry_path="/path/to/registry")
        >>> result = operation.scaffold(
        ...     template_ref="software.dev/cli-tool/default",
        ...     output_path="/path/to/output",
        ...     entity_data={"title": "My Project", "id": "my-proj"},
        ...     dry_run=False,
        ... )
        >>> print(result.summary())

    Attributes:
        registry_path: Path to the registry root directory (optional)
    """

    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize the scaffold operation.

        Args:
            registry_path: Path to the registry root directory (optional).
                          Used for resolving registry-local templates.
        """
        self.registry_path = registry_path
        self._resolver: Optional[TemplateResolver] = None
        self._parser: Optional[TemplateParser] = None

    @property
    def resolver(self) -> TemplateResolver:
        """Get or create the template resolver"""
        if self._resolver is None:
            self._resolver = TemplateResolver(registry_path=self.registry_path)
        return self._resolver

    @property
    def parser(self) -> TemplateParser:
        """Get or create the template parser"""
        if self._parser is None:
            self._parser = TemplateParser()
        return self._parser

    def resolve_template(self, template_ref: str) -> Path:
        """
        Resolve a template reference to an actual file path.

        Resolution order:
        1. Explicit path (if file exists)
        2. Registry-local templates (.hxc/templates/)
        3. User templates (~/.hxc/templates/)

        Args:
            template_ref: Template reference (path or identifier)

        Returns:
            Path to the resolved template file

        Raises:
            TemplateNotFoundOperationError: If template cannot be resolved
        """
        try:
            return self.resolver.resolve(template_ref)
        except TemplateResolutionError as e:
            raise TemplateNotFoundOperationError(
                template_ref, e.searched_paths
            ) from e
        except TemplateResolverError as e:
            raise TemplateNotFoundOperationError(template_ref) from e

    def resolve_from_category(self, category: str) -> Optional[Path]:
        """
        Resolve a template from category notation.

        Parses category strings like "software.dev/cli-tool.author/variant"
        to extract and resolve the template variant.

        Args:
            category: Category string potentially containing variant notation

        Returns:
            Path to resolved template, or None if no variant specified

        Raises:
            TemplateNotFoundOperationError: If variant is specified but cannot be resolved
        """
        try:
            return self.resolver.resolve_from_category(category)
        except TemplateResolutionError as e:
            raise TemplateNotFoundOperationError(
                e.template_ref, e.searched_paths
            ) from e
        except TemplateResolverError as e:
            raise TemplateNotFoundOperationError(str(e)) from e

    def parse_template(self, template_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Parse a template file from disk.

        Args:
            template_path: Path to the template YAML file

        Returns:
            Parsed and validated template definition dictionary

        Raises:
            TemplateNotFoundOperationError: If template file doesn't exist
            TemplateValidationError: If template fails validation
        """
        try:
            return self.parser.parse(template_path)
        except TemplateNotFoundError as e:
            raise TemplateNotFoundOperationError(e.path) from e
        except MissingRequiredFieldError as e:
            raise TemplateValidationError(
                str(template_path), f"missing required field: {e.field_name}"
            ) from e
        except PathTraversalError as e:
            raise ScaffoldSecurityError(
                f"Path traversal detected in template: {e.path}", e.path
            ) from e
        except InvalidPathError as e:
            raise TemplateValidationError(
                str(template_path), f"invalid path: {e.path}"
            ) from e
        except InvalidTemplateError as e:
            raise TemplateValidationError(str(template_path), str(e)) from e
        except TemplateLoadError as e:
            raise TemplateValidationError(str(template_path), e.reason or str(e)) from e
        except TemplateParserError as e:
            raise TemplateValidationError(str(template_path), str(e)) from e

    def build_variables(
        self,
        template_data: Dict[str, Any],
        entity_data: Dict[str, Any],
        prompt_values: Optional[Dict[str, Any]] = None,
    ) -> TemplateVariables:
        """
        Build template variables from entity data and prompts.

        Args:
            template_data: Parsed template definition
            entity_data: Entity data for variable substitution
            prompt_values: Optional user-provided prompt values

        Returns:
            Configured TemplateVariables instance
        """
        variables = TemplateVariables.from_entity_and_template(
            entity_data=entity_data,
            template_data=template_data,
            prompt_values=prompt_values,
        )
        return variables

    def check_pending_prompts(
        self,
        variables: TemplateVariables,
    ) -> List[Dict[str, Any]]:
        """
        Check for prompt variables that need user input.

        Args:
            variables: TemplateVariables instance

        Returns:
            List of prompt variable definitions that need values
        """
        return variables.get_pending_prompts()

    def validate_output_path(
        self,
        output_path: Union[str, Path],
        allow_non_empty: bool = False,
    ) -> List[str]:
        """
        Validate that output path is suitable for scaffolding.

        Args:
            output_path: Path to validate
            allow_non_empty: If True, allow non-empty directories

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        output_path = Path(output_path)

        # Resolve to absolute path
        if not output_path.is_absolute():
            output_path = output_path.resolve()

        # Check if path exists
        if output_path.exists():
            if output_path.is_file():
                issues.append(f"Output path is a file, not a directory: {output_path}")
            elif not allow_non_empty and any(output_path.iterdir()):
                issues.append(f"Output directory is not empty: {output_path}")

        # Check parent directory exists
        parent = output_path.parent
        if not parent.exists():
            issues.append(f"Parent directory does not exist: {parent}")

        return issues

    def scaffold(
        self,
        template_ref: str,
        output_path: Union[str, Path],
        entity_data: Optional[Dict[str, Any]] = None,
        prompt_values: Optional[Dict[str, Any]] = None,
        dry_run: bool = False,
        allow_non_empty: bool = False,
        require_all_prompts: bool = True,
    ) -> ScaffoldOperationResult:
        """
        Execute scaffolding operation.

        This is the main entry point for scaffolding, handling:
        - Template resolution
        - Template parsing
        - Variable resolution
        - Scaffolding execution or preview

        Args:
            template_ref: Template reference (path or identifier)
            output_path: Path where scaffolding should be performed
            entity_data: Optional entity data for variable substitution
            prompt_values: Optional user-provided prompt values
            dry_run: If True, preview without making changes
            allow_non_empty: If True, allow scaffolding in non-empty directories
            require_all_prompts: If True, raise error if prompts are missing

        Returns:
            ScaffoldOperationResult with operation details

        Raises:
            TemplateNotFoundOperationError: If template cannot be found
            TemplateValidationError: If template fails validation
            ScaffoldSecurityError: If security violation is detected
            ScaffoldExecutionError: If scaffolding fails
            PromptRequiredError: If prompt values are required but not provided
        """
        if entity_data is None:
            entity_data = {}

        result = ScaffoldOperationResult(dry_run=dry_run)

        try:
            # Step 1: Resolve template
            template_path = self.resolve_template(template_ref)
            result.template_path = str(template_path)

            # Step 2: Parse template
            template_data = self.parse_template(template_path)
            result.template_name = template_data.get("name")
            result.template_version = template_data.get("version")

            # Step 3: Build variables
            variables = self.build_variables(
                template_data=template_data,
                entity_data=entity_data,
                prompt_values=prompt_values,
            )

            # Step 4: Check for pending prompts
            pending_prompts = self.check_pending_prompts(variables)
            if pending_prompts:
                result.pending_prompts = pending_prompts
                if require_all_prompts:
                    raise PromptRequiredError(pending_prompts)

            # Step 5: Validate output path
            output_path = Path(output_path).resolve()
            result.output_path = str(output_path)

            if not dry_run:
                validation_issues = self.validate_output_path(
                    output_path, allow_non_empty
                )
                if validation_issues:
                    raise ScaffoldExecutionError(
                        f"Output path validation failed: {validation_issues[0]}"
                    )

            # Step 6: Create executor and execute
            executor = TemplateExecutor(
                template=template_data,
                variables=variables,
                template_base_path=template_path.parent,
            )

            scaffold_result = executor.execute(
                output_path=output_path,
                dry_run=dry_run,
                create_output_dir=True,
            )

            result.scaffold_result = scaffold_result
            result.success = scaffold_result.success

            if not scaffold_result.success and scaffold_result.errors:
                result.error = scaffold_result.errors[0]

        except (
            TemplateNotFoundOperationError,
            TemplateValidationError,
            ScaffoldSecurityError,
            PromptRequiredError,
        ):
            raise
        except DirectoryCreationError as e:
            raise ScaffoldExecutionError(
                f"Failed to create directory: {e.path}"
            ) from e
        except FileCreationError as e:
            raise ScaffoldExecutionError(
                f"Failed to create file: {e.path}"
            ) from e
        except FileCopyError as e:
            raise ScaffoldExecutionError(
                f"Failed to copy file from '{e.source}' to '{e.destination}'"
            ) from e
        except GitInitError as e:
            raise ScaffoldExecutionError(
                f"Failed to initialize git repository: {e.path}"
            ) from e
        except PathTraversalError as e:
            raise ScaffoldSecurityError(
                f"Path traversal detected: {e.path}", e.path
            ) from e
        except UndefinedVariableError as e:
            raise ScaffoldExecutionError(
                f"Undefined variable: {e.variable_name}"
            ) from e
        except VariableSubstitutionError as e:
            raise ScaffoldExecutionError(
                f"Variable substitution failed: {e}"
            ) from e
        except (ExecutorError, ScaffoldError) as e:
            raise ScaffoldExecutionError(str(e)) from e
        except VariableError as e:
            raise ScaffoldExecutionError(f"Variable error: {e}") from e
        except TemplateSchemaError as e:
            raise TemplateValidationError(template_ref, str(e)) from e

        return result

    def preview(
        self,
        template_ref: str,
        output_path: Union[str, Path],
        entity_data: Optional[Dict[str, Any]] = None,
        prompt_values: Optional[Dict[str, Any]] = None,
    ) -> ScaffoldOperationResult:
        """
        Preview scaffolding without making changes.

        This is a convenience method equivalent to scaffold(dry_run=True).

        Args:
            template_ref: Template reference (path or identifier)
            output_path: Path where scaffolding would be performed
            entity_data: Optional entity data for variable substitution
            prompt_values: Optional user-provided prompt values

        Returns:
            ScaffoldOperationResult with preview of what would be created
        """
        return self.scaffold(
            template_ref=template_ref,
            output_path=output_path,
            entity_data=entity_data,
            prompt_values=prompt_values,
            dry_run=True,
            require_all_prompts=False,
        )

    def list_templates(
        self,
        include_registry: bool = True,
        include_user: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        List all available templates.

        Args:
            include_registry: Include registry-local templates
            include_user: Include user templates

        Returns:
            List of template info dictionaries with:
            - id: Template identifier
            - path: Full path to template file
            - source: 'registry' or 'user'
            - name: Template name (if parseable)
            - version: Template version (if parseable)
            - description: Template description (if parseable)
        """
        templates = []

        for template_id, template_path, source in self.resolver.list_templates(
            include_registry=include_registry,
            include_user=include_user,
        ):
            template_info: Dict[str, Any] = {
                "id": template_id,
                "path": str(template_path),
                "source": source,
            }

            # Try to parse template for metadata
            try:
                template_data = self.parser.parse(template_path)
                template_info["name"] = template_data.get("name")
                template_info["version"] = template_data.get("version")
                template_info["description"] = template_data.get("description")
                template_info["author"] = template_data.get("author")
                template_info["valid"] = True
            except (TemplateParserError, TemplateSchemaError):
                template_info["valid"] = False

            templates.append(template_info)

        return templates

    def get_template_info(self, template_ref: str) -> Dict[str, Any]:
        """
        Get detailed information about a template.

        Args:
            template_ref: Template reference (path or identifier)

        Returns:
            Dictionary with template details including:
            - path: Resolved template path
            - name: Template name
            - version: Template version
            - description: Template description
            - author: Template author
            - structure: List of directories to create
            - files: List of files to create
            - copy: List of files to copy
            - git: Git configuration
            - variables: Variable definitions
            - source: Template source ('explicit', 'registry', or 'user')

        Raises:
            TemplateNotFoundOperationError: If template cannot be found
            TemplateValidationError: If template fails validation
        """
        # Resolve template
        template_path = self.resolve_template(template_ref)

        # Parse template
        template_data = self.parse_template(template_path)

        # Get source
        source = self.resolver.get_template_source(template_ref) or "unknown"

        return {
            "path": str(template_path),
            "name": template_data.get("name"),
            "version": template_data.get("version"),
            "description": template_data.get("description"),
            "author": template_data.get("author"),
            "structure": template_data.get("structure", []),
            "files": template_data.get("files", []),
            "copy": template_data.get("copy", []),
            "git": template_data.get("git"),
            "variables": template_data.get("variables", []),
            "source": source,
        }

    def template_exists(self, template_ref: str) -> bool:
        """
        Check if a template reference can be resolved.

        Args:
            template_ref: Template reference to check

        Returns:
            True if template can be resolved, False otherwise
        """
        return self.resolver.template_exists(template_ref)

    @staticmethod
    def parse_category_variant(category: str) -> CategoryVariant:
        """
        Parse category notation to extract variant.

        Args:
            category: Category string potentially containing variant notation

        Returns:
            CategoryVariant with parsed components
        """
        return CategoryVariant.parse(category)

    def ensure_template_directories(self) -> Dict[str, Optional[Path]]:
        """
        Ensure template directories exist.

        Creates user templates directory and registry templates directory
        (if registry path is set).

        Returns:
            Dictionary with 'user' and 'registry' paths (or None if not created)
        """
        result: Dict[str, Optional[Path]] = {
            "user": None,
            "registry": None,
        }

        try:
            result["user"] = self.resolver.ensure_user_templates_dir()
        except OSError:
            pass

        if self.registry_path:
            try:
                result["registry"] = self.resolver.ensure_registry_templates_dir()
            except OSError:
                pass

        return result


def scaffold_from_template(
    template_ref: str,
    output_path: Union[str, Path],
    entity_data: Optional[Dict[str, Any]] = None,
    prompt_values: Optional[Dict[str, Any]] = None,
    registry_path: Optional[str] = None,
    dry_run: bool = False,
) -> ScaffoldOperationResult:
    """
    Execute scaffolding from a template reference.

    This is a convenience function that creates a ScaffoldOperation
    and executes scaffolding in one call.

    Args:
        template_ref: Template reference (path or identifier)
        output_path: Path where scaffolding should be performed
        entity_data: Optional entity data for variable substitution
        prompt_values: Optional user-provided prompt values
        registry_path: Optional registry path for template resolution
        dry_run: If True, preview without making changes

    Returns:
        ScaffoldOperationResult with operation details

    Raises:
        TemplateNotFoundOperationError: If template cannot be found
        TemplateValidationError: If template fails validation
        ScaffoldSecurityError: If security violation is detected
        ScaffoldExecutionError: If scaffolding fails
        PromptRequiredError: If prompt values are required but not provided
    """
    operation = ScaffoldOperation(registry_path=registry_path)
    return operation.scaffold(
        template_ref=template_ref,
        output_path=output_path,
        entity_data=entity_data,
        prompt_values=prompt_values,
        dry_run=dry_run,
    )


def preview_scaffold(
    template_ref: str,
    output_path: Union[str, Path],
    entity_data: Optional[Dict[str, Any]] = None,
    prompt_values: Optional[Dict[str, Any]] = None,
    registry_path: Optional[str] = None,
) -> ScaffoldOperationResult:
    """
    Preview scaffolding without making changes.

    This is a convenience function equivalent to scaffold_from_template(dry_run=True).

    Args:
        template_ref: Template reference (path or identifier)
        output_path: Path where scaffolding would be performed
        entity_data: Optional entity data for variable substitution
        prompt_values: Optional user-provided prompt values
        registry_path: Optional registry path for template resolution

    Returns:
        ScaffoldOperationResult with preview of what would be created
    """
    return scaffold_from_template(
        template_ref=template_ref,
        output_path=output_path,
        entity_data=entity_data,
        prompt_values=prompt_values,
        registry_path=registry_path,
        dry_run=True,
    )