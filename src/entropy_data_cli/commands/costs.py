"""Costs commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data_cli.output import OutputFormat, print_resource_list, print_success
from entropy_data_cli.util import read_body

costs_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "costs"
RESOURCE_TYPE = "costs"


@costs_app.command("list")
def list_costs(
    data_product_id: Annotated[str, typer.Option("--data-product-id", help="Data product ID to list costs for.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all costs of a data product."""
    from entropy_data_cli.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources(RESOURCE_PATH, params={"dataProductId": data_product_id})
        print_resource_list(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@costs_app.command("add")
def add_cost(
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Add a cost."""
    from entropy_data_cli.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        client.post_resource(RESOURCE_PATH, body)
        print_success("Cost added.")
    except Exception as e:
        handle_error(e)


@costs_app.command("delete")
def delete_cost(
    id: Annotated[str, typer.Argument(help="Cost ID.")],
) -> None:
    """Delete a cost."""
    from entropy_data_cli.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Cost '{id}' deleted.")
    except Exception as e:
        handle_error(e)
