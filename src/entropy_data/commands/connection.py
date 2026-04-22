"""Connection management commands."""

from typing import Annotated

import typer
from rich.table import Table

from entropy_data import config as cfg
from entropy_data.output import console, print_error, print_success

connection_app = typer.Typer(no_args_is_help=True)


@connection_app.command("list")
def list_connections() -> None:
    """List all configured connections."""
    connections = cfg.list_connections()
    if not connections:
        console.print("No connections configured. Run: entropy-data connection add <name>")
        return

    table = Table(show_header=True)
    table.add_column("Name")
    table.add_column("Host")
    table.add_column("API Key")
    table.add_column("Default")
    for conn in connections:
        table.add_row(
            conn["name"],
            conn["host"],
            conn["api_key"],
            "*" if conn["default"] else "",
        )
    console.print(table)


@connection_app.command("add")
def add_connection(
    name: Annotated[str, typer.Argument(help="Connection name.")],
    api_key: Annotated[str, typer.Option("--api-key", prompt="API key", help="The API key.")] = None,
    host: Annotated[
        str, typer.Option("--host", prompt="Host", prompt_required=False, help="API host URL.")
    ] = cfg.DEFAULT_HOST,
) -> None:
    """Add or update a named connection."""
    try:
        cfg.add_connection(name, api_key, host)
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
