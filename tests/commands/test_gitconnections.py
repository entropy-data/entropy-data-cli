"""Tests for git connection subcommands on dataproducts and datacontracts."""

import json

import pytest
import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


CONNECTION_RESPONSE = {
    "gitConnectionId": "11111111-1111-1111-1111-111111111111",
    "gitConnectionType": "github",
    "repositoryUrl": "https://github.com/acme/contracts",
    "repositoryBranch": "main",
    "repositoryPath": "contracts/orders.yaml",
    "syncStatus": "UP_TO_DATE",
    "webLink": "https://github.com/acme/contracts/blob/main/contracts/orders.yaml",
    "lastHash": "abc123",
}


@pytest.fixture
def configured(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_get(configured, resource):
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/{resource}/orders/gitconnection",
        json=CONNECTION_RESPONSE,
        status=200,
    )
    result = runner.invoke(app, [resource, "gitconnection", "get", "orders"])
    assert result.exit_code == 0
    assert "github.com/acme/contracts" in result.output


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_put(configured, resource):
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/{resource}/orders/gitconnection",
        json=CONNECTION_RESPONSE,
        status=200,
    )
    result = runner.invoke(
        app,
        [
            resource,
            "gitconnection",
            "put",
            "orders",
            "--repository-url",
            "https://github.com/acme/contracts",
            "--repository-path",
            "contracts/orders.yaml",
            "--git-connection-type",
            "github",
        ],
    )
    assert result.exit_code == 0
    assert "saved" in result.output
    sent = json.loads(responses.calls[-1].request.body)
    assert sent["repositoryUrl"] == "https://github.com/acme/contracts"
    assert sent["repositoryPath"] == "contracts/orders.yaml"
    assert sent["gitConnectionType"] == "github"


def test_gitconnection_put_requires_credential_or_type(configured):
    result = runner.invoke(
        app,
        [
            "dataproducts",
            "gitconnection",
            "put",
            "orders",
            "--repository-url",
            "https://github.com/acme/contracts",
            "--repository-path",
            "contracts/orders.yaml",
        ],
    )
    assert result.exit_code != 0


def test_gitconnection_put_rejects_invalid_type(configured):
    result = runner.invoke(
        app,
        [
            "dataproducts",
            "gitconnection",
            "put",
            "orders",
            "--repository-url",
            "https://github.com/acme/contracts",
            "--repository-path",
            "contracts/orders.yaml",
            "--git-connection-type",
            "svn",
        ],
    )
    assert result.exit_code != 0


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_put_with_credential_external_id(configured, resource):
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/{resource}/orders/gitconnection",
        json=CONNECTION_RESPONSE,
        status=200,
    )
    result = runner.invoke(
        app,
        [
            resource,
            "gitconnection",
            "put",
            "orders",
            "--repository-url",
            "https://github.com/acme/contracts",
            "--repository-path",
            "contracts/orders.yaml",
            "--git-credential-external-id",
            "acme-ci",
        ],
    )
    assert result.exit_code == 0
    sent = json.loads(responses.calls[-1].request.body)
    assert sent["gitCredentialExternalId"] == "acme-ci"
    assert "gitConnectionType" not in sent


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_delete(configured, resource):
    responses.add(
        responses.DELETE,
        f"{BASE_URL}/api/{resource}/orders/gitconnection",
        status=200,
    )
    result = runner.invoke(app, [resource, "gitconnection", "delete", "orders"])
    assert result.exit_code == 0
    assert "deleted" in result.output


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_pull(configured, resource):
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/{resource}/orders/gitconnection/pull",
        json=CONNECTION_RESPONSE,
        status=200,
    )
    result = runner.invoke(app, [resource, "gitconnection", "pull", "orders"])
    assert result.exit_code == 0
    assert "pulled" in result.output


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_push(configured, resource):
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/{resource}/orders/gitconnection/push",
        json=CONNECTION_RESPONSE,
        status=200,
    )
    result = runner.invoke(
        app,
        [resource, "gitconnection", "push", "orders", "--commit-message", "update orders"],
    )
    assert result.exit_code == 0
    assert "pushed" in result.output
    sent = json.loads(responses.calls[-1].request.body)
    assert sent["commitMessage"] == "update orders"


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_push_no_body(configured, resource):
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/{resource}/orders/gitconnection/push",
        json=CONNECTION_RESPONSE,
        status=200,
    )
    result = runner.invoke(app, [resource, "gitconnection", "push", "orders"])
    assert result.exit_code == 0
    assert responses.calls[-1].request.body in (None, b"null", "null")


@pytest.mark.parametrize("resource", ["dataproducts", "datacontracts"])
@responses.activate
def test_gitconnection_push_pr(configured, resource):
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/{resource}/orders/gitconnection/push-pr",
        json=CONNECTION_RESPONSE,
        status=200,
    )
    result = runner.invoke(
        app,
        [
            resource,
            "gitconnection",
            "push-pr",
            "orders",
            "--branch-name",
            "feat/orders",
            "--title",
            "Update orders",
            "--commit-message",
            "update orders",
            "--comment",
            "ci push",
        ],
    )
    assert result.exit_code == 0
    sent = json.loads(responses.calls[-1].request.body)
    assert sent["branchName"] == "feat/orders"
    assert sent["title"] == "Update orders"
    assert sent["commitMessage"] == "update orders"
    assert sent["comment"] == "ci push"


def test_gitconnection_help_under_dataproducts():
    result = runner.invoke(app, ["dataproducts", "gitconnection", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "put" in result.output
    assert "delete" in result.output
    assert "pull" in result.output
    assert "push" in result.output
    assert "push-pr" in result.output


def test_gitconnection_help_under_datacontracts():
    result = runner.invoke(app, ["datacontracts", "gitconnection", "--help"])
    assert result.exit_code == 0
    assert "get" in result.output
    assert "push-pr" in result.output
