"""Tests for the top-level CLI app and its global options."""

import json
import os
import re

import httpx
import pytest
import respx
import yaml
from typer.testing import CliRunner

from entropy_data.cli import app

runner = CliRunner()


def test_system_truststore_option_in_help():
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    plain_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "--system-truststore" in plain_output


def test_system_truststore_flag_injects(monkeypatch):
    calls = []
    monkeypatch.setattr("entropy_data.cli.inject_system_truststore", lambda: calls.append(True))
    result = runner.invoke(app, ["--system-truststore", "teams", "list"])
    # The command fails without a configured connection, but the app callback has run.
    assert result.exit_code != 0
    assert calls == [True]


def test_system_truststore_env_var_injects(monkeypatch):
    calls = []
    monkeypatch.setattr("entropy_data.cli.inject_system_truststore", lambda: calls.append(True))
    monkeypatch.setenv("ENTROPY_DATA_SYSTEM_TRUSTSTORE", "1")
    result = runner.invoke(app, ["teams", "list"])
    assert result.exit_code != 0
    assert calls == [True]


def test_system_truststore_not_injected_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr("entropy_data.cli.inject_system_truststore", lambda: calls.append(True))
    monkeypatch.delenv("ENTROPY_DATA_SYSTEM_TRUSTSTORE", raising=False)
    result = runner.invoke(app, ["teams", "list"])
    assert result.exit_code != 0
    assert calls == []


def test_dotenv_in_working_directory_is_loaded(monkeypatch, tmp_path):
    # Without usecwd, python-dotenv searches upward from the installed package,
    # so a project's .env next to where the user runs the CLI was never found.
    (tmp_path / ".env").write_text("ENTROPY_DATA_API_KEY=dotenv_key\nENTROPY_DATA_HOST=https://dotenv.host\n")
    monkeypatch.chdir(tmp_path)
    # Register both keys with monkeypatch so the values load_dotenv sets are removed again.
    for key in ["ENTROPY_DATA_API_KEY", "ENTROPY_DATA_HOST"]:
        monkeypatch.setenv(key, "")
        monkeypatch.delenv(key)

    result = runner.invoke(app, ["connection", "list"])

    assert result.exit_code == 0
    assert os.environ.get("ENTROPY_DATA_API_KEY") == "dotenv_key"
    assert os.environ.get("ENTROPY_DATA_HOST") == "https://dotenv.host"


def test_errors_go_to_stderr_as_plain_text_in_table_mode():
    result = runner.invoke(app, ["teams", "list"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "Configuration error: No API key found." in result.stderr


@pytest.mark.parametrize("fmt, load", [("json", json.loads), ("yaml", yaml.safe_load)])
def test_configuration_errors_are_structured_on_stderr_in_machine_formats(fmt, load):
    result = runner.invoke(app, ["-o", fmt, "teams", "list"])
    assert result.exit_code == 2
    assert result.stdout == ""
    error = load(result.stderr)["error"]
    assert error["type"] == "configuration_error"
    assert error["message"].startswith("No API key found.")


@respx.mock
def test_api_errors_are_json_on_stderr_with_status_and_url():
    url = "https://api.entropy-data.com/api/teams/missing"
    respx.get(url).mock(return_value=httpx.Response(404, json={"detail": "Team not found"}))
    result = runner.invoke(app, ["-o", "json", "--api-key", "key", "teams", "get", "missing"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert json.loads(result.stderr) == {
        "error": {
            "type": "api_error",
            "message": f"HTTP 404 from {url}: Team not found",
            "status": 404,
            "url": url,
        }
    }


TEAMS_URL = "https://api.entropy-data.com/api/teams"
PROXY_VARIABLES = ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"]


@pytest.fixture
def proxy_env(monkeypatch):
    for name in PROXY_VARIABLES:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    # Without any proxy variable, urllib falls back to the operating system's proxy settings.
    monkeypatch.setenv("NO_PROXY", "unrelated.example.test")
    return monkeypatch.setenv


def _teams_list_error(*options):
    result = runner.invoke(app, ["-o", "json", "--api-key", "key", *options, "teams", "list"])
    assert result.exit_code == 1
    assert result.stdout == ""
    return json.loads(result.stderr)["error"]


@respx.mock
def test_connection_errors_name_the_host(proxy_env):
    respx.get(TEAMS_URL).mock(side_effect=httpx.ConnectError("[Errno 61] Connection refused"))

    assert _teams_list_error() == {
        "type": "connection_error",
        "message": "Could not connect to https://api.entropy-data.com: [Errno 61] Connection refused",
        "url": "https://api.entropy-data.com/api/teams?p=0",
    }


@respx.mock
def test_connection_errors_name_the_configured_proxy_without_its_credentials(proxy_env):
    proxy_env("HTTPS_PROXY", "http://user:secret@proxy.example.test:8080")
    respx.get(TEAMS_URL).mock(side_effect=httpx.ConnectError("[Errno 61] Connection refused"))

    error = _teams_list_error()

    assert error["type"] == "connection_error"
    assert error["proxy"] == "http://proxy.example.test:8080"
    assert error["message"] == (
        "Could not connect to https://api.entropy-data.com: [Errno 61] Connection refused. "
        "A proxy is configured for this host (http://proxy.example.test:8080): "
        "check that it is reachable, or list the host in NO_PROXY to connect directly."
    )
    assert "secret" not in json.dumps(error)


@respx.mock
def test_connection_errors_do_not_mention_a_proxy_the_host_bypasses(proxy_env):
    proxy_env("HTTPS_PROXY", "http://proxy.example.test:8080")
    proxy_env("NO_PROXY", "api.entropy-data.com")
    respx.get(TEAMS_URL).mock(side_effect=httpx.ConnectError("[Errno 61] Connection refused"))

    error = _teams_list_error()

    assert "proxy" not in error
    assert "proxy" not in error["message"]


@respx.mock
def test_connection_errors_are_plain_text_in_table_mode(proxy_env):
    respx.get(TEAMS_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))

    result = runner.invoke(app, ["--api-key", "key", "teams", "list"])

    assert result.exit_code == 1
    assert "Connection error: Could not connect to https://api.entropy-data.com: timed out" in result.stderr


@respx.mock
def test_a_proxy_asking_for_credentials_is_reported_as_a_proxy_error(proxy_env):
    proxy_env("HTTPS_PROXY", "http://proxy.example.test:8080")
    respx.get(TEAMS_URL).mock(return_value=httpx.Response(407))

    error = _teams_list_error()

    assert error["type"] == "proxy_error"
    assert error["status"] == 407
    assert error["proxy"] == "http://proxy.example.test:8080"
    assert error["message"] == (
        "The proxy http://proxy.example.test:8080 requires authentication (HTTP 407). "
        "Put the credentials into the proxy URL, for example http://user:password@proxy.example.com:8080."
    )


@respx.mock
def test_a_failing_proxy_tunnel_is_reported_as_a_proxy_error(proxy_env):
    proxy_env("HTTPS_PROXY", "http://proxy.example.test:8080")
    respx.get(TEAMS_URL).mock(side_effect=httpx.ProxyError("403 Forbidden"))

    error = _teams_list_error()

    assert error["type"] == "proxy_error"
    assert error["proxy"] == "http://proxy.example.test:8080"
    assert error["message"] == "The proxy http://proxy.example.test:8080 refused the connection: 403 Forbidden"
