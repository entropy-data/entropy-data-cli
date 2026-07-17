"""Export / apply / prune engine for the portable resource set.

All user-facing commands (`export dir`, `apply dir`, `import zip`, `sync`)
are thin wrappers over the functions here so they share one enumeration, upsert
and prune implementation and cannot drift. Everything is continue-on-error: a
single resource failure is logged and counted, never aborts the run.

Flat resources are `/api/{api_path}` (list-all) + `/api/{api_path}/{id}`. A document
resource (``Resource.document`` set) is one raw-YAML document per parent, GET/PUT at
the expanded ``{parent}`` path; its artifact lives at ``<name>/<parent_id>.yaml``.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from entropy_data.client import (
    REQUEST_TIMEOUT,
    ApiError,
    EntropyDataClient,
    _raise_for_status,
    _validate_resource_id,
)
from entropy_data.output import console, error_console
from entropy_data.resources import RESOURCE_BY_NAME, Resource, sanitize_filename, strip_audit_fields


@dataclass
class SyncResult:
    """Tally of an export or import run."""

    ok: int = 0
    fail: int = 0

    def add(self, other: "SyncResult") -> None:
        self.ok += other.ok
        self.fail += other.fail


@dataclass
class PlanCounts:
    """Per-resource dry-run plan."""

    create: int = 0
    update: int = 0
    prune: int = 0


# --- enumeration (source side) --------------------------------------------------


def _list_all(client: EntropyDataClient, resource: Resource, parent_id: str | None = None) -> list[dict]:
    """Return every item of a resource, following ``Link: rel="next"`` if paginated.

    ``parent_id`` selects the parent for a nested resource; it is ignored for flat ones.
    """
    api_path = resource.path_for(parent_id)
    if not resource.paginated:
        items, _ = client.list_resources(api_path)
        return list(items)

    items: list[dict] = []
    page = 0
    while True:
        batch, has_next = client.list_resources(api_path, params={"p": page})
        items.extend(batch)
        if not has_next:
            break
        page += 1
    return items


def _enumerate_ids(client: EntropyDataClient, resource: Resource, parent_id: str | None = None) -> set[str]:
    """Return the set of resource ids currently on the target (for prune / dry-run)."""
    return {
        str(item[resource.id_field]) for item in _list_all(client, resource, parent_id) if item.get(resource.id_field)
    }


def _parent_ids(client: EntropyDataClient, resource: Resource) -> list[str]:
    """List the ids of a nested resource's parent (e.g. namespaces for concepts)."""
    parent = RESOURCE_BY_NAME[resource.parent]
    return [str(item[parent.id_field]) for item in _list_all(client, parent) if item.get(parent.id_field)]


# --- singleton (org-level object, no id) ---------------------------------------


def _get_singleton(client: EntropyDataClient, resource: Resource) -> dict:
    """GET the singleton object at ``/api/{api_path}`` (returns ``{}`` when unset)."""
    response = client.session.get(f"{client.base_url}/api/{resource.api_path}", timeout=REQUEST_TIMEOUT)
    _raise_for_status(response)
    body = response.json()
    return body if isinstance(body, dict) else {}


def _put_singleton(client: EntropyDataClient, resource: Resource, body: dict) -> None:
    """PUT the singleton object at ``/api/{api_path}`` (no id segment)."""
    response = client.session.put(f"{client.base_url}/api/{resource.api_path}", json=body, timeout=REQUEST_TIMEOUT)
    _raise_for_status(response)


def _singleton_file(root: Path, resource: Resource) -> Path:
    return root / resource.name / f"{resource.name}.yaml"


# --- document (one raw-YAML document per parent) --------------------------------


