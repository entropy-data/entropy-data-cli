"""Tests for settings commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data_cli.config as cfg
from entropy_data_cli.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

CUSTOMIZATION_YAML = """dataProduct:
  customFilters:
    - displayName: Status
      customField: status
"""

CUSTOMIZATION_JSON = {"dataProduct": {"customFilters": [{"displayName": "Status", "customField": "status"}]}}


@responses.activate
def test_settings_get_customization_yaml(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/settings/customization",
        body=CUSTOMIZATION_YAML,
        content_type="application/yaml",
        status=200,
    )
    result = runner.invoke(app, ["settings", "get-customization"])
    assert result.exit_code == 0
    assert "customFilters" in result.output


@responses.activate
def test_settings_get_customization_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/settings/customization",
        json=CUSTOMIZATION_JSON,
        status=200,
    )
    result = runner.invoke(app, ["settings", "get-customization", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "dataProduct" in data


@responses.activate
def test_settings_put_customization_yaml(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{BASE_URL}/api/settings/customization", status=200)
    yaml_file = tmp_path / "customization.yaml"
    yaml_file.write_text(CUSTOMIZATION_YAML)
    result = runner.invoke(app, ["settings", "put-customization", "--file", str(yaml_file)])
    assert result.exit_code == 0
    assert "updated" in result.output
    assert responses.calls[0].request.headers["Content-Type"] == "application/yaml"


@responses.activate
def test_settings_put_customization_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{BASE_URL}/api/settings/customization", status=200)
    json_file = tmp_path / "customization.json"
    json_file.write_text(json.dumps(CUSTOMIZATION_JSON))
    result = runner.invoke(app, ["settings", "put-customization", "--file", str(json_file)])
    assert result.exit_code == 0
    assert "updated" in result.output
    assert responses.calls[0].request.headers["Content-Type"] == "application/json"


def test_settings_help():
    result = runner.invoke(app, ["settings", "--help"])
    assert result.exit_code == 0
    assert "get-customization" in result.output
    assert "put-customization" in result.output
