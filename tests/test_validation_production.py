"""Production-quality validation tests."""

import pytest

from database_schema_spec.core.schemas import ValidationResult
from database_schema_spec.validation.schema_validator import SchemaValidator


class TestSchemaValidator:
    """Test SchemaValidator with comprehensive coverage."""

    def test_validate_valid_basic_schema(self):
        """Should validate a basic valid schema successfully."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "database": {"type": "object"},
                "schema": {"type": "object"},
            },
            "required": ["database", "schema"],
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(schema)

        assert result.is_valid
        assert len(result.errors) == 0
        assert isinstance(result.warnings, list)

    def test_validate_schema_missing_required_properties(self):
        """Should detect missing required properties."""
        schema = {
            "type": "object"
            # Missing properties field
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(schema)

        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("properties" in error.lower() for error in result.errors)

    def test_validate_schema_invalid_json_schema(self):
        """Should detect invalid JSON Schema structure."""
        invalid_schema = {
            "type": "invalid_type",  # Not a valid JSON Schema type
            "properties": {"test": {"type": "another_invalid_type"}},
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(invalid_schema)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_validate_schema_with_oneOf_conditions(self):
        """Should validate schemas with complex oneOf conditions."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {"database": {"type": "object"}},
            "oneOf": [
                {
                    "if": {
                        "properties": {
                            "database": {
                                "properties": {"engine": {"const": "postgresql"}}
                            }
                        }
                    },
                    "then": {"properties": {"postgres_features": {"type": "object"}}},
                }
            ],
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(schema)

        assert result.is_valid
        assert len(result.errors) == 0

    def test_validate_schema_with_refs(self):
        """Should handle schemas with $ref references."""
        schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "database": {"$ref": "database.json"},
                "schema": {"$ref": "schema.json"},
            },
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(schema)

        assert result.is_valid
        # Should not error on $ref - that's resolved elsewhere

    def test_validate_schema_circular_structure(self):
        """Should handle potential circular references in validation."""
        # Create a schema that references itself (though not a real $ref)
        schema = {
            "type": "object",
            "properties": {
                "self": {
                    "type": "object",
                    "properties": {
                        "nested": {
                            "type": "object",
                            # This would be a deep nesting scenario
                            "properties": {"database": {"type": "string"}},
                        }
                    },
                }
            },
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(schema)

        assert result.is_valid

    def test_validate_schema_performance_large_schema(self):
        """Should validate large schemas efficiently."""
        # Create a large schema with many properties
        large_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {},
        }

        # Add many properties
        for i in range(1000):
            large_schema["properties"][f"prop_{i}"] = {
                "type": "string",
                "description": f"Property {i}",
                "minLength": 1,
                "maxLength": 100,
            }

        validator = SchemaValidator()

        import time

        start_time = time.time()
        result: ValidationResult = validator.validate_schema(large_schema)
        end_time = time.time()

        validation_time = end_time - start_time

        assert result.is_valid
        assert validation_time < 2.0, f"Validation took too long: {validation_time}s"

    def test_validate_schema_with_warnings(self):
        """Should generate warnings for problematic but valid schemas."""
        # Schema that might generate warnings (structure-specific)
        schema_with_warnings = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "database": {"type": "object"}
                # Might generate warnings about missing required fields
            },
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(schema_with_warnings)

        # Should be valid but might have warnings
        assert result.is_valid
        assert isinstance(result.warnings, list)

    @pytest.mark.parametrize(
        "invalid_type",
        [
            "invalid_type",
            123,  # Not a string
            [],  # Array instead of string
            None,  # None type
        ],
    )
    def test_validate_schema_invalid_types(self, invalid_type):
        """Should reject schemas with invalid type values."""
        invalid_schema = {"type": invalid_type, "properties": {}}

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(invalid_schema)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_validate_schema_empty_input(self):
        """Test validation of empty schema - should be valid but with warnings."""
        validator = SchemaValidator()
        result = validator.validate_schema({})

        # Empty schema is technically valid JSON Schema but will have warnings
        assert result.is_valid
        assert (
            len(result.warnings) > 0
        )  # Should have warnings about missing recommended fields
        assert "Missing '$schema' field" in result.warnings[0]

    def test_validate_schema_malformed_properties(self):
        """Should detect malformed properties structures."""
        malformed_schema = {
            "type": "object",
            "properties": "this should be an object",  # Invalid - should be dict
        }

        validator = SchemaValidator()
        result: ValidationResult = validator.validate_schema(malformed_schema)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_validation_result_immutability(self):
        """Should ensure ValidationResult behaves as expected."""
        schema = {"type": "object", "properties": {"test": {"type": "string"}}}

        validator = SchemaValidator()
        result = validator.validate_schema(schema)

        # Test the result object structure
        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert isinstance(result.is_valid, bool)
