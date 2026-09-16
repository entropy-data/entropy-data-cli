"""Tests for the data contract branches commands and the --branch flags on data contract commands."""

import json

import pytest
import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
BRANCHES = f"{BASE_URL}/api/datacontracts/orders/branches"

BRANCH = {
    "name": "add-status",
    "data_contract_id": "orders",
    "branch_data_contract_id": "branch-orders-add-status",
    "version": "1.0.0",
    "target_version": "1.0.0",
    "version_state": "needsBump",
    "suggested_step": "minor",
    "suggested_version": "1.1.0",
    "breaking_changes": [],
    "change_count": 1,
    "behind_target": False,
    "conflicted": False,
    "conflicts": [],
}

YAML_BODY = """apiVersion: v3.0.2
kind: DataContract
id: orders
name: Orders
version: 1.0.0
"""


@pytest.fixture(autouse=True)
def api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_branches_list_as_table_and_json():
    responses.add(responses.GET, BRANCHES, json=[BRANCH], status=200)
    result = runner.invoke(app, ["datacontracts", "branches", "list", "orders"])
    assert result.exit_code == 0
    assert "add-status" in result.output
    assert "needsBump" in result.output

    result = runner.invoke(app, ["datacontracts", "branches", "list", "orders", "-o", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["name"] == "add-status"


@responses.activate
def test_branches_create_get_delete():
    responses.add(responses.PUT, f"{BRANCHES}/add-status", json=BRANCH, status=200)
    responses.add(responses.GET, f"{BRANCHES}/add-status", json=BRANCH, status=200)
    responses.add(responses.DELETE, f"{BRANCHES}/add-status", status=204)

    result = runner.invoke(app, ["datacontracts", "branches", "create", "orders", "add-status"])
    assert result.exit_code == 0
    assert "created" in result.output

    result = runner.invoke(app, ["datacontracts", "branches", "get", "orders", "add-status", "-o", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["suggested_version"] == "1.1.0"

    result = runner.invoke(app, ["datacontracts", "branches", "delete", "orders", "add-status"])
    assert result.exit_code == 0
    assert "deleted" in result.output


@responses.activate
def test_branches_yaml_and_put(tmp_path):
    responses.add(
        responses.GET,
        f"{BRANCHES}/add-status/datacontract.yaml",
        body=YAML_BODY,
        content_type="application/yaml",
        status=200,
    )
    responses.add(responses.PUT, f"{BRANCHES}/add-status/datacontract.yaml", status=200)

    result = runner.invoke(app, ["datacontracts", "branches", "yaml", "orders", "add-status"])
    assert result.exit_code == 0
    assert "kind: DataContract" in result.output
    assert responses.calls[0].request.headers["Accept"] == "application/yaml"

    edited = tmp_path / "orders.yaml"
    edited.write_text(YAML_BODY.replace("1.0.0", "1.1.0") + "# kept as written\n")
    result = runner.invoke(app, ["datacontracts", "branches", "put", "orders", "add-status", "--file", str(edited)])
    assert result.exit_code == 0
    assert "updated" in result.output
    put = responses.calls[1].request
    assert put.headers["Content-Type"] == "application/yaml"
    assert put.body.decode() == edited.read_text()


@responses.activate
def test_branches_changes_and_rebase():
    changes = [
        {
            "key": "property:ORDERS/STATUS",
            "element_type": "property",
            "path": "schema.ORDERS.STATUS",
            "name": "STATUS",
            "op": "add",
            "impact": "structural",
            "fields": [],
        }
    ]
    responses.add(responses.GET, f"{BRANCHES}/add-status/changes", json=changes, status=200)
    responses.add(responses.POST, f"{BRANCHES}/add-status/rebase", json={**BRANCH, "behind_target": False}, status=200)

    result = runner.invoke(app, ["datacontracts", "branches", "changes", "orders", "add-status"])
    assert result.exit_code == 0
    assert "property:ORDERS/STATUS" in result.output
    assert "structural" in result.output

    result = runner.invoke(app, ["datacontracts", "branches", "rebase", "orders", "add-status"])
    assert result.exit_code == 0
    assert "updated from data contract" in result.output


@responses.activate
def test_branches_merge_lands_with_version_and_route():
    responses.add(responses.POST, f"{BRANCHES}/add-status/merge", status=204)
    result = runner.invoke(
        app,
        [
            "datacontracts", "branches", "merge", "orders", "add-status",
            "--version", "1.1.0", "--route", "land", "--no-update-ports",
        ],
    )  # fmt: skip
    assert result.exit_code == 0
    assert "merged into data contract" in result.output
    assert json.loads(responses.calls[0].request.body) == {
        "update_port_versions": False,
        "version": "1.1.0",
        "route": "land",
    }


@responses.activate
def test_branches_merge_opens_a_request():
    request = {
        "remote_id": "7",
        "type": "pull_request",
        "title": "Merge add-status into Orders",
        "url": "https://github.com/test/repo/pull/7",
        "status": "open",
        "mergeability": "mergeable",
        "comment_count": 0,
    }
    responses.add(responses.POST, f"{BRANCHES}/add-status/merge", json=request, status=200)
    result = runner.invoke(
        app, ["datacontracts", "branches", "merge", "orders", "add-status", "--route", "pull_request", "-o", "json"]
    )
    assert result.exit_code == 0
    assert "The branch stays open" in result.output
    assert "https://github.com/test/repo/pull/7" in result.output
    assert json.loads(responses.calls[0].request.body) == {"update_port_versions": True, "route": "pull_request"}


def test_branches_merge_rejects_an_unknown_route():
    result = runner.invoke(app, ["datacontracts", "branches", "merge", "orders", "add-status", "--route", "sideways"])
    assert result.exit_code != 0
    assert "land, pull_request" in result.output


@responses.activate
def test_branches_merge_surfaces_a_refusal():
    responses.add(
        responses.POST,
        f"{BRANCHES}/add-status/merge",
        json={"message": "Branch 'add-status' is still at version '1.0.0'"},
        status=422,
    )
    result = runner.invoke(app, ["datacontracts", "branches", "merge", "orders", "add-status"])
    assert result.exit_code != 0
    assert "1.0.0" in result.output


@responses.activate
def test_datacontract_commands_take_a_branch():
    responses.add(responses.POST, f"{BRANCHES}/add-status/test", json={"result": "passed"}, status=200)
    responses.add(
        responses.GET,
        f"{BRANCHES}/add-status/datacontract.yaml",
        body=YAML_BODY,
        content_type="application/yaml",
        status=200,
    )
    responses.add(
        responses.POST,
        f"{BRANCHES}/add-status/generate",
        json={"dataContractId": "orders", "generationType": "sql-ddl", "files": []},
        status=200,
    )

    result = runner.invoke(app, ["datacontracts", "test", "orders", "--branch", "add-status", "--server", "prod"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"result": "passed"}
    assert responses.calls[0].request.params == {"server": "prod"}

    result = runner.invoke(app, ["datacontracts", "yaml", "orders", "-b", "add-status"])
    assert result.exit_code == 0
    assert "kind: DataContract" in result.output

    result = runner.invoke(app, ["datacontracts", "generate", "orders", "--type", "sql-ddl", "--branch", "add-status"])
    assert result.exit_code == 0
    assert json.loads(result.output)["generationType"] == "sql-ddl"


def test_branch_names_are_validated():
    result = runner.invoke(app, ["datacontracts", "yaml", "orders", "--branch", "../main"])
    assert result.exit_code != 0
    assert "path traversal" in result.output
