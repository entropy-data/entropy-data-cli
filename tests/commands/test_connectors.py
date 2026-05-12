"""Tests for connectors commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

CONNECTORS_LIST = [
    {"id": "databricks-prod", "info": {"type": "databricks", "connectorVersion": "1.0.0"}},
    {"id": "snowflake-eu", "info": {"type": "snowflake", "connectorVersion": "2.1.3"}},
]


@responses.activate
def test_connectors_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/connectors", json=CONNECTORS_LIST, status=200)
    result = runner.invoke(app, ["connectors", "list"])
    assert result.exit_code == 0
    assert "databricks-prod" in result.output
    assert "snowflake" in result.output


@responses.activate
def test_connectors_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/connectors/databricks-prod",
        json=CONNECTORS_LIST[0],
        status=200,
    )
    result = runner.invoke(app, ["connectors", "get", "databricks-prod", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "databricks-prod"


@responses.activate
def test_connectors_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{BASE_URL}/api/connectors/databricks-prod", status=200)
    body_file = tmp_path / "connector.json"
    body_file.write_text(json.dumps(CONNECTORS_LIST[0]))
    result = runner.invoke(app, ["connectors", "put", "databricks-prod", "--file", str(body_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@responses.activate
def test_connectors_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/connectors/databricks-prod", status=200)
    result = runner.invoke(app, ["connectors", "delete", "databricks-prod"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_connectors_help():
    result = runner.invoke(app, ["connectors", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "get", "put", "delete"):
        assert cmd in result.output
