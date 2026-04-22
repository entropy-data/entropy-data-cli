"""Data contracts commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

datacontracts_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "datacontracts"
RESOURCE_TYPE = "datacontracts"


@datacontracts_app.command("list")
def list_datacontracts(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    query: Annotated[Optional[str], typer.Option("--query", "-q", help="Search term.")] = None,
    owner: Annotated[Optional[str], typer.Option("--owner", help="Filter by owner.")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag.")] = None,
    sort: Annotated[Optional[str], typer.Option("--sort", help="Sort field.")] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all data contracts."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {"p": page}
        if query:
            params["q"] = query
        if owner:
            params["owner"] = owner
        if tag:
            params["tag"] = tag
        if sort:
            params["sort"] = sort
        data, has_next = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("get")
def get_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a data contract by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("put")
def put_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a data contract."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Data contract '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("test")
def test_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    server: Annotated[Optional[str], typer.Option("--server", "-s", help="Server name to test against.")] = None,
) -> None:
    """Run a data contract test."""
    import json

    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        params = {}
        if server:
            params["server"] = server
        # Data contract tests can take a long time (up to 30 minutes)
        data = client.post_action_json(RESOURCE_PATH, id, "test", params=params, timeout=1800)
        print(json.dumps(data, indent=2))
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("delete")
def delete_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
) -> None:
    """Delete a data contract."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Data contract '{id}' deleted.")
    except Exception as e:
        handle_error(e)
