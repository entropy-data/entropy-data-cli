"""Data products commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

dataproducts_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "dataproducts"
RESOURCE_TYPE = "dataproducts"


@dataproducts_app.command("list")
def list_dataproducts(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    query: Annotated[Optional[str], typer.Option("--query", "-q", help="Search term.")] = None,
    status: Annotated[Optional[str], typer.Option("--status", help="Filter by status.")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag.")] = None,
    sort: Annotated[Optional[str], typer.Option("--sort", help="Sort field.")] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all data products."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {"p": page}
        if query:
            params["q"] = query
        if status:
            params["status"] = status
        if tag:
            params["tag"] = tag
        if sort:
            params["sort"] = sort
        data, has_next = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("get")
def get_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a data product by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("put")
def put_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a data product."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Data product '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("delete")
def delete_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
) -> None:
    """Delete a data product."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Data product '{id}' deleted.")
    except Exception as e:
        handle_error(e)
