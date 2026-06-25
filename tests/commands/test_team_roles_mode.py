"""Tests for organization team-roles-mode commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
URL = f"{BASE_URL}/api/organization/team-roles-mode"


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_get_table(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, URL, json={"mode": "CUSTOM"}, status=200)
    result = runner.invoke(app, ["organization", "team-roles-mode", "get"])
    assert result.exit_code == 0, result.output
    assert "CUSTOM" in result.output


@responses.activate
def test_get_json(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, URL, json={"mode": "DEFAULT"}, status=200)
    result = runner.invoke(app, ["organization", "team-roles-mode", "get", "--output", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["mode"] == "DEFAULT"


@responses.activate
def test_set_custom(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, URL, json={"mode": "CUSTOM"}, status=200)
    result = runner.invoke(app, ["organization", "team-roles-mode", "set", "CUSTOM"])
    assert result.exit_code == 0, result.output
    assert "CUSTOM" in result.output
    assert json.loads(responses.calls[0].request.body) == {"mode": "CUSTOM"}


@responses.activate
def test_set_default(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, URL, json={"mode": "DEFAULT"}, status=200)
    result = runner.invoke(app, ["organization", "team-roles-mode", "set", "DEFAULT"])
    assert result.exit_code == 0, result.output
    assert json.loads(responses.calls[0].request.body) == {"mode": "DEFAULT"}


def test_set_rejects_unknown_mode(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    result = runner.invoke(app, ["organization", "team-roles-mode", "set", "BOGUS"])
    assert result.exit_code != 0


@responses.activate
def test_set_custom_conflict_surfaces_error(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.PUT,
        URL,
        json={"detail": "Cannot switch to CUSTOM team roles: no custom team roles are defined."},
        status=409,
    )
    result = runner.invoke(app, ["organization", "team-roles-mode", "set", "CUSTOM"])
    assert result.exit_code == 1
    assert "no custom team roles" in result.output


def test_help_lists_subcommands(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    result = runner.invoke(app, ["organization", "team-roles-mode", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "set" in result.output
