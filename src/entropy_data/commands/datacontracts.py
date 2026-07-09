"""Data contracts commands."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

datacontracts_app = typer.Typer(no_args_is_help=True)
RESOURCE_PATH = "datacontracts"
RESOURCE_TYPE = "datacontracts"


@datacontracts_app.command("list")
def list_datacontracts(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    query: Annotated[Optional[str], typer.Option("--query", "-q", help="Search term.")] = None,
    owner: Annotated[Optional[str], typer.Option("--owner", help="Filter by owner.")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag.")] = None,
    sort: Annotated[Optional[str], typer.Option("--sort", help="Sort field.")] = None,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all data contracts."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        params = {"p": page}
        if query:
            params["q"] = query
        if owner:
            params["owner"] = owner
        if tag:
            params["tag"] = tag
        if sort:
            params["sort"] = sort
        data, has_next = client.list_resources(RESOURCE_PATH, params=params)
        print_resource_list(data, RESOURCE_TYPE, fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("get")
def get_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a data contract by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(RESOURCE_PATH, id)
        print_resource(data, RESOURCE_TYPE, fmt)
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("put")
def put_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a data contract."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        client = get_client()
        location = client.put_resource(RESOURCE_PATH, id, body)
        print_success(f"Data contract '{id}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("test")
def test_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    server: Annotated[Optional[str], typer.Option("--server", "-s", help="Server name to test against.")] = None,
) -> None:
    """Run a data contract test."""
    import json

    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        params = {}
        if server:
            params["server"] = server
        # Data contract tests can take a long time (up to 30 minutes)
        data = client.post_action_json(RESOURCE_PATH, id, "test", params=params, timeout=1800)
        print(json.dumps(data, indent=2))
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("delete")
def delete_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
) -> None:
    """Delete a data contract."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(RESOURCE_PATH, id)
        print_success(f"Data contract '{id}' deleted.")
    except Exception as e:
        handle_error(e)


GENERATE_TYPES = (
    "sql-select",
    "sql-ddl",
    "dbt-models",
    "dbt-sources",
    "json-schema",
    "pydantic",
    "custom",
)


@datacontracts_app.command("yaml")
def yaml_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    out_file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Write YAML to this file. Defaults to stdout."),
    ] = None,
) -> None:
    """Get a data contract as ODCS YAML."""
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status, _validate_resource_id

    try:
        client = get_client()
        _validate_resource_id(id)
        response = client.session.get(
            f"{client.base_url}/api/datacontracts/{id}/datacontract.yaml",
            headers={"Accept": "application/yaml"},
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        if out_file is not None:
            out_file.write_text(response.text)
            print_success(f"Data contract '{id}' written to {out_file}.")
        else:
            print(response.text)
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("generate")
def generate_datacontract(
    id: Annotated[str, typer.Argument(help="Data contract ID.")],
    type: Annotated[
        str,
        typer.Option(
            "--type",
            "-t",
            help=f"Generation type. One of: {', '.join(GENERATE_TYPES)}.",
        ),
    ] = ...,
    prompt: Annotated[
        Optional[str],
        typer.Option("--prompt", help="Prompt for AI-powered custom generation. Required when --type custom."),
    ] = None,
    out_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--out-dir",
            help="Directory to write each generated file into. If omitted, prints the JSON response.",
        ),
    ] = None,
) -> None:
    """Generate code artifacts from an ODCS data contract."""
    import json

    from entropy_data.cli import get_client, handle_error

    if type not in GENERATE_TYPES:
        raise typer.BadParameter(
            f"Must be one of: {', '.join(GENERATE_TYPES)}",
            param_hint="--type",
        )
    if type == "custom" and not prompt:
        raise typer.BadParameter("--prompt is required when --type custom.")

    body: dict = {"type": type}
    if prompt:
        body["prompt"] = prompt

    try:
        client = get_client()
        # Generation may invoke an LLM for `custom`, so allow extra time.
        data = client.post_action_json(RESOURCE_PATH, id, "generate", body=body, timeout=300)
        if out_dir is None:
            print(json.dumps(data, indent=2))
            return
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in data.get("files", []):
            filename = f.get("filename") or "generated.out"
            (out_dir / filename).write_text(f.get("content", ""))
        print_success(f"Wrote {len(data.get('files', []))} generated file(s) to {out_dir}.")
    except Exception as e:
        handle_error(e)


@datacontracts_app.command("import-from-git")
def import_datacontract_from_git(
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
    """Import a data contract from a Git repository."""
    from entropy_data.cli import get_client, handle_error

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
        client.post_resource("datacontracts/import/git", body)
        print_success("Data contract imported from Git.")
    except Exception as e:
        handle_error(e)


def _build_git_import_body(
    file: Optional[Path],
    repository_url: Optional[str],
    repository_path: Optional[str],
    repository_branch: Optional[str],
    git_connection_type: Optional[str],
    host: Optional[str],
    git_credential_external_id: Optional[str],
) -> dict:
    """Assemble a GitImportRequest body from --file or individual flags."""
    if file is not None:
        return read_body(file)
    if not repository_url or not repository_path:
        raise typer.BadParameter(
            "Provide --file, or both --repository-url and --repository-path.",
        )
    if not git_connection_type and not git_credential_external_id:
        raise typer.BadParameter(
            "Provide --git-connection-type or --git-credential-external-id.",
        )
    body: dict = {"repositoryUrl": repository_url, "repositoryPath": repository_path}
    if repository_branch:
        body["repositoryBranch"] = repository_branch
    if git_connection_type:
        body["gitConnectionType"] = git_connection_type
    if host:
        body["host"] = host
    if git_credential_external_id:
        body["gitCredentialExternalId"] = git_credential_external_id
    return body


from entropy_data.commands.gitconnections import make_gitconnection_app  # noqa: E402

datacontracts_app.add_typer(
    make_gitconnection_app(RESOURCE_PATH, "Data contract"),
    name="gitconnection",
    help="Manage the git connection.",
)
