"""Settings commands."""

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table

from entropy_data.output import OutputFormat, console, print_data, print_success
from entropy_data.util import read_body

settings_app = typer.Typer(no_args_is_help=True)
team_roles_app = typer.Typer(no_args_is_help=True)
email_templates_app = typer.Typer(no_args_is_help=True)


@settings_app.command("get-customization")
def get_customization(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get organization customization settings."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        accept = "application/json" if fmt == OutputFormat.json else "application/yaml"
        response = client.session.get(
            f"{client.base_url}/api/settings/customization",
            headers={"Accept": accept},
            timeout=client.timeout,
        )
        _raise_for_status(response)
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(response.json()))
        else:
            console.print(response.text)
    except Exception as e:
        handle_error(e)


@settings_app.command("put-customization")
def put_customization(
    file: Annotated[Path, typer.Option("--file", "-f", help="YAML or JSON file (use - for stdin).")] = ...,
) -> None:
    """Update organization customization settings."""
    from entropy_data.cli import get_client, handle_error

    try:
        _put_yaml_or_json(get_client(), "/api/settings/customization", file)
        print_success("Customization updated.")
    except Exception as e:
        handle_error(e)


@settings_app.command("get-scim-mapping")
def get_scim_mapping(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get the SCIM group mapping configuration."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        accept = "application/json" if fmt == OutputFormat.json else "application/yaml"
        response = client.session.get(
            f"{client.base_url}/api/settings/scim-mapping",
            headers={"Accept": accept},
            timeout=client.timeout,
        )
        _raise_for_status(response)
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(response.json()))
        else:
            console.print(response.text)
    except Exception as e:
        handle_error(e)


@settings_app.command("put-scim-mapping")
def put_scim_mapping(
    file: Annotated[Path, typer.Option("--file", "-f", help="YAML or JSON file (use - for stdin).")] = ...,
) -> None:
    """Update the SCIM group mapping configuration."""
    from entropy_data.cli import get_client, handle_error

    try:
        _put_yaml_or_json(get_client(), "/api/settings/scim-mapping", file)
        print_success("SCIM mapping updated.")
    except Exception as e:
        handle_error(e)


def _put_yaml_or_json(client, path: str, file: Path) -> None:
    """PUT a YAML or JSON payload from `file` to `path`, picking Content-Type by extension/content."""
    from entropy_data.client import _raise_for_status

    if str(file) == "-":
        content = sys.stdin.read()
    else:
        content = file.read_text()
    is_json = str(file).endswith(".json") or content.lstrip().startswith("{")
    content_type = "application/json" if is_json else "application/yaml"
    response = client.session.put(
        f"{client.base_url}{path}",
        data=content.encode(),
        headers={"Content-Type": content_type},
        timeout=client.timeout,
    )
    _raise_for_status(response)


@team_roles_app.command("get")
def get_team_roles(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show the team roles configuration (default roles or the custom catalog)."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        response = client.session.get(f"{client.base_url}/api/settings/team-roles", timeout=client.timeout)
        _raise_for_status(response)
        data = response.json()
        if fmt != OutputFormat.table:
            print_data(data, fmt)
            return

        console.print(f"mode: [cyan]{data.get('mode', '')}[/cyan]")
        roles = data.get("team-roles") or []
        if roles:
            table = Table()
            table.add_column("name", style="cyan")
            table.add_column("rank")
            table.add_column("permissions")
            for role in roles:
                table.add_row(
                    str(role.get("name", "")),
                    str(role.get("rank", "")),
                    ", ".join(role.get("permissions", []) or []),
                )
            console.print(table)
    except Exception as e:
        handle_error(e)


@team_roles_app.command("put")
def put_team_roles(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="JSON or YAML file with the body (use - for stdin).")
    ] = ...,
) -> None:
    """Set the team roles configuration.

    The body is the aggregate payload, e.g. `{"mode": "default"}` or
    `{"mode": "custom-team-roles", "team-roles": [ ... ]}`. With `custom-team-roles`
    the listed roles replace the whole catalog; an empty list is rejected with 409.
    """
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _raise_for_status

    try:
        body = read_body(file)
        client = get_client()
        response = client.session.put(
            f"{client.base_url}/api/settings/team-roles",
            json=body,
            timeout=client.timeout,
        )
        _raise_for_status(response)
        mode = response.json().get("mode", "")
        print_success(f"Team roles configuration saved (mode: {mode}).")
    except Exception as e:
        handle_error(e)


settings_app.add_typer(
    team_roles_app,
    name="team-roles",
    help="Get or set the organization's team roles configuration.",
)


@email_templates_app.command("get")
def get_email_templates(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show the organization's email templates.

    Every email type with its enabled state and the effective subject and body per
    language, each marked as built-in or customized. `--output yaml` prints the
    document `put` takes.
    """
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        response = client.session.get(f"{client.base_url}/api/settings/email-templates", timeout=client.timeout)
        _raise_for_status(response)
        data = response.json()
        if fmt != OutputFormat.table:
            print_data(data, fmt)
            return

        table = Table()
        table.add_column("type", style="cyan")
        table.add_column("enabled")
        table.add_column("customized")
        for name, template in (data.get("templates") or {}).items():
            languages = template.get("languages") or {}
            customized = [lang for lang, content in languages.items() if content.get("customized")]
            table.add_row(
                name,
                "yes" if template.get("enabled", True) else "no",
                ", ".join(customized) or "-",
            )
        console.print(table)
    except Exception as e:
        handle_error(e)


@email_templates_app.command("put")
def put_email_templates(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="JSON or YAML file with the body (use - for stdin).")
    ] = ...,
) -> None:
    """Set the organization's email templates.

    The body is the document `get --output yaml` prints: `templates.<type>.enabled`
    and `templates.<type>.languages.<lang>.{subject, body}`. It replaces the whole
    setup — types and languages not in the file revert to the built-in email, and
    wording identical to the built-in text stays uncustomized, so a `get` written
    back unchanged customizes nothing.
    """
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _raise_for_status

    try:
        body = read_body(file)
        client = get_client()
        response = client.session.put(
            f"{client.base_url}/api/settings/email-templates",
            json=body,
            timeout=client.timeout,
        )
        _raise_for_status(response)
        templates = response.json().get("templates") or {}
        customized = sum(
            1
            for template in templates.values()
            if any(content.get("customized") for content in (template.get("languages") or {}).values())
        )
        disabled = sum(1 for template in templates.values() if template.get("enabled") is False)
        print_success(f"Email templates saved ({customized} customized, {disabled} disabled).")
    except Exception as e:
        handle_error(e)


settings_app.add_typer(
    email_templates_app,
    name="email-templates",
    help="Get or set the organization's email templates.",
)
