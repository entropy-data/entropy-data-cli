"""Tests for connection commands."""

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


def test_connection_list_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    result = runner.invoke(app, ["connection", "list"])
    assert result.exit_code == 0
    assert "No connections" in result.output


def test_connection_add_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    result = runner.invoke(app, ["connection", "add", "prod", "--api-key", "mykey123456", "--host", BASE_URL])
    assert result.exit_code == 0
    assert "saved" in result.output

    result = runner.invoke(app, ["connection", "list"])
    assert result.exit_code == 0
    assert "prod" in result.output
    assert "*" in result.output  # default marker


def test_connection_remove(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    runner.invoke(app, ["connection", "add", "prod", "--api-key", "key1", "--host", BASE_URL])
    result = runner.invoke(app, ["connection", "remove", "prod"])
    assert result.exit_code == 0
    assert "removed" in result.output


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


def test_connection_help():
    result = runner.invoke(app, ["connection", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "remove" in result.output
    assert "set-default" in result.output
    assert "test" in result.output
