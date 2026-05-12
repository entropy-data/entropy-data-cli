"""Git credentials subcommands shared by `organization` and `teams`."""

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, console, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

GIT_CONNECTION_TYPES = ("github", "gitlab", "bitbucket", "azuredevops")
TOKEN_TYPES = ("authenticationToken", "apiToken")


def _base_path(scope: str, team_id: Optional[str]) -> str:
    """URL segment under /api/ for the gitcredentials collection."""
    if scope == "organization":
        return "organization/gitcredentials"
    if not team_id:
        raise typer.BadParameter("team-id is required for team-scoped git credentials.")
    return f"teams/{team_id}/gitcredentials"


def _read_token_arg(value: Optional[str]) -> Optional[str]:
    """Resolve --authentication-token: a literal value, '-' (stdin), or None."""
    if value == "-":
        return sys.stdin.read().strip()
    return value


def _build_create_body(
    file: Optional[Path],
    git_connection_type: Optional[str],
    authentication_token: Optional[str],
    external_id: Optional[str],
    host: Optional[str],
    token_name: Optional[str],
    token_type: Optional[str],
    bitbucket_username: Optional[str],
) -> dict:
    if file is not None:
        return read_body(file)
    if not git_connection_type:
        raise typer.BadParameter("Provide --file, or --git-connection-type plus --authentication-token.")
    if not authentication_token:
        raise typer.BadParameter("--authentication-token is required (use '-' to read from stdin).")
    body: dict = {
        "gitConnectionType": git_connection_type,
        "authenticationToken": authentication_token,
    }
    if external_id:
        body["externalId"] = external_id
    if host:
        body["host"] = host
    if token_name:
        body["tokenName"] = token_name
    if token_type:
        body["tokenType"] = token_type
    if bitbucket_username:
        body["bitbucketUsername"] = bitbucket_username
    return body


def _build_update_body(
    file: Optional[Path],
    git_connection_type: Optional[str],
    authentication_token: Optional[str],
    external_id: Optional[str],
    host: Optional[str],
    token_name: Optional[str],
    token_type: Optional[str],
    bitbucket_username: Optional[str],
) -> dict:
    if file is not None:
        return read_body(file)
    if not git_connection_type:
        raise typer.BadParameter("Provide --file, or --git-connection-type (token is optional on update).")
    body: dict = {"gitConnectionType": git_connection_type}
    if authentication_token:
        body["authenticationToken"] = authentication_token
    if external_id:
        body["externalId"] = external_id
    if host:
        body["host"] = host
    if token_name:
        body["tokenName"] = token_name
    if token_type:
        body["tokenType"] = token_type
    if bitbucket_username:
        body["bitbucketUsername"] = bitbucket_username
    return body


