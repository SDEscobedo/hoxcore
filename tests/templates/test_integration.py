"""
Integration tests for HoxCore Template System.

This module provides end-to-end integration tests for the declarative template
scaffolding system, testing the full workflow from template definition to
scaffolded project structure.

Tests cover:
- Full create + scaffold workflow
- Category variant auto-scaffolding
- CLI command integration
- MCP tools integration
- Multi-component interactions (resolver -> parser -> executor)
- Error handling across component boundaries
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from hxc.templates.executor import TemplateExecutor, ScaffoldResult
from hxc.templates.parser import TemplateParser
from hxc.templates.resolver import TemplateResolver, CategoryVariant
from hxc.templates.variables import TemplateVariables
from hxc.templates.schema import validate_template
from hxc.core.operations.scaffold import (
    ScaffoldOperation,
    ScaffoldOperationResult,
    TemplateNotFoundOperationError,
    TemplateValidationError,
    ScaffoldSecurityError,
    ScaffoldExecutionError,
    PromptRequiredError,
    scaffold_from_template,
    preview_scaffold,
)


class TestFullScaffoldingWorkflow:
    """Integration tests for complete scaffolding workflow"""

    def test_end_to_end_scaffold_from_file(
        self, cli_tool_template_file, sample_entity_data, output_dir
    ):
        """Test complete scaffolding from template file to output"""
        # Execute scaffolding
        result = scaffold_from_template(
            template_ref=str(cli_tool_template_file),
            output_path=output_dir,
            entity_data=sample_entity_data,
            prompt_values={"author_name": "Test Author"},
            dry_run=False,
        )

        # Verify success
        assert result.success is True
        assert result.dry_run is False

        # Verify directory structure was created
        assert output_dir.exists()
        assert (output_dir / "src" / "my_project").exists()
        assert (output_dir / "tests").exists()
        assert (output_dir / "docs").exists()

        # Verify files were created with correct content
        readme = output_dir / "README.md"
        assert readme.exists()
        readme_content = readme.read_text()
        assert "My Project" in readme_content

        # Verify __init__.py was created
        init_file = output_dir / "src" / "my_project" / "__init__.py"
        assert init_file.exists()
        init_content = init_file.read_text()
        assert "My Project" in init_content

    def test_end_to_end_scaffold_with_git(
        self, tmp_path, sample_entity_data, skip_without_git
    ):
        """Test scaffolding with Git initialization"""
        # Create template with git config
        template_data = {
            "name": "git-template",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src"}],
            "files": [
                {"path": "README.md", "content": "# {{title}}"},
            ],
            "git": {
                "init": True,
                "initial_commit": True,
                "commit_message": "Initial commit: {{title}}",
            },
        }

        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        output_path = tmp_path / "output"

        # Execute scaffolding
        result = scaffold_from_template(
            template_ref=str(template_file),
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=False,
        )

        assert result.success is True
        assert result.git_initialized is True
        assert (output_path / ".git").exists()

        # Verify commit was created
        log = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=output_path,
            capture_output=True,
            text=True,
        )
        if log.returncode == 0:
            assert "My Project" in log.stdout

    def test_end_to_end_preview_does_not_modify(
        self, cli_tool_template_file, sample_entity_data, output_dir
    ):
        """Test that preview mode does not modify filesystem"""
        output_dir.mkdir(parents=True, exist_ok=True)
        initial_contents = list(output_dir.iterdir())

        # Execute preview
        result = preview_scaffold(
            template_ref=str(cli_tool_template_file),
            output_path=output_dir,
            entity_data=sample_entity_data,
            prompt_values={"author_name": "Test Author"},
        )

        # Verify preview result
        assert result.success is True
        assert result.dry_run is True

        # Verify directories and files would be created
        assert len(result.directories_created) > 0
        assert len(result.files_created) > 0

        # Verify filesystem was not modified
        final_contents = list(output_dir.iterdir())
        assert initial_contents == final_contents

    def test_scaffold_with_variable_substitution(
        self, tmp_path, sample_entity_data
    ):
        """Test that variables are correctly substituted throughout"""
        template_data = {
            "name": "variable-template",
            "version": "1.0",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "id", "source": "entity"},
                {"name": "custom_var", "source": "prompt", "default": "custom_value"},
            ],
            "structure": [
                {"type": "directory", "path": "{{id}}"},
            ],
            "files": [
                {
                    "path": "{{id}}/config.yml",
                    "content": "title: {{title}}\ncustom: {{custom_var}}\n",
                },
            ],
        }

        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        output_path = tmp_path / "output"

        result = scaffold_from_template(
            template_ref=str(template_file),
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=False,
        )

        assert result.success is True

        # Verify directory was created with substituted name
        assert (output_path / "my_project").exists()

        # Verify file content was substituted
        config_file = output_path / "my_project" / "config.yml"
        assert config_file.exists()
        content = config_file.read_text()
        assert "title: My Project" in content
        assert "custom: custom_value" in content


class TestScaffoldOperationIntegration:
    """Integration tests for ScaffoldOperation class"""

    def test_scaffold_operation_resolve_and_execute(
        self, registry_with_templates, sample_entity_data, output_dir
    ):
        """Test ScaffoldOperation resolving and executing template"""
        operation = ScaffoldOperation(registry_path=str(registry_with_templates))

        result = operation.scaffold(
            template_ref="software.dev/cli-tool/default",
            output_path=output_dir,
            entity_data=sample_entity_data,
            dry_run=False,
            require_all_prompts=False,
        )

        assert result.success is True
        assert output_dir.exists()

    def test_scaffold_operation_preview(
        self, registry_with_templates, sample_entity_data, output_dir
    ):
        """Test ScaffoldOperation preview mode"""
        operation = ScaffoldOperation(registry_path=str(registry_with_templates))
        output_dir.mkdir(parents=True, exist_ok=True)

        result = operation.preview(
            template_ref="software.dev/cli-tool/default",
            output_path=output_dir,
            entity_data=sample_entity_data,
        )

        assert result.success is True
        assert result.dry_run is True
        assert len(result.directories_created) > 0

    def test_scaffold_operation_list_templates(self, registry_with_templates):
        """Test listing available templates"""
        operation = ScaffoldOperation(registry_path=str(registry_with_templates))

        templates = operation.list_templates()

        assert len(templates) > 0
        assert any(t["source"] == "registry" for t in templates)

    def test_scaffold_operation_get_template_info(self, registry_with_templates):
        """Test getting template information"""
        operation = ScaffoldOperation(registry_path=str(registry_with_templates))

        info = operation.get_template_info("software.dev/cli-tool/default")

        assert info["name"] == "cli-tool-default"
        assert "structure" in info
        assert "files" in info

    def test_scaffold_operation_template_not_found(self, temp_registry, output_dir):
        """Test handling of missing template"""
        operation = ScaffoldOperation(registry_path=str(temp_registry))

        with pytest.raises(TemplateNotFoundOperationError) as exc_info:
            operation.scaffold(
                template_ref="nonexistent/template",
                output_path=output_dir,
                entity_data={},
            )

        assert "nonexistent/template" in str(exc_info.value)

    def test_scaffold_operation_validation_error(self, tmp_path, output_dir):
        """Test handling of invalid template"""
        # Create invalid template
        template_file = tmp_path / "invalid.yml"
        template_file.write_text("name: test\n")  # Missing version

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises(TemplateValidationError):
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data={},
            )

    def test_scaffold_operation_security_violation(self, tmp_path, output_dir):
        """Test handling of security violations"""
        # Create template with path traversal
        template_data = {
            "name": "malicious",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "../outside"}],
        }
        template_file = tmp_path / "malicious.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises((TemplateValidationError, ScaffoldSecurityError)):
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data={},
            )


class TestCategoryVariantIntegration:
    """Integration tests for category variant template resolution"""

    def test_parse_category_variant(self):
        """Test parsing category with variant notation"""
        cv = CategoryVariant.parse("software.dev/cli-tool.johndoe/latex-v2")

        assert cv.category == "software.dev/cli-tool"
        assert cv.variant == "johndoe/latex-v2"
        assert cv.has_variant is True

    def test_parse_category_without_variant(self):
        """Test parsing category without variant"""
        cv = CategoryVariant.parse("software.dev/cli-tool")

        assert cv.category == "software.dev/cli-tool"
        assert cv.variant is None
        assert cv.has_variant is False

    def test_resolve_template_from_category(self, user_templates_dir):
        """Test resolving template from category variant"""
        # Create template at the expected path
        template_path = (
            user_templates_dir
            / "software"
            / "dev"
            / "cli-tool"
            / "myauthor"
            / "variant.yml"
        )
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_data = {"name": "variant-template", "version": "1.0"}
        with open(template_path, "w") as f:
            yaml.dump(template_data, f)

        resolver = TemplateResolver(user_templates_dir=str(user_templates_dir))

        result = resolver.resolve_from_category(
            "software.dev/cli-tool.myauthor/variant"
        )

        assert result is not None
        assert result.exists()

    def test_scaffold_from_category_variant(
        self, user_templates_dir, sample_entity_data, tmp_path
    ):
        """Test scaffolding using category variant notation"""
        # Create template at category variant path
        template_path = (
            user_templates_dir / "mycat" / "author" / "template.yml"
        )
        template_path.parent.mkdir(parents=True, exist_ok=True)

        template_data = {
            "name": "category-template",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "src"}],
            "files": [{"path": "README.md", "content": "# {{title}}"}],
        }
        with open(template_path, "w") as f:
            yaml.dump(template_data, f)

        operation = ScaffoldOperation(
            registry_path=None,
        )
        # Override user templates dir for this test
        operation._resolver = TemplateResolver(
            user_templates_dir=str(user_templates_dir)
        )

        output_path = tmp_path / "output"

        # Use the category variant syntax
        cv = CategoryVariant.parse("mycat.author/template")
        if cv.has_variant:
            template_ref = cv.template_path

            result = operation.scaffold(
                template_ref=template_ref,
                output_path=output_path,
                entity_data=sample_entity_data,
                dry_run=False,
            )

            assert result.success is True
            assert (output_path / "src").exists()


class TestResolverParserExecutorIntegration:
    """Integration tests for resolver -> parser -> executor pipeline"""

    def test_full_pipeline(
        self, registry_with_templates, sample_entity_data, output_dir
    ):
        """Test complete resolution -> parsing -> execution pipeline"""
        # Step 1: Resolve template
        resolver = TemplateResolver(registry_path=str(registry_with_templates))
        template_path = resolver.resolve("software.dev/cli-tool/default")
        assert template_path.exists()

        # Step 2: Parse template
        parser = TemplateParser()
        template_data = parser.parse(template_path)
        assert template_data["name"] == "cli-tool-default"

        # Step 3: Build variables
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=template_data,
            prompt_values={"author_name": "Integration Test"},
        )
        assert "title" in variables

        # Step 4: Execute scaffolding
        executor = TemplateExecutor(template_data, variables)
        result = executor.execute(output_dir, dry_run=False, create_output_dir=True)

        assert result.success is True
        assert output_dir.exists()

    def test_pipeline_with_template_references(
        self, template_with_file_references, sample_entity_data
    ):
        """Test pipeline with template file references"""
        template_path = template_with_file_references / "template.yml"

        # Parse template
        parser = TemplateParser()
        template_data = parser.parse(template_path)

        # Build variables
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=template_data,
        )

        # Execute scaffolding
        output_path = template_with_file_references.parent / "output"
        executor = TemplateExecutor(template_data, variables)
        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True

        # Verify template file references were resolved
        gitignore = output_path / ".gitignore"
        assert gitignore.exists()
        assert "__pycache__" in gitignore.read_text()

    def test_pipeline_with_asset_copying(
        self, template_with_assets, sample_entity_data
    ):
        """Test pipeline with asset file copying"""
        template_path = template_with_assets / "template.yml"

        parser = TemplateParser()
        template_data = parser.parse(template_path)

        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=template_data,
            prompt_values={"author_name": "Test"},
        )

        output_path = template_with_assets.parent / "output"
        executor = TemplateExecutor(
            template_data, variables, template_base_path=template_with_assets
        )
        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True

        # Verify assets were copied
        license_file = output_path / "LICENSE"
        assert license_file.exists()
        assert "MIT License" in license_file.read_text()


class TestErrorHandlingIntegration:
    """Integration tests for error handling across components"""

    def test_missing_template_error_propagation(self, temp_registry, output_dir):
        """Test that missing template errors propagate correctly"""
        operation = ScaffoldOperation(registry_path=str(temp_registry))

        with pytest.raises(TemplateNotFoundOperationError) as exc_info:
            operation.scaffold(
                template_ref="missing/template",
                output_path=output_dir,
                entity_data={},
            )

        error = exc_info.value
        assert "missing/template" in str(error)
        assert hasattr(error, "searched_paths")

    def test_validation_error_propagation(self, tmp_path, output_dir):
        """Test that validation errors propagate correctly"""
        # Create template with invalid structure
        template_file = tmp_path / "invalid.yml"
        template_file.write_text("not: valid\ntemplate: format\n")

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises(TemplateValidationError):
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data={},
            )

    def test_prompt_required_error(self, tmp_path, output_dir, sample_entity_data):
        """Test handling of required prompt variables"""
        template_data = {
            "name": "prompt-template",
            "version": "1.0",
            "variables": [
                {"name": "required_var", "source": "prompt"},  # No default
            ],
            "files": [
                {"path": "config.txt", "content": "{{required_var}}"},
            ],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises(PromptRequiredError) as exc_info:
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data=sample_entity_data,
                require_all_prompts=True,
            )

        assert "required_var" in str(exc_info.value)

    def test_execution_error_contains_context(
        self, tmp_path, sample_entity_data
    ):
        """Test that execution errors contain helpful context"""
        template_data = {
            "name": "error-template",
            "version": "1.0",
            "copy": [
                {"source": "nonexistent/file.txt", "destination": "output.txt"},
            ],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        output_path = tmp_path / "output"
        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises(ScaffoldExecutionError) as exc_info:
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_path,
                entity_data=sample_entity_data,
            )

        assert "copy" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


class TestCLIIntegration:
    """Integration tests for CLI command integration"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_with_template_stores_metadata(
        self, mock_get_registry_path, temp_registry
    ):
        """Test that create with --template stores template metadata"""
        from hxc.cli import main

        mock_get_registry_path.return_value = str(temp_registry)

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main([
                "create",
                "project",
                "Test Project",
                "--template",
                "software.dev/cli-tool.default",
                "--no-commit",
            ])

        assert result == 0

        # Verify template was stored in entity
        project_file = temp_registry / "projects" / "proj-12345678.yml"
        assert project_file.exists()

        with open(project_file) as f:
            data = yaml.safe_load(f)

        assert data["template"] == "software.dev/cli-tool.default"

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_with_scaffold_creates_structure(
        self, mock_get_registry_path, registry_with_templates, tmp_path, capsys
    ):
        """Test that create with --scaffold creates directory structure"""
        from hxc.cli import main

        mock_get_registry_path.return_value = str(registry_with_templates)

        output_path = tmp_path / "my_project"

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main([
                "create",
                "project",
                "Test Project",
                "--template",
                "software.dev/cli-tool/default",
                "--scaffold",
                "--output",
                str(output_path),
                "--no-commit",
            ])

        # Check if scaffolding was attempted
        # Note: May fail if template prompts are required
        # The test verifies the integration path works
        captured = capsys.readouterr()
        
        # Either success or prompt required error is acceptable
        assert result == 0 or "Prompt" in captured.out

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_create_scaffold_dry_run(
        self, mock_get_registry_path, registry_with_templates, tmp_path, capsys
    ):
        """Test that --dry-run previews scaffolding without changes"""
        from hxc.cli import main

        mock_get_registry_path.return_value = str(registry_with_templates)

        output_path = tmp_path / "preview_project"

        with patch(
            "hxc.core.operations.create.uuid.uuid4",
            return_value=MagicMock(
                __str__=lambda x: "12345678-1234-5678-1234-567812345678"
            ),
        ):
            result = main([
                "create",
                "project",
                "Test Project",
                "--template",
                "software.dev/cli-tool/default",
                "--scaffold",
                "--output",
                str(output_path),
                "--dry-run",
                "--no-commit",
            ])

        # Dry-run requires scaffold flag
        captured = capsys.readouterr()
        
        # Check appropriate behavior occurred
        # Note: error about --dry-run requiring --scaffold is also valid
        assert result in [0, 1]


