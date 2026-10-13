"""Tests for dataproducts commands."""

import json

import httpx
import respx
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


@respx.mock
def test_dataproducts_import_from_git_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.post(f"{BASE_URL}/api/dataproducts/import/git").mock(
        return_value=httpx.Response(201, json={"gitConnectionId": "abc"})
    )
    result = runner.invoke(
        app,
        [
            "dataproducts",
            "import-from-git",
            "--repository-url",
            "https://github.com/x/y",
            "--repository-path",
            "products/orders.yaml",
            "--git-connection-type",
            "github",
            "--repository-branch",
            "develop",
        ],
    )
    assert result.exit_code == 0
    body = json.loads(respx.calls[0].request.content)
    assert body == {
        "repositoryUrl": "https://github.com/x/y",
        "repositoryPath": "products/orders.yaml",
        "gitConnectionType": "github",
        "repositoryBranch": "develop",
    }


@respx.mock
def test_dataproducts_import_from_git_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.post(f"{BASE_URL}/api/dataproducts/import/git").mock(
        return_value=httpx.Response(201, json={"gitConnectionId": "abc"})
    )
    body_file = tmp_path / "import.json"
    body_file.write_text(
        json.dumps(
            {
                "repositoryUrl": "https://github.com/x/y",
                "repositoryPath": "products/orders.yaml",
                "gitConnectionType": "github",
            }
        )
    )
    result = runner.invoke(app, ["dataproducts", "import-from-git", "--file", str(body_file)])
    assert result.exit_code == 0


@respx.mock
def test_dataproducts_star(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.put(f"{BASE_URL}/api/dataproducts/orders/star").mock(return_value=httpx.Response(204))
    result = runner.invoke(app, ["dataproducts", "star", "orders"])
    assert result.exit_code == 0
    assert "Starred" in result.output


@respx.mock
def test_dataproducts_unstar(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.delete(f"{BASE_URL}/api/dataproducts/orders/star").mock(return_value=httpx.Response(204))
    result = runner.invoke(app, ["dataproducts", "unstar", "orders"])
    assert result.exit_code == 0
    assert "Unstarred" in result.output


@respx.mock
def test_dataproducts_star_status(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/dataproducts/orders/star").mock(
        return_value=httpx.Response(200, json={"count": 7, "starredByMe": True})
    )
    result = runner.invoke(app, ["dataproducts", "star-status", "orders", "--output", "json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"count": 7, "starredByMe": True}


@respx.mock
def test_dataproducts_stargazers(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    respx.get(f"{BASE_URL}/api/dataproducts/orders/stargazers").mock(
        return_value=httpx.Response(
            200, json=[{"userId": "alice", "fullName": "Alice A"}, {"userId": "bob", "fullName": "Bob B"}]
        )
    )
    result = runner.invoke(app, ["dataproducts", "stargazers", "orders"])
    assert result.exit_code == 0
    assert "alice" in result.output
    assert "Bob B" in result.output


def test_dataproducts_help():
    result = runner.invoke(app, ["dataproducts", "--help"])
    assert result.exit_code == 0
    assert "import-from-git" in result.output
    assert "gitconnection" in result.output
    assert "star" in result.output
    assert "stargazers" in result.output
