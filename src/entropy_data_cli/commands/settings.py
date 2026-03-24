"""Settings commands."""

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data_cli.output import OutputFormat, console, print_success

settings_app = typer.Typer(no_args_is_help=True)


@settings_app.command("get-customization")
def get_customization(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get organization customization settings."""
    from entropy_data_cli.cli import get_client, get_output_format, handle_error
    from entropy_data_cli.client import REQUEST_TIMEOUT, _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        accept = "application/json" if fmt == OutputFormat.json else "application/yaml"
        response = client.session.get(
            f"{client.base_url}/api/settings/customization",
            headers={"Accept": accept},
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        if fmt == OutputFormat.json:
            console.print_json(json.dumps(response.json()))
        else:
            console.print(response.text)
    except Exception as e:
        handle_error(e)


@settings_app.command("put-customization")
def put_customization(
    file: Annotated[Path, typer.Option("--file", "-f", help="YAML or JSON file (use - for stdin).")] = ...,
) -> None:
    """Update organization customization settings."""
    from entropy_data_cli.cli import get_client, handle_error
    from entropy_data_cli.client import REQUEST_TIMEOUT, _raise_for_status

    try:
        if str(file) == "-":
            content = sys.stdin.read()
        else:
            content = file.read_text()

        client = get_client()
        # Detect content type from file extension or content
        is_json = str(file).endswith(".json") or content.lstrip().startswith("{")
        content_type = "application/json" if is_json else "application/yaml"
        response = client.session.put(
            f"{client.base_url}/api/settings/customization",
            data=content.encode(),
            headers={"Content-Type": content_type},
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success("Customization updated.")
    except Exception as e:
        handle_error(e)
