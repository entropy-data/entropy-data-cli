"""Tests for export / import dir / apply commands and the shared sync engine."""

import responses
import yaml
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app
from entropy_data.resources import RESOURCE_ORDER, select_resources

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"
TARGET_URL = "https://target.example.com"


def _config_with_two_connections(tmp_path, monkeypatch):
    """Write a config.toml with a source (default) and a target connection."""
    config_file = tmp_path / "config.toml"
    monkeypatch.setattr(cfg, "CONFIG_FILE", config_file)
    cfg.save_config(
        {
            "default_connection_name": "source",
            "connections": {
                "source": {"api_key": "src-key", "host": BASE_URL},
                "target": {"api_key": "tgt-key", "host": TARGET_URL},
            },
        }
    )


# --- resource ordering ----------------------------------------------------------


def test_sourcesystems_is_included_in_order():
    names = [r.name for r in RESOURCE_ORDER]
    assert "sourcesystems" in names
    # Fixes the drop bug: sourcesystems sits after policies and before assets.
    assert names.index("policies") < names.index("sourcesystems") < names.index("assets")


def test_new_resources_present_in_order():
    names = [r.name for r in RESOURCE_ORDER]
    for expected in ("certifications", "classification-schemes", "example-data"):
        assert expected in names
    # example-data comes after dataproducts (its parent).
    assert names.index("dataproducts") < names.index("example-data")
    # canonical full order
    assert names == [
        "teams",
        "tags",
        "definitions",
        "policies",
        "sourcesystems",
        "certifications",
        "classification-schemes",
        "assets",
        "datacontracts",
        "dataproducts",
        "example-data",
        "access",
        "semantic-namespaces",
        "semantic-concepts",
        "semantic-relationships",
    ]


def test_semantics_nested_under_namespaces():
    by_name = {r.name: r for r in RESOURCE_ORDER}
    # Concepts and relationships are nested under namespaces and come after them.
    assert by_name["semantic-concepts"].parent == "semantic-namespaces"
    assert by_name["semantic-relationships"].parent == "semantic-namespaces"
    names = [r.name for r in RESOURCE_ORDER]
    assert names.index("semantic-namespaces") < names.index("semantic-concepts")
    assert names.index("semantic-namespaces") < names.index("semantic-relationships")
    # The api_path is a parent template expanded per namespace.
    assert by_name["semantic-concepts"].path_for("core") == "semantics/experimental/namespaces/core/concepts"


def test_select_resources_include_exclude():
    only = select_resources(include=["teams", "tags"])
    assert [r.name for r in only] == ["teams", "tags"]

    without = select_resources(exclude=["access"])
    assert "access" not in [r.name for r in without]


def test_select_resources_unknown_raises():
    import pytest

    with pytest.raises(ValueError):
        select_resources(include=["nope"])


# --- export ---------------------------------------------------------------------


@responses.activate
def test_export_writes_files(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    # Only teams and certifications have content; everything else lists empty.
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/teams",
        json=[{"id": "team-a", "name": "A", "members": [{"emailAddress": "x@y.z"}]}],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/certifications",
        json=[{"id": "gold", "name": "Gold", "createdAt": "2020-01-01"}],
        status=200,
    )
    for r in RESOURCE_ORDER:
        if r.name in ("teams", "certifications"):
            continue
        responses.add(responses.GET, f"{BASE_URL}/api/{r.api_path}", json=[], status=200)

    dest = tmp_path / "export"
    result = runner.invoke(app, ["export", "dir", str(dest)])
    assert result.exit_code == 0, result.output

    team_file = dest / "teams" / "team-a.yaml"
    assert team_file.is_file()
    # Export keeps members (faithful round-trip); import strips them.
    assert yaml.safe_load(team_file.read_text())["members"] == [{"emailAddress": "x@y.z"}]

    cert_file = dest / "certifications" / "gold.yaml"
    body = yaml.safe_load(cert_file.read_text())
    assert body["id"] == "gold"
    # Audit fields stripped.
    assert "createdAt" not in body


