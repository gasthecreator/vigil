from packages.contracts.generate_ts import map_schema_type_to_ts


def test_openapi_enum_and_const_become_typescript_literals():
    assert map_schema_type_to_ts({"enum": ["recorded", "unavailable"]}) == (
        '"recorded" | "unavailable"'
    )
    assert map_schema_type_to_ts({"type": "string", "const": "abstained"}) == '"abstained"'