def make_git_credentials_app(scope: str) -> typer.Typer:
    """Build a Typer app exposing git-credentials operations for the given `scope`.

    `scope` is "organization" or "team". For "team", every subcommand takes a
    leading `team-id` argument that maps to the path parameter.
    """
    if scope not in ("organization", "team"):
        raise ValueError(f"Unknown scope: {scope}")

    app = typer.Typer(no_args_is_help=True)
    needs_team_id = scope == "team"

    if needs_team_id:

        @app.command("list")
        def list_(
            team_id: Annotated[str, typer.Argument(help="Team ID.")],
            output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
        ) -> None:
            """List git credentials."""
            _list_credentials(scope, team_id, output)

        @app.command("get")
        def get_(
            team_id: Annotated[str, typer.Argument(help="Team ID.")],
            credential_id: Annotated[str, typer.Argument(help="Git credential UUID.")],
            output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
        ) -> None:
            """Get a single git credential."""
            _get_credential(scope, team_id, credential_id, output)

        @app.command("create")
        def create_(
            team_id: Annotated[str, typer.Argument(help="Team ID.")],
            file: Annotated[
                Optional[Path],
                typer.Option("--file", "-f", help="JSON or YAML file with the create body (use - for stdin)."),
            ] = None,
            git_connection_type: Annotated[
                Optional[str],
                typer.Option(
                    "--git-connection-type",
                    help=f"One of: {', '.join(GIT_CONNECTION_TYPES)}.",
                ),
            ] = None,
            authentication_token: Annotated[
                Optional[str],
                typer.Option(
                    "--authentication-token",
                    help="Auth token (PAT, OAuth, app password). Use '-' to read from stdin.",
                ),
            ] = None,
            external_id: Annotated[
                Optional[str], typer.Option("--external-id", help="Optional org-unique external ID.")
            ] = None,
            host: Annotated[Optional[str], typer.Option("--host", help="Git host URL.")] = None,
            token_name: Annotated[
                Optional[str], typer.Option("--token-name", help="Display name for the token.")
            ] = None,
            token_type: Annotated[
                Optional[str],
                typer.Option("--token-type", help=f"One of: {', '.join(TOKEN_TYPES)}."),
            ] = None,
            bitbucket_username: Annotated[
                Optional[str],
                typer.Option(
                    "--bitbucket-username",
                    help="Required for bitbucket with token-type apiToken.",
                ),
            ] = None,
        ) -> None:
            """Create a git credential."""
            _create_credential(
                scope,
                team_id,
                file,
                git_connection_type,
                authentication_token,
                external_id,
                host,
                token_name,
                token_type,
                bitbucket_username,
            )

        @app.command("update")
        def update_(
            team_id: Annotated[str, typer.Argument(help="Team ID.")],
            credential_id: Annotated[str, typer.Argument(help="Git credential UUID.")],
            file: Annotated[
                Optional[Path],
                typer.Option("--file", "-f", help="JSON or YAML file with the update body (use - for stdin)."),
            ] = None,
            git_connection_type: Annotated[
                Optional[str],
                typer.Option(
                    "--git-connection-type",
                    help=f"One of: {', '.join(GIT_CONNECTION_TYPES)}.",
                ),
            ] = None,
            authentication_token: Annotated[
                Optional[str],
                typer.Option(
                    "--authentication-token",
                    help="Omit to keep the existing token. Use '-' to read from stdin.",
                ),
            ] = None,
            external_id: Annotated[Optional[str], typer.Option("--external-id")] = None,
            host: Annotated[Optional[str], typer.Option("--host")] = None,
            token_name: Annotated[Optional[str], typer.Option("--token-name")] = None,
            token_type: Annotated[Optional[str], typer.Option("--token-type")] = None,
            bitbucket_username: Annotated[Optional[str], typer.Option("--bitbucket-username")] = None,
        ) -> None:
            """Update a git credential."""
            _update_credential(
                scope,
                team_id,
                credential_id,
                file,
                git_connection_type,
                authentication_token,
                external_id,
                host,
                token_name,
                token_type,
                bitbucket_username,
            )

        @app.command("delete")
        def delete_(
            team_id: Annotated[str, typer.Argument(help="Team ID.")],
            credential_id: Annotated[str, typer.Argument(help="Git credential UUID.")],
        ) -> None:
            """Delete a git credential."""
            _delete_credential(scope, team_id, credential_id)

    else:

        @app.command("list")
        def list_(
            output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
        ) -> None:
            """List git credentials."""
            _list_credentials(scope, None, output)

        @app.command("get")
        def get_(
            credential_id: Annotated[str, typer.Argument(help="Git credential UUID.")],
            output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
        ) -> None:
            """Get a single git credential."""
            _get_credential(scope, None, credential_id, output)

        @app.command("create")
        def create_(
            file: Annotated[
                Optional[Path],
                typer.Option("--file", "-f", help="JSON or YAML file with the create body (use - for stdin)."),
            ] = None,
            git_connection_type: Annotated[
                Optional[str],
                typer.Option(
                    "--git-connection-type",
                    help=f"One of: {', '.join(GIT_CONNECTION_TYPES)}.",
                ),
            ] = None,
            authentication_token: Annotated[
                Optional[str],
                typer.Option(
                    "--authentication-token",
                    help="Auth token (PAT, OAuth, app password). Use '-' to read from stdin.",
                ),
            ] = None,
            external_id: Annotated[Optional[str], typer.Option("--external-id")] = None,
            host: Annotated[Optional[str], typer.Option("--host")] = None,
            token_name: Annotated[Optional[str], typer.Option("--token-name")] = None,
            token_type: Annotated[Optional[str], typer.Option("--token-type")] = None,
            bitbucket_username: Annotated[Optional[str], typer.Option("--bitbucket-username")] = None,
        ) -> None:
            """Create a git credential."""
            _create_credential(
                scope,
                None,
                file,
                git_connection_type,
                authentication_token,
                external_id,
                host,
                token_name,
                token_type,
                bitbucket_username,
            )

        @app.command("update")
        def update_(
            credential_id: Annotated[str, typer.Argument(help="Git credential UUID.")],
            file: Annotated[
                Optional[Path],
                typer.Option("--file", "-f", help="JSON or YAML file with the update body (use - for stdin)."),
            ] = None,
            git_connection_type: Annotated[
                Optional[str],
                typer.Option(
                    "--git-connection-type",
                    help=f"One of: {', '.join(GIT_CONNECTION_TYPES)}.",
                ),
            ] = None,
            authentication_token: Annotated[Optional[str], typer.Option("--authentication-token")] = None,
            external_id: Annotated[Optional[str], typer.Option("--external-id")] = None,
            host: Annotated[Optional[str], typer.Option("--host")] = None,
            token_name: Annotated[Optional[str], typer.Option("--token-name")] = None,
            token_type: Annotated[Optional[str], typer.Option("--token-type")] = None,
            bitbucket_username: Annotated[Optional[str], typer.Option("--bitbucket-username")] = None,
        ) -> None:
            """Update a git credential."""
            _update_credential(
                scope,
                None,
                credential_id,
                file,
                git_connection_type,
                authentication_token,
                external_id,
                host,
                token_name,
                token_type,
                bitbucket_username,
            )

        @app.command("delete")
        def delete_(
            credential_id: Annotated[str, typer.Argument(help="Git credential UUID.")],
        ) -> None:
            """Delete a git credential."""
            _delete_credential(scope, None, credential_id)

    return app


