"""Insights commands (EXPERIMENTAL): dashboards and the semantic models their metrics come from.

A dashboard is a Perses dashboard (kind: PersesDashboard) whose panels show metrics from semantic
models. A semantic model is an Ossie document: datasets on data product tables, and the metrics
computed from them. Both APIs are experimental and may change.
"""

from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

insights_app = typer.Typer(no_args_is_help=True)
dashboards_app = typer.Typer(no_args_is_help=True)
semantic_models_app = typer.Typer(no_args_is_help=True)

DASHBOARDS_PATH = "insights/dashboards"
DASHBOARDS_TYPE = "insights-dashboards"
MODELS_PATH = "insights/semantic-models"
MODELS_TYPE = "insights-semantic-models"


class RemovedMetrics(str, Enum):
    remove = "remove"
    keep = "keep"


def _write_or_print(text: str, out_file: Optional[Path], what: str) -> None:
    if out_file is not None:
        out_file.write_text(text)
        print_success(f"{what} written to {out_file}.")
    else:
        print(text)


def _align_id(body: dict, id: str, label: str, get, set_) -> dict:
    """Fill the id field from the path when the file leaves it out; refuse a different one."""
    current = get(body)
    if current not in (None, id):
        raise typer.BadParameter(f"The file's {label} '{current}' does not match '{id}'.")
    return set_(body, id)


# Dashboards


@dashboards_app.command("list")
def list_dashboards(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the dashboards the API key sees, the Overview first."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data, has_next = get_client().list_resources(DASHBOARDS_PATH)
        print_resource_list(data, DASHBOARDS_TYPE, fmt, has_next_page=has_next)
    except Exception as e:
        handle_error(e)


@dashboards_app.command("get")
def get_dashboard(
    id: Annotated[str, typer.Argument(help="Dashboard ID (metadata.name).")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a dashboard."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        print_resource(get_client().get_resource(DASHBOARDS_PATH, id), DASHBOARDS_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@dashboards_app.command("yaml")
def yaml_dashboard(
    id: Annotated[str, typer.Argument(help="Dashboard ID (metadata.name).")],
    out_file: Annotated[
        Optional[Path], typer.Option("--file", "-f", help="Write YAML to this file. Defaults to stdout.")
    ] = None,
) -> None:
    """Get a dashboard as the YAML stored for it."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _validate_resource_id

    try:
        _validate_resource_id(id)
        text = get_client().http.get_text(f"/api/{DASHBOARDS_PATH}/{id}/dashboard.yaml")
        _write_or_print(text, out_file, f"Dashboard '{id}'")
    except Exception as e:
        handle_error(e)


@dashboards_app.command("put")
def put_dashboard(
    id: Annotated[str, typer.Argument(help="Dashboard ID (metadata.name).")],
    file: Annotated[
        Path, typer.Option("--file", "-f", help="PersesDashboard as JSON or YAML (use - for stdin).")
    ] = ...,
) -> None:
    """Add or replace a dashboard.

    The file is a Perses dashboard (apiVersion perses.dev/v1alpha1, kind PersesDashboard), as
    'insights dashboards yaml' prints it. A file without metadata.name takes the ID.
    """
    from entropy_data.cli import get_client, handle_error

    def set_name(body: dict, value: str) -> dict:
        return {**body, "metadata": {**(body.get("metadata") or {}), "name": value}}

    try:
        body = _align_id(
            read_body(file), id, "metadata.name", lambda b: (b.get("metadata") or {}).get("name"), set_name
        )
        location = get_client().put_resource(DASHBOARDS_PATH, id, body)
        print_success(f"Dashboard '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@dashboards_app.command("delete")
def delete_dashboard(
    id: Annotated[str, typer.Argument(help="Dashboard ID (metadata.name).")],
) -> None:
    """Delete a dashboard. The built-in Overview cannot be deleted."""
    from entropy_data.cli import get_client, handle_error

    try:
        get_client().delete_resource(DASHBOARDS_PATH, id)
        print_success(f"Dashboard '{id}' deleted.")
    except Exception as e:
        handle_error(e)


# Semantic models


@semantic_models_app.command("list")
def list_semantic_models(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the semantic models, the built-in entropy_data_marketplace_analytics first."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        data, has_next = get_client().list_resources(MODELS_PATH)
        print_resource_list(data, MODELS_TYPE, fmt, has_next_page=has_next)
    except Exception as e:
        handle_error(e)


@semantic_models_app.command("get")
def get_semantic_model(
    name: Annotated[str, typer.Argument(help="Semantic model name.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a semantic model with its datasets and metrics."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        print_resource(get_client().get_resource(MODELS_PATH, name), MODELS_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@semantic_models_app.command("yaml")
def yaml_semantic_model(
    name: Annotated[str, typer.Argument(help="Semantic model name.")],
    out_file: Annotated[
        Optional[Path], typer.Option("--file", "-f", help="Write YAML to this file. Defaults to stdout.")
    ] = None,
) -> None:
    """Get a semantic model as a standalone Ossie YAML document, the way other Ossie tools read it."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _validate_resource_id

    try:
        _validate_resource_id(name)
        text = get_client().http.get_text(f"/api/{MODELS_PATH}/{name}/model.yaml")
        _write_or_print(text, out_file, f"Semantic model '{name}'")
    except Exception as e:
        handle_error(e)


@semantic_models_app.command("put")
def put_semantic_model(
    name: Annotated[str, typer.Argument(help="Semantic model name.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="Ossie document as JSON or YAML (use - for stdin).")] = ...,
    removed_metrics: Annotated[
        Optional[RemovedMetrics],
        typer.Option(
            "--removed-metrics",
            help=(
                "When the update removes metrics that dashboards show: 'remove' takes those widgets off their "
                "dashboards, 'keep' leaves them showing that the metric no longer exists. Without it, such an "
                "update is refused."
            ),
        ),
    ] = None,
) -> None:
    """Add or replace a semantic model with a complete Ossie document.

    Datasets name the data product table their rows come from in a custom extension with
    vendor_name ENTROPY_DATA. A file without `name` takes the model name.
    """
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _validate_resource_id

    try:
        _validate_resource_id(name)
        body = _align_id(read_body(file), name, "name", lambda b: b.get("name"), lambda b, v: {**b, "name": v})
        params = {"removedMetrics": removed_metrics.value} if removed_metrics else None
        response = get_client().http.put_json(f"/api/{MODELS_PATH}/{name}", body, params=params)
        print_success(f"Semantic model '{name}' saved.")
        print_link(response.location_html)
    except Exception as e:
        handle_error(e)


@semantic_models_app.command("delete")
def delete_semantic_model(
    name: Annotated[str, typer.Argument(help="Semantic model name.")],
) -> None:
    """Delete a semantic model. Dashboard widgets that show its metrics then say the metric no longer exists."""
    from entropy_data.cli import get_client, handle_error

    try:
        get_client().delete_resource(MODELS_PATH, name)
        print_success(f"Semantic model '{name}' deleted.")
    except Exception as e:
        handle_error(e)


insights_app.add_typer(dashboards_app, name="dashboards", help="Manage Insights dashboards (Perses format).")
insights_app.add_typer(
    semantic_models_app,
    name="semantic-models",
    help="Manage the semantic models (Ossie documents) that dashboard metrics come from.",
)
