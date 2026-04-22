"""Entropy Data CLI — main application entry point."""

import logging
import sys
from typing import Annotated, Optional

import typer
from dotenv import load_dotenv
from rich.console import Console

from entropy_data import __version__
from entropy_data.client import ApiError, EntropyDataClient
from entropy_data.config import ConfigurationError, resolve_connection
from entropy_data.output import OutputFormat

# Global state shared across commands
_connection_name: str | None = None
_cli_api_key: str | None = None
_cli_host: str | None = None
_output_format: OutputFormat = OutputFormat.table
_debug: bool = False

error_console = Console(stderr=True)


def get_client() -> EntropyDataClient:
    """Create an API client from the resolved connection config."""
    config = resolve_connection(
        connection_name=_connection_name,
        cli_api_key=_cli_api_key,
        cli_host=_cli_host,
    )
    return EntropyDataClient(config)


def get_output_format() -> OutputFormat:
    return _output_format


def handle_error(e: Exception) -> None:
    """Handle errors with appropriate output and exit codes."""
    if _debug:
        raise e
    if isinstance(e, ConfigurationError):
        error_console.print(f"[red]Configuration error: {e}[/red]")
        raise SystemExit(2)
    if isinstance(e, ApiError):
        error_console.print(f"[red]API error: {e}[/red]")
        raise SystemExit(1)
    error_console.print(f"[red]Error: {e}[/red]")
    raise SystemExit(1)


def version_callback(value: bool) -> None:
    if value:
        print(f"entropy-data {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="entropy-data",
    help="CLI for Entropy Data.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", help="Show version and exit.", callback=version_callback, is_eager=True),
    ] = None,
    connection: Annotated[Optional[str], typer.Option("--connection", "-c", help="Named connection to use.")] = None,
    api_key: Annotated[Optional[str], typer.Option("--api-key", help="API key (overrides config and env).")] = None,
    host: Annotated[Optional[str], typer.Option("--host", help="API host URL (overrides config and env).")] = None,
    output: Annotated[OutputFormat, typer.Option("--output", "-o", help="Output format.")] = OutputFormat.table,
    debug: Annotated[bool, typer.Option("--debug", help="Enable debug output.")] = False,
) -> None:
    """Entropy Data CLI — manage your data platform from the command line."""
    global _connection_name, _cli_api_key, _cli_host, _output_format, _debug
    load_dotenv()
    _connection_name = connection
    _cli_api_key = api_key
    _cli_host = host
    _output_format = output
    _debug = debug
    if debug:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)


# Register command groups
from entropy_data.commands.access import access_app  # noqa: E402
from entropy_data.commands.api_keys import api_keys_app  # noqa: E402
from entropy_data.commands.assets import assets_app  # noqa: E402
from entropy_data.commands.certifications import certifications_app  # noqa: E402
from entropy_data.commands.connection import connection_app  # noqa: E402
from entropy_data.commands.costs import costs_app  # noqa: E402
from entropy_data.commands.datacontracts import datacontracts_app  # noqa: E402
from entropy_data.commands.dataproducts import dataproducts_app  # noqa: E402
from entropy_data.commands.definitions import definitions_app  # noqa: E402
from entropy_data.commands.events import events_app  # noqa: E402
from entropy_data.commands.example_data import example_data_app  # noqa: E402
from entropy_data.commands.import_export import import_app  # noqa: E402
from entropy_data.commands.lineage import lineage_app  # noqa: E402
from entropy_data.commands.search import search_app  # noqa: E402
from entropy_data.commands.settings import settings_app  # noqa: E402
from entropy_data.commands.sourcesystems import sourcesystems_app  # noqa: E402
from entropy_data.commands.tags import tags_app  # noqa: E402
from entropy_data.commands.teams import teams_app  # noqa: E402
from entropy_data.commands.test_results import test_results_app  # noqa: E402
from entropy_data.commands.usage import usage_app  # noqa: E402

app.add_typer(connection_app, name="connection", help="Manage connections.")
app.add_typer(teams_app, name="teams", help="Manage teams.")
app.add_typer(dataproducts_app, name="dataproducts", help="Manage data products.")
app.add_typer(datacontracts_app, name="datacontracts", help="Manage data contracts.")
app.add_typer(access_app, name="access", help="Manage access (data usage agreements).")
app.add_typer(sourcesystems_app, name="sourcesystems", help="Manage source systems.")
app.add_typer(definitions_app, name="definitions", help="Manage definitions.")
app.add_typer(certifications_app, name="certifications", help="Manage certifications.")
app.add_typer(example_data_app, name="example-data", help="Manage example data.")
app.add_typer(test_results_app, name="test-results", help="Manage test results.")
app.add_typer(costs_app, name="costs", help="Manage costs.")
app.add_typer(assets_app, name="assets", help="Manage data assets.")
app.add_typer(tags_app, name="tags", help="Manage tags.")
app.add_typer(api_keys_app, name="api-keys", help="Manage API keys.")
app.add_typer(settings_app, name="settings", help="Manage organization settings.")
app.add_typer(events_app, name="events", help="Poll events.")
app.add_typer(lineage_app, name="lineage", help="Manage lineage (OpenLineage events).")
app.add_typer(search_app, name="search", help="Search across resources.")
app.add_typer(usage_app, name="usage", help="Manage usage (OpenTelemetry traces).")
app.add_typer(import_app, name="import", help="Import organization exports.")
