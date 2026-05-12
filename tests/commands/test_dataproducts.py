"""Tests for dataproducts commands."""

import json

import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


@responses.activate
def test_dataproducts_import_from_git_flags(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/dataproducts/import/git",
        json={"gitConnectionId": "abc"},
        status=201,
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
    body = json.loads(responses.calls[0].request.body)
    assert body == {
        "repositoryUrl": "https://github.com/x/y",
        "repositoryPath": "products/orders.yaml",
        "gitConnectionType": "github",
        "repositoryBranch": "develop",
    }


@responses.activate
def test_dataproducts_import_from_git_file(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/dataproducts/import/git",
        json={"gitConnectionId": "abc"},
        status=201,
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


def test_dataproducts_help():
    result = runner.invoke(app, ["dataproducts", "--help"])
    assert result.exit_code == 0
    assert "import-from-git" in result.output
    assert "gitconnection" in result.output
