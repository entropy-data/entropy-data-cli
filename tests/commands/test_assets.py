"""Tests for assets commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data_cli.config as cfg
from entropy_data_cli.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

ASSETS_LIST = [
    {
        "id": "asset-1",
        "info": {"name": "my_table", "type": "snowflake_table", "source": "snowflake", "owner": "team-456"},
    },
    {
        "id": "asset-2",
        "info": {"name": "orders", "type": "databricks_table", "source": "databricks", "owner": "team-789"},
    },
]


@responses.activate
def test_assets_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/assets", json=ASSETS_LIST, status=200)
    result = runner.invoke(app, ["assets", "list"])
    assert result.exit_code == 0
    assert "asset-1" in result.output
    assert "my_table" in result.output


@responses.activate
def test_assets_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/assets", json=ASSETS_LIST, status=200)
    result = runner.invoke(app, ["assets", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@responses.activate
def test_assets_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/assets/asset-1", json=ASSETS_LIST[0], status=200)
    result = runner.invoke(app, ["assets", "get", "asset-1"])
    assert result.exit_code == 0
    assert "asset-1" in result.output


@responses.activate
def test_assets_get_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/assets/asset-1", json=ASSETS_LIST[0], status=200)
    result = runner.invoke(app, ["assets", "get", "asset-1", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "asset-1"


@responses.activate
def test_assets_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{BASE_URL}/api/assets/asset-1", status=200)
    asset_file = tmp_path / "asset.json"
    asset_file.write_text(json.dumps(ASSETS_LIST[0]))
    result = runner.invoke(app, ["assets", "put", "asset-1", "--file", str(asset_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@responses.activate
def test_assets_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/assets/asset-1", status=200)
    result = runner.invoke(app, ["assets", "delete", "asset-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_assets_help():
    result = runner.invoke(app, ["assets", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "put" in result.output
    assert "delete" in result.output
