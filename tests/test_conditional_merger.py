from database_schema_spec.core.schemas import DatabaseVariantSpec
from database_schema_spec.resolution.conditional_merger import ConditionalMerger


class DummyResolver:
    def resolve_references(self, schema, current_file=None):
        return schema


def make_variant(engine="postgresql", version="15.0"):
    return DatabaseVariantSpec(engine=engine, version=version, engine_spec_path=None)


def test_matches_variant_condition_if_then():
    variant = make_variant()
    merger = ConditionalMerger(DummyResolver())
    condition = {
        "if": {
            "properties": {
                "database": {
                    "properties": {
                        "engine": {"const": "postgresql"},
                        "version": {"const": "15.0"},
                    }
                }
            }
        }
    }
    assert merger._matches_variant_condition(condition, variant)


def test_matches_variant_condition_direct_properties():
    variant = make_variant()
    merger = ConditionalMerger(DummyResolver())
    condition = {
        "properties": {
            "engine": {"const": "postgresql"},
            "version": {"const": "15.0"},
        }
    }
    assert merger._matches_variant_condition(condition, variant)


def test_check_properties_match_false():
    variant = make_variant()
    merger = ConditionalMerger(DummyResolver())
    properties = {
        "engine": {"const": "mysql"},
        "version": {"const": "15.0"},
    }
    assert not merger._check_properties_match(properties, variant)
