"""Team notification channel subcommands."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, console, print_success
from entropy_data.util import read_body

notifications_app = typer.Typer(no_args_is_help=True)


def _channel_url(client, team_id: str, channel_id: str) -> str:
    return f"{client.base_url}/api/teams/{team_id}/notification-channels/{channel_id}"


@notifications_app.command("get")
def get_channel(
    team_id: Annotated[str, typer.Argument(help="Team ID.")],
    channel_id: Annotated[str, typer.Argument(help="Notification channel ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a team's notification channel."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    fmt = output or get_output_format()
    try:
        client = get_client()
        _validate_resource_id(team_id)
        _validate_resource_id(channel_id)
        response = client.session.get(_channel_url(client, team_id, channel_id), timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        data = response.json()
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(data))
        else:
            console.print_json(json.dumps(data))
    except Exception as e:
        handle_error(e)


@notifications_app.command("put")
def put_channel(
    team_id: Annotated[str, typer.Argument(help="Team ID.")],
    channel_id: Annotated[str, typer.Argument(help="Notification channel ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a team's notification channel."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    try:
        body = read_body(file)
        client = get_client()
        _validate_resource_id(team_id)
        _validate_resource_id(channel_id)
        response = client.session.put(
            _channel_url(client, team_id, channel_id),
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success(f"Notification channel '{channel_id}' saved for team '{team_id}'.")
    except Exception as e:
        handle_error(e)


@notifications_app.command("delete")
def delete_channel(
    team_id: Annotated[str, typer.Argument(help="Team ID.")],
    channel_id: Annotated[str, typer.Argument(help="Notification channel ID.")],
) -> None:
    """Delete a team's notification channel."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    try:
        client = get_client()
        _validate_resource_id(team_id)
        _validate_resource_id(channel_id)
        response = client.session.delete(_channel_url(client, team_id, channel_id), timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        print_success(f"Notification channel '{channel_id}' deleted for team '{team_id}'.")
    except Exception as e:
        handle_error(e)
