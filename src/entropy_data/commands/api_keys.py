"""API Keys commands."""

import json
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, console, print_success

api_keys_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "api-keys"


@api_keys_app.command("create")
def create_api_key(
    scope: Annotated[str, typer.Option("--scope", help="Scope: 'team' (read/write) or 'team_read' (read-only).")],
    team_id: Annotated[str, typer.Option("--team-id", help="Team ID to scope the key to.")],
    display_name: Annotated[
        Optional[str], typer.Option("--display-name", help="Human-readable name for the key.")
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Create a team-scoped API key."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        body = {"scope": scope, "teamId": team_id}
        if display_name:
            body["displayName"] = display_name
        client = get_client()
        response = client.session.post(
            f"{client.base_url}/api/{RESOURCE_PATH}",
            json=body,
            timeout=30,
        )
        from entropy_data.client import _raise_for_status

        _raise_for_status(response)
        data = response.json()
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(data))
        else:
            print_success(f"API key created: {data.get('organizationApiKeyId')}")
            key = data.get("key")
            if key:
                console.print(f"[bold]Key:[/bold] {key}")
                console.print("[dim]This key is only shown once. Store it securely.[/dim]")
    except Exception as e:
        handle_error(e)


@api_keys_app.command("delete")
def delete_api_key(
    id: Annotated[str, typer.Argument(help="API key ID.")],
) -> None:
    """Delete a team-scoped API key."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"API key '{id}' deleted.")
    except Exception as e:
        handle_error(e)
