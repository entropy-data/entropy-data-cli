# Entropy Data CLI

<p>
  <a href="https://github.com/entropy-data/entropy-data-cli/actions/workflows/ci.yaml?query=branch%3Amain">
    <img alt="CI" src="https://img.shields.io/github/actions/workflow/status/entropy-data/entropy-data-cli/ci.yaml?branch=main"></a>
  <a href="https://pypi.org/project/entropy-data/">
    <img alt="PyPI" src="https://img.shields.io/pypi/v/entropy-data" /></a>
  <a href="https://pypi.org/project/entropy-data/">
    <img alt="Python" src="https://img.shields.io/pypi/pyversions/entropy-data" /></a>
</p>

The `entropy-data` CLI lets you manage your [Entropy Data](https://entropy-data.com) platform from the command line.

You can manage data products, data contracts, access agreements, teams, source systems, definitions, certifications, and more — directly from your terminal or CI/CD pipeline.

- Docs: [https://docs.entropy-data.com](https://docs.entropy-data.com)
- PyPI: [https://pypi.org/project/entropy-data/](https://pypi.org/project/entropy-data/)
- GitHub: [https://github.com/entropy-data/entropy-data-cli](https://github.com/entropy-data/entropy-data-cli)

## Install

Requires Python >= 3.11.

```bash
uv tool install entropy-data
entropy-data --help
```

Or with pip:

```bash
pip install entropy-data
entropy-data --help
```

### Docker

```bash
docker run --rm entropydata/entropy-data-cli --help
```

## Getting Started

### 1. Configure a connection

Generate an API key in the [Entropy Data UI](https://app.entropy-data.com) under organization settings, then:

```bash
entropy-data connection add prod
# prompts for API key and host
```

The added connection becomes the default. Switch with `entropy-data connection set-default <name>`, or pick one per call with `--connection <name>`.

### 2. Explore your data platform

```bash
# List teams
entropy-data teams list

# Get a specific data product
entropy-data dataproducts get my-data-product

# List data contracts as JSON
entropy-data datacontracts list --output json
```

### 3. Manage resources

```bash
# Create or update a team from a YAML file
entropy-data teams put marketing --file team.yaml

# Show the team roles configuration, or switch to a custom role catalog
entropy-data settings team-roles get
entropy-data settings team-roles put --file team-roles.yaml

# Dump the email templates, edit the wording, and write them back
entropy-data settings email-templates get --output yaml > email-templates.yaml
entropy-data settings email-templates put --file email-templates.yaml

# Approve an access agreement
entropy-data access approve 640864de-83d4-4619-afba-ccea8037ed3a

# Search across all resources
entropy-data search query "customer orders"

# Draft a change to a data contract on a branch, test it, and land it
entropy-data datacontracts branches create orders add-status
entropy-data datacontracts branches put orders add-status --file orders.yaml
entropy-data datacontracts test orders --branch add-status
entropy-data datacontracts branches blast-radius orders add-status
entropy-data datacontracts branches merge orders add-status --version 1.1.0

# Propose ontology changes on a branch of a semantic namespace, then merge them
entropy-data semantics branches create sales add-credit-limit
entropy-data semantics branches put sales add-credit-limit --file ontology.yaml
entropy-data semantics branches changes sales add-credit-limit
entropy-data semantics branches blast-radius sales add-credit-limit
entropy-data semantics branches merge sales add-credit-limit
```

### Time ranges and paging for usage, lineage, and test results

`usage list`, `lineage list`, and `test-results list` show the newest records first, one page at a time (100 per page, 10 for test results):

```bash
# Lineage events of the last 24 hours
entropy-data lineage list --since 24h

# Every test run of a contract against production in September
entropy-data test-results list --data-contract-id orders --server production --since 2026-09-01 --until 2026-10-01 --all

# Usage spans in pages of 500
entropy-data usage list --scope-name usage --limit 500 --page 1
```

`--since` (inclusive) and `--until` (exclusive) take an ISO date or date-time (UTC unless it has an offset), or a relative time like `30m`, `24h`, `7d`, `2w`. `--all` follows every page. With `-o json`, a note on stderr says when more pages exist.

The server applies these filters. A server from before that feature ignores them, so the CLI applies them to what it gets back and says so on stderr.

## Commands

```
entropy-data [--version] [--connection NAME] [--output table|json|yaml] [--debug] [--timeout SECONDS]

  connection      list | get | add | remove | set-default | test
  dataproducts    list | get | put | delete | import-from-git | star | unstar | star-status | stargazers | gitconnection ...
  datacontracts   list | get | put | test | delete | yaml | generate | import-from-git | gitconnection ...
                  branches list | create | get | put | yaml | changes | rebase | merge | delete
  access          list | get | put | delete | approve | reject [--reason] | cancel [--reason] [--end] | request
  teams           list | get | put | delete | git-credentials ... | notifications ...
  sourcesystems   list | get | put | delete
  definitions     list | get | put | delete
  certifications  list | get | put | delete
  classifications list | get | put | delete
  policies        list | get | put | delete
  dataproductbuilders list | get | put | delete
  example-data    list | get | put | delete
  usecases        list | get | yaml | put | delete (preview)
  custom-quality-checks get
  test-results    list | get | publish | delete
  costs           list | add (upsert) | delete
  assets          list | get | put | delete | tags ...
  tags            list | get | put | delete
  api-keys        create | delete
  connectors      list | get | put | delete
  integrations    list | get | put | delete | runs | runs-get | runs-latest | run | cancel | unity-catalog-metadata ...
  organization    get | members ... | features get | put | git-credentials ...
  settings        get-customization | put-customization | get-scim-mapping | put-scim-mapping | team-roles ... | email-templates ... | dataproduct-types ... | output-port-types get | put | delete
  events          poll
  lineage         list | submit | delete
  schemas         get
  search          query
  insights        dashboards list | get | yaml | put | delete
                  semantic-models list | get | yaml | put [--removed-metrics] | delete
  semantics       namespaces list | get | put | delete | yaml | put-yaml | search
                  concepts ... | relationships ... (deprecated: use namespaces yaml / put-yaml)
                  branches list | create | get | put | yaml | changes | rebase | merge | delete
  usage           list | submit | delete
  export          dir
  apply           dir [--include] [--exclude] [--prune] [--dry-run]
  import          zip
  sync            --source SRC --target TGT --include a,b [--exclude] [--prune] [--dry-run] [--keep DIR]
```

## Syncing organization state between instances

`sync` copies the portable declarative state of an organization from one Entropy Data
instance to another — for example to promote a test environment to prod. It exports the
source and applies it to the target in one step (`export dir` + `apply dir` do the same in
two). Only state reachable through the public `/api/**` API and portable across instances
is copied (no secrets, telemetry, or environment-specific identity). Every write is an
idempotent PUT-by-id, so runs converge and are safe to repeat.

`sync` copies **nothing by default** — name the resources to sync with `--include`.

**Supported resources** (in dependency order): `teams`, `tags`, `definitions`, `policies`,
`dataproduct-types`, `output-port-types`, `dataproductbuilders`, `sourcesystems`, `certifications`, `classification-schemes`, `assets`, `datacontracts`,
`dataproducts`, `example-data`, `usecases`, `access`, `semantic-namespaces`, `semantic-ontology`,
`email-templates`, `organization-features`.

`output-port-types` is copied only when the source has changed its output port types (not while
it still shows the defaults, `legacy: true`). `usecases` needs Use Cases switched on
(`useCasesEnabled`): a source with them off has none to copy, and a target with them off is
switched on before the use cases are written when the applied `organization-features` turns them
on; otherwise the run fails the use cases and says so.

**Not synced:** users & team members, API keys, git credentials, integration and connector
credentials, usage, costs, test results, events, and lineage (per-instance identity,
secrets, or telemetry). Organization customization, SCIM mapping, team-roles configuration,
notification channels, connectors, and integrations are **not supported yet**.

```bash
# Preview a test -> prod sync of selected resources without writing anything.
entropy-data sync --source test --target prod --include teams,policies,datacontracts,dataproducts --dry-run

# Sync those resources.
entropy-data sync --source test --target prod --include teams,policies,datacontracts,dataproducts

# Mirror: also delete target resources that are absent from the source.
entropy-data sync --source test --target prod --include datacontracts --prune

# The two-step equivalent, with a reviewable YAML tree in between.
entropy-data -c test export dir ./state
entropy-data -c prod apply dir ./state
```

### `apply dir` — apply a local export tree

`apply dir <path>` reconciles a local export directory into the connected instance, in the
spirit of `kubectl apply -f <dir>`. The tree follows a **folder-as-kind** convention: the
directory name is the resource kind and each YAML file below it is one resource, addressed
by the id in its body.

```
state/
  teams/                          # folder name = resource kind
    marketing.yaml                # one file per resource (filename is cosmetic)
  policies/
    pii-policy.yaml
  datacontracts/
    orders-1-orders.yaml
  semantic-ontology/
    main.yaml                     # document resources: one YAML doc per namespace
  organization-features/
    organization-features.yaml    # singleton: <name>/<name>.yaml
```

Unlike `kubectl`, the files carry no `kind:` field — the enclosing folder is authoritative,
so a file only means what its folder says. Folders that are not a known resource kind are
ignored. Unlike `sync`, `apply dir` applies the **whole tree by default** (the directory is
your selection); use `--include`/`--exclude` to narrow it, `--dry-run` to preview, and
`--prune` to also delete instance resources absent from the tree. This layout matches the
app's own organization export, so an `export dir` tree and an in-app export zip interchange.

Useful options:

- `--include a,b` — narrow the apply to these resources (names from the supported list
  above). Optional; the whole tree is applied when omitted.
- `--exclude a,b` — drop resources from the applied set.
- `--prune` — after upserts, delete target resources absent from the directory, in reverse
  dependency order. Guarded by a confirmation prompt unless `--yes` is passed.
- `--dry-run` — print per-resource create/update/(prune) counts; no writes.

Notes:

- Team members are stripped on import (users are per-instance identities); the export
  keeps them so the artifact is a faithful snapshot.
- The semantics graph is copied as one OSI ontology YAML document per namespace
  (`semantic-ontology/<namespace>.yaml`) via the app's `.../{ns}/ontology.yaml` endpoint,
  which imports it in the correct internal dependency order and provisions the namespace
  from the metadata (display name, read-only flag, owning team) carried in the document's root
  `custom_properties` — so there is no separate namespace artifact. Requires that endpoint
  on the target instance. A tree exported by an older version that still carries a
  `semantic-namespaces/` folder is applied as before.
- The organization feature configuration is an org-level singleton
  (`organization-features/organization-features.yaml`), applied last and never pruned. It
  requires the app's `GET`/`PUT /api/organization/features` endpoint (entropy-data#1521),
  which must be merged and deployed to the target instance first.

## Connection Management

Connections are stored in `~/.entropy-data/config.toml`:

```toml
default_connection_name = "prod"

[connections.prod]
api_key = "ed_abc123..."
host = "https://api.entropy-data.com"

[connections.dev]
api_key = "ed_xyz789..."
host = "https://localhost:8080"
```

You can also use environment variables (`ENTROPY_DATA_API_KEY`, `ENTROPY_DATA_HOST`) or CLI options (`--api-key`, `--host`).

### `.env` File Support

The CLI automatically loads a `.env` file from the current working directory. This is useful for project-specific configuration:

```bash
# .env
ENTROPY_DATA_API_KEY=ed_abc123...
ENTROPY_DATA_HOST=https://api.entropy-data.com
```

Values from `.env` are loaded as environment variables and do **not** override already-set environment variables.

Resolution precedence: CLI options (`--api-key`, `--host`, `--connection`) > environment variables / `.env` > default connection from the config file.

`entropy-data connection list` warns (on stderr) when `ENTROPY_DATA_API_KEY` or `ENTROPY_DATA_HOST` is set, because those override the default connection; in the table the default is marked `* (env)`, and in `-o json` it carries `"overridden_by": [...]`.

### Errors

Errors are written to stderr, never stdout, and the CLI exits non-zero (2 for configuration errors, 1 otherwise). With `-o json` or `-o yaml` the error is a structured document, so scripts can parse it:

```json
{
  "error": {
    "type": "api_error",
    "message": "HTTP 404 from https://api.entropy-data.com/api/teams/missing: Team not found",
    "status": 404,
    "url": "https://api.entropy-data.com/api/teams/missing"
  }
}
```

`type` is one of:

| Type | Meaning | Extra fields |
|---|---|---|
| `configuration_error` | No usable connection, for example a missing API key | |
| `api_error` | The API answered with an error status | `status`, `url` |
| `connection_error` | The host could not be reached | `url`, and `proxy` when a proxy is configured for the host |
| `proxy_error` | A proxy refused the request or asked for credentials | `url`, `proxy`, and `status` when the proxy answered with one |
| `error` | Anything else | |

`proxy` never contains the proxy's credentials.

### TLS behind a corporate proxy or internal CA

By default the CLI verifies TLS certificates against the bundled CA certificates (`certifi`). In a corporate network with a TLS-inspecting proxy or an internal certificate authority, this can fail with `CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate`, because the root CA is installed in the operating system's trust store but not in the bundled list.

Use the global `--system-truststore` option to verify against the operating system's trust store (macOS Keychain, Windows certificate store, or the system CA certificates on Linux) instead:

```bash
entropy-data --system-truststore datacontracts list
```

You can also enable it for every invocation by exporting an environment variable:

```bash
export ENTROPY_DATA_SYSTEM_TRUSTSTORE=1
```

This keeps certificate verification on while trusting the corporate root CA, and applies to every command that makes HTTPS requests.

### Proxies

The CLI honors the standard proxy environment variables (upper or lower case):

| Variable | Used for |
|---|---|
| `HTTPS_PROXY` | requests to an `https://` host |
| `HTTP_PROXY` | requests to an `http://` host |
| `ALL_PROXY` | requests that no other variable covers |
| `NO_PROXY` | hosts to reach directly: a comma-separated list of hosts, domain suffixes or IP addresses; `*` turns proxying off |

```bash
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,.internal.example.com
entropy-data datacontracts list
```

A proxy URL may use `http`, `https`, `socks5` or `socks5h`, and may carry credentials (`http://user:password@proxy.example.com:8080`). A proxy that inspects TLS usually needs `--system-truststore` as well, see above. Connection failures are not retried for requests that go through a proxy.

To ignore these variables and connect directly, use the global `--no-trust-env` option or set `ENTROPY_DATA_TRUST_ENV=false`. This also ignores the certificate variables `SSL_CERT_FILE` and `SSL_CERT_DIR`:

```bash
entropy-data --no-trust-env datacontracts list
```

### Timeouts

Each API request waits 30 seconds for a response by default (some commands wait longer, e.g. `datacontracts test`). Large documents, such as a semantic ontology with a thousand concepts, can take the server longer. Use the global `--timeout` option, or `ENTROPY_DATA_TIMEOUT`, to wait longer; it applies to every request of the invocation:

```bash
entropy-data --timeout 120 semantics branches put sales add-credit-limit --file ontology.yaml
```

## Development

```bash
git clone https://github.com/entropy-data/entropy-data-cli
cd entropy-data-cli
uv sync --dev
uv run pytest
uv run ruff check .
```

The tests check the CLI against a copy of the Entropy Data OpenAPI spec in `tests/openapi.yaml`:
every table column must be in its endpoint's response schema, and every request a command sends
in the tests must be a documented operation with documented query parameters. A field or parameter
the API drops then fails the tests instead of printing an empty column. Refresh the copy with
`./update-openapi` when the API changes.

## Release

1. Update the version in `pyproject.toml`
2. Update `CHANGELOG.md` with a `## [X.Y.Z]` section
3. Commit, tag, and push:

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to X.Y.Z"
git tag vX.Y.Z
git push origin main --tags
```

The release workflow will automatically run tests, publish to PyPI, create a GitHub Release, and push a Docker image to Docker Hub.
