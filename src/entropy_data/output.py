"""Output formatting for CLI results."""

import json
import sys
from enum import Enum

import yaml
from rich.console import Console
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    yaml = "yaml"


def print_data(data, fmt: OutputFormat) -> None:
    """Print data structured as JSON or YAML.

    Machine formats are written straight to stdout, NOT through the Rich
    console: Rich soft-wraps to the (80-col, non-TTY) console width and parses
    markup, which breaks long scalar values mid-token and yields invalid YAML
    when the output is piped or redirected to a file. ``width`` is set high so
    PyYAML itself does not fold long strings either.
    """
    if fmt == OutputFormat.yaml:
        sys.stdout.write(
            yaml.safe_dump(
                data,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
                width=4096,
            )
        )
    else:
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")


# Column definitions per resource type: list of (header, dict_key)
RESOURCE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "dataproducts": [("ID", "id"), ("Title", "name"), ("Status", "status"), ("Owner", "team.name")],
    "datacontracts": [("ID", "id"), ("Title", "name"), ("Version", "version"), ("Owner", "team.name")],
    "access": [
        ("ID", "id"),
        ("Purpose", "info.purpose"),
        ("Status", "info.status"),
        ("Active", "info.active"),
        ("Provider", "provider.dataProductId"),
        ("Consumer", "consumer.teamId"),
    ],
    "teams": [("ID", "id"), ("Name", "name"), ("Type", "type"), ("Parent", "parent")],
    "my-teams": [("ID", "id"), ("Name", "name"), ("Type", "type"), ("Parent", "parent"), ("Role", "role")],
    "sourcesystems": [("ID", "id"), ("Name", "name"), ("Owner", "owner")],
    "definitions": [("ID", "id"), ("Name", "title"), ("Owner", "owner")],
    "certifications": [("ID", "id"), ("Name", "name"), ("Rank", "rank"), ("Tag", "tag")],
    "policies": [("ID", "id"), ("Name", "name"), ("Status", "status")],
    "example-data": [("ID", "id"), ("Data Product", "dataProductId"), ("Schema", "schemaName")],
    "test-results": [("ID", "id"), ("Data Contract", "dataContractId"), ("Result", "result")],
    "events": [("ID", "id"), ("Type", "type"), ("Subject", "subject"), ("Time", "time")],
    "costs": [("ID", "id"), ("Data Product", "dataProductId"), ("Amount", "amount"), ("Currency", "currency")],
    "assets": [
        ("ID", "id"),
        ("Name", "info.name"),
        ("Type", "info.type"),
        ("Source", "info.source"),
        ("Owner", "info.owner"),
    ],
    "tags": [("ID", "id"), ("Owner", "info.owner"), ("Description", "info.description")],
    "organization-members": [("Email", "emailAddress"), ("User ID", "userId"), ("Role", "role")],
    "custom-team-roles": [
        ("Name", "name"),
        ("Rank", "rank"),
        ("Permissions", "permissions"),
        ("Description", "description"),
    ],
    "connectors": [("ID", "id"), ("Type", "info.type"), ("Version", "info.connectorVersion")],
    "integrations": [
        ("ID", "externalId"),
        ("Name", "name"),
        ("Source", "source"),
        ("Team", "assetOwnerTeamExternalId"),
        ("Enabled", "enabled"),
        ("Latest Run", "latestRun.status"),
    ],
    "integration-runs": [
        ("ID", "ingestionRunId"),
        ("Status", "status"),
        ("Started", "startedAt"),
        ("Completed", "completedAt"),
        ("Processed", "assetsProcessed"),
        ("Created", "assetsCreated"),
        ("Updated", "assetsUpdated"),
        ("Deleted", "assetsDeleted"),
    ],
    "git-credentials": [
        ("ID", "id"),
        ("External ID", "externalId"),
        ("Type", "gitConnectionType"),
        ("Host", "host"),
        ("Token Name", "tokenName"),
    ],
    "semantic-namespaces": [
        ("Namespace", "namespace"),
        ("Name", "name"),
        ("Team", "team"),
        ("Read-only", "read_only"),
    ],
    "semantic-concepts": [
        ("ID", "id"),
        ("Name", "name"),
        ("Kind", "kind"),
        ("Group", "group"),
        ("Status", "status"),
    ],
    "semantic-relationships": [
        ("ID", "id"),
        ("Name", "name"),
        ("Type", "type"),
        ("Multiplicity", "multiplicity"),
    ],
    "lineage": [
        ("Event Type", "eventType"),
        ("Event Time", "eventTime"),
        ("Job", "job.name"),
        ("Namespace", "job.namespace"),
    ],
    "usage": [],
}


def _get_nested(data: dict, key: str) -> str:
    """Get a nested value from a dict using dot notation."""
    parts = key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return ""
    return str(current) if current is not None else ""


def print_resource(data: dict, resource_type: str, fmt: OutputFormat) -> None:
    """Print a single resource."""
    if fmt != OutputFormat.table:
        print_data(data, fmt)
        return

    columns = RESOURCE_COLUMNS.get(resource_type, [])
    if columns:
        table = Table(show_header=True)
        for header, _ in columns:
            table.add_column(header)
        table.add_row(*[_get_nested(data, key) for _, key in columns])
        console.print(table)
    else:
        console.print_json(json.dumps(data))


def print_resource_list(
    data: list[dict],
    resource_type: str,
    fmt: OutputFormat,
    has_next_page: bool = False,
    page: int = 0,
    title: str | None = None,
) -> None:
    """Print a list of resources."""
    if fmt != OutputFormat.table:
        print_data(data, fmt)
        return

    columns = RESOURCE_COLUMNS.get(resource_type, [])
    if not columns:
        console.print_json(json.dumps(data))
        return

    table = Table(show_header=True, title=title or f"{resource_type} (page {page})")
    for header, _ in columns:
        table.add_column(header)
    for item in data:
        table.add_row(*[_get_nested(item, key) for _, key in columns])
    console.print(table)

    if has_next_page:
        console.print(f"\nMore results available. Use --page {page + 1} to see the next page.")


def print_success(message: str) -> None:
    console.print(f"[green]{message}[/green]")


def print_link(url: str) -> None:
    if url:
        console.print(f"Open {url}")


def print_error(message: str) -> None:
    error_console.print(f"[red]Error: {message}[/red]")
