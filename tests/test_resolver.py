"""Tests for the JSON reference resolver."""

import json
import tempfile
from pathlib import Path

import pytest

from database_schema_spec.core.exceptions import (
    CircularReferenceError,
    ReferenceResolutionError,
)
from database_schema_spec.resolution.resolver import JSONRefResolver


class TestCircularReferenceDetection:
    """Tests for circular reference detection."""

    def test_detect_circular_reference_in_stack(self):
        """Test detection of circular reference when ref is in stack."""
        resolver = JSONRefResolver()
        resolver.resolution_stack = ["a.json", "b.json"]
        assert resolver.detect_circular_reference("a.json")

    def test_detect_no_circular_reference(self):
        """Test no circular reference when ref is not in stack."""
        resolver = JSONRefResolver()
        resolver.resolution_stack = ["a.json", "b.json"]
        assert not resolver.detect_circular_reference("c.json")


class TestResolveReferencesBasic:
    """Tests for basic reference resolution."""

    def test_resolve_references_no_ref(self):
        """Test schema without $ref returns unchanged."""
        resolver = JSONRefResolver()
        schema = {"properties": {"foo": {"type": "string"}}}
        result = resolver.resolve_references(schema)
        assert result == schema

    def test_resolve_references_with_external_ref(self, monkeypatch):
        """Test resolving external file reference."""
        resolver = JSONRefResolver()
        schema = {"$ref": "other.json", "extra": 1}
        referenced = {"properties": {"bar": {"type": "number"}}}

        def fake_load_referenced_file(ref_path, current_file=None):
            assert ref_path == "other.json"
            return referenced

        resolver.load_referenced_file = fake_load_referenced_file  # type: ignore[method-assign]
        result = resolver.resolve_references(schema)
        assert "bar" in result["properties"]
        assert result["extra"] == 1


class TestParseRef:
    """Tests for $ref parsing into file path and JSON pointer."""

    def test_parse_ref_external_file_only(self):
        """Test parsing external file reference without pointer."""
        resolver = JSONRefResolver()
        file_path, pointer = resolver._parse_ref("other.json")
        assert file_path == "other.json"
        assert pointer is None

    def test_parse_ref_local_pointer_only(self):
        """Test parsing local pointer reference."""
        resolver = JSONRefResolver()
        file_path, pointer = resolver._parse_ref("#/$defs/envs")
        assert file_path is None
        assert pointer == "/$defs/envs"

    def test_parse_ref_external_with_pointer(self):
        """Test parsing external file reference with JSON pointer."""
        resolver = JSONRefResolver()
        file_path, pointer = resolver._parse_ref("engines/postgresql.json#/$defs/envs")
        assert file_path == "engines/postgresql.json"
        assert pointer == "/$defs/envs"

    def test_parse_ref_empty_pointer(self):
        """Test parsing reference with empty pointer after #."""
        resolver = JSONRefResolver()
        file_path, pointer = resolver._parse_ref("other.json#")
        assert file_path == "other.json"
        assert pointer is None

    def test_parse_ref_root_pointer(self):
        """Test parsing reference with root pointer."""
        resolver = JSONRefResolver()
        file_path, pointer = resolver._parse_ref("other.json#/")
        assert file_path == "other.json"
        assert pointer == "/"


class TestResolveJsonPointer:
    """Tests for JSON pointer resolution within documents."""

    def test_resolve_simple_pointer(self):
        """Test resolving a simple JSON pointer."""
        resolver = JSONRefResolver()
        document = {
            "$defs": {"envs": {"type": "object", "description": "Environment configs"}}
        }
        result = resolver._resolve_json_pointer(document, "/$defs/envs", "test")
        assert result == {"type": "object", "description": "Environment configs"}

    def test_resolve_nested_pointer(self):
        """Test resolving a deeply nested JSON pointer."""
        resolver = JSONRefResolver()
        document = {"level1": {"level2": {"level3": {"value": "deep"}}}}
        result = resolver._resolve_json_pointer(
            document, "/level1/level2/level3", "test"
        )
        assert result == {"value": "deep"}

    def test_resolve_pointer_with_escaped_chars(self):
        """Test resolving pointer with escaped characters (~0 and ~1)."""
        resolver = JSONRefResolver()
        # ~1 decodes to /, ~0 decodes to ~
        document = {
            "a/b": {"type": "string"},
            "a~b": {"type": "number"},
        }
        result1 = resolver._resolve_json_pointer(document, "/a~1b", "test")
        assert result1 == {"type": "string"}

        result2 = resolver._resolve_json_pointer(document, "/a~0b", "test")
        assert result2 == {"type": "number"}

    def test_resolve_pointer_empty_returns_document(self):
        """Test that empty pointer returns the whole document."""
        resolver = JSONRefResolver()
        document = {"foo": {"bar": "baz"}}
        result = resolver._resolve_json_pointer(document, "", "test")
        assert result == document

    def test_resolve_pointer_root_returns_document(self):
        """Test that root pointer (/) returns the whole document."""
        resolver = JSONRefResolver()
        document = {"foo": {"bar": "baz"}}
        result = resolver._resolve_json_pointer(document, "/", "test")
        assert result == document

    def test_resolve_pointer_key_not_found(self):
        """Test error when JSON pointer key doesn't exist."""
        resolver = JSONRefResolver()
        document = {"$defs": {"envs": {}}}
        with pytest.raises(ReferenceResolutionError) as exc_info:
            resolver._resolve_json_pointer(document, "/$defs/nonexistent", "test")
        assert "not found" in str(exc_info.value)

    def test_resolve_pointer_non_object_result(self):
        """Test error when pointer resolves to non-object."""
        resolver = JSONRefResolver()
        document = {"$defs": {"value": "string_value"}}
        with pytest.raises(ReferenceResolutionError) as exc_info:
            resolver._resolve_json_pointer(document, "/$defs/value", "test")
        assert "non-object" in str(exc_info.value)

    def test_resolve_pointer_array_index(self):
        """Test resolving pointer through array index."""
        resolver = JSONRefResolver()
        document = {
            "items": [
                {"name": "first"},
                {"name": "second"},
            ]
        }
        result = resolver._resolve_json_pointer(document, "/items/1", "test")
        assert result == {"name": "second"}

    def test_resolve_pointer_invalid_array_index(self):
        """Test error with invalid array index."""
        resolver = JSONRefResolver()
        document = {"items": [{"name": "first"}]}
        with pytest.raises(ReferenceResolutionError) as exc_info:
            resolver._resolve_json_pointer(document, "/items/invalid", "test")
        assert "invalid array index" in str(exc_info.value)


