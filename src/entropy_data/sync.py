"""Export / import / prune engine for the portable resource set.

All three user-facing commands (`export dir`, `import dir`/`import zip`, `apply`)
are thin wrappers over the functions here so they share one enumeration, upsert
and prune implementation and cannot drift. Everything is continue-on-error: a
single resource failure is logged and counted, never aborts the run.
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
from entropy_data.resources import Resource, sanitize_filename, strip_audit_fields


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


def _list_all(client: EntropyDataClient, resource: Resource) -> list[dict]:
    """Return every item of a resource, following ``Link: rel="next"`` if paginated."""
    if not resource.paginated:
        items, _ = client.list_resources(resource.api_path)
        return list(items)

    items: list[dict] = []
    page = 0
    while True:
        batch, has_next = client.list_resources(resource.api_path, params={"p": page})
        items.extend(batch)
        if not has_next:
            break
        page += 1
    return items


def _enumerate_ids(client: EntropyDataClient, resource: Resource) -> set[str]:
    """Return the set of resource ids currently on the target (for prune / dry-run)."""
    return {str(item[resource.id_field]) for item in _list_all(client, resource) if item.get(resource.id_field)}


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


def export_dir(client: EntropyDataClient, dest: Path, resources: list[Resource]) -> SyncResult:
    """Enumerate the source and write one YAML file per resource under ``dest``."""
    total = SyncResult()
    for resource in resources:
        console.print(f"\n[bold]{resource.name}[/bold]")
        try:
            items = _list_all(client, resource)
        except ApiError as e:
            error_console.print(f"  [red]FAIL[/red] list {resource.name}: {e}")
            total.fail += 1
            continue

        if not items:
            console.print("  (none)")
            continue

        target_dir = dest / resource.name
        target_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            rid = item.get(resource.id_field)
            if rid is None:
                error_console.print(f"  [red]FAIL[/red] item without '{resource.id_field}'")
                total.fail += 1
                continue
            rid = str(rid)
            try:
                body = client.get_resource(resource.api_path, rid) if resource.detail else item
                body = strip_audit_fields(body)
                path = target_dir / f"{sanitize_filename(rid)}.yaml"
                path.write_text(yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=4096))
                console.print(f"  [green]OK[/green]   {rid}")
                total.ok += 1
            except ApiError as e:
                error_console.print(f"  [red]FAIL[/red] {rid}: {e}")
                total.fail += 1
    return total


# --- import --------------------------------------------------------------------


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


def _upsert_teams(client: EntropyDataClient, resource: Resource, entries: list[tuple[str, dict]]) -> SyncResult:
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
                    client.put_resource(resource.api_path, tid, t["data"])
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


def _upsert(client: EntropyDataClient, resource: Resource, entries: list[tuple[str, dict]]) -> SyncResult:
    """Upsert one resource type via PUT-by-id (idempotent), continue-on-error."""
    if resource.topo_sort_parents:
        return _upsert_teams(client, resource, entries)

    result = SyncResult()
    for rid, body in entries:
        payload = {**body, "members": []} if resource.strip_members else body
        try:
            client.put_resource(resource.api_path, rid, payload)
            console.print(f"  [green]OK[/green]   {rid}")
            result.ok += 1
            if resource.tag_assignments:
                result.add(_apply_tag_assignments(client, rid, payload))
        except ApiError as e:
            error_console.print(f"  [red]FAIL[/red] {rid}: {e}")
            result.fail += 1
    return result


def _prune(
    client: EntropyDataClient,
    resources: list[Resource],
    imported_ids: dict[str, set[str]],
) -> SyncResult:
    """Delete target resources absent from the import set, in reverse dependency order."""
    result = SyncResult()
    for resource in reversed(resources):
        keep = imported_ids.get(resource.name, set())
        try:
            existing = _list_all(client, resource)
        except ApiError as e:
            error_console.print(f"  [red]FAIL[/red] list {resource.name}: {e}")
            result.fail += 1
            continue

        to_delete = [item for item in existing if str(item.get(resource.id_field)) not in keep]
        if not to_delete:
            continue

        console.print(f"\n[bold]prune {resource.name}[/bold]")
        ordered = _order_for_deletion(resource, to_delete)
        for item in ordered:
            rid = str(item[resource.id_field])
            try:
                client.delete_resource(resource.api_path, rid)
                console.print(f"  [green]DEL[/green]  {rid}")
                result.ok += 1
            except ApiError as e:
                error_console.print(f"  [red]FAIL[/red] {rid}: {e}")
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


@dataclass
class ImportPlan:
    """Result of a dry-run: per-resource create/update/prune counts."""

    counts: dict[str, PlanCounts] = field(default_factory=dict)


def plan_import(
    client: EntropyDataClient,
    source: Path,
    resources: list[Resource],
    prune: bool = False,
) -> ImportPlan:
    """Compute create/update/(prune) counts without writing anything."""
    plan = ImportPlan()
    for resource in resources:
        resource_dir = source / resource.name
        entries = _load_dir(resource_dir, resource) if resource_dir.is_dir() else []
        imported_ids = {rid for rid, _ in entries}

        try:
            existing_ids = _enumerate_ids(client, resource)
        except ApiError as e:
            error_console.print(f"[red]FAIL[/red] list {resource.name}: {e}")
            existing_ids = set()

        counts = PlanCounts(
            create=len(imported_ids - existing_ids),
            update=len(imported_ids & existing_ids),
            prune=len(existing_ids - imported_ids) if prune else 0,
        )
        if counts.create or counts.update or counts.prune:
            plan.counts[resource.name] = counts
    return plan


def import_dir(
    client: EntropyDataClient,
    source: Path,
    resources: list[Resource],
    prune: bool = False,
) -> SyncResult:
    """Upsert every resource under ``source`` in dependency order, optionally pruning."""
    total = SyncResult()
    imported_ids: dict[str, set[str]] = {}

    for resource in resources:
        resource_dir = source / resource.name
        if not resource_dir.is_dir():
            continue
        entries = _load_dir(resource_dir, resource)
        imported_ids[resource.name] = {rid for rid, _ in entries}
        if not entries:
            continue
        console.print(f"\n[bold]{resource.name}[/bold]")
        total.add(_upsert(client, resource, entries))

    if prune:
        total.add(_prune(client, resources, imported_ids))

    return total
