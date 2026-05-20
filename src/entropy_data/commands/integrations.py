"""Integrations commands.

Manage native data-platform integrations (Snowflake, Databricks, BigQuery, …):
list configured integrations, inspect their decrypted configuration as YAML,
view run history, and trigger or cancel a manual ingestion run.

The API path key uses the integration's UUID. For convenience these commands
accept either a UUID or the integration's user-facing identifier (`externalId`
or display `name`); the lookup happens client-side via list + filter.
"""

from __future__ import annotations

import re
import sys
import time
from datetime import datetime, timedelta
from typing import Annotated, Optional

import typer

from entropy_data.client import ApiError, EntropyDataClient
from entropy_data.output import (
    OutputFormat,
    print_resource,
    print_resource_list,
    print_success,
)

integrations_app = typer.Typer(no_args_is_help=True)

RESOURCE_PATH = "integrations"
RESOURCE_TYPE = "integrations"
RUN_RESOURCE_TYPE = "integration-runs"

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _resolve_ingestion_id(client: EntropyDataClient, identifier: str) -> str:
    """Accept a UUID, externalId, or display name; return the integration's UUID.

    Lists once and filters in-process — fine because integrations are few per org
    (typically a handful). If the identifier matches more than one integration,
    raises with the candidate list so the user can disambiguate.
    """
    if _UUID_RE.match(identifier):
        return identifier
    integrations, _ = client.list_resources(RESOURCE_PATH)
    matches = [i for i in integrations if i.get("externalId") == identifier or i.get("name") == identifier]
    if not matches:
        raise typer.BadParameter(
            f"No integration found with externalId or name '{identifier}'. "
            f"Run 'entropy-data integrations list' to see configured integrations."
        )
    if len(matches) > 1:
        listing = "\n".join(f"  - {i['externalId']} (name: '{i['name']}', id: {i['ingestionId']})" for i in matches)
        raise typer.BadParameter(
            f"Identifier '{identifier}' matches multiple integrations; pass the ingestionId instead:\n{listing}"
        )
    return matches[0]["ingestionId"]


