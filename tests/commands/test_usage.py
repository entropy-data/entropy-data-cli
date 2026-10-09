"""Tests for usage commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

# GET /api/v1/traces answers with one OTLP/JSON document, not a list.
TRACES_DATA = {"resourceSpans": []}


@responses.activate
def test_usage_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/traces", json=TRACES_DATA, status=200)
    result = runner.invoke(app, ["usage", "list"])
    assert result.exit_code == 0


@responses.activate
def test_usage_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/traces", json=TRACES_DATA, status=200)
    result = runner.invoke(app, ["usage", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"resourceSpans": []}


@responses.activate
def test_usage_list_with_filters(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/traces", json=TRACES_DATA, status=200)
    result = runner.invoke(app, ["usage", "list", "--scope-name", "usage", "--data-product-id", "dp-1"])
    assert result.exit_code == 0


@responses.activate
def test_usage_submit(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/v1/traces", status=200)
    traces_file = tmp_path / "traces.json"
    traces_file.write_text(json.dumps({"resourceSpans": []}))
    result = runner.invoke(app, ["usage", "submit", "--file", str(traces_file)])
    assert result.exit_code == 0
    assert "submitted" in result.output


@responses.activate
def test_usage_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/v1/traces", json={"deletedCount": 5}, status=200)
    result = runner.invoke(app, ["usage", "delete", "--data-product-id", "dp-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output
    assert "5" in result.output


def test_usage_help():
    result = runner.invoke(app, ["usage", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "submit" in result.output
    assert "delete" in result.output


def _traces(*spans: tuple[str, int]) -> dict:
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": []},
                "scopeSpans": [
                    {
                        "scope": {"name": "usage"},
                        "spans": [{"spanId": span_id, "startTimeUnixNano": str(nanos)} for span_id, nanos in spans],
                    }
                ],
            }
        ]
    }


OCT_1 = 1759276800 * 1_000_000_000  # 2025-10-01T00:00:00Z
DAY = 86400 * 1_000_000_000


@responses.activate
def test_usage_list_sends_time_range_and_page(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/v1/traces", json=TRACES_DATA, status=200)
    result = runner.invoke(app, ["usage", "list", "--scope-name", "usage", "--since", "2025-10-01"])
    assert result.exit_code == 0
    assert responses.calls[0].request.params == {
        "scopeName": "usage",
        "from": "2025-10-01T00:00:00Z",
        "p": "0",
        "size": "100",
    }


@responses.activate
def test_usage_list_all_joins_the_pages_into_one_document(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    url = f"{BASE_URL}/api/v1/traces"
    responses.add(
        responses.GET,
        url,
        json=_traces(("s2", OCT_1 + DAY)),
        headers={"Link": '</api/v1/traces?size=1&p=1>; rel="next"'},
        match=[responses.matchers.query_param_matcher({"p": "0", "size": "1"})],
    )
    responses.add(
        responses.GET,
        url,
        json=_traces(("s1", OCT_1)),
        match=[responses.matchers.query_param_matcher({"p": "1", "size": "1"})],
    )
    result = runner.invoke(app, ["-o", "json", "usage", "list", "--all", "-l", "1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert [rs["scopeSpans"][0]["spans"][0]["spanId"] for rs in data["resourceSpans"]] == ["s2", "s1"]


@responses.activate
def test_usage_list_filters_spans_locally_when_the_server_ignores_the_range(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/v1/traces",
        json=_traces(("old", OCT_1 - DAY), ("s1", OCT_1 + DAY), ("s2", OCT_1 + 2 * DAY), ("s3", OCT_1 + 3 * DAY)),
    )
    result = runner.invoke(app, ["-o", "json", "usage", "list", "--since", "2025-10-01", "--limit", "2"])
    assert result.exit_code == 0
    spans = json.loads(result.stdout)["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert sorted(s["spanId"] for s in spans) == ["s2", "s3"]  # the newest two in range
    assert "does not support all filters or the page size" in result.stderr
