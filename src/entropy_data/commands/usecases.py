"""Use cases commands (preview).

A use case is the value data products help create, in its own format (kind: UseCase), shaped like
an ODPS data product. It lists the data products assigned to it in `dataProducts`. The API answers
404 while Use Cases are not switched on for the organization (`useCasesEnabled` in
`organization features`).
"""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
import yaml

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success

usecases_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "usecases"
RESOURCE_TYPE = "usecases"


@usecases_app.command("list")
def list_usecases(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List use cases."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data, has_next = get_client().list_resources(RESOURCE_PATH, params={"p": page})
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@usecases_app.command("get")
def get_usecase(
    id: Annotated[str, typer.Argument(help="Use case ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a use case by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data = get_client().get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@usecases_app.command("yaml")
def yaml_usecase(
    id: Annotated[str, typer.Argument(help="Use case ID.")],
    out_file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Write YAML to this file. Defaults to stdout."),
    ] = None,
) -> None:
    """Get a use case as the YAML stored for it, comments included."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _validate_resource_id

    try:
        _validate_resource_id(id)
        text = get_client().http.get_text(f"/api/{RESOURCE_PATH}/{id}")
        if out_file is not None:
            out_file.write_text(text)
            print_success(f"Use case '{id}' written to {out_file}.")
        else:
            print(text)
    except Exception as e:
        handle_error(e)


@usecases_app.command("put")
def put_usecase(
    id: Annotated[str, typer.Argument(help="Use case ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="YAML or JSON file (use - for stdin).")] = ...,
) -> None:
    """Create or update a use case.

    A YAML file is sent as written, so the server stores it with its comments. A file without
    `dataProducts` keeps the data products assigned to the stored use case; a file with
    `dataProducts` replaces them, and an empty list unassigns them all.
    """
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _validate_resource_id

    try:
        _validate_resource_id(id)
        content = sys.stdin.read() if str(file) == "-" else file.read_text()
        body = yaml.safe_load(content)
        if not isinstance(body, dict):
            raise typer.BadParameter("The file must hold one use case (a mapping with apiVersion, kind, id, name).")
        if body.get("id") not in (None, id):
            raise typer.BadParameter(f"The file's id '{body['id']}' does not match the use case ID '{id}'.")
        client = get_client()
        is_json = str(file).endswith(".json") or content.lstrip().startswith("{")
        if is_json or "id" not in body:
            location = client.put_resource(RESOURCE_PATH, id, body)
        else:
            location = client.http.put_text(f"/api/{RESOURCE_PATH}/{id}", content).location_html
        print_success(f"Use case '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@usecases_app.command("delete")
def delete_usecase(
    id: Annotated[str, typer.Argument(help="Use case ID.")],
) -> None:
    """Delete a use case."""
    from entropy_data.cli import get_client, handle_error

    try:
        get_client().delete_resource(RESOURCE_PATH, id)
        print_success(f"Use case '{id}' deleted.")
    except Exception as e:
        handle_error(e)
