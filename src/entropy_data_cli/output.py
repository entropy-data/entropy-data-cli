"""Output formatting for CLI results."""

import json
from enum import Enum

from rich.console import Console
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


class OutputFormat(str, Enum):
    table = "table"
    json = "json"


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
    "sourcesystems": [("ID", "id"), ("Name", "name"), ("Owner", "owner")],
    "definitions": [("ID", "id"), ("Name", "title"), ("Owner", "owner")],
    "certifications": [("ID", "id"), ("Name", "name"), ("Rank", "rank"), ("Tag", "tag")],
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
    if fmt == OutputFormat.json:
        console.print_json(json.dumps(data))
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
    data: list[dict], resource_type: str, fmt: OutputFormat, has_next_page: bool = False, page: int = 0
) -> None:
    """Print a list of resources."""
    if fmt == OutputFormat.json:
        console.print_json(json.dumps(data))
        return

    columns = RESOURCE_COLUMNS.get(resource_type, [])
    if not columns:
        console.print_json(json.dumps(data))
        return

    table = Table(show_header=True, title=f"{resource_type} (page {page})")
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
