"""Tests for team notification-channels commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

CHANNEL_PAYLOAD = {
    "id": "slack-alerts",
    "type": "slack",
    "config": {"webhook": "https://hooks.slack.example.com/abc"},
}


@responses.activate
def test_notifications_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/teams/marketing/notification-channels/slack-alerts",
        json=CHANNEL_PAYLOAD,
        status=200,
    )
    result = runner.invoke(app, ["teams", "notifications", "get", "marketing", "slack-alerts"])
    assert result.exit_code == 0
    assert "slack-alerts" in result.output


@responses.activate
def test_notifications_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/teams/marketing/notification-channels/slack-alerts",
        status=200,
    )
    body_file = tmp_path / "channel.json"
    body_file.write_text(json.dumps(CHANNEL_PAYLOAD))
    result = runner.invoke(
        app,
        ["teams", "notifications", "put", "marketing", "slack-alerts", "--file", str(body_file)],
    )
    assert result.exit_code == 0
    assert "saved" in result.output
    body = json.loads(responses.calls[0].request.body)
    assert body["type"] == "slack"


@responses.activate
def test_notifications_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.DELETE,
        f"{BASE_URL}/api/teams/marketing/notification-channels/slack-alerts",
        status=200,
    )
    result = runner.invoke(app, ["teams", "notifications", "delete", "marketing", "slack-alerts"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_notifications_help():
    result = runner.invoke(app, ["teams", "notifications", "--help"])
    assert result.exit_code == 0
    for cmd in ("get", "put", "delete"):
        assert cmd in result.output
