from pathlib import Path

from database_schema_spec.cli.generator import SchemaGenerator


def test_schema_generation(tmp_path):
    # Use a temporary output directory
    docs_path = Path("docs")
    output_path = tmp_path / "output"
    generator = SchemaGenerator(docs_path=docs_path, output_path=output_path)
    try:
        generator.run()
    except SystemExit as e:
        # Accept exit code 0 (success)
        assert e.code == 0
    # Check that output directory was created
    assert output_path.exists()
    # Optionally, check for expected files
    files = list(output_path.rglob("*.json"))
    assert files, "No schema files generated"
