"""Tests for integrations commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

INGESTION_ID = "11111111-1111-1111-1111-111111111111"
SECOND_INGESTION_ID = "22222222-2222-2222-2222-222222222222"

DEMO_INTEGRATION = {
    "ingestionId": INGESTION_ID,
    "externalId": "demo-snowflake",
    "name": "Demo Snowflake",
    "source": "snowflake",
    "enabled": True,
    "assetOwnerTeamExternalId": "platform-team",
    "createdAt": "2026-05-01T00:00:00Z",
    "updatedAt": "2026-05-19T00:00:00Z",
    "latestRun": {
        "ingestionRunId": "aaaa1111-1111-1111-1111-111111111111",
        "ingestionId": INGESTION_ID,
        "status": "SUCCESS",
        "message": None,
        "assetsProcessed": 1256,
        "assetsCreated": 5,
        "assetsUpdated": 1251,
        "assetsDeleted": 0,
        "startedAt": "2026-05-19T07:13:00Z",
        "completedAt": "2026-05-19T07:43:00Z",
    },
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_integrations_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, f"{BASE_URL}/api/integrations", json=[DEMO_INTEGRATION], status=200)
    result = runner.invoke(app, ["integrations", "list", "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["externalId"] == "demo-snowflake"
    assert data[0]["source"] == "snowflake"
    assert data[0]["latestRun"]["status"] == "SUCCESS"


@responses.activate
def test_integrations_list_filters_source(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations",
        json=[DEMO_INTEGRATION],
        status=200,
    )
    result = runner.invoke(app, ["integrations", "list", "--source", "snowflake"])
    assert result.exit_code == 0
    assert "source=snowflake" in responses.calls[0].request.url


@responses.activate
def test_integrations_list_filters_enabled(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations",
        json=[DEMO_INTEGRATION],
        status=200,
    )
    result = runner.invoke(app, ["integrations", "list", "--enabled"])
    assert result.exit_code == 0
    assert "enabled=true" in responses.calls[0].request.url


@responses.activate
def test_integrations_get_by_uuid(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, f"{BASE_URL}/api/integrations/{INGESTION_ID}", json=DEMO_INTEGRATION, status=200)
    result = runner.invoke(app, ["integrations", "get", INGESTION_ID, "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["externalId"] == "demo-snowflake"


@responses.activate
def test_integrations_get_by_external_id_resolves_via_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    # First call: list (for name resolution)
    responses.add(responses.GET, f"{BASE_URL}/api/integrations", json=[DEMO_INTEGRATION], status=200)
    # Second call: get by uuid
    responses.add(responses.GET, f"{BASE_URL}/api/integrations/{INGESTION_ID}", json=DEMO_INTEGRATION, status=200)
    result = runner.invoke(app, ["integrations", "get", "demo-snowflake", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["ingestionId"] == INGESTION_ID
    # Two requests: list (resolve), then get
    assert len(responses.calls) == 2


@responses.activate
def test_integrations_get_name_not_found(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, f"{BASE_URL}/api/integrations", json=[DEMO_INTEGRATION], status=200)
    result = runner.invoke(app, ["integrations", "get", "no-such-integration"])
    assert result.exit_code != 0
    assert "No integration found" in result.output


@responses.activate
def test_integrations_get_name_ambiguous(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    duplicate = {**DEMO_INTEGRATION, "ingestionId": SECOND_INGESTION_ID, "externalId": "demo-snowflake"}
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations",
        json=[DEMO_INTEGRATION, duplicate],
        status=200,
    )
    result = runner.invoke(app, ["integrations", "get", "demo-snowflake"])
    assert result.exit_code != 0
    assert "multiple integrations" in result.output
    assert INGESTION_ID in result.output
    assert SECOND_INGESTION_ID in result.output


@responses.activate
def test_integrations_configuration_returns_yaml(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    yaml_body = (
        "externalId: demo-snowflake\n"
        "source: snowflake\n"
        "name: Demo Snowflake\n"
        "scheduleExpression: '0 0 6 * * ?'\n"
        "filters:\n  databases:\n  - DP_*\n"
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{INGESTION_ID}/configuration",
        body=yaml_body,
        status=200,
        content_type="application/x-yaml",
    )
    result = runner.invoke(app, ["integrations", "configuration", INGESTION_ID])
    assert result.exit_code == 0, result.output
    assert "externalId: demo-snowflake" in result.output
    assert "source: snowflake" in result.output


@responses.activate
def test_integrations_runs_lists_history(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    runs = [
        DEMO_INTEGRATION["latestRun"],
        {
            **DEMO_INTEGRATION["latestRun"],
            "ingestionRunId": "bbbb1111-1111-1111-1111-111111111111",
            "status": "FAILED",
            "completedAt": "2026-05-18T06:16:00Z",
        },
    ]
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{INGESTION_ID}/runs",
        json=runs,
        status=200,
    )
    result = runner.invoke(app, ["integrations", "runs", INGESTION_ID, "--limit", "10", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [r["status"] for r in data] == ["SUCCESS", "FAILED"]
    assert "limit=10" in responses.calls[0].request.url


@responses.activate
def test_integrations_runs_get_by_uuid(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    run = DEMO_INTEGRATION["latestRun"]
    run_id = run["ingestionRunId"]
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{INGESTION_ID}/runs/{run_id}",
        json=run,
        status=200,
    )
    result = runner.invoke(app, ["integrations", "runs-get", INGESTION_ID, run_id, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ingestionRunId"] == run_id
    assert data["status"] == "SUCCESS"


@responses.activate
def test_integrations_runs_get_resolves_name_via_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    run = DEMO_INTEGRATION["latestRun"]
    run_id = run["ingestionRunId"]
    # First call: list (for name resolution), then get the single run by uuid
    responses.add(responses.GET, f"{BASE_URL}/api/integrations", json=[DEMO_INTEGRATION], status=200)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{INGESTION_ID}/runs/{run_id}",
        json=run,
        status=200,
    )
    result = runner.invoke(app, ["integrations", "runs-get", "demo-snowflake", run_id, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ingestionRunId"] == run_id
    assert len(responses.calls) == 2


@responses.activate
def test_integrations_run_triggers_and_returns_scheduled(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/integrations/{INGESTION_ID}/run",
        json={
            "ingestionId": INGESTION_ID,
            "scheduledAt": "2026-05-20T07:43:00Z",
            "deferred": False,
            "message": "Run scheduled; poll /runs for status.",
        },
        status=202,
    )
    result = runner.invoke(app, ["integrations", "run", INGESTION_ID])
    assert result.exit_code == 0, result.output
    assert "Run scheduled" in result.output


@responses.activate
def test_integrations_run_conflict_surfaces_clear_message(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/integrations/{INGESTION_ID}/run",
        json={"status": "already_running", "message": "An ingestion run is already in progress."},
        status=409,
    )
    result = runner.invoke(app, ["integrations", "run", INGESTION_ID])
    assert result.exit_code == 1
    assert "Conflict" in result.output
    assert "already in progress" in result.output


@responses.activate
def test_integrations_cancel_returns_success(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/integrations/{INGESTION_ID}/cancel",
        status=204,
    )
    result = runner.invoke(app, ["integrations", "cancel", INGESTION_ID])
    assert result.exit_code == 0, result.output
    assert "Cancellation requested" in result.output


def test_integrations_help_lists_subcommands():
    result = runner.invoke(app, ["integrations", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "get", "configuration", "runs", "runs-get", "run", "cancel"):
        assert cmd in result.output


def test_top_level_help_includes_integrations():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "integrations" in result.output
