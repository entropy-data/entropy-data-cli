# Changelog

## [Unreleased]

## [0.3.17]

- Add `entropy-data classifications list|get|put|delete` for managing classification schemes (`GET /api/classification-schemes`, `GET|PUT|DELETE /api/classification-schemes/{schemeExternalId}`). Classification schemes define sensitivity tiers (e.g. Public, Internal, Sensitive) that can be assigned to data products, data contracts, and semantic concepts; each scheme is addressed by its stable `externalId` and carries its tiers inline.

## [0.3.16]

- Add the global `--system-truststore` option (env `ENTROPY_DATA_SYSTEM_TRUSTSTORE`) to verify TLS using the operating system's certificate trust store instead of the bundled CA certificates, for use behind a corporate proxy or with an internal CA.

## [0.3.15]

- Replace `entropy-data organization custom-team-roles ...` and the interim `organization team-roles-mode` command with `entropy-data settings team-roles get|put`. The configuration is now a single aggregate payload — `{mode: default}` or `{mode: custom-team-roles, team-roles: [...]}` — wrapping the new `GET`/`PUT /api/settings/team-roles`. `put` replaces the whole catalog when mode is `custom-team-roles`; an empty catalog or dropping a role still assigned to a member is rejected with 409.

## [0.3.14]

- `integrations` commands now address an integration by its `externalId` only; the internal UUID is no longer accepted. The API is now externalId-native — every path keys on `externalId` (`GET /api/integrations/{externalId}`, `.../runs`, `.../run`, `.../cancel`) and responses no longer return the internal `ingestionId`. Run and trigger output reference their integration via `integrationExternalId`. Display `name` is still accepted and resolved client-side.
- `entropy-data integrations get` inlines the integration's decrypted `configuration` (credentials excluded), so a single call returns both metadata and configuration; use `-o yaml` for a YAML view. The separate `integrations configuration` command is dropped as redundant.
- Add `entropy-data integrations runs-latest <integration>` to fetch the most recent ingestion run. Wraps `GET /api/integrations/{externalId}/runs/latest`.

## [0.3.13]

- Add `entropy-data organization custom-team-roles list|get|put|delete` to manage organization-scoped custom team roles. `put` creates, updates, or renames a role and accepts repeated or comma-separated `--permissions`.
- `entropy-data connection add` now also prompts for the host when the call is interactive (no `--api-key` given), defaulting to `https://api.entropy-data.com` when confirmed with enter. Previously the host silently fell back to the cloud default in the interactive flow, making it easy to store a connection to the wrong instance (e.g. when targeting a local Community Edition). Scripted calls that pass `--api-key` are unaffected and keep defaulting silently.

## [0.3.12]

- Add `entropy-data integrations runs-get <integration> <run-id>` to fetch a single ingestion run by id. Wraps `GET /api/integrations/{ingestionId}/runs/{ingestionRunId}`, the last documented API endpoint not yet exposed by the CLI. Like the other `integrations` commands, the integration argument accepts an `externalId`, display `name`, or UUID.

## [0.3.11]

- Add `entropy-data integrations list|get|configuration|runs|run|cancel` to manage native data-platform integrations (Snowflake, Databricks, BigQuery, Postgres, MySQL, MariaDB, MSSQL, Glue, Alation, Fabric, Power BI). Wraps the new `/api/integrations` endpoints. Commands accept the integration's `externalId`, display `name`, or UUID; name-to-UUID resolution happens client-side. `integrations run` supports `--wait` to poll the run until it reaches a terminal status (SUCCESS, FAILED, CANCELLED), useful for CI and automation that wants to know the outcome before continuing.

## [0.3.10]

- `--output yaml` no longer produces invalid YAML. Output was printed through the Rich console, which soft-wraps to the terminal width (80 cols when not a TTY) and parses markup, breaking long scalar values mid-token when piped or redirected to a file. Machine formats (`json`/`yaml`) are now written straight to stdout.
- `entropy-data connection get` with `--output json`/`yaml` now returns the API key in clear text. Machine formats are consumed by scripts (e.g. exporting the key for another tool); masking only broke automation and added no security since the key is already stored in plaintext locally. The mask / `--show-api-key` flag now governs the human `table` view only.

## [0.3.9]

- `entropy-data access request` now sets `info.startDate` to today by default. Without it, the platform left auto-approved agreements with `info.active: false`, and lineage / input-port views silently skipped them.

## [0.3.8]

- Add `entropy-data policies list|get|put|delete` to manage policies. Wraps `/api/policies` and `/api/policies/{externalId}`.

## [0.3.7]