def _get_document(client: EntropyDataClient, resource: Resource, parent_id: str) -> str:
    """GET the raw YAML document at the expanded ``{parent}`` path."""
    response = client.session.get(
        f"{client.base_url}/api/{resource.path_for(parent_id)}",
        headers={"Accept": "application/yaml"},
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status(response)
    return response.text


def _put_document(client: EntropyDataClient, resource: Resource, parent_id: str, text: str) -> None:
    """PUT the raw YAML document to the expanded ``{parent}`` path."""
    response = client.session.put(
        f"{client.base_url}/api/{resource.path_for(parent_id)}",
        data=text.encode("utf-8"),
        headers={"Content-Type": "application/yaml"},
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status(response)


def _export_document(client: EntropyDataClient, resource: Resource, parent_id: str, target_dir: Path) -> SyncResult:
    """Fetch one parent's YAML document and write it to ``<name>/<parent_id>.yaml`` (skips when empty)."""
    total = SyncResult()
    try:
        text = _get_document(client, resource, parent_id)
    except ApiError as e:
        error_console.print(f"  [red]FAIL[/red] {parent_id}: {e}")
        total.fail += 1
        return total

    if not text.strip():  # empty document; nothing to copy
        return total

    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"{sanitize_filename(parent_id)}.yaml").write_text(text)
    console.print(f"  [green]OK[/green]   {parent_id}")
    total.ok += 1
    return total


# --- assigned-tags sub-resource (assets) ---------------------------------------


def _get_assigned_tags(client: EntropyDataClient, asset_id: str) -> list[str]:
    _validate_resource_id(asset_id)
    response = client.session.get(
        f"{client.base_url}/api/assets/{asset_id}/assigned-tags",
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status(response)
    return response.json()


def _put_assigned_tag(client: EntropyDataClient, asset_id: str, tag_id: str) -> None:
    _validate_resource_id(asset_id)
    # tag_id may be hierarchical ("governance/PII"); the server validates it.
    response = client.session.put(
        f"{client.base_url}/api/assets/{asset_id}/assigned-tags/{tag_id}",
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status(response)


def _apply_tag_assignments(client: EntropyDataClient, asset_id: str, body: dict) -> SyncResult:
    """Replay an asset's ``assignedTags`` via the sub-resource endpoint.

    The asset PUT ignores ``assignedTags``, so tags are assigned separately.
    Idempotent: only tags not already present are added.
    """
    result = SyncResult()
    desired = body.get("assignedTags") or []
    if not desired:
        return result
    try:
        existing = set(_get_assigned_tags(client, asset_id))
    except ApiError:
        existing = set()
    for tag in desired:
        if tag in existing:
            continue
        try:
            _put_assigned_tag(client, asset_id, tag)
            console.print(f"    [green]OK[/green]   tag {tag}")
            result.ok += 1
        except ApiError as e:
            error_console.print(f"    [red]FAIL[/red] tag {tag}: {e}")
            result.fail += 1
    return result


# --- export --------------------------------------------------------------------


def _export_items(client: EntropyDataClient, resource: Resource, parent_id: str | None, target_dir: Path) -> SyncResult:
    """Enumerate one (flat resource) or one parent's children (nested) into ``target_dir``."""
    total = SyncResult()
    api_path = resource.path_for(parent_id)
    try:
        items = _list_all(client, resource, parent_id)
    except ApiError as e:
        error_console.print(f"  [red]FAIL[/red] list {resource.name}: {e}")
        total.fail += 1
        return total

    if not items:
        return total

    target_dir.mkdir(parents=True, exist_ok=True)
    for item in items:
        rid = item.get(resource.id_field)
        if rid is None:
            error_console.print(f"  [red]FAIL[/red] item without '{resource.id_field}'")
            total.fail += 1
            continue
        rid = str(rid)
        try:
            body = client.get_resource(api_path, rid) if resource.detail else item
            body = strip_audit_fields(body)
            path = target_dir / f"{sanitize_filename(rid)}.yaml"
            path.write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=4096))
            label = f"{parent_id}/{rid}" if parent_id else rid
            console.print(f"  [green]OK[/green]   {label}")
            total.ok += 1
        except ApiError as e:
            error_console.print(f"  [red]FAIL[/red] {rid}: {e}")
            total.fail += 1
    return total


def _export_singleton(client: EntropyDataClient, resource: Resource, target_dir: Path) -> SyncResult:
    """Fetch the singleton object and write it to ``<name>/<name>.yaml`` (skips when unset)."""
    total = SyncResult()
    try:
        body = strip_audit_fields(_get_singleton(client, resource))
    except ApiError as e:
        error_console.print(f"  [red]FAIL[/red] {resource.name}: {e}")
        total.fail += 1
        return total

    if not body:  # nothing configured on the source; nothing to copy
        return total

    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / f"{resource.name}.yaml").write_text(
        yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=4096)
    )
    console.print(f"  [green]OK[/green]   {resource.name}")
    total.ok += 1
    return total


