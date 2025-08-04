"""Conditional oneOf logic and engine-specific merging with validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from database_schema_spec.core.constants import ONEOF_FIELD, REF_FIELD
from database_schema_spec.core.exceptions import ValidationError
from database_schema_spec.core.schemas import DatabaseVariantSpec

if TYPE_CHECKING:
    from database_schema_spec.resolution.interfaces import IJSONRefResolver


class ConditionalMerger:
    """Handles conditional oneOf logic and engine-specific merging with validation.

    This class processes oneOf conditional blocks in JSON schemas to resolve
    them to database-specific configurations. It supports two formats:
    1. if/then conditional structure (specs.json style)
    2. Direct property constraints (database.json style)
    """

    def __init__(self, resolver: "IJSONRefResolver") -> None:
        """Initialize the conditional merger.

        Args:
            resolver: JSON reference resolver for handling nested references
        """
        self.resolver = resolver

    def apply_conditional_logic(
        self, base_schema: dict[str, Any], variant: DatabaseVariantSpec
    ) -> dict[str, Any]:
        """Apply conditional oneOf logic for a specific database variant.

        Args:
            base_schema: The resolved base schema
            variant: Database variant to apply conditions for

        Returns:
            Schema with oneOf conditions resolved for the variant

        Raises:
            ValidationError: If no matching condition found or multiple matches
        """
        # Make a copy of the schema to avoid modifying the original
        result_schema = dict(base_schema)

        # Check if this schema has oneOf conditions to process
        oneof_data = result_schema.get(ONEOF_FIELD)
        if not oneof_data or not isinstance(oneof_data, list):
            return result_schema

        # Track matching conditions
        matching_conditions = []

        # First pass: find all matching conditions
        for condition in oneof_data:
            if not isinstance(condition, dict):
                continue

            # Check if this condition matches our variant
            if self._matches_variant_condition(condition, variant):
                matching_conditions.append(condition)

        # Validate that exactly one condition matched
        if len(matching_conditions) == 0:
            supported_variants = self._get_supported_variants(base_schema)
            raise ValidationError(
                [
                    f"No matching oneOf condition found for {variant.engine} {variant.version}. "
                    f"Supported variants: {', '.join(supported_variants)}"
                ]
            )
        elif len(matching_conditions) > 1:
            raise ValidationError(
                [
                    f"Multiple matching conditions found for {variant.engine} {variant.version}. "
                    f"oneOf conditions should be mutually exclusive."
                ]
            )

        # Apply the single matching condition
        condition = matching_conditions[0]
        merged_schema = self._merge_condition_schema(result_schema, condition, variant)
        result_schema = merged_schema

        # Remove the oneOf block since we've resolved it
        if ONEOF_FIELD in result_schema:
            del result_schema[ONEOF_FIELD]

        return result_schema

    def _matches_variant_condition(
        self, condition: dict[str, Any], variant: DatabaseVariantSpec
    ) -> bool:
        """Check if a oneOf condition matches the given database variant."""
        if self._is_if_then_condition(condition):
            return self._matches_if_then_condition(condition, variant)
        if self._is_direct_properties_condition(condition):
            return self._matches_direct_properties_condition(condition, variant)
        return False

    def _is_if_then_condition(self, condition: dict[str, Any]) -> bool:
        return "if" in condition and isinstance(condition["if"], dict)

    def _matches_if_then_condition(
        self, condition: dict[str, Any], variant: DatabaseVariantSpec
    ) -> bool:
        if_condition = condition["if"]
        return self._check_if_condition_match(if_condition, variant)

    def _is_direct_properties_condition(self, condition: dict[str, Any]) -> bool:
        return "properties" in condition and isinstance(condition["properties"], dict)

    def _matches_direct_properties_condition(
        self, condition: dict[str, Any], variant: DatabaseVariantSpec
    ) -> bool:
        properties = condition["properties"]
        return self._check_properties_match(properties, variant)

    def _check_if_condition_match(
        self, if_condition: dict[str, Any], variant: DatabaseVariantSpec
    ) -> bool:
        """Check if an 'if' condition matches the variant.

        Args:
            if_condition: The if condition to evaluate
            variant: Database variant to match against

        Returns:
            True if condition matches, False otherwise
        """
        # Look for database properties in the if condition
        if "properties" not in if_condition:
            return False

        properties = if_condition["properties"]
        if not isinstance(properties, dict):
            return False

        # Check for database property constraints (nested style)
        if "database" in properties:
            db_props = properties["database"]
            if not isinstance(db_props, dict):
                return False

            if "properties" in db_props:
                db_properties = db_props["properties"]
                if isinstance(db_properties, dict):
                    return self._check_properties_match(db_properties, variant)

        # Check for direct property constraints (direct style)
        elif "engine" in properties or "version" in properties:
            return self._check_properties_match(properties, variant)

        return False

    def _check_properties_match(
        self, properties: dict[str, Any], variant: DatabaseVariantSpec
    ) -> bool:
        """Check if property constraints match the variant."""
        if not self._engine_matches(properties, variant.engine):
            return False
        if not self._version_matches(properties, variant.version):
            return False
        return True

    def _engine_matches(self, properties: dict[str, Any], engine: str) -> bool:
        if "engine" not in properties:
            return True
        engine_constraint = properties["engine"]
        if isinstance(engine_constraint, dict) and "const" in engine_constraint:
            const_val = engine_constraint["const"]
            return isinstance(const_val, str) and const_val == engine
        if isinstance(engine_constraint, str):
            return engine_constraint == engine
        return True

    def _version_matches(self, properties: dict[str, Any], version: str) -> bool:
        if "version" not in properties:
            return True
        version_constraint = properties["version"]
        if isinstance(version_constraint, dict) and "const" in version_constraint:
            const_val = version_constraint["const"]
            return isinstance(const_val, str) and const_val == version
        if isinstance(version_constraint, str):
            return version_constraint == version
        return True

    def _merge_condition_schema(
        self,
        base_schema: dict[str, Any],
        condition: dict[str, Any],
        variant: DatabaseVariantSpec,
    ) -> dict[str, Any]:
        """Merge a matching condition into the base schema.

        Args:
            base_schema: The base schema to merge into
            condition: The matching oneOf condition
            variant: Database variant being processed

        Returns:
            Merged schema with condition applied

        Raises:
            ValidationError: If merging fails
        """
        result_schema = dict(base_schema)

        # Handle if/then conditional structure
        if "then" in condition:
            then_clause = condition["then"]
            if not isinstance(then_clause, dict):
                return result_schema

            # If then clause has a $ref, resolve it first
            if REF_FIELD in then_clause:
                try:
                    resolved_then = self.resolver.resolve_references(then_clause)
                    result_schema = self._deep_merge_schemas(
                        result_schema, resolved_then
                    )
                except Exception as e:
                    raise ValidationError(
                        [f"Failed to resolve then clause reference: {e}"]
                    ) from e
            else:
                result_schema = self._deep_merge_schemas(result_schema, then_clause)

        # Handle direct property structure (database.json style)
        elif "properties" in condition:
            # For direct properties, just merge them in
            if "properties" not in result_schema:
                result_schema["properties"] = {}

            condition_props = condition["properties"]
            if isinstance(condition_props, dict):
                if isinstance(result_schema["properties"], dict):
                    result_schema["properties"] = self._deep_merge_schemas(
                        result_schema["properties"], condition_props
                    )

        return result_schema

    def _deep_merge_schemas(
        self, base: dict[str, Any], overlay: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge two schema dictionaries.

        Args:
            base: Base schema dictionary
            overlay: Schema dictionary to overlay

        Returns:
            Merged schema with overlay taking precedence
        """
        result = dict(base)

        for key, value in overlay.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge_schemas(result[key], value)
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    def _get_supported_variants(self, schema: dict[str, Any]) -> list[str]:
        """Extract supported variants from oneOf conditions for error reporting.

        Args:
            schema: Schema containing oneOf conditions

        Returns:
            List of supported variant strings in "Engine Version" format
        """
        variants: list[str] = []
        oneof_data = schema.get(ONEOF_FIELD, [])

        if not isinstance(oneof_data, list):
            return variants

        for condition in oneof_data:
            if not isinstance(condition, dict):
                continue

            # Try to extract variant info from different formats
            variant_info = self._extract_variant_from_condition(condition)
            if variant_info:
                variants.append(variant_info)

        return variants

    def _extract_variant_from_condition(self, condition: dict[str, Any]) -> str | None:
        """Extract variant string from a oneOf condition."""
        variant = self._extract_variant_from_if_then(condition)
        if variant is not None:
            return variant
        return self._extract_variant_from_direct_properties(condition)

    def _extract_variant_from_if_then(self, condition: dict[str, Any]) -> str | None:
        """Extract variant from if/then format."""
        if "if" in condition:
            if_condition = condition["if"]
            if isinstance(if_condition, dict) and "properties" in if_condition:
                if_props = if_condition["properties"]
                if isinstance(if_props, dict) and "database" in if_props:
                    db_props = if_props["database"]
                    if isinstance(db_props, dict) and "properties" in db_props:
                        db_properties = db_props["properties"]
                        if isinstance(db_properties, dict):
                            return self._extract_variant_from_properties(db_properties)
        return None

    def _extract_variant_from_direct_properties(
        self, condition: dict[str, Any]
    ) -> str | None:
        """Extract variant from direct properties format."""
        if "properties" in condition:
            props = condition["properties"]
            if isinstance(props, dict):
                return self._extract_variant_from_properties(props)
        return None

    def _extract_variant_from_properties(
        self, properties: dict[str, Any]
    ) -> str | None:
        """Extract variant from property constraints.

        Args:
            properties: Property constraints

        Returns:
            Variant string or None if not extractable
        """
        engine = None
        version = None

        # Extract engine
        if "engine" in properties:
            engine_prop = properties["engine"]
            if isinstance(engine_prop, dict) and "const" in engine_prop:
                const_val = engine_prop["const"]
                if isinstance(const_val, str):
                    engine = const_val

        # Extract version
        if "version" in properties:
            version_prop = properties["version"]
            if isinstance(version_prop, dict) and "const" in version_prop:
                const_val = version_prop["const"]
                if isinstance(const_val, str):
                    version = const_val

        if engine and version:
            return f"{engine} {version}"

        return None
