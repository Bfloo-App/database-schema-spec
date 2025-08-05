"""Core data models and shared types."""

from database_schema_spec.core.config import config
from database_schema_spec.core.exceptions import (
    CircularReferenceError,
    ConfigurationError,
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
    "ConfigurationError",
    "VariantExtractionError",
    "ValidationError",
    "config",
]