def export_dir(client: EntropyDataClient, dest: Path, resources: list[Resource]) -> SyncResult:
    """Enumerate the source and write one YAML file per resource under ``dest``."""
    total = SyncResult()
    for resource in resources:
        console.print(f"\n[bold]{resource.name}[/bold]")
        if resource.singleton:
            total.add(_export_singleton(client, resource, dest / resource.name))
            continue
        if resource.document:
            try:
                parent_ids = _parent_ids(client, resource)
            except ApiError as e:
                error_console.print(f"  [red]FAIL[/red] list parents for {resource.name}: {e}")
                total.fail += 1
                continue
            for pid in parent_ids:
                total.add(_export_document(client, resource, pid, dest / resource.name))
            continue
        total.add(_export_items(client, resource, None, dest / resource.name))
    return total


# --- apply ---------------------------------------------------------------------


def _load_dir(resource_dir: Path, resource: Resource) -> list[tuple[str, dict]]:
    """Read every ``*.yaml`` file in a resource directory into (id, body) pairs."""
    entries: list[tuple[str, dict]] = []
    for f in sorted(resource_dir.glob("*.yaml")):
        data = yaml.safe_load(f.read_text())
        if not isinstance(data, dict):
            continue
        rid = data.get(resource.id_field)
        if rid is None:
            continue
        entries.append((str(rid), strip_audit_fields(data)))
    return entries


def _upsert_teams(
    client: EntropyDataClient, resource: Resource, api_path: str, entries: list[tuple[str, dict]]
) -> SyncResult:
    """Upsert teams parents-first, stripping members."""
    result = SyncResult()
    teams = {rid: {"data": {**body, "members": []}, "parent": body.get("parent")} for rid, body in entries}
    imported: set[str] = set()

    while len(imported) < len(teams):
        progress = False
        for tid, t in teams.items():
            if tid in imported:
                continue
            if t["parent"] is None or t["parent"] in imported:
                try:
                    client.put_resource(api_path, tid, t["data"])
                    console.print(f"  [green]OK[/green]   {tid}")
                    result.ok += 1
                except ApiError as e:
                    error_console.print(f"  [red]FAIL[/red] {tid}: {e}")
                    result.fail += 1
                imported.add(tid)
                progress = True
        if not progress:
            remaining = set(teams) - imported
            error_console.print(f"  [red]ERROR: circular or broken parent references: {remaining}[/red]")
            result.fail += len(remaining)
            break
    return result


def _upsert(
    client: EntropyDataClient,
    resource: Resource,
    api_path: str,
    entries: list[tuple[str, dict]],
    label_prefix: str = "",
) -> SyncResult:
    """Upsert one resource type via PUT-by-id (idempotent), continue-on-error."""
    if resource.topo_sort_parents:
        return _upsert_teams(client, resource, api_path, entries)

    result = SyncResult()
    for rid, body in entries:
        payload = {**body, "members": []} if resource.strip_members else body
        try:
            client.put_resource(api_path, rid, payload)
            console.print(f"  [green]OK[/green]   {label_prefix}{rid}")
            result.ok += 1
            if resource.tag_assignments:
                result.add(_apply_tag_assignments(client, rid, payload))
        except ApiError as e:
            error_console.print(f"  [red]FAIL[/red] {label_prefix}{rid}: {e}")
            result.fail += 1
    return result


def _order_for_deletion(resource: Resource, items: list[dict]) -> list[dict]:
    """For hierarchical resources, delete children before parents; else keep order."""
    if not resource.topo_sort_parents:
        return items

    remaining = {str(item[resource.id_field]): item for item in items}
    ordered: list[dict] = []
    while remaining:
        # A team is a leaf here if no other team still queued names it as parent.
        parents_in_play = {item.get("parent") for item in remaining.values()}
        leaves = [rid for rid in remaining if rid not in parents_in_play]
        if not leaves:  # cycle or broken refs: fall back to whatever is left
            leaves = list(remaining)
        for rid in leaves:
            ordered.append(remaining.pop(rid))
    return ordered


def _prune_one(
    client: EntropyDataClient,
    resource: Resource,
    api_path: str,
    keep: set[str],
    parent_id: str | None,
) -> SyncResult:
    """Delete target items of one (flat resource) or one parent scope (nested) absent from ``keep``."""
    result = SyncResult()
    try:
        existing = _list_all(client, resource, parent_id)
    except ApiError as e:
        error_console.print(f"  [red]FAIL[/red] list {resource.name}: {e}")
        result.fail += 1
        return result

    to_delete = [item for item in existing if str(item.get(resource.id_field)) not in keep]
    if not to_delete:
        return result

    label = f"{resource.name} [{parent_id}]" if parent_id else resource.name
    console.print(f"\n[bold]prune {label}[/bold]")
    for item in _order_for_deletion(resource, to_delete):
        rid = str(item[resource.id_field])
        try:
            client.delete_resource(api_path, rid)
            console.print(f"  [green]DEL[/green]  {rid}")
            result.ok += 1
        except ApiError as e:
            error_console.print(f"  [red]FAIL[/red] {rid}: {e}")
            result.fail += 1
    return result


