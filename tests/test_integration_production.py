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

        # Check for generated schema files
        postgres_output = temp_output_dir / "postgresql" / "v15.0" / "spec.json"
        mysql_output = temp_output_dir / "mysql" / "v8.0" / "spec.json"

        assert postgres_output.exists(), "PostgreSQL schema should be generated"
        assert mysql_output.exists(), "MySQL schema should be generated"

        # Check for project schemas
        assert (temp_output_dir / "config" / "base.json").exists()
        assert (temp_output_dir / "config" / "engines" / "postgresql.json").exists()
        assert (temp_output_dir / "config" / "engines" / "mysql.json").exists()
        assert (temp_output_dir / "manifest.json").exists()
        assert (temp_output_dir / "smap.json").exists()

        # Verify content quality
        with open(postgres_output) as f:
            postgres_schema = json.load(f)

        with open(mysql_output) as f:
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
            temp_output_dir / "mysql" / "v8.0",
            temp_output_dir / "config" / "engines",
        ]

        for path in expected_structure:
            assert path.exists(), f"Expected directory {path} should exist"

        # Check spec files
        assert (temp_output_dir / "postgresql" / "v15.0" / "spec.json").exists()
        assert (temp_output_dir / "mysql" / "v8.0" / "spec.json").exists()

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

        # Create directory and spec for the new variant
        postgresql_14_dir = (
            temp_docs_dir / "schemas" / "engines" / "postgresql" / "v14.0"
        )
        postgresql_14_dir.mkdir(parents=True)

        with open(postgresql_14_dir / "spec.json", "w") as f:
            json.dump(
                {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "title": "PostgreSQL 14.0 Schema",
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
                f,
                indent=2,
            )

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run_for_testing()

        # Should create output for all variants
        assert (temp_output_dir / "postgresql" / "v15.0" / "spec.json").exists()
        assert (temp_output_dir / "postgresql" / "v14.0" / "spec.json").exists()
        assert (temp_output_dir / "mysql" / "v8.0" / "spec.json").exists()

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
        assert "base" in smap["project"]["config"]
        assert "engines" in smap["project"]["config"]

        # Check engine configs are present
        assert "postgresql" in smap["project"]["config"]["engines"]
        assert "mysql" in smap["project"]["config"]["engines"]

        # Check engine specs are present
        assert "postgresql" in smap["engines"]
        assert "mysql" in smap["engines"]
        assert "v15.0" in smap["engines"]["postgresql"]
        assert "v8.0" in smap["engines"]["mysql"]

    def test_schema_generation_performance_with_large_schema(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should handle large schemas efficiently."""
        # Create a large schema with many properties
        large_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
        }

        # Add 100 properties to simulate a large schema
        for i in range(100):
            large_schema["properties"][f"property_{i}"] = {
                "type": "string",
                "description": f"Property {i}",
            }

        # Update the PostgreSQL spec with the large schema
        spec_file = (
            temp_docs_dir / "schemas" / "engines" / "postgresql" / "v15.0" / "spec.json"
        )
        with open(spec_file, "w") as f:
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
