"""Organization commands."""

from typing import Annotated, Optional

import typer
from rich.table import Table

from entropy_data.output import OutputFormat, console, print_data, print_resource, print_resource_list

organization_app = typer.Typer(no_args_is_help=True)
members_app = typer.Typer(no_args_is_help=True)


@organization_app.command("get")
def get_organization(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get settings of the organization the current API key is bound to."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        response = client.session.get(
            f"{client.base_url}/api/organization/settings",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        data = response.json()
        if fmt != OutputFormat.table:
            print_data(data, fmt)
            return

        table = Table(show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        for key in ("vanityUrl", "host", "fullName", "logoUrl", "supportEmailAddress", "brand", "plan"):
            value = data.get(key)
            if value:
                table.add_row(key, str(value))
        sso = data.get("sso")
        if sso:
            table.add_row("sso.issuer", sso.get("issuer", ""))
            if sso.get("tenant"):
                table.add_row("sso.tenant", sso["tenant"])
            if sso.get("autoJoin") is not None:
                table.add_row("sso.autoJoin", str(sso["autoJoin"]))
        console.print(table)
    except Exception as e:
        handle_error(e)


@members_app.command("list")
def list_members(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List organization members."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources("organization/members", params={"p": page})
        print_resource_list(data, "organization-members", fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@members_app.command("get")
def get_member(
    email_address: Annotated[str, typer.Argument(help="Email address of the member.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get an organization member by email address."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource("organization/members", email_address)
        print_resource(data, "organization-members", fmt)
    except Exception as e:
        handle_error(e)


organization_app.add_typer(members_app, name="members", help="Manage organization members.")


from entropy_data.commands.custom_team_roles import custom_team_roles_app  # noqa: E402
from entropy_data.commands.git_credentials import make_git_credentials_app  # noqa: E402
from entropy_data.commands.team_roles_mode import team_roles_mode_app  # noqa: E402

organization_app.add_typer(
    make_git_credentials_app("organization"),
    name="git-credentials",
    help="Manage organization-level git credentials.",
)

organization_app.add_typer(
    custom_team_roles_app,
    name="custom-team-roles",
    help="Manage organization-level custom team roles.",
)

organization_app.add_typer(
    team_roles_mode_app,
    name="team-roles-mode",
    help="Get or set whether the organization uses default or custom team roles.",
)
