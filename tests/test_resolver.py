from database_schema_spec.resolution.resolver import JSONRefResolver


def test_circular_reference_detection():
    resolver = JSONRefResolver()
    resolver.resolution_stack = ["a.json", "b.json"]
    assert resolver.detect_circular_reference("a.json")
    assert not resolver.detect_circular_reference("c.json")


def test_resolve_references_no_ref():
    resolver = JSONRefResolver()
    schema = {"properties": {"foo": {"type": "string"}}}
    result = resolver.resolve_references(schema)
    assert result == schema


def test_resolve_references_with_ref(monkeypatch):
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