def _list_credentials(scope: str, team_id: Optional[str], output: Optional[OutputFormat]) -> None:
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(_base_path(scope, team_id))
        print_resource_list(data, "git-credentials", fmt)
    except Exception as e:
        handle_error(e)


def _get_credential(scope: str, team_id: Optional[str], credential_id: str, output: Optional[OutputFormat]) -> None:
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(_base_path(scope, team_id), credential_id)
        print_resource(data, "git-credentials", fmt)
    except Exception as e:
        handle_error(e)


def _create_credential(
    scope: str,
    team_id: Optional[str],
    file: Optional[Path],
    git_connection_type: Optional[str],
    authentication_token: Optional[str],
    external_id: Optional[str],
    host: Optional[str],
    token_name: Optional[str],
    token_type: Optional[str],
    bitbucket_username: Optional[str],
) -> None:
    from entropy_data.cli import get_client, handle_error
    from entropy_data.client import REQUEST_TIMEOUT, _raise_for_status

    if git_connection_type and git_connection_type not in GIT_CONNECTION_TYPES:
        raise typer.BadParameter(
            f"Must be one of: {', '.join(GIT_CONNECTION_TYPES)}", param_hint="--git-connection-type"
        )
    if token_type and token_type not in TOKEN_TYPES:
        raise typer.BadParameter(f"Must be one of: {', '.join(TOKEN_TYPES)}", param_hint="--token-type")

    body = _build_create_body(
        file=file,
        git_connection_type=git_connection_type,
        authentication_token=_read_token_arg(authentication_token),
        external_id=external_id,
        host=host,
        token_name=token_name,
        token_type=token_type,
        bitbucket_username=bitbucket_username,
    )

    try:
        client = get_client()
        response = client.session.post(
            f"{client.base_url}/api/{_base_path(scope, team_id)}",
            json=body,
            timeout=REQUEST_TIMEOUT,
        )
        _raise_for_status(response)
        data = response.json()
        print_success(f"Git credential '{data.get('id')}' created.")
        console.print_json(json.dumps(data))
    except Exception as e:
        handle_error(e)


def _update_credential(
    scope: str,
    team_id: Optional[str],
    credential_id: str,
    file: Optional[Path],
    git_connection_type: Optional[str],
    authentication_token: Optional[str],
    external_id: Optional[str],
    host: Optional[str],
    token_name: Optional[str],
    token_type: Optional[str],
    bitbucket_username: Optional[str],
) -> None:
    from entropy_data.cli import get_client, handle_error

    if git_connection_type and git_connection_type not in GIT_CONNECTION_TYPES:
        raise typer.BadParameter(
            f"Must be one of: {', '.join(GIT_CONNECTION_TYPES)}", param_hint="--git-connection-type"
        )
    if token_type and token_type not in TOKEN_TYPES:
        raise typer.BadParameter(f"Must be one of: {', '.join(TOKEN_TYPES)}", param_hint="--token-type")

    body = _build_update_body(
        file=file,
        git_connection_type=git_connection_type,
        authentication_token=_read_token_arg(authentication_token),
        external_id=external_id,
        host=host,
        token_name=token_name,
        token_type=token_type,
        bitbucket_username=bitbucket_username,
    )

    try:
        client = get_client()
        client.put_resource(_base_path(scope, team_id), credential_id, body)
        print_success(f"Git credential '{credential_id}' updated.")
    except Exception as e:
        handle_error(e)


def _delete_credential(scope: str, team_id: Optional[str], credential_id: str) -> None:
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(_base_path(scope, team_id), credential_id)
        print_success(f"Git credential '{credential_id}' deleted.")
    except Exception as e:
        handle_error(e)
