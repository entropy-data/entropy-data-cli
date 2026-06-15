"""Tests for integrations commands."""

import json

import responses
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
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations",
        json=integrations if integrations is not None else [DEMO_INTEGRATION],
        status=200,
    )


@responses.activate
def test_integrations_list(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, f"{BASE_URL}/api/integrations", json=[DEMO_INTEGRATION], status=200)
    result = runner.invoke(app, ["integrations", "list", "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["externalId"] == EXTERNAL_ID
    assert data[0]["source"] == "snowflake"


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
def test_integrations_get_resolves_and_inlines_configuration(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    responses.add(responses.GET, f"{BASE_URL}/api/integrations/{EXTERNAL_ID}", json=DEMO_INTEGRATION_DETAIL, status=200)
    result = runner.invoke(app, ["integrations", "get", EXTERNAL_ID, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["externalId"] == EXTERNAL_ID
    assert data["configuration"]["source"] == "snowflake"
    # Resolve (list) then GET the single resource by externalId.
    assert len(responses.calls) == 2


@responses.activate
def test_integrations_get_by_uuid_is_not_accepted(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    # The API is externalId-native; an internal UUID is no longer a valid identifier.
    result = runner.invoke(app, ["integrations", "get", A_UUID])
    assert result.exit_code != 0
    assert "No integration found" in result.output


@responses.activate
def test_integrations_get_name_not_found(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    result = runner.invoke(app, ["integrations", "get", "no-such-integration"])
    assert result.exit_code != 0
    assert "No integration found" in result.output


@responses.activate
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


@responses.activate
def test_integrations_configuration_returns_yaml(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    yaml_body = (
        "externalId: demo-snowflake\n"
        "source: snowflake\n"
        "name: Demo Snowflake\n"
        "scheduleExpression: '0 0 6 * * ?'\n"
        "filters:\n  databases:\n  - DP_*\n"
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{EXTERNAL_ID}/configuration",
        body=yaml_body,
        status=200,
        content_type="application/yaml",
    )
    result = runner.invoke(app, ["integrations", "configuration", EXTERNAL_ID])
    assert result.exit_code == 0, result.output
    assert "externalId: demo-snowflake" in result.output
    assert "source: snowflake" in result.output


@responses.activate
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
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{EXTERNAL_ID}/runs",
        json=runs,
        status=200,
    )
    result = runner.invoke(app, ["integrations", "runs", EXTERNAL_ID, "--limit", "10", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert [r["status"] for r in data] == ["SUCCESS", "FAILED"]
    # calls[0] is the resolve list; calls[1] is the runs request.
    assert "limit=10" in responses.calls[1].request.url


@responses.activate
def test_integrations_runs_get_by_id(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    run_id = DEMO_RUN["ingestionRunId"]
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{EXTERNAL_ID}/runs/{run_id}",
        json=DEMO_RUN,
        status=200,
    )
    result = runner.invoke(app, ["integrations", "runs-get", EXTERNAL_ID, run_id, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ingestionRunId"] == run_id
    assert data["integrationExternalId"] == EXTERNAL_ID
    assert data["status"] == "SUCCESS"


@responses.activate
def test_integrations_runs_latest(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/integrations/{EXTERNAL_ID}/runs/latest",
        json=DEMO_RUN,
        status=200,
    )
    result = runner.invoke(app, ["integrations", "runs-latest", EXTERNAL_ID, "--output", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ingestionRunId"] == DEMO_RUN["ingestionRunId"]
    assert data["status"] == "SUCCESS"


@responses.activate
def test_integrations_run_triggers_and_returns_scheduled(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/integrations/{EXTERNAL_ID}/run",
        json={
            "integrationExternalId": EXTERNAL_ID,
            "scheduledAt": "2026-05-20T07:43:00Z",
            "deferred": False,
            "message": "Run scheduled; poll /runs/latest for status.",
        },
        status=202,
    )
    result = runner.invoke(app, ["integrations", "run", EXTERNAL_ID])
    assert result.exit_code == 0, result.output
    assert "Run scheduled" in result.output


@responses.activate
def test_integrations_run_conflict_surfaces_clear_message(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/integrations/{EXTERNAL_ID}/run",
        json={"status": "already_running", "message": "An ingestion run is already in progress."},
        status=409,
    )
    result = runner.invoke(app, ["integrations", "run", EXTERNAL_ID])
    assert result.exit_code == 1
    assert "Conflict" in result.output
    assert "already in progress" in result.output


@responses.activate
def test_integrations_cancel_returns_success(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    _mock_list()
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/integrations/{EXTERNAL_ID}/cancel",
        status=204,
    )
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
