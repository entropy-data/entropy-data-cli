"""Tests for policies commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

POLICIES_LIST = [
    {"id": "pol_pii_handling", "name": "PII Handling", "status": "Published", "content": "..."},
    {"id": "pol_retention", "name": "Data Retention", "status": "Draft", "content": "..."},
]


@responses.activate
def test_policies_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/policies", json=POLICIES_LIST, status=200)
    result = runner.invoke(app, ["policies", "list"])
    assert result.exit_code == 0
    assert "PII Handling" in result.output
    assert "Data Retention" in result.output


@responses.activate
def test_policies_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/policies", json=POLICIES_LIST, status=200)
    result = runner.invoke(app, ["policies", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@responses.activate
def test_policies_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/policies/pol_pii_handling",
        json=POLICIES_LIST[0],
        status=200,
    )
    result = runner.invoke(app, ["policies", "get", "pol_pii_handling"])
    assert result.exit_code == 0
    assert "PII Handling" in result.output


@responses.activate
def test_policies_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/policies/pol_pii_handling",
        status=200,
    )
    policy_file = tmp_path / "policy.json"
    policy_file.write_text(json.dumps({"id": "pol_pii_handling", "name": "PII Handling", "status": "Draft"}))
    result = runner.invoke(app, ["policies", "put", "pol_pii_handling", "--file", str(policy_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@responses.activate
def test_policies_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/policies/pol_pii_handling", status=200)
    result = runner.invoke(app, ["policies", "delete", "pol_pii_handling"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_policies_help():
    result = runner.invoke(app, ["policies", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "put" in result.output
    assert "delete" in result.output
