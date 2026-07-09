"""Tests for schemas commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

ODCS_SCHEMA = {"$schema": "https://json-schema.org/draft/2019-09/schema", "title": "ODCS", "type": "object"}
ODPS_CUSTOM_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2019-09/schema",
    "allOf": [{"title": "ODPS"}, {"properties": {"status": {"enum": ["active", "retired"]}}}],
}


def _configure(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_schemas_get_odcs(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/schemas/odcs.schema.json",
        json=ODCS_SCHEMA,
        status=200,
        headers={"X-Schema-Version": "3.1.0"},
    )
    result = runner.invoke(app, ["schemas", "get", "odcs"])
    assert result.exit_code == 0
    assert json.loads(result.output)["title"] == "ODCS"


@responses.activate
def test_schemas_get_custom(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/schemas/odps-custom.schema.json",
        json=ODPS_CUSTOM_SCHEMA,
        status=200,
        headers={"X-Schema-Version": "1.0.0"},
    )
    result = runner.invoke(app, ["schemas", "get", "odps", "--custom"])
    assert result.exit_code == 0
    assert json.loads(result.output)["allOf"][1]["properties"]["status"]["enum"] == ["active", "retired"]


@responses.activate
def test_schemas_get_pinned_version(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/schemas/odcs-3.1.0.schema.json",
        json=ODCS_SCHEMA,
        status=200,
        headers={"X-Schema-Version": "3.1.0"},
    )
    result = runner.invoke(app, ["schemas", "get", "odcs", "--version", "3.1.0"])
    assert result.exit_code == 0
    assert json.loads(result.output)["title"] == "ODCS"


@responses.activate
def test_schemas_get_pinned_version_custom(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/schemas/odps-1.0.0-custom.schema.json",
        json=ODPS_CUSTOM_SCHEMA,
        status=200,
        headers={"X-Schema-Version": "1.0.0"},
    )
    result = runner.invoke(app, ["schemas", "get", "odps", "--version", "1.0.0", "--custom"])
    assert result.exit_code == 0
    assert "allOf" in json.loads(result.output)


@responses.activate
def test_schemas_get_writes_file_with_served_version(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/schemas/odcs-custom.schema.json",
        json=ODCS_SCHEMA,
        status=200,
        headers={"X-Schema-Version": "3.1.0"},
    )
    out_file = tmp_path / "odcs-custom.schema.json"
    result = runner.invoke(app, ["schemas", "get", "odcs", "--custom", "--file", str(out_file)])
    assert result.exit_code == 0
    assert "3.1.0" in result.output
    assert json.loads(out_file.read_text())["title"] == "ODCS"


@responses.activate
def test_schemas_get_unknown_version_returns_error(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/schemas/odcs-9.9.9.schema.json",
        json={"detail": "Schema version 9.9.9 is not available for odcs"},
        status=404,
    )
    result = runner.invoke(app, ["schemas", "get", "odcs", "--version", "9.9.9"])
    assert result.exit_code == 1
    assert "9.9.9" in result.output


def test_schemas_get_invalid_version_format(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    result = runner.invoke(app, ["schemas", "get", "odcs", "--version", "latest"])
    assert result.exit_code == 1
    assert "Invalid schema version" in result.output


def test_schemas_get_invalid_spec(monkeypatch, tmp_path):
    _configure(monkeypatch, tmp_path)
    result = runner.invoke(app, ["schemas", "get", "dcs"])
    assert result.exit_code == 2
