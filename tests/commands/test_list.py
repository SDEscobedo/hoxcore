"""
Tests for the list command
"""
import os
import yaml
import pathlib
import datetime
import shutil
import pytest
from unittest.mock import patch, MagicMock

from hxc.cli import main
from hxc.commands.cmd_list import ListCommand
from hxc.commands.registry import RegistryCommand
from hxc.core.operations.list import ListOperation
from hxc.core.enums import EntityType, EntityStatus, SortField, OutputFormat


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary registry for testing"""
    # Create directory structure
    registry_path = tmp_path / "test_registry"
    registry_path.mkdir(parents=True)
    
    # Create marker files and directories
    (registry_path / ".hxc").mkdir()
    (registry_path / "config.yml").write_text("# Test config")
    
    # Create entity directories
    projects_dir = registry_path / "projects"
    programs_dir = registry_path / "programs"
    missions_dir = registry_path / "missions"
    actions_dir = registry_path / "actions"
    
    projects_dir.mkdir()
    programs_dir.mkdir()
    missions_dir.mkdir()
    actions_dir.mkdir()
    
    # Create sample items
    # Projects
    create_sample_project(projects_dir, "proj-001", "Test Project 1", "P-001", "active")
    create_sample_project(projects_dir, "proj-002", "Test Project 2", "P-002", "completed", 
                         tags=["test", "important"], category="software.dev/cli-tool")
    create_sample_project(projects_dir, "proj-003", "Test Project 3", "P-003", "on-hold", 
                         due_date="2024-12-31", parent="P-002")
    
    # Programs
    create_sample_item(programs_dir, "prog-001", "program", "Test Program 1", "PG-001", "active")
    create_sample_item(programs_dir, "prog-002", "program", "Test Program 2", "PG-002", "planned")
    
    # Missions
    create_sample_item(missions_dir, "miss-001", "mission", "Test Mission 1", "M-001", "active")
    
    # Actions
    create_sample_item(actions_dir, "act-001", "action", "Test Action 1", "A-001", "active")
    create_sample_item(actions_dir, "act-002", "action", "Test Action 2", "A-002", "completed")
    
    yield registry_path
    
    # Clean up
    if registry_path.exists():
        shutil.rmtree(registry_path)


def create_sample_project(directory, filename, title, item_id, status, **kwargs):
    """Create a sample project file"""
    project_data = {
        "type": "project",
        "title": title,
        "id": item_id,
        "uid": filename.split("-")[1],
        "status": status,
        "description": f"Description for {title}",
    }
    
    # Add optional fields
    if "tags" in kwargs:
        project_data["tags"] = kwargs["tags"]
    if "category" in kwargs:
        project_data["category"] = kwargs["category"]
    if "due_date" in kwargs:
        project_data["due_date"] = kwargs["due_date"]
    if "parent" in kwargs:
        project_data["parent"] = kwargs["parent"]
    
    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(project_data, f)


def create_sample_item(directory, filename, item_type, title, item_id, status):
    """Create a sample item file"""
    item_data = {
        "type": item_type,
        "title": title,
        "id": item_id,
        "uid": filename.split("-")[1],
        "status": status,
        "description": f"Description for {title}",
    }
    
    filepath = directory / f"{filename}.yml"
    with open(filepath, "w") as f:
        yaml.dump(item_data, f)


def test_list_command_registration():
    """Test that the list command is properly registered"""
    from hxc.commands import get_available_commands
    
    available_commands = get_available_commands()
    assert "list" in available_commands


def test_list_command_parser():
    """Test list command parser registration"""
    from argparse import ArgumentParser
    
    parser = ArgumentParser()
    subparsers = parser.add_subparsers()
    
    cmd_parser = ListCommand.register_subparser(subparsers)
    
    # Verify parser has the expected arguments
    actions = {action.dest for action in cmd_parser._actions}
    assert "type" in actions
    assert "status" in actions
    assert "tags" in actions
    assert "category" in actions
    assert "parent" in actions
    assert "id" in actions
    assert "query" in actions
    assert "before" in actions
    assert "after" in actions
    assert "max" in actions
    assert "sort" in actions
    assert "desc" in actions
    assert "format" in actions


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_projects_basic(mock_get_registry_path, temp_registry):
    """Test basic listing of projects"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project"])
        
        # Check result
        assert result == 0
        
        # Check that output included all projects
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 1" in output
        assert "Test Project 2" in output
        assert "Test Project 3" in output
        assert "active" in output
        assert "completed" in output
        assert "on-hold" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_all_items(mock_get_registry_path, temp_registry):
    """Test listing all items"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "all"])
        
        # Check result
        assert result == 0
        
        # Check that output included items from all types
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project" in output
        assert "Test Program" in output
        assert "Test Mission" in output
        assert "Test Action" in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_status(mock_get_registry_path, temp_registry):
    """Test filtering items by status"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--status", "completed"])
        
        # Check result
        assert result == 0
        
        # Check that output included only completed projects
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_tag(mock_get_registry_path, temp_registry):
    """Test filtering items by tag"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--tag", "important"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects with the tag
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_category(mock_get_registry_path, temp_registry):
    """Test filtering items by category"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--category", "software.dev/cli-tool"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects with the category
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_parent(mock_get_registry_path, temp_registry):
    """Test filtering items by parent"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--parent", "P-002"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects with the parent
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 3" in output
        assert "Test Project 1" not in output
        assert "Test Project 2" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_id(mock_get_registry_path, temp_registry):
    """Test filtering items by ID"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--id", "P-001"])
        
        # Check result
        assert result == 0
        
        # Check that output included only the project with the ID
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 1" in output
        assert "Test Project 2" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_filter_by_query(mock_get_registry_path, temp_registry):
    """Test filtering items by text query"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--query", "Project 2"])
        
        # Check result
        assert result == 0
        
        # Check that output included only projects matching the query
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "Test Project 2" in output
        assert "Test Project 1" not in output
        assert "Test Project 3" not in output


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_max_items(mock_get_registry_path, temp_registry):
    """Test limiting the number of items"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--max", "2"])
        
        # Check result
        assert result == 0
        
        # Count the number of projects in the output
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        # Count project lines (excluding header and separator)
        project_lines = 0
        for line in output_calls:
            if "Project" in line and "TYPE" not in line:
                project_lines += 1
        
        assert project_lines == 2


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_sort_order(mock_get_registry_path, temp_registry):
    """Test sorting items"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    with patch("builtins.print") as mock_print:
        # Test ascending sort by title (default)
        result = main(["list", "project", "--sort", "title"])
        
        # Check result
        assert result == 0
        
        # Get the output lines
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        project_lines = [line for line in output_calls if "Project" in line and "TYPE" not in line]
        
        # Check that projects are sorted by title
        assert "Test Project 1" in project_lines[0]
        assert "Test Project 2" in project_lines[1]
        assert "Test Project 3" in project_lines[2]
        
        # Clear the mock for the next test
        mock_print.reset_mock()
        
        # Test descending sort by title
        result = main(["list", "project", "--sort", "title", "--desc"])
        
        # Check result
        assert result == 0
        
        # Get the output lines
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        project_lines = [line for line in output_calls if "Project" in line and "TYPE" not in line]
        
        # Check that projects are sorted by title in descending order
        assert "Test Project 3" in project_lines[0]
        assert "Test Project 2" in project_lines[1]
        assert "Test Project 1" in project_lines[2]


@patch("hxc.commands.registry.RegistryCommand.get_registry_path")
def test_list_output_formats(mock_get_registry_path, temp_registry):
    """Test different output formats"""
    # Configure mock to return the temp registry
    mock_get_registry_path.return_value = str(temp_registry)
    
    # Test yaml format
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--format", "yaml", "--id", "P-001"])
        
        # Check result
        assert result == 0
        
        # Check that output is in YAML format
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert "title: Test Project 1" in output
        assert "type: project" in output
        assert "id: P-001" in output
    
    # Test json format
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--format", "json", "--id", "P-001"])
        
        # Check result
        assert result == 0
        
        # Check that output is in JSON format
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        output = "\n".join(output_calls)
        
        assert '"title": "Test Project 1"' in output
        assert '"type": "project"' in output
        assert '"id": "P-001"' in output
    
    # Test id format
    with patch("builtins.print") as mock_print:
        result = main(["list", "project", "--format", "id"])
        
        # Check result
        assert result == 0
        
        # Check that output contains only IDs
        output_calls = [call[0][0] for call in mock_print.call_args_list]
        
        assert "P-001" in output_calls
        assert "P-002" in output_calls
        assert "P-003" in output_calls
        assert "Test Project" not in "\n".join(output_calls)


@patch("hxc.commands.registry.RegistryCommand.get_registry_path", return_value=None)
@patch("hxc.commands.cmd_list.ListCommand._get_registry_path", return_value=None)
def test_list_no_registry(mock_get_project_root, mock_get_registry_path):
    """Test listing with no registry found"""
    with patch("builtins.print") as mock_print:
        result = main(["list", "project"])
        
        # Check result indicates failure
        assert result == 1
        
        # Check error message
        mock_print.assert_called_once()
        assert "No registry found" in mock_print.call_args[0][0]


class TestListCommandUsesSharedOperation:
    """Tests to verify CLI uses the shared ListOperation"""
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_cli_uses_list_operation(self, mock_get_registry_path, temp_registry):
        """Test that CLI command uses ListOperation internally"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("hxc.commands.cmd_list.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.return_value = {
                "success": True,
                "entities": [],
                "count": 0,
                "filters": {},
                "sort": {"field": "title", "descending": False},
            }
            MockOperation.return_value = mock_instance
            
            with patch("builtins.print"):
                result = main(["list", "project"])
            
            MockOperation.assert_called_once_with(str(temp_registry))
            mock_instance.list_entities.assert_called_once()
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_cli_passes_all_filters_to_operation(self, mock_get_registry_path, temp_registry):
        """Test that CLI passes all filter parameters to ListOperation"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("hxc.commands.cmd_list.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.return_value = {
                "success": True,
                "entities": [],
                "count": 0,
                "filters": {},
                "sort": {"field": "title", "descending": False},
            }
            MockOperation.return_value = mock_instance
            
            with patch("builtins.print"):
                result = main([
                    "list", "project",
                    "--status", "active",
                    "--tag", "test",
                    "--category", "software",
                    "--parent", "P-000",
                    "--id", "P-001",
                    "--query", "search term",
                    "--before", "2024-12-31",
                    "--after", "2024-01-01",
                    "--sort", "due_date",
                    "--desc",
                    "--max", "10",
                ])
            
            # Verify the call arguments
            call_kwargs = mock_instance.list_entities.call_args[1]
            assert call_kwargs["status"] == EntityStatus.ACTIVE
            assert call_kwargs["tags"] == ["test"]
            assert call_kwargs["category"] == "software"
            assert call_kwargs["parent"] == "P-000"
            assert call_kwargs["identifier"] == "P-001"
            assert call_kwargs["query"] == "search term"
            assert call_kwargs["due_before"] == "2024-12-31"
            assert call_kwargs["due_after"] == "2024-01-01"
            assert call_kwargs["sort_field"] == SortField.DUE_DATE
            assert call_kwargs["descending"] is True
            assert call_kwargs["max_items"] == 10
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_cli_handles_operation_error(self, mock_get_registry_path, temp_registry):
        """Test that CLI handles ListOperation errors gracefully"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("hxc.commands.cmd_list.ListOperation") as MockOperation:
            mock_instance = MagicMock()
            mock_instance.list_entities.return_value = {
                "success": False,
                "error": "Test error message",
            }
            MockOperation.return_value = mock_instance
            
            with patch("builtins.print") as mock_print:
                result = main(["list", "project"])
            
            assert result == 1
            output = mock_print.call_args[0][0]
            assert "Error listing items" in output


