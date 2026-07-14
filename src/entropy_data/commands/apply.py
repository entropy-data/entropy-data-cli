"""`apply` — copy portable org state from a source instance to a target instance.

Mechanism: export the source into a staged directory, then import that directory
into the target. Both halves reuse the ``export dir`` / ``import dir`` engine, so
the staged artifact is auditable and identical to a manual ``export`` + ``import``.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.commands.import_export import _parse_csv, print_plan
from entropy_data.output import console, error_console
from entropy_data.resources import select_resources
from entropy_data.sync import export_dir, import_dir, plan_import


def apply_command(
    to: Annotated[str, typer.Option("--to", help="Target named connection to apply state onto.")],
    source: Annotated[
        Optional[str],
        typer.Option("--source", help="Source named connection (defaults to the global -c/--connection)."),
    ] = None,
    prune: Annotated[bool, typer.Option("--prune", help="Delete target resources absent from the source.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the prune confirmation prompt.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print planned create/update/(prune) counts; write nothing to the target.")
    ] = False,
    keep: Annotated[
        Optional[Path], typer.Option("--keep", help="Retain the staged export in this directory (else a temp dir).")
    ] = None,
    include: Annotated[Optional[str], typer.Option("--include", help="Comma-separated resources to include.")] = None,
    exclude: Annotated[Optional[str], typer.Option("--exclude", help="Comma-separated resources to exclude.")] = None,
) -> None:
    """Copy portable organization state from a source connection to a target connection."""
    from entropy_data.cli import client_for_connection, get_client, handle_error

    try:
        resources = select_resources(_parse_csv(include), _parse_csv(exclude))
        source_client = client_for_connection(source) if source else get_client()
        target_client = client_for_connection(to)
    except Exception as e:
        handle_error(e)
        return

    if keep is not None:
        staged = keep
        staged.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        staged = Path(tempfile.mkdtemp(prefix="entropy-data-apply-"))
        cleanup = True

    try:
        console.print(f"[bold]Exporting source into {staged}[/bold]")
        export_result = export_dir(source_client, staged, resources)
        console.print(f"\n[bold]Export:[/bold] {export_result.ok} exported, {export_result.fail} failed")

        if dry_run:
            print_plan(plan_import(target_client, staged, resources, prune=prune))
            if export_result.fail > 0:
                raise typer.Exit(1)
            return

        if prune and not yes:
            console.print("[yellow]--prune will DELETE target resources absent from the source.[/yellow]")
            if not typer.confirm("Proceed with prune?"):
                console.print("Aborted.")
                raise typer.Exit(1)

        console.print("\n[bold]Applying to target[/bold]")
        import_result = import_dir(target_client, staged, resources, prune=prune)
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
