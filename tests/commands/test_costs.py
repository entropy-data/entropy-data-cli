"""Tests for costs commands."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"

COSTS_LIST = [
    {"id": "cost-1", "dataProductId": "dp-1", "amount": 100.0, "currency": "USD"},
    {"id": "cost-2", "dataProductId": "dp-1", "amount": 50.0, "currency": "EUR"},
]


@respx.mock
def test_costs_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/costs").mock(return_value=httpx.Response(200, json=COSTS_LIST))
    result = runner.invoke(app, ["costs", "list", "--data-product-id", "dp-1"])
    assert result.exit_code == 0
    assert "cost-1" in result.output


@respx.mock
def test_costs_list_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/costs").mock(return_value=httpx.Response(200, json=COSTS_LIST))
    result = runner.invoke(app, ["costs", "list", "--data-product-id", "dp-1", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 2


@respx.mock
def test_costs_add(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.post(f"{BASE_URL}/api/costs").mock(return_value=httpx.Response(200))
    cost_file = tmp_path / "cost.json"
    cost_file.write_text(json.dumps({"dataProductId": "dp-1", "amount": 100.0, "currency": "USD"}))
    result = runner.invoke(app, ["costs", "add", "--file", str(cost_file)])
    assert result.exit_code == 0
    assert "added" in result.output


@respx.mock
def test_costs_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{BASE_URL}/api/costs/cost-1").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["costs", "delete", "cost-1"])
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_costs_help():
    result = runner.invoke(app, ["costs", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "add" in result.output
    assert "delete" in result.output
