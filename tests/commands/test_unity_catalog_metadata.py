"""Tests for the Unity Catalog metadata integration commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
PATH = f"{BASE_URL}/api/integrations/unity-catalog-metadata"

LAKEHOUSE = {"externalId": "lakehouse", "name": "Lakehouse", "enabled": True}
LAKEHOUSE_DETAIL = {
    **LAKEHOUSE,
    "credential": {
        "databricksHost": "adb-1.azuredatabricks.net",
        "databricksClientId": "app-id",
        "databricksWarehouseId": "wh-1",
    },
    "status": {"inSync": 3, "unresolved": 0, "failed": 1, "waitingEvents": 2, "taskRunning": False},
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_list_and_get(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, PATH, json=[LAKEHOUSE], status=200)
    responses.add(responses.GET, f"{PATH}/lakehouse", json=LAKEHOUSE_DETAIL, status=200)

    result = runner.invoke(app, ["integrations", "unity-catalog-metadata", "list", "--disabled", "-o", "json"])
    assert result.exit_code == 0, result.output
    assert "enabled=false" in responses.calls[0].request.url
    assert json.loads(result.output)[0]["externalId"] == "lakehouse"

    result = runner.invoke(app, ["integrations", "unity-catalog-metadata", "get", "lakehouse", "-o", "json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["status"]["waitingEvents"] == 2
    assert "databricksClientSecret" not in data["credential"]


@responses.activate
def test_put_from_options_and_from_file(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, f"{PATH}/lakehouse", json=LAKEHOUSE_DETAIL, status=201)
    result = runner.invoke(
        app,
        [
            "integrations",
            "unity-catalog-metadata",
            "put",
            "lakehouse",
            "--name",
            "Lakehouse",
            "--host",
            "adb-1.azuredatabricks.net",
            "--client-id",
            "app-id",
            "--client-secret",
            "s3cret",
            "--warehouse-id",
            "wh-1",
        ],
    )
    assert result.exit_code == 0, result.output
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "name": "Lakehouse",
        "credential": {
            "databricksHost": "adb-1.azuredatabricks.net",
            "databricksClientId": "app-id",
            "databricksClientSecret": "s3cret",
            "databricksWarehouseId": "wh-1",
        },
    }

    # A file carries the body; options override its values, and a rename alone sends no credential
    file = tmp_path / "lakehouse.yaml"
    file.write_text("name: Lakehouse\nenabled: false\n")
    result = runner.invoke(
        app,
        [
            "integrations",
            "unity-catalog-metadata",
            "put",
            "lakehouse",
            "--file",
            str(file),
            "--name",
            "Lakehouse (prod)",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(responses.calls[1].request.body) == {"name": "Lakehouse (prod)", "enabled": False}

    result = runner.invoke(app, ["integrations", "unity-catalog-metadata", "put", "lakehouse", "--host", "x"])
    assert result.exit_code != 0
    assert "name" in result.output


@responses.activate
def test_tables_queue_retry_discard_and_delete(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{PATH}/lakehouse/tables",
        json=[
            {
                "dataContractExternalId": "orders",
                "dataContractElement": "lake",
                "tableFullName": "sales.public.orders",
                "state": "failed",
                "lastError": "boom",
            }
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{PATH}/lakehouse/queue",
        json=[
            {
                "eventType": "DataContractUpdatedEvent",
                "externalId": "orders",
                "since": "2026-10-06T08:00:00Z",
                "attempts": 1,
            }
        ],
        status=200,
    )
    responses.add(
        responses.POST,
        f"{PATH}/lakehouse/tables/retry-failed",
        json={
            "integrationExternalId": "lakehouse",
            "count": 1,
            "message": "1 data contracts with failed or unresolved tables are written again",
        },
        status=200,
    )
    responses.add(
        responses.POST,
        f"{PATH}/lakehouse/queue/discard",
        json={"integrationExternalId": "lakehouse", "count": 2, "message": "2 waiting events discarded"},
        status=200,
    )
    responses.add(responses.DELETE, f"{PATH}/lakehouse", status=204)

    result = runner.invoke(
        app, ["integrations", "unity-catalog-metadata", "tables", "lakehouse", "--state", "failed", "-o", "json"]
    )
    assert result.exit_code == 0, result.output
    assert "state=failed" in responses.calls[0].request.url
    assert json.loads(result.output)[0]["tableFullName"] == "sales.public.orders"

    result = runner.invoke(app, ["integrations", "unity-catalog-metadata", "queue", "lakehouse", "-o", "json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]["eventType"] == "DataContractUpdatedEvent"

    result = runner.invoke(app, ["integrations", "unity-catalog-metadata", "retry-failed", "lakehouse"])
    assert result.exit_code == 0, result.output
    assert "written again" in result.output

    result = runner.invoke(app, ["integrations", "unity-catalog-metadata", "discard-queue", "lakehouse"])
    assert result.exit_code == 0, result.output
    assert "2 waiting events discarded" in result.output

    result = runner.invoke(app, ["integrations", "unity-catalog-metadata", "delete", "lakehouse"])
    assert result.exit_code == 0, result.output
    assert responses.calls[-1].request.method == "DELETE"