class TestListCommandDateFilters:
    """Tests for date range filters in list command"""
    
    @pytest.fixture
    def temp_registry_with_dates(self, tmp_path):
        """Create a registry with entities having various due dates"""
        registry_path = tmp_path / "date_registry"
        registry_path.mkdir(parents=True)
        
        (registry_path / ".hxc").mkdir()
        (registry_path / "config.yml").write_text("# Test config")
        
        projects_dir = registry_path / "projects"
        projects_dir.mkdir()
        (registry_path / "programs").mkdir()
        (registry_path / "missions").mkdir()
        (registry_path / "actions").mkdir()
        
        # Create projects with different due dates
        create_sample_project(projects_dir, "proj-early", "Early Project", "P-EARLY", "active",
                             due_date="2024-03-15")
        create_sample_project(projects_dir, "proj-mid", "Mid Project", "P-MID", "active",
                             due_date="2024-06-30")
        create_sample_project(projects_dir, "proj-late", "Late Project", "P-LATE", "active",
                             due_date="2024-12-31")
        create_sample_project(projects_dir, "proj-nodate", "No Date Project", "P-NODATE", "active")
        
        yield registry_path
        
        if registry_path.exists():
            shutil.rmtree(registry_path)
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_filter_before_date(self, mock_get_registry_path, temp_registry_with_dates):
        """Test filtering by due date before a specific date"""
        mock_get_registry_path.return_value = str(temp_registry_with_dates)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--before", "2024-07-01"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            assert "Early Project" in output
            assert "Mid Project" in output
            assert "Late Project" not in output
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_filter_after_date(self, mock_get_registry_path, temp_registry_with_dates):
        """Test filtering by due date after a specific date"""
        mock_get_registry_path.return_value = str(temp_registry_with_dates)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--after", "2024-07-01"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            assert "Early Project" not in output
            assert "Mid Project" not in output
            assert "Late Project" in output
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_filter_date_range(self, mock_get_registry_path, temp_registry_with_dates):
        """Test filtering by date range"""
        mock_get_registry_path.return_value = str(temp_registry_with_dates)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--after", "2024-04-01", "--before", "2024-10-01"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            assert "Early Project" not in output
            assert "Mid Project" in output
            assert "Late Project" not in output


