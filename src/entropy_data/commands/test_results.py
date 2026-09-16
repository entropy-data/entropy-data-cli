"""Test results commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

test_results_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "test-results"
RESOURCE_TYPE = "test-results"


@test_results_app.command("list")
def list_test_results(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    data_contract_id: Annotated[
        Optional[str], typer.Option("--data-contract-id", help="Filter by data contract.")
    ] = None,
    branch: Annotated[
        Optional[str],
        typer.Option(
            "--branch", "-b", help="Only the runs on this branch of the data contract. Needs --data-contract-id."
        ),
    ] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all test results."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    if branch and not data_contract_id:
        raise typer.BadParameter("--branch needs --data-contract-id.", param_hint="--branch")
    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {"p": page}
        if data_contract_id:
            params["dataContractId"] = data_contract_id
        if branch:
            params["branch"] = branch
        data, has_next = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@test_results_app.command("get")
def get_test_result(
    id: Annotated[str, typer.Argument(help="Test result ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a test result by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@test_results_app.command("publish")
def publish_test_results(
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
    data_contract_id: Annotated[
        Optional[str],
        typer.Option(
            "--data-contract-id", help="The data contract whose branch the results belong to. Needs --branch."
        ),
    ] = None,
    branch: Annotated[
        Optional[str],
        typer.Option(
            "--branch",
            "-b",
            help="Publish the results onto this branch of the data contract instead of the data contract.",
        ),
    ] = None,
) -> None:
    """Publish test results."""
    from entropy_data.cli import get_client, handle_error

    if (branch is None) != (data_contract_id is None):
        raise typer.BadParameter("--branch and --data-contract-id go together.", param_hint="--branch")
    try:
        body = read_body(file)
        client = get_client()
        if branch:
            from entropy_data.commands.datacontract_branches import branch_path

            location = client.post_resource(f"{branch_path(data_contract_id, branch)}/test-results", body)
            print_success(f"Test results published onto branch '{branch}' of data contract '{data_contract_id}'.")
        else:
            location = client.post_resource(RESOURCE_PATH, body)
            print_success("Test results published.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@test_results_app.command("delete")
def delete_test_result(
    id: Annotated[str, typer.Argument(help="Test result ID.")],
) -> None:
    """Delete a test result."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Test result '{id}' deleted.")
    except Exception as e:
        handle_error(e)