- Add `yaml` as a third value for `--output` / `-o` alongside `table` and `json`. Useful when piping results into editors or files that expect YAML (e.g. data contracts).
- `entropy-data access list` now supports `--provider-dataproduct`, `--consumer-dataproduct`, and `--consumer-type` filters, passed through to the existing `providerDataProductId`, `consumerDataProductId`, and `consumerType` query parameters of `GET /api/access`.

## [0.3.6]

- `entropy-data connection add` now sets the newly added connection as the default, overriding any previously set default.

## [0.3.5]

- Add `entropy-data semantics search <namespace> <query> [--kind <kind>] [--limit <n>]` for case-insensitive substring search across concept id, name, and description in a namespace. Implemented client-side over the existing `GET /api/semantics/experimental/namespaces/{ns}/concepts` endpoint.
- Add `entropy-data access request <data-product-id> <output-port-id> --purpose <text> --consumer-team|--consumer-user|--consumer-dataproduct <id> [--roles <comma-list>] [--id <agreement-id>]` to submit an access request for a provider output port. Wraps `PUT /api/access/{id}` and auto-generates a UUID when `--id` is omitted.

## [0.3.4]

- Add `entropy-data datacontracts yaml <id>` to fetch a data contract as ODCS YAML (writes to stdout or `--file`). Backed by `GET /api/datacontracts/{id}.yaml`.
- Add `entropy-data datacontracts generate <id> --type <kind>` for code generation (`sql-select`, `sql-ddl`, `dbt-models`, `dbt-sources`, `json-schema`, `pydantic`, `custom`). With `--out-dir`, each returned file is written to disk; without it, the JSON response is printed.
- Add `entropy-data dataproducts import-from-git` and `entropy-data datacontracts import-from-git` to import resources from a Git repository (flags or `--file body.json`).
- Add `entropy-data organization members list` and `entropy-data organization members get <email>` to inspect organization membership.
- Add `entropy-data settings get-scim-mapping` and `entropy-data settings put-scim-mapping` to manage the SCIM group mapping (YAML or JSON, mirrors the customization commands).
- Add `entropy-data connectors list|get|put|delete` to manage connector state.
- Add `entropy-data assets tags list|add|remove` to manage tag assignments on data assets.
- Add `entropy-data organization git-credentials list|get|create|update|delete` and `entropy-data teams git-credentials list|get|create|update|delete <team-id>` to manage organization- and team-level git credentials. Pass `--authentication-token -` to read the secret from stdin.
- Add `entropy-data teams notifications get|put|delete <team-id> <channel-id>` to manage a team's notification channels.
- Add EXPERIMENTAL `entropy-data semantics namespaces list|get|put|delete`, `entropy-data semantics concepts list|get|put|delete <namespace> [<external-id>]`, and `entropy-data semantics relationships list|get|put|delete <namespace> [<external-id>]` covering the `/api/semantics/experimental/...` endpoints. PUT commands enforce that any `namespace`/`id` in the body matches the path argument.

## [0.3.3]

- Add `entropy-data organization get` to fetch organization settings (vanity URL, host, full name, plan, SSO) for the API key in use. Backed by the new `GET /api/organization/settings` endpoint.
- Add `entropy-data connection get [name]` to inspect a stored connection. API key is masked by default; pass `--show-api-key` to print it in clear text. Use `-o json` for scripting.
- `entropy-data connection add` auto-fetches the organization vanity URL via `/api/organization/settings` and stores it on the connection. Best-effort: older servers or network errors fall back to no vanity URL.
- `connection list` surfaces the stored vanity URL.

## [0.3.2]

- Add `git-connection` subcommands to `dataproducts` and `datacontracts`

## [0.3.1]

- Support Python 3.11 (lowered minimum from 3.12)

## [0.3.0]

- Rename PyPI package from `entropy-data-cli` to `entropy-data`. Install with `pip install entropy-data` (or `uv tool install entropy-data`). The CLI command remains `entropy-data`.

## [0.2.3]

- Add `.env` file support for project-specific configuration via `python-dotenv`
- Document release process in README

## [0.2.2]

- Fix version reporting to read from package metadata instead of hardcoded value

## [0.2.1]

- Add Docker Hub publish to CI and release workflows

## [0.2.0]

- Fix negative page numbers leaking SQL queries from the server
- Fix mismatched resource ID in body vs CLI argument silently using body ID
- Fix HTML error responses (e.g., from Tomcat) displayed as raw markup
- Add max resource ID length validation (256 characters)
- Add 30s HTTP request timeout to prevent hanging on unreachable hosts

## [0.1.0]

- Initial release
- CRUD commands for data products, data contracts, access, teams, source systems, definitions, certifications, example data, test results
- Access workflow commands: approve, reject, cancel
- Event polling and search
- Connection management with `~/.entropy-data/config.toml`
- Table and JSON output formats
