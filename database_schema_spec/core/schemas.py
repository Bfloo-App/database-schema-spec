"""Pydantic models for type-safe data validation and parsing."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DatabaseVariantSpec(BaseModel):
    """Pydantic model for database variant specifications.

    Provides type safety and validation for database engine and version data.
    """

    engine: str = Field(..., min_length=1, description="Database engine name")
    version: str = Field(..., min_length=1, description="Database version")
    engine_spec_path: str | None = Field(
        None, description="Path to engine specification file"
    )

    @field_validator("engine")
    @classmethod
    def validate_engine(cls, v: str) -> str:
        """Validate engine name format."""
        if not v.replace("_", "").replace("-", "").replace(" ", "").isalnum():
            raise ValueError(
                "Engine name must contain only alphanumeric characters, hyphens, underscores, and spaces"
            )
        return v

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version format."""
        if not v.replace(".", "").replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Version must contain only alphanumeric characters, dots, hyphens, and underscores"
            )
        return v

    def __str__(self) -> str:
        """Return string representation in format 'engine version'."""
        return f"{self.engine} {self.version}"

    def output_path(self) -> str:
        """Generate the output directory path for this variant.

        Returns:
            Path in format 'engine/version' with lowercase engine name
        """
        return f"{self.engine.lower()}/{self.version}"


class ValidationResult(BaseModel):
    """Result of schema validation with type safety.

    Provides validated results for schema validation operations.
    """

    is_valid: bool = Field(..., description="Whether the schema passed validation")
    errors: list[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    warnings: list[str] = Field(
        default_factory=list, description="Validation warning messages"
    )

    def add_error(self, message: str) -> None:
        """Add an error message to the validation result."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message to the validation result."""
        self.warnings.append(message)
