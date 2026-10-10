"""Tests for the data product score commands."""

import json

import pytest
import responses
from typer.testing import CliRunner

import entropy_data.config as cfg
from entropy_data.cli import app

runner = CliRunner()
BASE_URL = "https://api.entropy-data.com"


@pytest.fixture(autouse=True)
def api_key(monkeypatch, tmp_path):
    monkeypatch.setattr(cfg, "CONFIG_FILE", tmp_path / "config.toml")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")


def score(product_id: str, value: int = 80) -> dict:
    return {"dataProductId": product_id, "score": value, "rating": "good", "rulesFulfilled": 4, "rulesApplicable": 5}


@responses.activate
def test_scores_lists_one_page_by_default():
    responses.add(responses.GET, f"{BASE_URL}/api/dataproducts/scores", json=[score("orders")])

    result = runner.invoke(app, ["-o", "json", "dataproducts", "scores"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["dataProductId"] == "orders"
    assert responses.calls[0].request.params == {"p": "0", "size": "100"}


@responses.activate
def test_scores_all_follows_the_link_header():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/dataproducts/scores",
        json=[score("a"), score("b")],
        headers={"Link": '</api/dataproducts/scores?p=1&size=2>; rel="next"'},
        match=[responses.matchers.query_param_matcher({"p": "0", "size": "2"})],
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/dataproducts/scores",
        json=[score("c")],
        match=[responses.matchers.query_param_matcher({"p": "1", "size": "2"})],
    )

    result = runner.invoke(app, ["-o", "json", "dataproducts", "scores", "--limit", "2", "--all"])

    assert result.exit_code == 0
    assert [s["dataProductId"] for s in json.loads(result.stdout)] == ["a", "b", "c"]


@responses.activate
def test_scores_all_pages_on_a_server_without_link_header():
    # Older servers send no Link header here: a full page may have a next one, a short page ends it.
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/dataproducts/scores",
        json=[score("a"), score("b")],
        match=[responses.matchers.query_param_matcher({"p": "0", "size": "2"})],
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/dataproducts/scores",
        json=[],
        match=[responses.matchers.query_param_matcher({"p": "1", "size": "2"})],
    )

    result = runner.invoke(app, ["-o", "json", "dataproducts", "scores", "--limit", "2", "--all"])

    assert result.exit_code == 0
    assert [s["dataProductId"] for s in json.loads(result.stdout)] == ["a", "b"]
    assert len(responses.calls) == 2


@responses.activate
def test_score_of_one_data_product_includes_rules():
    body = {
        **score("orders"),
        "rules": [{"key": "has-contract", "category": "contracts", "status": "failed", "weight": 10}],
    }
    responses.add(responses.GET, f"{BASE_URL}/api/dataproducts/orders/score", json=body)

    result = runner.invoke(app, ["-o", "json", "dataproducts", "score", "orders"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["rules"][0]["status"] == "failed"


@responses.activate
def test_score_definition_and_rules():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/settings/dataproduct-score",
        json={
            "ratingBands": {"excellent": 90, "good": 70, "fair": 50},
            "rules": [{"key": "owner", "category": "ownership"}],
        },
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/data-product-score/rules",
        json={"rules": [{"key": "owner", "category": "ownership", "weight": 5, "label": "Has an owner"}]},
    )

    definition = runner.invoke(app, ["-o", "json", "settings", "dataproduct-score", "get"])
    rules = runner.invoke(app, ["settings", "dataproduct-score", "rules"])

    assert definition.exit_code == 0
    assert json.loads(definition.stdout)["ratingBands"]["good"] == 70
    assert rules.exit_code == 0
    assert "Has an owner" in rules.stdout


@responses.activate
def test_scores_with_a_team_key_reports_the_error():
    responses.add(responses.GET, f"{BASE_URL}/api/dataproducts/scores", status=403, json={"message": "Forbidden"})

    result = runner.invoke(app, ["dataproducts", "scores"])

    assert result.exit_code == 1