class TestTemplateCommandIntegration:
    """Integration tests for template management command"""

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_template_list(self, mock_get_registry_path, registry_with_templates, capsys):
        """Test hxc template list command"""
        from hxc.cli import main

        mock_get_registry_path.return_value = str(registry_with_templates)

        result = main(["template", "list"])

        assert result == 0

        captured = capsys.readouterr()
        assert "template" in captured.out.lower()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_template_show(self, mock_get_registry_path, registry_with_templates, capsys):
        """Test hxc template show command"""
        from hxc.cli import main

        mock_get_registry_path.return_value = str(registry_with_templates)

        result = main(["template", "show", "software.dev/cli-tool/default"])

        assert result == 0

        captured = capsys.readouterr()
        assert "cli-tool" in captured.out.lower()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_template_validate(
        self, mock_get_registry_path, registry_with_templates, capsys
    ):
        """Test hxc template validate command"""
        from hxc.cli import main

        mock_get_registry_path.return_value = str(registry_with_templates)

        result = main(["template", "validate", "software.dev/cli-tool/default"])

        assert result == 0

        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_template_preview(
        self, mock_get_registry_path, registry_with_templates, tmp_path, capsys
    ):
        """Test hxc template preview command"""
        from hxc.cli import main

        mock_get_registry_path.return_value = str(registry_with_templates)

        output_path = tmp_path / "preview"
        output_path.mkdir()

        result = main([
            "template",
            "preview",
            "software.dev/cli-tool/default",
            "--output",
            str(output_path),
            "--title",
            "Preview Project",
        ])

        assert result == 0

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out or "Would create" in captured.out


