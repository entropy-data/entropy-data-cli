"""Shared definition of the portable resource set and its dependency order.

`export`, `import` and `sync` all consume :data:`RESOURCE_ORDER` so they cannot
drift: the same directory names, API paths, identity fields and per-resource
handling flags drive enumeration (export), upsert (import) and orchestration
(sync).

The canonical dependency order is:

    teams -> tags -> definitions -> policies -> sourcesystems ->
    certifications -> classification-schemes -> assets ->
    datacontracts -> dataproducts -> example-data -> access ->
    semantic-namespaces -> semantic-ontology -> organization-features

Pruning walks this list in reverse so dependents are removed before their
dependencies.

Three resource shapes:

* Flat — ``/api/{api_path}`` lists the whole organization and
  ``/api/{api_path}/{id}`` addresses one. Artifact: ``<name>/<id>.yaml``.
* Document (``document`` set, with a ``{parent}`` ``api_path``) — one raw-YAML
  document per parent, GET/PUT directly at the expanded path. Enumerated by
  listing the parent. Artifact: ``<name>/<parent_id>.yaml``. Not prunable. Used
  for the semantic ontology: the app imports the whole namespace document in the
  correct internal order (groups before members), so the client needs no
  per-concept ordering of its own.
* Singleton (``singleton`` set) — one org-level object read/written directly at
  ``/api/{api_path}`` (no id, no list). Artifact: ``<name>/<name>.yaml``. Not
  prunable. ``organization-features`` is applied last so a restrictive policy it
  carries cannot reject the resources imported before it.
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
    parent      name of the parent resource; when set, ``api_path`` is a
                ``{parent}`` template expanded per parent id
    singleton   one org-level object at ``/api/{api_path}`` (no id, no list, not
                prunable) rather than a collection
    document    one raw-YAML document per parent, GET/PUT directly at the expanded
                ``{parent}`` path (not prunable); requires ``parent``
    """

    name: str
    api_path: str
    id_field: str = "id"
    paginated: bool = False
    detail: bool = False
    strip_members: bool = False
    topo_sort_parents: bool = False
    tag_assignments: bool = False
    parent: str | None = None
    singleton: bool = False
    document: bool = False

    def path_for(self, parent_id: str | None = None) -> str:
        """Resolve ``api_path`` for a given parent id (identity for flat resources)."""
        if self.parent is None:
            return self.api_path
        if parent_id is None:
            raise ValueError(f"Resource '{self.name}' is under '{self.parent}' and needs a parent id.")
        return self.api_path.format(parent=parent_id)


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
    # Semantics: the namespace row carries the metadata; the whole ontology (concepts +
    # relationships) is copied as one OSI YAML document per namespace via the app's
    # ontology.yaml endpoint, which imports it in the correct internal dependency order.
    Resource("semantic-namespaces", "semantics/experimental/namespaces", id_field="namespace"),
    Resource(
        "semantic-ontology",
        "semantics/experimental/namespaces/{parent}/ontology.yaml",
        parent="semantic-namespaces",
        document=True,
    ),
    # Org-level singleton. Applied last: it may carry a restrictive managedTagsPolicy
    # that would otherwise reject tag/asset imports running earlier in the same sync.
    # Requires the app-side GET/PUT /api/organization/features endpoint (entropy-data#1521).
    Resource("organization-features", "organization/features", singleton=True),
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
