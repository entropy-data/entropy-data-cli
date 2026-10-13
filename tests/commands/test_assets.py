"""Tests for assets commands."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

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


@respx.mock
def test_assets_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/assets").mock(return_value=httpx.Response(200, json=ASSETS_LIST))
    result = runner.invoke(app, ["assets", "list"])
    assert result.exit_code == 0
    assert "asset-1" in result.output
    assert "my_table" in result.output


@respx.mock
def test_assets_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/assets").mock(return_value=httpx.Response(200, json=ASSETS_LIST))
    result = runner.invoke(app, ["assets", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@respx.mock
def test_assets_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/assets/asset-1").mock(return_value=httpx.Response(200, json=ASSETS_LIST[0]))
    result = runner.invoke(app, ["assets", "get", "asset-1"])
    assert result.exit_code == 0
    assert "asset-1" in result.output


@respx.mock
def test_assets_get_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/assets/asset-1").mock(return_value=httpx.Response(200, json=ASSETS_LIST[0]))
    result = runner.invoke(app, ["assets", "get", "asset-1", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "asset-1"


@respx.mock
def test_assets_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/assets/asset-1").mock(return_value=httpx.Response(200))
    asset_file = tmp_path / "asset.json"
    asset_file.write_text(json.dumps(ASSETS_LIST[0]))
    result = runner.invoke(app, ["assets", "put", "asset-1", "--file", str(asset_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@respx.mock
def test_assets_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{BASE_URL}/api/assets/asset-1").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["assets", "delete", "asset-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output


@respx.mock
def test_assets_tags_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/assets/asset-1/assigned-tags").mock(
        return_value=httpx.Response(200, json=["pii:true", "governance/internal"])
    )
    result = runner.invoke(app, ["assets", "tags", "list", "asset-1"])
    assert result.exit_code == 0
    assert "pii:true" in result.output
    assert "governance/internal" in result.output


@respx.mock
def test_assets_tags_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/assets/asset-1/assigned-tags").mock(return_value=httpx.Response(200, json=["pii:true"]))
    result = runner.invoke(app, ["assets", "tags", "list", "asset-1", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == ["pii:true"]


@respx.mock
def test_assets_tags_add(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/assets/asset-1/assigned-tags/governance/PII").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["assets", "tags", "add", "asset-1", "governance/PII"])
    assert result.exit_code == 0
    assert "assigned" in result.output


@respx.mock
def test_assets_tags_remove(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{BASE_URL}/api/assets/asset-1/assigned-tags/governance/PII").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["assets", "tags", "remove", "asset-1", "governance/PII"])
    assert result.exit_code == 0
    assert "removed" in result.output


def test_assets_help():
    result = runner.invoke(app, ["assets", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "put" in result.output
    assert "delete" in result.output
    assert "tags" in result.output
