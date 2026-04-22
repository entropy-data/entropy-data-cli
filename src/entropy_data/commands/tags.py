"""Tags commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

tags_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "tags"
RESOURCE_TYPE = "tags"


@tags_app.command("list")
def list_tags(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    owner: Annotated[Optional[str], typer.Option("--owner", help="Filter by owner (team name).")] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all tags."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        params = {"p": page}
        if owner:
            params["owner"] = owner
        client = get_client()
        data, has_next = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@tags_app.command("get")
def get_tag(
    id: Annotated[str, typer.Argument(help="Tag ID (e.g. 'Governance/PII').")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a tag by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@tags_app.command("put")
def put_tag(
    id: Annotated[str, typer.Argument(help="Tag ID (e.g. 'Governance/PII').")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a tag."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Tag '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@tags_app.command("delete")
def delete_tag(
    id: Annotated[str, typer.Argument(help="Tag ID (e.g. 'Governance/PII').")],
) -> None:
    """Delete a tag."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Tag '{id}' deleted.")
    except Exception as e:
        handle_error(e)
