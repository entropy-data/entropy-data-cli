"""Tests for insights dashboards and semantic-models commands."""

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
DASHBOARDS = f"{BASE_URL}/api/insights/dashboards"
MODELS = f"{BASE_URL}/api/insights/semantic-models"

DASHBOARD = {
    "apiVersion": "perses.dev/v1alpha1",
    "kind": "PersesDashboard",
    "metadata": {"name": "governance-board-kpis", "annotations": {"entropy-data.com/owner": "governance"}},
    "spec": {"display": {"name": "Governance board KPIs"}, "duration": "90d", "panels": {}, "layouts": []},
}
MODEL = {
    "version": "0.1.0",
    "name": "governance_kpis",
    "description": "KPIs for the governance board",
    "datasets": [],
    "metrics": [],
}


@pytest.fixture(autouse=True)
def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


def _text(output: str) -> str:
    return " ".join(output.split())


# --- dashboards ------------------------------------------------------------------------


@respx.mock
def test_dashboards_list_table():
    respx.get(DASHBOARDS).mock(return_value=httpx.Response(200, json=[DASHBOARD]))
    result = runner.invoke(app, ["insights", "dashboards", "list"])
    assert result.exit_code == 0, result.output
    out = _text(result.output)
    assert "governance-board-kpis" in out and "Governance board KPIs" in out and "90d" in out


@respx.mock
def test_dashboards_get_json():
    respx.get(f"{DASHBOARDS}/governance-board-kpis").mock(return_value=httpx.Response(200, json=DASHBOARD))
    result = runner.invoke(app, ["insights", "dashboards", "get", "governance-board-kpis", "-o", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["kind"] == "PersesDashboard"


@respx.mock
def test_dashboards_yaml_writes_a_file(tmp_path):
    text = yaml.safe_dump(DASHBOARD)
    respx.get(f"{DASHBOARDS}/governance-board-kpis/dashboard.yaml").mock(return_value=httpx.Response(200, text=text))
    out = tmp_path / "dashboard.yaml"
    result = runner.invoke(app, ["insights", "dashboards", "yaml", "governance-board-kpis", "--file", str(out)])
    assert result.exit_code == 0, result.output
    assert out.read_text() == text


@respx.mock
def test_dashboards_put_sends_json_and_fills_in_the_name(tmp_path):
    route = respx.put(f"{DASHBOARDS}/governance-board-kpis").mock(
        return_value=httpx.Response(200, headers={"location-html": "https://app/governance/insights-v2/x"})
    )
    body = {**DASHBOARD, "metadata": {"annotations": {"entropy-data.com/owner": "governance"}}}
    doc = tmp_path / "dashboard.yaml"
    doc.write_text(yaml.safe_dump(body))
    result = runner.invoke(app, ["insights", "dashboards", "put", "governance-board-kpis", "--file", str(doc)])
    assert result.exit_code == 0, result.output
    sent = json.loads(route.calls.last.request.content)
    assert sent["metadata"] == {
        "name": "governance-board-kpis",
        "annotations": {"entropy-data.com/owner": "governance"},
    }
    assert "insights-v2" in result.output


def test_dashboards_put_rejects_a_mismatched_name(tmp_path):
    doc = tmp_path / "dashboard.yaml"
    doc.write_text(yaml.safe_dump(DASHBOARD))
    result = runner.invoke(app, ["insights", "dashboards", "put", "other", "--file", str(doc)])
    assert result.exit_code != 0
    assert "does not match" in _text(result.output)


@respx.mock
def test_dashboards_delete():
    route = respx.delete(f"{DASHBOARDS}/governance-board-kpis").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["insights", "dashboards", "delete", "governance-board-kpis"])
    assert result.exit_code == 0, result.output
    assert route.called


# --- semantic models -------------------------------------------------------------------


@respx.mock
def test_semantic_models_list_table():
    respx.get(MODELS).mock(return_value=httpx.Response(200, json=[MODEL]))
    result = runner.invoke(app, ["insights", "semantic-models", "list"])
    assert result.exit_code == 0, result.output
    out = _text(result.output)
    assert "governance_kpis" in out and "0.1.0" in out


@respx.mock
def test_semantic_models_yaml():
    respx.get(f"{MODELS}/governance_kpis/model.yaml").mock(
        return_value=httpx.Response(200, text="version: 0.1.0\nname: governance_kpis\n")
    )
    result = runner.invoke(app, ["insights", "semantic-models", "yaml", "governance_kpis"])
    assert result.exit_code == 0, result.output
    assert "name: governance_kpis" in result.output


@respx.mock
def test_semantic_models_put_without_removed_metrics(tmp_path):
    route = respx.put(f"{MODELS}/governance_kpis").mock(return_value=httpx.Response(200))
    doc = tmp_path / "model.yaml"
    doc.write_text(yaml.safe_dump(MODEL))
    result = runner.invoke(app, ["insights", "semantic-models", "put", "governance_kpis", "--file", str(doc)])
    assert result.exit_code == 0, result.output
    request = route.calls.last.request
    assert "removedMetrics" not in request.url.params
    assert json.loads(request.content)["name"] == "governance_kpis"


@respx.mock
def test_semantic_models_put_with_removed_metrics(tmp_path):
    route = respx.put(f"{MODELS}/governance_kpis").mock(return_value=httpx.Response(200))
    doc = tmp_path / "model.yaml"
    doc.write_text(yaml.safe_dump({k: v for k, v in MODEL.items() if k != "name"}))
    result = runner.invoke(
        app,
        ["insights", "semantic-models", "put", "governance_kpis", "--file", str(doc), "--removed-metrics", "remove"],
    )
    assert result.exit_code == 0, result.output
    request = route.calls.last.request
    assert request.url.params["removedMetrics"] == "remove"
    assert json.loads(request.content)["name"] == "governance_kpis"


@respx.mock
def test_semantic_models_put_surfaces_the_conflict_over_removed_metrics(tmp_path):
    respx.put(f"{MODELS}/governance_kpis").mock(
        return_value=httpx.Response(409, json={"detail": "The update removes metrics that dashboards show."})
    )
    doc = tmp_path / "model.yaml"
    doc.write_text(yaml.safe_dump(MODEL))
    result = runner.invoke(app, ["insights", "semantic-models", "put", "governance_kpis", "--file", str(doc)])
    assert result.exit_code != 0
    assert "removes metrics" in _text(result.output)


def test_semantic_models_put_rejects_an_unknown_removed_metrics_value(tmp_path):
    doc = tmp_path / "model.yaml"
    doc.write_text(yaml.safe_dump(MODEL))
    result = runner.invoke(
        app,
        ["insights", "semantic-models", "put", "governance_kpis", "--file", str(doc), "--removed-metrics", "drop"],
    )
    assert result.exit_code != 0


@respx.mock
def test_semantic_models_delete():
    route = respx.delete(f"{MODELS}/governance_kpis").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["insights", "semantic-models", "delete", "governance_kpis"])
    assert result.exit_code == 0, result.output
    assert route.called
