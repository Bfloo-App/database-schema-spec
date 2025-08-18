"""Schema validation against JSON Schema standards."""

from __future__ import annotations

from typing import Any

import jsonschema
from jsonschema import Draft7Validator

from database_schema_spec.core.config import config
from database_schema_spec.core.schemas import ValidationResult


class SchemaValidator:
    """Validates generated schemas against JSON Schema standards.

    This validator checks that generated schemas conform to JSON Schema Draft 7
    standard and includes additional checks for project-specific requirements.
    """

    def validate_schema(self, schema: dict[str, Any]) -> ValidationResult:
        """Validate a schema against JSON Schema Draft 7 standard.

        Args:
            schema: Schema to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate against JSON Schema Draft 7
        try:
            Draft7Validator.check_schema(schema)
        except jsonschema.SchemaError as e:
            errors.append(f"JSON Schema validation failed: {e.message}")

        # Perform additional custom validations
        self._validate_required_fields(schema, errors)
        self._validate_schema_structure(schema, warnings)

        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _validate_required_fields(
        self, schema: dict[str, Any], errors: list[str]
    ) -> None:
        """Validate that required fields are present in the schema.

        Args:
            schema: Schema to validate
            errors: List to append errors to
        """
        # For a JSON Schema, we should validate it has the basic structure
        # Check that it's a proper JSON Schema with properties (if it's an object schema)
        if schema.get("type") == "object" and "properties" not in schema:
            errors.append(
                "Missing 'properties' field - object type schemas should have properties"
            )
            return

        # Only validate project-specific requirements for root schemas that have both database and schema refs
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            if "properties" in schema:
                errors.append("'properties' field must be an object")
            return

        # Only require database/schema properties if this looks like a root project schema
        # (has $schema field and references both database and schema)
        is_root_schema = (
            "$schema" in schema
            and isinstance(properties, dict)
            and any(
                prop.get("$ref") in ["database.json", "schema.json"]
                for prop in properties.values()
                if isinstance(prop, dict)
            )
        )

        if is_root_schema:
            # Check for database property definition
            if "database" not in properties:
                errors.append("Missing 'database' property definition in schema")
            elif not isinstance(properties["database"], dict):
                errors.append("'database' property definition must be an object")

            # Check for schema property definition
            if "schema" not in properties:
                errors.append("Missing 'schema' property definition in schema")
            elif not isinstance(properties["schema"], dict):
                errors.append("'schema' property definition must be an object")

    def _validate_schema_structure(
        self, schema: dict[str, Any], warnings: list[str]
    ) -> None:
        """Validate the overall structure of the schema.

        Args:
            schema: Schema to validate
            warnings: List to append warnings to
        """
        # Check for recommended fields
        if config.json_schema_fields.schema_field not in schema:
            warnings.append(
                "Missing '$schema' field - recommended for schema validation"
            )

        if config.json_schema_fields.id_field not in schema:
            warnings.append(
                "Missing '$id' field - recommended for schema identification"
            )

        if "title" not in schema:
            warnings.append("Missing 'title' field - recommended for documentation")

        # Check for unresolved references
        self._check_unresolved_refs(schema, warnings, "")

    def _check_unresolved_refs(self, obj: Any, warnings: list[str], path: str) -> None:
        """Recursively check for unresolved $ref references.
        Args:
            obj: Object to check
            warnings: List to append warnings to
            path: Current path in the object tree for error reporting
        """
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else str(key)
                if key == config.json_schema_fields.ref_field and isinstance(
                    value, str
                ):
                    warnings.append(
                        f"Unresolved reference found at {current_path}: {value}"
                    )
                else:
                    self._check_unresolved_refs(value, warnings, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                self._check_unresolved_refs(item, warnings, current_path)
