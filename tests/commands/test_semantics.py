"""Tests for semantics commands."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
NS_URL = f"{BASE_URL}/api/semantics/experimental/namespaces"

NAMESPACES = [
    {"namespace": "main", "name": "Main", "team": "checkout", "read_only": False},
    {"namespace": "archive", "name": "Archive", "team": "ops", "read_only": True},
]

CONCEPT = {
    "id": "customer",
    "name": "Customer",
    "kind": "entity",
    "status": "active",
}

CONCEPTS_FOR_SEARCH = [
    {
        "id": "customer",
        "name": "Customer",
        "kind": "entity",
        "description": "A person or organization that purchases.",
    },
    {
        "id": "account",
        "name": "Account",
        "kind": "entity",
        "description": "An ongoing relationship with a customer.",
    },
    {
        "id": "mrr",
        "name": "Monthly Recurring Revenue",
        "kind": "metric",
        "description": "Monthly revenue from active subscriptions.",
    },
]

RELATIONSHIP = {
    "id": "customer-has-orders",
    "name": "Customer has Orders",
    "type": "relatedTo",
    "multiplicity": "1:n",
    "relates": [{"concept": "customer"}, {"concept": "order"}],
}


# Namespaces


@respx.mock
def test_semantics_namespaces_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(NS_URL).mock(return_value=httpx.Response(200, json=NAMESPACES))
    result = runner.invoke(app, ["semantics", "namespaces", "list"])
    assert result.exit_code == 0
    assert "main" in result.output
    assert "archive" in result.output


@respx.mock
def test_semantics_namespaces_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{NS_URL}/main").mock(return_value=httpx.Response(200, json=NAMESPACES[0]))
    result = runner.invoke(app, ["semantics", "namespaces", "get", "main", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["namespace"] == "main"


@respx.mock
def test_semantics_namespaces_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{NS_URL}/main").mock(return_value=httpx.Response(200))
    body_file = tmp_path / "ns.json"
    body_file.write_text(json.dumps({"name": "Main"}))
    result = runner.invoke(app, ["semantics", "namespaces", "put", "main", "--file", str(body_file)])
    assert result.exit_code == 0
    body = json.loads(respx.calls[0].request.content)
    assert body == {"name": "Main", "namespace": "main"}


def test_semantics_namespaces_put_rejects_mismatched_id(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    body_file = tmp_path / "ns.json"
    body_file.write_text(json.dumps({"namespace": "other", "name": "Other"}))
    result = runner.invoke(app, ["semantics", "namespaces", "put", "main", "--file", str(body_file)])
    assert result.exit_code != 0


@respx.mock
def test_semantics_namespaces_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{NS_URL}/main").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["semantics", "namespaces", "delete", "main"])
    assert result.exit_code == 0
    assert "deleted" in result.output


# Concepts


@respx.mock
def test_semantics_concepts_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{NS_URL}/main/concepts").mock(return_value=httpx.Response(200, json=[CONCEPT]))
    result = runner.invoke(app, ["semantics", "concepts", "list", "main"])
    assert result.exit_code == 0
    assert "customer" in result.output


@respx.mock
def test_semantics_concepts_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{NS_URL}/main/concepts/customer").mock(return_value=httpx.Response(200, json=CONCEPT))
    result = runner.invoke(app, ["semantics", "concepts", "get", "main", "customer"])
    assert result.exit_code == 0
    assert "customer" in result.output


@respx.mock
def test_semantics_concepts_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{NS_URL}/main/concepts/customer").mock(return_value=httpx.Response(200))
    body_file = tmp_path / "concept.json"
    body_file.write_text(json.dumps({"name": "Customer", "kind": "entity"}))
    result = runner.invoke(
        app,
        ["semantics", "concepts", "put", "main", "customer", "--file", str(body_file)],
    )
    assert result.exit_code == 0
    body = json.loads(respx.calls[0].request.content)
    assert body["id"] == "customer"
    assert body["name"] == "Customer"


@respx.mock
def test_semantics_concepts_put_hierarchical_id(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{NS_URL}/main/concepts/Security/Group").mock(return_value=httpx.Response(200))
    body_file = tmp_path / "concept.json"
    body_file.write_text(json.dumps({"kind": "group"}))
    result = runner.invoke(
        app,
        ["semantics", "concepts", "put", "main", "Security/Group", "--file", str(body_file)],
    )
    assert result.exit_code == 0


@respx.mock
def test_semantics_concepts_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{NS_URL}/main/concepts/customer").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["semantics", "concepts", "delete", "main", "customer"])
    assert result.exit_code == 0
    assert "deleted" in result.output


# Relationships


@respx.mock
def test_semantics_relationships_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{NS_URL}/main/relationships").mock(return_value=httpx.Response(200, json=[RELATIONSHIP]))
    result = runner.invoke(app, ["semantics", "relationships", "list", "main"])
    assert result.exit_code == 0
    assert "customer-has-orders" in result.output


@respx.mock
def test_semantics_relationships_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{NS_URL}/main/relationships/customer-has-orders").mock(return_value=httpx.Response(200))
    body_file = tmp_path / "rel.json"
    body_file.write_text(
        json.dumps(
            {
                "type": "relatedTo",
                "relates": [{"concept": "customer"}, {"concept": "order"}],
            }
        )
    )
    result = runner.invoke(
        app,
        [
            "semantics",
            "relationships",
            "put",
            "main",
            "customer-has-orders",
            "--file",
            str(body_file),
        ],
    )
    assert result.exit_code == 0
    body = json.loads(respx.calls[0].request.content)
    assert body["id"] == "customer-has-orders"


@respx.mock
def test_semantics_relationships_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{NS_URL}/main/relationships/customer-has-orders").mock(return_value=httpx.Response(200))
    result = runner.invoke(
        app,
        ["semantics", "relationships", "delete", "main", "customer-has-orders"],
    )
    assert result.exit_code == 0


# Search


@respx.mock
def test_semantics_search_substring(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{NS_URL}/main/concepts").mock(return_value=httpx.Response(200, json=CONCEPTS_FOR_SEARCH))
    result = runner.invoke(app, ["semantics", "search", "main", "customer", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    ids = {c["id"] for c in data}
    # 'customer' matches both the customer concept and the account description
    assert ids == {"customer", "account"}


@respx.mock
def test_semantics_search_kind_filter(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{NS_URL}/main/concepts").mock(return_value=httpx.Response(200, json=CONCEPTS_FOR_SEARCH))
    result = runner.invoke(
        app,
        ["semantics", "search", "main", "revenue", "--kind", "metric", "--output", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1
    assert data[0]["id"] == "mrr"


@respx.mock
def test_semantics_search_limit(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{NS_URL}/main/concepts").mock(return_value=httpx.Response(200, json=CONCEPTS_FOR_SEARCH))
    result = runner.invoke(
        app,
        ["semantics", "search", "main", "a", "--limit", "1", "--output", "json"],
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) == 1


def test_semantics_search_empty_query(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    result = runner.invoke(app, ["semantics", "search", "main", "   "])
    assert result.exit_code == 2


def test_semantics_help():
    result = runner.invoke(app, ["semantics", "--help"])
    assert result.exit_code == 0
    for group in ("namespaces", "concepts", "relationships"):
        assert group in result.output
