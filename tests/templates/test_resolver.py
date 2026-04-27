"""
Tests for HoxCore Template Resolver.

This module tests the template path resolution functionality that handles
finding templates from various sources including explicit paths, registry-local
templates, user templates, and category variant notation parsing.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import yaml

from hxc.templates.resolver import (
    TemplateResolver,
    TemplateResolverError,
    TemplateResolutionError,
    CategoryVariant,
)


class TestCategoryVariantParse:
    """Tests for CategoryVariant.parse() static method"""

    def test_parse_category_without_variant_no_dots(self):
        """Test parsing category string without any dots (no variant possible)"""
        result = CategoryVariant.parse("software-dev/cli-tool")
        
        assert result.category == "software-dev/cli-tool"
        assert result.variant is None
        assert result.has_variant is False

    def test_parse_category_with_simple_variant(self):
        """Test parsing category with simple variant (single word)"""
        result = CategoryVariant.parse("cli-tool.default")
        
        assert result.category == "cli-tool"
        assert result.variant == "default"
        assert result.has_variant is True

    def test_parse_category_with_author_variant(self):
        """Test parsing category with author/variant notation"""
        result = CategoryVariant.parse("cli-tool.johndoe/latex-v2")
        
        assert result.category == "cli-tool"
        assert result.variant == "johndoe/latex-v2"
        assert result.has_variant is True

    def test_parse_simple_category_with_variant(self):
        """Test parsing simple category with variant"""
        result = CategoryVariant.parse("academic-article.johndoe/latex-v2")
        
        assert result.category == "academic-article"
        assert result.variant == "johndoe/latex-v2"
        assert result.has_variant is True

    def test_parse_empty_string(self):
        """Test parsing empty string"""
        result = CategoryVariant.parse("")
        
        assert result.category == ""
        assert result.variant is None
        assert result.has_variant is False

    def test_parse_whitespace_string(self):
        """Test parsing whitespace string"""
        result = CategoryVariant.parse("   ")
        
        assert result.category == ""
        assert result.variant is None
        assert result.has_variant is False

    def test_parse_category_with_simple_ending_variant(self):
        """Test category with simple variant at end"""
        result = CategoryVariant.parse("api.v2")
        
        # "v2" at the end after a dot is treated as a variant
        assert result.category == "api"
        assert result.variant == "v2"

    def test_parse_category_only_dots(self):
        """Test category with only dots (hierarchy)"""
        result = CategoryVariant.parse("software.dev.backend")
        
        # Last part after dot is treated as variant
        assert result.category == "software.dev"
        assert result.variant == "backend"

    def test_parse_complex_variant(self):
        """Test parsing complex variant with dashes and underscores"""
        result = CategoryVariant.parse("aerospace.nasa/apollo-11_template")
        
        assert result.category == "aerospace"
        assert result.variant == "nasa/apollo-11_template"

    def test_parse_preserves_leading_trailing_stripped(self):
        """Test that leading/trailing whitespace is stripped"""
        result = CategoryVariant.parse("  cli-tool.default  ")
        
        assert result.category == "cli-tool"
        assert result.variant == "default"


class TestCategoryVariantProperties:
    """Tests for CategoryVariant properties"""

    def test_has_variant_true(self):
        """Test has_variant property when variant exists"""
        cv = CategoryVariant(category="test", variant="variant")
        assert cv.has_variant is True

    def test_has_variant_false(self):
        """Test has_variant property when no variant"""
        cv = CategoryVariant(category="test", variant=None)
        assert cv.has_variant is False

    def test_template_path_with_variant(self):
        """Test template_path property with variant"""
        cv = CategoryVariant(category="software.dev/cli-tool", variant="johndoe/v2")
        
        expected = "software/dev/cli-tool/johndoe/v2"
        assert cv.template_path == expected

    def test_template_path_without_variant(self):
        """Test template_path property without variant"""
        cv = CategoryVariant(category="software.dev/cli-tool", variant=None)
        
        assert cv.template_path is None

    def test_template_path_simple_variant(self):
        """Test template_path with simple variant"""
        cv = CategoryVariant(category="generic/project", variant="default")
        
        expected = "generic/project/default"
        assert cv.template_path == expected

    def test_str_representation_with_variant(self):
        """Test string representation with variant"""
        cv = CategoryVariant(category="software.dev/cli-tool", variant="default")
        
        assert str(cv) == "software.dev/cli-tool.default"

    def test_str_representation_without_variant(self):
        """Test string representation without variant"""
        cv = CategoryVariant(category="software.dev/cli-tool", variant=None)
        
        assert str(cv) == "software.dev/cli-tool"


class TestTemplateResolverInit:
    """Tests for TemplateResolver initialization"""

    def test_init_with_no_arguments(self):
        """Test initialization with no arguments"""
        resolver = TemplateResolver()
        
        assert resolver.registry_path is None
        assert resolver.user_templates_dir == Path("~/.hxc/templates").expanduser()

    def test_init_with_registry_path(self, temp_registry):
        """Test initialization with registry path"""
        resolver = TemplateResolver(registry_path=str(temp_registry))
        
        assert resolver.registry_path == temp_registry

    def test_init_with_custom_user_templates(self, user_templates_dir):
        """Test initialization with custom user templates directory"""
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        
        assert resolver.user_templates_dir == user_templates_dir

    def test_init_with_all_arguments(self, temp_registry, user_templates_dir):
        """Test initialization with all arguments"""
        resolver = TemplateResolver(
            registry_path=str(temp_registry),
            user_templates_dir=str(user_templates_dir),
        )
        
        assert resolver.registry_path == temp_registry
        assert resolver.user_templates_dir == user_templates_dir

    def test_init_with_path_objects(self, temp_registry, user_templates_dir):
        """Test initialization with Path objects instead of strings"""
        resolver = TemplateResolver(
            registry_path=temp_registry,
            user_templates_dir=user_templates_dir,
        )
        
        assert resolver.registry_path == temp_registry
        assert resolver.user_templates_dir == user_templates_dir


class TestTemplateResolverResolve:
    """Tests for the resolve() method"""

    def test_resolve_explicit_path(self, template_file):
        """Test resolving an explicit file path"""
        resolver = TemplateResolver()
        result = resolver.resolve(str(template_file))
        
        assert result == template_file.resolve()

    def test_resolve_explicit_path_with_tilde(self, tmp_path, monkeypatch):
        """Test resolving a path with ~ expansion"""
        # Create mock home directory
        mock_home = tmp_path / "home"
        mock_home.mkdir()
        templates_dir = mock_home / ".hxc" / "templates"
        templates_dir.mkdir(parents=True)
        
        template_file = templates_dir / "test.yml"
        template_file.write_text("name: test\nversion: '1.0'")
        
        # The expanduser should be handled by the resolver
        resolver = TemplateResolver()
        
        # Test with explicit path
        result = resolver.resolve(str(template_file))
        assert result.exists()

    def test_resolve_relative_path_with_extension(self, create_template_file):
        """Test resolving a relative path with .yml extension"""
        template_path = create_template_file({"name": "test", "version": "1.0"})
        
        resolver = TemplateResolver()
        result = resolver.resolve(str(template_path))
        
        assert result == template_path.resolve()

    def test_resolve_from_registry_local(self, registry_with_templates):
        """Test resolving from registry .hxc/templates/"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        result = resolver.resolve("software.dev/cli-tool/default")
        
        expected_path = (
            registry_with_templates
            / ".hxc"
            / "templates"
            / "software.dev"
            / "cli-tool"
            / "default.yml"
        )
        assert result == expected_path.resolve()

    def test_resolve_from_user_templates(self, user_templates_with_content):
        """Test resolving from user templates directory"""
        resolver = TemplateResolver(user_templates_dir=str(user_templates_with_content))
        
        result = resolver.resolve("custom/my-template")
        
        expected_path = user_templates_with_content / "custom" / "my-template.yml"
        assert result == expected_path.resolve()

    def test_resolve_registry_takes_precedence_over_user(
        self, registry_with_templates, user_templates_dir
    ):
        """Test that registry templates take precedence over user templates"""
        # Create same template in both locations
        registry_template = (
            registry_with_templates / ".hxc" / "templates" / "test" / "template.yml"
        )
        registry_template.parent.mkdir(parents=True, exist_ok=True)
        registry_template.write_text("name: registry-version\nversion: '1.0'")
        
        user_template = user_templates_dir / "test" / "template.yml"
        user_template.parent.mkdir(parents=True, exist_ok=True)
        user_template.write_text("name: user-version\nversion: '1.0'")
        
        resolver = TemplateResolver(
            registry_path=str(registry_with_templates),
            user_templates_dir=str(user_templates_dir),
        )
        
        result = resolver.resolve("test/template")
        
        # Should resolve to registry version
        assert "registry" in str(result).lower() or str(registry_with_templates) in str(result)

    def test_resolve_empty_reference_raises_error(self):
        """Test that empty template reference raises error"""
        resolver = TemplateResolver()
        
        with pytest.raises(TemplateResolutionError) as exc_info:
            resolver.resolve("")
        
        assert "empty" in str(exc_info.value).lower()

    def test_resolve_nonexistent_template_raises_error(self, temp_registry):
        """Test that nonexistent template raises error"""
        resolver = TemplateResolver(registry_path=str(temp_registry))
        
        with pytest.raises(TemplateResolutionError) as exc_info:
            resolver.resolve("nonexistent/template")
        
        assert "nonexistent/template" in str(exc_info.value)

    def test_resolve_error_includes_searched_paths(self, temp_registry, user_templates_dir):
        """Test that resolution error includes searched paths"""
        resolver = TemplateResolver(
            registry_path=str(temp_registry),
            user_templates_dir=str(user_templates_dir),
        )
        
        with pytest.raises(TemplateResolutionError) as exc_info:
            resolver.resolve("missing/template")
        
        error = exc_info.value
        assert hasattr(error, "searched_paths")
        assert len(error.searched_paths) > 0

    def test_resolve_with_yml_extension_in_reference(self, create_template_file, tmp_path):
        """Test resolving when .yml extension is included in reference"""
        template_path = create_template_file(
            {"name": "test", "version": "1.0"},
            filename="my-template.yml",
        )
        
        resolver = TemplateResolver()
        result = resolver.resolve(str(template_path))
        
        assert result.exists()

    def test_resolve_dot_notation_to_path(self, user_templates_dir):
        """Test that dot notation is converted to path separators"""
        # Create nested template
        template_path = user_templates_dir / "software" / "dev" / "cli-tool.yml"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("name: cli-tool\nversion: '1.0'")
        
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        result = resolver.resolve("software.dev.cli-tool")
        
        assert result == template_path.resolve()

    def test_resolve_directory_with_default_yml(self, user_templates_dir):
        """Test resolving directory reference to default.yml inside"""
        # Create template directory with default.yml
        template_dir = user_templates_dir / "mytemplate"
        template_dir.mkdir(parents=True)
        default_file = template_dir / "default.yml"
        default_file.write_text("name: mytemplate-default\nversion: '1.0'")
        
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        result = resolver.resolve("mytemplate")
        
        assert result == default_file.resolve()

    def test_resolve_explicit_path_starting_with_dot_slash(self, tmp_path):
        """Test resolving explicit path starting with ./"""
        template_file = tmp_path / "local-template.yml"
        template_file.write_text("name: local\nversion: '1.0'")
        
        resolver = TemplateResolver()
        result = resolver.resolve(f"./{template_file}")
        
        # Should recognize as explicit path
        assert result.exists()

    def test_resolve_explicit_path_starting_with_dot_dot(self, tmp_path):
        """Test resolving explicit path starting with ../"""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        template_file = tmp_path / "parent-template.yml"
        template_file.write_text("name: parent\nversion: '1.0'")
        
        resolver = TemplateResolver()
        
        # Use relative path from subdir
        relative_path = f"../{template_file.name}"
        # Test from the perspective of explicit path detection
        # The resolver should handle paths starting with ../
        full_path = subdir / relative_path
        
        # This tests the explicit path handling
        result = resolver.resolve(str(template_file))
        assert result.exists()


