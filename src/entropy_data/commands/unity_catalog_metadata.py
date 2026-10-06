"""Unity Catalog metadata integrations.

The integrations that write data contract metadata to Databricks Unity Catalog
(`/api/integrations/unity-catalog-metadata`): list and inspect them, create or
change one with its service principal, see the tables they wrote and the queue of
changes they have not written yet, and retry or discard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

unity_catalog_metadata_app = typer.Typer(no_args_is_help=True)

RESOURCE_PATH = "integrations/unity-catalog-metadata"
RESOURCE_TYPE = "unity-catalog-metadata-integrations"
TABLES_TYPE = "unity-catalog-metadata-tables"
QUEUE_TYPE = "unity-catalog-metadata-queue"


@unity_catalog_metadata_app.command("list")
def list_integrations(
    enabled: Annotated[
        Optional[bool],
        typer.Option("--enabled/--disabled", help="Filter to integrations that write, or those switched off."),
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the Unity Catalog metadata integrations."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params: dict = {}
        if enabled is not None:
            params["enabled"] = "true" if enabled else "false"
        data, _ = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@unity_catalog_metadata_app.command("get")
def get_integration(
    external_id: Annotated[str, typer.Argument(help="Integration externalId.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get an integration with its credential (secret excluded) and its status: tables, queue and task."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, external_id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@unity_catalog_metadata_app.command("put")
def put_integration(
    external_id: Annotated[str, typer.Argument(help="Integration externalId.")],
    file: Annotated[
        Optional[Path],
        typer.Option(
            "--file",
            "-f",
            help="JSON or YAML file (use - for stdin) with `name`, `credential` (databricksHost, databricksClientId, "
            "databricksClientSecret, databricksWarehouseId) and `enabled`; the options below override its values.",
        ),
    ] = None,
    name: Annotated[Optional[str], typer.Option("--name", help="Display name.")] = None,
    host: Annotated[Optional[str], typer.Option("--host", help="The workspace host, with or without https://.")] = None,
    client_id: Annotated[
        Optional[str], typer.Option("--client-id", help="The service principal's application id.")
    ] = None,
    client_secret: Annotated[
        Optional[str],
        typer.Option(
            "--client-secret", help="The service principal's OAuth secret.", envvar="DATABRICKS_CLIENT_SECRET"
        ),
    ] = None,
    warehouse_id: Annotated[
        Optional[str],
        typer.Option(
            "--warehouse-id", help="The SQL warehouse that runs the COMMENT statements; without it, tags only."
        ),
    ] = None,
    enabled: Annotated[
        Optional[bool], typer.Option("--enabled/--disabled", help="Whether the integration writes.")
    ] = None,
) -> None:
    """Create or update a Unity Catalog metadata integration.

    On create the credential is required (host, client id and secret). On update an omitted credential keeps the
    stored one.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        body: dict = read_body(file) if file else {}
        if name is not None:
            body["name"] = name
        credential = dict(body.get("credential") or {})
        for key, value in (
            ("databricksHost", host),
            ("databricksClientId", client_id),
            ("databricksClientSecret", client_secret),
            ("databricksWarehouseId", warehouse_id),
        ):
            if value is not None:
                credential[key] = value
        if credential:
            body["credential"] = credential
        if enabled is not None:
            body["enabled"] = enabled
        if not body.get("name"):
            raise typer.BadParameter("A name is required: pass --name or a file with `name`.")
        client = get_client()
        client.put_resource(RESOURCE_PATH, external_id, body)
        print_success(f"Integration '{external_id}' saved.")
    except Exception as e:
        handle_error(e)


@unity_catalog_metadata_app.command("delete")
def delete_integration(
    external_id: Annotated[str, typer.Argument(help="Integration externalId.")],
) -> None:
    """Delete an integration with its queue, its records of written tables and its task; what was written stays."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, external_id)
        print_success(f"Integration '{external_id}' deleted.")
    except Exception as e:
        handle_error(e)


@unity_catalog_metadata_app.command("tables")
def list_tables(
    external_id: Annotated[str, typer.Argument(help="Integration externalId.")],
    state: Annotated[
        Optional[str], typer.Option("--state", help="Filter by state (in_sync, unresolved, failed).")
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the tables the integration wrote, with the state of the last write."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params: dict = {}
        if state:
            params["state"] = state
        data, _ = client.list_resources(f"{RESOURCE_PATH}/{external_id}/tables", params=params)
        print_resource_list(data, TABLES_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@unity_catalog_metadata_app.command("queue")
def list_queue(
    external_id: Annotated[str, typer.Argument(help="Integration externalId.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the changes the integration has not written yet, oldest first."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(f"{RESOURCE_PATH}/{external_id}/queue")
        print_resource_list(data, QUEUE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@unity_catalog_metadata_app.command("retry-failed")
def retry_failed(
    external_id: Annotated[str, typer.Argument(help="Integration externalId.")],
) -> None:
    """Write every data contract again that has a failed or unresolved table."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        result = client.post_action_json(RESOURCE_PATH, external_id, "tables/retry-failed")
        print_success(result.get("message") or f"{result.get('count', 0)} data contracts are written again.")
    except Exception as e:
        handle_error(e)


@unity_catalog_metadata_app.command("discard-queue")
def discard_queue(
    external_id: Annotated[str, typer.Argument(help="Integration externalId.")],
) -> None:
    """Drop every change that waits for the integration; later changes are written as usual."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        result = client.post_action_json(RESOURCE_PATH, external_id, "queue/discard")
        print_success(result.get("message") or f"{result.get('count', 0)} queue entries discarded.")
    except Exception as e:
        handle_error(e)
