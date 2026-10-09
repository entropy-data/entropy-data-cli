"""Connection configuration management for ~/.entropy-data/config.toml."""

import os
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path

import tomli_w

CONFIG_DIR = Path.home() / ".entropy-data"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DEFAULT_HOST = "https://api.entropy-data.com"


class ConfigurationError(Exception):
    """Missing or invalid configuration."""


@dataclass
class ConnectionConfig:
    api_key: str
    host: str = DEFAULT_HOST
    vanity_url: str | None = None


def load_config() -> dict:
    """Read ~/.entropy-data/config.toml, return empty dict if missing."""
    if not CONFIG_FILE.exists():
        return {}
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def save_config(config: dict) -> None:
    """Write config.toml with 0600 permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(config, f)
    CONFIG_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)


def resolve_connection(
    connection_name: str | None = None,
    cli_api_key: str | None = None,
    cli_host: str | None = None,
) -> ConnectionConfig:
    """Resolve connection with precedence: --api-key/--host > --connection > env vars > default config connection."""
    api_key = cli_api_key
    host = cli_host
    vanity_url: str | None = None

    # Layer 2: explicit --connection takes precedence over env vars
    if connection_name is not None:
        config = load_config()
        connections = config.get("connections", {})
        if connection_name not in connections:
            raise ConfigurationError(f"Connection '{connection_name}' not found.")
        conn = connections[connection_name]
        if api_key is None:
            api_key = conn.get("api_key")
        if host is None:
            host = conn.get("host")
        vanity_url = conn.get("vanity_url")

    # Layer 3: environment variables
    if api_key is None:
        api_key = os.getenv("ENTROPY_DATA_API_KEY")
    if host is None:
        host = os.getenv("ENTROPY_DATA_HOST")

    # Layer 4: default connection from config file
    if api_key is None or host is None:
        config = load_config()
        connections = config.get("connections", {})
        name = config.get("default_connection_name")
        if name and name in connections:
            conn = connections[name]
            if api_key is None:
                api_key = conn.get("api_key")
            if host is None:
                host = conn.get("host")
            if vanity_url is None:
                vanity_url = conn.get("vanity_url")

    # Default host
    if host is None:
        host = DEFAULT_HOST

    if api_key is None:
        raise ConfigurationError(
            "No API key found. Set ENTROPY_DATA_API_KEY, use --api-key, or run: entropy-data connection add <name>"
        )

    return ConnectionConfig(api_key=api_key, host=host, vanity_url=vanity_url)


def add_connection(name: str, api_key: str, host: str = DEFAULT_HOST, vanity_url: str | None = None) -> None:
    """Add or update a named connection."""
    if not name or not name.strip():
        raise ConfigurationError("Connection name must not be empty.")
    config = load_config()
    if "connections" not in config:
        config["connections"] = {}
    entry: dict = {"api_key": api_key, "host": host}
    if vanity_url:
        entry["vanity_url"] = vanity_url
    config["connections"][name] = entry
    config["default_connection_name"] = name
    save_config(config)


def remove_connection(name: str) -> None:
    """Remove a named connection."""
    config = load_config()
    connections = config.get("connections", {})
    if name not in connections:
        raise ConfigurationError(f"Connection '{name}' not found.")
    del connections[name]
    # Clear default if we removed it
    if config.get("default_connection_name") == name:
        if connections:
            config["default_connection_name"] = next(iter(connections))
        else:
            config.pop("default_connection_name", None)
    save_config(config)


def set_default_connection(name: str) -> None:
    """Set the default connection."""
    config = load_config()
    connections = config.get("connections", {})
    if name not in connections:
        raise ConfigurationError(f"Connection '{name}' not found.")
    config["default_connection_name"] = name
    save_config(config)


def mask_api_key(api_key: str) -> str:
    """Mask an API key for display (first/last 4 visible)."""
    if len(api_key) > 8:
        return api_key[:4] + "..." + api_key[-4:]
    return "****"


def env_overrides() -> dict[str, str]:
    """Connection settings set via ENTROPY_DATA_API_KEY / ENTROPY_DATA_HOST (or a .env file).

    These take precedence over the default connection (but not over --connection),
    see resolve_connection. Keys are the variable names, values are display-safe.
    """
    overrides = {}
    api_key = os.getenv("ENTROPY_DATA_API_KEY")
    if api_key is not None:
        overrides["ENTROPY_DATA_API_KEY"] = mask_api_key(api_key)
    host = os.getenv("ENTROPY_DATA_HOST")
    if host is not None:
        overrides["ENTROPY_DATA_HOST"] = host
    return overrides


def list_connections() -> list[dict]:
    """List all connections with masked API keys."""
    config = load_config()
    default_name = config.get("default_connection_name")
    connections = config.get("connections", {})
    result = []
    for name, conn in connections.items():
        result.append(
            {
                "name": name,
                "host": conn.get("host", DEFAULT_HOST),
                "vanity_url": conn.get("vanity_url"),
                "api_key": mask_api_key(conn.get("api_key", "")),
                "default": name == default_name,
            }
        )
    return result
