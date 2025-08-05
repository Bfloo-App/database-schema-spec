"""Production-quality test fixtures and configuration."""

# Set test environment variables BEFORE any imports that might trigger config loading
import os  # noqa: E402

os.environ.setdefault("BASE_URL", "https://test.example.com/schemas")

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock

import pytest

from database_schema_spec.core.schemas import DatabaseVariantSpec
from database_schema_spec.resolution.interfaces import IJSONRefResolver


def pytest_configure(config):
    """Configure pytest environment before any imports happen."""
    # Environment variable is already set at module level above
    pass


@pytest.fixture(scope="session", autouse=True)
def mock_config():
    """Ensure config uses test environment variables."""
    # At this point, the config should already be loaded with our test env vars
    # This fixture just serves as a placeholder for future config customization
    yield


@pytest.fixture
def temp_docs_dir():
    """Create a temporary docs directory with realistic test data."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create directory structure
    (temp_dir / "schemas" / "base").mkdir(parents=True)
    (temp_dir / "schemas" / "engines" / "postgresql" / "v15.0").mkdir(parents=True)
    (temp_dir / "schemas" / "engines" / "mysql" / "v8.0").mkdir(parents=True)

    # Create database.json with oneOf conditions (this is what the variant extractor expects)
    database_schema = {
        "title": "Database Configuration",
        "type": "object",
        "required": ["engine", "version"],
        "additionalProperties": False,
        "oneOf": [
            {
                "properties": {
                    "engine": {
                        "type": "string",
                        "description": "The type of database engine used",
                        "const": "postgresql",
                    },
                    "version": {
                        "type": "string",
                        "description": "The version of the PostgreSQL database engine",
                        "const": "15.0",
                    },
                }
            },
            {
                "properties": {
                    "engine": {
                        "type": "string",
                        "description": "The type of database engine used",
                        "const": "mysql",
                    },
                    "version": {
                        "type": "string",
                        "description": "The version of the MySQL database engine",
                        "const": "8.0",
                    },
                }
            },
        ],
    }

    # Create a simple schema.json for references
    schema_schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
        "required": ["name"],
    }

    # Write test files - database.json should contain the oneOf schema
    with open(temp_dir / "schemas" / "base" / "database.json", "w") as f:
        json.dump(database_schema, f, indent=2)

    with open(temp_dir / "schemas" / "base" / "schema.json", "w") as f:
        json.dump(schema_schema, f, indent=2)

    # Create engine-specific schema directories and files
    # PostgreSQL v15.0
    postgresql_dir = temp_dir / "schemas" / "engines" / "postgresql" / "v15.0"

    with open(postgresql_dir / "spec.json", "w") as f:
        json.dump(
            {
                "title": "PostgreSQL 15.0 Schema Rules",
                "properties": {
                    "postgres_features": {
                        "type": "object",
                        "description": "PostgreSQL-specific features",
                    }
                },
            },
            f,
            indent=2,
        )

    # MySQL v8.0
    mysql_dir = temp_dir / "schemas" / "engines" / "mysql" / "v8.0"

    with open(mysql_dir / "spec.json", "w") as f:
        json.dump(
            {
                "title": "MySQL 8.0 Schema Rules",
                "properties": {
                    "mysql_features": {
                        "type": "object",
                        "description": "MySQL-specific features",
                    }
                },
            },
            f,
            indent=2,
        )

    with open(temp_dir / "specs.json", "w") as f:
        json.dump(
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "title": "Database Schema Specification Test",
                "description": "Test schema specification",
                "type": "object",
                "properties": {
                    "database": {"$ref": "schemas/base/database.json"},
                    "schema": {"$ref": "schemas/base/schema.json"},
                },
                "required": ["database", "schema"],
                "additionalProperties": False,
                "variants": [
                    {"engine": "postgresql", "version": "15.0"},
                    {"engine": "mysql", "version": "8.0"},
                ],
            },
            f,
            indent=2,
        )

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def postgresql_variant():
    """Standard PostgreSQL variant for testing."""
    return DatabaseVariantSpec(
        engine="postgresql",
        version="15.0",
        engine_spec_path="schemas/engines/postgresql/v15.0",
    )


@pytest.fixture
def mysql_variant():
    """MySQL variant for testing."""
    return DatabaseVariantSpec(
        engine="mysql", version="8.0", engine_spec_path="schemas/engines/mysql/v8.0"
    )


@pytest.fixture
def mock_resolver():
    """Mock resolver that implements the interface properly."""
    mock = Mock(spec=IJSONRefResolver)
    mock.resolve_references.return_value = {}
    return mock


class SchemaTestHelper:
    """Helper class for creating test schemas."""

    @staticmethod
    def create_conditional_schema(
        engine: str, version: str, then_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a conditional schema for testing."""
        return {
            "oneOf": [
                {
                    "if": {
                        "properties": {
                            "database": {
                                "properties": {
                                    "engine": {"const": engine},
                                    "version": {"const": version},
                                }
                            }
                        }
                    },
                    "then": {"properties": then_properties},
                }
            ]
        }

    @staticmethod
    def create_direct_conditional_schema(
        engine: str, version: str, then_properties: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a direct conditional schema (database.json style)."""
        return {
            "oneOf": [
                {
                    "if": {
                        "properties": {
                            "engine": {"const": engine},
                            "version": {"const": version},
                        }
                    },
                    "then": {"properties": then_properties},
                }
            ]
        }

    @staticmethod
    def create_invalid_schema() -> Dict[str, Any]:
        """Create an invalid schema for error testing."""
        return {
            "oneOf": [
                {
                    "if": "invalid_structure",  # Should be object
                    "then": {"type": "object"},
                }
            ]
        }

    @staticmethod
    def create_multiple_match_schema() -> Dict[str, Any]:
        """Create a schema that would match multiple conditions."""
        return {
            "oneOf": [
                {
                    "if": {
                        "properties": {
                            "database": {
                                "properties": {"engine": {"const": "postgresql"}}
                            }
                        }
                    },
                    "then": {"properties": {"feature1": {"type": "string"}}},
                },
                {
                    "if": {
                        "properties": {
                            "database": {"properties": {"version": {"const": "15.0"}}}
                        }
                    },
                    "then": {"properties": {"feature2": {"type": "integer"}}},
                },
            ]
        }


@pytest.fixture
def schema_helper():
    """Provide schema helper for tests."""
    return SchemaTestHelper()
