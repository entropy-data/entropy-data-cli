# Design plan: `entropy-data apply`

Status: **design only, not implemented.** This document captures the analysis and the
agreed design for a new command that copies all portable org state from one Entropy Data
instance to another (e.g. promote a test environment's state to prod).

It also captures the app-side REST API gaps that must be closed first, because `apply` can
only copy state the public API exposes.

---

## 1. Goal

`entropy-data apply` replicates the **declarative org state** of a source instance onto a
target instance. Not a database clone — only resources that are (a) reachable through the
public `/api/**` REST API and (b) portable across instances (no secrets, no telemetry, no
env-specific identity).

Decisions taken during design:

- **Mechanism: export-then-import, always staged.** `apply` writes a local artifact, then
  imports it. The artifact is always produced (auditable, re-runnable), not streamed only.
- **Pruning: mirror with opt-in `--prune`.** Default is upsert-only; `--prune` additionally
  deletes target resources absent from source.
- **Scope of first cut: portable core + fix the `sourcesystems` drop bug.** The four
  additional writable resources (certifications, classification-schemes, example-data,
  semantics) slot into the canonical order and can ship as a fast-follow.
- **`uploaded_image` branding blobs are out of scope** — deliberately not copied and not
  tracked as a gap. Logos/icons are re-uploaded on the target.

---

## 2. Command shape

Export-then-import naturally fills a missing primitive: there is **no `export` command**
today (only `import zip`). The clean decomposition is three commands:

```
entropy-data export dir <path>  -c <source>              # NEW — enumerate source → local YAML tree
entropy-data import dir <path>  -c <target> [--prune]    # EXTEND — import currently only does `zip`
entropy-data apply  -c <source> --to <target> [--prune] [--keep <dir>] [--dry-run] \
                    [--include <r,...>] [--exclude <r,...>]
        # = export to a staged dir (temp, or --keep <dir> to retain) → import into target
```

- Reuses the existing named-connection resolver (`config.py`): `-c/--connection` already
  exists; add `--to` (a second named connection) resolved through the same
  `resolve_connection` path. No new auth plumbing.
- Artifact layout mirrors the app's `OrganizationExportService`: one directory per resource
  type, one `*.yaml` per resource named by `externalId`; top-level `id` field = identity.
  Keeps the CLI artifact interchangeable with the app's org-export zip.

### Cross-cutting behavior

- **`--dry-run`** — print per-type create/update/(prune) counts; no writes. Essential for
  test→prod.
- **`--include` / `--exclude <resource>`** — filter the resource set.
- **Idempotent** — all writes are PUT-by-externalId; re-runs converge.
- **Partial-failure policy** — continue-on-error (matches current `import`), collect
  failures, print a per-resource summary, exit non-zero if any failed. A half-applied target
  is safe to re-run.
- **Pagination** — enumeration must follow `Link: rel="next"` (tags, assets, certifications,
  etc. are paginated).
- **Strip audit fields** (`createdAt/By`, `updatedAt/By`) before PUT if any GET returns them.

---

## 3. Resource classification

`COPY` = portable declarative state keyed by stable `externalId`.
`TRANSFORM` = copyable shell, but refs/secrets/members must be rewritten or stripped.
`SKIP` = secret, telemetry, singleton identity, or read-only.

### COPY — the portable core (dependency order)

| # | Resource | In org-export? | In CLI `import`? | Notes |
|---|----------|:--:|:--:|---|
| 1 | teams | yes | yes | strip `members`; topo-sort parents first |
| 2 | tags | yes | yes | `owner` → team; needs teams first |
| 3 | definitions | yes | yes | → teams |
| 4 | policies | yes | yes | independent |
| 5 | sourcesystems | yes | **NO (bug)** | export writes it, current `import` silently drops it |
| 6 | certifications | no | no | gap — full CRUD, no deps; paginated list |
| 7 | classification-schemes | no | no | gap — whole-scheme PUT replaces all values |
| 8 | assets | yes | yes | → teams; tag assignments are a second sub-resource pass |
| 9 | datacontracts | yes | yes | → teams, assets. Warn if ODCS `servers` populated (env-specific) |
| 10 | dataproducts | yes | yes | → teams, contracts, assets. Skip `star`/`stargazers` |
| 11 | example-data | no | no | gap — → dataproducts (copy after) |
| 12 | semantics (ns→concepts→rels) | no | no | gap, experimental; strict internal order |
| 13 | access (DUAs) | yes | yes | last. Warn on `consumer.userId` (env-specific); approvals not replayed |

Canonical order for a shared `RESOURCE_ORDER` module (used by `export`, `import`, `apply`
so they can't drift):

```
teams → tags → definitions → policies → sourcesystems →
certifications → classification-schemes → assets →
datacontracts → dataproducts → example-data → semantics → access
```

### TRANSFORM

- **teams** — strip `members` (users are per-instance identities; `apply` owns this strip —
  it is *not* enforced by the client).
- **assets** — copy resource, then tag assignments (`PUT /assets/{id}/assigned-tags/{tagId}`)
  after `tags` exist.
- **access** — land as `requested`; do **not** auto-replay `/approve`. Flag `consumer.userId`
  that won't resolve on target.
- **settings/team-roles + settings/scim-mapping** — opt-in access config, see §5.

### SKIP

- **Secrets (unreadable / write-only):** git-credentials (token never returned),
  integrations (no create endpoint + decrypted creds never emitted), api-keys (POST-only,
  shown once).
- **Telemetry / derived:** costs, usage/traces, lineage, events, test-results, feed-item,
  connector health/state, policy check-runs.
- **Read-only / CLI-local:** organization settings & members (GET-only), search, schemas,
  connection profiles.
- **Env / IdP / identity singletons:** customization (branding), `organization/settings.sso`,
  SCIM v2 Users/Groups, snowflake/powerbi OAuth settings, MCP clients,
  user_datasource_connection.
- **User-scoped:** saved_filter.
- **Transactional workflow:** change_request (like access requests).
- **Dead/dropped:** meetings, aws/azure subscriptions.
- **Out of scope by decision:** uploaded_image branding blobs.

---

## 4. Bugs / inconsistencies found during analysis

1. **`import zip` silently drops `sourcesystems/`.** The app export produces the directory,
   but `RESOURCE_ORDER` in `import_export.py` omits it. Any `apply` built on the import path
   inherits this. Fix in the same work.
2. **Members asymmetry.** The org-export *embeds* team members; `import` *strips* them
   (`data["members"] = []`). Correct behavior, but it means the export zip is not a faithful
   round-trip, and `apply` must own the strip itself.

---

## 5. SSO / SCIM — conditional portability (do not blanket-skip)

The SSO/SCIM area is **not** uniformly skippable. It splits:

**Hard SKIP (structurally non-portable):**
- `organization/settings.sso` (issuer, tenant, autoJoin) — GET-only, no PUT; target's own
  IdP wiring identity.
- `/api/scim/v2/Users` + `/Groups` — the IdP's live provisioning target, not declarative
  state. Copying would fabricate/duplicate identities.
- `organization/members` — GET-only, IdP/SSO-provisioned.

**Conditionally portable, opt-in (`settings/team-roles` + `settings/scim-mapping`):**
these are declarative config, **not** user data. `ScimMappingConfiguration` maps
`scimGroup` (IdP group *display name*) → `type` (`organizationOwner` | `teamMemberRole`) →
`teamId` (team externalId) + `teamMemberRole` (role name). Three consequences:

1. **Dependency chain:** `team-roles` (role catalog) → `teams` (teamId) → `scim-mapping`.
   Order matters; not independent singletons.
2. **Conditional portability, keyed on IdP group display name**
   (`ScimMappingService` matches `mapping.scimGroup == scimGroup.displayName`):
   - Same IdP + same group names across test/prod → mapping is portable and valuable.
   - Different IdP / group names → every mapping silently **no-ops** on the target.
3. **Live blast radius — side-effectful, not inert config.**
   `ApiScimMappingController.saveScimMapping` calls `handleGroupsUpdatedByOrganizationId` on
   **every PUT**: writing the mapping to prod immediately re-runs it, adding/removing real
   team members and flipping `organizationOwner` on live users. And `ScimMappingService`
   listens on `TeamCreatedEvent`/`TeamUpdatedEvent`, so **applying teams re-runs any mapping
   that already exists on the target.**

**Design consequence:** `team-roles` + `scim-mapping` are a distinct opt-in "access config"
group (`--include settings/team-roles,settings/scim-mapping`), never in the default sweep,
applied in order team-roles → (teams) → scim-mapping, gated behind `--dry-run` + explicit
confirm (treat like `--prune`). Warn on the silent-dud case (target SCIM group names don't
match source). Document the latent team-apply side effect.

---

## 6. App-side REST API gaps (prerequisites)

`apply` can only copy what the API exposes. Two genuine gaps and one spec fix must ship and
deploy **before** the CLI can consume them.

### 6.1 `organization_features` — add an org-singleton pair (highest value)

Portable behavior/governance config with **no API today** (managed only by scattered web
controllers): `changeProcessMode`, `managedTagsPolicy`, `customTeamRolesEnabled`,
`openInOptions[]`, `customScript`, `intelligenceEnabled`,
`intelligenceQueryExecutionEnabled`, `dataContractTestsEnabled` / `dataContractTestsTags`.

- Add `GET /api/organization/features` + `PUT /api/organization/features` (singleton, mirrors
  `/api/settings/customization`; no externalId).
- Mask/omit `dataContractTestsApiKey` (secret) and `dataContractTestsApiEndpoint`
  (env-specific); exclude `showIntro` (transient UI state); no audit fields.
- Note: the `features/` *package* (`FeaturesCloud`, …) is compile-time plan gating, **not**
  this table — do not conflate.

### 6.2 `dataproductbuilder` — add API, needs a schema change first

Org-scoped declarative builder templates (name, plugin repo, supported agents, archetypes,
capabilities, team/tag refs) managed only via web forms.

- **Blocker:** the table has no `externalId` column (DB UUID only; `name` is mutable/
  non-unique). Add an `externalId` column (migration) before exposing an API.
- Then `GET /api/dataproductbuilders` (list) + `GET`/`PUT /api/dataproductbuilders/{externalId}`;
  reference teams by **team externalId**, not internal UUIDs.

### 6.3 Notification-channels — spec fix only, no new code

The list endpoint `GET /api/teams/{teamExternalId}/notification-channels` **already exists in
the controller** but is **missing from `openapi.yaml`**, and the documented single-channel
path has stale param names (`teamId`/`channelId` → `teamExternalId`/
`notificationChannelExternalId`). Add the list path + fix params. (Caveat: GET returns the
webhook URL, which is itself the Slack/Teams secret — fine for round-trip, but it is a
secret-exposing endpoint.)

### Confirmed NOT gaps (no new endpoint)

- certifications, classification-schemes, example-data, semantics → already have GET/PUT;
  these are CLI-import gaps, not API gaps.
- custom fields / custom schemas → definitions writable via `PUT /api/settings/customization`;
  `ApiSchemasController` serves derived schemas (read-only by design).
- input ports, SLOs → embedded in dataproduct/contract YAML (SLO tables dropped).
- integrations → GET never emits encrypted secrets; a config-only PUT would half-create broken
  integrations. Recreate at target.
- connector → API complete; body is agent health/state + API-key linkage (not portable).
- AI settings, snowflake/powerbi OAuth, MCP clients, user_datasource_connection → secrets /
  env-specific.
- saved_filter → per-user preference.
- change_request → transactional approval workflow.
- feed_item → derived activity stream.
- meetings, aws/azure subscriptions → dead (dropped by migration).

---

## 7. Open questions

1. Reference validation — a pre-flight pass reporting dangling `userId` / `servers` /
   credential refs, or warn inline during import?
2. `--prune` confirmation UX — interactive prompt vs. require `--yes`.
3. Should `export` / `import dir` be first-class documented commands, or internal to `apply`?
   (Recommend first-class — the artifact is independently useful.)

---

## 8. Sequencing

1. **App PRs** — `organization/features` endpoint, `dataproductbuilder` (migration + endpoint),
   notification-channels openapi fix. Deploy to the relevant instances.
2. **CLI** — shared `RESOURCE_ORDER` module; `export dir`; extend `import` with `dir`;
   `apply` orchestrating export→import with `--prune` / `--dry-run` / filters. Fix the
   `sourcesystems` drop. Add certifications/classification-schemes/example-data/semantics.

The app-side API work gates the CLI work: `apply` cannot reach `organization/features` or
`dataproductbuilder` until those endpoints exist on the target instance.
</content>
</invoke>