def _prune(
    client: EntropyDataClient,
    resources: list[Resource],
    imported_ids: dict[str, object],
) -> SyncResult:
    """Delete target resources absent from the import set, in reverse dependency order.

    ``imported_ids[name]`` is a ``set[str]`` of the flat resource's imported ids.
    """
    result = SyncResult()
    for resource in reversed(resources):
        if resource.singleton or resource.document:
            continue  # one object / one document — not a prunable collection
        keep = imported_ids.get(resource.name) or set()
        result.add(_prune_one(client, resource, resource.api_path, keep, None))
    return result


@dataclass
class ImportPlan:
    """Result of a dry-run: per-resource create/update/prune counts."""

    counts: dict[str, PlanCounts] = field(default_factory=dict)


def plan_apply(
    client: EntropyDataClient,
    source: Path,
    resources: list[Resource],
    prune: bool = False,
) -> ImportPlan:
    """Compute create/update/(prune) counts without writing anything."""
    plan = ImportPlan()
    for resource in resources:
        resource_dir = source / resource.name

        if resource.singleton:
            # A singleton is one in-place PUT; count it as an update when the artifact has it.
            counts = PlanCounts(update=1) if _singleton_file(source, resource).is_file() else PlanCounts()
        elif resource.document:
            # One in-place PUT per parent document present in the artifact.
            n = len(list(resource_dir.glob("*.yaml"))) if resource_dir.is_dir() else 0
            counts = PlanCounts(update=n)
        else:
            entries = _load_dir(resource_dir, resource) if resource_dir.is_dir() else []
            imported = {rid for rid, _ in entries}
            try:
                existing = _enumerate_ids(client, resource)
            except ApiError as e:
                error_console.print(f"[red]FAIL[/red] list {resource.name}: {e}")
                existing = set()
            counts = PlanCounts(
                create=len(imported - existing),
                update=len(imported & existing),
                prune=len(existing - imported) if prune else 0,
            )

        if counts.create or counts.update or counts.prune:
            plan.counts[resource.name] = counts
    return plan


def apply_dir(
    client: EntropyDataClient,
    source: Path,
    resources: list[Resource],
    prune: bool = False,
) -> SyncResult:
    """Upsert every resource under ``source`` in dependency order, optionally pruning."""
    total = SyncResult()
    imported_ids: dict[str, object] = {}

    for resource in resources:
        resource_dir = source / resource.name
        if not resource_dir.is_dir():
            continue

        if resource.singleton:
            f = _singleton_file(source, resource)
            if not f.is_file():
                continue
            body = strip_audit_fields(yaml.safe_load(f.read_text()) or {})
            console.print(f"\n[bold]{resource.name}[/bold]")
            try:
                _put_singleton(client, resource, body)
                console.print(f"  [green]OK[/green]   {resource.name}")
                total.ok += 1
            except ApiError as e:
                error_console.print(f"  [red]FAIL[/red] {resource.name}: {e}")
                total.fail += 1
            continue

        if resource.document:
            header_printed = False
            for f in sorted(resource_dir.glob("*.yaml")):
                parent_id = f.stem
                if not header_printed:
                    console.print(f"\n[bold]{resource.name}[/bold]")
                    header_printed = True
                try:
                    _put_document(client, resource, parent_id, f.read_text())
                    console.print(f"  [green]OK[/green]   {parent_id}")
                    total.ok += 1
                except ApiError as e:
                    error_console.print(f"  [red]FAIL[/red] {parent_id}: {e}")
                    total.fail += 1
            continue

        entries = _load_dir(resource_dir, resource)
        imported_ids[resource.name] = {rid for rid, _ in entries}
        if not entries:
            continue
        console.print(f"\n[bold]{resource.name}[/bold]")
        total.add(_upsert(client, resource, resource.api_path, entries))

    if prune:
        total.add(_prune(client, resources, imported_ids))

    return total
