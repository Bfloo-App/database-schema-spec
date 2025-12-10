"""Database variant extraction from oneOf blocks."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from database_schema_spec.core.config import config
from database_schema_spec.core.exceptions import VariantExtractionError
from database_schema_spec.core.schemas import DatabaseVariantSpec
from database_schema_spec.resolution.resolver import JSONRefResolver


class VariantExtractor:
    """Extracts database variants from oneOf blocks in database schema files.

    This class parses oneOf conditional blocks to identify all supported
    database engine and version combinations.
    """

    def __init__(self, resolver: JSONRefResolver) -> None:
        """Initialize the variant extractor.

        Args:
            resolver: JSON reference resolver for loading schema files
        """
        self.resolver = resolver

    def extract_variants(self) -> list[DatabaseVariantSpec]:
        """Extract all database variants from the database registry file.

        Returns:
            List of DatabaseVariantSpec objects representing all variants

        Raises:
            VariantExtractionError: If variants cannot be extracted
        """
        try:
            # Load the database registry file
            database_schema = self.resolver.resolve_file(
                config.file_names.database_registry_file
            )

            # Extract oneOf items
            oneof_items = database_schema.get(config.json_schema_fields.oneof_field, [])
            if not isinstance(oneof_items, list):
                raise VariantExtractionError(
                    f"Invalid oneOf structure in {config.file_names.database_registry_file}"
                )

            # Parse each oneOf item to extract variants
            variants = self.parse_oneof_block(oneof_items)

            if not variants:
                raise VariantExtractionError(
                    f"No variants found in {config.file_names.database_registry_file}"
                )

            return variants

        except Exception as e:
            if isinstance(e, VariantExtractionError):
                raise
            raise VariantExtractionError(
                f"Failed to extract variants from {config.file_names.database_registry_file}: {e}"
            ) from e

    def parse_oneof_block(self, oneof_items: list[Any]) -> list[DatabaseVariantSpec]:
        """Parse oneOf items to extract database variants.

        Args:
            oneof_items: List of oneOf condition objects

        Returns:
            List of extracted DatabaseVariantSpec objects

        Raises:
            VariantExtractionError: If parsing fails
        """
        variants: list[DatabaseVariantSpec] = []

        for item in oneof_items:
            if not isinstance(item, dict):
                continue

            # Extract properties from the oneOf item
            properties = item.get("properties")
            if not isinstance(properties, dict):
                continue

            # Extract engine and version from properties
            engine = None
            version = None

            # Get engine constraint
            if "engine" in properties:
                engine_prop = properties["engine"]
                if isinstance(engine_prop, dict) and "const" in engine_prop:
                    const_value = engine_prop["const"]
                    if isinstance(const_value, str):
                        engine = const_value

            # Get version constraint
            if "version" in properties:
                version_prop = properties["version"]
                if isinstance(version_prop, dict) and "const" in version_prop:
                    const_value = version_prop["const"]
                    if isinstance(const_value, str):
                        version = const_value

            # Create variant if we have both engine and version
            if engine and version:
                try:
                    variant = DatabaseVariantSpec(
                        engine=engine, version=version, engine_spec_path=None
                    )
                    variants.append(variant)
                except ValidationError as e:
                    raise VariantExtractionError(
                        f"Invalid variant data - engine: {engine}, version: {version}: {e}"
                    ) from e

        return variants
