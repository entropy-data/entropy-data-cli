"""Tests for datacontracts commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


YAML_BODY = """apiVersion: v3.1.0
kind: DataContract
id: search-queries
name: Search Queries v2
version: 1.0.0
"""


@responses.activate
def test_datacontracts_yaml_stdout(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/datacontracts/search-queries.yaml",
        body=YAML_BODY,
        content_type="application/yaml",
        status=200,
    )
    result = runner.invoke(app, ["datacontracts", "yaml", "search-queries"])
    assert result.exit_code == 0
    assert "kind: DataContract" in result.output
    assert responses.calls[0].request.headers["Accept"] == "application/yaml"


@responses.activate
def test_datacontracts_yaml_to_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/datacontracts/search-queries.yaml",
        body=YAML_BODY,
        content_type="application/yaml",
        status=200,
    )
    out = tmp_path / "out.yaml"
    result = runner.invoke(app, ["datacontracts", "yaml", "search-queries", "--file", str(out)])
    assert result.exit_code == 0
    assert out.read_text() == YAML_BODY


@responses.activate
def test_datacontracts_generate_prints_json(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    payload = {
        "dataContractId": "orders",
        "generationType": "sql-select",
        "files": [{"filename": "orders.sql", "language": "sql", "content": "SELECT 1"}],
    }
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/datacontracts/orders/generate",
        json=payload,
        status=200,
    )
    result = runner.invoke(app, ["datacontracts", "generate", "orders", "--type", "sql-select"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["dataContractId"] == "orders"
    body = json.loads(responses.calls[0].request.body)
    assert body == {"type": "sql-select"}


@responses.activate
def test_datacontracts_generate_writes_files(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/datacontracts/orders/generate",
        json={
            "dataContractId": "orders",
            "generationType": "sql-ddl",
            "files": [
                {"filename": "orders.sql", "language": "sql", "content": "CREATE TABLE orders ();"},
                {"filename": "items.sql", "language": "sql", "content": "CREATE TABLE items ();"},
            ],
        },
        status=200,
    )
    out_dir = tmp_path / "gen"
    result = runner.invoke(
        app,
        ["datacontracts", "generate", "orders", "--type", "sql-ddl", "--out-dir", str(out_dir)],
    )
    assert result.exit_code == 0
    assert (out_dir / "orders.sql").read_text() == "CREATE TABLE orders ();"
    assert (out_dir / "items.sql").read_text() == "CREATE TABLE items ();"


def test_datacontracts_generate_custom_requires_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    result = runner.invoke(app, ["datacontracts", "generate", "orders", "--type", "custom"])
    assert result.exit_code != 0


def test_datacontracts_generate_rejects_bad_type(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    result = runner.invoke(app, ["datacontracts", "generate", "orders", "--type", "bogus"])
    assert result.exit_code != 0


@responses.activate
def test_datacontracts_import_from_git_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/datacontracts/import/git",
        json={"gitConnectionId": "abc"},
        status=201,
    )
    result = runner.invoke(
        app,
        [
            "datacontracts",
            "import-from-git",
            "--repository-url",
            "https://github.com/x/y",
            "--repository-path",
            "contracts/orders.yaml",
            "--git-connection-type",
            "github",
        ],
    )
    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "repositoryUrl": "https://github.com/x/y",
        "repositoryPath": "contracts/orders.yaml",
        "gitConnectionType": "github",
    }


@responses.activate
def test_datacontracts_import_from_git_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/datacontracts/import/git",
        json={"gitConnectionId": "abc"},
        status=201,
    )
    body_file = tmp_path / "import.json"
    body_file.write_text(
        json.dumps(
            {
                "repositoryUrl": "https://github.com/x/y",
                "repositoryPath": "contracts/orders.yaml",
                "gitCredentialExternalId": "ci-cred",
            }
        )
    )
    result = runner.invoke(app, ["datacontracts", "import-from-git", "--file", str(body_file)])
    assert result.exit_code == 0
    body = json.loads(responses.calls[0].request.body)
    assert body["gitCredentialExternalId"] == "ci-cred"


def test_datacontracts_import_from_git_missing_args(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    result = runner.invoke(app, ["datacontracts", "import-from-git"])
    assert result.exit_code != 0


def test_datacontracts_help():
    result = runner.invoke(app, ["datacontracts", "--help"])
    assert result.exit_code == 0
    assert "yaml" in result.output
    assert "generate" in result.output
    assert "import-from-git" in result.output
