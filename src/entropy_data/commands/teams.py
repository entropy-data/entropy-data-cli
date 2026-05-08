"""Teams commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

teams_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "teams"
RESOURCE_TYPE = "teams"


@teams_app.command("list")
def list_teams(
    member: Annotated[
        Optional[str],
        typer.Option("--member", "-m", help="Filter to teams where this email is a member; adds a Role column."),
    ] = None,
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all teams."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        if member is None:
            data, has_next = client.list_resources(RESOURCE_PATH, params={"p": page})
            print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
            return

        all_teams: list[dict] = []
        current_page = 0
        while True:
            items, has_next = client.list_resources(RESOURCE_PATH, params={"p": current_page})
            all_teams.extend(items)
            if not has_next:
                break
            current_page += 1

        member_lower = member.lower()
        filtered: list[dict] = []
        for team in all_teams:
            for m in team.get("members") or []:
                if (m.get("emailAddress") or "").lower() == member_lower:
                    team["role"] = m.get("role") or ""
                    filtered.append(team)
                    break
        print_resource_list(filtered, "my-teams", fmt, title=f"teams where {member} is a member")
    except Exception as e:
        handle_error(e)


@teams_app.command("get")
def get_team(
    id: Annotated[str, typer.Argument(help="Team ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a team by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@teams_app.command("put")
def put_team(
    id: Annotated[str, typer.Argument(help="Team ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a team."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Team '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@teams_app.command("delete")
def delete_team(
    id: Annotated[str, typer.Argument(help="Team ID.")],
) -> None:
    """Delete a team."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Team '{id}' deleted.")
    except Exception as e:
        handle_error(e)
