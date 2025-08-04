"""
Database Schema Spec Generator

Entry point for the schema generator script.
"""

from database_schema_spec import SchemaGenerator


def main() -> None:
    """
    Entry point for the schema generator script.

    Creates SchemaGenerator instance and runs generation process.
    """
    generator = SchemaGenerator()
    generator.run()


if __name__ == "__main__":
    main()
