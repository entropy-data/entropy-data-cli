"""Git connection subcommands. Used as a sub-typer of dataproducts and datacontracts."""

import json
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_link, print_success

GIT_CONNECTION_TYPES = ("github", "gitlab", "bitbucket", "azuredevops")


def make_gitconnection_app(resource_path: str, resource_label: str) -> typer.Typer:
    """Build a Typer app exposing /api/{resource_path}/{id}/gitconnection operations.

    `resource_path` is the URL segment ("dataproducts" or "datacontracts").
    `resource_label` is the human-readable name shown in success messages.
    """

    app = typer.Typer(no_args_is_help=True)

    @app.command("get")
    def get_(
        id: Annotated[str, typer.Argument(help=f"{resource_label} ID.")],
        output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
    ) -> None:
        """Get the git connection."""
        from entropy_data.cli import get_client, get_output_format, handle_error

        fmt = output or get_output_format()
        try:
            client = get_client()
            data = client.get_gitconnection(resource_path, id)
            if fmt == OutputFormat.json:
                print(json.dumps(data, indent=2))
            else:
                print(json.dumps(data, indent=2))
        except Exception as e:
            handle_error(e)

    @app.command("put")
    def put_(
        id: Annotated[str, typer.Argument(help=f"{resource_label} ID.")],
        repository_url: Annotated[str, typer.Option("--repository-url", help="URL of the Git repository.")] = ...,
        repository_path: Annotated[
            str, typer.Option("--repository-path", help="Path to the YAML file in the repository.")
        ] = ...,
        repository_branch: Annotated[
            Optional[str],
            typer.Option("--repository-branch", help="Branch to use. Defaults to 'main'."),
        ] = None,
        git_connection_type: Annotated[
            Optional[str],
            typer.Option(
                "--git-connection-type",
                help=f"Git provider type. One of: {', '.join(GIT_CONNECTION_TYPES)}.",
            ),
        ] = None,
        host: Annotated[
            Optional[str],
            typer.Option("--host", help="Host of a self-hosted git provider. Omit for SaaS."),
        ] = None,
        git_credential_external_id: Annotated[
            Optional[str],
            typer.Option(
                "--git-credential-external-id",
                help="External ID of a stored git credential to use.",
            ),
        ] = None,
    ) -> None:
        """Create or update the git connection."""
        from entropy_data.cli import get_client, handle_error

        if git_connection_type and git_connection_type not in GIT_CONNECTION_TYPES:
            raise typer.BadParameter(
                f"Must be one of: {', '.join(GIT_CONNECTION_TYPES)}",
                param_hint="--git-connection-type",
            )
        if not git_connection_type and not git_credential_external_id:
            raise typer.BadParameter(
                "At least one of --git-connection-type or --git-credential-external-id must be provided.",
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

        try:
            client = get_client()
            data = client.put_gitconnection(resource_path, id, body)
            print_success(f"Git connection saved for {resource_label.lower()} '{id}'.")
            print_link(data.get("webLink"))
        except Exception as e:
            handle_error(e)

    @app.command("delete")
    def delete_(
        id: Annotated[str, typer.Argument(help=f"{resource_label} ID.")],
    ) -> None:
        """Delete the git connection."""
        from entropy_data.cli import get_client, handle_error

        try:
            client = get_client()
            client.delete_gitconnection(resource_path, id)
            print_success(f"Git connection deleted for {resource_label.lower()} '{id}'.")
        except Exception as e:
            handle_error(e)

    @app.command("pull")
    def pull_(
        id: Annotated[str, typer.Argument(help=f"{resource_label} ID.")],
    ) -> None:
        """Pull the file from Git into Entropy Data."""
        from entropy_data.cli import get_client, handle_error

        try:
            client = get_client()
            data = client.gitconnection_action(resource_path, id, "pull")
            print_success(f"{resource_label} '{id}' pulled from Git.")
            print_link(data.get("webLink"))
        except Exception as e:
            handle_error(e)

    @app.command("push")
    def push_(
        id: Annotated[str, typer.Argument(help=f"{resource_label} ID.")],
        commit_message: Annotated[
            Optional[str], typer.Option("--commit-message", help="Custom commit message.")
        ] = None,
    ) -> None:
        """Push the current Entropy Data file to Git."""
        from entropy_data.cli import get_client, handle_error

        body: dict | None = {"commitMessage": commit_message} if commit_message else None
        try:
            client = get_client()
            data = client.gitconnection_action(resource_path, id, "push", body)
            print_success(f"{resource_label} '{id}' pushed to Git.")
            print_link(data.get("webLink"))
        except Exception as e:
            handle_error(e)

    @app.command("push-pr")
    def push_pr(
        id: Annotated[str, typer.Argument(help=f"{resource_label} ID.")],
        commit_message: Annotated[
            Optional[str], typer.Option("--commit-message", help="Custom commit message.")
        ] = None,
        branch_name: Annotated[Optional[str], typer.Option("--branch-name", help="Name of the new branch.")] = None,
        title: Annotated[Optional[str], typer.Option("--title", help="Pull request title.")] = None,
        comment: Annotated[
            Optional[str],
            typer.Option("--comment", help="Pull request description / comment."),
        ] = None,
    ) -> None:
        """Push the current Entropy Data file to Git as a pull/merge request."""
        from entropy_data.cli import get_client, handle_error

        body: dict = {}
        if commit_message:
            body["commitMessage"] = commit_message
        if branch_name:
            body["branchName"] = branch_name
        if title:
            body["title"] = title
        if comment:
            body["comment"] = comment
        try:
            client = get_client()
            data = client.gitconnection_action(resource_path, id, "push-pr", body or None)
            print_success(f"{resource_label} '{id}' pushed to Git as pull request.")
            print_link(data.get("webLink"))
        except Exception as e:
            handle_error(e)

    return app
