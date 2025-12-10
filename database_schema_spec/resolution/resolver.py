"""JSON Schema reference resolver."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database_schema_spec.core.config import config
from database_schema_spec.core.exceptions import (
    CircularReferenceError,
    ReferenceResolutionError,
)
from database_schema_spec.core.schemas import DatabaseVariantSpec
from database_schema_spec.logger import logger


class JSONRefResolver:
    """Handles JSON Schema $ref reference resolution.

    This resolver processes JSON Schema files and resolves all $ref references,
    inlining the referenced content to produce a self-contained schema.
    """

    def __init__(
        self,
        base_path: Path = config.docs_dir,
        current_variant: DatabaseVariantSpec | None = None,
    ) -> None:
        """Initialize the JSON reference resolver.

        Args:
            base_path: Base directory for resolving relative references
            current_variant: Database variant (kept for interface compatibility)
        """
        self.base_path = base_path
        self.current_variant = current_variant
        self.resolution_stack: list[str] = []

    def resolve_references(
        self, schema: dict[str, Any], current_file: str | None = None
    ) -> dict[str, Any]:
        """Recursively resolve all $ref references in a schema."""
        if not isinstance(schema, dict):
            return schema

        if config.json_schema_fields.ref_field in schema:
            return self._resolve_ref(schema, current_file)
        return self._resolve_nested(schema, current_file)

    def _resolve_ref(
        self, schema: dict[str, Any], current_file: str | None
    ) -> dict[str, Any]:
        ref_path = schema[config.json_schema_fields.ref_field]
        if self.detect_circular_reference(ref_path):
            raise CircularReferenceError(self.resolution_stack + [ref_path])
        self.resolution_stack.append(ref_path)
        try:
            referenced_content = self.load_referenced_file(ref_path, current_file)
            new_current_file = self._get_new_current_file(current_file, ref_path)
            resolved_content = self.resolve_references(
                referenced_content, new_current_file
            )
            return self._merge_schema_with_ref(schema, resolved_content)
        finally:
            self.resolution_stack.pop()

    def _get_new_current_file(self, current_file: str | None, ref_path: str) -> str:
        if current_file:
            current_dir = (self.base_path / current_file).parent
            return str((current_dir / ref_path).relative_to(self.base_path))
        return ref_path

    def _merge_schema_with_ref(
        self, schema: dict[str, Any], resolved_content: dict[str, Any]
    ) -> dict[str, Any]:
        result = dict(resolved_content)
        for key, value in schema.items():
            if key == config.json_schema_fields.ref_field:
                continue
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = {**result[key], **value}
                else:
                    result[key] = value
            else:
                result[key] = value
        return result

    def _resolve_nested(
        self, schema: dict[str, Any], current_file: str | None
    ) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                result[key] = self.resolve_references(value, current_file)
            elif isinstance(value, list):
                result[key] = [
                    self.resolve_references(item, current_file)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    def detect_circular_reference(self, ref_path: str) -> bool:
        """Check if adding this reference would create a circular dependency.

        Args:
            ref_path: The reference path to check

        Returns:
            True if this would create a circular reference, False otherwise
        """
        return ref_path in self.resolution_stack

    def load_referenced_file(
        self, ref_path: str, current_file: str | None = None
    ) -> dict[str, Any]:
        """Load a JSON file from a reference path.

        Args:
            ref_path: Relative path to the referenced file
            current_file: Path of the file making the reference (for relative resolution)

        Returns:
            Parsed JSON content

        Raises:
            ReferenceResolutionError: If file doesn't exist or invalid JSON
        """
        try:
            # If we have a current file path, resolve relative to it
            if current_file:
                current_dir = (self.base_path / current_file).parent
                full_path = current_dir / ref_path
            else:
                # Resolve relative to base_path
                full_path = self.base_path / ref_path

            # Normalize the path
            full_path = full_path.resolve()

            # Check if file exists
            if not full_path.exists():
                raise FileNotFoundError(f"Referenced file not found: {full_path}")

            # Read and parse JSON
            with open(full_path, "r", encoding="utf-8") as f:
                content: dict[str, Any] = json.load(f)

            return content

        except FileNotFoundError as e:
            raise ReferenceResolutionError(ref_path, e)
        except json.JSONDecodeError as e:
            raise ReferenceResolutionError(ref_path, e)
        except Exception as e:
            raise ReferenceResolutionError(ref_path, e)

    def resolve_file(self, file_path: str) -> dict[str, Any]:
        """Load and resolve a JSON file with all $ref references resolved.

        Args:
            file_path: Path to the JSON file to load

        Returns:
            Fully resolved JSON schema

        Raises:
            ReferenceResolutionError: If file cannot be loaded or resolved
        """
        try:
            # Load the file
            full_path = self.base_path / file_path
            if not full_path.exists():
                logger.error("File not found: %s", full_path)
                raise FileNotFoundError(f"File not found: {full_path}")

            with open(full_path, "r", encoding="utf-8") as f:
                schema: dict[str, Any] = json.load(f)

            # Resolve all references
            resolved_schema = self.resolve_references(schema, file_path)
            return resolved_schema

        except Exception as e:
            logger.exception("Error resolving file '%s': %s", file_path, e)
            raise ReferenceResolutionError(file_path, e) from e
