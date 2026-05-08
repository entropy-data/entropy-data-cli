"""Tests for organization commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
ORG_SETTINGS_URL = f"{BASE_URL}/api/organization/settings"

ORG_PAYLOAD = {
    "vanityUrl": "acme",
    "host": "https://acme.entropy-data.com",
    "fullName": "Acme Corp",
    "logoUrl": "https://example.com/logo.png",
    "supportEmailAddress": "support@acme.com",
    "brand": "default",
    "plan": "enterprise",
    "sso": {
        "issuer": "azuresso",
        "tenant": "tenant-id",
        "autoJoin": True,
    },
}


@responses.activate
def test_organization_get_table(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, ORG_SETTINGS_URL, json=ORG_PAYLOAD, status=200)
    result = runner.invoke(app, ["organization", "get"])
    assert result.exit_code == 0
    assert "acme" in result.output
    assert "Acme Corp" in result.output
    assert "enterprise" in result.output
    assert "azuresso" in result.output


@responses.activate
def test_organization_get_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, ORG_SETTINGS_URL, json=ORG_PAYLOAD, status=200)
    result = runner.invoke(app, ["organization", "get", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["vanityUrl"] == "acme"
    assert data["plan"] == "enterprise"
    assert data["sso"]["issuer"] == "azuresso"


@responses.activate
def test_organization_get_minimal_payload(monkeypatch, tmp_path):
    """Org without SSO / optional fields renders cleanly."""
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        ORG_SETTINGS_URL,
        json={
            "vanityUrl": "minimal",
            "host": "https://minimal.entropy-data.com",
            "fullName": "Minimal",
            "logoUrl": "",
            "supportEmailAddress": None,
            "brand": None,
            "plan": None,
            "sso": None,
        },
        status=200,
    )
    result = runner.invoke(app, ["organization", "get"])
    assert result.exit_code == 0
    assert "minimal" in result.output


def test_organization_help():
    result = runner.invoke(app, ["organization", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
