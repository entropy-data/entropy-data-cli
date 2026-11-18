"""Search commands."""

import json
from enum import Enum
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, console, print_data

search_app = typer.Typer(no_args_is_help=True)


class SearchMode(str, Enum):
    DISCOVER = "DISCOVER"
    FIND = "FIND"
    GET_HELP = "GET_HELP"


@search_app.command("query")
def search_query(
    query: Annotated[str, typer.Argument(help="Search query.")],
    resource_type: Annotated[
        Optional[str],
        typer.Option(
            "--resource-type",
            "-t",
            help="Filter by resource type: DATA_PRODUCT, DATA_CONTRACT, SEMANTIC_CONCEPT, DATA_ASSET, DEFINITION, "
            "TEAM, TAG. Without it, the search covers data products and, when semantics are enabled, semantic "
            "concepts.",
        ),
    ] = None,
    mode: Annotated[
        Optional[SearchMode],
        typer.Option(
            "--mode",
            case_sensitive=False,
            help="Search mode instead of the one guessed from the query: DISCOVER (hybrid search with LLM "
            "reasoning), FIND (filtered search by id, title, ownership, ...), GET_HELP (explains business context "
            "and usage).",
        ),
    ] = None,
    diagnostics: Annotated[
        bool,
        typer.Option("--diagnostics", help="Add sources, userIntention and searchCriteria to the response."),
    ] = False,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Search across all resources."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {}
        if resource_type:
            params["resourceType"] = resource_type
        if mode:
            params["searchMode"] = mode.value
        if diagnostics:
            params["diagnostics"] = "true"
        data = client.search(query, **params)

        if fmt != OutputFormat.table:
            print_data(data, fmt)
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
