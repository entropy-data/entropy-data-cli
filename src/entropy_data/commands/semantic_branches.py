"""Branches of a semantic namespace: cut, author, review and merge a draft of its OSI ontology."""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_data, print_resource, print_resource_list, print_success

branches_app = typer.Typer(no_args_is_help=True)
RESOURCE_TYPE = "semantic-branches"
CHANGES_TYPE = "semantic-branch-changes"

NAMESPACE_HELP = "Namespace the branch is cut from."
BRANCH_HELP = "Branch name."


def branches_path(namespace: str) -> str:
    from entropy_data.client import _validate_resource_id

    _validate_resource_id(namespace)
    return f"semantics/experimental/namespaces/{namespace}/branches"


def branch_path(namespace: str, branch: str) -> str:
    from entropy_data.client import _validate_resource_id

    _validate_resource_id(branch)
    return f"{branches_path(namespace)}/{branch}"


def read_text(file: Path) -> str:
    if str(file) == "-":
        return sys.stdin.read()
    return file.read_text()


@branches_app.command("list")
def list_branches(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the branches cut from a namespace."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(branches_path(namespace))
        print_resource_list(data, RESOURCE_TYPE, fmt, title=f"Branches of {namespace}")
    except Exception as e:
        handle_error(e)


@branches_app.command("create")
def create_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Cut a branch from a namespace. Cutting an existing name returns that branch."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        response = client.session.put(f"{client.base_url}/api/{branch_path(namespace, branch)}", timeout=client.timeout)
        _raise_for_status(response)
        if fmt == OutputFormat.table:
            print_success(f"Branch '{branch}' of namespace '{namespace}' created.")
        print_resource(response.json(), RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@branches_app.command("get")
def get_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show a branch: whether the namespace moved since, its conflicts, and any open pull request."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(branches_path(namespace), branch)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@branches_app.command("delete")
def delete_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
) -> None:
    """Delete a branch and everything authored on it. The namespace is untouched."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(branches_path(namespace), branch)
        print_success(f"Branch '{branch}' of namespace '{namespace}' deleted.")
    except Exception as e:
        handle_error(e)


@branches_app.command("yaml")
def yaml_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    out_file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Write YAML to this file. Defaults to stdout."),
    ] = None,
) -> None:
    """Get the branch as one OSI ontology YAML document."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _raise_for_status

    try:
        client = get_client()
        response = client.session.get(
            f"{client.base_url}/api/{branch_path(namespace, branch)}/ontology.yaml",
            headers={"Accept": "application/yaml"},
            timeout=client.timeout,
        )
        _raise_for_status(response)
        if out_file is not None:
            out_file.write_text(response.text)
            print_success(f"Branch '{branch}' of namespace '{namespace}' written to {out_file}.")
        else:
            print(response.text)
    except Exception as e:
        handle_error(e)


@branches_app.command("put")
def put_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    file: Annotated[Path, typer.Option("--file", "-f", help="OSI ontology YAML file (use - for stdin).")] = ...,
) -> None:
    """Replace the branch with an OSI ontology YAML document.

    The document is the branch's complete state: a concept or relationship it leaves out is removed
    from the branch. The namespace itself is untouched until the branch is merged.
    """
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import _raise_for_status

    try:
        content = read_text(file)
        client = get_client()
        response = client.session.put(
            f"{client.base_url}/api/{branch_path(namespace, branch)}/ontology.yaml",
            data=content.encode("utf-8"),
            headers={"Content-Type": "application/yaml"},
            timeout=client.timeout,
        )
        _raise_for_status(response)
        print_success(f"Branch '{branch}' of namespace '{namespace}' updated.")
    except Exception as e:
        handle_error(e)


@branches_app.command("changes")
def changes_of_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List what the branch changes against the namespace, one entry per concept."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(f"{branch_path(namespace, branch)}/changes")
        print_resource_list(data, CHANGES_TYPE, fmt, title=f"Changes on {branch}")
    except Exception as e:
        handle_error(e)


@branches_app.command("rebase")
def rebase_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Update the branch from the namespace. Conflicts are reported and resolved in the UI."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.post_action_json(branches_path(namespace), branch, "rebase")
        if fmt == OutputFormat.table:
            print_success(f"Branch '{branch}' updated from namespace '{namespace}'.")
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@branches_app.command("merge")
def merge_branch(
    namespace: Annotated[str, typer.Argument(help=NAMESPACE_HELP)],
    branch: Annotated[str, typer.Argument(help=BRANCH_HELP)],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Merge the branch: land it on the namespace, or open a pull request where git requires review."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import _raise_for_status

    fmt = output or get_output_format()
    try:
        client = get_client()
        response = client.session.post(
            f"{client.base_url}/api/{branch_path(namespace, branch)}/merge", timeout=client.timeout
        )
        _raise_for_status(response)
        if response.status_code == 204:
            print_success(f"Branch '{branch}' merged into namespace '{namespace}'.")
            return
        # 200: the branch stays open, a pull/merge request was opened from it.
        data = response.json()
        if fmt == OutputFormat.table:
            print_success(f"Request opened for branch '{branch}'. The branch stays open.")
            print_data(data, OutputFormat.json)
        else:
            print_data(data, fmt)
    except Exception as e:
        handle_error(e)
