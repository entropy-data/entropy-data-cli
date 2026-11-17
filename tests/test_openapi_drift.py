"""Check the CLI's table columns against the OpenAPI spec (tests/openapi.yaml).

A table prints a missing field as an empty cell, so a field the API drops goes unnoticed: the
integrations list lost `latestRun` and its Latest Run column stayed empty for months. These tests
fail instead. When the API changes, refresh the spec with ./update-openapi and run them.
"""

import httpx
import pytest

from entropy_data.output import RESOURCE_COLUMNS
from tests import openapi_spec

# Table type → the GET endpoint whose items (or object) the table shows.
LIST_ENDPOINTS = {
    "dataproducts": "/api/dataproducts",
    "datacontracts": "/api/datacontracts",
    "access": "/api/access",
    "teams": "/api/teams",
    "my-teams": "/api/teams",
    "sourcesystems": "/api/sourcesystems",
    "definitions": "/api/definitions",
    "certifications": "/api/certifications",
    "policies": "/api/policies",
    "dataproductbuilders": "/api/dataproductbuilders",
    "example-data": "/api/example-data",
    "test-results": "/api/test-results",
    "datacontract-branches": "/api/datacontracts/{id}/branches",
    "datacontract-branch-changes": "/api/datacontracts/{id}/branches/{branch}/changes",
    "semantic-branches": "/api/semantics/experimental/namespaces/{namespace}/branches",
    "semantic-branch-changes": "/api/semantics/experimental/namespaces/{namespace}/branches/{branch}/changes",
    "events": "/api/events",
    "costs": "/api/costs",
    "assets": "/api/assets",
    "tags": "/api/tags",
    "star-status": "/api/dataproducts/{id}/star",
    "stargazers": "/api/dataproducts/{id}/stargazers",
    "classification-schemes": "/api/classification-schemes",
    "organization-members": "/api/organization/members",
    "connectors": "/api/connectors",
    "usecases": "/api/usecases",
    "integrations": "/api/integrations/ingest",
    "unity-catalog-metadata-integrations": "/api/integrations/unity-catalog-metadata",
    "unity-catalog-metadata-tables": "/api/integrations/unity-catalog-metadata/{integration}/tables",
    "unity-catalog-metadata-queue": "/api/integrations/unity-catalog-metadata/{integration}/queue",
    "integration-runs": "/api/integrations/ingest/{integration}/runs",
    "git-credentials": "/api/organization/gitcredentials",
    "semantic-namespaces": "/api/semantics/experimental/namespaces",
    "semantic-concepts": "/api/semantics/experimental/namespaces/{namespace}/concepts",
    "semantic-relationships": "/api/semantics/experimental/namespaces/{namespace}/relationships",
    "lineage": "/api/v1/lineage",
    "usage": "/api/v1/traces",
}

# Tables whose rows the CLI builds itself rather than printing the endpoint's items.
CLIENT_SIDE_TABLES = {
    # settings team-roles get prints `team-roles` out of {mode, team-roles}.
    "custom-team-roles": ("/api/settings/team-roles", "team-roles"),
}

# Columns the CLI fills in itself; the spec is not expected to have them.
CLIENT_SIDE_FIELDS = {
    # teams list --member adds the member's role in each team.
    ("my-teams", "role"),
    # integrations list fetches …/runs/latest per integration for the table.
    ("integrations", "latestRun.status"),
}


def _columns():
    for resource_type, columns in RESOURCE_COLUMNS.items():
        for _, field in columns:
            yield resource_type, field


def test_every_table_has_an_endpoint():
    unmapped = sorted(set(RESOURCE_COLUMNS) - set(LIST_ENDPOINTS) - set(CLIENT_SIDE_TABLES))
    assert not unmapped, f"Map these table types to their GET endpoint in LIST_ENDPOINTS: {unmapped}"


@pytest.mark.parametrize("template", sorted(set(LIST_ENDPOINTS.values())))
def test_endpoint_is_in_spec(template):
    assert template in openapi_spec.spec()["paths"], f"{template} is not in tests/openapi.yaml"


@pytest.mark.parametrize(("resource_type", "field"), sorted(_columns()))
def test_table_column_is_in_response_schema(resource_type, field):
    if (resource_type, field) in CLIENT_SIDE_FIELDS:
        return
    if resource_type in CLIENT_SIDE_TABLES:
        template, key = CLIENT_SIDE_TABLES[resource_type]
        schema = openapi_spec.list_item_schema(template)
        props, _ = openapi_spec._properties(schema)
        schema = openapi_spec._resolve(props[key])["items"]
    else:
        schema = openapi_spec.list_item_schema(LIST_ENDPOINTS[resource_type])
    assert openapi_spec.field_exists(schema, field), (
        f"Column '{field}' of the '{resource_type}' table is not in the response schema of "
        f"{LIST_ENDPOINTS.get(resource_type) or CLIENT_SIDE_TABLES[resource_type][0]}; it would always print empty."
    )


def test_client_side_fields_are_still_missing_from_the_spec():
    """When the API adds a field back, drop it from CLIENT_SIDE_FIELDS (and the CLI's workaround)."""
    back = []
    for resource_type, field in sorted(CLIENT_SIDE_FIELDS):
        schema = openapi_spec.list_item_schema(LIST_ENDPOINTS[resource_type])
        _, is_open = openapi_spec._properties(schema)
        if not is_open and openapi_spec.field_exists(schema, field):
            back.append((resource_type, field))
    assert not back, f"The spec now has these fields; remove the client-side workaround: {back}"


def test_request_check_flags_unknown_operations_and_parameters():
    def request(method, url):
        return httpx.Request(method, f"https://api.entropy-data.com{url}")

    problems = openapi_spec.undocumented_requests(
        [
            request("GET", "/api/integrations/ingest?source=snowflake"),
            request("GET", "/api/integrations/ingest/demo/runs/latest"),
            request("PUT", "/api/tags/Governance/PII"),
            request("GET", "/api/integrations/ingest?latestRun=true"),
            request("GET", "/api/no-such-thing"),
            request("PATCH", "/api/teams/t1"),
        ]
    )
    assert problems == [
        "GET /api/integrations/ingest: query parameter 'latestRun' is not in the spec",
        "GET /api/no-such-thing: not an operation in the spec",
        "PATCH /api/teams/t1: not an operation in the spec",
    ]
