"""Tests for the global --timeout option."""

import httpx
import pytest
import respx
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
    """The read timeout of every request sent, as httpx carries it to the transport."""
    seen = []
    send = httpx.Client.send

    def recording_send(self, request, **kwargs):
        seen.append(request.extensions["timeout"]["read"])
        return send(self, request, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", recording_send)
    return seen


@pytest.fixture
def document(tmp_path):
    path = tmp_path / "sales.yaml"
    path.write_text("ontology: []\n")
    return str(path)


@respx.mock
def test_requests_wait_30_seconds_by_default(timeouts, document):
    respx.put(f"{BRANCH}/ontology.yaml").mock(return_value=httpx.Response(200))
    result = runner.invoke(app, ["semantics", "branches", "put", "sales", "add-credit-limit", "-f", document])
    assert result.exit_code == 0
    assert timeouts == [30]


@respx.mock
def test_timeout_option_and_env_var(timeouts, document, monkeypatch):
    respx.put(f"{BRANCH}/ontology.yaml").mock(return_value=httpx.Response(200))
    respx.post(f"{BRANCH}/merge").mock(return_value=httpx.Response(204))

    result = runner.invoke(
        app, ["--timeout", "300", "semantics", "branches", "put", "sales", "add-credit-limit", "-f", document]
    )
    assert result.exit_code == 0
    monkeypatch.setenv("ENTROPY_DATA_TIMEOUT", "600")
    result = runner.invoke(app, ["semantics", "branches", "merge", "sales", "add-credit-limit"])
    assert result.exit_code == 0

    assert timeouts == [300, 600]


@respx.mock
def test_timeout_overrides_a_commands_own_longer_wait(timeouts):
    respx.post(f"{BASE_URL}/api/datacontracts/orders/test").mock(
        return_value=httpx.Response(200, json={"result": "passed"})
    )

    assert runner.invoke(app, ["datacontracts", "test", "orders"]).exit_code == 0
    assert runner.invoke(app, ["--timeout", "60", "datacontracts", "test", "orders"]).exit_code == 0

    assert timeouts == [1800, 60]


def test_timeout_must_be_positive():
    result = runner.invoke(app, ["--timeout", "0", "teams", "list"])
    assert result.exit_code != 0
