"""Tests for tags commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

TAGS_LIST = [
    {"id": "Governance/PII", "info": {"owner": "checkout", "description": "PII tag"}},
    {"id": "Quality/Gold", "info": {"owner": "data-team", "description": "Gold quality"}},
]


@responses.activate
def test_tags_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/tags", json=TAGS_LIST, status=200)
    result = runner.invoke(app, ["tags", "list"])
    assert result.exit_code == 0
    assert "Governance/PII" in result.output


@responses.activate
def test_tags_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/tags", json=TAGS_LIST, status=200)
    result = runner.invoke(app, ["tags", "list", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@responses.activate
def test_tags_list_with_owner(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/tags", json=[TAGS_LIST[0]], status=200)
    result = runner.invoke(app, ["tags", "list", "--owner", "checkout"])
    assert result.exit_code == 0
    assert "Governance/PII" in result.output


@responses.activate
def test_tags_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/tags/Governance/PII", json=TAGS_LIST[0], status=200)
    result = runner.invoke(app, ["tags", "get", "Governance/PII"])
    assert result.exit_code == 0
    assert "Governance/PII" in result.output


@responses.activate
def test_tags_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/tags/Governance/PII",
        status=200,
    )
    tag_file = tmp_path / "tag.json"
    tag_file.write_text(json.dumps({"id": "Governance/PII", "info": {"owner": "checkout"}}))
    result = runner.invoke(app, ["tags", "put", "Governance/PII", "--file", str(tag_file)])
    assert result.exit_code == 0
    assert "saved" in result.output


@responses.activate
def test_tags_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/tags/Governance/PII", status=200)
    result = runner.invoke(app, ["tags", "delete", "Governance/PII"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_tags_help():
    result = runner.invoke(app, ["tags", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "put" in result.output
    assert "delete" in result.output
