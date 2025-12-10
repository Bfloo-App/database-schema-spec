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

    # Create test directory structure
    postgresql_15_dir = temp_dir / "postgresql" / "15.0"
    postgresql_16_dir = temp_dir / "postgresql" / "16.0"
    mysql_8_dir = temp_dir / "mysql" / "8.0"

    postgresql_15_dir.mkdir(parents=True)
    postgresql_16_dir.mkdir(parents=True)
    mysql_8_dir.mkdir(parents=True)

    # Create test spec.json files
    test_schema = {
        "title": "Test Schema",
        "type": "object",
        "properties": {"test": {"type": "string"}},
    }

    with open(postgresql_15_dir / "spec.json", "w") as f:
        json.dump(test_schema, f)

    with open(postgresql_16_dir / "spec.json", "w") as f:
        json.dump(test_schema, f)

    with open(mysql_8_dir / "spec.json", "w") as f:
        json.dump(test_schema, f)

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

    def test_get_output_path(self, output_manager):
        """Test _get_output_path method."""
        path = output_manager._get_output_path("postgresql", "15.0")

        expected = output_manager.output_dir / "postgresql" / "15.0" / "spec.json"
        assert path == expected

    def test_get_output_path_lowercase_engine(self, output_manager):
        """Test _get_output_path converts engine name to lowercase."""
        path = output_manager._get_output_path("PostgreSQL", "15.0")

        expected = output_manager.output_dir / "postgresql" / "15.0" / "spec.json"
        assert path == expected

    def test_write_schema_success(self, output_manager):
        """Test successful schema writing."""
        schema = {
            "title": "Test Schema",
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }

        result_path = output_manager.write_schema(schema, "postgresql", "15.0")

        # Check that file was created
        assert result_path.exists()
        assert result_path.is_file()

        # Check file contents
        with open(result_path, "r") as f:
            written_schema = json.load(f)

        assert written_schema == schema

    def test_write_schema_creates_directories(self, tmp_path):
        """Test that write_schema creates necessary directories."""
        output_dir = tmp_path / "new_output"
        manager = OutputManager(output_dir)

        schema = {"test": "data"}

        result_path = manager.write_schema(schema, "mysql", "8.0")

        # Check that directories were created
        assert (output_dir / "mysql" / "8.0").exists()
        assert result_path.exists()

    def test_write_schema_permission_error(self, output_manager):
        """Test handling of permission errors during schema writing."""
        schema = {"test": "data"}

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            with pytest.raises(PermissionError, match="Failed to write schema"):
                output_manager.write_schema(schema, "postgresql", "15.0")

    def test_get_spec_url_relative_path(self, output_manager):
        """Test _get_spec_url with no base URL (relative path)."""
        url = output_manager._get_spec_url("postgresql", "15.0")

        assert url == "postgresql/15.0/spec.json"

    def test_get_spec_url_with_base_url(self, output_manager):
        """Test _get_spec_url with base URL."""
        base_url = "https://api.example.com/schemas"
        url = output_manager._get_spec_url("postgresql", "15.0", base_url)

        assert url == "https://api.example.com/schemas/postgresql/15.0/spec.json"

    def test_get_spec_url_with_trailing_slash_base_url(self, output_manager):
        """Test _get_spec_url strips trailing slash from base URL."""
        base_url = "https://api.example.com/schemas/"
        url = output_manager._get_spec_url("postgresql", "15.0", base_url)

        assert url == "https://api.example.com/schemas/postgresql/15.0/spec.json"

    def test_get_spec_url_engine_lowercase(self, output_manager):
        """Test _get_spec_url converts engine to lowercase."""
        url = output_manager._get_spec_url("PostgreSQL", "15.0")

        assert url == "postgresql/15.0/spec.json"

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

        expected = {
            "postgresql": {
                "15.0": "postgresql/15.0/spec.json",
                "16.0": "postgresql/16.0/spec.json",
            },
            "mysql": {"8.0": "mysql/8.0/spec.json"},
        }

        assert engine_map == expected

    def test_generate_engine_map_with_base_url(self, output_manager):
        """Test _generate_engine_map with base URL."""
        base_url = "https://api.example.com/schemas"
        engine_map = output_manager._generate_engine_map(base_url)

        expected = {
            "postgresql": {
                "15.0": "https://api.example.com/schemas/postgresql/15.0/spec.json",
                "16.0": "https://api.example.com/schemas/postgresql/16.0/spec.json",
            },
            "mysql": {"8.0": "https://api.example.com/schemas/mysql/8.0/spec.json"},
        }

        assert engine_map == expected

    def test_generate_engine_map_ignores_files_in_engine_dir(self, temp_output_dir):
        """Test _generate_engine_map ignores files in engine directories."""
        # Create a file in the postgresql directory (not a version directory)
        postgresql_dir = temp_output_dir / "postgresql"
        (postgresql_dir / "readme.txt").write_text("Some file")

        manager = OutputManager(temp_output_dir)
        engine_map = manager._generate_engine_map()

        # Should still have the version directories, but ignore the file
        assert "postgresql" in engine_map
        assert "15.0" in engine_map["postgresql"]
        assert "16.0" in engine_map["postgresql"]

    def test_generate_engine_map_ignores_version_dirs_without_spec(
        self, temp_output_dir
    ):
        """Test _generate_engine_map ignores version directories without spec.json."""
        # Create a version directory without spec.json
        empty_version_dir = temp_output_dir / "postgresql" / "17.0"
        empty_version_dir.mkdir()

        manager = OutputManager(temp_output_dir)
        engine_map = manager._generate_engine_map()

        # Should not include the empty version directory
        assert "17.0" not in engine_map["postgresql"]
        assert "15.0" in engine_map["postgresql"]
        assert "16.0" in engine_map["postgresql"]

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

        # Check structure
        assert "project" in written_map
        assert "engines" in written_map
        assert "config" in written_map["project"]
        assert "base" in written_map["project"]["config"]
        assert "engines" in written_map["project"]["config"]

        # Check engine configs
        assert "postgresql" in written_map["project"]["config"]["engines"]
        assert "mysql" in written_map["project"]["config"]["engines"]

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
        assert written_map["project"]["config"]["base"].startswith(base_url)
        for url in written_map["project"]["config"]["engines"].values():
            assert url.startswith(base_url)
        for engine_versions in written_map["engines"].values():
            for url in engine_versions.values():
                assert url.startswith(base_url)

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

        # Write some test schemas
        test_schema = {"test": "data"}
        manager.write_schema(test_schema, "postgresql", "15.0")
        manager.write_schema(test_schema, "mysql", "8.0")

        # Generate schema map
        smap_path = manager.write_schema_map(
            ["PostgreSQL", "MySQL"], "https://example.com"
        )

        # Verify schema map contains the schemas we just wrote
        with open(smap_path, "r") as f:
            schema_map = json.load(f)

        assert "postgresql" in schema_map["engines"]
        assert "mysql" in schema_map["engines"]
        assert (
            schema_map["engines"]["postgresql"]["15.0"]
            == "https://example.com/postgresql/15.0/spec.json"
        )
        assert (
            schema_map["engines"]["mysql"]["8.0"]
            == "https://example.com/mysql/8.0/spec.json"
        )
