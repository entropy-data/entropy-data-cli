"""Tests for connection commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
ORG_SETTINGS_URL = f"{BASE_URL}/api/organization/settings"


def test_connection_list_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    result = runner.invoke(app, ["connection", "list"])
    assert result.exit_code == 0
    assert "No connections" in result.output


@responses.activate
def test_connection_add_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    # Auto-fetch fails (no responses registered) — connection still saves without vanity
    result = runner.invoke(app, ["connection", "add", "prod", "--api-key", "mykey123456", "--host", BASE_URL])
    assert result.exit_code == 0
    assert "saved" in result.output

    result = runner.invoke(app, ["connection", "list"])
    assert result.exit_code == 0
    assert "prod" in result.output
    assert "*" in result.output  # default marker


@responses.activate
def test_connection_add_with_api_key_does_not_prompt_for_host(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    # scripted call: API key given, host omitted — silently defaults, no prompt
    result = runner.invoke(app, ["connection", "add", "prod", "--api-key", "mykey123456"])
    assert result.exit_code == 0
    assert "saved" in result.output
    assert "Host" not in result.output
    result = runner.invoke(app, ["connection", "get", "prod", "-o", "json"])
    assert json.loads(result.output)["host"] == cfg.DEFAULT_HOST


@responses.activate
def test_connection_add_interactive_confirms_host_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    # interactive call (no API key): prompts for key AND host; enter accepts the cloud default
    result = runner.invoke(app, ["connection", "add", "prod"], input="mykey123456\n\n")
    assert result.exit_code == 0
    assert "saved" in result.output
    assert f"Host [{cfg.DEFAULT_HOST}]" in result.output
    result = runner.invoke(app, ["connection", "get", "prod", "-o", "json"])
    assert json.loads(result.output)["host"] == cfg.DEFAULT_HOST


@responses.activate
def test_connection_add_interactive_overwrites_host(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    result = runner.invoke(app, ["connection", "add", "local"], input="mykey123456\nhttp://localhost:8081\n")
    assert result.exit_code == 0
    assert "saved" in result.output
    result = runner.invoke(app, ["connection", "get", "local", "-o", "json"])
    assert json.loads(result.output)["host"] == "http://localhost:8081"


@responses.activate
def test_connection_add_interactive_with_host_flag_does_not_prompt_for_host(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    # host given explicitly: only the API key is prompted
    result = runner.invoke(
        app, ["connection", "add", "local", "--host", "http://localhost:8081"], input="mykey123456\n"
    )
    assert result.exit_code == 0
    assert "saved" in result.output
    assert "Host" not in result.output
    result = runner.invoke(app, ["connection", "get", "local", "-o", "json"])
    assert json.loads(result.output)["host"] == "http://localhost:8081"


@responses.activate
def test_connection_add_fetches_vanity_url(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    responses.add(
        responses.GET,
        ORG_SETTINGS_URL,
        json={"vanityUrl": "acme", "host": BASE_URL, "fullName": "Acme Corp", "logoUrl": ""},
        status=200,
    )
    result = runner.invoke(app, ["connection", "add", "prod", "--api-key", "mykey", "--host", BASE_URL])
    assert result.exit_code == 0
    assert "saved" in result.output
    assert "acme" in result.output  # mentioned in the fetch confirmation line

    result = runner.invoke(app, ["connection", "list"])
    assert result.exit_code == 0
    assert "acme" in result.output


@responses.activate
def test_connection_add_handles_fetch_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    # Older server / endpoint missing → 404
    responses.add(responses.GET, ORG_SETTINGS_URL, json={"detail": "Not found"}, status=404)
    result = runner.invoke(app, ["connection", "add", "prod", "--api-key", "mykey", "--host", BASE_URL])
    assert result.exit_code == 0
    assert "saved" in result.output

    result = runner.invoke(app, ["connection", "list"])
    assert result.exit_code == 0
    assert "prod" in result.output


@responses.activate
def test_connection_remove(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "key1", "--host", BASE_URL])
    result = runner.invoke(app, ["connection", "remove", "prod"])
    assert result.exit_code == 0
    assert "removed" in result.output


@responses.activate
def test_connection_set_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "key1", "--host", BASE_URL])
    runner.invoke(app, ["connection", "add", "dev", "--api-key", "key2", "--host", "http://localhost:8080"])
    result = runner.invoke(app, ["connection", "set-default", "dev"])
    assert result.exit_code == 0
    assert "dev" in result.output


@responses.activate
def test_connection_test_success(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "key1", "--host", BASE_URL])
    responses.add(responses.GET, f"{BASE_URL}/api/teams", json=[], status=200)
    result = runner.invoke(app, ["connection", "test"])
    assert result.exit_code == 0
    assert "successful" in result.output


@responses.activate
def test_connection_get_masked_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "abcd1234efgh5678", "--host", BASE_URL])
    result = runner.invoke(app, ["connection", "get", "prod"])
    assert result.exit_code == 0
    assert "abcd...5678" in result.output
    assert "abcd1234efgh5678" not in result.output


@responses.activate
def test_connection_get_show_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "abcd1234efgh5678", "--host", BASE_URL])
    result = runner.invoke(app, ["connection", "get", "prod", "--show-api-key"])
    assert result.exit_code == 0
    assert "abcd1234efgh5678" in result.output


@responses.activate
def test_connection_get_uses_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "abcd1234efgh5678", "--host", BASE_URL])
    result = runner.invoke(app, ["connection", "get"])
    assert result.exit_code == 0
    assert "prod" in result.output
    assert "default" in result.output


@responses.activate
def test_connection_get_json(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "abcd1234efgh5678", "--host", BASE_URL])
    result = runner.invoke(app, ["connection", "get", "prod", "--show-api-key", "-o", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["name"] == "prod"
    assert payload["host"] == BASE_URL
    assert payload["api_key"] == "abcd1234efgh5678"
    assert payload["default"] is True


def test_connection_get_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    result = runner.invoke(app, ["connection", "get", "nope"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_connection_get_no_default(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    result = runner.invoke(app, ["connection", "get"])
    assert result.exit_code == 1
    assert "no default" in result.output.lower() or "no connection specified" in result.output.lower()


def test_connection_help():
    result = runner.invoke(app, ["connection", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "get" in result.output
    assert "add" in result.output
    assert "remove" in result.output
    assert "set-default" in result.output
    assert "test" in result.output
