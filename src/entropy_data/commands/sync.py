"""`sync` — copy selected portable org state from a source instance to a target instance.

Mechanism: export the source into a staged directory, then import that directory
into the target. Both halves reuse the ``export dir`` / ``apply dir`` engine, so
the staged artifact is auditable and identical to a manual ``export`` + ``import``.

``sync`` copies nothing by default: the resources to copy must be named explicitly
via ``--include`` so a run only touches what the operator intends.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.commands.import_export import _parse_csv, print_plan
from entropy_data.output import console, error_console
from entropy_data.resources import RESOURCE_ORDER, select_resources
from entropy_data.sync import apply_dir, export_dir, plan_apply


def sync_command(
    source: Annotated[str, typer.Option("--source", help="Source named connection to copy state from.")],
    target: Annotated[str, typer.Option("--target", help="Target named connection to write state onto.")],
    include: Annotated[
        Optional[str],
        typer.Option("--include", help="Comma-separated resources to sync (required; sync copies nothing by default)."),
    ] = None,
    exclude: Annotated[
        Optional[str], typer.Option("--exclude", help="Comma-separated resources to drop from --include.")
    ] = None,
    prune: Annotated[bool, typer.Option("--prune", help="Delete target resources absent from the source.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the prune confirmation prompt.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print planned create/update/(prune) counts; write nothing to the target.")
    ] = False,
    keep: Annotated[
        Optional[Path], typer.Option("--keep", help="Retain the staged export in this directory (else a temp dir).")
    ] = None,
) -> None:
    """Copy the selected portable organization state from a source connection to a target connection."""
    from entropy_data.cli import client_for_connection, handle_error

    included = _parse_csv(include)
    if not included:
        known = ", ".join(r.name for r in RESOURCE_ORDER)
        error_console.print(
            "[red]Nothing to sync: --include is required (sync copies nothing by default).[/red]\n"
            f"Name the resources to sync, e.g. --include teams,policies. Known resources: {known}"
        )
        raise typer.Exit(2)

    try:
        resources = select_resources(included, _parse_csv(exclude))
        source_client = client_for_connection(source)
        target_client = client_for_connection(target)
    except Exception as e:
        handle_error(e)
        return

    if keep is not None:
        staged = keep
        staged.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        staged = Path(tempfile.mkdtemp(prefix="entropy-data-sync-"))
        cleanup = True

    try:
        console.print(f"[bold]Exporting source into {staged}[/bold]")
        export_result = export_dir(source_client, staged, resources)
        console.print(f"\n[bold]Export:[/bold] {export_result.ok} exported, {export_result.fail} failed")

        if dry_run:
            print_plan(plan_apply(target_client, staged, resources, prune=prune))
            if export_result.fail > 0:
                raise typer.Exit(1)
            return

        if prune and not yes:
            console.print("[yellow]--prune will DELETE target resources absent from the source.[/yellow]")
            if not typer.confirm("Proceed with prune?"):
                console.print("Aborted.")
                raise typer.Exit(1)

        console.print("\n[bold]Applying to target[/bold]")
        import_result = apply_dir(target_client, staged, resources, prune=prune)
        console.print(
            f"\n[bold]Summary:[/bold] {import_result.ok} succeeded, {import_result.fail} failed "
            f"({export_result.fail} export failures)"
        )
        if import_result.fail > 0 or export_result.fail > 0:
            raise typer.Exit(1)
    finally:
        if cleanup:
            shutil.rmtree(staged, ignore_errors=True)
        elif not dry_run:
            error_console.print(f"Staged export retained at {staged}")
