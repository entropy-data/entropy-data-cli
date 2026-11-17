"""Read the Entropy Data OpenAPI spec the CLI is checked against (tests/openapi.yaml).

Refresh the copy with ./update-openapi. Used by the drift checks: the table columns in
tests/test_openapi_drift.py, and every request the test suite sends (tests/conftest.py).
"""

import functools
import re
from pathlib import Path

import yaml

SPEC_FILE = Path(__file__).parent / "openapi.yaml"
HTTP_METHODS = ("get", "put", "post", "delete", "patch")


@functools.cache
def spec() -> dict:
    return yaml.safe_load(SPEC_FILE.read_text())


@functools.cache
def _path_patterns() -> list[tuple[re.Pattern, str]]:
    """Path templates as regexes, literal templates first so /runs/latest wins over /runs/{id}."""
    templates = sorted(spec()["paths"], key=lambda t: (t.count("{"), -len(t)))
    patterns = []
    for template in templates:
        regex = "".join(
            "[^/]+" if part.startswith("{") else re.escape(part) for part in re.split(r"(\{[^}]+\})", template)
        )
        patterns.append((re.compile(f"^{regex}$"), template))
    return patterns


@functools.cache
def _trailing_patterns() -> list[tuple[re.Pattern, str]]:
    """Templates ending in a parameter, with that parameter spanning slashes.

    Hierarchical ids (a tag `Governance/PII`, a concept `Security/Group`) go into the path as
    they are, and the server takes the rest of the path as the id.
    """
    return [
        (re.compile(pattern.pattern.removesuffix("[^/]+$") + ".+$"), template)
        for pattern, template in _path_patterns()
        if template.endswith("}")
    ]


def match_path(path: str) -> str | None:
    """Return the spec's path template for a request path, or None."""
    for pattern, template in _path_patterns() + _trailing_patterns():
        if pattern.match(path):
            return template
    return None


def _resolve(node):
    """Follow local $refs; an external $ref (ODCS/ODPS JSON schemas) resolves to an open schema."""
    components = spec()["components"]
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if not ref.startswith("#/components/"):
            return {"additionalProperties": True}
        _, _, section, name = ref.split("/", 3)
        node = components[section][name]
    return node or {}


def query_parameters(template: str, method: str) -> set[str]:
    """Names of the query parameters the spec documents for an operation (path-level ones included)."""
    path_item = spec()["paths"][template]
    params = path_item.get("parameters", []) + path_item[method.lower()].get("parameters", [])
    return {p["name"] for p in map(_resolve, params) if p.get("in") == "query"}


def _properties(schema) -> tuple[dict, bool]:
    """(properties, open) of a schema, merging allOf/oneOf/anyOf. Open: any key may appear."""
    schema = _resolve(schema)
    props: dict = {}
    is_open = bool(schema.get("additionalProperties"))
    composed = False
    for key in ("allOf", "oneOf", "anyOf"):
        for sub in schema.get(key, []):
            composed = True
            sub_props, sub_open = _properties(sub)
            props.update(sub_props)
            is_open = is_open or sub_open
    props.update(schema.get("properties", {}))
    # A free-form object (no properties, no composition) says nothing about its keys.
    return props, is_open or (not props and not composed)


def list_item_schema(template: str) -> dict:
    """Schema of one item of a GET response: the array's items, or the object itself."""
    responses = spec()["paths"][template]["get"]["responses"]
    response = _resolve(responses.get(200) or responses.get("200"))
    content = next(iter(response["content"].values()))
    schema = _resolve(content["schema"])
    if schema.get("type") == "array":
        return schema["items"]
    return schema


def field_exists(schema, dotted: str) -> bool:
    """Whether a dot-separated field (as a table column reads it) can appear in the schema."""
    current = schema
    for part in dotted.split("."):
        props, is_open = _properties(current)
        if part in props:
            current = props[part]
        elif is_open:
            return True
        else:
            return False
    return True


def undocumented_requests(requests, allowed: dict | frozenset = frozenset()) -> list[str]:
    """Describe each request to /api/… that is not an operation in the spec, or sends a query
    parameter the operation does not document. ``allowed`` holds (method, template, parameter)
    keys to accept anyway; parameter None accepts the operation itself."""
    problems = []
    for request in requests:
        path, method = request.url.path, request.method
        if not path.startswith("/api/"):
            continue
        template = match_path(path)
        if template is None or method.lower() not in spec()["paths"][template]:
            if (method, template or path, None) not in allowed:
                problems.append(f"{method} {path}: not an operation in the spec")
            continue
        documented = query_parameters(template, method)
        for name in dict(request.url.params):
            if name not in documented and (method, template, name) not in allowed:
                problems.append(f"{method} {template}: query parameter '{name}' is not in the spec")
    return sorted(set(problems))
