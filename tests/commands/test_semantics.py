"""Tests for semantics commands."""

import json

import responses
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

RELATIONSHIP = {
    "id": "customer-has-orders",
    "name": "Customer has Orders",
    "type": "relatedTo",
    "multiplicity": "1:n",
    "relates": [{"concept": "customer"}, {"concept": "order"}],
}


# Namespaces


@responses.activate
def test_semantics_namespaces_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, NS_URL, json=NAMESPACES, status=200)
    result = runner.invoke(app, ["semantics", "namespaces", "list"])
    assert result.exit_code == 0
    assert "main" in result.output
    assert "archive" in result.output


@responses.activate
def test_semantics_namespaces_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{NS_URL}/main", json=NAMESPACES[0], status=200)
    result = runner.invoke(app, ["semantics", "namespaces", "get", "main", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["namespace"] == "main"


@responses.activate
def test_semantics_namespaces_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{NS_URL}/main", status=200)
    body_file = tmp_path / "ns.json"
    body_file.write_text(json.dumps({"name": "Main"}))
    result = runner.invoke(app, ["semantics", "namespaces", "put", "main", "--file", str(body_file)])
    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body == {"name": "Main", "namespace": "main"}


def test_semantics_namespaces_put_rejects_mismatched_id(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    body_file = tmp_path / "ns.json"
    body_file.write_text(json.dumps({"namespace": "other", "name": "Other"}))
    result = runner.invoke(app, ["semantics", "namespaces", "put", "main", "--file", str(body_file)])
    assert result.exit_code != 0


@responses.activate
def test_semantics_namespaces_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{NS_URL}/main", status=200)
    result = runner.invoke(app, ["semantics", "namespaces", "delete", "main"])
    assert result.exit_code == 0
    assert "deleted" in result.output


# Concepts


@responses.activate
def test_semantics_concepts_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{NS_URL}/main/concepts", json=[CONCEPT], status=200)
    result = runner.invoke(app, ["semantics", "concepts", "list", "main"])
    assert result.exit_code == 0
    assert "customer" in result.output


@responses.activate
def test_semantics_concepts_get(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{NS_URL}/main/concepts/customer", json=CONCEPT, status=200)
    result = runner.invoke(app, ["semantics", "concepts", "get", "main", "customer"])
    assert result.exit_code == 0
    assert "customer" in result.output


@responses.activate
def test_semantics_concepts_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{NS_URL}/main/concepts/customer", status=200)
    body_file = tmp_path / "concept.json"
    body_file.write_text(json.dumps({"name": "Customer", "kind": "entity"}))
    result = runner.invoke(
        app,
        ["semantics", "concepts", "put", "main", "customer", "--file", str(body_file)],
    )
    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body["id"] == "customer"
    assert body["name"] == "Customer"


@responses.activate
def test_semantics_concepts_put_hierarchical_id(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.PUT, f"{NS_URL}/main/concepts/Security/Group", status=200)
    body_file = tmp_path / "concept.json"
    body_file.write_text(json.dumps({"kind": "group"}))
    result = runner.invoke(
        app,
        ["semantics", "concepts", "put", "main", "Security/Group", "--file", str(body_file)],
    )
    assert result.exit_code == 0


@responses.activate
def test_semantics_concepts_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.DELETE, f"{NS_URL}/main/concepts/customer", status=200)
    result = runner.invoke(app, ["semantics", "concepts", "delete", "main", "customer"])
    assert result.exit_code == 0
    assert "deleted" in result.output


# Relationships


@responses.activate
def test_semantics_relationships_list(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(responses.GET, f"{NS_URL}/main/relationships", json=[RELATIONSHIP], status=200)
    result = runner.invoke(app, ["semantics", "relationships", "list", "main"])
    assert result.exit_code == 0
    assert "customer-has-orders" in result.output


@responses.activate
def test_semantics_relationships_put(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.PUT,
        f"{NS_URL}/main/relationships/customer-has-orders",
        status=200,
    )
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
    body = json.loads(responses.calls[0].request.body)
    assert body["id"] == "customer-has-orders"


@responses.activate
def test_semantics_relationships_delete(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.DELETE,
        f"{NS_URL}/main/relationships/customer-has-orders",
        status=200,
    )
    result = runner.invoke(
        app,
        ["semantics", "relationships", "delete", "main", "customer-has-orders"],
    )
    assert result.exit_code == 0
    assert "deleted" in result.output


def test_semantics_help():
    result = runner.invoke(app, ["semantics", "--help"])
    assert result.exit_code == 0
    for group in ("namespaces", "concepts", "relationships"):
        assert group in result.output
