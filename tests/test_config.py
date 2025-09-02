"""Test custom configuration error handling."""

import os
from unittest.mock import patch

import pytest

from database_schema_spec.core.config import Config
from database_schema_spec.core.exceptions import ConfigurationError


def test_missing_base_url_raises_configuration_error():
    """Test that missing BASE_URL raises ConfigurationError instead of ValidationError."""
    # Remove BASE_URL from environment for this test
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfigurationError) as exc_info:
            Config()

        error = exc_info.value
        assert error.variable_name == "BASE_URL"
        assert "Required configuration variable 'BASE_URL' is not set" in str(error)


def test_config_with_valid_base_url():
    """Test that Config works correctly when BASE_URL is provided."""
    with patch.dict(os.environ, {"BASE_URL": "https://example.com/api"}):
        config = Config()
        assert config.base_url == "https://example.com/api"
        assert config.docs_dir.name == "docs"
        assert config.output_dir.name == "output"
