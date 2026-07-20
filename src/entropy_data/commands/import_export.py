"""Import, export, and apply commands for organization state.

`export dir` enumerates a source instance into a local YAML tree; `apply dir`
reconciles such a tree into a target instance (kubectl-apply style: the folder name
is the resource kind); `import zip` extracts an app-produced org-export zip and
applies it the same way. All share the engine in ``entropy_data.sync`` and the
resource definitions in ``entropy_data.resources``.
"""

import tempfile
import zipfile
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import console, error_console
from entropy_data.resources import RESOURCE_ORDER, select_resources
from entropy_data.sync import apply_dir, export_dir, plan_apply

import_app = typer.Typer(no_args_is_help=True)
export_app = typer.Typer(no_args_is_help=True)
apply_app = typer.Typer(no_args_is_help=True)

_APPLY_DIR_HELP = (
    "Apply an organization export directory tree to the connected instance, like "
    "`kubectl apply -f <dir>`.\n\n"
    "The folder name is the resource kind and each YAML file below it is one resource "
    "(addressed by the id in its body). Files carry no kind: field, so the enclosing folder "
    "is authoritative, and folders that are not a known kind are ignored. By default the whole "
    "tree is applied; narrow it with --include / --exclude.\n\n"
    "Resource kinds (folder names): " + ", ".join(r.name for r in RESOURCE_ORDER) + "."
)


def _parse_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def print_plan(plan) -> None:
    """Print a dry-run plan table of create/update/(prune) counts per resource."""
    if not plan.counts:
        console.print("Nothing to do.")
    else:
        console.print("\n[bold]Dry run — planned changes:[/bold]")
        for name, counts in plan.counts.items():
            parts = [f"create={counts.create}", f"update={counts.update}"]
            if counts.prune:
                parts.append(f"prune={counts.prune}")
            console.print(f"  {name}: {', '.join(parts)}")

    if plan.fail:
        error_console.print(
            f"\n[red]{plan.fail} resource(s) could not be listed on the target; "
            "the counts above are computed against an empty target and are not reliable.[/red]"
        )


@import_app.command("zip")
def import_zip(
    file: Annotated[Path, typer.Argument(help="Path to the export zip file.")],
    prune: Annotated[bool, typer.Option("--prune", help="Delete target resources absent from the import.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the prune confirmation prompt.")] = False,
    include: Annotated[Optional[str], typer.Option("--include", help="Comma-separated resources to include.")] = None,
    exclude: Annotated[Optional[str], typer.Option("--exclude", help="Comma-separated resources to exclude.")] = None,
) -> None:
    """Import an organization export zip file."""
    from entropy_data.cli import get_client, handle_error

    if not file.is_file():
        error_console.print(f"[red]Error: {file} not found[/red]")
        raise typer.Exit(1)

    if not zipfile.is_zipfile(file):
        error_console.print(f"[red]Error: {file} is not a valid zip file[/red]")
        raise typer.Exit(1)

    try:
        resources = select_resources(_parse_csv(include), _parse_csv(exclude))
        client = get_client()
    except Exception as e:
        handle_error(e)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        extracted = Path(tmpdir)
        console.print(f"Extracting {file}...")
        with zipfile.ZipFile(file) as zf:
            zf.extractall(extracted)

        _apply_tree(client, extracted, resources, prune, yes)


@apply_app.command("dir", help=_APPLY_DIR_HELP)
def apply_dir_command(
    path: Annotated[Path, typer.Argument(help="Directory holding the export YAML tree.")],
    prune: Annotated[bool, typer.Option("--prune", help="Delete target resources absent from the directory.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the prune confirmation prompt.")] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Print planned create/update/(prune) counts; write nothing.")
    ] = False,
    include: Annotated[Optional[str], typer.Option("--include", help="Comma-separated resources to include.")] = None,
    exclude: Annotated[Optional[str], typer.Option("--exclude", help="Comma-separated resources to exclude.")] = None,
) -> None:
    """Apply a local export directory tree to the connected instance (kubectl-apply style)."""
    from entropy_data.cli import get_client, handle_error

    if not path.is_dir():
        error_console.print(f"[red]Error: {path} is not a directory[/red]")
        raise typer.Exit(1)

    try:
        resources = select_resources(_parse_csv(include), _parse_csv(exclude))
        client = get_client()
    except Exception as e:
        handle_error(e)
        return

    if dry_run:
        plan = plan_apply(client, path, resources, prune=prune)
        print_plan(plan)
        if plan.fail > 0:
            raise typer.Exit(1)
        return

    _apply_tree(client, path, resources, prune, yes)


def _apply_tree(client, source: Path, resources, prune: bool, yes: bool) -> None:
    """Shared apply driver for both ``apply dir`` and ``import zip``; prompts before pruning."""
    if prune and not yes:
        console.print("[yellow]--prune will DELETE target resources absent from the source.[/yellow]")
        if not typer.confirm("Proceed with prune?"):
            console.print("Aborted.")
            raise typer.Exit(1)

    result = apply_dir(client, source, resources, prune=prune)
    console.print(f"\n[bold]Summary:[/bold] {result.ok} succeeded, {result.fail} failed")
    if result.fail > 0:
        raise typer.Exit(1)


@export_app.command("dir")
def export_dir_command(
    path: Annotated[Path, typer.Argument(help="Destination directory for the export YAML tree.")],
    include: Annotated[Optional[str], typer.Option("--include", help="Comma-separated resources to include.")] = None,
    exclude: Annotated[Optional[str], typer.Option("--exclude", help="Comma-separated resources to exclude.")] = None,
) -> None:
    """Export organization state to a local YAML tree (one file per resource)."""
    from entropy_data.cli import get_client, handle_error

    try:
        resources = select_resources(_parse_csv(include), _parse_csv(exclude))
        client = get_client()
    except Exception as e:
        handle_error(e)
        return

    path.mkdir(parents=True, exist_ok=True)
    result = export_dir(client, path, resources)
    console.print(f"\n[bold]Summary:[/bold] {result.ok} exported, {result.fail} failed")
    if result.fail > 0:
        raise typer.Exit(1)
