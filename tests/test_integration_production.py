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
        generator.run()

        # Verify output structure
        assert temp_output_dir.exists()

        # Check for generated schema files
        postgres_output = temp_output_dir / "postgresql" / "15.0" / "spec.json"
        mysql_output = temp_output_dir / "mysql" / "8.0" / "spec.json"

        assert postgres_output.exists(), "PostgreSQL schema should be generated"
        assert mysql_output.exists(), "MySQL schema should be generated"

        # Verify content quality
        with open(postgres_output) as f:
            postgres_schema = json.load(f)

        with open(mysql_output) as f:
            mysql_schema = json.load(f)

        # Basic schema validation
        assert postgres_schema.get("type") == "object", (
            f"Expected 'object', got {postgres_schema.get('type')}"
        )
        assert mysql_schema.get("type") == "object", (
            f"Expected 'object', got {mysql_schema.get('type')}"
        )

        # Verify basic structure
        assert "database" in postgres_schema.get("properties", {})
        assert "schema" in postgres_schema.get("properties", {})
        assert "database" in mysql_schema.get("properties", {})
        assert "schema" in mysql_schema.get("properties", {})

        # Verify conditional logic was resolved (no oneOf should remain)
        assert "oneOf" not in postgres_schema
        assert "oneOf" not in mysql_schema

    def test_schema_generation_with_missing_docs(self, temp_output_dir):
        """Should handle missing documentation directory gracefully."""
        non_existent_path = Path("/non/existent/path")
        generator = SchemaGenerator(
            docs_path=non_existent_path, output_path=temp_output_dir
        )

        with pytest.raises(SchemaGenerationError):
            generator.run_for_testing()

    def test_schema_generation_with_invalid_specs_file(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should handle invalid specs.json file."""
        # Corrupt the specs.json file
        with open(temp_docs_dir / "specs.json", "w") as f:
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
        generator.run()

        # Verify directory structure matches expected pattern
        expected_structure = [
            temp_output_dir / "postgresql" / "15.0",
            temp_output_dir / "mysql" / "8.0",
        ]

        for path in expected_structure:
            assert path.exists(), f"Expected directory {path} should exist"
            assert (path / "spec.json").exists(), f"spec.json should exist in {path}"

    def test_schema_generation_output_content_validity(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should generate valid JSON Schema compliant output."""
        import jsonschema

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run()

        # Check all generated files are valid JSON Schema
        for schema_file in temp_output_dir.rglob("*.json"):
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
        import json

        # Add another variant to database.json oneOf (this is what the variant extractor reads)
        database_file = temp_docs_dir / "schemas" / "base" / "database.json"
        with open(database_file) as f:
            database_schema = json.load(f)

        # Add PostgreSQL 14.0 variant to oneOf
        database_schema["oneOf"].append(
            {
                "properties": {
                    "engine": {
                        "type": "string",
                        "description": "The type of database engine used",
                        "const": "postgresql",
                    },
                    "version": {
                        "type": "string",
                        "description": "The version of the PostgreSQL database engine",
                        "const": "14.0",
                    },
                }
            }
        )

        with open(database_file, "w") as f:
            json.dump(database_schema, f, indent=2)

        # Create directory for the new variant
        postgresql_14_dir = (
            temp_docs_dir / "schemas" / "engines" / "postgresql" / "v14.0"
        )
        postgresql_14_dir.mkdir(parents=True)

        # Create spec.json for the new variant
        with open(postgresql_14_dir / "spec.json", "w") as f:
            json.dump(
                {
                    "title": "PostgreSQL 14.0 Schema Rules",
                    "properties": {
                        "postgres_14_features": {
                            "type": "object",
                            "description": "PostgreSQL 14.0-specific features",
                        }
                    },
                },
                f,
                indent=2,
            )

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run()

        # Should create output for all variants
        assert (temp_output_dir / "postgresql" / "15.0" / "spec.json").exists()
        assert (temp_output_dir / "postgresql" / "14.0" / "spec.json").exists()
        assert (temp_output_dir / "mysql" / "8.0" / "spec.json").exists()

    def test_schema_generation_with_circular_references(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should detect and handle circular references."""
        # Create a circular reference scenario
        circular_schema = {"$ref": "circular_ref.json"}

        with open(temp_docs_dir / "schemas" / "base" / "circular_ref.json", "w") as f:
            json.dump({"$ref": "database.json"}, f)

        # Modify database.json to reference the circular file
        with open(temp_docs_dir / "schemas" / "base" / "database.json", "w") as f:
            json.dump(circular_schema, f)

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )

        # Should handle circular references gracefully
        with pytest.raises(SchemaGenerationError, match="circular"):
            generator.run_for_testing()

    def test_schema_generation_performance_with_large_schema(
        self, temp_docs_dir, temp_output_dir
    ):
        """Should handle large schemas efficiently."""
        # Create a large schema with many properties
        large_schema = {"type": "object", "properties": {}}

        # Add 100 properties to simulate a large schema
        for i in range(100):
            large_schema["properties"][f"property_{i}"] = {
                "type": "string",
                "description": f"Property {i}",
            }

        # Add the large schema to the base schemas
        with open(temp_docs_dir / "schemas" / "base" / "large_schema.json", "w") as f:
            json.dump(large_schema, f, indent=2)

        # Read existing database.json (don't overwrite the oneOf structure)
        with open(temp_docs_dir / "schemas" / "base" / "database.json") as f:
            database_schema = json.load(f)

        # Add a reference to the large schema in properties if not already there
        if "properties" not in database_schema:
            database_schema["properties"] = {}
        database_schema["properties"]["large_schema"] = {"$ref": "large_schema.json"}

        # Write back the modified database schema
        with open(temp_docs_dir / "schemas" / "base" / "database.json", "w") as f:
            json.dump(database_schema, f, indent=2)

        import time

        start_time = time.time()

        generator = SchemaGenerator(
            docs_path=temp_docs_dir, output_path=temp_output_dir
        )
        generator.run_for_testing()  # Use test-friendly version

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete within reasonable time (adjust as needed)
        assert processing_time < 5.0, (
            f"Schema generation took too long: {processing_time}s"
        )
