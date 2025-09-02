"""Main class that orchestrates the schema generation process."""

from __future__ import annotations

import sys
from pathlib import Path

from database_schema_spec.core.config import config
from database_schema_spec.core.exceptions import SchemaGenerationError, ValidationError
from database_schema_spec.core.schemas import DatabaseVariantSpec
from database_schema_spec.io.output_manager import OutputManager
from database_schema_spec.logger import logger, setup_logger
from database_schema_spec.resolution.conditional_merger import ConditionalMerger
from database_schema_spec.resolution.resolver import JSONRefResolver
from database_schema_spec.resolution.variant_extractor import VariantExtractor
from database_schema_spec.validation.schema_validator import SchemaValidator


class SchemaGenerator:
    """Main class that orchestrates the schema generation process.

    This class coordinates all components to extract database variants,
    resolve references, apply conditional logic, and generate final schemas.
    """

    def __init__(
        self, docs_path: Path = config.docs_dir, output_path: Path = config.output_dir
    ) -> None:
        """Initialize the schema generator.

        Args:
            docs_path: Path to documentation/schema files
            output_path: Path for generated output files
        """
        self.docs_path = docs_path
        self.output_path = output_path
        self.resolver = JSONRefResolver(docs_path)
        self.variant_extractor = VariantExtractor(self.resolver)
        self.output_manager = OutputManager(output_path)
        self.validator = SchemaValidator()

    def run(self) -> None:
        """Run the complete schema generation process.

        Raises:
            SystemExit: If any critical error occurs during generation
        """
        try:
            setup_logger()
            logger.info("Generating database schema specifications...")
            generated_files = self.generate_all_variants()
            logger.info(
                "Generation completed successfully! Generated %d unified schema file(s).",
                len(generated_files),
            )
        except SchemaGenerationError as e:
            logger.error("Schema generation error: %s", e, exc_info=True)
            sys.exit(config.exit_codes.error_invalid_schema)
        except FileNotFoundError as e:
            logger.error("Missing required input file: %s", e, exc_info=True)
            sys.exit(config.exit_codes.error_file_not_found)
        except Exception:
            logger.exception("Unexpected error occurred")
            sys.exit(config.exit_codes.error_file_system)

    def run_for_testing(self) -> list[Path]:
        """Run the complete schema generation process for testing.

        Unlike run(), this method raises exceptions instead of calling sys.exit(),
        making it suitable for unit tests.

        Returns:
            List of paths where schemas were written

        Raises:
            SchemaGenerationError: If any critical error occurs during generation
            FileNotFoundError: If required input files are missing
        """
        logger.info("Generating database schema specifications...")
        generated_files = self.generate_all_variants()
        return generated_files

    def generate_all_variants(self) -> list[Path]:
        """Generate unified schemas for all database variants.

        Returns:
            List of paths where schemas were written
        """
        # Create output directory structure
        self.output_manager.create_output_structure()

        # Extract all database variants
        variants = self.variant_extractor.extract_variants()

        # Generate schema for each variant
        generated_files: list[Path] = []
        for variant in variants:
            logger.info("Generating schema for %s", variant)
            file_path = self.generate_variant(variant)
            generated_files.append(file_path)

        # Generate version map after all variants are created
        logger.info("Generating version map...")
        vmap_path = self.output_manager.write_version_map(config.base_url)
        generated_files.append(vmap_path)
        logger.info("Version map written to: %s", vmap_path)

        return generated_files

    def generate_variant(self, variant: DatabaseVariantSpec) -> Path:
        """Generate unified schema for a specific database variant.

        Args:
            variant: Database variant to generate schema for

        Returns:
            Path where the schema was written
        """
        # Create a variant-aware resolver for this specific variant
        variant_resolver = JSONRefResolver(self.docs_path, variant)

        # Create variant-aware conditional merger
        variant_conditional_merger = ConditionalMerger(variant_resolver)

        # Load the root schema with variant-aware resolution
        base_schema = variant_resolver.resolve_file(config.file_names.root_schema_file)

        # Apply conditional logic for this variant
        unified_schema = variant_conditional_merger.apply_conditional_logic(
            base_schema, variant
        )

        # Inject dynamic $id derived from BASE_URL for the final output
        id_field = config.json_schema_fields.id_field
        schema_field = config.json_schema_fields.schema_field
        spec_url = self.output_manager._get_spec_url(
            variant.engine, variant.version, config.base_url
        )
        # Set/override $id
        unified_schema[id_field] = spec_url

        # Reorder top-level keys to ensure `$id` appears immediately after `$schema` when present
        if isinstance(unified_schema, dict):
            reordered: dict[str, object] = {}
            # If $schema exists, place it first
            if schema_field in unified_schema:
                reordered[schema_field] = unified_schema[schema_field]
                reordered[id_field] = unified_schema[id_field]
                for k, v in unified_schema.items():
                    if k not in (schema_field, id_field):
                        reordered[k] = v
                unified_schema = reordered  # type: ignore[assignment]
            else:
                # If no $schema, put $id first then the rest in original order
                reordered[id_field] = unified_schema[id_field]
                for k, v in unified_schema.items():
                    if k != id_field:
                        reordered[k] = v
                unified_schema = reordered  # type: ignore[assignment]

        # Validate the resulting schema
        validation_result = self.validator.validate_schema(unified_schema)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)

        # Write the schema to output file
        output_path = self.output_manager.write_schema(
            unified_schema, variant.engine, variant.version
        )

        return output_path
