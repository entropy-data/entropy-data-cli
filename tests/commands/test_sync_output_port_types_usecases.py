"""export / apply dir for output-port-types (singleton) and usecases (behind useCasesEnabled)."""

import json

import httpx
import respx
import yaml
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app
from entropy_data.resources import RESOURCE_BY_NAME, RESOURCE_ORDER

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
OUTPUT_PORT_TYPES = f"{BASE_URL}/api/settings/output-port-types"
USECASES = f"{BASE_URL}/api/usecases"
FEATURES = f"{BASE_URL}/api/organization/features"

PORT_TYPES = {
    "legacy": False,
    "onlyListedTypes": True,
    "outputPortTypes": [{"id": "snowflake", "label": "Snowflake", "enabled": True}],
    "supportedOutputPortTypes": [{"dataProductType": "source-aligned", "outputPortTypes": ["snowflake"]}],
}
USECASE = {
    "apiVersion": "v0.1.0",
    "kind": "UseCase",
    "id": "churn",
    "name": "Churn prediction",
    "team": {"name": "data-science"},
    "dataProducts": [{"id": "customers"}],
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


def _write(root, name, filename, body):
    (root / name).mkdir(parents=True, exist_ok=True)
    (root / name / filename).write_text(yaml.safe_dump(body))


def test_order_output_port_types_after_dataproduct_types_and_usecases_before_access():
    names = [r.name for r in RESOURCE_ORDER]
    assert names.index("dataproduct-types") < names.index("output-port-types") < names.index("dataproducts")
    assert names.index("dataproducts") < names.index("usecases") < names.index("access")
    assert RESOURCE_BY_NAME["output-port-types"].singleton
    assert RESOURCE_BY_NAME["usecases"].feature == "useCasesEnabled"


# --- output-port-types ------------------------------------------------------------


@respx.mock
def test_export_output_port_types(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(OUTPUT_PORT_TYPES).mock(return_value=httpx.Response(200, json=PORT_TYPES))
    dest = tmp_path / "export"
    result = runner.invoke(app, ["export", "dir", str(dest), "--include", "output-port-types"])
    assert result.exit_code == 0, result.output
    body = yaml.safe_load((dest / "output-port-types" / "output-port-types.yaml").read_text())
    assert body["outputPortTypes"][0]["id"] == "snowflake"


@respx.mock
def test_export_output_port_types_skips_legacy(monkeypatch, tmp_path):
    """A source that never changed its output port types has nothing of its own to copy."""
    _setup(monkeypatch, tmp_path)
    respx.get(OUTPUT_PORT_TYPES).mock(return_value=httpx.Response(200, json={**PORT_TYPES, "legacy": True}))
    dest = tmp_path / "export"
    result = runner.invoke(app, ["export", "dir", str(dest), "--include", "output-port-types"])
    assert result.exit_code == 0, result.output
    assert not (dest / "output-port-types").exists()
    assert "not configured on the source" in result.output


@respx.mock
def test_apply_output_port_types(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _write(tmp_path / "tree", "output-port-types", "output-port-types.yaml", PORT_TYPES)
    route = respx.put(OUTPUT_PORT_TYPES).mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["apply", "dir", str(tmp_path / "tree"), "--include", "output-port-types"])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content)["onlyListedTypes"] is True


# --- usecases -----------------------------------------------------------------------


@respx.mock
def test_export_usecases(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(USECASES).mock(return_value=httpx.Response(200, json=[USECASE]))
    dest = tmp_path / "export"
    result = runner.invoke(app, ["export", "dir", str(dest), "--include", "usecases"])
    assert result.exit_code == 0, result.output
    assert yaml.safe_load((dest / "usecases" / "churn.yaml").read_text())["name"] == "Churn prediction"


@respx.mock
def test_export_usecases_skips_when_off_on_the_source(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(USECASES).mock(
        return_value=httpx.Response(404, json={"detail": "Use Cases are not enabled for this organization."})
    )
    dest = tmp_path / "export"
    result = runner.invoke(app, ["export", "dir", str(dest), "--include", "usecases"])
    assert result.exit_code == 0, result.output
    assert "useCasesEnabled is off on the source" in result.output
    assert not (dest / "usecases").exists()


@respx.mock
def test_apply_usecases_when_on_on_the_target(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _write(tmp_path / "tree", "usecases", "churn.yaml", USECASE)
    respx.get(FEATURES).mock(return_value=httpx.Response(200, json={"useCasesEnabled": True}))
    route = respx.put(f"{USECASES}/churn").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["apply", "dir", str(tmp_path / "tree"), "--include", "usecases"])
    assert result.exit_code == 0, result.output
    assert json.loads(route.calls.last.request.content)["dataProducts"] == [{"id": "customers"}]


@respx.mock
def test_apply_usecases_switches_the_feature_on_when_the_artifact_does(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    tree = tmp_path / "tree"
    _write(tree, "usecases", "churn.yaml", USECASE)
    _write(tree, "organization-features", "organization-features.yaml", {"useCasesEnabled": True, "mcpEnabled": True})
    respx.get(FEATURES).mock(return_value=httpx.Response(200, json={"useCasesEnabled": None, "mcpEnabled": False}))
    features_put = respx.put(FEATURES).mock(return_value=httpx.Response(200, json={}))
    usecase_put = respx.put(f"{USECASES}/churn").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["apply", "dir", str(tree), "--include", "usecases,organization-features"])
    assert result.exit_code == 0, result.output
    assert usecase_put.called
    # First the one switch on top of the target's current features, then the full document last.
    early, final = (json.loads(c.request.content) for c in features_put.calls)
    assert early == {"useCasesEnabled": True, "mcpEnabled": False}
    assert final == {"useCasesEnabled": True, "mcpEnabled": True}


@respx.mock
def test_apply_usecases_fails_clearly_when_off_on_the_target(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _write(tmp_path / "tree", "usecases", "churn.yaml", USECASE)
    respx.get(FEATURES).mock(return_value=httpx.Response(200, json={}))
    usecase_put = respx.put(f"{USECASES}/churn").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["apply", "dir", str(tmp_path / "tree"), "--include", "usecases"])
    assert result.exit_code != 0
    assert not usecase_put.called
    assert "useCasesEnabled is off on the target" in " ".join(result.output.split())


@respx.mock
def test_apply_usecases_dry_run_against_a_target_with_the_feature_off(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _write(tmp_path / "tree", "usecases", "churn.yaml", USECASE)
    respx.get(USECASES).mock(return_value=httpx.Response(404, json={"detail": "not enabled"}))
    result = runner.invoke(app, ["apply", "dir", str(tmp_path / "tree"), "--include", "usecases", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "FAIL" not in result.output


@respx.mock
def test_prune_usecases_with_the_feature_off_deletes_nothing(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    (tmp_path / "tree" / "usecases").mkdir(parents=True)
    respx.get(USECASES).mock(return_value=httpx.Response(404, json={"detail": "not enabled"}))
    result = runner.invoke(app, ["apply", "dir", str(tmp_path / "tree"), "--include", "usecases", "--prune", "--yes"])
    assert result.exit_code == 0, result.output
    assert "FAIL" not in result.output
