"""Tests for costs commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

COSTS_LIST = [
    {"id": "cost-1", "dataProductId": "dp-1", "amount": 100.0, "currency": "USD"},
    {"id": "cost-2", "dataProductId": "dp-1", "amount": 50.0, "currency": "EUR"},
]


@responses.activate
def test_costs_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/costs", json=COSTS_LIST, status=200)
    result = runner.invoke(app, ["costs", "list", "--data-product-id", "dp-1"])
    assert result.exit_code == 0
    assert "cost-1" in result.output


@responses.activate
def test_costs_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{BASE_URL}/api/costs", json=COSTS_LIST, status=200)
    result = runner.invoke(app, ["costs", "list", "--data-product-id", "dp-1", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@responses.activate
def test_costs_add(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.POST, f"{BASE_URL}/api/costs", status=200)
    cost_file = tmp_path / "cost.json"
    cost_file.write_text(json.dumps({"dataProductId": "dp-1", "amount": 100.0, "currency": "USD"}))
    result = runner.invoke(app, ["costs", "add", "--file", str(cost_file)])
    assert result.exit_code == 0
    assert "added" in result.output


@responses.activate
def test_costs_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{BASE_URL}/api/costs/cost-1", status=200)
    result = runner.invoke(app, ["costs", "delete", "cost-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_costs_help():
    result = runner.invoke(app, ["costs", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "delete" in result.output
