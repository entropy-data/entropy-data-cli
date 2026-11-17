"""Organization commands."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table

from entropy_data.output import OutputFormat, console, print_data, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

organization_app = typer.Typer(no_args_is_help=True)
members_app = typer.Typer(no_args_is_help=True)
features_app = typer.Typer(no_args_is_help=True)
FEATURES_PATH = "/api/organization/features"


@organization_app.command("get")
def get_organization(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get settings of the organization the current API key is bound to."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data = get_client().http.get_json("/api/organization/settings")
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


@features_app.command("get")
def get_features(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show the organization's feature configuration.

    Policies and switches such as the change process, managed tags, auto-approval, Use Cases, MCP
    and the Quality Score. An empty value means the feature uses its default. `--output yaml`
    prints the document `put` takes.
    """
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data = get_client().http.get_json(FEATURES_PATH)
        if fmt != OutputFormat.table:
            print_data(data, fmt)
            return

        table = Table(show_header=False)
        table.add_column("Feature", style="cyan")
        table.add_column("Value")
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            table.add_row(key, "" if value is None else str(value))
        console.print(table)
    except Exception as e:
        handle_error(e)


@features_app.command("put")
def put_features(
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Replace the organization's feature configuration.

    The body is the document `get --output yaml` prints. It replaces the whole configuration: a
    feature the file leaves out goes back to its default. To change one feature, `get`, edit and
    `put` the whole document. The data contract test runner credentials are never changed.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        get_client().http.put_json(FEATURES_PATH, body)
        print_success("Organization features saved.")
    except Exception as e:
        handle_error(e)


organization_app.add_typer(
    features_app,
    name="features",
    help="Get or set the organization's feature configuration (policies and feature switches).",
)


from entropy_data.commands.git_credentials import make_git_credentials_app  # noqa: E402

organization_app.add_typer(
    make_git_credentials_app("organization"),
    name="git-credentials",
    help="Manage organization-level git credentials.",
)
