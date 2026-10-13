"""Team notification channel subcommands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_data, print_success
from entropy_data.util import read_body

notifications_app = typer.Typer(no_args_is_help=True)


def _channel_path(team_id: str, channel_id: str) -> str:
    from entropy_data.client import _validate_resource_id

    _validate_resource_id(team_id)
    _validate_resource_id(channel_id)
    return f"/api/teams/{team_id}/notification-channels/{channel_id}"


@notifications_app.command("get")
def get_channel(
    team_id: Annotated[str, typer.Argument(help="Team ID.")],
    channel_id: Annotated[str, typer.Argument(help="Notification channel ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a team's notification channel."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data = get_client().http.get_json(_channel_path(team_id, channel_id))
        print_data(data, fmt)
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

    try:
        body = read_body(file)
        get_client().http.put_json(_channel_path(team_id, channel_id), body)
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

    try:
        get_client().http.delete(_channel_path(team_id, channel_id))
        print_success(f"Notification channel '{channel_id}' deleted for team '{team_id}'.")
    except Exception as e:
        handle_error(e)
