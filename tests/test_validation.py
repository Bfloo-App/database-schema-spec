from database_schema_spec.core.schemas import ValidationResult
from database_schema_spec.validation.schema_validator import SchemaValidator


def test_valid_schema():
    schema = {
        "properties": {
            "database": {"type": "object"},
            "schema": {"type": "object"},
        }
    }
    validator = SchemaValidator()
    result: ValidationResult = validator.validate_schema(schema)
    assert result.is_valid
    assert not result.errors


def test_missing_properties():
    # Test a schema that explicitly declares type object but is missing properties
    schema = {"type": "object"}
    validator = SchemaValidator()
    result: ValidationResult = validator.validate_schema(schema)
    assert not result.is_valid
    assert "Missing 'properties' field" in result.errors[0]
