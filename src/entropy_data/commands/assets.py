"""Assets commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import (
    OutputFormat,
    console,
    print_data,
    print_link,
    print_resource,
    print_resource_list,
    print_success,
)
from entropy_data.util import read_body

assets_app = typer.Typer(no_args_is_help=True)
tags_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "assets"
RESOURCE_TYPE = "assets"


@assets_app.command("list")
def list_assets(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all data assets."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources(RESOURCE_PATH, params={"p": page})
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@assets_app.command("get")
def get_asset(
    id: Annotated[str, typer.Argument(help="Asset ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a data asset by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@assets_app.command("put")
def put_asset(
    id: Annotated[str, typer.Argument(help="Asset ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a data asset."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Asset '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@assets_app.command("delete")
def delete_asset(
    id: Annotated[str, typer.Argument(help="Asset ID.")],
) -> None:
    """Delete a data asset."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Asset '{id}' deleted.")
    except Exception as e:
        handle_error(e)


@tags_app.command("list")
def list_asset_tags(
    asset_id: Annotated[str, typer.Argument(help="Asset ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List tags assigned to an asset."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    fmt = output or get_output_format()
    try:
        client = get_client()
        _validate_resource_id(asset_id)
        response = client.session.get(
            f"{client.base_url}/api/assets/{asset_id}/assigned-tags",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        data = response.json()
        if fmt != OutputFormat.table:
            print_data(data, fmt)
        else:
            for tag in data:
                console.print(tag)
    except Exception as e:
        handle_error(e)


@tags_app.command("add")
def add_asset_tag(
    asset_id: Annotated[str, typer.Argument(help="Asset ID.")],
    tag_id: Annotated[str, typer.Argument(help="Tag ID (may be hierarchical, e.g. governance/PII).")],
) -> None:
    """Assign a tag to an asset."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    try:
        client = get_client()
        _validate_resource_id(asset_id)
        # tag_id can contain "/" (e.g. governance/PII) so we don't run it through the
        # path-traversal-rejecting validator; the server validates anyway.
        response = client.session.put(
            f"{client.base_url}/api/assets/{asset_id}/assigned-tags/{tag_id}",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success(f"Tag '{tag_id}' assigned to asset '{asset_id}'.")
    except Exception as e:
        handle_error(e)


@tags_app.command("remove")
def remove_asset_tag(
    asset_id: Annotated[str, typer.Argument(help="Asset ID.")],
    tag_id: Annotated[str, typer.Argument(help="Tag ID (may be hierarchical, e.g. governance/PII).")],
) -> None:
    """Unassign a tag from an asset."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    try:
        client = get_client()
        _validate_resource_id(asset_id)
        response = client.session.delete(
            f"{client.base_url}/api/assets/{asset_id}/assigned-tags/{tag_id}",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success(f"Tag '{tag_id}' removed from asset '{asset_id}'.")
    except Exception as e:
        handle_error(e)


assets_app.add_typer(tags_app, name="tags", help="Manage tag assignments on an asset.")
