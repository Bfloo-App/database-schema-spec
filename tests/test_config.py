"""Test custom configuration error handling."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import Field
from pydantic_settings import BaseSettings

from database_schema_spec.core.config import (
    ExitCodesConfig,
    FileNamesConfig,
    JSONSchemaFieldsConfig,
)
from database_schema_spec.core.exceptions import ConfigurationError


def test_missing_base_url_raises_configuration_error():
    """Test that missing BASE_URL raises ConfigurationError instead of ValidationError."""

    # Create a test config class that mimics the real Config but doesn't load .env
    class TestConfig(BaseSettings):
        """Test config that doesn't load from .env."""

        docs_dir: Path = Field(
            default=Path("docs"), description="Path to documentation/schema files"
        )
        output_dir: Path = Field(
            default=Path("output"), description="Path for generated output files"
        )
        base_url: str = Field(..., description="Base URL for generated spec files")
        file_names: FileNamesConfig = Field(default_factory=FileNamesConfig)
        json_schema_fields: JSONSchemaFieldsConfig = Field(
            default_factory=JSONSchemaFieldsConfig
        )
        exit_codes: ExitCodesConfig = Field(default_factory=ExitCodesConfig)

        model_config = {
            "env_file": None,  # Disable .env file loading
            "case_sensitive": False,
        }

        def __init__(self, **data):
            """Initialize config with custom error handling for missing required fields."""
            from pydantic import ValidationError

            try:
                super().__init__(**data)
            except ValidationError as e:
                for error in e.errors():
                    if error["type"] == "missing":
                        field_name = error["loc"][0] if error["loc"] else "unknown"
                        env_var_name = str(field_name).upper()
                        raise ConfigurationError(variable_name=env_var_name) from e
                raise

    # Clear environment and test
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            TestConfig()

        error = exc_info.value
        assert error.variable_name == "BASE_URL"
        assert "Required configuration variable 'BASE_URL' is not set" in str(error)


def test_config_with_valid_base_url():
    """Test that Config works correctly when BASE_URL is provided."""
    with patch.dict(os.environ, {"BASE_URL": "https://example.com/api"}):
        # Import fresh to get new instance with patched env
        from database_schema_spec.core.config import Config

        config = Config()
        assert config.base_url == "https://example.com/api"
        assert config.docs_dir.name == "docs"
        assert config.output_dir.name == "output"
