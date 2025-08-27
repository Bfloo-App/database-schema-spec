"""Configuration constants for the database schema spec generator."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from pydantic_settings import BaseSettings

from .exceptions import ConfigurationError


class FileNamesConfig(BaseModel):
    """Configuration for file names."""

    root_schema_file: str = "specs.json"
    database_schema_file: str = "schemas/base/database.json"


class JSONSchemaFieldsConfig(BaseModel):
    """Configuration for JSON Schema field names."""

    ref_field: str = "$ref"
    oneof_field: str = "oneOf"
    schema_field: str = "$schema"
    id_field: str = "$id"


class ExitCodesConfig(BaseModel):
    """Configuration for exit codes."""

    success: int = 0
    error_file_not_found: int = 1
    error_invalid_schema: int = 2
    error_circular_reference: int = 3
    error_validation_failed: int = 4
    error_file_system: int = 5


class Config(BaseSettings):
    """Main configuration class for the database schema spec generator."""

    # Directory paths
    docs_dir: Path = Field(
        default=Path("docs"), description="Path to documentation/schema files"
    )
    output_dir: Path = Field(
        default=Path("output"), description="Path for generated output files"
    )

    # Base URL for generated spec files (required from environment)
    base_url: str = Field(..., description="Base URL for generated spec files")

    # Nested configurations
    file_names: FileNamesConfig = Field(default_factory=FileNamesConfig)
    json_schema_fields: JSONSchemaFieldsConfig = Field(
        default_factory=JSONSchemaFieldsConfig
    )
    exit_codes: ExitCodesConfig = Field(default_factory=ExitCodesConfig)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    def __init__(self, **data):
        """Initialize config with custom error handling for missing required fields."""
        try:
            # Enforce presence of required env variables in the process environment
            # before delegating to BaseSettings. This ensures tests that clear os.environ
            # see the expected ConfigurationError.
            if "base_url" not in data and "BASE_URL" not in os.environ:
                raise ConfigurationError(variable_name="BASE_URL")

            super().__init__(**data)
        except ValidationError as e:
            # Only handle missing field errors, let other validation errors bubble up
            for error in e.errors():
                if error["type"] == "missing":
                    field_name = error["loc"][0] if error["loc"] else "unknown"
                    # Convert field name to environment variable name format
                    env_var_name = str(field_name).upper()
                    raise ConfigurationError(
                        variable_name=env_var_name,
                    ) from e
            # Re-raise the original ValidationError for non-missing errors
            raise


# At application import time, populate os.environ from .env (if present), then enforce presence.
load_dotenv()
config = Config()
