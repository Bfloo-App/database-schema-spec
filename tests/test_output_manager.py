"""Tests for the OutputManager class."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from database_schema_spec.io.output_manager import OutputManager


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory with test data."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create test directory structure with new schema layout
    postgresql_15_dir = temp_dir / "postgresql" / "v15.0"
    postgresql_16_dir = temp_dir / "postgresql" / "v16.0"
    mysql_8_dir = temp_dir / "mysql" / "v8.0"

    (postgresql_15_dir / "snapshot").mkdir(parents=True)
    (postgresql_16_dir / "snapshot").mkdir(parents=True)
    (mysql_8_dir / "snapshot").mkdir(parents=True)

    # Create test schema files (tables.json and snapshot schemas)
    test_tables = {
        "title": "Test Tables Schema",
        "type": "array",
        "items": {"type": "object"},
    }

    test_stored = {
        "title": "Test Stored Snapshot",
        "type": "object",
        "properties": {"description": {"type": "string"}, "tables": {"type": "array"}},
    }

    test_working = {
        "title": "Test Working Snapshot",
        "type": "object",
        "properties": {"schema": {"type": "object"}, "snapshot": {"type": "object"}},
    }

    for version_dir in [postgresql_15_dir, postgresql_16_dir, mysql_8_dir]:
        with open(version_dir / "tables.json", "w") as f:
            json.dump(test_tables, f)
        with open(version_dir / "snapshot" / "stored.json", "w") as f:
            json.dump(test_stored, f)
        with open(version_dir / "snapshot" / "working.json", "w") as f:
            json.dump(test_working, f)

    yield temp_dir

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def output_manager(temp_output_dir):
    """Create an OutputManager instance with a temporary directory."""
    return OutputManager(temp_output_dir)


class TestOutputManager:
    """Test suite for OutputManager class."""

    def test_init_with_default_output_dir(self):
        """Test OutputManager initialization with default output directory."""
        from database_schema_spec.core.config import config

        manager = OutputManager()
        assert manager.output_dir == config.output_dir

    def test_init_with_custom_output_dir(self, temp_output_dir):
        """Test OutputManager initialization with custom output directory."""
        manager = OutputManager(temp_output_dir)
        assert manager.output_dir == temp_output_dir

    def test_create_output_structure_success(self, tmp_path):
        """Test successful creation of output directory structure."""
        output_dir = tmp_path / "test_output"
        manager = OutputManager(output_dir)

        manager.create_output_structure()

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_create_output_structure_permission_error(self):
        """Test handling of permission errors during directory creation."""
        # Use a path that would cause permission error (like root-only directory)
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            manager = OutputManager(Path("/root/test"))

            with pytest.raises(
                PermissionError, match="Failed to create output directory"
            ):
                manager.create_output_structure()

    def test_get_engine_schema_path(self, output_manager):
        """Test _get_engine_schema_path method."""
        path = output_manager._get_engine_schema_path("postgresql", "v15.0", "tables")

        expected = output_manager.output_dir / "postgresql" / "v15.0" / "tables.json"
        assert path == expected

    def test_get_engine_schema_path_lowercase_engine(self, output_manager):
        """Test _get_engine_schema_path converts engine name to lowercase."""
        path = output_manager._get_engine_schema_path("PostgreSQL", "v15.0", "tables")

        expected = output_manager.output_dir / "postgresql" / "v15.0" / "tables.json"
        assert path == expected

    def test_write_engine_schema_success(self, output_manager):
        """Test successful engine schema writing."""
        schema = {
            "title": "Test Schema",
            "type": "array",
            "items": {"type": "object"},
        }

        result_path = output_manager.write_engine_schema(
            schema, "postgresql", "v15.0", "tables"
        )

        # Check that file was created
        assert result_path.exists()
        assert result_path.is_file()

        # Check file contents
        with open(result_path, "r") as f:
            written_schema = json.load(f)

        assert written_schema == schema

    def test_write_engine_schema_creates_directories(self, tmp_path):
        """Test that write_engine_schema creates necessary directories."""
        output_dir = tmp_path / "new_output"
        manager = OutputManager(output_dir)

        schema = {"test": "data"}

        result_path = manager.write_engine_schema(
            schema, "mysql", "v8.0", "snapshot/stored"
        )

        # Check that directories were created
        assert (output_dir / "mysql" / "v8.0" / "snapshot").exists()
        assert result_path.exists()

    def test_write_engine_schema_permission_error(self, output_manager):
        """Test handling of permission errors during schema writing."""
        schema = {"test": "data"}

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError, match="Failed to write schema"):
                output_manager.write_engine_schema(
                    schema, "postgresql", "v15.0", "tables"
                )

    def test_get_engine_schema_url_relative_path(self, output_manager):
        """Test _get_engine_schema_url with no base URL (relative path)."""
        url = output_manager._get_engine_schema_url("postgresql", "v15.0", "tables")

        assert url == "postgresql/v15.0/tables.json"

    def test_get_engine_schema_url_with_base_url(self, output_manager):
        """Test _get_engine_schema_url with base URL."""
        base_url = "https://api.example.com/schemas"
        url = output_manager._get_engine_schema_url(
            "postgresql", "v15.0", "tables", base_url
        )

        assert url == "https://api.example.com/schemas/postgresql/v15.0/tables.json"

    def test_get_engine_schema_url_with_trailing_slash_base_url(self, output_manager):
        """Test _get_engine_schema_url strips trailing slash from base URL."""
        base_url = "https://api.example.com/schemas/"
        url = output_manager._get_engine_schema_url(
            "postgresql", "v15.0", "tables", base_url
        )

        assert url == "https://api.example.com/schemas/postgresql/v15.0/tables.json"

    def test_get_engine_schema_url_engine_lowercase(self, output_manager):
        """Test _get_engine_schema_url converts engine to lowercase."""
        url = output_manager._get_engine_schema_url("PostgreSQL", "v15.0", "tables")

        assert url == "postgresql/v15.0/tables.json"

    def test_generate_engine_map_empty_directory(self, tmp_path):
        """Test _generate_engine_map with empty output directory."""
        empty_dir = tmp_path / "empty"
        manager = OutputManager(empty_dir)

        engine_map = manager._generate_engine_map()

        assert engine_map == {}

    def test_generate_engine_map_nonexistent_directory(self, tmp_path):
        """Test _generate_engine_map with nonexistent output directory."""
        nonexistent_dir = tmp_path / "nonexistent"
        manager = OutputManager(nonexistent_dir)

        engine_map = manager._generate_engine_map()

        assert engine_map == {}

    def test_generate_engine_map_multiple_engines(self, output_manager):
        """Test _generate_engine_map with multiple engines and versions."""
        engine_map = output_manager._generate_engine_map()

        # Check structure - now nested with schema types
        assert "postgresql" in engine_map
        assert "mysql" in engine_map

        # Check PostgreSQL versions
        assert "v15.0" in engine_map["postgresql"]
        assert "v16.0" in engine_map["postgresql"]

        # Check schema types within version
        assert "tables" in engine_map["postgresql"]["v15.0"]
        assert "snapshot" in engine_map["postgresql"]["v15.0"]
        assert "stored" in engine_map["postgresql"]["v15.0"]["snapshot"]
        assert "working" in engine_map["postgresql"]["v15.0"]["snapshot"]

        # Check URLs
        assert (
            engine_map["postgresql"]["v15.0"]["tables"]
            == "postgresql/v15.0/tables.json"
        )
        assert (
            engine_map["postgresql"]["v15.0"]["snapshot"]["stored"]
            == "postgresql/v15.0/snapshot/stored.json"
        )
        assert (
            engine_map["postgresql"]["v15.0"]["snapshot"]["working"]
            == "postgresql/v15.0/snapshot/working.json"
        )

    def test_generate_engine_map_with_base_url(self, output_manager):
        """Test _generate_engine_map with base URL."""
        base_url = "https://api.example.com/schemas"
        engine_map = output_manager._generate_engine_map(base_url)

        # Check URLs include base URL
        assert (
            engine_map["postgresql"]["v15.0"]["tables"]
            == "https://api.example.com/schemas/postgresql/v15.0/tables.json"
        )
        assert (
            engine_map["postgresql"]["v15.0"]["snapshot"]["stored"]
            == "https://api.example.com/schemas/postgresql/v15.0/snapshot/stored.json"
        )

    def test_generate_engine_map_ignores_files_in_engine_dir(self, temp_output_dir):
        """Test _generate_engine_map ignores files in engine directories."""
        # Create a file in the postgresql directory (not a version directory)
        postgresql_dir = temp_output_dir / "postgresql"
        (postgresql_dir / "readme.txt").write_text("Some file")

        manager = OutputManager(temp_output_dir)
        engine_map = manager._generate_engine_map()

        # Should still have the version directories, but ignore the file
        assert "postgresql" in engine_map
        assert "v15.0" in engine_map["postgresql"]
        assert "v16.0" in engine_map["postgresql"]

    def test_generate_engine_map_ignores_version_dirs_without_tables(
        self, temp_output_dir
    ):
        """Test _generate_engine_map ignores version directories without tables.json."""
        # Create a version directory without tables.json
        empty_version_dir = temp_output_dir / "postgresql" / "v17.0"
        empty_version_dir.mkdir()

        manager = OutputManager(temp_output_dir)
        engine_map = manager._generate_engine_map()

        # Should not include the empty version directory
        assert "v17.0" not in engine_map["postgresql"]
        assert "v15.0" in engine_map["postgresql"]
        assert "v16.0" in engine_map["postgresql"]

    def test_generate_engine_map_ignores_config_directory(self, temp_output_dir):
        """Test _generate_engine_map ignores the config directory."""
        # Create a config directory (should be ignored)
        config_dir = temp_output_dir / "config" / "engines"
        config_dir.mkdir(parents=True)
        (config_dir / "postgresql.json").write_text("{}")

        manager = OutputManager(temp_output_dir)
        engine_map = manager._generate_engine_map()

        # config should not appear in engine map
        assert "config" not in engine_map
        assert "postgresql" in engine_map

    def test_write_schema_map_success(self, output_manager):
        """Test successful schema map writing."""
        result_path = output_manager.write_schema_map(["PostgreSQL", "MySQL"])

        # Check that file was created
        assert result_path.exists()
        assert result_path.name == "smap.json"

        # Check file contents
        with open(result_path, "r") as f:
            written_map = json.load(f)

        # Check structure - now config is directly a map of engine -> URL
        assert "project" in written_map
        assert "engines" in written_map
        assert "config" in written_map["project"]

        # Check engine configs are directly under config (not config.engines)
        assert "postgresql" in written_map["project"]["config"]
        assert "mysql" in written_map["project"]["config"]

        # Verify the config URLs point to config/{engine}.json
        assert (
            written_map["project"]["config"]["postgresql"] == "config/postgresql.json"
        )
        assert written_map["project"]["config"]["mysql"] == "config/mysql.json"

        # Check engine specs
        assert "postgresql" in written_map["engines"]
        assert "mysql" in written_map["engines"]

    def test_write_schema_map_with_base_url(self, output_manager):
        """Test schema map writing with base URL."""
        base_url = "https://api.example.com/schemas"
        result_path = output_manager.write_schema_map(["PostgreSQL"], base_url)

        # Check file contents
        with open(result_path, "r") as f:
            written_map = json.load(f)

        # All URLs should include the base URL
        assert written_map["project"]["manifest"].startswith(base_url)

        # Config URLs are now directly under project.config
        for url in written_map["project"]["config"].values():
            assert url.startswith(base_url)

        # Check engine schema URLs (now nested structure)
        for engine_versions in written_map["engines"].values():
            for version_schemas in engine_versions.values():
                # tables URL
                assert version_schemas["tables"].startswith(base_url)
                # snapshot URLs
                if "snapshot" in version_schemas:
                    for snapshot_url in version_schemas["snapshot"].values():
                        assert snapshot_url.startswith(base_url)

    def test_write_schema_map_creates_output_directory(self, tmp_path):
        """Test that write_schema_map creates output directory if it doesn't exist."""
        output_dir = tmp_path / "new_output"
        manager = OutputManager(output_dir)

        result_path = manager.write_schema_map([])

        # Directory should be created
        assert output_dir.exists()
        assert result_path.exists()

    def test_write_schema_map_permission_error(self, output_manager):
        """Test handling of permission errors during schema map writing."""
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError, match="Failed to write schema map"):
                output_manager.write_schema_map([])

    def test_write_schema_map_json_formatting(self, output_manager):
        """Test that schema map is written with proper JSON formatting."""
        result_path = output_manager.write_schema_map(["PostgreSQL"])

        # Read the raw file content to check formatting
        with open(result_path, "r") as f:
            content = f.read()

        # Should be pretty-printed (contains newlines and indentation)
        assert "\n" in content
        assert "  " in content  # Check for indentation

        # Should be valid JSON
        json.loads(content)  # This will raise if invalid

    def test_integration_with_schema_generation(self, tmp_path):
        """Test integration of schema map with actual schema generation."""
        output_dir = tmp_path / "integration_test"
        manager = OutputManager(output_dir)

        # Write some test schemas using the new API
        test_tables = {"title": "Test Tables", "type": "array"}
        test_stored = {"title": "Test Stored", "type": "object"}
        test_working = {"title": "Test Working", "type": "object"}

        # PostgreSQL v15.0
        manager.write_engine_schema(test_tables, "postgresql", "v15.0", "tables")
        manager.write_engine_schema(
            test_stored, "postgresql", "v15.0", "snapshot/stored"
        )
        manager.write_engine_schema(
            test_working, "postgresql", "v15.0", "snapshot/working"
        )

        # MySQL v8.0
        manager.write_engine_schema(test_tables, "mysql", "v8.0", "tables")
        manager.write_engine_schema(test_stored, "mysql", "v8.0", "snapshot/stored")
        manager.write_engine_schema(test_working, "mysql", "v8.0", "snapshot/working")

        # Generate schema map
        smap_path = manager.write_schema_map(
            ["PostgreSQL", "MySQL"], "https://example.com"
        )

        # Verify schema map contains the schemas we just wrote
        with open(smap_path, "r") as f:
            schema_map = json.load(f)

        assert "postgresql" in schema_map["engines"]
        assert "mysql" in schema_map["engines"]

        # Check nested structure
        assert "v15.0" in schema_map["engines"]["postgresql"]
        assert "tables" in schema_map["engines"]["postgresql"]["v15.0"]
        assert "snapshot" in schema_map["engines"]["postgresql"]["v15.0"]

        assert (
            schema_map["engines"]["postgresql"]["v15.0"]["tables"]
            == "https://example.com/postgresql/v15.0/tables.json"
        )
        assert (
            schema_map["engines"]["postgresql"]["v15.0"]["snapshot"]["stored"]
            == "https://example.com/postgresql/v15.0/snapshot/stored.json"
        )
        assert (
            schema_map["engines"]["mysql"]["v8.0"]["tables"]
            == "https://example.com/mysql/v8.0/tables.json"
        )


