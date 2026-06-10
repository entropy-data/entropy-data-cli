"""Tests for organization custom-team-roles commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
COLLECTION_URL = f"{BASE_URL}/api/organization/custom-team-roles"

APPROVER = {
    "id": "00000000-0000-0000-0000-000000000001",
    "name": "Approver",
    "description": "Approves access",
    "rank": 10,
    "permissions": ["ACCESS_APPROVE", "ACCESS_EDIT"],
    "createdAt": "2026-06-10T00:00:00Z",
    "createdBy": "api-key:abc",
    "updatedAt": "2026-06-10T00:00:00Z",
    "updatedBy": "api-key:abc",
}


def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@responses.activate
def test_list_table(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, COLLECTION_URL, json=[APPROVER], status=200)
    result = runner.invoke(app, ["organization", "custom-team-roles", "list"])
    assert result.exit_code == 0, result.output
    assert "Approver" in result.output
    assert "ACCESS_APPROVE" in result.output


@responses.activate
def test_list_json(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, COLLECTION_URL, json=[APPROVER], status=200)
    result = runner.invoke(app, ["organization", "custom-team-roles", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["name"] == "Approver"
    assert data[0]["permissions"] == ["ACCESS_APPROVE", "ACCESS_EDIT"]


@responses.activate
def test_list_paging(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, COLLECTION_URL, json=[APPROVER], status=200)
    result = runner.invoke(app, ["organization", "custom-team-roles", "list", "--page", "2"])
    assert result.exit_code == 0
    assert "p=2" in responses.calls[0].request.url


@responses.activate
def test_get(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.GET, f"{COLLECTION_URL}/Approver", json=APPROVER, status=200)
    result = runner.invoke(app, ["organization", "custom-team-roles", "get", "Approver", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["name"] == "Approver"
    assert data["rank"] == 10


@responses.activate
def test_get_not_found(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.GET,
        f"{COLLECTION_URL}/Ghost",
        json={
            "type": "about:blank",
            "title": "Not Found",
            "status": 404,
            "detail": "Custom team role 'Ghost' not found",
        },
        status=404,
    )
    result = runner.invoke(app, ["organization", "custom-team-roles", "get", "Ghost"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


@responses.activate
def test_put_create_from_options(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, f"{COLLECTION_URL}/Approver", json=APPROVER, status=201)
    result = runner.invoke(
        app,
        [
            "organization",
            "custom-team-roles",
            "put",
            "Approver",
            "--description",
            "Approves access",
            "--rank",
            "10",
            "--permissions",
            "ACCESS_APPROVE,ACCESS_EDIT",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "saved" in result.output.lower()
    body = json.loads(responses.calls[0].request.body)
    assert body["name"] == "Approver"
    assert body["rank"] == 10
    assert body["permissions"] == ["ACCESS_APPROVE", "ACCESS_EDIT"]


@responses.activate
def test_put_create_from_file(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    body_file = tmp_path / "role.json"
    body_file.write_text(json.dumps({"name": "Approver", "rank": 10, "permissions": ["ACCESS_APPROVE"]}))
    responses.add(responses.PUT, f"{COLLECTION_URL}/Approver", json=APPROVER, status=201)
    result = runner.invoke(app, ["organization", "custom-team-roles", "put", "Approver", "--file", str(body_file)])
    assert result.exit_code == 0, result.output
    body = json.loads(responses.calls[0].request.body)
    assert body["name"] == "Approver"
    assert body["permissions"] == ["ACCESS_APPROVE"]


@responses.activate
def test_put_rename(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    renamed = {**APPROVER, "name": "FinalApprover"}
    responses.add(responses.PUT, f"{COLLECTION_URL}/Approver", json=renamed, status=200)
    result = runner.invoke(
        app,
        [
            "organization",
            "custom-team-roles",
            "put",
            "Approver",
            "--name",
            "FinalApprover",
            "--permissions",
            "ACCESS_APPROVE",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "renamed" in result.output.lower()
    assert "FinalApprover" in result.output
    body = json.loads(responses.calls[0].request.body)
    assert body["name"] == "FinalApprover"


@responses.activate
def test_put_permissions_repeated_and_comma_combined(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.PUT, f"{COLLECTION_URL}/Approver", json=APPROVER, status=201)
    result = runner.invoke(
        app,
        [
            "organization",
            "custom-team-roles",
            "put",
            "Approver",
            "--permissions",
            "ACCESS_APPROVE,ACCESS_EDIT",
            "--permissions",
            "ACCESS_REQUEST",
        ],
    )
    assert result.exit_code == 0, result.output
    body = json.loads(responses.calls[0].request.body)
    assert body["permissions"] == ["ACCESS_APPROVE", "ACCESS_EDIT", "ACCESS_REQUEST"]


@responses.activate
def test_put_rejects_invalid_permission(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.PUT,
        f"{COLLECTION_URL}/BadRole",
        json={
            "type": "about:blank",
            "title": "Bad Request",
            "status": 400,
            "detail": "Unknown permission(s): NOT_A_THING. Valid permissions: ...",
        },
        status=400,
    )
    result = runner.invoke(
        app,
        [
            "organization",
            "custom-team-roles",
            "put",
            "BadRole",
            "--permissions",
            "NOT_A_THING",
        ],
    )
    assert result.exit_code != 0
    assert "NOT_A_THING" in result.output


@responses.activate
def test_delete(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(responses.DELETE, f"{COLLECTION_URL}/Approver", status=204)
    result = runner.invoke(app, ["organization", "custom-team-roles", "delete", "Approver"])
    assert result.exit_code == 0, result.output
    assert "deleted" in result.output.lower()


@responses.activate
def test_delete_in_use_shows_conflict_message(monkeypatch, tmp_path):
    _setup(monkeypatch, tmp_path)
    responses.add(
        responses.DELETE,
        f"{COLLECTION_URL}/Approver",
        json={
            "type": "about:blank",
            "title": "Conflict",
            "status": 409,
            "detail": "Custom team role 'Approver' is assigned to 1 team member(s). Reassign or remove them before deleting or renaming.",
        },
        status=409,
    )
    result = runner.invoke(app, ["organization", "custom-team-roles", "delete", "Approver"])
    assert result.exit_code != 0
    assert "assigned to 1 team member" in result.output
