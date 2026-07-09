"""Schemas commands."""

from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import print_success

schemas_app = typer.Typer(no_args_is_help=True)


class SchemaSpec(str, Enum):
    odcs = "odcs"
    odps = "odps"


@schemas_app.command("get")
def get_schema(
    spec: Annotated[
        SchemaSpec,
        typer.Argument(help="The specification: odcs (data contracts) or odps (data products)."),
    ],
    version: Annotated[
        Optional[str],
        typer.Option(
            "--version", "-v", help="Pin a specification version, e.g. 3.1.0. Defaults to the current version."
        ),
    ] = None,
    custom: Annotated[
        bool,
        typer.Option("--custom", help="Compose the organization's customization overlay onto the base schema."),
    ] = False,
    out_file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Write the schema to this file. Defaults to stdout."),
    ] = None,
) -> None:
    """Get the JSON Schema that ODCS or ODPS documents validate against."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        schema_json, served_version = client.get_schema(spec.value, version=version, custom=custom)
        if out_file is not None:
            out_file.write_text(schema_json)
            suffix = f" (version {served_version})" if served_version else ""
            print_success(f"Schema written to {out_file}{suffix}.")
        else:
            # Raw print (no Rich formatting) so redirecting and piping stays byte-faithful.
            print(schema_json)
    except Exception as e:
        handle_error(e)