class TestListCommandQueryFilter:
    """Tests for query filter in list command"""
    
    @pytest.fixture
    def temp_registry_with_descriptions(self, tmp_path):
        """Create a registry with entities having various descriptions"""
        registry_path = tmp_path / "query_registry"
        registry_path.mkdir(parents=True)
        
        (registry_path / ".hxc").mkdir()
        (registry_path / "config.yml").write_text("# Test config")
        
        projects_dir = registry_path / "projects"
        projects_dir.mkdir()
        (registry_path / "programs").mkdir()
        (registry_path / "missions").mkdir()
        (registry_path / "actions").mkdir()
        
        # Create projects with specific content for searching
        project1 = {
            "type": "project",
            "title": "API Development",
            "id": "P-API",
            "uid": "apidev",
            "status": "active",
            "description": "Building REST endpoints for the application",
        }
        (projects_dir / "proj-apidev.yml").write_text(yaml.dump(project1))
        
        project2 = {
            "type": "project",
            "title": "Frontend Work",
            "id": "P-FE",
            "uid": "frontend",
            "status": "active",
            "description": "React components and styling",
        }
        (projects_dir / "proj-frontend.yml").write_text(yaml.dump(project2))
        
        project3 = {
            "type": "project",
            "title": "Database Migration",
            "id": "P-DB",
            "uid": "dbmigr",
            "status": "active",
            "description": "Migrating the REST API database",
        }
        (projects_dir / "proj-dbmigr.yml").write_text(yaml.dump(project3))
        
        yield registry_path
        
        if registry_path.exists():
            shutil.rmtree(registry_path)
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_query_matches_title(self, mock_get_registry_path, temp_registry_with_descriptions):
        """Test query filter matches in title"""
        mock_get_registry_path.return_value = str(temp_registry_with_descriptions)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--query", "API"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            assert "API Development" in output
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_query_matches_description(self, mock_get_registry_path, temp_registry_with_descriptions):
        """Test query filter matches in description"""
        mock_get_registry_path.return_value = str(temp_registry_with_descriptions)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--query", "React"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            assert "Frontend Work" in output
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_query_case_insensitive(self, mock_get_registry_path, temp_registry_with_descriptions):
        """Test query filter is case insensitive"""
        mock_get_registry_path.return_value = str(temp_registry_with_descriptions)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--query", "rest"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            # Should find both "REST endpoints" and "REST API database"
            assert "API Development" in output
            assert "Database Migration" in output


