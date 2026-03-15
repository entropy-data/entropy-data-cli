# Changelog

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
