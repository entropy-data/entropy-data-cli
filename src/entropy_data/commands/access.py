"""Access (data usage agreements) commands."""

import uuid
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

access_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "access"
RESOURCE_TYPE = "access"


@access_app.command("list")
def list_access(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    provider_dataproduct: Annotated[
        Optional[str],
        typer.Option("--provider-dataproduct", help="Filter by provider data product ID."),
    ] = None,
    consumer_dataproduct: Annotated[
        Optional[str],
        typer.Option("--consumer-dataproduct", help="Filter by consumer data product ID."),
    ] = None,
    consumer_type: Annotated[
        Optional[str],
        typer.Option("--consumer-type", help="Filter by consumer type (e.g. team, user, dataProduct)."),
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all access agreements."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params: dict = {"p": page}
        if provider_dataproduct:
            params["providerDataProductId"] = provider_dataproduct
        if consumer_dataproduct:
            params["consumerDataProductId"] = consumer_dataproduct
        if consumer_type:
            params["consumerType"] = consumer_type
        data, has_next = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@access_app.command("get")
def get_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get an access agreement by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@access_app.command("put")
def put_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Access agreement '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@access_app.command("delete")
def delete_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Delete an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Access agreement '{id}' deleted.")
    except Exception as e:
        handle_error(e)


@access_app.command("approve")
def approve_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Approve an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        location = client.post_action(RESOURCE_PATH, id, "approve")
        print_success(f"Access agreement '{id}' approved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@access_app.command("reject")
def reject_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Reject an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        location = client.post_action(RESOURCE_PATH, id, "reject")
        print_success(f"Access agreement '{id}' rejected.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@access_app.command("cancel")
def cancel_access(
    id: Annotated[str, typer.Argument(help="Access agreement ID.")],
) -> None:
    """Cancel an access agreement."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        location = client.post_action(RESOURCE_PATH, id, "cancel")
        print_success(f"Access agreement '{id}' cancelled.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@access_app.command("request")
def request_access(
    data_product_id: Annotated[str, typer.Argument(help="Provider data product ID.")],
    output_port_id: Annotated[str, typer.Argument(help="Provider output port ID.")],
    purpose: Annotated[str, typer.Option("--purpose", help="Business justification for the access.")] = ...,
    consumer_team: Annotated[
        Optional[str],
        typer.Option("--consumer-team", help="Consumer team ID (request on behalf of a team)."),
    ] = None,
    consumer_user: Annotated[
        Optional[str],
        typer.Option("--consumer-user", help="Consumer user ID (request on behalf of a user)."),
    ] = None,
    consumer_dataproduct: Annotated[
        Optional[str],
        typer.Option("--consumer-dataproduct", help="Consumer data product ID (cross-product agreement)."),
    ] = None,
    roles: Annotated[
        Optional[str],
        typer.Option("--roles", help="Comma-separated list of roles to request (e.g. analyst,data_engineer)."),
    ] = None,
    id: Annotated[
        Optional[str],
        typer.Option("--id", help="Agreement ID. Auto-generated UUID if not provided."),
    ] = None,
) -> None:
    """Submit an access request for a provider data product output port.

    Creates a new access agreement in 'requested' state via PUT /api/access/{id}. Exactly
    one of --consumer-team / --consumer-user / --consumer-dataproduct must be specified.
    """
    from entropy_data.cli import get_client, handle_error
    from entropy_data.output import error_console

    consumer_count = sum(c is not None for c in (consumer_team, consumer_user, consumer_dataproduct))
    if consumer_count != 1:
        error_console.print(
            "[red]Error: provide exactly one of --consumer-team, --consumer-user, or --consumer-dataproduct.[/red]"
        )
        raise SystemExit(2)

    agreement_id = id or str(uuid.uuid4())
    consumer: dict = {}
    if consumer_team is not None:
        consumer["teamId"] = consumer_team
    if consumer_user is not None:
        consumer["userId"] = consumer_user
    if consumer_dataproduct is not None:
        consumer["dataProductId"] = consumer_dataproduct

    body: dict = {
        "id": agreement_id,
        "provider": {
            "dataProductId": data_product_id,
            "outputPortId": output_port_id,
        },
        "consumer": consumer,
        "info": {
            "purpose": purpose,
        },
    }
    if roles:
        body["roles"] = [r.strip() for r in roles.split(",") if r.strip()]

    try:
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, agreement_id, body)
        print_success(f"Access request '{agreement_id}' submitted.")
        print_link(location)
    except Exception as e:
        handle_error(e)
