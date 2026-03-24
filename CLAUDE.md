# CLAUDE.md

## Development Environment Setup

```bash
# Using uv (recommended)
uv python pin 3.12
uv venv
source .venv/bin/activate
uv pip install -e '.[dev]'

# Or using pip
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Common Commands

```bash
# Run all tests
pytest

# Run a specific test
pytest tests/test_config.py::test_function_name

# Lint and format
ruff check .
ruff check --fix .
ruff format .

# CLI usage
entropy-data --version
entropy-data --help
entropy-data connection add prod
entropy-data teams list
```

## Project Architecture

CLI for Entropy Data.

### Core Modules
- `cli.py` — Typer app, global options, command group registration
- `config.py` — Connection config management (~/.entropy-data/config.toml)
- `client.py` — HTTP client wrapping requests (generic CRUD + actions)
- `output.py` — Output formatting (Rich tables, JSON)

### Command Modules (`commands/`)
Each file creates a `typer.Typer()` instance registered in `cli.py`.
Resources: dataproducts, datacontracts, access, teams, sourcesystems, definitions, certifications, example-data, test-results, events, search, connection.

### Config Resolution Precedence
1. CLI options (`--api-key`, `--host`)
2. Environment variables / `.env` file (`ENTROPY_DATA_API_KEY`, `ENTROPY_DATA_HOST`)
3. Named connection from `~/.entropy-data/config.toml`

## Code Conventions
- Python 3.12+
- Typer for CLI, Rich for output, Pydantic for models, requests for HTTP
- Ruff for linting/formatting (line-length 120)
- Tests use pytest + responses (mocked HTTP)
