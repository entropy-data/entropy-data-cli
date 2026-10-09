"""Data product builders commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

dataproductbuilders_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "dataproductbuilders"
RESOURCE_TYPE = "dataproductbuilders"


@dataproductbuilders_app.command("list")
def list_dataproductbuilders(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all data product builders."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources(RESOURCE_PATH)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next)
    except Exception as e:
        handle_error(e)


@dataproductbuilders_app.command("get")
def get_dataproductbuilder(
    id: Annotated[str, typer.Argument(help="Data product builder ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a data product builder by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@dataproductbuilders_app.command("put")
def put_dataproductbuilder(
    id: Annotated[str, typer.Argument(help="Data product builder ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or replace a data product builder. Fields left out are cleared."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Data product builder '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@dataproductbuilders_app.command("delete")
def delete_dataproductbuilder(
    id: Annotated[str, typer.Argument(help="Data product builder ID.")],
) -> None:
    """Delete a data product builder."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Data product builder '{id}' deleted.")
    except Exception as e:
        handle_error(e)
