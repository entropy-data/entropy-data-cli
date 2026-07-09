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
docker run --rm entropy-data/cli --help
```

## Getting Started

### 1. Configure a connection

Generate an API key in the [Entropy Data UI](https://app.entropy-data.com) under organization settings, then:

```bash
entropy-data connection add prod
# prompts for API key and host
```

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

# Approve an access agreement
entropy-data access approve 640864de-83d4-4619-afba-ccea8037ed3a

# Search across all resources
entropy-data search query "customer orders"
```

## Commands

```
entropy-data [--version] [--connection NAME] [--output table|json|yaml] [--debug]

  connection      list | get | add | remove | set-default | test
  dataproducts    list | get | put | delete | import-from-git | star | unstar | star-status | stargazers | gitconnection ...
  datacontracts   list | get | put | test | delete | yaml | generate | import-from-git | gitconnection ...
  access          list | get | put | delete | approve | reject | cancel | request
  teams           list | get | put | delete | git-credentials ... | notifications ...
  sourcesystems   list | get | put | delete
  definitions     list | get | put | delete
  certifications  list | get | put | delete
  classifications list | get | put | delete
  policies        list | get | put | delete
  example-data    list | get | put | delete
  test-results    list | get | publish | delete
  costs           list | add | delete
  assets          list | get | put | delete | tags ...
  tags            list | get | put | delete
  api-keys        create | delete
  connectors      list | get | put | delete
  integrations    list | get | runs | runs-get | runs-latest | run | cancel
  organization    get | members ... | git-credentials ...
  settings        get-customization | put-customization | get-scim-mapping | put-scim-mapping | team-roles ...
  events          poll
  lineage         list | submit | delete
  schemas         get
  search          query
  semantics       namespaces ... | concepts ... | relationships ... | search
  usage           list | submit | delete
  import          zip
```

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

Resolution precedence: CLI options > environment variables / `.env` > config file.

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

## Development

```bash
git clone https://github.com/entropy-data/entropy-data-cli
cd entropy-data-cli
uv sync --dev
uv run pytest
uv run ruff check .
```

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
