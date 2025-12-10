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

    # Create directory structure matching new architecture
    (temp_dir / "schemas" / "project" / "config" / "engines").mkdir(parents=True)
    (temp_dir / "schemas" / "engines" / "postgresql" / "v15.0").mkdir(parents=True)
    (temp_dir / "schemas" / "engines" / "mysql" / "v8.0").mkdir(parents=True)

    # Create _registry_.json (engine/version registry using oneOf format)
    registry = {
        "$comment": "Registry of supported database engine/version combinations.",
        "title": "Database Engine Registry",
        "oneOf": [
            {
                "properties": {
                    "engine": {"const": "PostgreSQL"},
                    "version": {"const": "v15.0"},
                }
            },
            {
                "properties": {
                    "engine": {"const": "MySQL"},
                    "version": {"const": "v8.0"},
                }
            },
        ],
    }

    with open(temp_dir / "schemas" / "_registry_.json", "w") as f:
        json.dump(registry, f, indent=2)

    # Create base config schema
    base_config = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Base Project Configuration",
        "type": "object",
        "properties": {
            "schema_id": {"type": "string", "format": "uuid"},
            "database": {
                "type": "object",
                "properties": {"engine": {"type": "string"}},
                "required": ["engine"],
            },
        },
        "required": ["database"],
    }

    with open(temp_dir / "schemas" / "project" / "config" / "base.json", "w") as f:
        json.dump(base_config, f, indent=2)

    # Create PostgreSQL config schema
    postgresql_config = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "PostgreSQL Configuration",
        "type": "object",
        "properties": {
            "environments": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "dbname": {"type": "string"},
                        "user": {"type": "string"},
                    },
                    "required": ["host", "dbname", "user"],
                },
            }
        },
        "required": ["environments"],
    }

    with open(
        temp_dir / "schemas" / "project" / "config" / "engines" / "postgresql.json", "w"
    ) as f:
        json.dump(postgresql_config, f, indent=2)

    # Create MySQL config schema
    mysql_config = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "MySQL Configuration",
        "type": "object",
        "properties": {
            "environments": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer"},
                        "database": {"type": "string"},
                        "user": {"type": "string"},
                    },
                    "required": ["host", "database", "user"],
                },
            }
        },
        "required": ["environments"],
    }

    with open(
        temp_dir / "schemas" / "project" / "config" / "engines" / "mysql.json", "w"
    ) as f:
        json.dump(mysql_config, f, indent=2)

    # Create manifest schema
    manifest_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Snapshot Manifest",
        "type": "object",
        "properties": {"current": {"type": "string"}, "snapshots": {"type": "array"}},
        "required": ["current", "snapshots"],
    }

    with open(temp_dir / "schemas" / "project" / "manifest.json", "w") as f:
        json.dump(manifest_schema, f, indent=2)

    # Create PostgreSQL v15.0 spec
    postgresql_spec = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "PostgreSQL 15.0 Schema",
        "type": "object",
        "properties": {"name": {"type": "string"}, "tables": {"type": "array"}},
        "required": ["name"],
    }

    with open(
        temp_dir / "schemas" / "engines" / "postgresql" / "v15.0" / "spec.json", "w"
    ) as f:
        json.dump(postgresql_spec, f, indent=2)

    # Create MySQL v8.0 spec
    mysql_spec = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "MySQL 8.0 Schema",
        "type": "object",
        "properties": {"name": {"type": "string"}, "tables": {"type": "array"}},
        "required": ["name"],
    }

    with open(
        temp_dir / "schemas" / "engines" / "mysql" / "v8.0" / "spec.json", "w"
    ) as f:
        json.dump(mysql_spec, f, indent=2)

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
