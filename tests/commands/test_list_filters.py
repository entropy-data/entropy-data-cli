"""Tests for the list filters that pass through to the API's query parameters."""

import httpx
import pytest
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


@pytest.fixture(autouse=True)
def _setup(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


def _params(route) -> list[tuple[str, str]]:
    return sorted(route.calls.last.request.url.params.multi_items())


@respx.mock
def test_dataproducts_list_filters_by_team_domain_and_type():
    route = respx.get(f"{BASE_URL}/api/dataproducts").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(
        app,
        ["dataproducts", "list", "--team", "sales", "--team", "ops", "--domain", "retail", "--type", "source-aligned"],
    )
    assert result.exit_code == 0, result.output
    assert _params(route) == [
        ("domainId", "retail"),
        ("p", "0"),
        ("teamId", "ops"),
        ("teamId", "sales"),
        ("type", "source-aligned"),
    ]


@respx.mock
def test_datacontracts_list_filters_by_team_domain_and_status():
    route = respx.get(f"{BASE_URL}/api/datacontracts").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(app, ["datacontracts", "list", "--team", "sales", "--domain", "retail", "--status", "draft"])
    assert result.exit_code == 0, result.output
    assert _params(route) == [("domainId", "retail"), ("p", "0"), ("status", "draft"), ("teamId", "sales")]


@respx.mock
def test_assets_list_filters_by_source_qualified_name_and_source_id():
    route = respx.get(f"{BASE_URL}/api/assets").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(
        app,
        ["assets", "list", "--source", "snowflake", "--qualified-name", "DB.SALES.ORDERS", "--source-id", "42"],
    )
    assert result.exit_code == 0, result.output
    assert _params(route) == [
        ("p", "0"),
        ("qualifiedName", "DB.SALES.ORDERS"),
        ("source", "snowflake"),
        ("sourceId", "42"),
    ]


@respx.mock
def test_assets_list_without_filters_sends_only_the_page():
    route = respx.get(f"{BASE_URL}/api/assets").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(app, ["assets", "list"])
    assert result.exit_code == 0, result.output
    assert _params(route) == [("p", "0")]


@respx.mock
def test_example_data_list_filters_by_output_port_and_data_contract():
    route = respx.get(f"{BASE_URL}/api/example-data").mock(return_value=httpx.Response(200, json=[]))
    result = runner.invoke(
        app, ["example-data", "list", "--output-port-id", "port-1", "--data-contract-id", "contract-1"]
    )
    assert result.exit_code == 0, result.output
    assert _params(route) == [("dataContractId", "contract-1"), ("outputPortId", "port-1")]


@respx.mock
def test_search_takes_mode_and_diagnostics():
    route = respx.get(f"{BASE_URL}/api/search").mock(return_value=httpx.Response(200, json={"results": []}))
    result = runner.invoke(app, ["search", "query", "orders", "--mode", "find", "--diagnostics"])
    assert result.exit_code == 0, result.output
    assert _params(route) == [("diagnostics", "true"), ("query", "orders"), ("searchMode", "FIND")]


def test_search_rejects_an_unknown_mode():
    result = runner.invoke(app, ["search", "query", "orders", "--mode", "browse"])
    assert result.exit_code != 0
