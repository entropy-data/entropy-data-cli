"""Tests for settings commands."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

CUSTOMIZATION_YAML = """dataProduct:
  customFilters:
    - displayName: Status
      customField: status
"""

CUSTOMIZATION_JSON = {"dataProduct": {"customFilters": [{"displayName": "Status", "customField": "status"}]}}


@respx.mock
def test_settings_get_customization_yaml(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/settings/customization").mock(
        return_value=httpx.Response(200, text=CUSTOMIZATION_YAML, headers={"Content-Type": "application/yaml"})
    )
    result = runner.invoke(app, ["settings", "get-customization"])
    assert result.exit_code == 0
    assert "customFilters" in result.output


@respx.mock
def test_settings_get_customization_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/settings/customization").mock(return_value=httpx.Response(200, json=CUSTOMIZATION_JSON))
    result = runner.invoke(app, ["settings", "get-customization", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "dataProduct" in data


@respx.mock
def test_settings_put_customization_yaml(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/settings/customization").mock(return_value=httpx.Response(200))
    yaml_file = tmp_path / "customization.yaml"
    yaml_file.write_text(CUSTOMIZATION_YAML)
    result = runner.invoke(app, ["settings", "put-customization", "--file", str(yaml_file)])
    assert result.exit_code == 0
    assert "updated" in result.output
    assert respx.calls[0].request.headers["Content-Type"] == "application/yaml"


@respx.mock
def test_settings_put_customization_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/settings/customization").mock(return_value=httpx.Response(200))
    json_file = tmp_path / "customization.json"
    json_file.write_text(json.dumps(CUSTOMIZATION_JSON))
    result = runner.invoke(app, ["settings", "put-customization", "--file", str(json_file)])
    assert result.exit_code == 0
    assert "updated" in result.output
    assert respx.calls[0].request.headers["Content-Type"] == "application/json"


SCIM_MAPPING_YAML = """scimGroupMappings:
  - scimGroup: admins
    type: organizationOwner
"""

SCIM_MAPPING_JSON = {
    "scimGroupMappings": [{"scimGroup": "admins", "type": "organizationOwner"}],
}


@respx.mock
def test_settings_get_scim_mapping_yaml(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/settings/scim-mapping").mock(
        return_value=httpx.Response(200, text=SCIM_MAPPING_YAML, headers={"Content-Type": "application/yaml"})
    )
    result = runner.invoke(app, ["settings", "get-scim-mapping"])
    assert result.exit_code == 0
    assert "scimGroupMappings" in result.output


@respx.mock
def test_settings_get_scim_mapping_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/settings/scim-mapping").mock(return_value=httpx.Response(200, json=SCIM_MAPPING_JSON))
    result = runner.invoke(app, ["settings", "get-scim-mapping", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "scimGroupMappings" in data


@respx.mock
def test_settings_put_scim_mapping_yaml(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/settings/scim-mapping").mock(return_value=httpx.Response(200))
    yaml_file = tmp_path / "mapping.yaml"
    yaml_file.write_text(SCIM_MAPPING_YAML)
    result = runner.invoke(app, ["settings", "put-scim-mapping", "--file", str(yaml_file)])
    assert result.exit_code == 0
    assert "updated" in result.output
    assert respx.calls[0].request.headers["Content-Type"] == "application/yaml"


@respx.mock
def test_settings_put_scim_mapping_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/settings/scim-mapping").mock(return_value=httpx.Response(200))
    json_file = tmp_path / "mapping.json"
    json_file.write_text(json.dumps(SCIM_MAPPING_JSON))
    result = runner.invoke(app, ["settings", "put-scim-mapping", "--file", str(json_file)])
    assert result.exit_code == 0
    assert respx.calls[0].request.headers["Content-Type"] == "application/json"


def test_settings_help():
    result = runner.invoke(app, ["settings", "--help"])
    assert result.exit_code == 0
    assert "get-customization" in result.output
    assert "put-customization" in result.output
    assert "get-scim-mapping" in result.output
    assert "put-scim-mapping" in result.output
