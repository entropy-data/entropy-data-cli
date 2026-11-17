"""Tests for settings output-port-types, organization features, usecases and custom-quality-checks."""

import json

import httpx
import pytest
import respx
import yaml
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
OUTPUT_PORT_TYPES = f"{BASE_URL}/api/settings/output-port-types"
FEATURES = f"{BASE_URL}/api/organization/features"
USECASES = f"{BASE_URL}/api/usecases"

PORT_TYPES = {
    "legacy": True,
    "onlyListedTypes": False,
    "outputPortTypes": [
        {"id": "snowflake", "label": "Snowflake", "enabled": True, "accessRequests": {"mode": "external-link"}},
        {"id": "kafka", "label": "", "enabled": False},
    ],
    "supportedOutputPortTypes": [{"dataProductType": "source-aligned", "outputPortTypes": ["snowflake"]}],
}
USECASE = {"apiVersion": "v0.1.0", "kind": "UseCase", "id": "churn", "name": "Churn prediction", "status": "active"}
USECASE_YAML = "# Owned by data science\napiVersion: v0.1.0\nkind: UseCase\nid: churn\nname: Churn prediction\n"


@pytest.fixture(autouse=True)
def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


def _text(output: str) -> str:
    return " ".join(output.split())


# --- settings output-port-types --------------------------------------------------------


@respx.mock
def test_output_port_types_get_table():
    respx.get(OUTPUT_PORT_TYPES).mock(return_value=httpx.Response(200, json=PORT_TYPES))
    result = runner.invoke(app, ["settings", "output-port-types", "get"])
    assert result.exit_code == 0, result.output
    out = _text(result.output)
    assert "snowflake" in out and "external-link" in out and "kafka" in out
    assert "legacy" in out
    assert "source-aligned: snowflake" in out


@respx.mock
def test_output_port_types_get_yaml_is_the_put_document():
    respx.get(OUTPUT_PORT_TYPES).mock(return_value=httpx.Response(200, json=PORT_TYPES))
    result = runner.invoke(app, ["settings", "output-port-types", "get", "-o", "yaml"])
    assert result.exit_code == 0, result.output
    assert yaml.safe_load(result.output) == PORT_TYPES


@respx.mock
def test_output_port_types_put_sends_yaml_as_written(tmp_path):
    route = respx.put(OUTPUT_PORT_TYPES).mock(return_value=httpx.Response(200))
    doc = tmp_path / "types.yaml"
    doc.write_text(yaml.safe_dump(PORT_TYPES))
    result = runner.invoke(app, ["settings", "output-port-types", "put", "--file", str(doc)])
    assert result.exit_code == 0, result.output
    request = route.calls.last.request
    assert request.headers["content-type"].startswith("application/yaml")
    assert yaml.safe_load(request.content) == PORT_TYPES


@respx.mock
def test_output_port_types_delete():
    route = respx.delete(OUTPUT_PORT_TYPES).mock(return_value=httpx.Response(204))
    result = runner.invoke(app, ["settings", "output-port-types", "delete"])
    assert result.exit_code == 0, result.output
    assert route.called
    assert "defaults apply again" in result.output


# --- organization features -------------------------------------------------------------


@respx.mock
def test_organization_features_get_table():
    respx.get(FEATURES).mock(
        return_value=httpx.Response(
            200, json={"changeProcessMode": "approval-required", "useCasesEnabled": True, "openInOptions": ["dbx"]}
        )
    )
    result = runner.invoke(app, ["organization", "features", "get"])
    assert result.exit_code == 0, result.output
    out = _text(result.output)
    assert "changeProcessMode │ approval-required" in out
    assert "useCasesEnabled │ True" in out
    assert '["dbx"]' in out


@respx.mock
def test_organization_features_put_sends_the_whole_document(tmp_path):
    route = respx.put(FEATURES).mock(return_value=httpx.Response(200, json={}))
    doc = tmp_path / "features.yaml"
    doc.write_text("useCasesEnabled: true\nmcpEnabled: false\n")
    result = runner.invoke(app, ["organization", "features", "put", "--file", str(doc)])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content) == {"useCasesEnabled": True, "mcpEnabled": False}


