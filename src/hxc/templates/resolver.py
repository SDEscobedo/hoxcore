"""
HoxCore Template Resolver.

This module provides template path resolution from various sources including
explicit paths, registry-local templates, user templates, and category
variant notation parsing.

Template Resolution Order:
1. Explicit path: `--template ./my-template.yml`
2. Registry-local: `.hxc/templates/<template-path>.yml`
3. User templates: `~/.hxc/templates/<template-path>.yml`
4. Category extraction: Parse `category: software.dev/cli-tool.author/variant`
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Union


class TemplateResolverError(Exception):
    """Base exception for template resolver errors"""

    pass


class TemplateResolutionError(TemplateResolverError):
    """Raised when a template cannot be resolved to a valid path"""

    def __init__(self, template_ref: str, searched_paths: Optional[List[str]] = None):
        self.template_ref = template_ref
        self.searched_paths = searched_paths or []
        message = f"Could not resolve template: {template_ref}"
        if searched_paths:
            paths_str = "\n  - ".join(searched_paths)
            message += f"\nSearched locations:\n  - {paths_str}"
        super().__init__(message)


# Common hierarchy segments that are part of category paths, not author names
_COMMON_HIERARCHY_SEGMENTS = frozenset({
    'dev', 'org', 'com', 'net', 'io', 'co', 'gov', 'edu', 'api', 'app',
    'web', 'cli', 'lib', 'pkg', 'src', 'doc', 'docs', 'test', 'tests'
})


@dataclass
class CategoryVariant:
    """
    Parsed category notation with optional template variant.

    Category notation format: `category-path.author/variant`

    Examples:
        - `software.dev/cli-tool` -> category only, no variant
        - `software.dev/cli-tool.default` -> category with local variant
        - `software.dev/cli-tool.johndoe/latex-v2` -> category with author/variant

    Attributes:
        category: The base category path (e.g., "software.dev/cli-tool")
        variant: The template variant if present (e.g., "johndoe/latex-v2")
        has_variant: Whether a variant was specified
    """

    category: str
    variant: Optional[str] = None

    @property
    def has_variant(self) -> bool:
        """Check if a template variant was specified"""
        return self.variant is not None

    @property
    def template_path(self) -> Optional[str]:
        """
        Get the template path derived from category and variant.

        Returns:
            Template path string or None if no variant specified
        """
        if not self.has_variant:
            return None

        # Convert category to path format
        # e.g., "software.dev/cli-tool" -> "software/dev/cli-tool"
        category_path = self.category.replace(".", "/")
        # Clean up any double slashes
        while "//" in category_path:
            category_path = category_path.replace("//", "/")

        # Combine with variant
        # e.g., "software/dev/cli-tool" + "johndoe/latex-v2"
        #    -> "software/dev/cli-tool/johndoe/latex-v2"
        return f"{category_path}/{self.variant}"

    @classmethod
    def parse(cls, category_string: str) -> "CategoryVariant":
        """
        Parse a category string into category and variant components.

        The format is: `category-path.variant` where:
        - category-path can contain dots and slashes for hierarchy
        - variant is separated by a dot and can be:
          - A simple identifier (e.g., "default")
          - An author/variant pattern (e.g., "johndoe/latex-v2")

        The key distinction is that common hierarchy segments (like "dev", "org")
        followed by a slash are part of the category, not an author/variant.

        Examples:
            "software.dev/cli-tool" -> category="software.dev/cli-tool", variant=None
            "software.dev/cli-tool.default" -> category="software.dev/cli-tool", variant="default"
            "software.dev/cli-tool.johndoe/v2" -> category="software.dev/cli-tool", variant="johndoe/v2"
            "academic-article.johndoe/latex-v2" -> category="academic-article", variant="johndoe/latex-v2"

        Args:
            category_string: The category string to parse

        Returns:
            CategoryVariant instance with parsed components
        """
        if not category_string:
            return cls(category="", variant=None)

        category_string = category_string.strip()

        if not category_string:
            return cls(category="", variant=None)

        # Find all dot positions
        dot_positions = [i for i, c in enumerate(category_string) if c == '.']

        if not dot_positions:
            # No dots, entire string is category
            return cls(category=category_string, variant=None)

        # Check from right to left for valid variant patterns
        for dot_idx in reversed(dot_positions):
            after_dot = category_string[dot_idx + 1:]
            before_dot = category_string[:dot_idx]

            # Skip if either part would be empty
            if not after_dot or not before_dot:
                continue

            # Case 1: Simple identifier (no slash) - e.g., "default"
            if '/' not in after_dot:
                # Must be a valid identifier at the end
                if re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', after_dot):
                    return cls(category=before_dot, variant=after_dot)

            # Case 2: Author/variant pattern (contains slash) - e.g., "johndoe/latex-v2"
            else:
                # Split on the first slash to get author and variant name
                slash_idx = after_dot.find('/')
                author_part = after_dot[:slash_idx]
                variant_name = after_dot[slash_idx + 1:]

                # Validate both parts are valid identifiers
                if (author_part and variant_name and
                    re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', author_part) and
                    re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', variant_name)):

                    # Check if author_part looks like an author name (not a common segment)
                    # Common segments like "dev", "org" are part of category hierarchy
                    if author_part.lower() not in _COMMON_HIERARCHY_SEGMENTS:
                        return cls(category=before_dot, variant=after_dot)

        # No valid variant found, entire string is category
        return cls(category=category_string, variant=None)

    def __str__(self) -> str:
        """String representation of the category variant"""
        if self.has_variant:
            return f"{self.category}.{self.variant}"
        return self.category


class TemplateResolver:
    """
    Resolver for HoxCore template paths.

    This class handles resolution of template references to actual file paths,
    supporting multiple resolution strategies:

    1. Explicit paths (absolute or relative file paths)
    2. Registry-local templates (`.hxc/templates/` in registry)
    3. User templates (`~/.hxc/templates/`)
    4. Category variant extraction (parsing category notation)

    Example Usage:
        >>> resolver = TemplateResolver(registry_path="/path/to/registry")
        >>> template_path = resolver.resolve("software.dev/cli-tool/default")
        >>> print(template_path)
        '/home/user/.hxc/templates/software.dev/cli-tool/default.yml'

    Attributes:
        registry_path: Path to the current registry (optional)
        user_templates_dir: Path to user templates directory (~/.hxc/templates)
    """

    DEFAULT_USER_TEMPLATES_DIR = "~/.hxc/templates"
    TEMPLATE_EXTENSION = ".yml"

    def __init__(
        self,
        registry_path: Optional[Union[str, Path]] = None,
        user_templates_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize the template resolver.

        Args:
            registry_path: Path to the current registry (optional)
            user_templates_dir: Custom user templates directory (optional)
        """
        self.registry_path = Path(registry_path) if registry_path else None
        self.user_templates_dir = Path(
            user_templates_dir or self.DEFAULT_USER_TEMPLATES_DIR
        ).expanduser()

    def resolve(self, template_ref: str) -> Path:
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
            TemplateResolutionError: If template cannot be resolved
        """
        if not template_ref:
            raise TemplateResolutionError(
                template_ref, ["Template reference cannot be empty"]
            )

        template_ref = template_ref.strip()
        searched_paths: List[str] = []

        # 1. Try as explicit path first
        explicit_path = self._try_explicit_path(template_ref)
        if explicit_path:
            return explicit_path
        searched_paths.append(f"Explicit path: {template_ref}")

        # Normalize the template reference for directory lookups
        normalized_ref = self._normalize_template_ref(template_ref)

        # 2. Try registry-local templates
        if self.registry_path:
            registry_template = self._try_registry_local(normalized_ref)
            if registry_template:
                return registry_template
            registry_templates_dir = self.registry_path / ".hxc" / "templates"
            searched_paths.append(f"Registry local: {registry_templates_dir}")

        # 3. Try user templates
        user_template = self._try_user_templates(normalized_ref)
        if user_template:
            return user_template
        searched_paths.append(f"User templates: {self.user_templates_dir}")

        # 4. Could not resolve
        raise TemplateResolutionError(template_ref, searched_paths)

    def resolve_from_category(self, category: str) -> Optional[Path]:
        """
        Resolve a template from a category string with variant notation.

        Args:
            category: Category string potentially containing variant notation

        Returns:
            Path to resolved template, or None if no variant specified

        Raises:
            TemplateResolutionError: If variant is specified but cannot be resolved
        """
        parsed = CategoryVariant.parse(category)

        if not parsed.has_variant:
            return None

        template_path = parsed.template_path
        if not template_path:
            return None

        return self.resolve(template_path)

    def list_templates(
        self, include_registry: bool = True, include_user: bool = True
    ) -> List[Tuple[str, Path, str]]:
        """
        List all available templates.

        Args:
            include_registry: Include registry-local templates
            include_user: Include user templates

        Returns:
            List of tuples (template_id, path, source) where source is
            'registry' or 'user'
        """
        templates: List[Tuple[str, Path, str]] = []

        # Registry-local templates
        if include_registry and self.registry_path:
            registry_templates_dir = self.registry_path / ".hxc" / "templates"
            if registry_templates_dir.exists():
                for template_path in registry_templates_dir.rglob(
                    f"*{self.TEMPLATE_EXTENSION}"
                ):
                    template_id = self._path_to_template_id(
                        template_path, registry_templates_dir
                    )
                    templates.append((template_id, template_path, "registry"))

        # User templates
        if include_user and self.user_templates_dir.exists():
            for template_path in self.user_templates_dir.rglob(
                f"*{self.TEMPLATE_EXTENSION}"
            ):
                template_id = self._path_to_template_id(
                    template_path, self.user_templates_dir
                )
                templates.append((template_id, template_path, "user"))

        return templates

    def template_exists(self, template_ref: str) -> bool:
        """
        Check if a template reference can be resolved.

        Args:
            template_ref: Template reference to check

        Returns:
            True if template can be resolved, False otherwise
        """
        try:
            self.resolve(template_ref)
            return True
        except TemplateResolutionError:
            return False

    def get_template_source(self, template_ref: str) -> Optional[str]:
        """
        Get the source of a template (explicit, registry, or user).

        Args:
            template_ref: Template reference

        Returns:
            Source string ('explicit', 'registry', 'user') or None if not found
        """
        template_ref = template_ref.strip()

        # Check explicit path
        if self._try_explicit_path(template_ref):
            return "explicit"

        normalized_ref = self._normalize_template_ref(template_ref)

        # Check registry-local
        if self.registry_path and self._try_registry_local(normalized_ref):
            return "registry"

        # Check user templates
        if self._try_user_templates(normalized_ref):
            return "user"

        return None

    def _try_explicit_path(self, template_ref: str) -> Optional[Path]:
        """
        Try to resolve template reference as an explicit file path.

        Args:
            template_ref: Template reference

        Returns:
            Path if file exists, None otherwise
        """
        path = Path(template_ref).expanduser()

        # Check if it's an absolute path or clearly a file path
        if path.is_absolute() or template_ref.startswith(
            ("./", "../", "~/")
        ):
            if path.exists() and path.is_file():
                return path.resolve()
            # Also try with extension
            if not template_ref.endswith(self.TEMPLATE_EXTENSION):
                path_with_ext = Path(f"{template_ref}{self.TEMPLATE_EXTENSION}").expanduser()
                if path_with_ext.exists() and path_with_ext.is_file():
                    return path_with_ext.resolve()
            return None

        # Check if it looks like a file path (contains extension)
        if template_ref.endswith(self.TEMPLATE_EXTENSION):
            if path.exists() and path.is_file():
                return path.resolve()

        return None

    def _try_registry_local(self, normalized_ref: str) -> Optional[Path]:
        """
        Try to resolve template from registry-local templates.

        Args:
            normalized_ref: Normalized template reference

        Returns:
            Path if found, None otherwise
        """
        if not self.registry_path:
            return None

        templates_dir = self.registry_path / ".hxc" / "templates"
        if not templates_dir.exists():
            return None

        return self._find_template_in_dir(templates_dir, normalized_ref)

    def _try_user_templates(self, normalized_ref: str) -> Optional[Path]:
        """
        Try to resolve template from user templates directory.

        Args:
            normalized_ref: Normalized template reference

        Returns:
            Path if found, None otherwise
        """
        if not self.user_templates_dir.exists():
            return None

        return self._find_template_in_dir(self.user_templates_dir, normalized_ref)

    def _find_template_in_dir(
        self, base_dir: Path, normalized_ref: str
    ) -> Optional[Path]:
        """
        Find a template file in a directory.

        Tries multiple path variations:
        1. Exact path with extension
        2. Path as directory with default.yml inside
        3. Variations with dots converted to slashes

        Args:
            base_dir: Base directory to search in
            normalized_ref: Normalized template reference

        Returns:
            Path if found, None otherwise
        """
        # Try direct path with extension
        direct_path = base_dir / f"{normalized_ref}{self.TEMPLATE_EXTENSION}"
        if direct_path.exists() and direct_path.is_file():
            return direct_path.resolve()

        # Try as directory with default.yml
        dir_path = base_dir / normalized_ref
        if dir_path.exists() and dir_path.is_dir():
            default_path = dir_path / f"default{self.TEMPLATE_EXTENSION}"
            if default_path.exists() and default_path.is_file():
                return default_path.resolve()

        # Try with dots converted to directory separators
        # e.g., "software.dev.cli-tool" -> "software/dev/cli-tool"
        alt_ref = normalized_ref.replace(".", "/")
        if alt_ref != normalized_ref:
            alt_path = base_dir / f"{alt_ref}{self.TEMPLATE_EXTENSION}"
            if alt_path.exists() and alt_path.is_file():
                return alt_path.resolve()

            # Also try as directory
            alt_dir_path = base_dir / alt_ref
            if alt_dir_path.exists() and alt_dir_path.is_dir():
                default_path = alt_dir_path / f"default{self.TEMPLATE_EXTENSION}"
                if default_path.exists() and default_path.is_file():
                    return default_path.resolve()

        return None

    def _normalize_template_ref(self, template_ref: str) -> str:
        """
        Normalize a template reference for directory lookups.

        Removes extension if present and normalizes path separators.

        Args:
            template_ref: Raw template reference

        Returns:
            Normalized reference string
        """
        # Remove extension if present
        if template_ref.endswith(self.TEMPLATE_EXTENSION):
            template_ref = template_ref[: -len(self.TEMPLATE_EXTENSION)]

        # Normalize path separators (convert backslashes to forward slashes)
        template_ref = template_ref.replace("\\", "/")

        # Remove leading/trailing slashes
        template_ref = template_ref.strip("/")

        return template_ref

    def _path_to_template_id(self, template_path: Path, base_dir: Path) -> str:
        """
        Convert a template file path to a template ID.

        Args:
            template_path: Absolute path to template file
            base_dir: Base templates directory

        Returns:
            Template ID string
        """
        relative = template_path.relative_to(base_dir)
        # Remove extension
        template_id = str(relative)
        if template_id.endswith(self.TEMPLATE_EXTENSION):
            template_id = template_id[: -len(self.TEMPLATE_EXTENSION)]
        # Normalize separators
        template_id = template_id.replace("\\", "/")
        return template_id

    def ensure_user_templates_dir(self) -> Path:
        """
        Ensure the user templates directory exists.

        Returns:
            Path to user templates directory
        """
        self.user_templates_dir.mkdir(parents=True, exist_ok=True)
        return self.user_templates_dir

    def ensure_registry_templates_dir(self) -> Optional[Path]:
        """
        Ensure the registry templates directory exists.

        Returns:
            Path to registry templates directory, or None if no registry
        """
        if not self.registry_path:
            return None

        templates_dir = self.registry_path / ".hxc" / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        return templates_dir

    @staticmethod
    def extract_category_variant(category: str) -> CategoryVariant:
        """
        Static helper to parse category notation.

        Args:
            category: Category string

        Returns:
            Parsed CategoryVariant
        """
        return CategoryVariant.parse(category)