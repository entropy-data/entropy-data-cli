"""Tests for usage commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data_cli.config as cfg
from entropy_data_cli.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

TRACES_DATA = [{"resourceSpans": []}]


@responses.activate
def test_usage_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/traces", json=TRACES_DATA, status=200)
    result = runner.invoke(app, ["usage", "list"])
    assert result.exit_code == 0


@responses.activate
def test_usage_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/traces", json=TRACES_DATA, status=200)
    result = runner.invoke(app, ["usage", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)


@responses.activate
def test_usage_list_with_filters(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/traces", json=TRACES_DATA, status=200)
    result = runner.invoke(app, ["usage", "list", "--scope-name", "usage", "--data-product-id", "dp-1"])
    assert result.exit_code == 0


@responses.activate
def test_usage_submit(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/v1/traces", status=200)
    traces_file = tmp_path / "traces.json"
    traces_file.write_text(json.dumps({"resourceSpans": []}))
    result = runner.invoke(app, ["usage", "submit", "--file", str(traces_file)])
    assert result.exit_code == 0
    assert "submitted" in result.output


@responses.activate
def test_usage_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/v1/traces", json={"deletedCount": 5}, status=200)
    result = runner.invoke(app, ["usage", "delete", "--data-product-id", "dp-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output
    assert "5" in result.output


def test_usage_help():
    result = runner.invoke(app, ["usage", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "submit" in result.output
    assert "delete" in result.output
