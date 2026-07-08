"""Classification schemes commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

classifications_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "classification-schemes"
RESOURCE_TYPE = "classification-schemes"


@classifications_app.command("list")
def list_classifications(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all classification schemes."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources(RESOURCE_PATH)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next)
    except Exception as e:
        handle_error(e)


@classifications_app.command("get")
def get_classification(
    scheme_external_id: Annotated[
        str, typer.Argument(help="Classification scheme external ID (e.g. 'classification').")
    ],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a classification scheme by external ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, scheme_external_id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@classifications_app.command("put")
def put_classification(
    scheme_external_id: Annotated[
        str, typer.Argument(help="Classification scheme external ID (e.g. 'classification').")
    ],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a classification scheme."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, scheme_external_id, body)
        print_success(f"Classification scheme '{scheme_external_id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@classifications_app.command("delete")
def delete_classification(
    scheme_external_id: Annotated[
        str, typer.Argument(help="Classification scheme external ID (e.g. 'classification').")
    ],
) -> None:
    """Delete a classification scheme."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, scheme_external_id)
        print_success(f"Classification scheme '{scheme_external_id}' deleted.")
    except Exception as e:
        handle_error(e)
