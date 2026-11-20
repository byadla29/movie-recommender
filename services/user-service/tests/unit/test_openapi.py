"""The generated API contract is internally consistent."""

from collections.abc import Iterator
from typing import Any

from fastapi import FastAPI


def _refs(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)


def test_every_ref_points_to_a_defined_schema(app: FastAPI) -> None:
    spec = app.openapi()
    defined = {f"#/components/schemas/{name}" for name in spec["components"]["schemas"]}

    refs = set(_refs(spec))

    assert "#/components/schemas/Problem" in refs
    assert refs <= defined, refs - defined


def test_every_me_endpoint_requires_a_bearer_token(app: FastAPI) -> None:
    spec = app.openapi()

    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            if path.startswith("/v1/me"):
                assert operation.get("security") == [{"HTTPBearer": []}], (method, path)
                assert "401" in operation["responses"], (method, path)