class TestWriteResolvedEngineConfig:
    """Tests for the write_resolved_engine_config method."""

    def test_write_resolved_engine_config_success(self, tmp_path):
        """Test successful resolved engine config writing."""
        docs_dir = tmp_path / "docs"
        output_dir = tmp_path / "output"
        (docs_dir / "schemas" / "project" / "config" / "engines").mkdir(parents=True)

        # Create engine-specific schema
        engine_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "$defs": {"envs": {"type": "object", "description": "Environment configs"}},
        }
        with open(
            docs_dir / "schemas" / "project" / "config" / "engines" / "postgresql.json",
            "w",
        ) as f:
            json.dump(engine_schema, f)

        # Create base config schema with reference to engine schema
        base_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Base Project Configuration",
            "type": "object",
            "$defs": {
                "schemaDefinition": {
                    "properties": {
                        "envs": {"$ref": "engines/postgresql.json#/$defs/envs"}
                    }
                }
            },
            "properties": {
                "schemas": {
                    "additionalProperties": {"$ref": "#/$defs/schemaDefinition"}
                }
            },
        }
        with open(docs_dir / "schemas" / "project" / "config" / "base.json", "w") as f:
            json.dump(base_schema, f)

        manager = OutputManager(output_dir, docs_dir)
        result_path = manager.write_resolved_engine_config(
            "PostgreSQL",
            "schemas/project/config/base.json",
            "https://example.com",
        )

        # Check that file was created at correct path
        assert result_path.exists()
        assert result_path == output_dir / "config" / "postgresql.json"

        # Check file contents
        with open(result_path, "r") as f:
            written_schema = json.load(f)

        # Verify $id was injected
        assert written_schema["$id"] == "https://example.com/config/postgresql.json"

        # Verify title was updated
        assert "PostgreSQL" in written_schema["title"]

        # Verify the reference was resolved (envs should be inlined)
        schema_def = written_schema["$defs"]["schemaDefinition"]
        assert schema_def["properties"]["envs"]["type"] == "object"
        assert schema_def["properties"]["envs"]["description"] == "Environment configs"

    def test_write_resolved_engine_config_output_path(self, tmp_path):
        """Test that config is written to config/{engine}.json."""
        docs_dir = tmp_path / "docs"
        output_dir = tmp_path / "output"
        (docs_dir / "schemas" / "project" / "config").mkdir(parents=True)

        # Create minimal base config schema
        base_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Base Config",
            "type": "object",
        }
        with open(docs_dir / "schemas" / "project" / "config" / "base.json", "w") as f:
            json.dump(base_schema, f)

        manager = OutputManager(output_dir, docs_dir)
        result_path = manager.write_resolved_engine_config(
            "MySQL",
            "schemas/project/config/base.json",
        )

        # Verify output path follows config/{engine}.json pattern
        assert result_path == output_dir / "config" / "mysql.json"
        assert result_path.exists()

    def test_write_resolved_engine_config_preserves_schema_order(self, tmp_path):
        """Test that $schema and $id are ordered correctly."""
        docs_dir = tmp_path / "docs"
        output_dir = tmp_path / "output"
        (docs_dir / "schemas" / "project" / "config").mkdir(parents=True)

        base_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Base Config",
            "type": "object",
        }
        with open(docs_dir / "schemas" / "project" / "config" / "base.json", "w") as f:
            json.dump(base_schema, f)

        manager = OutputManager(output_dir, docs_dir)
        result_path = manager.write_resolved_engine_config(
            "PostgreSQL",
            "schemas/project/config/base.json",
            "https://example.com",
        )

        # Read raw content to check key ordering
        with open(result_path, "r") as f:
            content = f.read()

        # $schema should come before $id
        schema_pos = content.find('"$schema"')
        id_pos = content.find('"$id"')
        assert schema_pos < id_pos
