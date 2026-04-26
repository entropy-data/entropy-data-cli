# Changelog

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