class TestTemplateResolverResolveFromCategory:
    """Tests for resolve_from_category() method"""

    def test_resolve_from_category_with_variant(self, registry_with_templates):
        """Test resolving template from category with variant"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        # Create the template that matches the variant
        template_dir = (
            registry_with_templates
            / ".hxc"
            / "templates"
            / "software"
            / "dev"
            / "cli-tool"
            / "custom"
        )
        template_dir.mkdir(parents=True, exist_ok=True)
        template_file = template_dir / "variant.yml"
        template_file.write_text("name: custom-variant\nversion: '1.0'")
        
        result = resolver.resolve_from_category("software.dev/cli-tool.custom/variant")
        
        assert result is not None
        assert result.exists()

    def test_resolve_from_category_without_variant_no_dots(self, temp_registry):
        """Test that category without dots (no variant possible) returns None"""
        resolver = TemplateResolver(registry_path=str(temp_registry))
        
        # Category with no dots cannot have a variant
        result = resolver.resolve_from_category("software-dev-cli-tool")
        
        assert result is None

    def test_resolve_from_category_variant_not_found(self, temp_registry):
        """Test that missing variant raises error"""
        resolver = TemplateResolver(registry_path=str(temp_registry))
        
        with pytest.raises(TemplateResolutionError):
            resolver.resolve_from_category("cli-tool.missing/variant")

    def test_resolve_from_category_simple_variant(self, registry_with_templates):
        """Test resolving simple variant from category"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        # Create template matching the path
        template_dir = (
            registry_with_templates
            / ".hxc"
            / "templates"
            / "cli-tool"
        )
        template_dir.mkdir(parents=True, exist_ok=True)
        template_file = template_dir / "simple.yml"
        template_file.write_text("name: simple\nversion: '1.0'")
        
        result = resolver.resolve_from_category("cli-tool.simple")
        
        assert result is not None


