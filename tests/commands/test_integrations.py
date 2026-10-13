"""Tests for integrations commands."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

A_UUID = "11111111-1111-1111-1111-111111111111"
EXTERNAL_ID = "demo-snowflake"

DEMO_RUN = {
    "ingestionRunId": "aaaa1111-1111-1111-1111-111111111111",
    "integrationExternalId": EXTERNAL_ID,
    "status": "SUCCESS",
    "message": None,
    "assetsProcessed": 1256,
    "assetsCreated": 5,
    "assetsUpdated": 1251,
    "assetsDeleted": 0,
    "startedAt": "2026-05-19T07:13:00Z",
    "completedAt": "2026-05-19T07:43:00Z",
}

# List/summary view: addressed by externalId; no internal UUID, no embedded configuration or run.
DEMO_INTEGRATION = {
    "externalId": EXTERNAL_ID,
    "name": "Demo Snowflake",
    "source": "snowflake",
    "enabled": True,
    "assetOwnerTeamExternalId": "platform-team",
}

# Single-resource view: configuration inlined.
DEMO_INTEGRATION_DETAIL = {
    **DEMO_INTEGRATION,
    "configuration": {
        "externalId": EXTERNAL_ID,
        "source": "snowflake",
        "name": "Demo Snowflake",
        "scheduleExpression": "0 0 6 * * ?",
        "filters": {"databases": ["DP_*"]},
    },
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


def _mock_list(integrations=None):
    """Register the list call the resolver uses to map an identifier to its externalId."""
    respx.get(f"{BASE_URL}/api/integrations/ingest").mock(
        return_value=httpx.Response(200, json=integrations if integrations is not None else [DEMO_INTEGRATION])
    )


@respx.mock
def test_integrations_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(f"{BASE_URL}/api/integrations/ingest").mock(return_value=httpx.Response(200, json=[DEMO_INTEGRATION]))
    result = runner.invoke(app, ["integrations", "list", "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["externalId"] == EXTERNAL_ID
    assert data[0]["source"] == "snowflake"


@respx.mock
def test_integrations_list_filters_source(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(f"{BASE_URL}/api/integrations/ingest").mock(return_value=httpx.Response(200, json=[DEMO_INTEGRATION]))
    result = runner.invoke(app, ["integrations", "list", "--source", "snowflake"])
    assert result.exit_code == 0
    assert "source=snowflake" in str(respx.calls[0].request.url)


@respx.mock
def test_integrations_list_filters_enabled(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.get(f"{BASE_URL}/api/integrations/ingest").mock(return_value=httpx.Response(200, json=[DEMO_INTEGRATION]))
    result = runner.invoke(app, ["integrations", "list", "--enabled"])
    assert result.exit_code == 0
    assert "enabled=true" in str(respx.calls[0].request.url)


@respx.mock
def test_integrations_get_resolves_and_inlines_configuration(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    respx.get(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}").mock(
        return_value=httpx.Response(200, json=DEMO_INTEGRATION_DETAIL)
    )
    result = runner.invoke(app, ["integrations", "get", EXTERNAL_ID, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["externalId"] == EXTERNAL_ID
    assert data["configuration"]["source"] == "snowflake"
    # Resolve (list) then GET the single resource by externalId.
    assert len(respx.calls) == 2


@respx.mock
def test_integrations_get_by_uuid_is_not_accepted(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    # The API is externalId-native; an internal UUID is no longer a valid identifier.
    result = runner.invoke(app, ["integrations", "get", A_UUID])
    assert result.exit_code != 0
    assert "No integration found" in result.output


@respx.mock
def test_integrations_get_name_not_found(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    result = runner.invoke(app, ["integrations", "get", "no-such-integration"])
    assert result.exit_code != 0
    assert "No integration found" in result.output


@respx.mock
def test_integrations_get_name_ambiguous(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    duplicate = {**DEMO_INTEGRATION, "externalId": "demo-snowflake-2"}
    _mock_list([DEMO_INTEGRATION, duplicate])
    # Both share the display name, so resolving by name is ambiguous.
    result = runner.invoke(app, ["integrations", "get", "Demo Snowflake"])
    assert result.exit_code != 0
    assert "multiple integrations" in result.output
    assert EXTERNAL_ID in result.output
    assert "demo-snowflake-2" in result.output


@respx.mock
def test_integrations_runs_lists_history(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    runs = [
        DEMO_RUN,
        {
            **DEMO_RUN,
            "ingestionRunId": "bbbb1111-1111-1111-1111-111111111111",
            "status": "FAILED",
            "completedAt": "2026-05-18T06:16:00Z",
        },
    ]
    respx.get(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}/runs").mock(
        return_value=httpx.Response(200, json=runs)
    )
    result = runner.invoke(app, ["integrations", "runs", EXTERNAL_ID, "--limit", "10", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [r["status"] for r in data] == ["SUCCESS", "FAILED"]
    # calls[0] is the resolve list; calls[1] is the runs request.
    assert "limit=10" in str(respx.calls[1].request.url)


@respx.mock
def test_integrations_runs_get_by_id(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    run_id = DEMO_RUN["ingestionRunId"]
    respx.get(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}/runs/{run_id}").mock(
        return_value=httpx.Response(200, json=DEMO_RUN)
    )
    result = runner.invoke(app, ["integrations", "runs-get", EXTERNAL_ID, run_id, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ingestionRunId"] == run_id
    assert data["integrationExternalId"] == EXTERNAL_ID
    assert data["status"] == "SUCCESS"


@respx.mock
def test_integrations_runs_latest(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    respx.get(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}/runs/latest").mock(
        return_value=httpx.Response(200, json=DEMO_RUN)
    )
    result = runner.invoke(app, ["integrations", "runs-latest", EXTERNAL_ID, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ingestionRunId"] == DEMO_RUN["ingestionRunId"]
    assert data["status"] == "SUCCESS"


@respx.mock
def test_integrations_run_triggers_and_returns_scheduled(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    respx.post(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}/run").mock(
        return_value=httpx.Response(
            202,
            json={
                "integrationExternalId": EXTERNAL_ID,
                "scheduledAt": "2026-05-20T07:43:00Z",
                "deferred": False,
                "message": "Run scheduled; poll /runs/latest for status.",
            },
        )
    )
    result = runner.invoke(app, ["integrations", "run", EXTERNAL_ID])
    assert result.exit_code == 0, result.output
    assert "Run scheduled" in result.output


@respx.mock
def test_integrations_run_conflict_surfaces_clear_message(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    respx.post(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}/run").mock(
        return_value=httpx.Response(
            409, json={"status": "already_running", "message": "An ingestion run is already in progress."}
        )
    )
    result = runner.invoke(app, ["integrations", "run", EXTERNAL_ID])
    assert result.exit_code == 1
    assert "Conflict" in result.output
    assert "already in progress" in result.output


@respx.mock
def test_integrations_cancel_returns_success(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    respx.post(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}/cancel").mock(return_value=httpx.Response(204))
    result = runner.invoke(app, ["integrations", "cancel", EXTERNAL_ID])
    assert result.exit_code == 0, result.output
    assert "Cancellation requested" in result.output


def test_integrations_help_lists_subcommands():
    result = runner.invoke(app, ["integrations", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "get", "configuration", "runs", "runs-get", "runs-latest", "run", "cancel"):
        assert cmd in result.output


def test_top_level_help_includes_integrations():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "integrations" in result.output


@respx.mock
def test_integrations_put_sends_configuration_credential_and_enabled(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.put(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}").mock(
        return_value=httpx.Response(201, json=DEMO_INTEGRATION_DETAIL)
    )
    # A 'get' output with a credential added is a valid file: the extra top-level keys are ignored
    document = {
        **DEMO_INTEGRATION_DETAIL,
        "credential": {"type": "pat", "details": {"account": "acme", "user": "svc", "pat": "s3cret"}},
    }
    file = tmp_path / "integration.json"
    file.write_text(json.dumps(document))
    result = runner.invoke(app, ["integrations", "put", EXTERNAL_ID, "--file", str(file), "--disabled"])
    assert result.exit_code == 0, result.output
    body = json.loads(respx.calls[0].request.content)
    assert body["configuration"]["scheduleExpression"] == "0 0 6 * * ?"
    assert body["credential"]["details"]["pat"] == "s3cret"
    assert body["enabled"] is False
    assert "externalId" not in body


@respx.mock
def test_integrations_put_needs_a_configuration(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    file = tmp_path / "integration.json"
    file.write_text(json.dumps({"name": "No configuration here"}))
    result = runner.invoke(app, ["integrations", "put", EXTERNAL_ID, "--file", str(file)])
    assert result.exit_code != 0
    assert "configuration" in result.output
    assert len(respx.calls) == 0


@respx.mock
def test_integrations_delete_with_and_without_assets(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    respx.delete(f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}").mock(return_value=httpx.Response(204))
    result = runner.invoke(app, ["integrations", "delete", "Demo Snowflake"])
    assert result.exit_code == 0, result.output
    assert str(respx.calls[-1].request.url) == f"{BASE_URL}/api/integrations/ingest/{EXTERNAL_ID}"

    result = runner.invoke(app, ["integrations", "delete", EXTERNAL_ID, "--delete-assets"])
    assert result.exit_code == 0, result.output
    assert "deleteAssets=true" in str(respx.calls[-1].request.url)