class TestResolveLocalPointer:
    """Tests for local pointer resolution (#/$defs/...)."""

    def test_resolve_local_pointer_no_current_file(self):
        """Test error when resolving local pointer without current file."""
        resolver = JSONRefResolver()
        with pytest.raises(ReferenceResolutionError) as exc_info:
            resolver._resolve_local_pointer("/$defs/test", None, "#/$defs/test")
        assert "without current file context" in str(exc_info.value)


class TestExternalFileWithPointer:
    """Tests for external file references with JSON pointers."""

    def test_resolve_external_file_with_pointer(self):
        """Test resolving external file reference with JSON pointer."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create the external file with $defs
            external_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$defs": {
                    "envs": {
                        "type": "object",
                        "description": "Environment configurations",
                        "properties": {"host": {"type": "string"}},
                    }
                },
            }
            (temp_path / "engines").mkdir()
            with open(temp_path / "engines" / "postgresql.json", "w") as f:
                json.dump(external_schema, f)

            # Create the main file that references the external file
            main_schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "properties": {"envs": {"$ref": "engines/postgresql.json#/$defs/envs"}},
            }
            with open(temp_path / "base.json", "w") as f:
                json.dump(main_schema, f)

            # Resolve
            resolver = JSONRefResolver(temp_path)
            result = resolver.resolve_file("base.json")

            # Verify the reference was resolved
            assert "properties" in result
            assert "envs" in result["properties"]
            assert result["properties"]["envs"]["type"] == "object"
            assert (
                result["properties"]["envs"]["description"]
                == "Environment configurations"
            )


class TestLocalPointerResolution:
    """Tests for local pointer resolution within the same file."""

    def test_resolve_local_pointer_in_file(self):
        """Test resolving local $ref pointer within the same file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a file with local $ref
            schema = {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "$defs": {"stringType": {"type": "string", "minLength": 1}},
                "properties": {"name": {"$ref": "#/$defs/stringType"}},
            }
            with open(temp_path / "schema.json", "w") as f:
                json.dump(schema, f)

            # Resolve
            resolver = JSONRefResolver(temp_path)
            result = resolver.resolve_file("schema.json")

            # Verify local reference was resolved
            assert result["properties"]["name"]["type"] == "string"
            assert result["properties"]["name"]["minLength"] == 1


class TestFileCaching:
    """Tests for file caching functionality."""

    def test_file_caching(self):
        """Test that files are cached and not re-read."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            schema = {"type": "object"}
            with open(temp_path / "cached.json", "w") as f:
                json.dump(schema, f)

            resolver = JSONRefResolver(temp_path)

            # First load
            result1 = resolver._load_file_cached("cached.json")

            # Modify the file
            with open(temp_path / "cached.json", "w") as f:
                json.dump({"type": "string"}, f)

            # Second load should return cached version
            result2 = resolver._load_file_cached("cached.json")

            assert result1 == result2
            assert result1["type"] == "object"  # Original value, not modified


class TestCircularReferenceError:
    """Tests for circular reference error handling."""

    def test_circular_reference_local_pointer(self):
        """Test circular reference detection with local pointers."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a file with circular local reference
            schema = {
                "$defs": {"a": {"$ref": "#/$defs/b"}, "b": {"$ref": "#/$defs/a"}},
                "properties": {"test": {"$ref": "#/$defs/a"}},
            }
            with open(temp_path / "circular.json", "w") as f:
                json.dump(schema, f)

            resolver = JSONRefResolver(temp_path)
            with pytest.raises(CircularReferenceError):
                resolver.resolve_file("circular.json")


class TestComplexSchemaResolution:
    """Tests for complex schema resolution scenarios."""

    def test_resolve_nested_external_and_local_refs(self):
        """Test resolving schema with both external and local references."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "components").mkdir()

            # Create component file
            component = {
                "$defs": {
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                        },
                    }
                }
            }
            with open(temp_path / "components" / "address.json", "w") as f:
                json.dump(component, f)

            # Create main file with mixed references
            main_schema = {
                "$defs": {
                    "person": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "address": {
                                "$ref": "components/address.json#/$defs/address"
                            },
                        },
                    }
                },
                "properties": {"owner": {"$ref": "#/$defs/person"}},
            }
            with open(temp_path / "main.json", "w") as f:
                json.dump(main_schema, f)

            # Resolve
            resolver = JSONRefResolver(temp_path)
            result = resolver.resolve_file("main.json")

            # Verify nested resolution
            owner = result["properties"]["owner"]
            assert owner["type"] == "object"
            assert owner["properties"]["name"]["type"] == "string"
            assert owner["properties"]["address"]["type"] == "object"
            assert (
                owner["properties"]["address"]["properties"]["street"]["type"]
                == "string"
            )
