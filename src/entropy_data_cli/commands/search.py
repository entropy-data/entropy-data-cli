"""Search commands."""

import json
from typing import Annotated, Optional

import typer

from entropy_data_cli.output import OutputFormat, console

search_app = typer.Typer(no_args_is_help=True)


@search_app.command("query")
def search_query(
    query: Annotated[str, typer.Argument(help="Search query.")],
    resource_type: Annotated[
        Optional[str], typer.Option("--resource-type", "-t", help="Filter by resource type.")
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Search across all resources."""
    from entropy_data_cli.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {}
        if resource_type:
            params["resourceType"] = resource_type
        data = client.search(query, **params)

        if fmt == OutputFormat.json:
            console.print_json(json.dumps(data))
            return

        # Table output for search results
        results = data if isinstance(data, list) else data.get("results", data.get("items", [data]))
        if isinstance(results, list):
            from rich.table import Table

            table = Table(show_header=True, title="Search Results")
            table.add_column("Type")
            table.add_column("ID")
            table.add_column("Title")
            for item in results:
                table.add_row(
                    str(item.get("resourceType", item.get("type", ""))),
                    str(item.get("id", "")),
                    str(item.get("title", item.get("name", ""))),
                )
            console.print(table)
        else:
            console.print_json(json.dumps(data))
    except Exception as e:
        handle_error(e)