@integrations_app.command("list")
def list_integrations(
    source: Annotated[
        Optional[str], typer.Option("--source", help="Filter by source platform (snowflake, databricks, …).")
    ] = None,
    team: Annotated[
        Optional[str],
        typer.Option("--team", help="Filter to integrations owned by a specific team (team externalId)."),
    ] = None,
    enabled: Annotated[
        Optional[bool], typer.Option("--enabled/--disabled", help="Filter by schedule-enabled state.")
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List integrations."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params: dict = {}
        if source:
            params["source"] = source
        if team:
            params["owningTeamExternalId"] = team
        if enabled is not None:
            params["enabled"] = "true" if enabled else "false"
        data, _ = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@integrations_app.command("get")
def get_integration(
    identifier: Annotated[
        str,
        typer.Argument(help="Integration UUID, externalId, or display name."),
    ],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a single integration with its most recent run."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        ingestion_id = _resolve_ingestion_id(client, identifier)
        data = client.get_resource(RESOURCE_PATH, ingestion_id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@integrations_app.command("configuration")
def get_configuration(
    identifier: Annotated[
        str,
        typer.Argument(help="Integration UUID, externalId, or display name."),
    ],
) -> None:
    """Print the integration's decrypted configuration as YAML.

    Credentials are stored separately and are never returned by this command.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        ingestion_id = _resolve_ingestion_id(client, identifier)
        # The configuration endpoint returns YAML (text/yaml). Use the session directly
        # since the typed helpers all assume JSON.
        response = client.session.get(
            f"{client.base_url}/api/{RESOURCE_PATH}/{ingestion_id}/configuration",
            timeout=30,
        )
        response.raise_for_status()
        sys.stdout.write(response.text)
        if not response.text.endswith("\n"):
            sys.stdout.write("\n")
    except Exception as e:
        handle_error(e)


@integrations_app.command("runs")
def list_runs(
    identifier: Annotated[
        str,
        typer.Argument(help="Integration UUID, externalId, or display name."),
    ],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum number of runs to return.")] = 50,
    status: Annotated[
        Optional[str],
        typer.Option("--status", help="Filter by status (RUNNING, SUCCESS, FAILED, CANCELLED)."),
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List past runs for an integration, most recent first."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        ingestion_id = _resolve_ingestion_id(client, identifier)
        params: dict = {"limit": limit}
        if status:
            params["status"] = status
        data, _ = client.list_resources(f"{RESOURCE_PATH}/{ingestion_id}/runs", params=params)
        print_resource_list(data, RUN_RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@integrations_app.command("run")
def trigger_run(
    identifier: Annotated[
        str,
        typer.Argument(help="Integration UUID, externalId, or display name."),
    ],
    wait: Annotated[
        bool,
        typer.Option(
            "--wait",
            help="Wait for the run to reach a terminal status (SUCCESS, FAILED, CANCELLED).",
        ),
    ] = False,
    timeout: Annotated[
        int,
        typer.Option(
            "--timeout",
            help="With --wait: maximum seconds to wait before giving up. Default 3600 (1h).",
        ),
    ] = 3600,
    poll_interval: Annotated[
        int,
        typer.Option(
            "--poll-interval",
            help="With --wait: seconds between polls. Default 10.",
        ),
    ] = 10,
) -> None:
    """Trigger a manual ingestion run.

    Returns immediately by default (fire-and-forget). With --wait the command polls
    the run history until the new run reaches a terminal status, then exits with 0
    on SUCCESS or 1 on FAILED / CANCELLED.
    """
    from entropy_data.cli import error_console, get_client, handle_error

    try:
        client = get_client()
        ingestion_id = _resolve_ingestion_id(client, identifier)
        result = client.post_action_json(RESOURCE_PATH, ingestion_id, "run")
        scheduled_at = result.get("scheduledAt")
        deferred = result.get("deferred", False)

        if deferred:
            print_success("Run scheduled — will be picked up on the next due-check cycle (~5 minutes).")
        else:
            print_success(f"Run scheduled at {scheduled_at}.")

        if wait:
            _wait_for_run(client, ingestion_id, scheduled_at, timeout, poll_interval)
    except ApiError as e:
        if getattr(e, "status_code", None) == 409:
            error_console.print(
                "[red]Conflict: An ingestion run is already in progress for this integration. "
                "Use 'entropy-data integrations cancel ...' to abort it, or wait for it to finish.[/red]"
            )
            raise SystemExit(1)
        handle_error(e)
    except Exception as e:
        handle_error(e)


@integrations_app.command("cancel")
def cancel_run(
    identifier: Annotated[
        str,
        typer.Argument(help="Integration UUID, externalId, or display name."),
    ],
) -> None:
    """Cancel the currently running ingestion."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        ingestion_id = _resolve_ingestion_id(client, identifier)
        client.post_action(RESOURCE_PATH, ingestion_id, "cancel")
        print_success("Cancellation requested.")
    except Exception as e:
        handle_error(e)


# ─── --wait polling helper ───────────────────────────────────────────────────


def _parse_instant(value: str) -> datetime:
    """Parse an ISO-8601 instant; tolerate trailing 'Z'."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _wait_for_run(
    client: EntropyDataClient,
    ingestion_id: str,
    scheduled_at: str,
    timeout_sec: int,
    poll_interval: int,
) -> None:
    """Poll the run history until a run for this trigger reaches a terminal status."""
    from entropy_data.cli import error_console

    scheduled_dt = _parse_instant(scheduled_at)
    # Allow 5-second slack because the scheduler may stamp startedAt before scheduledAt
    # on a busy host (clock drift / pre-emption).
    threshold = scheduled_dt - timedelta(seconds=5)
    deadline = time.monotonic() + timeout_sec
    last_status: Optional[str] = None

    while time.monotonic() < deadline:
        runs, _ = client.list_resources(f"{RESOURCE_PATH}/{ingestion_id}/runs", params={"limit": 5})
        target = next(
            (r for r in runs if _parse_instant(r["startedAt"]) >= threshold),
            None,
        )
        if target is not None:
            if target["status"] != last_status:
                print(
                    f"Run {target['ingestionRunId']}: {target['status']} — "
                    f"{target['assetsProcessed']} assets processed "
                    f"(created={target['assetsCreated']}, updated={target['assetsUpdated']}, "
                    f"deleted={target['assetsDeleted']})"
                )
                last_status = target["status"]
            if target["status"] == "SUCCESS":
                return
            if target["status"] in ("FAILED", "CANCELLED"):
                error_console.print(f"[red]Run ended with status {target['status']}.[/red]")
                if target.get("message"):
                    error_console.print(f"[red]{target['message']}[/red]")
                raise SystemExit(1)
        time.sleep(poll_interval)

    error_console.print(
        f"[yellow]Timed out after {timeout_sec}s — run did not finish. "
        "It may still complete; check 'entropy-data integrations runs <name>'.[/yellow]"
    )
    raise SystemExit(2)
