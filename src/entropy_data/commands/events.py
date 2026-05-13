"""Events commands."""

from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_data, print_resource_list

events_app = typer.Typer(no_args_is_help=True)


@events_app.command("poll")
def poll_events(
    last_event_id: Annotated[
        Optional[str], typer.Option("--last-event-id", help="Last event ID for incremental polling.")
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Poll for events."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_events(last_event_id=last_event_id)
        if fmt != OutputFormat.table:
            print_data(data, fmt)
        else:
            print_resource_list(data, "events", fmt)
    except Exception as e:
        handle_error(e)
