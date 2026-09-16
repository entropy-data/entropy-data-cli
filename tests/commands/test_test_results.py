"""Tests for test-results commands."""

import json

import pytest
import responses
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


@responses.activate
def test_publish_to_the_data_contract(tmp_path):
    responses.add(responses.POST, f"{BASE_URL}/api/test-results", status=201)
    body = tmp_path / "results.json"
    body.write_text(json.dumps(RESULTS))
    result = runner.invoke(app, ["test-results", "publish", "--file", str(body)])
    assert result.exit_code == 0
    assert "published" in result.output
    assert json.loads(responses.calls[0].request.body) == RESULTS


@responses.activate
def test_publish_onto_a_branch(tmp_path):
    responses.add(responses.POST, f"{BASE_URL}/api/datacontracts/orders/branches/add-status/test-results", status=201)
    body = tmp_path / "results.json"
    body.write_text(json.dumps(RESULTS))
    result = runner.invoke(
        app,
        ["test-results", "publish", "--file", str(body), "--data-contract-id", "orders", "--branch", "add-status"],
    )
    assert result.exit_code == 0
    assert "branch 'add-status'" in result.output
    assert json.loads(responses.calls[0].request.body) == RESULTS


def test_publish_needs_both_the_data_contract_and_the_branch(tmp_path):
    body = tmp_path / "results.json"
    body.write_text(json.dumps(RESULTS))
    result = runner.invoke(app, ["test-results", "publish", "--file", str(body), "--branch", "add-status"])
    assert result.exit_code != 0
    assert "go together" in result.output


@responses.activate
def test_list_narrows_to_a_branch():
    responses.add(responses.GET, f"{BASE_URL}/api/test-results", json=[{"id": "r1", **RESULTS}], status=200)
    result = runner.invoke(
        app, ["test-results", "list", "--data-contract-id", "orders", "--branch", "add-status", "-o", "json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)[0]["id"] == "r1"
    assert responses.calls[0].request.params == {"p": "0", "dataContractId": "orders", "branch": "add-status"}


def test_list_branch_needs_the_data_contract():
    result = runner.invoke(app, ["test-results", "list", "--branch", "add-status"])
    assert result.exit_code != 0
    assert "narrows the runs of one data contract" in result.output
