"""JSON Schema reference resolution components."""

from database_schema_spec.resolution.conditional_merger import ConditionalMerger
from database_schema_spec.resolution.resolver import JSONRefResolver
from database_schema_spec.resolution.variant_extractor import VariantExtractor

__all__ = ["JSONRefResolver", "VariantExtractor", "ConditionalMerger"]
