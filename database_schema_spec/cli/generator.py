"""Main class that orchestrates the schema generation process."""

from __future__ import annotations

import sys
from pathlib import Path

from database_schema_spec.core.config import config
from database_schema_spec.core.exceptions import SchemaGenerationError, ValidationError
from database_schema_spec.core.schemas import DatabaseVariantSpec
from database_schema_spec.io.output_manager import OutputManager
from database_schema_spec.logger import logger, setup_logger
from database_schema_spec.resolution.resolver import JSONRefResolver
from database_schema_spec.resolution.variant_extractor import VariantExtractor
from database_schema_spec.validation.schema_validator import SchemaValidator


class SchemaGenerator:
    """Main class that orchestrates the schema generation process.

    This class coordinates all components to extract database variants,
    resolve references, and generate final schemas for each engine/version.
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
        self.output_manager = OutputManager(output_path, docs_path)
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
                "Generation completed successfully! Generated %d file(s).",
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

        # Extract all database variants from registry
        variants = self.variant_extractor.extract_variants()

        # Collect unique engine names for config generation
        engines: list[str] = list({v.engine for v in variants})

        # Generate schema for each variant
        generated_files: list[Path] = []
        for variant in variants:
            logger.info("Generating schema for %s %s", variant.engine, variant.version)
            file_path = self.generate_variant(variant)
            generated_files.append(file_path)

        # Generate project schemas
        logger.info("Generating project schemas...")

        # Generate base config schema
        base_config_path = self.output_manager.write_project_schema(
            config.file_names.project_config_base_schema,
            "config/base.json",
            config.base_url,
        )
        generated_files.append(base_config_path)
        logger.info("Base config schema written to: %s", base_config_path)

        # Generate engine-specific config schemas
        for engine in engines:
            engine_lower = engine.lower()
            source_path = config.file_names.project_config_engine_pattern.format(
                engine=engine_lower
            )
            output_path = f"config/engines/{engine_lower}.json"
            engine_config_path = self.output_manager.write_project_schema(
                source_path, output_path, config.base_url
            )
            generated_files.append(engine_config_path)
            logger.info(
                "Engine config schema for %s written to: %s", engine, engine_config_path
            )

        # Generate manifest schema
        manifest_path = self.output_manager.write_project_schema(
            config.file_names.project_manifest_schema, "manifest.json", config.base_url
        )
        generated_files.append(manifest_path)
        logger.info("Manifest schema written to: %s", manifest_path)

        # Generate schema map after all files are created
        logger.info("Generating schema map...")
        smap_path = self.output_manager.write_schema_map(engines, config.base_url)
        generated_files.append(smap_path)
        logger.info("Schema map written to: %s", smap_path)

        return generated_files

    def generate_variant(self, variant: DatabaseVariantSpec) -> Path:
        """Generate unified schema for a specific database variant.

        Args:
            variant: Database variant to generate schema for

        Returns:
            Path where the schema was written
        """
        # Build path to engine-specific spec file
        spec_path = config.file_names.engine_spec_pattern.format(
            engine=variant.engine.lower(),
            version=variant.version,
        )

        # Create a variant-aware resolver and load the spec directly
        variant_resolver = JSONRefResolver(self.docs_path, variant)
        unified_schema = variant_resolver.resolve_file(spec_path)

        # Inject dynamic $id derived from BASE_URL for the final output
        id_field = config.json_schema_fields.id_field
        schema_field = config.json_schema_fields.schema_field
        spec_url = self.output_manager._get_spec_url(
            variant.engine, variant.version, config.base_url
        )

        # Set/override $id
        unified_schema[id_field] = spec_url

        # Reorder top-level keys to ensure `$id` appears immediately after `$schema`
        unified_schema = self._reorder_schema_keys(
            unified_schema, id_field, schema_field
        )

        # Validate the resulting schema
        validation_result = self.validator.validate_schema(unified_schema)
        if not validation_result.is_valid:
            raise ValidationError(validation_result.errors)

        # Write the schema to output file
        output_path = self.output_manager.write_schema(
            unified_schema, variant.engine, variant.version
        )

        return output_path

    def _reorder_schema_keys(
        self, schema: dict, id_field: str, schema_field: str
    ) -> dict:
        """Reorder schema keys to put $schema and $id first.

        Args:
            schema: Schema dictionary to reorder
            id_field: Name of the $id field
            schema_field: Name of the $schema field

        Returns:
            Reordered schema dictionary
        """
        if not isinstance(schema, dict):
            return schema

        reordered: dict[str, object] = {}

        # If $schema exists, place it first, then $id
        if schema_field in schema:
            reordered[schema_field] = schema[schema_field]
            reordered[id_field] = schema[id_field]
            for k, v in schema.items():
                if k not in (schema_field, id_field):
                    reordered[k] = v
        else:
            # If no $schema, put $id first then the rest
            reordered[id_field] = schema[id_field]
            for k, v in schema.items():
                if k != id_field:
                    reordered[k] = v

        return reordered