class TestListCommandMultipleTags:
    """Tests for multiple tag filters in list command"""
    
    @pytest.fixture
    def temp_registry_with_tags(self, tmp_path):
        """Create a registry with entities having multiple tags"""
        registry_path = tmp_path / "tag_registry"
        registry_path.mkdir(parents=True)
        
        (registry_path / ".hxc").mkdir()
        (registry_path / "config.yml").write_text("# Test config")
        
        projects_dir = registry_path / "projects"
        projects_dir.mkdir()
        (registry_path / "programs").mkdir()
        (registry_path / "missions").mkdir()
        (registry_path / "actions").mkdir()
        
        # Create projects with different tag combinations
        create_sample_project(projects_dir, "proj-ab", "Project AB", "P-AB", "active",
                             tags=["alpha", "beta"])
        create_sample_project(projects_dir, "proj-ac", "Project AC", "P-AC", "active",
                             tags=["alpha", "gamma"])
        create_sample_project(projects_dir, "proj-bc", "Project BC", "P-BC", "active",
                             tags=["beta", "gamma"])
        create_sample_project(projects_dir, "proj-abc", "Project ABC", "P-ABC", "active",
                             tags=["alpha", "beta", "gamma"])
        
        yield registry_path
        
        if registry_path.exists():
            shutil.rmtree(registry_path)
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_multiple_tags_and_logic(self, mock_get_registry_path, temp_registry_with_tags):
        """Test filtering by multiple tags with AND logic"""
        mock_get_registry_path.return_value = str(temp_registry_with_tags)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--tag", "alpha", "--tag", "beta"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            # Should match projects with both alpha AND beta
            assert "Project AB" in output
            assert "Project ABC" in output
            assert "Project AC" not in output
            assert "Project BC" not in output


