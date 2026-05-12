"""Connectors commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

connectors_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "connectors"
RESOURCE_TYPE = "connectors"


@connectors_app.command("list")
def list_connectors(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all connectors."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(RESOURCE_PATH)
        print_resource_list(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@connectors_app.command("get")
def get_connector(
    id: Annotated[str, typer.Argument(help="Connector ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a connector by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@connectors_app.command("put")
def put_connector(
    id: Annotated[str, typer.Argument(help="Connector ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a connector."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Connector '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@connectors_app.command("delete")
def delete_connector(
    id: Annotated[str, typer.Argument(help="Connector ID.")],
) -> None:
    """Delete a connector."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Connector '{id}' deleted.")
    except Exception as e:
        handle_error(e)
