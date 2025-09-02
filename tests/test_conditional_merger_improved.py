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
        """Should not apply conditions for non-matching variant."""
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
