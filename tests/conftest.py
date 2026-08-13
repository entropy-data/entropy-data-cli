"""Shared test fixtures."""

import pytest

from entropy_data import config as cfg


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure no env vars leak between tests."""
    for key in ["ENTROPY_DATA_API_KEY", "ENTROPY_DATA_HOST", "ENTROPY_DATA_SSL_VERIFY"]:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, tmp_path):
    """Keep the developer's own ~/.entropy-data/config.toml out of the tests.

    Without this a test that reaches resolve_connection() finds a real,
    credentialed connection on a configured machine and calls the live API,
    while CI — where no config file exists — sees the failure the test expects.
    Tests that need a config of their own still point these at their own
    tmp_path; this only decides what a test that sets up nothing sees.
    """
    config_dir = tmp_path / "config-home"
    config_dir.mkdir()
    monkeypatch.setattr(cfg, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cfg, "CONFIG_FILE", config_dir / "config.toml")
