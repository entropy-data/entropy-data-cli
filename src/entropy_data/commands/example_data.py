"""Example data commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

example_data_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "example-data"
RESOURCE_TYPE = "example-data"


@example_data_app.command("list")
def list_example_data(
    data_product_id: Annotated[Optional[str], typer.Option("--data-product-id", help="Filter by data product.")] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all example data entries."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {}
        if data_product_id:
            params["dataProductId"] = data_product_id
        data, has_next = client.list_resources(RESOURCE_PATH, params=params or None)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next)
    except Exception as e:
        handle_error(e)


@example_data_app.command("get")
def get_example_data(
    id: Annotated[str, typer.Argument(help="Example data ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get example data by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@example_data_app.command("put")
def put_example_data(
    id: Annotated[str, typer.Argument(help="Example data ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update example data."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Example data '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@example_data_app.command("delete")
def delete_example_data(
    id: Annotated[str, typer.Argument(help="Example data ID.")],
) -> None:
    """Delete example data."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Example data '{id}' deleted.")
    except Exception as e:
        handle_error(e)
