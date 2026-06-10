"""Custom team roles commands (organization-scoped)."""

from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.output import OutputFormat, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

custom_team_roles_app = typer.Typer(no_args_is_help=True)

BASE_PATH = "organization/custom-team-roles"


def _split_permissions(values: Optional[list[str]]) -> Optional[list[str]]:
    """Allow `--permissions A,B --permissions C` style; flatten and trim."""
    if not values:
        return None
    out: list[str] = []
    for v in values:
        for part in v.split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def _build_body(
    name: str,
    body_name: Optional[str],
    description: Optional[str],
    rank: Optional[int],
    permissions: Optional[list[str]],
    file: Optional[Path],
) -> dict:
    if file is not None:
        body = read_body(file)
        body.setdefault("name", body_name or name)
        return body
    body: dict = {"name": body_name or name}
    if description is not None:
        body["description"] = description
    if rank is not None:
        body["rank"] = rank
    if permissions is not None:
        body["permissions"] = permissions
    else:
        body["permissions"] = []
    return body


@custom_team_roles_app.command("list")
def list_roles(
    page: Annotated[int, typer.Option("--page", "-p", help="Page number (0-indexed).")] = 0,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List custom team roles defined for the organization."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, has_next = client.list_resources(BASE_PATH, params={"p": page})
        print_resource_list(data, "custom-team-roles", fmt, has_next_page=has_next, page=page)
    except Exception as e:
        handle_error(e)


@custom_team_roles_app.command("get")
def get_role(
    name: Annotated[str, typer.Argument(help="Name of the custom team role.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a custom team role by name."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(BASE_PATH, name)
        print_resource(data, "custom-team-roles", fmt)
    except Exception as e:
        handle_error(e)


@custom_team_roles_app.command("put")
def put_role(
    name: Annotated[str, typer.Argument(help="Name of the role at this URL. Pass a different --name to rename.")],
    file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="JSON or YAML file with the body (use - for stdin)."),
    ] = None,
    body_name: Annotated[
        Optional[str],
        typer.Option(
            "--name",
            help="Name to set on the role. Must equal the path name on create. Set to a different value to rename an existing role.",
        ),
    ] = None,
    description: Annotated[Optional[str], typer.Option("--description", help="Optional description.")] = None,
    rank: Annotated[
        Optional[int],
        typer.Option("--rank", help="Display order — lower ranks appear first."),
    ] = None,
    permissions: Annotated[
        Optional[list[str]],
        typer.Option(
            "--permissions",
            help="Comma-separated or repeated TeamPermission values (e.g. ACCESS_APPROVE,ACCESS_EDIT).",
        ),
    ] = None,
) -> None:
    """Create, update, or rename a custom team role.

    Resolution by path `name`:
      - No role at path, body name matches → create.
      - Role at path, body name matches → update in place.
      - Role at path, body name differs → rename (rejected if the path name is still
        assigned to a team member, or if the new name already exists).
      - No role at path, body name differs → 400.
    """
    from entropy_data.cli import get_client, handle_error

    body = _build_body(
        name=name,
        body_name=body_name,
        description=description,
        rank=rank,
        permissions=_split_permissions(permissions),
        file=file,
    )

    try:
        client = get_client()
        client.put_resource(BASE_PATH, name, body)
        target = body.get("name") or name
        if target != name:
            print_success(f"Custom team role '{name}' renamed to '{target}'.")
        else:
            print_success(f"Custom team role '{target}' saved.")
    except Exception as e:
        handle_error(e)


@custom_team_roles_app.command("delete")
def delete_role(
    name: Annotated[str, typer.Argument(help="Name of the custom team role to delete.")],
) -> None:
    """Delete a custom team role.

    Rejected with 409 when the role is still assigned to any team member.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(BASE_PATH, name)
        print_success(f"Custom team role '{name}' deleted.")
    except Exception as e:
        handle_error(e)
