"""Tests for the settings team-roles commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
URL = f"{BASE_URL}/api/settings/team-roles"

CUSTOM = {
    "mode": "custom-team-roles",
    "team-roles": [
        {"name": "Approver", "rank": 0, "permissions": ["ACCESS_APPROVE", "ACCESS_EDIT"]},
    ],
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_get_default_table(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, URL, json={"mode": "default"}, status=200)
    result = runner.invoke(app, ["settings", "team-roles", "get"])
    assert result.exit_code == 0, result.output
    assert "default" in result.output


@responses.activate
def test_get_custom_table(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, URL, json=CUSTOM, status=200)
    result = runner.invoke(app, ["settings", "team-roles", "get"])
    assert result.exit_code == 0, result.output
    assert "custom-team-roles" in result.output
    assert "Approver" in result.output
    assert "ACCESS_APPROVE" in result.output


@responses.activate
def test_get_json(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, URL, json=CUSTOM, status=200)
    result = runner.invoke(app, ["settings", "team-roles", "get", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["mode"] == "custom-team-roles"
    assert data["team-roles"][0]["name"] == "Approver"


@responses.activate
def test_put_default(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, URL, json={"mode": "default"}, status=200)
    body_file = tmp_path / "body.json"
    body_file.write_text(json.dumps({"mode": "default"}))
    result = runner.invoke(app, ["settings", "team-roles", "put", "--file", str(body_file)])
    assert result.exit_code == 0, result.output
    assert json.loads(responses.calls[0].request.body) == {"mode": "default"}


@responses.activate
def test_put_custom_from_yaml(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, URL, json=CUSTOM, status=200)
    body_file = tmp_path / "body.yaml"
    body_file.write_text(
        "mode: custom-team-roles\nteam-roles:\n  - name: Approver\n    permissions: [ACCESS_APPROVE]\n"
    )
    result = runner.invoke(app, ["settings", "team-roles", "put", "--file", str(body_file)])
    assert result.exit_code == 0, result.output
    sent = json.loads(responses.calls[0].request.body)
    assert sent["mode"] == "custom-team-roles"
    assert sent["team-roles"][0]["name"] == "Approver"


@responses.activate
def test_put_custom_conflict_surfaces_error(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.PUT,
        URL,
        json={"detail": "Cannot switch to custom team roles with an empty role list."},
        status=409,
    )
    body_file = tmp_path / "body.json"
    body_file.write_text(json.dumps({"mode": "custom-team-roles", "team-roles": []}))
    result = runner.invoke(app, ["settings", "team-roles", "put", "--file", str(body_file)])
    assert result.exit_code == 1
    assert "empty role list" in result.output


def test_help_lists_subcommands(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    result = runner.invoke(app, ["settings", "team-roles", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "put" in result.output
