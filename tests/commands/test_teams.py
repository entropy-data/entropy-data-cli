"""Tests for teams commands."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

TEAMS_LIST = [
    {"id": "marketing", "name": "Marketing", "type": "Team", "parent": "sales"},
    {"id": "engineering", "name": "Engineering", "type": "Domain Team", "parent": None},
]

TEAMS_LIST_WITH_MEMBERS = [
    {
        "id": "marketing",
        "name": "Marketing",
        "type": "Team",
        "parent": "sales",
        "members": [
            {"emailAddress": "alice@example.com", "role": "Owner"},
            {"emailAddress": "bob@example.com", "role": "Member"},
        ],
    },
    {
        "id": "engineering",
        "name": "Engineering",
        "type": "Domain Team",
        "parent": None,
        "members": [{"emailAddress": "carol@example.com", "role": "Lead"}],
    },
    {
        "id": "platform",
        "name": "Platform",
        "type": "Team",
        "parent": None,
        "members": [{"emailAddress": "alice@example.com", "role": "Maintainer"}],
    },
]


@respx.mock
def test_teams_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/teams").mock(return_value=httpx.Response(200, json=TEAMS_LIST))
    result = runner.invoke(app, ["teams", "list"])
    assert result.exit_code == 0
    assert "marketing" in result.output
    assert "Marketing" in result.output


@respx.mock
def test_teams_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/teams").mock(return_value=httpx.Response(200, json=TEAMS_LIST))
    result = runner.invoke(app, ["teams", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@respx.mock
def test_teams_list_member_filter(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/teams").mock(return_value=httpx.Response(200, json=TEAMS_LIST_WITH_MEMBERS))
    result = runner.invoke(app, ["teams", "list", "--member", "alice@example.com"])
    assert result.exit_code == 0
    assert "marketing" in result.output
    assert "platform" in result.output
    assert "engineering" not in result.output
    assert "Owner" in result.output
    assert "Maintainer" in result.output


@respx.mock
def test_teams_list_member_filter_case_insensitive(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/teams").mock(return_value=httpx.Response(200, json=TEAMS_LIST_WITH_MEMBERS))
    result = runner.invoke(app, ["teams", "list", "-m", "ALICE@example.com", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    ids = {t["id"] for t in data}
    assert ids == {"marketing", "platform"}
    roles = {t["id"]: t["role"] for t in data}
    assert roles == {"marketing": "Owner", "platform": "Maintainer"}


@respx.mock
def test_teams_list_member_filter_paginates(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/teams", params__eq={"p": "0"}).mock(
        return_value=httpx.Response(
            200, json=TEAMS_LIST_WITH_MEMBERS[:1], headers={"Link": '</api/teams?p=1>; rel="next"'}
        )
    )
    respx.get(f"{BASE_URL}/api/teams", params__eq={"p": "1"}).mock(
        return_value=httpx.Response(200, json=TEAMS_LIST_WITH_MEMBERS[1:])
    )
    result = runner.invoke(app, ["teams", "list", "--member", "alice@example.com", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    ids = {t["id"] for t in data}
    assert ids == {"marketing", "platform"}


@respx.mock
def test_teams_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/teams/marketing").mock(return_value=httpx.Response(200, json=TEAMS_LIST[0]))
    result = runner.invoke(app, ["teams", "get", "marketing"])
    assert result.exit_code == 0
    assert "marketing" in result.output


@respx.mock
def test_teams_get_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/teams/marketing").mock(return_value=httpx.Response(200, json=TEAMS_LIST[0]))
    result = runner.invoke(app, ["teams", "get", "marketing", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "marketing"


@respx.mock
def test_teams_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/teams/marketing").mock(
        return_value=httpx.Response(200, headers={"location-html": "https://app.entropy-data.com/teams/marketing"})
    )
    team_file = tmp_path / "team.json"
    team_file.write_text(json.dumps({"id": "marketing", "name": "Marketing", "type": "Team"}))
    result = runner.invoke(app, ["teams", "put", "marketing", "--file", str(team_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@respx.mock
def test_teams_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{BASE_URL}/api/teams/marketing").mock(return_value=httpx.Response(200))
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
