"""Connection management commands."""

from typing import Annotated, Optional

import typer
from rich.table import Table

from entropy_data import config as cfg
from entropy_data.output import OutputFormat, console, error_console, print_data, print_error, print_success

connection_app = typer.Typer(no_args_is_help=True)


def _fetch_vanity_url(api_key: str, host: str) -> str | None:
    """Best-effort fetch of the org vanity URL via /api/organization/settings.

    Returns None on any failure (older server, network error, etc.) so callers
    can fall back to None instead of failing the whole `connection add`.
    """
    from entropy_data.client import EntropyDataClient

    try:
        client = EntropyDataClient(cfg.ConnectionConfig(api_key=api_key, host=host))
        response = client.session.get(
            f"{client.base_url}/api/organization/settings",
            timeout=client.timeout,
        )
        if response.ok:
            return response.json().get("vanityUrl")
    except Exception:
        return None
    return None


def _env_override_notice(overrides: dict[str, str], default_name: str | None) -> str:
    """Explain how ENTROPY_DATA_* variables change which credentials commands use."""
    api_key = overrides.get("ENTROPY_DATA_API_KEY")
    host = overrides.get("ENTROPY_DATA_HOST")
    if api_key is not None:
        target = f"the default connection '{default_name}'" if default_name else "any stored connection"
        notice = f"ENTROPY_DATA_API_KEY is set ({api_key}): commands use it instead of {target}"
        if host is not None:
            notice += f", with ENTROPY_DATA_HOST ({host})"
        elif default_name:
            notice += " (the host still comes from the default connection)"
    else:
        notice = (
            f"ENTROPY_DATA_HOST is set ({host}): commands send the default connection's API key "
            "to this host instead of its stored host"
        )
    return notice + ". Pass --connection <name> to use a stored connection."


@connection_app.command("list")
def list_connections(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all configured connections, and any ENTROPY_DATA_* environment variables overriding them."""
    from entropy_data.cli import get_output_format

    connections = cfg.list_connections()
    overrides = cfg.env_overrides()
    default_name = next((conn["name"] for conn in connections if conn["default"]), None)
    for conn in connections:
        if conn["default"] and overrides:
            conn["overridden_by"] = list(overrides)

    if overrides:
        error_console.print(
            f"[yellow]{_env_override_notice(overrides, default_name)}[/yellow]", highlight=False, soft_wrap=True
        )

    fmt = output or get_output_format()
    if fmt != OutputFormat.table:
        print_data(connections, fmt)
        return

    if not connections:
        console.print("No connections configured. Run: entropy-data connection add <name>")
        return

    table = Table(show_header=True)
    table.add_column("Name")
    table.add_column("Host")
    table.add_column("Vanity URL")
    table.add_column("API Key")
    table.add_column("Default")
    for conn in connections:
        default_marker = ""
        if conn["default"]:
            default_marker = "* (env)" if overrides else "*"
        table.add_row(
            conn["name"],
            conn["host"],
            conn.get("vanity_url") or "",
            conn["api_key"],
            default_marker,
        )
    console.print(table)


@connection_app.command("get")
def get_connection(
    name: Annotated[
        Optional[str],
        typer.Argument(help="Connection name. Defaults to the default connection."),
    ] = None,
    show_api_key: Annotated[
        bool,
        typer.Option("--show-api-key", help="Print the API key in clear text (default: masked)."),
    ] = False,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get details of a named connection (use --show-api-key to reveal the key)."""
    from entropy_data.cli import get_output_format

    config = cfg.load_config()
    connections = config.get("connections", {})

    resolved_name = name or config.get("default_connection_name")
    if resolved_name is None:
        print_error("No connection specified and no default set. Run: entropy-data connection set-default <name>")
        raise typer.Exit(1)
    if resolved_name not in connections:
        print_error(f"Connection '{resolved_name}' not found.")
        raise typer.Exit(1)

    conn = connections[resolved_name]
    api_key_value = conn.get("api_key", "")
    displayed_key = api_key_value if show_api_key else cfg.mask_api_key(api_key_value)
    is_default = config.get("default_connection_name") == resolved_name

    fmt = output or get_output_format()
    if fmt != OutputFormat.table:
        # JSON/YAML are machine-consumed (scripts, automation). Masking here
        # only breaks tooling and adds no security — the key already lives in
        # plaintext in ~/.entropy-data/config.toml. Emit the real value; the
        # mask / --show-api-key flag governs the human `table` view only.
        payload = {
            "name": resolved_name,
            "host": conn.get("host", cfg.DEFAULT_HOST),
            "vanity_url": conn.get("vanity_url"),
            "api_key": api_key_value,
            "default": is_default,
        }
        print_data(payload, fmt)
        return

    table = Table(show_header=False)
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("name", resolved_name)
    table.add_row("host", conn.get("host", cfg.DEFAULT_HOST))
    if conn.get("vanity_url"):
        table.add_row("vanity_url", conn["vanity_url"])
    table.add_row("api_key", displayed_key)
    if is_default:
        table.add_row("default", "yes")
    console.print(table)


@connection_app.command("add")
def add_connection(
    name: Annotated[str, typer.Argument(help="Connection name.")],
    api_key: Annotated[Optional[str], typer.Option("--api-key", help="The API key.")] = None,
    host: Annotated[
        Optional[str], typer.Option("--host", help=f"API host URL. Defaults to {cfg.DEFAULT_HOST}.")
    ] = None,
) -> None:
    """Add or update a named connection.

    The organization vanity URL is read from /api/organization/settings using the
    provided API key. Fetching is best-effort: older servers or network errors
    fall back to no vanity URL on the stored connection.
    """
    if api_key is None:
        # No API key on the command line: the call is interactive anyway, so also
        # confirm the host explicitly instead of silently storing the cloud default.
        api_key = typer.prompt("API key")
        if host is None:
            host = typer.prompt("Host", default=cfg.DEFAULT_HOST)
    if host is None:
        host = cfg.DEFAULT_HOST
    try:
        vanity_url = _fetch_vanity_url(api_key, host)
        if vanity_url:
            console.print(f"Fetched organization vanity URL '[cyan]{vanity_url}[/cyan]' from {host}.")
        cfg.add_connection(name, api_key, host, vanity_url=vanity_url)
        print_success(f"Connection '{name}' saved.")
    except cfg.ConfigurationError as e:
        print_error(str(e))
        raise typer.Exit(1)


@connection_app.command("remove")
def remove_connection(
    name: Annotated[str, typer.Argument(help="Connection name to remove.")],
) -> None:
    """Remove a named connection."""
    try:
        cfg.remove_connection(name)
        print_success(f"Connection '{name}' removed.")
    except cfg.ConfigurationError as e:
        print_error(str(e))
        raise typer.Exit(1)


@connection_app.command("set-default")
def set_default(
    name: Annotated[str, typer.Argument(help="Connection name to set as default.")],
) -> None:
    """Set the default connection."""
    try:
        cfg.set_default_connection(name)
        print_success(f"Default connection set to '{name}'.")
    except cfg.ConfigurationError as e:
        print_error(str(e))
        raise typer.Exit(1)


@connection_app.command("test")
def test_connection() -> None:
    """Test the current connection by calling the API."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.list_resources("teams", params={"p": "0"})
        print_success("Connection successful.")
    except Exception as e:
        handle_error(e)
