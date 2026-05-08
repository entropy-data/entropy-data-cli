"""Organization commands."""

import json
from typing import Annotated, Optional

import typer
from rich.table import Table

from entropy_data.output import OutputFormat, console

organization_app = typer.Typer(no_args_is_help=True)


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
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(data))
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
