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
dataproduct_types_app = typer.Typer(no_args_is_help=True)
output_port_types_app = typer.Typer(no_args_is_help=True)


@settings_app.command("get-customization")
def get_customization(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get organization customization settings."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    try:
        _print_json_or_yaml(get_client(), "/api/settings/customization", output or get_output_format())
    except Exception as e:
        handle_error(e)


def _print_json_or_yaml(client, path: str, fmt: OutputFormat) -> None:
    """Print a document the API serves as JSON or YAML, in the format asked for (YAML unless json)."""
    if fmt == OutputFormat.json:
        console.print_json(json.dumps(client.http.get_json(path)))
    else:
        console.print(client.http.get_text(path))


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

    try:
        _print_json_or_yaml(get_client(), "/api/settings/scim-mapping", output or get_output_format())
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
    if str(file) == "-":
        content = sys.stdin.read()
    else:
        content = file.read_text()
    is_json = str(file).endswith(".json") or content.lstrip().startswith("{")
    content_type = "application/json" if is_json else "application/yaml"
    client.http.put_text(path, content, content_type=content_type)


@team_roles_app.command("get")
def get_team_roles(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show the team roles configuration (default roles or the custom catalog)."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data = get_client().http.get_json("/api/settings/team-roles")
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

    try:
        body = read_body(file)
        mode = get_client().http.request("PUT", "/api/settings/team-roles", json=body).json().get("mode", "")
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

    fmt = output or get_output_format()
    try:
        data = get_client().http.get_json("/api/settings/email-templates")
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

    try:
        body = read_body(file)
        saved = get_client().http.request("PUT", "/api/settings/email-templates", json=body).json()
        templates = saved.get("templates") or {}
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


@dataproduct_types_app.command("get")
def get_dataproduct_types(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show the organization's data product types.

    Every type in order with its behavior, labels and flags; `builtIn` marks types the
    organization has not defined itself. `--output yaml` prints the document `put` takes.
    """
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data = get_client().http.get_json("/api/settings/dataproduct-types")
        if fmt != OutputFormat.table:
            print_data(data, fmt)
            return

        table = Table()
        table.add_column("id", style="cyan")
        table.add_column("label")
        table.add_column("behavior")
        table.add_column("enabled")
        table.add_column("default")
        table.add_column("built-in")
        for type_ in data.get("dataProductTypes") or []:
            labels = type_.get("labels") or {}
            table.add_row(
                type_.get("id", ""),
                labels.get("en") or next(iter(labels.values()), ""),
                type_.get("behavior") or "",
                "yes" if type_.get("enabled", True) else "no",
                "yes" if type_.get("default") else "",
                "yes" if type_.get("builtIn") else "",
            )
        console.print(table)
    except Exception as e:
        handle_error(e)


@dataproduct_types_app.command("put")
def put_dataproduct_types(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="JSON or YAML file with the body (use - for stdin).")
    ] = ...,
) -> None:
    """Set the organization's data product types.

    The body is the document `get --output yaml` prints: `dataProductTypes`, a list of
    types with `id`, `outputPorts`, `labels`, `descriptions`, `examples`, `icon`,
    `enabled`, `showOnMarketplaceHome` and `default`. It replaces the whole list — types
    not in the file are removed. `behavior` and `builtIn` are read-only, and system types
    are ignored, so a `get` written back unchanged is accepted.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        _put_yaml_or_json(get_client(), "/api/settings/dataproduct-types", file)
        print_success("Data product types saved.")
    except Exception as e:
        handle_error(e)


settings_app.add_typer(
    dataproduct_types_app,
    name="dataproduct-types",
    help="Get or set the organization's data product types.",
)


OUTPUT_PORT_TYPES_PATH = "/api/settings/output-port-types"


@output_port_types_app.command("get")
def get_output_port_types(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show the organization's output port types.

    The types with their access request rules (enabled ones first, in dropdown order), the output
    port types each data product type offers, and whether only the enabled types are allowed.
    `legacy: true` means the organization has not changed them yet; the document then shows the
    settings that apply today. `--output yaml` prints the document `put` takes.
    """
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data = get_client().http.get_json(OUTPUT_PORT_TYPES_PATH)
        if fmt != OutputFormat.table:
            print_data(data, fmt)
            return

        table = Table()
        table.add_column("id", style="cyan")
        table.add_column("label")
        table.add_column("enabled")
        table.add_column("access requests")
        table.add_column("id pattern")
        for type_ in data.get("outputPortTypes") or []:
            table.add_row(
                type_.get("id", ""),
                type_.get("label") or "",
                "yes" if type_.get("enabled", True) else "no",
                (type_.get("accessRequests") or {}).get("mode") or "default",
                type_.get("outputPortIdPattern") or "",
            )
        console.print(table)
        notes = []
        if data.get("legacy"):
            notes.append("legacy: not changed by the organization yet; these are the settings that apply today")
        if data.get("onlyListedTypes"):
            notes.append("only the enabled types are allowed")
        for supported in data.get("supportedOutputPortTypes") or []:
            dp_type = supported.get("dataProductType") or ""
            types = supported.get("outputPortTypes") or []
            notes.append(f"data product type {dp_type}: {', '.join(types) or 'none'}")
        for note in notes:
            console.print(f"[dim]{note}[/dim]")
    except Exception as e:
        handle_error(e)


@output_port_types_app.command("put")
def put_output_port_types(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="JSON or YAML file with the body (use - for stdin).")
    ] = ...,
) -> None:
    """Replace the organization's output port types.

    The body is the document `get --output yaml` prints. The order of the enabled
    `outputPortTypes` is the dropdown order. Own types not in the file are removed; a default type
    not in the file stays, disabled. `legacy` is read-only and ignored.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        _put_yaml_or_json(get_client(), OUTPUT_PORT_TYPES_PATH, file)
        print_success("Output port types saved.")
    except Exception as e:
        handle_error(e)


@output_port_types_app.command("delete")
def delete_output_port_types() -> None:
    """Drop the organization's output port type settings and use the defaults again.

    The output port types and rules that applied before apply again, including the output port
    type list of the customization YAML.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        get_client().http.delete(OUTPUT_PORT_TYPES_PATH)
        print_success("Output port type settings deleted; the defaults apply again.")
    except Exception as e:
        handle_error(e)


settings_app.add_typer(
    output_port_types_app,
    name="output-port-types",
    help="Get, set or reset the organization's output port types.",
)
