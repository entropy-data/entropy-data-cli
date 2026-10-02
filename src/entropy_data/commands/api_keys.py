"""API Keys commands."""

from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, console, print_data, print_success

api_keys_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "api-keys"


@api_keys_app.command("create")
def create_api_key(
    team_id: Annotated[str, typer.Option("--team-id", help="Team ID to scope the key to.")],
    scope: Annotated[
        str, typer.Option("--scope", help="Scope: 'team' (read/write) or 'team_read' (read-only).")
    ] = "team",
    display_name: Annotated[
        Optional[str], typer.Option("--display-name", help="Human-readable name for the key.")
    ] = None,
    permission: Annotated[
        Optional[list[str]],
        typer.Option(
            "--permission",
            help=(
                "Permission the key may write with, by name (e.g. DATAPRODUCT_EDIT); repeat for more. "
                "Without it the key carries everything your key holds on the team."
            ),
        ),
    ] = None,
    read_only: Annotated[
        bool, typer.Option("--read-only", help="Create a read-only key (the same as --scope team_read).")
    ] = False,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Create a team-scoped API key."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        if read_only and permission:
            raise typer.BadParameter("--read-only and --permission exclude each other.")
        body = {"scope": scope, "teamId": team_id}
        if display_name:
            body["displayName"] = display_name
        if read_only:
            body["permissions"] = []
        elif permission:
            body["permissions"] = permission
        client = get_client()
        response = client.session.post(
            f"{client.base_url}/api/{RESOURCE_PATH}",
            json=body,
            timeout=client.timeout,
        )
        from entropy_data.client import _raise_for_status

        _raise_for_status(response)
        data = response.json()
        if fmt != OutputFormat.table:
            print_data(data, fmt)
        else:
            print_success(f"API key created: {data.get('organizationApiKeyId')}")
            permissions = data.get("permissions")
            if permissions is not None:
                console.print("[bold]Permissions:[/bold] " + (", ".join(permissions) if permissions else "read only"))
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