class TestListCommandSortByFileMetadata:
    """Tests for sorting by file metadata (created/modified)"""
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_sort_by_created(self, mock_get_registry_path, temp_registry):
        """Test sorting by created date"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--sort", "created"])
            
            # Should not raise
            assert result == 0
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_list_sort_by_modified(self, mock_get_registry_path, temp_registry):
        """Test sorting by modified date"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--sort", "modified"])
            
            # Should not raise
            assert result == 0


class TestListCommandBehavioralParityWithMCP:
    """Tests to verify CLI and MCP produce identical results"""
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_cli_and_operation_produce_same_filter_results(self, mock_get_registry_path, temp_registry):
        """Test that CLI filters produce same results as direct ListOperation"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        # Get results via direct operation
        operation = ListOperation(str(temp_registry))
        operation_result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            status=EntityStatus.COMPLETED,
            include_file_metadata=True,
        )
        
        # Get results via CLI (capture what it would display)
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--status", "completed", "--format", "id"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            cli_ids = set(output_calls)
        
        # Compare
        operation_ids = {e["id"] for e in operation_result["entities"]}
        assert cli_ids == operation_ids
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_cli_and_operation_produce_same_sort_order(self, mock_get_registry_path, temp_registry):
        """Test that CLI sorting produces same order as direct ListOperation"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        # Get results via direct operation
        operation = ListOperation(str(temp_registry))
        operation_result = operation.list_entities(
            entity_types=[EntityType.PROJECT],
            sort_field=SortField.TITLE,
            descending=True,
            include_file_metadata=True,
        )
        
        # Get results via CLI
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--sort", "title", "--desc", "--format", "id"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            cli_ids = output_calls
        
        # Compare order
        operation_ids = [e["id"] for e in operation_result["entities"]]
        assert cli_ids == operation_ids


