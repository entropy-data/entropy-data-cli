"""Tests for data product builders commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
BUILDER_ID = "dbt"

BUILDERS_LIST = [
    {
        "id": BUILDER_ID,
        "name": "dbt",
        "pluginRepository": "https://github.com/example/dbt-builder",
        "supportedAgents": ["claude_code"],
    },
    {"id": "snowflake", "name": "Snowflake"},
]


@responses.activate
def test_dataproductbuilders_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/dataproductbuilders", json=BUILDERS_LIST, status=200)
    result = runner.invoke(app, ["dataproductbuilders", "list"])
    assert result.exit_code == 0
    assert "dbt" in result.output
    assert "Snowflake" in result.output


@responses.activate
def test_dataproductbuilders_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/dataproductbuilders", json=BUILDERS_LIST, status=200)
    result = runner.invoke(app, ["dataproductbuilders", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@responses.activate
def test_dataproductbuilders_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/dataproductbuilders/{BUILDER_ID}",
        json=BUILDERS_LIST[0],
        status=200,
    )
    result = runner.invoke(app, ["dataproductbuilders", "get", BUILDER_ID])
    assert result.exit_code == 0
    assert "dbt" in result.output


@responses.activate
def test_dataproductbuilders_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/dataproductbuilders/{BUILDER_ID}",
        json=BUILDERS_LIST[0],
        status=200,
    )
    builder_file = tmp_path / "builder.yaml"
    builder_file.write_text("name: dbt\nsupportedAgents:\n  - claude_code\n")
    result = runner.invoke(app, ["dataproductbuilders", "put", BUILDER_ID, "--file", str(builder_file)])
    assert result.exit_code == 0
    assert "saved" in result.output
    assert json.loads(responses.calls[0].request.body) == {"name": "dbt", "supportedAgents": ["claude_code"]}


@responses.activate
def test_dataproductbuilders_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/dataproductbuilders/{BUILDER_ID}", status=200)
    result = runner.invoke(app, ["dataproductbuilders", "delete", BUILDER_ID])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_dataproductbuilders_help():
    result = runner.invoke(app, ["dataproductbuilders", "--help"])
    assert result.exit_code == 0
    for command in ("list", "get", "put", "delete"):
        assert command in result.output