@responses.activate
def test_export_detail_fetches_each_item(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    # dataproducts list returns a partial body; the full body comes from GET /{id}.
    responses.add(responses.GET, f"{BASE_URL}/api/dataproducts", json=[{"id": "dp-1"}], status=200)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/dataproducts/dp-1",
        json={"id": "dp-1", "info": {"title": "Full body"}},
        status=200,
    )
    for r in RESOURCE_ORDER:
        if r.name == "dataproducts":
            continue
        responses.add(responses.GET, f"{BASE_URL}/api/{r.api_path}", json=[], status=200)

    dest = tmp_path / "export"
    result = runner.invoke(app, ["export", "dir", str(dest), "--include", "dataproducts"])
    assert result.exit_code == 0, result.output
    body = yaml.safe_load((dest / "dataproducts" / "dp-1.yaml").read_text())
    assert body["info"]["title"] == "Full body"


# --- import dir -----------------------------------------------------------------


def _write_tree(root, tree):
    for dirname, files in tree.items():
        d = root / dirname
        d.mkdir(parents=True, exist_ok=True)
        for name, body in files.items():
            (d / f"{name}.yaml").write_text(yaml.safe_dump(body))


@responses.activate
def test_import_dir_upserts_in_order(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    _write_tree(
        src,
        {
            "teams": {
                "parent-team": {"id": "parent-team", "name": "Parent", "members": [{"emailAddress": "a@b.c"}]},
                "child-team": {"id": "child-team", "name": "Child", "parent": "parent-team"},
            },
            "certifications": {"gold": {"id": "gold", "name": "Gold"}},
        },
    )

    puts = []

    def _record(request):
        puts.append(request.url)
        return (200, {}, "")

    responses.add_callback(responses.PUT, f"{BASE_URL}/api/teams/parent-team", callback=_record)
    responses.add_callback(responses.PUT, f"{BASE_URL}/api/teams/child-team", callback=_record)
    responses.add_callback(responses.PUT, f"{BASE_URL}/api/certifications/gold", callback=_record)

    result = runner.invoke(app, ["import", "dir", str(src)])
    assert result.exit_code == 0, result.output
    # Parent team upserted before its child.
    assert puts.index(f"{BASE_URL}/api/teams/parent-team") < puts.index(f"{BASE_URL}/api/teams/child-team")
    assert f"{BASE_URL}/api/certifications/gold" in puts


@responses.activate
def test_import_dir_strips_team_members(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    _write_tree(src, {"teams": {"t1": {"id": "t1", "name": "T", "members": [{"emailAddress": "a@b.c"}]}}})

    captured = {}

    def _capture(request):
        import json as _json

        captured["body"] = _json.loads(request.body)
        return (200, {}, "")

    responses.add_callback(responses.PUT, f"{BASE_URL}/api/teams/t1", callback=_capture)

    result = runner.invoke(app, ["import", "dir", str(src), "--include", "teams"])
    assert result.exit_code == 0, result.output
    assert captured["body"]["members"] == []


@responses.activate
def test_import_dir_assigns_asset_tags(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    _write_tree(
        src,
        {"assets": {"asset-1": {"id": "asset-1", "info": {"name": "A"}, "assignedTags": ["pii", "governance/PII"]}}},
    )

    responses.add(responses.PUT, f"{BASE_URL}/api/assets/asset-1", status=200)
    # One tag already assigned -> only the missing one is added (idempotent).
    responses.add(responses.GET, f"{BASE_URL}/api/assets/asset-1/assigned-tags", json=["pii"], status=200)
    tag_puts = []

    def _record_tag(request):
        tag_puts.append(request.url)
        return (200, {}, "")

    responses.add_callback(
        responses.PUT, f"{BASE_URL}/api/assets/asset-1/assigned-tags/governance/PII", callback=_record_tag
    )

    result = runner.invoke(app, ["import", "dir", str(src), "--include", "assets"])
    assert result.exit_code == 0, result.output
    assert tag_puts == [f"{BASE_URL}/api/assets/asset-1/assigned-tags/governance/PII"]


@responses.activate
def test_import_dir_dry_run_no_writes(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    _write_tree(
        src,
        {"certifications": {"gold": {"id": "gold", "name": "Gold"}, "silver": {"id": "silver", "name": "Silver"}}},
    )

    # Target already has "gold" -> gold is an update, silver is a create.
    responses.add(responses.GET, f"{BASE_URL}/api/certifications", json=[{"id": "gold"}], status=200)

    result = runner.invoke(app, ["import", "dir", str(src), "--include", "certifications", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "create=1" in result.output
    assert "update=1" in result.output
    # No PUT was registered; a write would have raised ConnectionError.


# --- prune ----------------------------------------------------------------------


@responses.activate
def test_import_dir_prune_deletes_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    _write_tree(src, {"certifications": {"gold": {"id": "gold", "name": "Gold"}}})

    responses.add(responses.PUT, f"{BASE_URL}/api/certifications/gold", status=200)
    # Target has gold (kept) and bronze (absent from import -> pruned).
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/certifications",
        json=[{"id": "gold"}, {"id": "bronze"}],
        status=200,
    )
    deletes = []

    def _record_delete(request):
        deletes.append(request.url)
        return (200, {}, "")

    responses.add_callback(responses.DELETE, f"{BASE_URL}/api/certifications/bronze", callback=_record_delete)

    result = runner.invoke(app, ["import", "dir", str(src), "--include", "certifications", "--prune", "--yes"])
    assert result.exit_code == 0, result.output
    # Only the absent resource is deleted.
    assert deletes == [f"{BASE_URL}/api/certifications/bronze"]


@responses.activate
def test_import_dir_prune_deletes_teams_children_first(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    # Import is empty for teams -> both existing teams get pruned, child before parent.
    (src / "teams").mkdir(parents=True)

    responses.add(
        responses.GET,
        f"{BASE_URL}/api/teams",
        json=[{"id": "parent", "parent": None}, {"id": "child", "parent": "parent"}],
        status=200,
    )
    deletes = []

    def _record(request):
        deletes.append(request.url.rsplit("/", 1)[-1])
        return (200, {}, "")

    responses.add_callback(responses.DELETE, f"{BASE_URL}/api/teams/parent", callback=_record)
    responses.add_callback(responses.DELETE, f"{BASE_URL}/api/teams/child", callback=_record)

    result = runner.invoke(app, ["import", "dir", str(src), "--include", "teams", "--prune", "--yes"])
    assert result.exit_code == 0, result.output
    assert deletes == ["child", "parent"]


@responses.activate
def test_import_dir_prune_prompt_abort(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    _write_tree(src, {"certifications": {"gold": {"id": "gold", "name": "Gold"}}})

    # Decline the confirmation prompt -> abort, no HTTP calls.
    result = runner.invoke(app, ["import", "dir", str(src), "--include", "certifications", "--prune"], input="n\n")
    assert result.exit_code == 1
    assert "Aborted" in result.output


# --- apply ----------------------------------------------------------------------


@responses.activate
def test_apply_orchestrates_export_import(monkeypatch, tmp_path):
    _config_with_two_connections(tmp_path, monkeypatch)

    # Source export: one certification, everything else empty.
    responses.add(responses.GET, f"{BASE_URL}/api/certifications", json=[{"id": "gold", "name": "Gold"}], status=200)
    for r in RESOURCE_ORDER:
        if r.name == "certifications":
            continue
        responses.add(responses.GET, f"{BASE_URL}/api/{r.api_path}", json=[], status=200)

    # Target import: capture the PUT.
    target_puts = []

    def _record(request):
        target_puts.append(request.url)
        return (200, {}, "")

    responses.add_callback(responses.PUT, f"{TARGET_URL}/api/certifications/gold", callback=_record)

    keep = tmp_path / "staged"
    result = runner.invoke(app, ["apply", "--to", "target", "--keep", str(keep)])
    assert result.exit_code == 0, result.output
    assert target_puts == [f"{TARGET_URL}/api/certifications/gold"]
    # Staged artifact retained.
    assert (keep / "certifications" / "gold.yaml").is_file()


@responses.activate
def test_apply_dry_run_no_target_writes(monkeypatch, tmp_path):
    _config_with_two_connections(tmp_path, monkeypatch)

    responses.add(responses.GET, f"{BASE_URL}/api/certifications", json=[{"id": "gold", "name": "Gold"}], status=200)
    for r in RESOURCE_ORDER:
        if r.name == "certifications":
            continue
        responses.add(responses.GET, f"{BASE_URL}/api/{r.api_path}", json=[], status=200)

    # Target enumeration for the plan (read-only); no certifications yet -> create.
    for r in RESOURCE_ORDER:
        responses.add(responses.GET, f"{TARGET_URL}/api/{r.api_path}", json=[], status=200)

    result = runner.invoke(app, ["apply", "--to", "target", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "create=1" in result.output


def test_import_help_lists_dir_and_zip():
    result = runner.invoke(app, ["import", "--help"])
    assert result.exit_code == 0
    assert "zip" in result.output
    assert "dir" in result.output


# --- semantics (nested) ---------------------------------------------------------

NS = f"{BASE_URL}/api/semantics/experimental/namespaces"


@responses.activate
def test_export_semantics_nested(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    # One namespace, one concept in it (concept body fetched per-item via detail).
    responses.add(responses.GET, NS, json=[{"namespace": "core", "label": "Core"}], status=200)
    responses.add(responses.GET, f"{NS}/core/concepts", json=[{"id": "customer"}], status=200)
    responses.add(
        responses.GET,
        f"{NS}/core/concepts/customer",
        json={"id": "customer", "name": "Customer", "kind": "entity"},
        status=200,
    )
    responses.add(responses.GET, f"{NS}/core/relationships", json=[], status=200)

    dest = tmp_path / "export"
    result = runner.invoke(
        app,
        ["export", "dir", str(dest), "--include", "semantic-namespaces,semantic-concepts,semantic-relationships"],
    )
    assert result.exit_code == 0, result.output

    assert yaml.safe_load((dest / "semantic-namespaces" / "core.yaml").read_text())["namespace"] == "core"
    # Nested layout: <name>/<namespace>/<child>.yaml, full body from the detail GET.
    concept = yaml.safe_load((dest / "semantic-concepts" / "core" / "customer.yaml").read_text())
    assert concept["name"] == "Customer"


@responses.activate
def test_import_semantics_nested_namespace_before_concept(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    (src / "semantic-namespaces").mkdir(parents=True)
    (src / "semantic-namespaces" / "core.yaml").write_text(yaml.safe_dump({"namespace": "core", "label": "Core"}))
    (src / "semantic-concepts" / "core").mkdir(parents=True)
    (src / "semantic-concepts" / "core" / "customer.yaml").write_text(
        yaml.safe_dump({"id": "customer", "name": "Customer"})
    )

    puts = []

    def _record(request):
        puts.append(request.url)
        return (200, {}, "")

    responses.add_callback(responses.PUT, f"{NS}/core", callback=_record)
    responses.add_callback(responses.PUT, f"{NS}/core/concepts/customer", callback=_record)

    result = runner.invoke(app, ["import", "dir", str(src), "--include", "semantic-namespaces,semantic-concepts"])
    assert result.exit_code == 0, result.output
    # Namespace is created before the concept nested under it.
    assert puts == [f"{NS}/core", f"{NS}/core/concepts/customer"]


@responses.activate
def test_prune_semantics_nested_deletes_absent_concept(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    src = tmp_path / "tree"
    (src / "semantic-namespaces").mkdir(parents=True)
    (src / "semantic-namespaces" / "core.yaml").write_text(yaml.safe_dump({"namespace": "core"}))
    (src / "semantic-concepts" / "core").mkdir(parents=True)
    (src / "semantic-concepts" / "core" / "keep.yaml").write_text(yaml.safe_dump({"id": "keep"}))

    responses.add(responses.PUT, f"{NS}/core", status=200)
    responses.add(responses.PUT, f"{NS}/core/concepts/keep", status=200)
    # Prune enumerates parents (namespaces) then children per namespace on the target.
    responses.add(responses.GET, NS, json=[{"namespace": "core"}], status=200)
    responses.add(responses.GET, f"{NS}/core/concepts", json=[{"id": "keep"}, {"id": "drop"}], status=200)

    deletes = []

    def _record_delete(request):
        deletes.append(request.url)
        return (200, {}, "")

    responses.add_callback(responses.DELETE, f"{NS}/core/concepts/drop", callback=_record_delete)

    result = runner.invoke(
        app,
        ["import", "dir", str(src), "--include", "semantic-namespaces,semantic-concepts", "--prune", "--yes"],
    )
    assert result.exit_code == 0, result.output
    # Only the concept absent from the import is deleted, addressed under its namespace.
    assert deletes == [f"{NS}/core/concepts/drop"]
