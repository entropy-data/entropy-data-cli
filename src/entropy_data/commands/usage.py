"""Usage commands (OpenTelemetry traces)."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.listing import (
    AllOption,
    Listing,
    PageOption,
    SinceOption,
    TimeRange,
    UntilOption,
    fetch_traces,
    limit_option,
    print_listing,
)
from entropy_data.output import OutputFormat, print_success
from entropy_data.util import read_body

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
    since: SinceOption = None,
    until: UntilOption = None,
    page: PageOption = 0,
    limit: limit_option(100) = 100,
    all_pages: AllOption = False,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List usage traces (spans by start time, newest first) as OTLP/JSON."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    time_range = TimeRange.parse(since, until)
    try:
        params = {}
        if scope_name:
            params["scopeName"] = scope_name
        if data_product_id:
            params["dataProductId"] = data_product_id
        if data_contract_id:
            params["dataContractId"] = data_contract_id
        client = get_client()
        listing = Listing(params, time_range, page=page, limit=limit, all_pages=all_pages)
        data, has_next = fetch_traces(client, RESOURCE_PATH, listing)
        print_listing(data, RESOURCE_TYPE, fmt, has_next, page)
    except Exception as e:
        handle_error(e)


@usage_app.command("submit")
def submit_usage(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="JSON or YAML file with OTLP/JSON traces (use - for stdin).")
    ] = ...,
) -> None:
    """Submit OpenTelemetry traces in OTLP/JSON format."""
    from entropy_data.cli import get_client, handle_error

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
    from entropy_data.cli import get_client, handle_error

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
