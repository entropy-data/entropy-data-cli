"""Data products commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

dataproducts_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "dataproducts"
RESOURCE_TYPE = "dataproducts"


@dataproducts_app.command("list")
def list_dataproducts(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    query: Annotated[Optional[str], typer.Option("--query", "-q", help="Search term.")] = None,
    status: Annotated[Optional[str], typer.Option("--status", help="Filter by status.")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag.")] = None,
    sort: Annotated[Optional[str], typer.Option("--sort", help="Sort field.")] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all data products."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {"p": page}
        if query:
            params["q"] = query
        if status:
            params["status"] = status
        if tag:
            params["tag"] = tag
        if sort:
            params["sort"] = sort
        data, has_next = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("get")
def get_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a data product by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("put")
def put_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a data product."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Data product '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("delete")
def delete_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
) -> None:
    """Delete a data product."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Data product '{id}' deleted.")
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("import-from-git")
def import_dataproduct_from_git(
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="JSON or YAML file with the GitImportRequest body (use - for stdin)."),
    ] = None,
    repository_url: Annotated[
        Optional[str], typer.Option("--repository-url", help="URL of the Git repository.")
    ] = None,
    repository_path: Annotated[
        Optional[str], typer.Option("--repository-path", help="Path to the YAML file in the repository.")
    ] = None,
    repository_branch: Annotated[
        Optional[str], typer.Option("--repository-branch", help="Branch. Defaults to 'main'.")
    ] = None,
    git_connection_type: Annotated[
        Optional[str],
        typer.Option(
            "--git-connection-type",
            help="github | gitlab | bitbucket | azuredevops. Required without --git-credential-external-id.",
        ),
    ] = None,
    host: Annotated[Optional[str], typer.Option("--host", help="Host of a self-hosted git provider.")] = None,
    git_credential_external_id: Annotated[
        Optional[str],
        typer.Option(
            "--git-credential-external-id",
            help="External ID of a stored git credential to use.",
        ),
    ] = None,
) -> None:
    """Import a data product from a Git repository."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.commands.datacontracts import _build_git_import_body

    body = _build_git_import_body(
        file=file,
        repository_url=repository_url,
        repository_path=repository_path,
        repository_branch=repository_branch,
        git_connection_type=git_connection_type,
        host=host,
        git_credential_external_id=git_credential_external_id,
    )

    try:
        client = get_client()
        client.post_resource("dataproducts/import/git", body)
        print_success("Data product imported from Git.")
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("star")
def star_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
) -> None:
    """Star a data product (requires a user-scoped API key)."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    try:
        client = get_client()
        _validate_resource_id(id)
        response = client.session.put(
            f"{client.base_url}/api/{RESOURCE_PATH}/{id}/star",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success(f"Starred data product '{id}'.")
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("unstar")
def unstar_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
) -> None:
    """Remove your star from a data product (requires a user-scoped API key)."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    try:
        client = get_client()
        _validate_resource_id(id)
        response = client.session.delete(
            f"{client.base_url}/api/{RESOURCE_PATH}/{id}/star",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_success(f"Unstarred data product '{id}'.")
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("star-status")
def star_status_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Show the star count and whether you starred a data product."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    fmt = output or get_output_format()
    try:
        client = get_client()
        _validate_resource_id(id)
        response = client.session.get(
            f"{client.base_url}/api/{RESOURCE_PATH}/{id}/star",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_resource(response.json(), "star-status", fmt)
    except Exception as e:
        handle_error(e)


@dataproducts_app.command("stargazers")
def stargazers_dataproduct(
    id: Annotated[str, typer.Argument(help="Data product ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List the users who starred a data product (organization owners only)."""
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    fmt = output or get_output_format()
    try:
        client = get_client()
        _validate_resource_id(id)
        response = client.session.get(
            f"{client.base_url}/api/{RESOURCE_PATH}/{id}/stargazers",
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        print_resource_list(response.json(), "stargazers", fmt)
    except Exception as e:
        handle_error(e)


from entropy_data.commands.gitconnections import make_gitconnection_app  # noqa: E402

dataproducts_app.add_typer(
    make_gitconnection_app(RESOURCE_PATH, "Data product"),
    name="gitconnection",
    help="Manage the git connection.",
)
