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

    def __init__(
        self,
        output_dir: Path = config.output_dir,
        docs_dir: Path = config.docs_dir,
    ) -> None:
        """Initialize the output manager.

        Args:
            output_dir: Base directory for output files
            docs_dir: Base directory for source schema files
        """
        self.output_dir = output_dir
        self.docs_dir = docs_dir

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

    def _generate_engine_map(self, base_url: str = "") -> dict[str, dict[str, str]]:
        """Generate a map of all available engines and versions.

        Args:
            base_url: Base URL to prepend to spec URLs (optional)

        Returns:
            Dictionary mapping engines to versions to URLs
        """
        engine_map: dict[str, dict[str, str]] = {}

        if not self.output_dir.exists():
            return engine_map

        # Reserved directory names that are not engines
        reserved_dirs = {"config", "manifest.json", "smap.json"}

        # Iterate through all engine directories
        for engine_dir in self.output_dir.iterdir():
            if (
                engine_dir.is_dir()
                and not engine_dir.name.startswith(".")
                and engine_dir.name not in reserved_dirs
            ):
                engine_name = engine_dir.name
                versions: dict[str, str] = {}

                # Iterate through all version directories for this engine
                for version_dir in engine_dir.iterdir():
                    if version_dir.is_dir():
                        spec_file = version_dir / "spec.json"
                        if spec_file.exists():
                            version_name = version_dir.name
                            spec_url = self._get_spec_url(
                                engine_name, version_name, base_url
                            )
                            versions[version_name] = spec_url

                # Only add engine if it has at least one version
                if versions:
                    engine_map[engine_name] = versions

        return engine_map

    def write_project_schema(
        self, source_path: str, output_path: str, base_url: str = ""
    ) -> Path:
        """Write a project schema to the output with $id injected.

        Args:
            source_path: Relative path to source schema file (from docs_dir)
            output_path: Relative output path (e.g., 'config/base.json')
            base_url: Base URL for $id injection

        Returns:
            Path where the file was written

        Raises:
            PermissionError: If unable to write file
            FileNotFoundError: If source file doesn't exist
        """
        source_file = self.docs_dir / source_path
        full_output_path = self.output_dir / output_path

        if not source_file.exists():
            raise FileNotFoundError(f"Source schema not found: {source_file}")

        try:
            # Ensure output directory exists
            full_output_path.parent.mkdir(parents=True, exist_ok=True)

            # Load the source schema
            with open(source_file, "r", encoding="utf-8") as f:
                schema: dict[str, Any] = json.load(f)

            # Inject $id
            if base_url:
                schema_url = f"{base_url.rstrip('/')}/{output_path}"
                # Ensure $id comes after $schema
                reordered: dict[str, Any] = {}
                if "$schema" in schema:
                    reordered["$schema"] = schema["$schema"]
                reordered["$id"] = schema_url
                for k, v in schema.items():
                    if k not in ("$schema", "$id"):
                        reordered[k] = v
                schema = reordered

            # Write to output
            with open(full_output_path, "w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, ensure_ascii=False)

            return full_output_path

        except json.JSONDecodeError as e:
            raise PermissionError(f"Invalid JSON in source schema {source_file}: {e}")
        except Exception as e:
            raise PermissionError(
                f"Failed to write project schema to {full_output_path}: {e}"
            ) from e

    def write_schema_map(self, engines: list[str], base_url: str = "") -> Path:
        """Write the schema map to smap.json in the output root.

        The schema map contains:
        - project:
          - manifest: URL to manifest.json schema
          - config:
            - base: URL to config/base.json schema
            - engines: Map of engine name -> config URL
        - engines: Map of engine -> version -> spec URL

        Args:
            engines: List of engine names to include in config mapping
            base_url: Base URL to prepend to spec URLs (optional)

        Returns:
            Path where the smap.json file was written

        Raises:
            PermissionError: If unable to write file
        """
        base = base_url.rstrip("/") if base_url else ""

        # Build engine config map
        engine_configs: dict[str, str] = {}
        for engine in engines:
            engine_lower = engine.lower()
            config_path = f"config/engines/{engine_lower}.json"
            engine_configs[engine_lower] = (
                f"{base}/{config_path}" if base else config_path
            )

        schema_map: dict[str, Any] = {
            "project": {
                "manifest": f"{base}/manifest.json" if base else "manifest.json",
                "config": {
                    "base": f"{base}/config/base.json" if base else "config/base.json",
                    "engines": engine_configs,
                },
            },
            "engines": self._generate_engine_map(base_url),
        }

        smap_path = self.output_dir / "smap.json"

        try:
            # Ensure output directory exists
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Write the schema map to the file
            with open(smap_path, "w", encoding="utf-8") as f:
                json.dump(schema_map, f, indent=2, ensure_ascii=False)

            return smap_path

        except Exception as e:
            raise PermissionError(
                f"Failed to write schema map to {smap_path}: {e}"
            ) from e
