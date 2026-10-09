"""Tests for lineage commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

LINEAGE_EVENTS = [
    {
        "eventType": "COMPLETE",
        "eventTime": "2024-01-01T00:00:00Z",
        "job": {"namespace": "my-namespace", "name": "my-job"},
        "run": {"runId": "run-1"},
    },
]


@responses.activate
def test_lineage_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/lineage", json=LINEAGE_EVENTS, status=200)
    result = runner.invoke(app, ["lineage", "list"])
    assert result.exit_code == 0
    assert "COMPLETE" in result.output


@responses.activate
def test_lineage_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/lineage", json=LINEAGE_EVENTS, status=200)
    result = runner.invoke(app, ["lineage", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


@responses.activate
def test_lineage_list_with_filters(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/lineage", json=LINEAGE_EVENTS, status=200)
    result = runner.invoke(
        app, ["lineage", "list", "--job-namespace", "my-namespace", "--job-name", "my-job", "--event-type", "COMPLETE"]
    )
    assert result.exit_code == 0


@responses.activate
def test_lineage_submit(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/v1/lineage", status=200)
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(LINEAGE_EVENTS[0]))
    result = runner.invoke(app, ["lineage", "submit", "--file", str(event_file)])
    assert result.exit_code == 0
    assert "submitted" in result.output


@responses.activate
def test_lineage_submit_with_data_product(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/v1/lineage", status=200)
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(LINEAGE_EVENTS[0]))
    result = runner.invoke(
        app,
        ["lineage", "submit", "--file", str(event_file), "--data-product-id", "dp-1", "--output-port-name", "port-1"],
    )
    assert result.exit_code == 0


@responses.activate
def test_lineage_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/v1/lineage", json={}, status=200)
    result = runner.invoke(app, ["lineage", "delete", "--run-id", "run-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_lineage_help():
    result = runner.invoke(app, ["lineage", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "submit" in result.output
    assert "delete" in result.output


def _event(run_id: str, event_time: str) -> dict:
    return {"eventType": "COMPLETE", "eventTime": event_time, "run": {"runId": run_id}, "job": {"name": "m"}}


@responses.activate
def test_lineage_list_sends_time_range_and_page(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/lineage", json=[], status=200)
    result = runner.invoke(
        app,
        ["lineage", "list", "--since", "2026-10-01", "--until", "2026-10-08T12:00:00+02:00", "-p", "2", "-l", "50"],
    )
    assert result.exit_code == 0
    assert responses.calls[0].request.params == {
        "from": "2026-10-01T00:00:00Z",
        "to": "2026-10-08T10:00:00Z",
        "p": "2",
        "size": "50",
    }


@responses.activate
def test_lineage_list_all_follows_the_next_links(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    url = f"{BASE_URL}/api/v1/lineage"
    responses.add(
        responses.GET,
        url,
        json=[_event("r1", "2026-10-03T00:00:00Z")],
        headers={"Link": '</api/v1/lineage?size=1&p=1>; rel="next"'},
        match=[responses.matchers.query_param_matcher({"p": "0", "size": "1"})],
    )
    responses.add(
        responses.GET,
        url,
        json=[_event("r2", "2026-10-02T00:00:00Z")],
        match=[responses.matchers.query_param_matcher({"p": "1", "size": "1"})],
    )
    result = runner.invoke(app, ["-o", "json", "lineage", "list", "--all", "--limit", "1"])
    assert result.exit_code == 0
    assert [e["run"]["runId"] for e in json.loads(result.stdout)] == ["r1", "r2"]
    assert result.stderr == ""


@responses.activate
def test_lineage_list_filters_and_pages_locally_when_the_server_ignores_it(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    # An older server: no paging, no time filter — every event, oldest first.
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/v1/lineage",
        json=[
            _event("too-old", "2026-09-01T00:00:00Z"),
            _event("r1", "2026-10-02T00:00:00Z"),
            _event("r2", "2026-10-03T00:00:00Z"),
            _event("r3", "2026-10-04T00:00:00Z"),
        ],
    )
    result = runner.invoke(app, ["-o", "json", "lineage", "list", "--since", "2026-10-01", "--limit", "2"])
    assert result.exit_code == 0
    assert [e["run"]["runId"] for e in json.loads(result.stdout)] == ["r1", "r2"]
    assert "does not support the time range or page size" in result.stderr
    assert "--page 1" in result.stderr


def test_lineage_list_rejects_an_invalid_time():
    result = runner.invoke(app, ["lineage", "list", "--since", "last-tuesday"])
    assert result.exit_code == 2
    assert "is not a time" in result.output
