"""Tests for git credentials commands (organization + team scopes)."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

ORG_CRED_LIST = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "externalId": "ci-github",
        "gitConnectionType": "github",
        "host": "github.com",
        "tokenName": "CI PAT",
    },
]

CRED_RESPONSE = ORG_CRED_LIST[0]


# Organization-scope


@responses.activate
def test_org_git_credentials_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/organization/gitcredentials",
        json=ORG_CRED_LIST,
        status=200,
    )
    result = runner.invoke(app, ["organization", "git-credentials", "list"])
    assert result.exit_code == 0
    assert "ci-github" in result.output
    assert "github" in result.output


@responses.activate
def test_org_git_credentials_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/organization/gitcredentials/{CRED_RESPONSE['id']}",
        json=CRED_RESPONSE,
        status=200,
    )
    result = runner.invoke(
        app,
        ["organization", "git-credentials", "get", CRED_RESPONSE["id"], "--output", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["externalId"] == "ci-github"


@responses.activate
def test_org_git_credentials_create_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/organization/gitcredentials",
        json=CRED_RESPONSE,
        status=201,
    )
    result = runner.invoke(
        app,
        [
            "organization",
            "git-credentials",
            "create",
            "--git-connection-type",
            "github",
            "--authentication-token",
            "ghp_secret",
            "--external-id",
            "ci-github",
            "--token-name",
            "CI PAT",
        ],
    )
    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "gitConnectionType": "github",
        "authenticationToken": "ghp_secret",
        "externalId": "ci-github",
        "tokenName": "CI PAT",
    }
    assert "created" in result.output


@responses.activate
def test_org_git_credentials_update(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/organization/gitcredentials/{CRED_RESPONSE['id']}",
        status=200,
    )
    result = runner.invoke(
        app,
        [
            "organization",
            "git-credentials",
            "update",
            CRED_RESPONSE["id"],
            "--git-connection-type",
            "github",
            "--token-name",
            "Rotated PAT",
        ],
    )
    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    # No authenticationToken means server preserves the existing one
    assert body == {"gitConnectionType": "github", "tokenName": "Rotated PAT"}


@responses.activate
def test_org_git_credentials_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.DELETE,
        f"{BASE_URL}/api/organization/gitcredentials/{CRED_RESPONSE['id']}",
        status=204,
    )
    result = runner.invoke(app, ["organization", "git-credentials", "delete", CRED_RESPONSE["id"]])
    assert result.exit_code == 0
    assert "deleted" in result.output


# Team-scope


@responses.activate
def test_team_git_credentials_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/teams/marketing/gitcredentials",
        json=ORG_CRED_LIST,
        status=200,
    )
    result = runner.invoke(app, ["teams", "git-credentials", "list", "marketing"])
    assert result.exit_code == 0
    assert "ci-github" in result.output


@responses.activate
def test_team_git_credentials_create_from_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/teams/marketing/gitcredentials",
        json=CRED_RESPONSE,
        status=201,
    )
    body_file = tmp_path / "body.json"
    body_file.write_text(
        json.dumps(
            {
                "gitConnectionType": "gitlab",
                "authenticationToken": "glpat_abc",
                "host": "gitlab.example.com",
            }
        )
    )
    result = runner.invoke(
        app,
        ["teams", "git-credentials", "create", "marketing", "--file", str(body_file)],
    )
    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body["gitConnectionType"] == "gitlab"
    assert body["host"] == "gitlab.example.com"


def test_team_git_credentials_create_validates_token(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    result = runner.invoke(
        app,
        [
            "teams",
            "git-credentials",
            "create",
            "marketing",
            "--git-connection-type",
            "github",
        ],
    )
    assert result.exit_code != 0


def test_team_git_credentials_rejects_bad_type(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    result = runner.invoke(
        app,
        [
            "teams",
            "git-credentials",
            "create",
            "marketing",
            "--git-connection-type",
            "bogus",
            "--authentication-token",
            "x",
        ],
    )
    assert result.exit_code != 0


def test_org_git_credentials_help():
    result = runner.invoke(app, ["organization", "git-credentials", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "get", "create", "update", "delete"):
        assert cmd in result.output


def test_team_git_credentials_help():
    result = runner.invoke(app, ["teams", "git-credentials", "--help"])
    assert result.exit_code == 0
    for cmd in ("list", "get", "create", "update", "delete"):
        assert cmd in result.output