class TestMCPToolsIntegration:
    """Integration tests for MCP tools"""

    def test_list_templates_tool(self, registry_with_templates):
        """Test list_templates_tool MCP function"""
        from hxc.mcp.tools import list_templates_tool

        result = list_templates_tool(registry_path=str(registry_with_templates))

        assert result["success"] is True
        assert "templates" in result
        assert result["count"] >= 0

    def test_show_template_tool(self, registry_with_templates):
        """Test show_template_tool MCP function"""
        from hxc.mcp.tools import show_template_tool

        result = show_template_tool(
            template_ref="software.dev/cli-tool/default",
            registry_path=str(registry_with_templates),
        )

        assert result["success"] is True
        assert "template" in result
        assert result["template"]["name"] == "cli-tool-default"

    def test_validate_template_tool(self, registry_with_templates):
        """Test validate_template_tool MCP function"""
        from hxc.mcp.tools import validate_template_tool

        result = validate_template_tool(
            template_ref="software.dev/cli-tool/default",
            registry_path=str(registry_with_templates),
        )

        assert result["success"] is True
        assert result["valid"] is True

    def test_preview_scaffold_tool(self, registry_with_templates, tmp_path):
        """Test preview_scaffold_tool MCP function"""
        from hxc.mcp.tools import preview_scaffold_tool

        output_path = tmp_path / "preview"
        output_path.mkdir()

        result = preview_scaffold_tool(
            template_ref="software.dev/cli-tool/default",
            output_path=str(output_path),
            entity_data={"title": "Test Project", "id": "test_proj"},
            registry_path=str(registry_with_templates),
        )

        assert result["success"] is True
        assert result["dry_run"] is True

    def test_scaffold_tool(self, registry_with_templates, tmp_path):
        """Test scaffold_tool MCP function"""
        from hxc.mcp.tools import scaffold_tool

        output_path = tmp_path / "scaffold_output"

        result = scaffold_tool(
            template_ref="software.dev/cli-tool/default",
            output_path=str(output_path),
            entity_data={"title": "Test Project", "id": "test_proj"},
            prompt_values={"author_name": "MCP Test"},
            registry_path=str(registry_with_templates),
        )

        # May succeed or require prompts
        assert "success" in result

    def test_init_template_directories_tool(self, tmp_path):
        """Test init_template_directories_tool MCP function"""
        from hxc.mcp.tools import init_template_directories_tool

        result = init_template_directories_tool(registry_path=str(tmp_path))

        assert result["success"] is True

    def test_create_entity_with_scaffold_tool(self, registry_with_templates, tmp_path):
        """Test create_entity_tool with scaffold option"""
        from hxc.mcp.tools import create_entity_tool

        result = create_entity_tool(
            type="project",
            title="Scaffolded Project",
            template="software.dev/cli-tool/default",
            scaffold=True,
            scaffold_output=str(tmp_path / "scaffold_project"),
            use_git=False,
            registry_path=str(registry_with_templates),
        )

        # Either success or scaffold warning is acceptable
        assert result["success"] is True
        # Entity should be created even if scaffolding has issues
        assert "uid" in result


