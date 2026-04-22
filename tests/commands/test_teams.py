"""Tests for teams commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

TEAMS_LIST = [
    {"id": "marketing", "name": "Marketing", "type": "Team", "parent": "sales"},
    {"id": "engineering", "name": "Engineering", "type": "Domain Team", "parent": None},
]


@responses.activate
def test_teams_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/teams", json=TEAMS_LIST, status=200)
    result = runner.invoke(app, ["teams", "list"])
    assert result.exit_code == 0
    assert "marketing" in result.output
    assert "Marketing" in result.output


@responses.activate
def test_teams_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/teams", json=TEAMS_LIST, status=200)
    result = runner.invoke(app, ["teams", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@responses.activate
def test_teams_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/teams/marketing", json=TEAMS_LIST[0], status=200)
    result = runner.invoke(app, ["teams", "get", "marketing"])
    assert result.exit_code == 0
    assert "marketing" in result.output


@responses.activate
def test_teams_get_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/teams/marketing", json=TEAMS_LIST[0], status=200)
    result = runner.invoke(app, ["teams", "get", "marketing", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "marketing"


@responses.activate
def test_teams_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/teams/marketing",
        status=200,
        headers={"location-html": "https://app.entropy-data.com/teams/marketing"},
    )
    team_file = tmp_path / "team.json"
    team_file.write_text(json.dumps({"id": "marketing", "name": "Marketing", "type": "Team"}))
    result = runner.invoke(app, ["teams", "put", "marketing", "--file", str(team_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@responses.activate
def test_teams_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/teams/marketing", status=200)
    result = runner.invoke(app, ["teams", "delete", "marketing"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_teams_list_no_api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    result = runner.invoke(app, ["teams", "list"])
    assert result.exit_code != 0


def test_teams_help():
    result = runner.invoke(app, ["teams", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "put" in result.output
    assert "delete" in result.output
