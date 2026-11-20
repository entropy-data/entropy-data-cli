"""Shared test fixtures."""

import pytest

from entropy_data import config as cfg


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Ensure no env vars leak between tests."""
    for key in ["ENTROPY_DATA_API_KEY", "ENTROPY_DATA_HOST", "ENTROPY_DATA_SSL_VERIFY", "ENTROPY_DATA_TRUST_ENV"]:
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


# Requests the suite sends that are not in tests/openapi.yaml as sent, with why that is fine.
# (method, path template or literal path, query parameter or None for the operation itself)
UNDOCUMENTED_REQUESTS: dict[tuple[str, str, str | None], str] = {}


@pytest.fixture(autouse=True)
def requests_match_openapi(monkeypatch):
    """Fail a test whose CLI command sends a request the OpenAPI spec does not document.

    Every request a command sends in the tests (mocked by respx) must be an operation in
    tests/openapi.yaml, with query parameters the operation documents. So when the API renames
    or drops an endpoint or parameter, refreshing the spec (./update-openapi) fails the tests of
    the commands that still use it, instead of the CLI silently sending what the server ignores.
    """
    import httpx

    from tests import openapi_spec

    sent: list[httpx.Request] = []
    original_send = httpx.Client.send

    def recording_send(self, request, *args, **kwargs):
        sent.append(request)
        return original_send(self, request, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", recording_send)
    yield

    problems = openapi_spec.undocumented_requests(sent, UNDOCUMENTED_REQUESTS)
    assert not problems, "Requests that tests/openapi.yaml does not document:\n" + "\n".join(problems)