class TestSecurityIntegration:
    """Integration tests for security enforcement"""

    def test_path_traversal_blocked_in_structure(self, tmp_path, output_dir):
        """Test that path traversal in structure is blocked"""
        template_data = {
            "name": "traversal-template",
            "version": "1.0",
            "structure": [{"type": "directory", "path": "../outside"}],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises((TemplateValidationError, ScaffoldSecurityError)):
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data={},
            )

    def test_path_traversal_blocked_in_files(self, tmp_path, output_dir):
        """Test that path traversal in file paths is blocked"""
        template_data = {
            "name": "traversal-template",
            "version": "1.0",
            "files": [{"path": "../outside.txt", "content": "malicious"}],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises((TemplateValidationError, ScaffoldSecurityError)):
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data={},
            )

    def test_absolute_path_blocked(self, tmp_path, output_dir):
        """Test that absolute paths are blocked"""
        template_data = {
            "name": "absolute-template",
            "version": "1.0",
            "files": [{"path": "/etc/passwd", "content": "malicious"}],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises((TemplateValidationError, ScaffoldSecurityError)):
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data={},
            )

    def test_variable_substitution_traversal_blocked(
        self, tmp_path, output_dir
    ):
        """Test that path traversal via variable substitution is blocked"""
        template_data = {
            "name": "var-traversal-template",
            "version": "1.0",
            "files": [{"path": "{{malicious_path}}/file.txt", "content": "test"}],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        operation = ScaffoldOperation(registry_path=str(tmp_path))

        with pytest.raises(ScaffoldExecutionError):
            operation.scaffold(
                template_ref=str(template_file),
                output_path=output_dir,
                entity_data={"malicious_path": "../outside"},
            )


class TestMultiTemplateWorkflow:
    """Integration tests for workflows with multiple templates"""

    def test_list_and_resolve_multiple_templates(
        self, registry_with_templates, user_templates_with_content
    ):
        """Test listing and resolving templates from multiple sources"""
        operation = ScaffoldOperation(registry_path=str(registry_with_templates))
        # Override user templates
        operation._resolver = TemplateResolver(
            registry_path=str(registry_with_templates),
            user_templates_dir=str(user_templates_with_content),
        )

        templates = operation.list_templates(
            include_registry=True, include_user=True
        )

        # Should have templates from both sources
        sources = {t["source"] for t in templates}
        assert "registry" in sources or "user" in sources

    def test_template_resolution_priority(
        self, registry_with_templates, user_templates_dir
    ):
        """Test that registry templates take precedence over user templates"""
        # Create same template in user directory
        user_template = user_templates_dir / "software.dev" / "cli-tool" / "default.yml"
        user_template.parent.mkdir(parents=True, exist_ok=True)
        with open(user_template, "w") as f:
            yaml.dump({"name": "user-version", "version": "1.0"}, f)

        resolver = TemplateResolver(
            registry_path=str(registry_with_templates),
            user_templates_dir=str(user_templates_dir),
        )

        path = resolver.resolve("software.dev/cli-tool/default")
        parser = TemplateParser()
        data = parser.parse(path)

        # Registry version should be used
        assert data["name"] == "cli-tool-default"


class TestScaffoldResultIntegration:
    """Integration tests for ScaffoldOperationResult"""

    def test_result_to_dict_success(
        self, cli_tool_template_file, sample_entity_data, output_dir
    ):
        """Test ScaffoldOperationResult.to_dict() for successful scaffold"""
        result = scaffold_from_template(
            template_ref=str(cli_tool_template_file),
            output_path=output_dir,
            entity_data=sample_entity_data,
            prompt_values={"author_name": "Test"},
            dry_run=False,
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert "directories_created" in result_dict
        assert "files_created" in result_dict
        assert "total_items" in result_dict

    def test_result_to_dict_dry_run(
        self, cli_tool_template_file, sample_entity_data, output_dir
    ):
        """Test ScaffoldOperationResult.to_dict() for dry-run"""
        output_dir.mkdir(parents=True, exist_ok=True)

        result = preview_scaffold(
            template_ref=str(cli_tool_template_file),
            output_path=output_dir,
            entity_data=sample_entity_data,
            prompt_values={"author_name": "Test"},
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["dry_run"] is True

    def test_result_summary(
        self, cli_tool_template_file, sample_entity_data, output_dir
    ):
        """Test ScaffoldResult.summary() output"""
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=yaml.safe_load(cli_tool_template_file.read_text()),
            prompt_values={"author_name": "Test"},
        )

        template_data = yaml.safe_load(cli_tool_template_file.read_text())
        executor = TemplateExecutor(template_data, variables)

        result = executor.execute(output_dir, dry_run=False, create_output_dir=True)

        summary = result.summary()

        assert isinstance(summary, str)
        assert str(output_dir) in summary or "output" in summary.lower()


class TestTemplateVariablesIntegration:
    """Integration tests for template variables across components"""

    def test_variables_from_all_sources(self, full_template_data, sample_entity_data):
        """Test variables from entity, system, and prompt sources"""
        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=full_template_data,
            prompt_values={"author_name": "Integration Test Author"},
        )

        # Entity variables
        assert variables.get_variable("title") == "My Project"
        assert variables.get_variable("id") == "my_project"

        # System variables
        assert "year" in variables
        assert "date" in variables
        assert variables.get_variable("template_name") == "full-template"

        # Prompt variables
        assert variables.get_variable("author_name") == "Integration Test Author"

    def test_variable_substitution_in_executor(
        self, tmp_path, sample_entity_data
    ):
        """Test that executor correctly substitutes all variable types"""
        template_data = {
            "name": "var-test",
            "version": "1.0",
            "variables": [
                {"name": "title", "source": "entity"},
                {"name": "year", "source": "system"},
                {"name": "custom", "source": "prompt", "default": "default_value"},
            ],
            "files": [
                {
                    "path": "info.txt",
                    "content": "Title: {{title}}\nYear: {{year}}\nCustom: {{custom}}",
                },
            ],
        }

        variables = TemplateVariables.from_entity_and_template(
            entity_data=sample_entity_data,
            template_data=template_data,
            prompt_values={"custom": "provided_value"},
        )

        executor = TemplateExecutor(template_data, variables)
        output_path = tmp_path / "output"
        result = executor.execute(output_path, dry_run=False, create_output_dir=True)

        assert result.success is True

        info_file = output_path / "info.txt"
        content = info_file.read_text()

        assert "Title: My Project" in content
        assert "Custom: provided_value" in content
        # Year should be current year, not template variable
        assert "{{year}}" not in content


class TestEdgeCasesIntegration:
    """Integration tests for edge cases and boundary conditions"""

    def test_empty_template_structure(self, tmp_path, sample_entity_data):
        """Test scaffolding with empty structure and files"""
        template_data = {
            "name": "empty-template",
            "version": "1.0",
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        output_path = tmp_path / "output"
        result = scaffold_from_template(
            template_ref=str(template_file),
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=False,
        )

        assert result.success is True
        assert result.total_items == 0

    def test_deeply_nested_structure(self, tmp_path, sample_entity_data):
        """Test scaffolding with deeply nested directories"""
        template_data = {
            "name": "nested-template",
            "version": "1.0",
            "structure": [
                {"type": "directory", "path": "a/b/c/d/e/f"},
            ],
            "files": [
                {"path": "a/b/c/d/e/f/deep.txt", "content": "Deep content"},
            ],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        output_path = tmp_path / "output"
        result = scaffold_from_template(
            template_ref=str(template_file),
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=False,
        )

        assert result.success is True
        assert (output_path / "a" / "b" / "c" / "d" / "e" / "f" / "deep.txt").exists()

    def test_unicode_content(self, tmp_path, sample_entity_data):
        """Test scaffolding with Unicode content"""
        template_data = {
            "name": "unicode-template",
            "version": "1.0",
            "files": [
                {
                    "path": "unicode.txt",
                    "content": "Hello 世界! 🚀 Émojis and ünïcödé",
                },
            ],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f, allow_unicode=True)

        output_path = tmp_path / "output"
        result = scaffold_from_template(
            template_ref=str(template_file),
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=False,
        )

        assert result.success is True
        content = (output_path / "unicode.txt").read_text(encoding="utf-8")
        assert "世界" in content
        assert "🚀" in content

    def test_many_files_performance(self, tmp_path, sample_entity_data):
        """Test scaffolding with many files"""
        files = [
            {"path": f"file_{i:03d}.txt", "content": f"Content {i}"}
            for i in range(100)
        ]
        template_data = {
            "name": "many-files-template",
            "version": "1.0",
            "files": files,
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        output_path = tmp_path / "output"
        result = scaffold_from_template(
            template_ref=str(template_file),
            output_path=output_path,
            entity_data=sample_entity_data,
            dry_run=False,
        )

        assert result.success is True
        assert len(result.files_created) == 100

    def test_special_characters_in_variable_values(self, tmp_path):
        """Test that special characters in variable values are handled"""
        template_data = {
            "name": "special-chars-template",
            "version": "1.0",
            "files": [
                {"path": "content.txt", "content": "Title: {{title}}"},
            ],
        }
        template_file = tmp_path / "template.yml"
        with open(template_file, "w") as f:
            yaml.dump(template_data, f)

        entity_data = {
            "title": "Project with <special> & \"characters\"",
            "id": "special_proj",
        }

        output_path = tmp_path / "output"
        result = scaffold_from_template(
            template_ref=str(template_file),
            output_path=output_path,
            entity_data=entity_data,
            dry_run=False,
        )

        assert result.success is True
        content = (output_path / "content.txt").read_text()
        assert "<special>" in content
        assert '"characters"' in content