"""Semantics commands (EXPERIMENTAL): namespaces, concepts, relationships."""

import sys
from pathlib import Path
from typing import Annotated, Optional

import typer

from entropy_data.client import _validate_resource_id
from entropy_data.output import OutputFormat, print_link, print_resource, print_resource_list, print_success
from entropy_data.util import read_body

semantics_app = typer.Typer(no_args_is_help=True, help="EXPERIMENTAL semantics API.")

BASE = "semantics/experimental/namespaces"

namespaces_app = typer.Typer(no_args_is_help=True)
concepts_app = typer.Typer(no_args_is_help=True)
relationships_app = typer.Typer(no_args_is_help=True)


# Namespaces


@namespaces_app.command("list")
def list_namespaces(
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List all semantic namespaces."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(BASE)
        print_resource_list(data, "semantic-namespaces", fmt)
    except Exception as e:
        handle_error(e)


@namespaces_app.command("get")
def get_namespace(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a namespace by ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(BASE, namespace)
        print_resource(data, "semantic-namespaces", fmt)
    except Exception as e:
        handle_error(e)


@namespaces_app.command("put")
def put_namespace(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a namespace."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        # The server validates that body.namespace matches the path; align them here
        # so callers can omit `namespace` from the file.
        if "namespace" in body and body["namespace"] != namespace:
            raise typer.BadParameter(
                f"Body namespace '{body['namespace']}' does not match path '{namespace}'.",
            )
        body = {**body, "namespace": namespace}
        client = get_client()
        location = client.put_resource(BASE, namespace, body)
        print_success(f"Semantic namespace '{namespace}' saved.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@namespaces_app.command("delete")
def delete_namespace(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
) -> None:
    """Delete a namespace (cascades to concepts and relationships)."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(BASE, namespace)
        print_success(f"Semantic namespace '{namespace}' deleted.")
    except Exception as e:
        handle_error(e)


# Concepts


@namespaces_app.command("yaml")
def yaml_namespace(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    out_file: Annotated[
        Optional[Path],
        typer.Option("--file", "-f", help="Write YAML to this file. Defaults to stdout."),
    ] = None,
) -> None:
    """Get the whole namespace as one OSI ontology YAML document (concepts and relationships)."""
    from entropy_data.cli import get_client, handle_error

    try:
        _validate_resource_id(namespace)
        text = get_client().http.get_text(f"/api/{BASE}/{namespace}/ontology.yaml")
        if out_file is not None:
            out_file.write_text(text)
            print_success(f"Namespace '{namespace}' written to {out_file}.")
        else:
            print(text)
    except Exception as e:
        handle_error(e)


@namespaces_app.command("put-yaml")
def put_namespace_yaml(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="OSI ontology YAML file (use - for stdin).")] = ...,
) -> None:
    """Replace the namespace's concepts and relationships with an OSI ontology YAML document.

    The document is the namespace's complete state: a concept or relationship it leaves out is
    deleted. Creates the namespace if it does not exist. To change a draft first, use
    'semantics branches'.
    """
    from entropy_data.cli import get_client, handle_error

    try:
        _validate_resource_id(namespace)
        content = sys.stdin.read() if str(file) == "-" else file.read_text()
        get_client().http.put_text(f"/api/{BASE}/{namespace}/ontology.yaml", content)
        print_success(f"Namespace '{namespace}' replaced from {'stdin' if str(file) == '-' else file}.")
    except Exception as e:
        handle_error(e)


# Concepts and relationships (deprecated upstream: write the namespace as a whole instead)

DEPRECATED_HINT = (
    "Deprecated by the API: read and write the namespace as a whole with "
    "'semantics namespaces yaml' and 'semantics namespaces put-yaml'."
)


def _concepts_path(namespace: str) -> str:
    return f"{BASE}/{namespace}/concepts"


@concepts_app.command("list", deprecated=True)
def list_concepts(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List concepts in a namespace."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(_concepts_path(namespace))
        print_resource_list(data, "semantic-concepts", fmt)
    except Exception as e:
        handle_error(e)


@concepts_app.command("get", deprecated=True)
def get_concept(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    external_id: Annotated[str, typer.Argument(help="Concept external ID (may contain '/').")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a concept by namespace and external ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(_concepts_path(namespace), external_id)
        print_resource(data, "semantic-concepts", fmt)
    except Exception as e:
        handle_error(e)


@concepts_app.command("put", deprecated=True)
def put_concept(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    external_id: Annotated[str, typer.Argument(help="Concept external ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a concept."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        if "id" in body and body["id"] != external_id:
            raise typer.BadParameter(
                f"Body id '{body['id']}' does not match path '{external_id}'.",
            )
        body = {**body, "id": external_id}
        client = get_client()
        location = client.put_resource(_concepts_path(namespace), external_id, body)
        print_success(f"Concept '{external_id}' saved in namespace '{namespace}'.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@concepts_app.command("delete", deprecated=True)
def delete_concept(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    external_id: Annotated[str, typer.Argument(help="Concept external ID.")],
) -> None:
    """Delete a concept and any relationships referencing it."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(_concepts_path(namespace), external_id)
        print_success(f"Concept '{external_id}' deleted from namespace '{namespace}'.")
    except Exception as e:
        handle_error(e)


# Relationships


def _relationships_path(namespace: str) -> str:
    return f"{BASE}/{namespace}/relationships"


@relationships_app.command("list", deprecated=True)
def list_relationships(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """List relationships in a namespace."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data, _ = client.list_resources(_relationships_path(namespace))
        print_resource_list(data, "semantic-relationships", fmt)
    except Exception as e:
        handle_error(e)


@relationships_app.command("get", deprecated=True)
def get_relationship(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    external_id: Annotated[str, typer.Argument(help="Relationship external ID (may contain '/').")],
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Get a relationship by namespace and external ID."""
    from entropy_data.cli import get_client, get_output_format, handle_error

    fmt = output or get_output_format()
    try:
        client = get_client()
        data = client.get_resource(_relationships_path(namespace), external_id)
        print_resource(data, "semantic-relationships", fmt)
    except Exception as e:
        handle_error(e)


@relationships_app.command("put", deprecated=True)
def put_relationship(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    external_id: Annotated[str, typer.Argument(help="Relationship external ID.")],
    file: Annotated[Path, typer.Option("--file", "-f", help="JSON or YAML file (use - for stdin).")] = ...,
) -> None:
    """Create or update a relationship."""
    from entropy_data.cli import get_client, handle_error

    try:
        body = read_body(file)
        if "id" in body and body["id"] != external_id:
            raise typer.BadParameter(
                f"Body id '{body['id']}' does not match path '{external_id}'.",
            )
        body = {**body, "id": external_id}
        client = get_client()
        location = client.put_resource(_relationships_path(namespace), external_id, body)
        print_success(f"Relationship '{external_id}' saved in namespace '{namespace}'.")
        print_link(location)
    except Exception as e:
        handle_error(e)


@relationships_app.command("delete", deprecated=True)
def delete_relationship(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    external_id: Annotated[str, typer.Argument(help="Relationship external ID.")],
) -> None:
    """Delete a relationship."""
    from entropy_data.cli import get_client, handle_error

    try:
        client = get_client()
        client.delete_resource(_relationships_path(namespace), external_id)
        print_success(f"Relationship '{external_id}' deleted from namespace '{namespace}'.")
    except Exception as e:
        handle_error(e)


@semantics_app.command("search")
def search_concepts(
    namespace: Annotated[str, typer.Argument(help="Namespace ID.")],
    query: Annotated[str, typer.Argument(help="Search query (case-insensitive substring).")],
    kind: Annotated[
        Optional[str],
        typer.Option("--kind", help="Filter by kind: entity, metric, group, shared_property, property."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", help="Max results.")] = 50,
    output: Annotated[Optional[OutputFormat], typer.Option("--output", "-o", help="Output format.")] = None,
) -> None:
    """Search concepts in a namespace by case-insensitive substring against id, name, description.

    Implemented client-side: fetches all concepts in the namespace via the experimental list
    endpoint, then filters in memory. The platform has no dedicated search endpoint.
    """
    from entropy_data.cli import get_client, get_output_format, handle_error
    from entropy_data.output import error_console

    fmt = output or get_output_format()
    q = query.strip().lower()
    if not q:
        error_console.print("[red]Error: query must not be empty.[/red]")
        raise SystemExit(2)

    try:
        client = get_client()
        all_concepts, _ = client.list_resources(_concepts_path(namespace))

        def matches(c: dict) -> bool:
            haystack = " ".join(
                [
                    c.get("id") or "",
                    c.get("name") or "",
                    c.get("description") or "",
                ]
            ).lower()
            return q in haystack

        filtered = [c for c in all_concepts if matches(c) and (kind is None or c.get("kind") == kind)]
        truncated = filtered[: max(1, limit)]
        print_resource_list(truncated, "semantic-concepts", fmt)
    except Exception as e:
        handle_error(e)


from entropy_data.commands.semantic_branches import branches_app  # noqa: E402

semantics_app.add_typer(namespaces_app, name="namespaces", help="Manage semantic namespaces.")
semantics_app.add_typer(
    concepts_app, name="concepts", help=f"Manage semantic concepts one at a time. {DEPRECATED_HINT}"
)
semantics_app.add_typer(
    relationships_app,
    name="relationships",
    help=f"Manage semantic relationships one at a time. {DEPRECATED_HINT}",
)
semantics_app.add_typer(
    branches_app,
    name="branches",
    help="Branches of a semantic namespace: cut, author, review and merge a draft.",
)
