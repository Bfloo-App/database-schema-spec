"""Configuration constants for the database schema spec generator."""

from pathlib import Path

# Directory paths
DOCS_DIR = Path("docs")
OUTPUT_DIR = Path("output")

# File names
ROOT_SCHEMA_FILE = "specs.json"
DATABASE_SCHEMA_FILE = "schemas/base/database.json"

# JSON Schema field names
REF_FIELD = "$ref"
ONEOF_FIELD = "oneOf"
SCHEMA_FIELD = "$schema"
ID_FIELD = "$id"

# Exit codes
SUCCESS = 0
ERROR_FILE_NOT_FOUND = 1
ERROR_INVALID_SCHEMA = 2
ERROR_CIRCULAR_REFERENCE = 3
ERROR_VALIDATION_FAILED = 4
ERROR_FILE_SYSTEM = 5