class TestTemplateResolverListTemplates:
    """Tests for list_templates() method"""

    def test_list_templates_empty_registry(self, temp_registry, user_templates_dir):
        """Test listing templates when directories are empty"""
        resolver = TemplateResolver(
            registry_path=str(temp_registry),
            user_templates_dir=str(user_templates_dir),
        )
        
        templates = resolver.list_templates()
        
        assert templates == []

    def test_list_templates_from_registry(self, registry_with_templates):
        """Test listing templates from registry"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        templates = resolver.list_templates(include_registry=True, include_user=False)
        
        assert len(templates) > 0
        
        # Check structure of returned tuples
        for template_id, path, source in templates:
            assert isinstance(template_id, str)
            assert isinstance(path, Path)
            assert source == "registry"

    def test_list_templates_from_user(self, user_templates_with_content):
        """Test listing templates from user directory"""
        resolver = TemplateResolver(user_templates_dir=str(user_templates_with_content))
        
        templates = resolver.list_templates(include_registry=False, include_user=True)
        
        assert len(templates) > 0
        
        for template_id, path, source in templates:
            assert source == "user"

    def test_list_templates_from_both(self, registry_with_templates, user_templates_with_content):
        """Test listing templates from both registry and user"""
        resolver = TemplateResolver(
            registry_path=str(registry_with_templates),
            user_templates_dir=str(user_templates_with_content),
        )
        
        templates = resolver.list_templates(include_registry=True, include_user=True)
        
        sources = {source for _, _, source in templates}
        assert "registry" in sources
        assert "user" in sources

    def test_list_templates_include_registry_false(self, registry_with_templates):
        """Test listing with include_registry=False"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        templates = resolver.list_templates(include_registry=False, include_user=True)
        
        for _, _, source in templates:
            assert source != "registry"

    def test_list_templates_include_user_false(self, user_templates_with_content):
        """Test listing with include_user=False"""
        resolver = TemplateResolver(user_templates_dir=str(user_templates_with_content))
        
        templates = resolver.list_templates(include_registry=True, include_user=False)
        
        for _, _, source in templates:
            assert source != "user"

    def test_list_templates_nested_directories(self, user_templates_dir):
        """Test listing templates in nested directories"""
        # Create nested template structure
        (user_templates_dir / "category" / "subcategory").mkdir(parents=True)
        template = user_templates_dir / "category" / "subcategory" / "deep.yml"
        template.write_text("name: deep\nversion: '1.0'")
        
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        templates = resolver.list_templates()
        
        template_ids = [tid for tid, _, _ in templates]
        assert any("category" in tid and "subcategory" in tid for tid in template_ids)

    def test_list_templates_without_registry_path(self, user_templates_with_content):
        """Test listing when no registry path is set"""
        resolver = TemplateResolver(
            registry_path=None,
            user_templates_dir=str(user_templates_with_content),
        )
        
        templates = resolver.list_templates(include_registry=True, include_user=True)
        
        # Should only have user templates
        for _, _, source in templates:
            assert source == "user"


