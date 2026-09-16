"""Branches of a data contract: cut, author, review and merge a draft of an ODCS document."""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_data, print_resource, print_resource_list, print_success

branches_app = typer.Typer(no_args_is_help=True)
RESOURCE_TYPE = "datacontract-branches"
CHANGES_TYPE = "datacontract-branch-changes"
MERGE_ROUTES = ("land", "pull_request")

ID_HELP = "Data contract ID."
BRANCH_HELP = "Branch name."


def branches_path(data_contract_id: str) -> str:
    from entropy_data.client import _validate_resource_id

    _validate_resource_id(data_contract_id)
    return f"datacontracts/{data_contract_id}/branches"


def branch_path(data_contract_id: str, branch: str) -> str:
    from entropy_data.client import _validate_resource_id

    _validate_resource_id(branch)
    return f"{branches_path(data_contract_id)}/{branch}"


def read_text(file: Path) -> str:
    """The document as written, byte for byte: the branch keeps the author's formatting."""
    if str(file) == "-":
        return sys.stdin.read()
    return file.read_text()


@branches_app.command("list")
def list_branches(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the branches of a data contract."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(branches_path(id))
        print_resource_list(data, RESOURCE_TYPE, fmt, title=f"Branches of {id}")
    except Exception as e:
        handle_error(e)


@branches_app.command("create")
def create_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Cut a branch from a data contract. The branch starts as a copy of the data contract."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        response = client.session.put(f"{client.base_url}/api/{branch_path(id, branch)}", timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        print_success(f"Branch '{branch}' of data contract '{id}' created.")
        print_resource(response.json(), RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@branches_app.command("get")
def get_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show a branch: its version against main, what it changes, and whether it conflicts."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(branches_path(id), branch)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@branches_app.command("delete")
def delete_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
) -> None:
    """Delete a branch and everything authored on it. The data contract is untouched."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(branches_path(id), branch)
        print_success(f"Branch '{branch}' of data contract '{id}' deleted.")
    except Exception as e:
        handle_error(e)


@branches_app.command("yaml")
def yaml_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    out_file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Write YAML to this file. Defaults to stdout."),
    ] = None,
) -> None:
    """Get the branch's document as ODCS YAML."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    try:
        client = get_client()
        response = client.session.get(
            f"{client.base_url}/api/{branch_path(id, branch)}/datacontract.yaml",
            headers={"Accept": "application/yaml"},
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        if out_file is not None:
            out_file.write_text(response.text)
            print_success(f"Branch '{branch}' of data contract '{id}' written to {out_file}.")
        else:
            print(response.text)
    except Exception as e:
        handle_error(e)


@branches_app.command("put")
def put_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    file: Annotated[Path, typer.Option("--file", "-f", help="ODCS YAML file (use - for stdin).")] = ...,
) -> None:
    """Replace the branch's document with an ODCS YAML file. The data contract itself is untouched."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    try:
        content = read_text(file)
        client = get_client()
        response = client.session.put(
            f"{client.base_url}/api/{branch_path(id, branch)}/datacontract.yaml",
            data=content.encode("utf-8"),
            headers={"Content-Type": "application/yaml"},
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success(f"Branch '{branch}' of data contract '{id}' updated.")
    except Exception as e:
        handle_error(e)


@branches_app.command("changes")
def changes_of_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List what the branch changes against the data contract, element by element."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(f"{branch_path(id, branch)}/changes")
        print_resource_list(data, CHANGES_TYPE, fmt, title=f"Changes on {branch}")
    except Exception as e:
        handle_error(e)


@branches_app.command("rebase")
def rebase_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Update the branch from the data contract. Conflicts are reported and resolved in the UI."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.post_action_json(branches_path(id), branch, "rebase")
        print_success(f"Branch '{branch}' updated from data contract '{id}'.")
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@branches_app.command("merge")
def merge_branch(
    id: Annotated[str, typer.Argument(help=ID_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    version: Annotated[
        Optional[str],
        typer.Option(
            "--version",
            help="The version the data contract lands with. Needed when the branch's own version is not above main's.",
        ),
    ] = None,
    route: Annotated[
        Optional[str],
        typer.Option(
            "--route",
            help=f"One of: {', '.join(MERGE_ROUTES)}. Defaults to what the data contract's git branch requires.",
        ),
    ] = None,
    update_ports: Annotated[
        bool,
        typer.Option(
            "--update-ports/--no-update-ports",
            help="Set the landed version on the output ports that implement the data contract.",
        ),
    ] = True,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Merge the branch: land it on the data contract, or open a pull request from it."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    if route is not None and route not in MERGE_ROUTES:
        raise typer.BadParameter(f"Must be one of: {', '.join(MERGE_ROUTES)}", param_hint="--route")

    fmt = output or get_output_format()
    body: dict = {"update_port_versions": update_ports}
    if version:
        body["version"] = version
    if route:
        body["route"] = route
    try:
        client = get_client()
        response = client.session.post(
            f"{client.base_url}/api/{branch_path(id, branch)}/merge", json=body, timeout=REQUEST_TIMEOUT
        )
        _raise_for_status(response)
        if response.status_code == 204:
            print_success(f"Branch '{branch}' merged into data contract '{id}'.")
            return
        # 200: the branch stays open, a pull/merge request was opened from it.
        data = response.json()
        print_success(f"Request opened for branch '{branch}'. The branch stays open.")
        print_data(data, fmt)
    except Exception as e:
        handle_error(e)
