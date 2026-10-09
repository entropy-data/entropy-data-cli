"""Tests for the top-level CLI app and its global options."""

import os
import re

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
