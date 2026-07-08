"""Tests for classifications commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

SCHEMES = [
    {
        "externalId": "classification",
        "name": "Classification",
        "customProperty": "classification",
        "description": "Sensitivity and confidentiality of the data.",
        "classifications": [
            {"externalId": "public", "name": "Public", "level": 1},
            {"externalId": "sensitive", "name": "Sensitive", "level": 4},
        ],
    },
    {"externalId": "gdpr", "name": "GDPR", "description": "GDPR categories."},
]


@responses.activate
def test_classifications_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/classification-schemes", json=SCHEMES, status=200)
    result = runner.invoke(app, ["classifications", "list"])
    assert result.exit_code == 0
    assert "classification" in result.output
    assert "GDPR" in result.output


@responses.activate
def test_classifications_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/classification-schemes", json=SCHEMES, status=200)
    result = runner.invoke(app, ["classifications", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@responses.activate
def test_classifications_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/classification-schemes/classification",
        json=SCHEMES[0],
        status=200,
    )
    result = runner.invoke(app, ["classifications", "get", "classification"])
    assert result.exit_code == 0
    assert "Classification" in result.output


@responses.activate
def test_classifications_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{BASE_URL}/api/classification-schemes/classification", status=200)
    scheme_file = tmp_path / "scheme.json"
    scheme_file.write_text(json.dumps(SCHEMES[0]))
    result = runner.invoke(app, ["classifications", "put", "classification", "--file", str(scheme_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@responses.activate
def test_classifications_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/classification-schemes/classification", status=200)
    result = runner.invoke(app, ["classifications", "delete", "classification"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_classifications_help():
    result = runner.invoke(app, ["classifications", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "put" in result.output
    assert "delete" in result.output
