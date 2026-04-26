"""
HoxCore Template Executor.

This module provides scaffolding execution - creating directory structures,
files with content injection, file copying, and git initialization based
on template definitions. All operations are declarative and secure.

Security Constraints:
    - No shell command execution
    - No script execution
    - No network access
    - No arbitrary file reading
    - No path traversal (../)
    - Only read from designated template directories
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from hxc.templates.schema import validate_path_security, PathTraversalError, InvalidPathError
from hxc.templates.variables import TemplateVariables, VariableSubstitutionError


class ExecutorError(Exception):
    """Base exception for executor errors"""

    pass


class ScaffoldError(ExecutorError):
    """Raised when scaffolding fails"""

    def __init__(self, message: str, path: Optional[str] = None):
        self.path = path
        super().__init__(message)


class DirectoryCreationError(ScaffoldError):
    """Raised when directory creation fails"""

    def __init__(self, path: str, reason: Optional[str] = None):
        self.reason = reason
        message = f"Failed to create directory: {path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, path)


class FileCreationError(ScaffoldError):
    """Raised when file creation fails"""

    def __init__(self, path: str, reason: Optional[str] = None):
        self.reason = reason
        message = f"Failed to create file: {path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, path)


class FileCopyError(ScaffoldError):
    """Raised when file copying fails"""

    def __init__(
        self, source: str, destination: str, reason: Optional[str] = None
    ):
        self.source = source
        self.destination = destination
        self.reason = reason
        message = f"Failed to copy file from '{source}' to '{destination}'"
        if reason:
            message += f" - {reason}"
        super().__init__(message, destination)


class GitInitError(ScaffoldError):
    """Raised when git initialization fails"""

    def __init__(self, path: str, reason: Optional[str] = None):
        self.reason = reason
        message = f"Failed to initialize git repository at: {path}"
        if reason:
            message += f" - {reason}"
        super().__init__(message, path)


@dataclass
class ScaffoldResult:
    """
    Result of a scaffolding operation.

    Attributes:
        success: Whether the scaffolding completed successfully
        output_path: Path where scaffolding was performed
        directories_created: List of directories created
        files_created: List of files created
        files_copied: List of files copied
        git_initialized: Whether git was initialized
        git_committed: Whether initial commit was made
        dry_run: Whether this was a dry-run (no actual changes)
        errors: List of error messages (for partial failures)
        warnings: List of warning messages
    """

    success: bool = True
    output_path: str = ""
    directories_created: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_copied: List[str] = field(default_factory=list)
    git_initialized: bool = False
    git_committed: bool = False
    dry_run: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def total_items_created(self) -> int:
        """Total number of items created (directories + files)"""
        return (
            len(self.directories_created)
            + len(self.files_created)
            + len(self.files_copied)
        )

    def add_error(self, error: str) -> None:
        """Add an error message and mark as failed"""
        self.errors.append(error)
        self.success = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)

    def summary(self) -> str:
        """Generate a human-readable summary of the result"""
        if self.dry_run:
            prefix = "[DRY-RUN] Would create"
        else:
            prefix = "Created"

        lines = [f"{prefix} at {self.output_path}:"]

        if self.directories_created:
            lines.append(f"  📁 {len(self.directories_created)} directories")
            for d in self.directories_created:
                lines.append(f"     - {d}")

        if self.files_created:
            lines.append(f"  📄 {len(self.files_created)} files")
            for f in self.files_created:
                lines.append(f"     - {f}")

        if self.files_copied:
            lines.append(f"  📋 {len(self.files_copied)} files copied")
            for f in self.files_copied:
                lines.append(f"     - {f}")

        if self.git_initialized:
            git_status = "Git repository initialized"
            if self.git_committed:
                git_status += " with initial commit"
            lines.append(f"  🔧 {git_status}")

        if self.warnings:
            lines.append("  ⚠️  Warnings:")
            for w in self.warnings:
                lines.append(f"     - {w}")

        if self.errors:
            lines.append("  ❌ Errors:")
            for e in self.errors:
                lines.append(f"     - {e}")

        return "\n".join(lines)


class TemplateExecutor:
    """
    Executor for HoxCore template scaffolding.

    This class handles the actual creation of directories, files, and
    git initialization based on a parsed template definition. All operations
    are declarative and secure - no code execution is performed.

    Example Usage:
        >>> from hxc.templates import TemplateParser, TemplateVariables
        >>> parser = TemplateParser()
        >>> template = parser.parse("~/.hxc/templates/cli-tool/default.yml")
        >>> variables = TemplateVariables.from_entity(entity_data)
        >>> executor = TemplateExecutor(template, variables)
        >>> result = executor.execute(output_path="./my-project", dry_run=False)
        >>> print(result.summary())

    Attributes:
        template: Parsed template definition dictionary
        variables: TemplateVariables instance for substitution
        template_base_path: Base path for template assets (for copy operations)
    """

    def __init__(
        self,
        template: Dict[str, Any],
        variables: TemplateVariables,
        template_base_path: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize the template executor.

        Args:
            template: Parsed template definition dictionary
            variables: TemplateVariables instance for variable substitution
            template_base_path: Base path for template assets (optional)
                               If not provided, copy operations will be skipped
        """
        self.template = template
        self.variables = variables

        if template_base_path:
            self.template_base_path = Path(template_base_path).resolve()
        else:
            # Try to extract from template's _source_path
            source_path = template.get("_source_path")
            if source_path:
                self.template_base_path = Path(source_path).parent.resolve()
            else:
                self.template_base_path = None

    def execute(
        self,
        output_path: Union[str, Path],
        dry_run: bool = False,
        create_output_dir: bool = True,
    ) -> ScaffoldResult:
        """
        Execute the scaffolding operation.

        This method creates the directory structure, files, copies assets,
        and initializes git based on the template definition.

        Args:
            output_path: Path where scaffolding should be performed
            dry_run: If True, simulate operations without making changes
            create_output_dir: If True, create the output directory if it doesn't exist

        Returns:
            ScaffoldResult with details of what was created

        Raises:
            ScaffoldError: If scaffolding fails critically
            DirectoryCreationError: If a directory cannot be created
            FileCreationError: If a file cannot be created
            FileCopyError: If a file cannot be copied
            GitInitError: If git initialization fails
        """
        output_path = Path(output_path).resolve()
        result = ScaffoldResult(output_path=str(output_path), dry_run=dry_run)

        # Create output directory if needed
        if create_output_dir and not dry_run:
            try:
                output_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise DirectoryCreationError(str(output_path), str(e))

        if not dry_run and not output_path.exists():
            raise ScaffoldError(
                f"Output path does not exist: {output_path}",
                str(output_path),
            )

        # Execute scaffolding phases
        try:
            self._create_structure(output_path, result, dry_run)
            self._create_files(output_path, result, dry_run)
            self._copy_files(output_path, result, dry_run)
            self._initialize_git(output_path, result, dry_run)
        except (DirectoryCreationError, FileCreationError, FileCopyError, GitInitError):
            # Re-raise these specific errors
            raise
        except Exception as e:
            result.add_error(f"Unexpected error during scaffolding: {e}")

        return result

    def _create_structure(
        self,
        output_path: Path,
        result: ScaffoldResult,
        dry_run: bool,
    ) -> None:
        """
        Create directory structure from template.

        Args:
            output_path: Base output path
            result: ScaffoldResult to update
            dry_run: If True, simulate without changes
        """
        structure = self.template.get("structure", [])

        for entry in structure:
            entry_type = entry.get("type")
            path_template = entry.get("path", "")

            if entry_type != "directory":
                result.add_warning(f"Unknown structure type: {entry_type}")
                continue

            try:
                # Substitute variables in path
                resolved_path = self.variables.substitute_path(path_template)

                # Validate path security
                validate_path_security(resolved_path)

                full_path = output_path / resolved_path

                if not dry_run:
                    full_path.mkdir(parents=True, exist_ok=True)

                # Store relative path in result
                result.directories_created.append(resolved_path)

            except VariableSubstitutionError as e:
                raise DirectoryCreationError(path_template, str(e))
            except (PathTraversalError, InvalidPathError) as e:
                raise DirectoryCreationError(path_template, str(e))
            except OSError as e:
                raise DirectoryCreationError(path_template, str(e))

    def _create_files(
        self,
        output_path: Path,
        result: ScaffoldResult,
        dry_run: bool,
    ) -> None:
        """
        Create files with content from template.

        Args:
            output_path: Base output path
            result: ScaffoldResult to update
            dry_run: If True, simulate without changes
        """
        files = self.template.get("files", [])

        for entry in files:
            path_template = entry.get("path", "")
            content = entry.get("content")
            template_ref = entry.get("template")

            try:
                # Substitute variables in path
                resolved_path = self.variables.substitute_path(path_template)

                # Validate path security
                validate_path_security(resolved_path)

                full_path = output_path / resolved_path

                # Determine file content
                if content is not None:
                    # Inline content - substitute variables
                    file_content = self.variables.substitute(content)
                elif template_ref is not None:
                    # Template reference - load from file
                    file_content = self._load_template_file(template_ref)
                    file_content = self.variables.substitute(file_content)
                else:
                    result.add_warning(
                        f"File entry '{path_template}' has no content or template"
                    )
                    continue

                if not dry_run:
                    # Ensure parent directory exists
                    full_path.parent.mkdir(parents=True, exist_ok=True)

                    # Write file content
                    full_path.write_text(file_content, encoding="utf-8")

                result.files_created.append(resolved_path)

            except VariableSubstitutionError as e:
                raise FileCreationError(path_template, str(e))
            except (PathTraversalError, InvalidPathError) as e:
                raise FileCreationError(path_template, str(e))
            except OSError as e:
                raise FileCreationError(path_template, str(e))

    def _load_template_file(self, template_ref: str) -> str:
        """
        Load content from a template file reference.

        Args:
            template_ref: Reference to template file (relative to template base)

        Returns:
            File content as string

        Raises:
            FileCreationError: If template file cannot be loaded
        """
        if not self.template_base_path:
            raise FileCreationError(
                template_ref,
                "Cannot load template file: template base path not set",
            )

        # Validate path security
        try:
            validate_path_security(template_ref)
        except (PathTraversalError, InvalidPathError) as e:
            raise FileCreationError(template_ref, str(e))

        # Construct full path to template file
        template_file = self.template_base_path / template_ref

        # Add .txt or .tmpl extension if not present and file doesn't exist
        if not template_file.exists():
            for ext in [".txt", ".tmpl", ".template"]:
                with_ext = self.template_base_path / f"{template_ref}{ext}"
                if with_ext.exists():
                    template_file = with_ext
                    break

        if not template_file.exists():
            raise FileCreationError(
                template_ref,
                f"Template file not found: {template_file}",
            )

        # Security check: ensure template file is within template base
        try:
            template_file.resolve().relative_to(self.template_base_path)
        except ValueError:
            raise FileCreationError(
                template_ref,
                "Template file path escapes template directory",
            )

        try:
            return template_file.read_text(encoding="utf-8")
        except IOError as e:
            raise FileCreationError(template_ref, f"Cannot read file: {e}")

    def _copy_files(
        self,
        output_path: Path,
        result: ScaffoldResult,
        dry_run: bool,
    ) -> None:
        """
        Copy files from template assets.

        Args:
            output_path: Base output path
            result: ScaffoldResult to update
            dry_run: If True, simulate without changes
        """
        copy_entries = self.template.get("copy", [])

        if not copy_entries:
            return

        if not self.template_base_path:
            result.add_warning(
                "Copy entries specified but template base path not set - skipping"
            )
            return

        for entry in copy_entries:
            source = entry.get("source", "")
            destination = entry.get("destination", "")

            try:
                # Validate paths
                validate_path_security(source)
                validate_path_security(destination)

                # Substitute variables in destination
                resolved_destination = self.variables.substitute_path(destination)
                validate_path_security(resolved_destination)

                # Resolve full paths
                source_path = self.template_base_path / source
                dest_path = output_path / resolved_destination

                # Security check: ensure source is within template base
                try:
                    source_path.resolve().relative_to(self.template_base_path)
                except ValueError:
                    raise FileCopyError(
                        source,
                        resolved_destination,
                        "Source path escapes template directory",
                    )

                if not source_path.exists():
                    raise FileCopyError(
                        source,
                        resolved_destination,
                        f"Source file not found: {source_path}",
                    )

                if not dry_run:
                    # Ensure parent directory exists
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file or directory
                    if source_path.is_dir():
                        if dest_path.exists():
                            shutil.rmtree(dest_path)
                        shutil.copytree(
                            source_path,
                            dest_path,
                            symlinks=False,  # Don't follow symlinks (security)
                        )
                    else:
                        shutil.copy2(source_path, dest_path)

                result.files_copied.append(resolved_destination)

            except VariableSubstitutionError as e:
                raise FileCopyError(source, destination, str(e))
            except (PathTraversalError, InvalidPathError) as e:
                raise FileCopyError(source, destination, str(e))
            except OSError as e:
                raise FileCopyError(source, destination, str(e))

    def _initialize_git(
        self,
        output_path: Path,
        result: ScaffoldResult,
        dry_run: bool,
    ) -> None:
        """
        Initialize git repository if specified in template.

        Args:
            output_path: Base output path
            result: ScaffoldResult to update
            dry_run: If True, simulate without changes
        """
        git_config = self.template.get("git")

        if not git_config:
            return

        if not git_config.get("init", False):
            return

        if dry_run:
            result.git_initialized = True
            if git_config.get("initial_commit", False):
                result.git_committed = True
            return

        # Check if git is available
        if not self._git_available():
            result.add_warning("Git is not installed - skipping git initialization")
            return

        # Check if already a git repository
        if (output_path / ".git").exists():
            result.add_warning("Directory is already a git repository")
            result.git_initialized = True
        else:
            # Initialize git repository
            try:
                subprocess.run(
                    ["git", "init"],
                    cwd=output_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                result.git_initialized = True
            except subprocess.CalledProcessError as e:
                raise GitInitError(str(output_path), e.stderr or str(e))
            except FileNotFoundError:
                result.add_warning("Git executable not found - skipping initialization")
                return

        # Create initial commit if requested
        if git_config.get("initial_commit", False) and result.git_initialized:
            commit_message = git_config.get(
                "commit_message", "Initial commit from HoxCore template"
            )

            # Substitute variables in commit message
            try:
                commit_message = self.variables.substitute(commit_message)
            except VariableSubstitutionError:
                # Use unsubstituted message if substitution fails
                pass

            try:
                # Stage all files
                subprocess.run(
                    ["git", "add", "."],
                    cwd=output_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Create commit
                subprocess.run(
                    ["git", "commit", "-m", commit_message],
                    cwd=output_path,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                result.git_committed = True

            except subprocess.CalledProcessError as e:
                stderr = e.stderr or ""
                # "nothing to commit" is not an error
                if "nothing to commit" in stderr.lower():
                    result.add_warning("No files to commit")
                else:
                    result.add_warning(f"Failed to create initial commit: {stderr}")

    @staticmethod
    def _git_available() -> bool:
        """Check if git is available on the system."""
        try:
            subprocess.run(
                ["git", "--version"],
                check=True,
                capture_output=True,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def preview(self, output_path: Union[str, Path]) -> ScaffoldResult:
        """
        Preview scaffolding without making changes.

        This is a convenience method equivalent to execute(dry_run=True).

        Args:
            output_path: Path where scaffolding would be performed

        Returns:
            ScaffoldResult with preview of what would be created
        """
        return self.execute(output_path, dry_run=True, create_output_dir=False)

    def get_required_prompts(self) -> List[Dict[str, Any]]:
        """
        Get list of prompt variables that need user input.

        Returns:
            List of prompt variable definitions from template
        """
        return self.variables.get_pending_prompts()

    @classmethod
    def from_template_file(
        cls,
        template_path: Union[str, Path],
        entity_data: Dict[str, Any],
        prompt_values: Optional[Dict[str, Any]] = None,
    ) -> "TemplateExecutor":
        """
        Create executor from a template file path.

        This is a convenience factory that handles parsing and variable
        resolution in one step.

        Args:
            template_path: Path to template YAML file
            entity_data: Entity data for variable substitution
            prompt_values: Optional user-provided prompt values

        Returns:
            Configured TemplateExecutor instance

        Raises:
            TemplateNotFoundError: If template file doesn't exist
            TemplateLoadError: If template cannot be parsed
            InvalidTemplateError: If template is invalid
        """
        from hxc.templates.parser import TemplateParser

        parser = TemplateParser()
        template = parser.parse(template_path)

        variables = TemplateVariables.from_entity_and_template(
            entity_data=entity_data,
            template_data=template,
            prompt_values=prompt_values,
        )

        return cls(template, variables)

    def validate_output_path(self, output_path: Union[str, Path]) -> List[str]:
        """
        Validate that output path is suitable for scaffolding.

        Args:
            output_path: Path to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        output_path = Path(output_path)

        # Check if path is absolute
        if not output_path.is_absolute():
            output_path = output_path.resolve()

        # Check if path exists and is not empty
        if output_path.exists():
            if output_path.is_file():
                issues.append(f"Output path is a file, not a directory: {output_path}")
            elif any(output_path.iterdir()):
                issues.append(f"Output directory is not empty: {output_path}")

        # Check if parent directory exists
        parent = output_path.parent
        if not parent.exists():
            issues.append(f"Parent directory does not exist: {parent}")

        # Check write permissions on parent
        if parent.exists() and not os.access(parent, os.W_OK):
            issues.append(f"No write permission for: {parent}")

        return issues

    def get_template_info(self) -> Dict[str, Any]:
        """
        Get information about the template being executed.

        Returns:
            Dictionary with template metadata
        """
        return {
            "name": self.template.get("name"),
            "version": self.template.get("version"),
            "description": self.template.get("description"),
            "author": self.template.get("author"),
            "structure_count": len(self.template.get("structure", [])),
            "files_count": len(self.template.get("files", [])),
            "copy_count": len(self.template.get("copy", [])),
            "has_git": bool(self.template.get("git", {}).get("init")),
            "has_initial_commit": bool(
                self.template.get("git", {}).get("initial_commit")
            ),
        }


def execute_template(
    template_path: Union[str, Path],
    output_path: Union[str, Path],
    entity_data: Dict[str, Any],
    prompt_values: Optional[Dict[str, Any]] = None,
    dry_run: bool = False,
) -> ScaffoldResult:
    """
    Execute a template scaffolding operation.

    This is a convenience function that combines template parsing,
    variable resolution, and execution in one call.

    Args:
        template_path: Path to template YAML file
        output_path: Path where scaffolding should be performed
        entity_data: Entity data for variable substitution
        prompt_values: Optional user-provided prompt values
        dry_run: If True, simulate without making changes

    Returns:
        ScaffoldResult with details of what was created

    Raises:
        TemplateNotFoundError: If template file doesn't exist
        TemplateLoadError: If template cannot be parsed
        InvalidTemplateError: If template is invalid
        ScaffoldError: If scaffolding fails
    """
    executor = TemplateExecutor.from_template_file(
        template_path=template_path,
        entity_data=entity_data,
        prompt_values=prompt_values,
    )

    return executor.execute(output_path=output_path, dry_run=dry_run)


def preview_template(
    template_path: Union[str, Path],
    output_path: Union[str, Path],
    entity_data: Dict[str, Any],
    prompt_values: Optional[Dict[str, Any]] = None,
) -> ScaffoldResult:
    """
    Preview a template scaffolding operation without making changes.

    Args:
        template_path: Path to template YAML file
        output_path: Path where scaffolding would be performed
        entity_data: Entity data for variable substitution
        prompt_values: Optional user-provided prompt values

    Returns:
        ScaffoldResult with preview of what would be created
    """
    return execute_template(
        template_path=template_path,
        output_path=output_path,
        entity_data=entity_data,
        prompt_values=prompt_values,
        dry_run=True,
    )