# --- usecases --------------------------------------------------------------------------


@respx.mock
def test_usecases_list_table():
    respx.get(USECASES).mock(return_value=httpx.Response(200, json=[{**USECASE, "team": {"name": "data-science"}}]))
    result = runner.invoke(app, ["usecases", "list"])
    assert result.exit_code == 0, result.output
    out = _text(result.output)
    assert "churn" in out and "active" in out and "data-science" in out


@respx.mock
def test_usecases_list_says_when_use_cases_are_off():
    respx.get(USECASES).mock(
        return_value=httpx.Response(404, json={"detail": "Use Cases are not enabled for this organization."})
    )
    result = runner.invoke(app, ["usecases", "list"])
    assert result.exit_code != 0
    assert "not enabled" in result.output


@respx.mock
def test_usecases_get_json():
    respx.get(f"{USECASES}/churn").mock(return_value=httpx.Response(200, json=USECASE))
    result = runner.invoke(app, ["usecases", "get", "churn", "-o", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["name"] == "Churn prediction"


@respx.mock
def test_usecases_yaml_asks_for_the_stored_yaml():
    route = respx.get(f"{USECASES}/churn").mock(return_value=httpx.Response(200, text=USECASE_YAML))
    result = runner.invoke(app, ["usecases", "yaml", "churn"])
    assert result.exit_code == 0, result.output
    assert route.calls.last.request.headers["accept"].startswith("application/yaml")
    assert "# Owned by data science" in result.output


@respx.mock
def test_usecases_put_yaml_keeps_comments(tmp_path):
    route = respx.put(f"{USECASES}/churn").mock(return_value=httpx.Response(200))
    doc = tmp_path / "churn.yaml"
    doc.write_text(USECASE_YAML)
    result = runner.invoke(app, ["usecases", "put", "churn", "--file", str(doc)])
    assert result.exit_code == 0, result.output
    request = route.calls.last.request
    assert request.headers["content-type"].startswith("application/yaml")
    assert request.content.decode() == USECASE_YAML


@respx.mock
def test_usecases_put_json(tmp_path):
    route = respx.put(f"{USECASES}/churn").mock(return_value=httpx.Response(200))
    doc = tmp_path / "churn.json"
    doc.write_text(json.dumps(USECASE))
    result = runner.invoke(app, ["usecases", "put", "churn", "--file", str(doc)])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content)["id"] == "churn"


def test_usecases_put_rejects_a_mismatched_id(tmp_path):
    doc = tmp_path / "churn.yaml"
    doc.write_text(USECASE_YAML)
    result = runner.invoke(app, ["usecases", "put", "upsell", "--file", str(doc)])
    assert result.exit_code != 0
    assert "does not match" in _text(result.output)


@respx.mock
def test_usecases_delete():
    route = respx.delete(f"{USECASES}/churn").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["usecases", "delete", "churn"])
    assert result.exit_code == 0, result.output
    assert route.called


# --- custom-quality-checks --------------------------------------------------------------

CHECK_YAML = "description: ${column} between ${arguments.min} and ${arguments.max}.\ndimension: conformity\n"


@respx.mock
def test_custom_quality_check_get_prints_the_file():
    respx.get(f"{BASE_URL}/api/custom-quality-checks/range/check.yaml").mock(
        return_value=httpx.Response(200, text=CHECK_YAML)
    )
    result = runner.invoke(app, ["custom-quality-checks", "get", "range"])
    assert result.exit_code == 0, result.output
    assert "dimension: conformity" in result.output


@respx.mock
def test_custom_quality_check_get_writes_a_file(tmp_path):
    respx.get(f"{BASE_URL}/api/custom-quality-checks/range/check.yaml").mock(
        return_value=httpx.Response(200, text=CHECK_YAML)
    )
    out = tmp_path / "checks" / "range.yaml"
    out.parent.mkdir()
    result = runner.invoke(app, ["custom-quality-checks", "get", "range", "--file", str(out)])
    assert result.exit_code == 0, result.output
    assert out.read_text() == CHECK_YAML
