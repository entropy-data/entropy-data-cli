"""Import command for organization exports."""

import tempfile
import zipfile
from pathlib import Path
from typing import Annotated

import typer
import yaml

from entropy_data.client import ApiError
from entropy_data.output import console, error_console

import_app = typer.Typer(no_args_is_help=True)

# Import order respects resource dependencies:
# teams (parent→child), tags (→teams), definitions (→teams),
# assets (→teams), datacontracts (→teams, assets),
# dataproducts (→teams, datacontracts, assets), access (→dataproducts)
RESOURCE_ORDER = [
    ("teams", "teams"),
    ("tags", "tags"),
    ("definitions", "definitions"),
    ("assets", "assets"),
    ("datacontracts", "datacontracts"),
    ("dataproducts", "dataproducts"),
    ("access", "access"),
]


def _import_teams(teams_dir: Path, client) -> tuple[int, int]:
    """Import teams in topological order (parents before children), stripping members."""
    teams = {}
    for f in sorted(teams_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        data["members"] = []
        teams[data["id"]] = {"data": data, "parent": data.get("parent")}

    imported: set[str] = set()
    success_count = 0
    error_count = 0

    while len(imported) < len(teams):
        progress = False
        for tid, t in teams.items():
            if tid in imported:
                continue
            if t["parent"] is None or t["parent"] in imported:
                try:
                    client.put_resource("teams", tid, t["data"])
                    console.print(f"  [green]OK[/green]   {tid}")
                    success_count += 1
                except ApiError as e:
                    error_console.print(f"  [red]FAIL[/red] {tid}: {e}")
                    error_count += 1
                imported.add(tid)
                progress = True

        if not progress:
            remaining = set(teams.keys()) - imported
            error_console.print(f"  [red]ERROR: circular or broken parent references: {remaining}[/red]")
            error_count += len(remaining)
            break

    return success_count, error_count


def _import_simple(resource_dir: Path, api_path: str, client) -> tuple[int, int]:
    """Import resources from a directory using PUT."""
    success_count = 0
    error_count = 0

    for f in sorted(resource_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        resource_id = data["id"]
        try:
            client.put_resource(api_path, resource_id, data)
            console.print(f"  [green]OK[/green]   {resource_id}")
            success_count += 1
        except ApiError as e:
            error_console.print(f"  [red]FAIL[/red] {resource_id}: {e}")
            error_count += 1

    return success_count, error_count


@import_app.command("zip")
def import_zip(
    file: Annotated[Path, typer.Argument(help="Path to the export zip file.")],
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
        client = get_client()
    except Exception as e:
        handle_error(e)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = Path(tmpdir)
        console.print(f"Extracting {file}...")
        with zipfile.ZipFile(file) as zf:
            zf.extractall(export_dir)

        total_ok = 0
        total_fail = 0

        for directory, api_path in RESOURCE_ORDER:
            resource_dir = export_dir / directory
            if not resource_dir.is_dir():
                continue

            console.print(f"\n[bold]{api_path}[/bold]")

            if directory == "teams":
                ok, fail = _import_teams(resource_dir, client)
            else:
                ok, fail = _import_simple(resource_dir, api_path, client)

            total_ok += ok
            total_fail += fail

        console.print(f"\n[bold]Summary:[/bold] {total_ok} succeeded, {total_fail} failed")
        if total_fail > 0:
            raise typer.Exit(1)
