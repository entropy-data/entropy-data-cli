"""Policies commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

policies_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "policies"
RESOURCE_TYPE = "policies"


@policies_app.command("list")
def list_policies(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all policies."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources(RESOURCE_PATH)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next)
    except Exception as e:
        handle_error(e)


@policies_app.command("get")
def get_policy(
    id: Annotated[str, typer.Argument(help="Policy ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a policy by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@policies_app.command("put")
def put_policy(
    id: Annotated[str, typer.Argument(help="Policy ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a policy."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Policy '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@policies_app.command("delete")
def delete_policy(
    id: Annotated[str, typer.Argument(help="Policy ID.")],
) -> None:
    """Delete a policy."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Policy '{id}' deleted.")
    except Exception as e:
        handle_error(e)
