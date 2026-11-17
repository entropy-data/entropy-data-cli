"""Custom quality checks commands.

A custom quality check is a reusable check an organization defines once and data contracts refer
to. The API serves each check's file as saved, in the format datacontract-cli reads from a local
checks folder.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import print_success

custom_quality_checks_app = typer.Typer(no_args_is_help=True)


@custom_quality_checks_app.command("get")
def get_custom_quality_check(
    id: Annotated[str, typer.Argument(help="Custom quality check ID.")],
    out_file: Annotated[
        Optional[Path],
        typer.Option(
            "--file",
            "-f",
            help="Write the check to this file, e.g. into the checks folder datacontract-cli reads. Defaults to stdout.",
        ),
    ] = None,
) -> None:
    """Get a custom quality check as its YAML file, exactly as saved."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _validate_resource_id

    try:
        _validate_resource_id(id)
        text = get_client().http.get_text(f"/api/custom-quality-checks/{id}/check.yaml")
        if out_file is not None:
            out_file.write_text(text)
            print_success(f"Custom quality check '{id}' written to {out_file}.")
        else:
            print(text)
    except Exception as e:
        handle_error(e)
