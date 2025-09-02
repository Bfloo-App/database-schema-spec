"""Custom exception classes for the database schema spec generator."""

from __future__ import annotations


class SchemaGenerationError(Exception):
    """Base exception for schema generation errors.

    All custom exceptions in the database schema spec generator inherit from this class.
    """

    pass


class ReferenceResolutionError(SchemaGenerationError):
    """Error during JSON reference resolution.

    Raised when a JSON reference ($ref) cannot be resolved to a valid schema.

    Args:
        ref_path: The reference path that failed to resolve
        cause: The underlying exception that caused the resolution failure
    """

    def __init__(self, ref_path: str, cause: Exception) -> None:
        self.ref_path = ref_path
        self.cause = cause
        super().__init__(f"Failed to resolve reference '{ref_path}': {cause}")


class CircularReferenceError(SchemaGenerationError):
    """Error when circular reference detected.

    Raised when a circular dependency is detected in JSON references,
    which would cause infinite recursion during resolution.

    Args:
        reference_chain: List of references showing the circular dependency path
    """

    def __init__(self, reference_chain: list[str]) -> None:
        self.reference_chain = reference_chain
        super().__init__(f"Circular reference detected: {' -> '.join(reference_chain)}")


class VariantExtractionError(SchemaGenerationError):
    """Error during database variant extraction.

    Raised when database-specific variants cannot be extracted from conditional schemas.
    """

    pass


class ValidationError(SchemaGenerationError):
    """Error during schema validation.

    Raised when schema validation fails with one or more validation errors.

    Args:
        errors: List of validation error messages
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Schema validation failed: {'; '.join(errors)}")


class ConfigurationError(SchemaGenerationError):
    """Error in application configuration.

    Raised when required configuration values are missing or invalid,
    such as missing environment variables or invalid configuration settings.

    Args:
        variable_name: The name of the configuration variable that caused the error
        message: Optional custom error message
    """

    def __init__(self, variable_name: str) -> None:
        self.variable_name = variable_name
        message = f"Required configuration variable '{variable_name}' is not set"
        super().__init__(message)
