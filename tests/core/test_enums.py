"""
Tests for core enumerations
"""

import pytest

from hxc.core.enums import EntityStatus, EntityType, OutputFormat, SortField


class TestEntityType:
    """Tests for EntityType enum"""

    def test_entity_type_values(self):
        """Test that all entity types have correct values"""
        assert EntityType.PROGRAM.value == "program"
        assert EntityType.PROJECT.value == "project"
        assert EntityType.MISSION.value == "mission"
        assert EntityType.ACTION.value == "action"

    def test_entity_type_values_list(self):
        """Test that values() returns all entity type values"""
        values = EntityType.values()
        assert len(values) == 4
        assert "program" in values
        assert "project" in values
        assert "mission" in values
        assert "action" in values

    def test_entity_type_from_string_valid(self):
        """Test converting valid strings to EntityType"""
        assert EntityType.from_string("program") == EntityType.PROGRAM
        assert EntityType.from_string("project") == EntityType.PROJECT
        assert EntityType.from_string("mission") == EntityType.MISSION
        assert EntityType.from_string("action") == EntityType.ACTION

    def test_entity_type_from_string_case_insensitive(self):
        """Test that from_string is case insensitive"""
        assert EntityType.from_string("PROGRAM") == EntityType.PROGRAM
        assert EntityType.from_string("Project") == EntityType.PROJECT
        assert EntityType.from_string("MiSsIoN") == EntityType.MISSION

    def test_entity_type_from_string_invalid(self):
        """Test that invalid strings raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            EntityType.from_string("invalid")

        assert "Invalid entity type 'invalid'" in str(exc_info.value)
        assert "program" in str(exc_info.value)
        assert "project" in str(exc_info.value)

    def test_entity_type_get_folder_name(self):
        """Test getting folder names for entity types"""
        assert EntityType.PROGRAM.get_folder_name() == "programs"
        assert EntityType.PROJECT.get_folder_name() == "projects"
        assert EntityType.MISSION.get_folder_name() == "missions"
        assert EntityType.ACTION.get_folder_name() == "actions"

    def test_entity_type_get_file_prefix(self):
        """Test getting file prefixes for entity types"""
        assert EntityType.PROGRAM.get_file_prefix() == "prog"
        assert EntityType.PROJECT.get_file_prefix() == "proj"
        assert EntityType.MISSION.get_file_prefix() == "miss"
        assert EntityType.ACTION.get_file_prefix() == "act"


class TestEntityStatus:
    """Tests for EntityStatus enum"""

    def test_entity_status_values(self):
        """Test that all status values are correct"""
        assert EntityStatus.ACTIVE.value == "active"
        assert EntityStatus.COMPLETED.value == "completed"
        assert EntityStatus.ON_HOLD.value == "on-hold"
        assert EntityStatus.CANCELLED.value == "cancelled"
        assert EntityStatus.PLANNED.value == "planned"

    def test_entity_status_values_list(self):
        """Test that values() returns all status values"""
        values = EntityStatus.values()
        assert len(values) == 5
        assert "active" in values
        assert "completed" in values
        assert "on-hold" in values
        assert "cancelled" in values
        assert "planned" in values

    def test_entity_status_from_string_valid(self):
        """Test converting valid strings to EntityStatus"""
        assert EntityStatus.from_string("active") == EntityStatus.ACTIVE
        assert EntityStatus.from_string("completed") == EntityStatus.COMPLETED
        assert EntityStatus.from_string("on-hold") == EntityStatus.ON_HOLD
        assert EntityStatus.from_string("cancelled") == EntityStatus.CANCELLED
        assert EntityStatus.from_string("planned") == EntityStatus.PLANNED

    def test_entity_status_from_string_case_insensitive(self):
        """Test that from_string is case insensitive"""
        assert EntityStatus.from_string("ACTIVE") == EntityStatus.ACTIVE
        assert EntityStatus.from_string("Completed") == EntityStatus.COMPLETED
        assert EntityStatus.from_string("ON-HOLD") == EntityStatus.ON_HOLD

    def test_entity_status_from_string_invalid(self):
        """Test that invalid strings raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            EntityStatus.from_string("invalid")

        assert "Invalid status 'invalid'" in str(exc_info.value)
        assert "active" in str(exc_info.value)
        assert "completed" in str(exc_info.value)