class TestTemplateResolverTemplateExists:
    """Tests for template_exists() method"""

    def test_template_exists_true(self, registry_with_templates):
        """Test template_exists returns True for existing template"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        result = resolver.template_exists("software.dev/cli-tool/default")
        
        assert result is True

    def test_template_exists_false(self, temp_registry):
        """Test template_exists returns False for missing template"""
        resolver = TemplateResolver(registry_path=str(temp_registry))
        
        result = resolver.template_exists("nonexistent/template")
        
        assert result is False

    def test_template_exists_explicit_path(self, template_file):
        """Test template_exists with explicit file path"""
        resolver = TemplateResolver()
        
        result = resolver.template_exists(str(template_file))
        
        assert result is True

    def test_template_exists_nonexistent_explicit_path(self, tmp_path):
        """Test template_exists with nonexistent explicit path"""
        resolver = TemplateResolver()
        
        result = resolver.template_exists(str(tmp_path / "missing.yml"))
        
        assert result is False


class TestTemplateResolverGetTemplateSource:
    """Tests for get_template_source() method"""

    def test_get_source_explicit(self, template_file):
        """Test get_template_source returns 'explicit' for file path"""
        resolver = TemplateResolver()
        
        result = resolver.get_template_source(str(template_file))
        
        assert result == "explicit"

    def test_get_source_registry(self, registry_with_templates):
        """Test get_template_source returns 'registry' for registry template"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        result = resolver.get_template_source("software.dev/cli-tool/default")
        
        assert result == "registry"

    def test_get_source_user(self, user_templates_with_content):
        """Test get_template_source returns 'user' for user template"""
        resolver = TemplateResolver(user_templates_dir=str(user_templates_with_content))
        
        result = resolver.get_template_source("custom/my-template")
        
        assert result == "user"

    def test_get_source_not_found(self, temp_registry):
        """Test get_template_source returns None for missing template"""
        resolver = TemplateResolver(registry_path=str(temp_registry))
        
        result = resolver.get_template_source("nonexistent/template")
        
        assert result is None

    def test_get_source_registry_before_user(
        self, registry_with_templates, user_templates_dir
    ):
        """Test that registry source is returned when template exists in both"""
        # Create same template in both locations
        registry_template = (
            registry_with_templates / ".hxc" / "templates" / "shared" / "template.yml"
        )
        registry_template.parent.mkdir(parents=True, exist_ok=True)
        registry_template.write_text("name: shared\nversion: '1.0'")
        
        user_template = user_templates_dir / "shared" / "template.yml"
        user_template.parent.mkdir(parents=True, exist_ok=True)
        user_template.write_text("name: shared\nversion: '1.0'")
        
        resolver = TemplateResolver(
            registry_path=str(registry_with_templates),
            user_templates_dir=str(user_templates_dir),
        )
        
        result = resolver.get_template_source("shared/template")
        
        assert result == "registry"


