"""Shared test fixtures."""

import pytest


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure no env vars leak between tests."""
    for key in ["ENTROPY_DATA_API_KEY", "ENTROPY_DATA_HOST", "ENTROPY_DATA_SSL_VERIFY"]:
        monkeypatch.delenv(key, raising=False)
