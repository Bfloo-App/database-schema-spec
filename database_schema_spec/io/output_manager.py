"""File system operations for output generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database_schema_spec.core.constants import OUTPUT_DIR


class OutputManager:
    """Manages file system operations for output generation.

    This class handles creating directory structures and writing
    resolved schemas to the appropriate output locations.
    """

    def __init__(self, output_dir: Path = OUTPUT_DIR) -> None:
        """Initialize the output manager.

        Args:
            output_dir: Base directory for output files
        """
        self.output_dir = output_dir

    def create_output_structure(self) -> None:
        """Create the base output directory structure.

        Raises:
            PermissionError: If unable to create directories
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise PermissionError(
                f"Failed to create output directory {self.output_dir}: {e}"
            ) from e

    def write_schema(self, schema: dict[str, Any], engine: str, version: str) -> Path:
        """Write a resolved schema to the appropriate output file.

        Args:
            schema: Fully resolved schema to write
            engine: Database engine name
            version: Database version

        Returns:
            Path where the file was written

        Raises:
            PermissionError: If unable to write file
        """
        output_path = self.get_output_path(engine, version)

        try:
            # Create directory structure if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the schema to the file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)

            return output_path

        except Exception as e:
            raise PermissionError(
                f"Failed to write schema to {output_path}: {e}"
            ) from e

    def get_output_path(self, engine: str, version: str) -> Path:
        """Get the output path for a specific engine/version combination.

        Args:
            engine: Database engine name
            version: Database version

        Returns:
            Path where the spec should be written
        """
        return self.output_dir / engine.lower() / version / "spec.json"