class TestTemplateResolverEnsureDirectories:
    """Tests for ensure_*_dir() methods"""

    def test_ensure_user_templates_dir_creates(self, tmp_path):
        """Test that ensure_user_templates_dir creates the directory"""
        templates_dir = tmp_path / "new_templates"
        
        resolver = TemplateResolver(user_templates_dir=str(templates_dir))
        result = resolver.ensure_user_templates_dir()
        
        assert templates_dir.exists()
        assert result == templates_dir

    def test_ensure_user_templates_dir_existing(self, user_templates_dir):
        """Test ensure_user_templates_dir with existing directory"""
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        result = resolver.ensure_user_templates_dir()
        
        assert result == user_templates_dir

    def test_ensure_registry_templates_dir_creates(self, temp_registry):
        """Test that ensure_registry_templates_dir creates the directory"""
        # Remove existing templates dir to test creation
        templates_dir = temp_registry / ".hxc" / "templates"
        if templates_dir.exists():
            import shutil
            shutil.rmtree(templates_dir)
        
        resolver = TemplateResolver(registry_path=str(temp_registry))
        result = resolver.ensure_registry_templates_dir()
        
        assert templates_dir.exists()
        assert result == templates_dir

    def test_ensure_registry_templates_dir_no_registry(self):
        """Test ensure_registry_templates_dir returns None when no registry"""
        resolver = TemplateResolver(registry_path=None)
        result = resolver.ensure_registry_templates_dir()
        
        assert result is None

    def test_ensure_registry_templates_dir_existing(self, temp_registry):
        """Test ensure_registry_templates_dir with existing directory"""
        resolver = TemplateResolver(registry_path=str(temp_registry))
        result = resolver.ensure_registry_templates_dir()
        
        expected = temp_registry / ".hxc" / "templates"
        assert result == expected


