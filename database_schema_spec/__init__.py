"""
Database Schema Spec Generator

A Python package for generating unified JSON documentation files for database schemas
by resolving JSON Schema references and handling oneOf variants.
"""

from database_schema_spec.cli.generator import SchemaGenerator

__all__ = ["SchemaGenerator"]