class TestListCommandOutputFormats:
    """Additional tests for output format handling"""
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_yaml_output_excludes_file_metadata(self, mock_get_registry_path, temp_registry):
        """Test that YAML output excludes internal _file metadata"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--format", "yaml", "--id", "P-001"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            # Should not contain _file metadata
            assert "_file:" not in output
            assert "path:" not in output or "P-001" not in output
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_json_output_excludes_file_metadata(self, mock_get_registry_path, temp_registry):
        """Test that JSON output excludes internal _file metadata"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--format", "json", "--id", "P-001"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            # Should not contain _file metadata
            assert '"_file"' not in output
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_pretty_format_uses_table(self, mock_get_registry_path, temp_registry):
        """Test that pretty format uses table display"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--format", "pretty"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            # Should have table header
            assert "TYPE" in output
            assert "ID" in output
            assert "TITLE" in output
            assert "STATUS" in output


class TestListCommandInvalidInputs:
    """Tests for invalid input handling"""
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_invalid_entity_type(self, mock_get_registry_path, temp_registry):
        """Test handling of invalid entity type"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        # Invalid type should be rejected by argparse
        with pytest.raises(SystemExit):
            main(["list", "invalid_type"])
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_invalid_status(self, mock_get_registry_path, temp_registry):
        """Test handling of invalid status"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        # Invalid status should be rejected by argparse
        with pytest.raises(SystemExit):
            main(["list", "project", "--status", "invalid_status"])
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_invalid_sort_field(self, mock_get_registry_path, temp_registry):
        """Test handling of invalid sort field"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        # Invalid sort field should be rejected by argparse
        with pytest.raises(SystemExit):
            main(["list", "project", "--sort", "invalid_field"])
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_invalid_format(self, mock_get_registry_path, temp_registry):
        """Test handling of invalid output format"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        # Invalid format should be rejected by argparse
        with pytest.raises(SystemExit):
            main(["list", "project", "--format", "invalid_format"])


class TestListCommandEmptyResults:
    """Tests for empty result handling"""
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_no_matching_items_message(self, mock_get_registry_path, temp_registry):
        """Test message when no items match filters"""
        mock_get_registry_path.return_value = str(temp_registry)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project", "--status", "cancelled"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            assert "No items found" in output
    
    @patch("hxc.commands.registry.RegistryCommand.get_registry_path")
    def test_empty_registry(self, mock_get_registry_path, tmp_path):
        """Test listing from an empty registry"""
        # Create empty registry
        registry_path = tmp_path / "empty_registry"
        registry_path.mkdir(parents=True)
        (registry_path / ".hxc").mkdir()
        (registry_path / "config.yml").write_text("# Test config")
        (registry_path / "projects").mkdir()
        (registry_path / "programs").mkdir()
        (registry_path / "missions").mkdir()
        (registry_path / "actions").mkdir()
        
        mock_get_registry_path.return_value = str(registry_path)
        
        with patch("builtins.print") as mock_print:
            result = main(["list", "project"])
            
            assert result == 0
            
            output_calls = [call[0][0] for call in mock_print.call_args_list]
            output = "\n".join(output_calls)
            
            assert "No items found" in output