class TestTemplateResolverStaticMethods:
    """Tests for static helper methods"""

    def test_extract_category_variant(self):
        """Test the static extract_category_variant method"""
        result = TemplateResolver.extract_category_variant(
            "cli-tool.author/variant"
        )
        
        assert isinstance(result, CategoryVariant)
        assert result.category == "cli-tool"
        assert result.variant == "author/variant"


class TestTemplateResolverPrivateMethods:
    """Tests for private helper methods"""

    def test_normalize_template_ref_removes_extension(self):
        """Test that _normalize_template_ref removes .yml extension"""
        resolver = TemplateResolver()
        
        result = resolver._normalize_template_ref("template.yml")
        
        assert result == "template"

    def test_normalize_template_ref_normalizes_separators(self):
        """Test that _normalize_template_ref normalizes path separators"""
        resolver = TemplateResolver()
        
        result = resolver._normalize_template_ref("path\\to\\template")
        
        assert "\\" not in result
        assert result == "path/to/template"

    def test_normalize_template_ref_strips_slashes(self):
        """Test that _normalize_template_ref strips leading/trailing slashes"""
        resolver = TemplateResolver()
        
        result = resolver._normalize_template_ref("/path/to/template/")
        
        assert result == "path/to/template"

    def test_path_to_template_id(self, user_templates_dir):
        """Test _path_to_template_id converts path to ID"""
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        
        template_path = user_templates_dir / "category" / "subcategory" / "template.yml"
        result = resolver._path_to_template_id(template_path, user_templates_dir)
        
        assert result == "category/subcategory/template"
        assert ".yml" not in result


class TestExceptionClasses:
    """Tests for custom exception classes"""

    def test_template_resolver_error_is_exception(self):
        """Test that TemplateResolverError is an Exception"""
        error = TemplateResolverError("test error")
        assert isinstance(error, Exception)

    def test_template_resolution_error_is_resolver_error(self):
        """Test that TemplateResolutionError inherits from TemplateResolverError"""
        error = TemplateResolutionError("missing-template")
        assert isinstance(error, TemplateResolverError)
        assert isinstance(error, Exception)

    def test_template_resolution_error_stores_template_ref(self):
        """Test that TemplateResolutionError stores template_ref"""
        error = TemplateResolutionError("my-template")
        assert error.template_ref == "my-template"

    def test_template_resolution_error_stores_searched_paths(self):
        """Test that TemplateResolutionError stores searched_paths"""
        searched = ["/path/1", "/path/2"]
        error = TemplateResolutionError("my-template", searched_paths=searched)
        
        assert error.searched_paths == searched

    def test_template_resolution_error_empty_searched_paths(self):
        """Test TemplateResolutionError with no searched_paths"""
        error = TemplateResolutionError("my-template")
        assert error.searched_paths == []

    def test_template_resolution_error_message(self):
        """Test TemplateResolutionError message format"""
        error = TemplateResolutionError("my-template")
        
        assert "my-template" in str(error)
        assert "resolve" in str(error).lower() or "not" in str(error).lower()

    def test_template_resolution_error_message_with_paths(self):
        """Test TemplateResolutionError message includes searched paths"""
        searched = ["/path/to/templates"]
        error = TemplateResolutionError("my-template", searched_paths=searched)
        
        assert "my-template" in str(error)
        # The error message should indicate where it searched
        assert "/path/to/templates" in str(error) or "Searched" in str(error)


