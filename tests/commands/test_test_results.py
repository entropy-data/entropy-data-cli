"""Tests for test-results commands."""

import json

import httpx
import pytest
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

RESULTS = {
    "dataContractId": "orders",
    "server": "prod",
    "result": "passed",
    "checks": [],
}


@pytest.fixture(autouse=True)
def api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@respx.mock
def test_publish_to_the_data_contract(tmp_path):
    respx.post(f"{BASE_URL}/api/test-results").mock(return_value=httpx.Response(201))
    body = tmp_path / "results.json"
    body.write_text(json.dumps(RESULTS))
    result = runner.invoke(app, ["test-results", "publish", "--file", str(body)])
    assert result.exit_code == 0
    assert "published" in result.output
    assert json.loads(respx.calls[0].request.content) == RESULTS


@respx.mock
def test_publish_onto_a_branch(tmp_path):
    respx.post(f"{BASE_URL}/api/datacontracts/orders/branches/add-status/test-results").mock(
        return_value=httpx.Response(201)
    )
    body = tmp_path / "results.json"
    body.write_text(json.dumps(RESULTS))
    result = runner.invoke(
        app,
        ["test-results", "publish", "--file", str(body), "--data-contract-id", "orders", "--branch", "add-status"],
    )
    assert result.exit_code == 0
    assert "published onto branch" in result.output
    assert json.loads(respx.calls[0].request.content) == RESULTS


def test_publish_needs_both_the_data_contract_and_the_branch(tmp_path):
    body = tmp_path / "results.json"
    body.write_text(json.dumps(RESULTS))
    result = runner.invoke(app, ["test-results", "publish", "--file", str(body), "--branch", "add-status"])
    assert result.exit_code != 0
    assert "go together" in result.output


@respx.mock
def test_list_narrows_to_a_branch():
    respx.get(f"{BASE_URL}/api/test-results").mock(return_value=httpx.Response(200, json=[{"id": "r1", **RESULTS}]))
    result = runner.invoke(
        app, ["test-results", "list", "--data-contract-id", "orders", "--branch", "add-status", "-o", "json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["id"] == "r1"
    assert dict(respx.calls[0].request.url.params) == {
        "p": "0",
        "size": "10",
        "dataContractId": "orders",
        "branch": "add-status",
    }


def test_list_branch_needs_the_data_contract():
    result = runner.invoke(app, ["test-results", "list", "--branch", "add-status"])
    assert result.exit_code != 0
    assert "narrows the runs of one data contract" in result.output


@respx.mock
def test_list_sends_the_time_range_and_page_size():
    respx.get(f"{BASE_URL}/api/test-results").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(app, ["test-results", "list", "--since", "2026-10-01", "--limit", "50"])
    assert result.exit_code == 0
    assert dict(respx.calls[0].request.url.params) == {"from": "2026-10-01T00:00:00Z", "p": "0", "size": "50"}


@respx.mock
def test_list_filters_by_time_locally_when_the_server_ignores_it():
    respx.get(f"{BASE_URL}/api/test-results").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"id": "new", **RESULTS, "timestampStart": "2026-10-05T10:00:00Z"},
                {"id": "old", **RESULTS, "timestampStart": "2026-09-01T10:00:00Z"},
            ],
            headers={"Link": '</api/test-results?p=1>; rel="next"'},
        )
    )
    result = runner.invoke(app, ["-o", "json", "test-results", "list", "--since", "2026-10-01"])
    assert result.exit_code == 0
    assert [r["id"] for r in json.loads(result.stdout)] == ["new"]
    assert "does not support all filters or the page size" in result.stderr


@respx.mock
def test_list_filters_by_server():
    respx.get(f"{BASE_URL}/api/test-results").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(app, ["test-results", "list", "--data-contract-id", "orders", "--server", "production"])
    assert result.exit_code == 0
    assert dict(respx.calls[0].request.url.params) == {
        "dataContractId": "orders",
        "server": "production",
        "p": "0",
        "size": "10",
    }


@respx.mock
def test_list_filters_by_server_locally_when_the_server_ignores_it():
    respx.get(f"{BASE_URL}/api/test-results").mock(
        return_value=httpx.Response(
            200, json=[{"id": "a", **RESULTS, "server": "production"}, {"id": "b", **RESULTS, "server": "staging"}]
        )
    )
    result = runner.invoke(app, ["-o", "json", "test-results", "list", "--server", "staging"])
    assert result.exit_code == 0
    assert [r["id"] for r in json.loads(result.stdout)] == ["b"]
    assert "does not support all filters or the page size" in result.stderr
