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


def client_for_connection(name: str) -> EntropyDataClient:
    """Create an API client for a specific named connection (for `sync --source/--target`).

    Resolves the connection by name only — the global --api-key/--host overrides
    target the primary connection and must not bleed into a second endpoint.
    """
    config = resolve_connection(connection_name=name)
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


def inject_system_truststore() -> None:
    """Verify TLS using the operating system's certificate trust store instead of the
    bundled CA certificates. This lets the CLI work behind corporate proxies or with
    internal CAs whose root certificates are installed in the OS trust store but not in
    the certifi bundle that requests uses by default."""
    try:
        import truststore
    except ImportError:
        error_console.print("[red]--system-truststore requires the 'truststore' package, which is not installed.[/red]")
        raise typer.Exit(code=1)
    truststore.inject_into_ssl()


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
    system_truststore: Annotated[
        bool,
        typer.Option(
            "--system-truststore",
            help="Verify TLS using the operating system's certificate trust store "
            "instead of the bundled CA certificates (e.g. behind a corporate proxy or internal CA).",
            envvar="ENTROPY_DATA_SYSTEM_TRUSTSTORE",
        ),
    ] = False,
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
    if system_truststore:
        inject_system_truststore()


# Register command groups
from entropy_data.commands.access import access_app  # noqa: E402
from entropy_data.commands.api_keys import api_keys_app  # noqa: E402
from entropy_data.commands.assets import assets_app  # noqa: E402
from entropy_data.commands.certifications import certifications_app  # noqa: E402
from entropy_data.commands.classifications import classifications_app  # noqa: E402
from entropy_data.commands.connection import connection_app  # noqa: E402
from entropy_data.commands.connectors import connectors_app  # noqa: E402
from entropy_data.commands.costs import costs_app  # noqa: E402
from entropy_data.commands.datacontracts import datacontracts_app  # noqa: E402
from entropy_data.commands.dataproducts import dataproducts_app  # noqa: E402
from entropy_data.commands.definitions import definitions_app  # noqa: E402
from entropy_data.commands.events import events_app  # noqa: E402
from entropy_data.commands.example_data import example_data_app  # noqa: E402
from entropy_data.commands.import_export import export_app, import_app  # noqa: E402
from entropy_data.commands.integrations import integrations_app  # noqa: E402
from entropy_data.commands.lineage import lineage_app  # noqa: E402
from entropy_data.commands.organization import organization_app  # noqa: E402
from entropy_data.commands.policies import policies_app  # noqa: E402
from entropy_data.commands.schemas import schemas_app  # noqa: E402
from entropy_data.commands.search import search_app  # noqa: E402
from entropy_data.commands.semantics import semantics_app  # noqa: E402
from entropy_data.commands.settings import settings_app  # noqa: E402
from entropy_data.commands.sourcesystems import sourcesystems_app  # noqa: E402
from entropy_data.commands.sync import sync_command  # noqa: E402
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
app.add_typer(classifications_app, name="classifications", help="Manage classification schemes.")
app.add_typer(policies_app, name="policies", help="Manage policies.")
app.add_typer(example_data_app, name="example-data", help="Manage example data.")
app.add_typer(test_results_app, name="test-results", help="Manage test results.")
app.add_typer(costs_app, name="costs", help="Manage costs.")
app.add_typer(assets_app, name="assets", help="Manage data assets.")
app.add_typer(tags_app, name="tags", help="Manage tags.")
app.add_typer(api_keys_app, name="api-keys", help="Manage API keys.")
app.add_typer(connectors_app, name="connectors", help="Manage connectors.")
app.add_typer(integrations_app, name="integrations", help="Manage native data-platform integrations.")
app.add_typer(organization_app, name="organization", help="Get organization details.")
app.add_typer(settings_app, name="settings", help="Manage organization settings.")
app.add_typer(events_app, name="events", help="Poll events.")
app.add_typer(lineage_app, name="lineage", help="Manage lineage (OpenLineage events).")
app.add_typer(
    schemas_app,
    name="schemas",
    help="Get the JSON Schemas that data contracts (ODCS) and data products (ODPS) validate against.",
)
app.add_typer(search_app, name="search", help="Search across resources.")
app.add_typer(semantics_app, name="semantics", help="EXPERIMENTAL semantics API.")
app.add_typer(usage_app, name="usage", help="Manage usage (OpenTelemetry traces).")
app.add_typer(import_app, name="import", help="Import organization exports.")
app.add_typer(export_app, name="export", help="Export organization state to a local YAML tree.")

from entropy_data.resources import RESOURCE_ORDER as _RESOURCE_ORDER  # noqa: E402

_SYNC_HELP = (
    "Sync selected portable organization state from a source to a target connection.\n\n"
    "Nothing is copied unless named with --include (sync copies nothing by default).\n\n"
    "Supported resources: " + ", ".join(r.name for r in _RESOURCE_ORDER) + ".\n\n"
    "Not synced — users & team members, API keys, git credentials, integration and connector "
    "credentials, usage, costs, test results, events, and lineage (per-instance identity, secrets, "
    "or telemetry); organization customization, SCIM mapping, team-roles config, notification "
    "channels, connectors, and integrations are not supported yet."
)
app.command(name="sync", help=_SYNC_HELP)(sync_command)