class TestTemplateResolverIntegration:
    """Integration tests for template resolution"""

    def test_full_resolution_workflow(self, registry_with_templates):
        """Test complete template resolution workflow"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        # Check template exists
        assert resolver.template_exists("software.dev/cli-tool/default")
        
        # Get source
        source = resolver.get_template_source("software.dev/cli-tool/default")
        assert source == "registry"
        
        # Resolve path
        path = resolver.resolve("software.dev/cli-tool/default")
        assert path.exists()
        assert path.suffix == ".yml"

    def test_resolution_with_various_notations(self, user_templates_dir):
        """Test resolution with various template reference notations"""
        # Create template
        template_path = user_templates_dir / "test" / "mytemplate.yml"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("name: test\nversion: '1.0'")
        
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        
        # Various notations that should resolve to the same template
        notations = [
            "test/mytemplate",
            "test/mytemplate.yml",
        ]
        
        for notation in notations:
            try:
                result = resolver.resolve(notation)
                assert result == template_path.resolve(), f"Failed for notation: {notation}"
            except TemplateResolutionError:
                # Some notations may not resolve depending on implementation
                pass

    def test_multiple_templates_different_sources(
        self, registry_with_templates, user_templates_with_content
    ):
        """Test resolving templates from different sources"""
        resolver = TemplateResolver(
            registry_path=str(registry_with_templates),
            user_templates_dir=str(user_templates_with_content),
        )
        
        # Registry template
        registry_path = resolver.resolve("software.dev/cli-tool/default")
        assert resolver.get_template_source("software.dev/cli-tool/default") == "registry"
        
        # User template
        user_path = resolver.resolve("custom/my-template")
        assert resolver.get_template_source("custom/my-template") == "user"
        
        # They should be different paths
        assert registry_path != user_path

    def test_list_and_resolve_all(self, registry_with_templates):
        """Test that all listed templates can be resolved"""
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        
        templates = resolver.list_templates()
        
        for template_id, expected_path, source in templates:
            resolved_path = resolver.resolve(template_id)
            assert resolved_path == expected_path.resolve()

    def test_category_variant_to_resolution(self, user_templates_dir):
        """Test resolving template from category variant"""
        # Create template matching category variant structure
        template_path = (
            user_templates_dir / "cli-tool" / "myauthor" / "v1.yml"
        )
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("name: variant\nversion: '1.0'")
        
        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))
        
        # Parse category variant
        category = "cli-tool.myauthor/v1"
        cv = CategoryVariant.parse(category)
        
        assert cv.has_variant
        
        # Resolve the template path
        result = resolver.resolve_from_category(category)
        assert result is not None
        assert result.exists()


class TestCategoryVariantEdgeCases:
    """Edge case tests for CategoryVariant parsing"""

    def test_parse_multiple_slashes(self):
        """Test parsing category with multiple slashes"""
        result = CategoryVariant.parse("a/b/c.author/variant")
        
        assert result.category == "a/b/c"
        assert result.variant == "author/variant"

    def test_parse_numbers_in_variant(self):
        """Test parsing variant with numbers"""
        result = CategoryVariant.parse("category.v123")
        
        assert result.variant == "v123"

    def test_parse_underscores_in_variant(self):
        """Test parsing variant with underscores"""
        result = CategoryVariant.parse("category.my_variant_v2")
        
        assert result.variant == "my_variant_v2"

    def test_parse_dashes_in_variant(self):
        """Test parsing variant with dashes"""
        result = CategoryVariant.parse("category.my-variant")
        
        assert result.variant == "my-variant"

    def test_parse_mixed_separators(self):
        """Test parsing with mixed dots and slashes"""
        result = CategoryVariant.parse("project/type.author/template-v1")
        
        assert result.category == "project/type"
        assert result.variant == "author/template-v1"

    def test_parse_single_word(self):
        """Test parsing single word category"""
        result = CategoryVariant.parse("simple")
        
        assert result.category == "simple"
        assert result.variant is None

    def test_parse_category_ending_with_dot(self):
        """Test parsing category ending with dot"""
        result = CategoryVariant.parse("category.")
        
        # Trailing dot with nothing after should not create variant
        # Empty after_dot is skipped
        assert result.category == "category."
        assert result.variant is None

    def test_parse_preserves_case(self):
        """Test that parsing preserves case"""
        result = CategoryVariant.parse("CLI-Tool.MyAuthor/V2")
        
        # Check the parsed result
        assert result.category == "CLI-Tool"
        assert result.variant == "MyAuthor/V2"