class TestOutputFormat:
    """Tests for OutputFormat enum"""

    def test_output_format_values(self):
        """Test that all output format values are correct"""
        assert OutputFormat.TABLE.value == "table"
        assert OutputFormat.YAML.value == "yaml"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.ID.value == "id"
        assert OutputFormat.PRETTY.value == "pretty"

    def test_output_format_values_list(self):
        """Test that values() returns all output format values"""
        values = OutputFormat.values()
        assert len(values) == 5
        assert "table" in values
        assert "yaml" in values
        assert "json" in values
        assert "id" in values
        assert "pretty" in values

    def test_output_format_from_string_valid(self):
        """Test converting valid strings to OutputFormat"""
        assert OutputFormat.from_string("table") == OutputFormat.TABLE
        assert OutputFormat.from_string("yaml") == OutputFormat.YAML
        assert OutputFormat.from_string("json") == OutputFormat.JSON
        assert OutputFormat.from_string("id") == OutputFormat.ID
        assert OutputFormat.from_string("pretty") == OutputFormat.PRETTY

    def test_output_format_from_string_case_insensitive(self):
        """Test that from_string is case insensitive"""
        assert OutputFormat.from_string("TABLE") == OutputFormat.TABLE
        assert OutputFormat.from_string("Yaml") == OutputFormat.YAML
        assert OutputFormat.from_string("JSON") == OutputFormat.JSON

    def test_output_format_from_string_invalid(self):
        """Test that invalid strings raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            OutputFormat.from_string("invalid")

        assert "Invalid output format 'invalid'" in str(exc_info.value)
        assert "table" in str(exc_info.value)
        assert "yaml" in str(exc_info.value)


class TestSortField:
    """Tests for SortField enum"""

    def test_sort_field_values(self):
        """Test that all sort field values are correct"""
        assert SortField.TITLE.value == "title"
        assert SortField.ID.value == "id"
        assert SortField.DUE_DATE.value == "due_date"
        assert SortField.STATUS.value == "status"
        assert SortField.CREATED.value == "created"
        assert SortField.MODIFIED.value == "modified"

    def test_sort_field_values_list(self):
        """Test that values() returns all sort field values"""
        values = SortField.values()
        assert len(values) == 6
        assert "title" in values
        assert "id" in values
        assert "due_date" in values
        assert "status" in values
        assert "created" in values
        assert "modified" in values

    def test_sort_field_from_string_valid(self):
        """Test converting valid strings to SortField"""
        assert SortField.from_string("title") == SortField.TITLE
        assert SortField.from_string("id") == SortField.ID
        assert SortField.from_string("due_date") == SortField.DUE_DATE
        assert SortField.from_string("status") == SortField.STATUS
        assert SortField.from_string("created") == SortField.CREATED
        assert SortField.from_string("modified") == SortField.MODIFIED

    def test_sort_field_from_string_case_insensitive(self):
        """Test that from_string is case insensitive"""
        assert SortField.from_string("TITLE") == SortField.TITLE
        assert SortField.from_string("Id") == SortField.ID
        assert SortField.from_string("DUE_DATE") == SortField.DUE_DATE

    def test_sort_field_from_string_invalid(self):
        """Test that invalid strings raise ValueError"""
        with pytest.raises(ValueError) as exc_info:
            SortField.from_string("invalid")

        assert "Invalid sort field 'invalid'" in str(exc_info.value)
        assert "title" in str(exc_info.value)
        assert "id" in str(exc_info.value)


class TestEnumIntegration:
    """Integration tests for enum usage"""

    def test_entity_type_folder_and_prefix_consistency(self):
        """Test that folder names and prefixes are consistent across all entity types"""
        for entity_type in EntityType:
            folder = entity_type.get_folder_name()
            prefix = entity_type.get_file_prefix()

            # Folder should be plural form
            assert folder.endswith("s")

            # Prefix should be short form
            assert len(prefix) <= 4

            # Both should be lowercase
            assert folder == folder.lower()
            assert prefix == prefix.lower()

    def test_all_enums_have_values_method(self):
        """Test that all enum classes have a values() class method"""
        enums = [EntityType, EntityStatus, OutputFormat, SortField]

        for enum_class in enums:
            assert hasattr(enum_class, "values")
            assert callable(enum_class.values)

            values = enum_class.values()
            assert isinstance(values, list)
            assert len(values) > 0

    def test_all_enums_have_from_string_method(self):
        """Test that all enum classes have a from_string() class method"""
        enums = [EntityType, EntityStatus, OutputFormat, SortField]

        for enum_class in enums:
            assert hasattr(enum_class, "from_string")
            assert callable(enum_class.from_string)

    def test_enum_values_are_unique(self):
        """Test that all enum values within each enum are unique"""
        enums = [EntityType, EntityStatus, OutputFormat, SortField]

        for enum_class in enums:
            values = enum_class.values()
            assert len(values) == len(
                set(values)
            ), f"Duplicate values found in {enum_class.__name__}"

    def test_enum_members_are_accessible(self):
        """Test that all enum members can be accessed by name"""
        # EntityType
        assert EntityType.PROGRAM
        assert EntityType.PROJECT
        assert EntityType.MISSION
        assert EntityType.ACTION

        # EntityStatus
        assert EntityStatus.ACTIVE
        assert EntityStatus.COMPLETED
        assert EntityStatus.ON_HOLD
        assert EntityStatus.CANCELLED
        assert EntityStatus.PLANNED

        # OutputFormat
        assert OutputFormat.TABLE
        assert OutputFormat.YAML
        assert OutputFormat.JSON
        assert OutputFormat.ID
        assert OutputFormat.PRETTY

        # SortField
        assert SortField.TITLE
        assert SortField.ID
        assert SortField.DUE_DATE
        assert SortField.STATUS
        assert SortField.CREATED
        assert SortField.MODIFIED
