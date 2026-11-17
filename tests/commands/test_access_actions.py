"""Tests for `access approve`, `access reject` and `access cancel`."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


def _mock(action: str):
    return respx.post(f"{BASE_URL}/api/access/agr-1/{action}").mock(return_value=httpx.Response(200))


def _body(route):
    content = route.calls.last.request.content
    return json.loads(content) if content else None


@respx.mock
def test_reject_without_reason_sends_no_body(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    route = _mock("reject")
    result = runner.invoke(app, ["access", "reject", "agr-1"])
    assert result.exit_code == 0, result.output
    assert _body(route) is None


@respx.mock
def test_reject_with_reason(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    route = _mock("reject")
    result = runner.invoke(app, ["access", "reject", "agr-1", "--reason", "Use the aggregated port."])
    assert result.exit_code == 0, result.output
    assert _body(route) == {"reason": "Use the aggregated port."}


@respx.mock
def test_reject_surfaces_a_required_reason(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    respx.post(f"{BASE_URL}/api/access/agr-1/reject").mock(
        return_value=httpx.Response(400, json={"detail": "A reason is required to reject this access request."})
    )
    result = runner.invoke(app, ["access", "reject", "agr-1"])
    assert result.exit_code != 0
    assert "reason is required" in result.output


@respx.mock
def test_cancel_without_options_sends_no_body(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    route = _mock("cancel")
    result = runner.invoke(app, ["access", "cancel", "agr-1"])
    assert result.exit_code == 0, result.output
    assert _body(route) is None


@respx.mock
def test_cancel_with_reason_and_end(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    route = _mock("cancel")
    result = runner.invoke(
        app, ["access", "cancel", "agr-1", "--reason", "Security incident", "--end", "2026-12-31T00:00:00Z"]
    )
    assert result.exit_code == 0, result.output
    assert _body(route) == {"endTimestamp": "2026-12-31T00:00:00Z", "reason": "Security incident"}


@respx.mock
def test_cancel_end_keeps_an_offset(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    route = _mock("cancel")
    result = runner.invoke(app, ["access", "cancel", "agr-1", "--end", "2026-12-31T09:00:00+01:00"])
    assert result.exit_code == 0, result.output
    assert _body(route) == {"endTimestamp": "2026-12-31T09:00:00+01:00"}


def test_cancel_rejects_an_end_without_time_zone(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    result = runner.invoke(app, ["access", "cancel", "agr-1", "--end", "2026-12-31T00:00:00"])
    assert result.exit_code != 0
    assert "time zone" in result.output


def test_cancel_rejects_an_invalid_end(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    result = runner.invoke(app, ["access", "cancel", "agr-1", "--end", "next week"])
    assert result.exit_code != 0
    assert "Invalid --end" in result.output


@respx.mock
def test_approve_sends_no_body(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    route = _mock("approve")
    result = runner.invoke(app, ["access", "approve", "agr-1"])
    assert result.exit_code == 0, result.output
    assert _body(route) is None
