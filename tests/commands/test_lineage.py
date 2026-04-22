"""Tests for lineage commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

LINEAGE_EVENTS = [
    {
        "eventType": "COMPLETE",
        "eventTime": "2024-01-01T00:00:00Z",
        "job": {"namespace": "my-namespace", "name": "my-job"},
        "run": {"runId": "run-1"},
    },
]


@responses.activate
def test_lineage_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/lineage", json=LINEAGE_EVENTS, status=200)
    result = runner.invoke(app, ["lineage", "list"])
    assert result.exit_code == 0
    assert "COMPLETE" in result.output


@responses.activate
def test_lineage_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/lineage", json=LINEAGE_EVENTS, status=200)
    result = runner.invoke(app, ["lineage", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


@responses.activate
def test_lineage_list_with_filters(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/lineage", json=LINEAGE_EVENTS, status=200)
    result = runner.invoke(
        app, ["lineage", "list", "--job-namespace", "my-namespace", "--job-name", "my-job", "--event-type", "COMPLETE"]
    )
    assert result.exit_code == 0


@responses.activate
def test_lineage_submit(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/v1/lineage", status=200)
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(LINEAGE_EVENTS[0]))
    result = runner.invoke(app, ["lineage", "submit", "--file", str(event_file)])
    assert result.exit_code == 0
    assert "submitted" in result.output


@responses.activate
def test_lineage_submit_with_data_product(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/v1/lineage", status=200)
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(LINEAGE_EVENTS[0]))
    result = runner.invoke(
        app,
        ["lineage", "submit", "--file", str(event_file), "--data-product-id", "dp-1", "--output-port-name", "port-1"],
    )
    assert result.exit_code == 0


@responses.activate
def test_lineage_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/v1/lineage", json={}, status=200)
    result = runner.invoke(app, ["lineage", "delete", "--run-id", "run-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_lineage_help():
    result = runner.invoke(app, ["lineage", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "submit" in result.output
    assert "delete" in result.output
