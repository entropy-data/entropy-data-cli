"""Access (data usage agreements) commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

access_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "access"
RESOURCE_TYPE = "access"


@access_app.command("list")
def list_access(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all access agreements."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources(RESOURCE_PATH, params={"p": page})
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@access_app.command("get")
def get_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get an access agreement by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@access_app.command("put")
def put_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Access agreement '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@access_app.command("delete")
def delete_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Delete an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Access agreement '{id}' deleted.")
    except Exception as e:
        handle_error(e)


@access_app.command("approve")
def approve_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Approve an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        location = client.post_action(RESOURCE_PATH, id, "approve")
        print_success(f"Access agreement '{id}' approved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@access_app.command("reject")
def reject_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Reject an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        location = client.post_action(RESOURCE_PATH, id, "reject")
        print_success(f"Access agreement '{id}' rejected.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@access_app.command("cancel")
def cancel_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Cancel an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        location = client.post_action(RESOURCE_PATH, id, "cancel")
        print_success(f"Access agreement '{id}' cancelled.")
        print_link(location)
    except Exception as e:
        handle_error(e)
