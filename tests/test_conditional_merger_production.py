"""Production-quality tests for ConditionalMerger."""

import pytest

from database_schema_spec.core.exceptions import ValidationError
from database_schema_spec.resolution.conditional_merger import ConditionalMerger


class TestConditionalMerger:
    """Test ConditionalMerger public interface with comprehensive coverage."""

    def test_apply_conditional_logic_matching_postgresql(
        self, mock_resolver, postgresql_variant, schema_helper
    ):
        """Should apply conditions for matching PostgreSQL variant."""
        merger = ConditionalMerger(mock_resolver)

        base_schema = schema_helper.create_conditional_schema(
            engine="postgresql",
            version="15.0",
            then_properties={"id": {"type": "integer", "format": "int4"}},
        )

        result = merger.apply_conditional_logic(base_schema, postgresql_variant)

        # Should contain the then properties
        assert "properties" in result
        assert "id" in result["properties"]
        assert result["properties"]["id"]["format"] == "int4"
        # Should not contain oneOf anymore (resolved)
        assert "oneOf" not in result

    def test_apply_conditional_logic_non_matching_variant(
        self, mock_resolver, mysql_variant, schema_helper
    ):
        """Should raise ValidationError for non-matching variant."""
        merger = ConditionalMerger(mock_resolver)

        base_schema = schema_helper.create_conditional_schema(
            engine="postgresql",
            version="15.0",
            then_properties={"postgres_column": {"type": "string"}},
        )

        with pytest.raises(ValidationError, match="No matching oneOf condition found"):
            merger.apply_conditional_logic(base_schema, mysql_variant)

    def test_apply_conditional_logic_no_oneof(self, mock_resolver, postgresql_variant):
        """Should return schema unchanged when no oneOf present."""
        merger = ConditionalMerger(mock_resolver)

        base_schema = {"type": "object", "properties": {"name": {"type": "string"}}}

        result = merger.apply_conditional_logic(base_schema, postgresql_variant)

        assert result == base_schema

    def test_apply_conditional_logic_empty_oneof(
        self, mock_resolver, postgresql_variant
    ):
        """Should handle empty oneOf arrays."""
        merger = ConditionalMerger(mock_resolver)

        base_schema = {"oneOf": []}

        result = merger.apply_conditional_logic(base_schema, postgresql_variant)

        assert result == base_schema

    def test_apply_conditional_logic_invalid_condition_structure(
        self, mock_resolver, postgresql_variant, schema_helper
    ):
        """Should raise ValidationError for invalid condition structure."""
        merger = ConditionalMerger(mock_resolver)

        invalid_schema = schema_helper.create_invalid_schema()

        with pytest.raises(ValidationError):
            merger.apply_conditional_logic(invalid_schema, postgresql_variant)

    def test_apply_conditional_logic_multiple_matches_error(
        self, mock_resolver, postgresql_variant, schema_helper
    ):
        """Should raise ValidationError when multiple conditions match."""
        merger = ConditionalMerger(mock_resolver)

        schema_with_multiple_matches = schema_helper.create_multiple_match_schema()

        with pytest.raises(ValidationError, match="Multiple matching conditions"):
            merger.apply_conditional_logic(
                schema_with_multiple_matches, postgresql_variant
            )

    @pytest.mark.parametrize(
        "engine,version,expected_property",
        [
            ("postgresql", "15.0", "bigint_support"),
            ("postgresql", "14.0", "json_support"),
            ("mysql", "8.0", "mysql_specific"),
        ],
    )
    def test_apply_conditional_logic_multiple_variants(
        self, mock_resolver, engine, version, expected_property, schema_helper
    ):
        """Should correctly resolve conditions for different variants."""
        from database_schema_spec.core.schemas import DatabaseVariantSpec

        variant = DatabaseVariantSpec(
            engine=engine, version=version, engine_spec_path=None
        )
        merger = ConditionalMerger(mock_resolver)

        multi_variant_schema = {
            "oneOf": [
                {
                    "if": {
                        "properties": {
                            "database": {
                                "properties": {
                                    "engine": {"const": "postgresql"},
                                    "version": {"const": "15.0"},
                                }
                            }
                        }
                    },
                    "then": {"properties": {"bigint_support": {"type": "boolean"}}},
                },
                {
                    "if": {
                        "properties": {
                            "database": {
                                "properties": {
                                    "engine": {"const": "postgresql"},
                                    "version": {"const": "14.0"},
                                }
                            }
                        }
                    },
                    "then": {"properties": {"json_support": {"type": "boolean"}}},
                },
                {
                    "if": {
                        "properties": {
                            "database": {"properties": {"engine": {"const": "mysql"}}}
                        }
                    },
                    "then": {"properties": {"mysql_specific": {"type": "string"}}},
                },
            ]
        }

        result = merger.apply_conditional_logic(multi_variant_schema, variant)

        assert expected_property in result["properties"]

    def test_apply_conditional_logic_preserves_original_properties(
        self, mock_resolver, postgresql_variant
    ):
        """Should preserve original schema properties when merging conditions."""
        merger = ConditionalMerger(mock_resolver)

        base_schema = {
            "type": "object",
            "properties": {"existing_prop": {"type": "string"}},
            "oneOf": [
                {
                    "if": {
                        "properties": {
                            "database": {
                                "properties": {"engine": {"const": "postgresql"}}
                            }
                        }
                    },
                    "then": {"properties": {"new_prop": {"type": "integer"}}},
                }
            ],
        }

        result = merger.apply_conditional_logic(base_schema, postgresql_variant)

        # Should have both original and new properties
        assert "existing_prop" in result["properties"]
        assert "new_prop" in result["properties"]
        assert result["type"] == "object"

    def test_apply_conditional_logic_with_nested_refs(self, postgresql_variant):
        """Should handle schemas with nested $ref resolution."""
        from unittest.mock import Mock

        mock_resolver = Mock()
        mock_resolver.resolve_references.return_value = {
            "properties": {"resolved_prop": {"type": "string"}}
        }

        merger = ConditionalMerger(mock_resolver)

        schema_with_ref = {
            "oneOf": [
                {
                    "if": {
                        "properties": {
                            "database": {
                                "properties": {"engine": {"const": "postgresql"}}
                            }
                        }
                    },
                    "then": {"$ref": "nested_schema.json"},
                }
            ]
        }

        result = merger.apply_conditional_logic(schema_with_ref, postgresql_variant)

        # Should have called resolver for the $ref
        mock_resolver.resolve_references.assert_called_once()
        assert "resolved_prop" in result["properties"]

    def test_apply_conditional_logic_direct_properties_style(
        self, mock_resolver, postgresql_variant, schema_helper
    ):
        """Should handle direct properties style conditions (database.json style)."""
        merger = ConditionalMerger(mock_resolver)

        # This is the style used in database.json where if/then is at the top level
        direct_schema = schema_helper.create_direct_conditional_schema(
            engine="postgresql",
            version="15.0",
            then_properties={"postgres_column": {"type": "bigint"}},
        )

        result = merger.apply_conditional_logic(direct_schema, postgresql_variant)

        assert "properties" in result
        assert "postgres_column" in result["properties"]
        assert result["properties"]["postgres_column"]["type"] == "bigint"
