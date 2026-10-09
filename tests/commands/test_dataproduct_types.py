"""Tests for the settings dataproduct-types commands."""

import json

import responses
import yaml
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
URL = f"{BASE_URL}/api/settings/dataproduct-types"

DOCUMENT = {
    "dataProductTypes": [
        {
            "id": "source-aligned",
            "outputPorts": True,
            "behavior": "data-product",
            "labels": {"en": "Source-aligned"},
            "enabled": True,
            "default": True,
            "builtIn": False,
        },
        {
            "id": "dashboard",
            "outputPorts": False,
            "behavior": "data-consumer",
            "labels": {"en": "Dashboard"},
            "enabled": False,
            "default": False,
            "builtIn": False,
        },
    ]
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_dataproduct_types_get_table(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, URL, json=DOCUMENT, status=200)
    monkeypatch.setenv("COLUMNS", "200")
    result = runner.invoke(app, ["settings", "dataproduct-types", "get"])
    assert result.exit_code == 0, result.output
    assert "source-aligned" in result.output
    assert "Dashboard" in result.output
    assert "data-consumer" in result.output


@responses.activate
def test_dataproduct_types_get_yaml(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, URL, json=DOCUMENT, status=200)
    result = runner.invoke(app, ["settings", "dataproduct-types", "get", "--output", "yaml"])
    assert result.exit_code == 0, result.output
    assert yaml.safe_load(result.output) == DOCUMENT


@responses.activate
def test_dataproduct_types_put_yaml(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, URL, json=DOCUMENT, status=200)
    file = tmp_path / "types.yaml"
    file.write_text(yaml.safe_dump(DOCUMENT))
    result = runner.invoke(app, ["settings", "dataproduct-types", "put", "--file", str(file)])
    assert result.exit_code == 0, result.output
    assert "saved" in result.output
    request = responses.calls[0].request
    assert request.headers["Content-Type"] == "application/yaml"
    assert yaml.safe_load(request.body) == DOCUMENT


@responses.activate
def test_dataproduct_types_put_json(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, URL, json=DOCUMENT, status=200)
    file = tmp_path / "types.json"
    file.write_text(json.dumps(DOCUMENT))
    result = runner.invoke(app, ["settings", "dataproduct-types", "put", "--file", str(file)])
    assert result.exit_code == 0, result.output
    assert responses.calls[0].request.headers["Content-Type"] == "application/json"


@responses.activate
def test_dataproduct_types_put_validation_error(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, URL, json={"detail": "Exactly one type must be the default."}, status=422)
    file = tmp_path / "types.yaml"
    file.write_text(yaml.safe_dump(DOCUMENT))
    result = runner.invoke(app, ["settings", "dataproduct-types", "put", "--file", str(file)])
    assert result.exit_code == 1
