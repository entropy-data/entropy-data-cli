"""Tests for config module."""

import pytest

from entropy_data.config import (
    DEFAULT_HOST,
    ConfigurationError,
    add_connection,
    list_connections,
    load_config,
    remove_connection,
    resolve_connection,
    save_config,
    set_default_connection,
)


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    """Use a temp directory for config."""
    import entropy_data.config as cfg

    monkeypatch.setattr(cfg, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    return tmp_path


def test_load_config_missing(config_dir):
    assert load_config() == {}


def test_save_and_load(config_dir):
    data = {"default_connection_name": "test", "connections": {"test": {"api_key": "abc", "host": DEFAULT_HOST}}}
    save_config(data)
    loaded = load_config()
    assert loaded == data


def test_add_connection_sets_default(config_dir):
    add_connection("prod", "key123", DEFAULT_HOST)
    config = load_config()
    assert config["default_connection_name"] == "prod"
    assert config["connections"]["prod"]["api_key"] == "key123"


def test_add_second_connection_keeps_default(config_dir):
    add_connection("prod", "key1")
    add_connection("dev", "key2", "http://localhost:8080")
    config = load_config()
    assert config["default_connection_name"] == "prod"
    assert len(config["connections"]) == 2


def test_remove_connection(config_dir):
    add_connection("prod", "key1")
    add_connection("dev", "key2")
    remove_connection("dev")
    config = load_config()
    assert "dev" not in config["connections"]
    assert config["default_connection_name"] == "prod"


def test_remove_default_connection_reassigns(config_dir):
    add_connection("prod", "key1")
    add_connection("dev", "key2")
    remove_connection("prod")
    config = load_config()
    assert config["default_connection_name"] == "dev"


def test_remove_nonexistent_raises(config_dir):
    with pytest.raises(ConfigurationError, match="not found"):
        remove_connection("nope")


def test_set_default(config_dir):
    add_connection("prod", "key1")
    add_connection("dev", "key2")
    set_default_connection("dev")
    config = load_config()
    assert config["default_connection_name"] == "dev"


def test_set_default_nonexistent_raises(config_dir):
    with pytest.raises(ConfigurationError, match="not found"):
        set_default_connection("nope")


def test_list_connections_empty(config_dir):
    assert list_connections() == []


def test_list_connections_masked_keys(config_dir):
    add_connection("prod", "abcd1234efgh5678")
    result = list_connections()
    assert len(result) == 1
    assert result[0]["name"] == "prod"
    assert result[0]["api_key"] == "abcd...5678"
    assert result[0]["default"] is True


def test_resolve_from_config(config_dir):
    add_connection("prod", "mykey", "https://custom.host")
    conn = resolve_connection()
    assert conn.api_key == "mykey"
    assert conn.host == "https://custom.host"


def test_resolve_env_overrides_config(config_dir, monkeypatch):
    add_connection("prod", "config_key")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "env_key")
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://env.host")
    conn = resolve_connection()
    assert conn.api_key == "env_key"
    assert conn.host == "https://env.host"


def test_resolve_cli_overrides_env(config_dir, monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "env_key")
    conn = resolve_connection(cli_api_key="cli_key", cli_host="https://cli.host")
    assert conn.api_key == "cli_key"
    assert conn.host == "https://cli.host"


def test_resolve_named_connection(config_dir):
    add_connection("prod", "prod_key")
    add_connection("dev", "dev_key", "http://localhost:8080")
    conn = resolve_connection(connection_name="dev")
    assert conn.api_key == "dev_key"
    assert conn.host == "http://localhost:8080"


def test_resolve_no_key_raises(config_dir):
    with pytest.raises(ConfigurationError, match="No API key"):
        resolve_connection()


def test_resolve_default_host(config_dir, monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "mykey")
    conn = resolve_connection()
    assert conn.host == DEFAULT_HOST


def test_resolve_from_dotenv(config_dir, tmp_path, monkeypatch):
    """A .env file in the working directory should populate env vars."""
    from dotenv import load_dotenv

    dotenv_dir = tmp_path / "dotenv_test"
    dotenv_dir.mkdir()
    env_file = dotenv_dir / ".env"
    env_file.write_text("ENTROPY_DATA_API_KEY=dotenv_key\nENTROPY_DATA_HOST=https://dotenv.host\n")
    load_dotenv(env_file)
    conn = resolve_connection()
    assert conn.api_key == "dotenv_key"
    assert conn.host == "https://dotenv.host"


def test_env_var_overrides_dotenv(config_dir, tmp_path, monkeypatch):
    """Explicit env vars should take precedence over .env file values."""
    from dotenv import load_dotenv

    dotenv_dir = tmp_path / "dotenv_test"
    dotenv_dir.mkdir()
    env_file = dotenv_dir / ".env"
    env_file.write_text("ENTROPY_DATA_API_KEY=dotenv_key\n")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "real_env_key")
    load_dotenv(env_file, override=False)
    conn = resolve_connection()
    assert conn.api_key == "real_env_key"
