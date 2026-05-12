# Changelog

## [Unreleased]

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
