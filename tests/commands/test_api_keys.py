"""Tests for api-keys commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data_cli.config as cfg
from entropy_data_cli.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

API_KEY_CREATED = {
    "organizationApiKeyId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "displayName": "CI/CD Pipeline Key",
    "key": "ed-ak-abc123",
    "scope": "team",
    "teamId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
}


@responses.activate
def test_api_keys_create(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/api-keys", json=API_KEY_CREATED, status=201)
    result = runner.invoke(
        app,
        ["api-keys", "create", "--scope", "team", "--team-id", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"],
    )
    assert result.exit_code == 0
    assert "created" in result.output
    assert "ed-ak-abc123" in result.output


@responses.activate
def test_api_keys_create_with_display_name(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/api-keys", json=API_KEY_CREATED, status=201)
    result = runner.invoke(
        app,
        [
            "api-keys",
            "create",
            "--scope",
            "team",
            "--team-id",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "--display-name",
            "CI/CD Pipeline Key",
        ],
    )
    assert result.exit_code == 0
    sent_body = json.loads(responses.calls[0].request.body)
    assert sent_body["displayName"] == "CI/CD Pipeline Key"


@responses.activate
def test_api_keys_create_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/api-keys", json=API_KEY_CREATED, status=201)
    result = runner.invoke(
        app,
        [
            "api-keys",
            "create",
            "--scope",
            "team",
            "--team-id",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "--output",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["key"] == "ed-ak-abc123"


@responses.activate
def test_api_keys_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.DELETE,
        f"{BASE_URL}/api/api-keys/f47ac10b-58cc-4372-a567-0e02b2c3d479",
        status=204,
    )
    result = runner.invoke(app, ["api-keys", "delete", "f47ac10b-58cc-4372-a567-0e02b2c3d479"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_api_keys_help():
    result = runner.invoke(app, ["api-keys", "--help"])
    assert result.exit_code == 0
    assert "create" in result.output
    assert "delete" in result.output
