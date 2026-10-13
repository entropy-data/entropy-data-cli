"""Tests for the semantic namespace branches commands."""

import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
BRANCHES = f"{BASE_URL}/api/semantics/experimental/namespaces/sales/branches"

BRANCH = {
    "name": "add-credit-limit",
    "namespace": "sales",
    "branch_namespace": "branch-sales-add-credit-limit",
    "behind_target": False,
    "conflicted": False,
    "conflicts": [],
}

YAML_BODY = """version: 1.0.0
name: sales
ontology:
- concept:
    id: credit-limit
    name: Credit Limit
    type: ValueType
"""


@pytest.fixture(autouse=True)
def api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@respx.mock
def test_branches_list_as_table_and_json():
    respx.get(BRANCHES).mock(return_value=httpx.Response(200, json=[BRANCH]))
    result = runner.invoke(app, ["semantics", "branches", "list", "sales"])
    assert result.exit_code == 0
    assert "add-credit-limit" in result.output

    result = runner.invoke(app, ["semantics", "branches", "list", "sales", "-o", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["branch_namespace"] == "branch-sales-add-credit-limit"


@respx.mock
def test_branches_create_get_delete():
    respx.put(f"{BRANCHES}/add-credit-limit").mock(return_value=httpx.Response(200, json=BRANCH))
    respx.get(f"{BRANCHES}/add-credit-limit").mock(return_value=httpx.Response(200, json=BRANCH))
    respx.delete(f"{BRANCHES}/add-credit-limit").mock(return_value=httpx.Response(204))

    result = runner.invoke(app, ["semantics", "branches", "create", "sales", "add-credit-limit"])
    assert result.exit_code == 0
    assert "created" in result.output

    result = runner.invoke(app, ["semantics", "branches", "get", "sales", "add-credit-limit", "-o", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["namespace"] == "sales"

    result = runner.invoke(app, ["semantics", "branches", "delete", "sales", "add-credit-limit"])
    assert result.exit_code == 0
    assert "deleted" in result.output


@respx.mock
def test_branches_yaml_and_put(tmp_path):
    respx.get(f"{BRANCHES}/add-credit-limit/ontology.yaml").mock(
        return_value=httpx.Response(200, text=YAML_BODY, headers={"Content-Type": "application/yaml"})
    )
    respx.put(f"{BRANCHES}/add-credit-limit/ontology.yaml").mock(return_value=httpx.Response(200))

    result = runner.invoke(app, ["semantics", "branches", "yaml", "sales", "add-credit-limit"])
    assert result.exit_code == 0
    assert "id: credit-limit" in result.output
    assert respx.calls[0].request.headers["Accept"] == "application/yaml"

    edited = tmp_path / "sales.yaml"
    edited.write_text(YAML_BODY + "# kept as written\n")
    result = runner.invoke(app, ["semantics", "branches", "put", "sales", "add-credit-limit", "--file", str(edited)])
    assert result.exit_code == 0
    assert "updated" in result.output
    put = respx.calls[1].request
    assert put.headers["Content-Type"] == "application/yaml"
    assert put.content.decode() == edited.read_text()


@respx.mock
def test_branches_changes_and_rebase():
    changes = [
        {
            "external_id": "credit-limit",
            "element_type": "ValueType",
            "name": "Credit Limit",
            "op": "add",
            "impact": "additive",
            "warnings": [],
            "fields": [],
            "properties": [],
            "relationships": [],
        }
    ]
    respx.get(f"{BRANCHES}/add-credit-limit/changes").mock(return_value=httpx.Response(200, json=changes))
    respx.post(f"{BRANCHES}/add-credit-limit/rebase").mock(return_value=httpx.Response(200, json=BRANCH))

    result = runner.invoke(app, ["semantics", "branches", "changes", "sales", "add-credit-limit"])
    assert result.exit_code == 0
    assert "credit-limit" in result.output
    assert "additive" in result.output

    result = runner.invoke(app, ["semantics", "branches", "rebase", "sales", "add-credit-limit"])
    assert result.exit_code == 0
    assert "updated from namespace" in result.output


@respx.mock
def test_branches_merge_lands():
    respx.post(f"{BRANCHES}/add-credit-limit/merge").mock(return_value=httpx.Response(204))
    result = runner.invoke(app, ["semantics", "branches", "merge", "sales", "add-credit-limit"])
    assert result.exit_code == 0
    assert "merged into namespace" in result.output


@respx.mock
def test_branches_merge_opens_a_request():
    request = {
        "remote_id": "7",
        "type": "pull_request",
        "title": "Merge add-credit-limit into sales",
        "url": "https://github.com/test/repo/pull/7",
        "status": "open",
    }
    respx.post(f"{BRANCHES}/add-credit-limit/merge").mock(return_value=httpx.Response(200, json=request))
    result = runner.invoke(app, ["semantics", "branches", "merge", "sales", "add-credit-limit", "-o", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["url"] == "https://github.com/test/repo/pull/7"

    result = runner.invoke(app, ["semantics", "branches", "merge", "sales", "add-credit-limit"])
    assert result.exit_code == 0
    assert "The branch stays open" in result.output


@respx.mock
def test_branches_merge_surfaces_a_conflict():
    respx.post(f"{BRANCHES}/add-credit-limit/merge").mock(
        return_value=httpx.Response(409, json={"message": "Branch 'add-credit-limit' has no changes to merge"})
    )
    result = runner.invoke(app, ["semantics", "branches", "merge", "sales", "add-credit-limit"])
    assert result.exit_code != 0
    assert "no changes to merge" in result.output
