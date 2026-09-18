"""Tests for the global --timeout option."""

import pytest
import requests
import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
BRANCH = f"{BASE_URL}/api/semantics/experimental/namespaces/sales/branches/add-credit-limit"


@pytest.fixture(autouse=True)
def api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    monkeypatch.delenv("ENTROPY_DATA_TIMEOUT", raising=False)


@pytest.fixture
def timeouts(monkeypatch):
    seen = []
    send = requests.Session.send

    def recording_send(self, request, **kwargs):
        seen.append(kwargs.get("timeout"))
        return send(self, request, **kwargs)

    monkeypatch.setattr(requests.Session, "send", recording_send)
    return seen


@pytest.fixture
def document(tmp_path):
    path = tmp_path / "sales.yaml"
    path.write_text("ontology: []\n")
    return str(path)


@responses.activate
def test_requests_wait_30_seconds_by_default(timeouts, document):
    responses.add(responses.PUT, f"{BRANCH}/ontology.yaml", status=200)
    result = runner.invoke(app, ["semantics", "branches", "put", "sales", "add-credit-limit", "-f", document])
    assert result.exit_code == 0
    assert timeouts == [30]


@responses.activate
def test_timeout_option_and_env_var(timeouts, document, monkeypatch):
    responses.add(responses.PUT, f"{BRANCH}/ontology.yaml", status=200)
    responses.add(responses.POST, f"{BRANCH}/merge", status=204)

    result = runner.invoke(
        app, ["--timeout", "300", "semantics", "branches", "put", "sales", "add-credit-limit", "-f", document]
    )
    assert result.exit_code == 0
    monkeypatch.setenv("ENTROPY_DATA_TIMEOUT", "600")
    result = runner.invoke(app, ["semantics", "branches", "merge", "sales", "add-credit-limit"])
    assert result.exit_code == 0

    assert timeouts == [300, 600]


@responses.activate
def test_timeout_overrides_a_commands_own_longer_wait(timeouts):
    responses.add(responses.POST, f"{BASE_URL}/api/datacontracts/orders/test", json={"result": "passed"}, status=200)

    assert runner.invoke(app, ["datacontracts", "test", "orders"]).exit_code == 0
    assert runner.invoke(app, ["--timeout", "60", "datacontracts", "test", "orders"]).exit_code == 0

    assert timeouts == [1800, 60]


def test_timeout_must_be_positive():
    result = runner.invoke(app, ["--timeout", "0", "teams", "list"])
    assert result.exit_code != 0
