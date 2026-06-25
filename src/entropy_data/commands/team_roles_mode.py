"""Team roles mode command (organization-scoped).

Reads and sets whether team permissions are derived from the built-in default
roles or from the organization's custom team role catalog.
"""

from enum import Enum
from typing import Annotated, Optional

import typer
from rich.table import Table

from entropy_data.output import OutputFormat, console, print_data, print_success

team_roles_mode_app = typer.Typer(no_args_is_help=True)

PATH = "organization/team-roles-mode"


class TeamRolesMode(str, Enum):
    DEFAULT = "DEFAULT"
    CUSTOM = "CUSTOM"


@team_roles_mode_app.command("get")
def get_mode(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show whether the organization uses DEFAULT or CUSTOM team roles."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        response = client.session.get(f"{client.base_url}/api/{PATH}", timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        data = response.json()
        if fmt != OutputFormat.table:
            print_data(data, fmt)
            return

        table = Table(show_header=False)
        table.add_column("Field", style="cyan")
        table.add_column("Value")
        table.add_row("mode", str(data.get("mode", "")))
        console.print(table)
    except Exception as e:
        handle_error(e)


@team_roles_mode_app.command("set")
def set_mode(
    mode: Annotated[TeamRolesMode, typer.Argument(help="DEFAULT (built-in roles) or CUSTOM (custom team role catalog).")],
) -> None:
    """Switch the organization between DEFAULT and CUSTOM team roles.

    Switching to CUSTOM is rejected with 409 when no custom team roles are
    defined yet — create at least one first. Switching to DEFAULT never deletes
    custom roles and is always allowed.
    """
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    try:
        client = get_client()
        response = client.session.put(
            f"{client.base_url}/api/{PATH}",
            json={"mode": mode.value},
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success(f"Team roles mode set to {mode.value}.")
    except Exception as e:
        handle_error(e)
