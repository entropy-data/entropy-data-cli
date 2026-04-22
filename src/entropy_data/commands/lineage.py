"""Lineage commands (OpenLineage events)."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, console, print_resource_list, print_success
from entropy_data.util import read_body

lineage_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "v1/lineage"
RESOURCE_TYPE = "lineage"


@lineage_app.command("list")
def list_lineage(
    job_namespace: Annotated[Optional[str], typer.Option("--job-namespace", help="Filter by job namespace.")] = None,
    job_name: Annotated[Optional[str], typer.Option("--job-name", help="Filter by job name.")] = None,
    run_id: Annotated[Optional[str], typer.Option("--run-id", help="Filter by run ID.")] = None,
    event_type: Annotated[
        Optional[str],
        typer.Option("--event-type", help="Filter by event type (START, RUNNING, COMPLETE, ABORT, FAIL)."),
    ] = None,
    data_product_id: Annotated[
        Optional[str], typer.Option("--data-product-id", help="Filter by data product ID.")
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List OpenLineage events."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        params = {}
        if job_namespace:
            params["jobNamespace"] = job_namespace
        if job_name:
            params["jobName"] = job_name
        if run_id:
            params["runId"] = run_id
        if event_type:
            params["eventType"] = event_type
        if data_product_id:
            params["dataProductId"] = data_product_id
        client = get_client()
        data, _ = client.list_resources(RESOURCE_PATH, params=params)
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(data))
        else:
            print_resource_list(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@lineage_app.command("submit")
def submit_lineage(
    file: Annotated[
        Path, typer.Option("--file", "-f", help="JSON or YAML file with OpenLineage RunEvent (use - for stdin).")
    ] = ...,
    data_product_id: Annotated[
        Optional[str], typer.Option("--data-product-id", help="Data product ID to associate the event with.")
    ] = None,
    output_port_name: Annotated[
        Optional[str], typer.Option("--output-port-name", help="Output port name within the data product.")
    ] = None,
) -> None:
    """Submit an OpenLineage RunEvent."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        params = {}
        if data_product_id:
            params["dataProductId"] = data_product_id
        if output_port_name:
            params["outputPortName"] = output_port_name
        client = get_client()
        client.post_resource(RESOURCE_PATH, body, params=params or None)
        print_success("Lineage event submitted.")
    except Exception as e:
        handle_error(e)


@lineage_app.command("delete")
def delete_lineage(
    run_id: Annotated[Optional[str], typer.Option("--run-id", help="Delete by run ID.")] = None,
    job_namespace: Annotated[Optional[str], typer.Option("--job-namespace", help="Delete by job namespace.")] = None,
    job_name: Annotated[Optional[str], typer.Option("--job-name", help="Delete by job name.")] = None,
) -> None:
    """Delete OpenLineage events."""
    from entropy_data.cli import get_client, handle_error

    try:
        params = {}
        if run_id:
            params["runId"] = run_id
        if job_namespace:
            params["jobNamespace"] = job_namespace
        if job_name:
            params["jobName"] = job_name
        client = get_client()
        client.delete_resources(RESOURCE_PATH, params=params or None)
        print_success("Lineage events deleted.")
    except Exception as e:
        handle_error(e)
