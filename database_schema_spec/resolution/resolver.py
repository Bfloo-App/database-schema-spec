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

    Supports:
    - Local references: #/$defs/foo
    - External file references: other.json
    - External file with JSON pointer: other.json#/$defs/foo
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
        self._file_cache: dict[str, dict[str, Any]] = {}

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
        """Resolve a $ref reference.

        Handles:
        - Local references: #/$defs/foo (within current file)
        - External file references: other.json
        - External file with JSON pointer: other.json#/$defs/foo
        """
        ref_path = schema[config.json_schema_fields.ref_field]

        # Parse the reference into file path and JSON pointer
        file_path, json_pointer = self._parse_ref(ref_path)

        # Determine the resolution key for circular reference detection
        resolution_key = ref_path if file_path else f"{current_file or ''}:{ref_path}"

        if self.detect_circular_reference(resolution_key):
            raise CircularReferenceError(self.resolution_stack + [resolution_key])

        self.resolution_stack.append(resolution_key)
        try:
            if file_path:
                # External reference (with or without JSON pointer)
                referenced_content = self.load_referenced_file(file_path, current_file)
                new_current_file = self._get_new_current_file(current_file, file_path)

                if json_pointer:
                    # Extract the specific part using JSON pointer
                    referenced_content = self._resolve_json_pointer(
                        referenced_content, json_pointer, ref_path
                    )
            else:
                # Local reference (JSON pointer only, starts with #)
                # We need access to the root document
                if not json_pointer:
                    raise ReferenceResolutionError(
                        ref_path,
                        ValueError("Invalid local reference: missing JSON pointer"),
                    )
                referenced_content = self._resolve_local_pointer(
                    json_pointer, current_file, ref_path
                )
                new_current_file = current_file

            resolved_content = self.resolve_references(
                referenced_content, new_current_file
            )
            return self._merge_schema_with_ref(schema, resolved_content)
        finally:
            self.resolution_stack.pop()

    def _parse_ref(self, ref_path: str) -> tuple[str | None, str | None]:
        """Parse a $ref value into file path and JSON pointer components.

        Args:
            ref_path: The $ref value (e.g., "other.json#/$defs/foo" or "#/$defs/foo")

        Returns:
            Tuple of (file_path, json_pointer). Either can be None.
        """
        if "#" in ref_path:
            parts = ref_path.split("#", 1)
            file_path = parts[0] if parts[0] else None
            json_pointer = parts[1] if len(parts) > 1 and parts[1] else None
            return file_path, json_pointer
        return ref_path, None

    def _resolve_json_pointer(
        self, document: dict[str, Any], pointer: str, original_ref: str
    ) -> dict[str, Any]:
        """Resolve a JSON pointer within a document.

        Args:
            document: The JSON document to traverse
            pointer: JSON pointer string (e.g., "/$defs/envs")
            original_ref: Original reference for error messages

        Returns:
            The referenced portion of the document

        Raises:
            ReferenceResolutionError: If the pointer cannot be resolved
        """
        if not pointer or pointer == "/":
            return document

        # Remove leading slash and split into parts
        parts = pointer.lstrip("/").split("/")
        current = document

        for part in parts:
            # Handle JSON pointer escaping (~0 = ~, ~1 = /)
            part = part.replace("~1", "/").replace("~0", "~")

            if isinstance(current, dict):
                if part not in current:
                    raise ReferenceResolutionError(
                        original_ref,
                        KeyError(
                            f"JSON pointer '{pointer}' not found: key '{part}' "
                            f"does not exist"
                        ),
                    )
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError) as e:
                    raise ReferenceResolutionError(
                        original_ref,
                        KeyError(
                            f"JSON pointer '{pointer}' not found: "
                            f"invalid array index '{part}'"
                        ),
                    ) from e
            else:
                raise ReferenceResolutionError(
                    original_ref,
                    TypeError(
                        f"JSON pointer '{pointer}' cannot traverse "
                        f"non-container type at '{part}'"
                    ),
                )

        if not isinstance(current, dict):
            raise ReferenceResolutionError(
                original_ref,
                TypeError(f"JSON pointer '{pointer}' resolved to non-object type"),
            )

        return current

    def _resolve_local_pointer(
        self, pointer: str, current_file: str | None, original_ref: str
    ) -> dict[str, Any]:
        """Resolve a local JSON pointer (starting with #) within the current file.

        Args:
            pointer: JSON pointer string (e.g., "/$defs/envs")
            current_file: Path to the current file being processed
            original_ref: Original reference for error messages

        Returns:
            The referenced portion of the document

        Raises:
            ReferenceResolutionError: If the pointer cannot be resolved
        """
        if not current_file:
            raise ReferenceResolutionError(
                original_ref,
                ValueError(
                    "Cannot resolve local reference without current file context"
                ),
            )

        # Load the current file's root document
        root_document = self._load_file_cached(current_file)
        return self._resolve_json_pointer(root_document, pointer, original_ref)

    def _load_file_cached(self, file_path: str) -> dict[str, Any]:
        """Load a JSON file with caching.

        Args:
            file_path: Relative path to the file from base_path

        Returns:
            Parsed JSON content
        """
        if file_path not in self._file_cache:
            full_path = (self.base_path / file_path).resolve()
            if not full_path.exists():
                raise FileNotFoundError(f"File not found: {full_path}")
            with open(full_path, "r", encoding="utf-8") as f:
                self._file_cache[file_path] = json.load(f)
        return self._file_cache[file_path]

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
            CircularReferenceError: If circular references are detected
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

        except CircularReferenceError:
            # Re-raise circular reference errors directly
            raise
        except Exception as e:
            logger.exception("Error resolving file '%s': %s", file_path, e)
            raise ReferenceResolutionError(file_path, e) from e
