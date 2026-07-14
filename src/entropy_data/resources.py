"""Shared definition of the portable resource set and its dependency order.

`export`, `import` and `apply` all consume :data:`RESOURCE_ORDER` so they cannot
drift: the same directory names, API paths, identity fields and per-resource
handling flags drive enumeration (export), upsert (import) and orchestration
(apply).

The canonical dependency order is:

    teams -> tags -> definitions -> policies -> sourcesystems ->
    certifications -> classification-schemes -> assets ->
    datacontracts -> dataproducts -> example-data -> access

Pruning walks this list in reverse so dependents are removed before their
dependencies.
"""

from dataclasses import dataclass

# Persistence bookkeeping that must never be sent back on a PUT. The public API
# does not accept these, and a GET should not surface them, but strip defensively.
AUDIT_FIELDS = ("createdAt", "createdBy", "updatedAt", "updatedBy", "created_at", "updated_at")

# Characters that are invalid in filenames on common filesystems. Mirrors the
# app's OrganizationExportService.sanitizeFilename so the artifacts interchange.
_FILENAME_INVALID = '\\/:*?"<>|'


@dataclass(frozen=True)
class Resource:
    """One copyable resource type.

    name        directory name in the artifact tree and logical key for filters
    api_path    path segment for ``/api/{api_path}`` list/get/put/delete
    id_field    body field holding the stable identity (path id + filename)
    paginated   list follows ``Link: rel="next"`` (``p`` query param)
    detail      GET each item individually for the full body (list is partial)
    strip_members   drop ``members`` before PUT (teams: users are per-instance)
    topo_sort_parents   order writes so a parent is created before its children
    tag_assignments     after PUT, replay ``assignedTags`` via the sub-resource
                        endpoint ``PUT /assets/{id}/assigned-tags/{tagId}``
    """

    name: str
    api_path: str
    id_field: str = "id"
    paginated: bool = False
    detail: bool = False
    strip_members: bool = False
    topo_sort_parents: bool = False
    tag_assignments: bool = False


RESOURCE_ORDER: list[Resource] = [
    Resource("teams", "teams", paginated=True, strip_members=True, topo_sort_parents=True),
    Resource("tags", "tags", paginated=True),
    Resource("definitions", "definitions", paginated=True),
    Resource("policies", "policies"),
    Resource("sourcesystems", "sourcesystems", paginated=True),
    Resource("certifications", "certifications"),
    Resource("classification-schemes", "classification-schemes", id_field="externalId"),
    # assets list omits assignedTags and returns a partial body, so fetch each one.
    Resource("assets", "assets", paginated=True, detail=True, tag_assignments=True),
    # datacontracts / dataproducts list endpoints return only top-level fields.
    Resource("datacontracts", "datacontracts", detail=True),
    Resource("dataproducts", "dataproducts", detail=True),
    Resource("example-data", "example-data"),
    Resource("access", "access", paginated=True),
    # TODO: semantics (namespaces -> concepts -> relationships) is deliberately
    # excluded. The experimental semantics API is nested (concepts and
    # relationships live under a namespace path), which does not fit this flat
    # one-directory-per-resource model without a bespoke multi-level walker. Add
    # nested export/import support if/when semantics graduates from experimental.
]

RESOURCE_BY_NAME: dict[str, Resource] = {r.name: r for r in RESOURCE_ORDER}


def sanitize_filename(resource_id: str) -> str:
    """Make a resource id safe as a filename (ids may contain ``/``, ``:`` etc.)."""
    return "".join("_" if c in _FILENAME_INVALID else c for c in resource_id)


def strip_audit_fields(body: dict) -> dict:
    """Return a copy of ``body`` without top-level audit fields."""
    return {k: v for k, v in body.items() if k not in AUDIT_FIELDS}


def select_resources(
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[Resource]:
    """Filter :data:`RESOURCE_ORDER` by name, preserving dependency order.

    Raises ``ValueError`` naming any unknown resource so a typo in ``--include``
    or ``--exclude`` fails loudly instead of silently copying nothing.
    """
    unknown = sorted({n for n in (include or []) + (exclude or []) if n not in RESOURCE_BY_NAME})
    if unknown:
        known = ", ".join(r.name for r in RESOURCE_ORDER)
        raise ValueError(f"Unknown resource(s): {', '.join(unknown)}. Known resources: {known}")

    result = RESOURCE_ORDER
    if include:
        included = set(include)
        result = [r for r in result if r.name in included]
    if exclude:
        excluded = set(exclude)
        result = [r for r in result if r.name not in excluded]
    return result
