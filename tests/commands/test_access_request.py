"""Tests for the `access request` command."""

import json
import re

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_request_with_consumer_team(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    captured: dict = {}

    def _capture(request):
        captured["body"] = json.loads(request.body)
        return (200, {}, "")

    responses.add_callback(responses.PUT, re.compile(rf"{BASE_URL}/api/access/.+"), callback=_capture)

    result = runner.invoke(
        app,
        [
            "access",
            "request",
            "dp_account_master",
            "accounts",
            "--purpose",
            "Building churn model.",
            "--consumer-team",
            "customer-success",
        ],
    )
    assert result.exit_code == 0
    assert "submitted" in result.output
    body = captured["body"]
    assert body["provider"] == {"dataProductId": "dp_account_master", "outputPortId": "accounts"}
    assert body["consumer"] == {"teamId": "customer-success"}
    assert body["info"] == {"purpose": "Building churn model."}
    assert UUID_RE.match(body["id"])


@responses.activate
def test_request_with_explicit_id_and_roles(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    captured: dict = {}

    def _capture(request):
        captured["body"] = json.loads(request.body)
        return (200, {}, "")

    responses.add_callback(responses.PUT, f"{BASE_URL}/api/access/req-001", callback=_capture)

    result = runner.invoke(
        app,
        [
            "access",
            "request",
            "dp_a",
            "op_a",
            "--purpose",
            "x",
            "--consumer-user",
            "alice@example.com",
            "--roles",
            "analyst, data_engineer",
            "--id",
            "req-001",
        ],
    )
    assert result.exit_code == 0
    body = captured["body"]
    assert body["id"] == "req-001"
    assert body["consumer"] == {"userId": "alice@example.com"}
    assert body["roles"] == ["analyst", "data_engineer"]


def test_request_missing_consumer(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    result = runner.invoke(
        app,
        ["access", "request", "dp_a", "op_a", "--purpose", "x"],
    )
    assert result.exit_code == 2
    assert "consumer" in result.output.lower()


def test_request_multiple_consumers(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    result = runner.invoke(
        app,
        [
            "access",
            "request",
            "dp_a",
            "op_a",
            "--purpose",
            "x",
            "--consumer-team",
            "t1",
            "--consumer-user",
            "u1",
        ],
    )
    assert result.exit_code == 2


@responses.activate
def test_list_with_filters(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, f"{BASE_URL}/api/access", json=[], status=200)
    result = runner.invoke(
        app,
        [
            "access",
            "list",
            "--provider-dataproduct",
            "dp_provider",
            "--consumer-dataproduct",
            "dp_consumer",
            "--consumer-type",
            "team",
        ],
    )
    assert result.exit_code == 0
    qs = responses.calls[0].request.url.split("?", 1)[1]
    assert "providerDataProductId=dp_provider" in qs
    assert "consumerDataProductId=dp_consumer" in qs
    assert "consumerType=team" in qs


@responses.activate
def test_list_without_filters(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, f"{BASE_URL}/api/access", json=[], status=200)
    result = runner.invoke(app, ["access", "list"])
    assert result.exit_code == 0
    qs = responses.calls[0].request.url.split("?", 1)[1]
    assert "providerDataProductId" not in qs
    assert "consumerDataProductId" not in qs
    assert "consumerType" not in qs
