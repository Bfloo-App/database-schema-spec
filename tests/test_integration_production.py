"""Production-quality integration tests."""

import json
from pathlib import Path

import pytest

from database_schema_spec.cli.generator import SchemaGenerator
from database_schema_spec.core.exceptions import SchemaGenerationError


class TestSchemaGenerationIntegration:
    """Test complete schema generation workflow."""

    def test_schema_generation_with_real_data(self, temp_docs_dir, temp_output_dir):
        """Should generate valid schemas from realistic test data."""
        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )

        # This should not raise any exceptions
        generator.run_for_testing()

        # Verify output structure
        assert temp_output_dir.exists()

        # Check for generated schema files (new structure: tables.json, snapshot/)
        postgres_tables = temp_output_dir / "postgresql" / "v15.0" / "tables.json"
        postgres_stored = (
            temp_output_dir / "postgresql" / "v15.0" / "snapshot" / "stored.json"
        )
        postgres_working = (
            temp_output_dir / "postgresql" / "v15.0" / "snapshot" / "working.json"
        )
        mysql_tables = temp_output_dir / "mysql" / "v8.0" / "tables.json"

        assert postgres_tables.exists(), "PostgreSQL tables schema should be generated"
        assert postgres_stored.exists(), (
            "PostgreSQL stored snapshot schema should be generated"
        )
        assert postgres_working.exists(), (
            "PostgreSQL working snapshot schema should be generated"
        )
        assert mysql_tables.exists(), "MySQL tables schema should be generated"

        # Check for project schemas (new structure: config/{engine}.json, no base.json)
        assert (temp_output_dir / "config" / "postgresql.json").exists()
        assert (temp_output_dir / "config" / "mysql.json").exists()
        assert (temp_output_dir / "manifest.json").exists()
        assert (temp_output_dir / "smap.json").exists()

        # Verify content quality
        with open(postgres_tables) as f:
            postgres_schema = json.load(f)

        with open(mysql_tables) as f:
            mysql_schema = json.load(f)

        # Basic schema validation - check they have $id injected
        assert "$id" in postgres_schema
        assert "$id" in mysql_schema

    def test_schema_generation_with_missing_docs(self, temp_output_dir):
        """Should handle missing documentation directory gracefully."""
        non_existent_path = Path("/non/existent/path")
        generator = SchemaGenerator(
            docs_path=non_existent_path, output_path=temp_output_dir
        )

        with pytest.raises(SchemaGenerationError):
            generator.run_for_testing()

    def test_schema_generation_with_invalid_registry_file(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should handle invalid _registry_.json file."""
        # Corrupt the _registry_.json file
        with open(temp_docs_dir / "schemas" / "_registry_.json", "w") as f:
            f.write("invalid json content")

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )

        with pytest.raises(SchemaGenerationError):
            generator.run_for_testing()

    def test_schema_generation_preserves_file_structure(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should create proper output file structure."""
        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run_for_testing()

        # Verify directory structure matches expected pattern
        expected_structure = [
            temp_output_dir / "postgresql" / "v15.0",
            temp_output_dir / "postgresql" / "v15.0" / "snapshot",
            temp_output_dir / "mysql" / "v8.0",
            temp_output_dir / "mysql" / "v8.0" / "snapshot",
            temp_output_dir / "config",
        ]

        for path in expected_structure:
            assert path.exists(), f"Expected directory {path} should exist"

        # Check new schema files (tables.json, snapshot/stored.json, snapshot/working.json)
        assert (temp_output_dir / "postgresql" / "v15.0" / "tables.json").exists()
        assert (
            temp_output_dir / "postgresql" / "v15.0" / "snapshot" / "stored.json"
        ).exists()
        assert (
            temp_output_dir / "postgresql" / "v15.0" / "snapshot" / "working.json"
        ).exists()
        assert (temp_output_dir / "mysql" / "v8.0" / "tables.json").exists()

    def test_schema_generation_output_content_validity(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should generate valid JSON Schema compliant output."""
        import jsonschema

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run_for_testing()

        # Check all generated files are valid JSON Schema
        for schema_file in temp_output_dir.rglob("*.json"):
            if schema_file.name == "smap.json":
                continue  # smap.json is not a JSON Schema

            with open(schema_file) as f:
                schema_content = json.load(f)

            # Should be valid JSON Schema Draft 7
            try:
                jsonschema.Draft7Validator.check_schema(schema_content)
            except jsonschema.SchemaError as e:
                pytest.fail(
                    f"Generated schema {schema_file} is not valid JSON Schema: {e}"
                )

    def test_schema_generation_handles_multiple_variants(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should correctly handle multiple database variants."""
        # Add another variant to _registry_.json
        registry_file = temp_docs_dir / "schemas" / "_registry_.json"
        with open(registry_file) as f:
            registry = json.load(f)

        # Add PostgreSQL v14.0 variant using oneOf format
        registry["oneOf"].append(
            {
                "properties": {
                    "engine": {"const": "PostgreSQL"},
                    "version": {"const": "v14.0"},
                }
            }
        )

        with open(registry_file, "w") as f:
            json.dump(registry, f, indent=2)

        # Create directory and schemas for the new variant (new structure)
        postgresql_14_dir = (
            temp_docs_dir / "schemas" / "engines" / "postgresql" / "v14.0"
        )
        postgresql_14_snapshot_dir = postgresql_14_dir / "snapshot"
        postgresql_14_dir.mkdir(parents=True)
        postgresql_14_snapshot_dir.mkdir(parents=True)

        # Create tables.json
        with open(postgresql_14_dir / "tables.json", "w") as f:
            json.dump(
                {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "title": "PostgreSQL 14.0 Tables Schema",
                    "type": "array",
                    "items": {"type": "object"},
                },
                f,
                indent=2,
            )

        # Create snapshot/stored.json
        with open(postgresql_14_snapshot_dir / "stored.json", "w") as f:
            json.dump(
                {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "title": "Stored Snapshot",
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "tables": {"type": "array"},
                    },
                },
                f,
                indent=2,
            )

        # Create snapshot/working.json
        with open(postgresql_14_snapshot_dir / "working.json", "w") as f:
            json.dump(
                {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "title": "Working Snapshot",
                    "type": "object",
                    "properties": {
                        "schema": {"type": "object"},
                        "snapshot": {"type": "object"},
                    },
                },
                f,
                indent=2,
            )

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run_for_testing()

        # Should create output for all variants (new file structure)
        assert (temp_output_dir / "postgresql" / "v15.0" / "tables.json").exists()
        assert (temp_output_dir / "postgresql" / "v14.0" / "tables.json").exists()
        assert (temp_output_dir / "mysql" / "v8.0" / "tables.json").exists()

    def test_schema_generation_schema_map_structure(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should generate correct smap.json structure."""
        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run_for_testing()

        smap_path = temp_output_dir / "smap.json"
        assert smap_path.exists()

        with open(smap_path) as f:
            smap = json.load(f)

        # Check structure
        assert "project" in smap
        assert "engines" in smap

        # Check project section
        assert "manifest" in smap["project"]
        assert "config" in smap["project"]

        # Check engine configs are directly under config (new structure)
        assert "postgresql" in smap["project"]["config"]
        assert "mysql" in smap["project"]["config"]

        # Verify config URLs point to config/{engine}.json
        assert "config/postgresql.json" in smap["project"]["config"]["postgresql"]
        assert "config/mysql.json" in smap["project"]["config"]["mysql"]

        # Check engine specs are present (new nested structure)
        assert "postgresql" in smap["engines"]
        assert "mysql" in smap["engines"]
        assert "v15.0" in smap["engines"]["postgresql"]
        assert "v8.0" in smap["engines"]["mysql"]

        # Check nested schema types
        assert "tables" in smap["engines"]["postgresql"]["v15.0"]
        assert "snapshot" in smap["engines"]["postgresql"]["v15.0"]
        assert "stored" in smap["engines"]["postgresql"]["v15.0"]["snapshot"]
        assert "working" in smap["engines"]["postgresql"]["v15.0"]["snapshot"]

    def test_schema_generation_performance_with_large_schema(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should handle large schemas efficiently."""
        # Create a large schema with many properties
        large_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "array",
            "items": {
                "type": "object",
                "properties": {},
            },
        }

        # Add 100 properties to simulate a large schema
        for i in range(100):
            large_schema["items"]["properties"][f"property_{i}"] = {
                "type": "string",
                "description": f"Property {i}",
            }

        # Update the PostgreSQL tables.json with the large schema
        tables_file = (
            temp_docs_dir
            / "schemas"
            / "engines"
            / "postgresql"
            / "v15.0"
            / "tables.json"
        )
        with open(tables_file, "w") as f:
            json.dump(large_schema, f, indent=2)

        import time

        start_time = time.time()

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run_for_testing()

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete within reasonable time (adjust as needed)
        assert processing_time < 5.0, (
            f"Schema generation took too long: {processing_time}s"
        )
