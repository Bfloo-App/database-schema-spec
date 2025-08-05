"""File system operations for output generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database_schema_spec.core.config import config


class OutputManager:
    """Manages file system operations for output generation.

    This class handles creating directory structures and writing
    resolved schemas to the appropriate output locations.
    """

    def __init__(self, output_dir: Path = config.output_dir) -> None:
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
        output_path = self._get_output_path(engine, version)

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

    def _get_output_path(self, engine: str, version: str) -> Path:
        """Get the output path for a specific engine/version combination.

        Args:
            engine: Database engine name
            version: Database version

        Returns:
            Path where the spec should be written
        """
        return self.output_dir / engine.lower() / version / "spec.json"

    def _get_spec_url(self, engine: str, version: str, base_url: str = "") -> str:
        """Get the URL for a specific engine/version spec file.

        Args:
            engine: Database engine name
            version: Database version
            base_url: Base URL to prepend (optional)

        Returns:
            URL pointing to the spec file
        """
        relative_path = f"{engine.lower()}/{version}/spec.json"
        if base_url:
            return f"{base_url.rstrip('/')}/{relative_path}"
        return relative_path

    def _generate_version_map(self, base_url: str = "") -> dict[str, dict[str, str]]:
        """Generate a version map of all available engines and versions.

        Args:
            base_url: Base URL to prepend to spec URLs (optional)

        Returns:
            Dictionary mapping engines to versions to URLs
        """
        version_map: dict[str, dict[str, str]] = {}

        if not self.output_dir.exists():
            return version_map

        # Iterate through all engine directories
        for engine_dir in self.output_dir.iterdir():
            if engine_dir.is_dir():
                engine_name = engine_dir.name
                version_map[engine_name] = {}

                # Iterate through all version directories for this engine
                for version_dir in engine_dir.iterdir():
                    if version_dir.is_dir():
                        spec_file = version_dir / "spec.json"
                        if spec_file.exists():
                            version_name = version_dir.name
                            spec_url = self._get_spec_url(
                                engine_name, version_name, base_url
                            )
                            version_map[engine_name][version_name] = spec_url

        return version_map

    def write_version_map(self, base_url: str = "") -> Path:
        """Write the version map to vmap.json in the output root.

        Args:
            base_url: Base URL to prepend to spec URLs (optional)

        Returns:
            Path where the vmap.json file was written

        Raises:
            PermissionError: If unable to write file
        """
        version_map = self._generate_version_map(base_url)
        vmap_path = self.output_dir / "vmap.json"

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Write the version map to the file
            with open(vmap_path, "w", encoding="utf-8") as f:
                json.dump(version_map, f, indent=2, ensure_ascii=False)

            return vmap_path

        except Exception as e:
            raise PermissionError(
                f"Failed to write version map to {vmap_path}: {e}"
            ) from e
