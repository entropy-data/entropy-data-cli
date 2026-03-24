"""Usage commands (OpenTelemetry traces)."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data_cli.output import OutputFormat, console, print_resource_list, print_success
from entropy_data_cli.util import read_body

usage_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "v1/traces"
RESOURCE_TYPE = "usage"


@usage_app.command("list")
def list_usage(
    scope_name: Annotated[
        Optional[str], typer.Option("--scope-name", help="Filter by scope name (e.g., 'usage').")
    ] = None,
    data_product_id: Annotated[
        Optional[str], typer.Option("--data-product-id", help="Filter by data product ID.")
    ] = None,
    data_contract_id: Annotated[
        Optional[str], typer.Option("--data-contract-id", help="Filter by data contract ID.")
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List usage traces."""
    from entropy_data_cli.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        params = {}
        if scope_name:
            params["scopeName"] = scope_name
        if data_product_id:
            params["dataProductId"] = data_product_id
        if data_contract_id:
            params["dataContractId"] = data_contract_id
        client = get_client()
        data, _ = client.list_resources(RESOURCE_PATH, params=params)
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(data))
        else:
            print_resource_list(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@usage_app.command("submit")
def submit_usage(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="JSON or YAML file with OTLP/JSON traces (use - for stdin).")
    ] = ...,
) -> None:
    """Submit OpenTelemetry traces in OTLP/JSON format."""
    from entropy_data_cli.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        client.post_resource(RESOURCE_PATH, body)
        print_success("Usage traces submitted.")
    except Exception as e:
        handle_error(e)


@usage_app.command("delete")
def delete_usage(
    scope_name: Annotated[Optional[str], typer.Option("--scope-name", help="Delete by scope name.")] = None,
    data_product_id: Annotated[
        Optional[str], typer.Option("--data-product-id", help="Delete by data product ID.")
    ] = None,
    data_contract_id: Annotated[
        Optional[str], typer.Option("--data-contract-id", help="Delete by data contract ID.")
    ] = None,
    span_id: Annotated[Optional[str], typer.Option("--span-id", help="Delete a specific trace by span ID.")] = None,
) -> None:
    """Delete usage traces."""
    from entropy_data_cli.cli import get_client, handle_error

    try:
        params = {}
        if scope_name:
            params["scopeName"] = scope_name
        if data_product_id:
            params["dataProductId"] = data_product_id
        if data_contract_id:
            params["dataContractId"] = data_contract_id
        if span_id:
            params["spanId"] = span_id
        client = get_client()
        result = client.delete_resources(RESOURCE_PATH, params=params or None)
        deleted = result.get("deletedCount", "unknown")
        print_success(f"Usage traces deleted ({deleted} deleted).")
    except Exception as e:
        handle_error(e)
