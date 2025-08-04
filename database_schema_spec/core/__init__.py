"""Core data models and shared types."""

from database_schema_spec.core.constants import (
    DATABASE_SCHEMA_FILE,
    DOCS_DIR,
    ERROR_CIRCULAR_REFERENCE,
    ERROR_FILE_NOT_FOUND,
    ERROR_FILE_SYSTEM,
    ERROR_INVALID_SCHEMA,
    ERROR_VALIDATION_FAILED,
    ID_FIELD,
    ONEOF_FIELD,
    OUTPUT_DIR,
    REF_FIELD,
    ROOT_SCHEMA_FILE,
    SCHEMA_FIELD,
    SUCCESS,
)
from database_schema_spec.core.exceptions import (
    CircularReferenceError,
    ReferenceResolutionError,
    SchemaGenerationError,
    ValidationError,
    VariantExtractionError,
)
from database_schema_spec.core.schemas import DatabaseVariantSpec, ValidationResult

__all__ = [
    "DatabaseVariantSpec",
    "ValidationResult",
    "SchemaGenerationError",
    "ReferenceResolutionError",
    "CircularReferenceError",
    "VariantExtractionError",
    "ValidationError",
    "DOCS_DIR",
    "OUTPUT_DIR",
    "ROOT_SCHEMA_FILE",
    "DATABASE_SCHEMA_FILE",
    "REF_FIELD",
    "ONEOF_FIELD",
    "SCHEMA_FIELD",
    "ID_FIELD",
    "SUCCESS",
    "ERROR_FILE_NOT_FOUND",
    "ERROR_INVALID_SCHEMA",
    "ERROR_CIRCULAR_REFERENCE",
    "ERROR_VALIDATION_FAILED",
    "ERROR_FILE_SYSTEM",
]
