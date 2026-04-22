"""Tests for the HTTP client."""

import pytest
import responses

from entropy_data.client import ApiError, EntropyDataClient, NotFoundError, ValidationError
from entropy_data.config import ConnectionConfig

BASE_URL = "https://api.entropy-data.com"


@pytest.fixture
def client():
    config = ConnectionConfig(api_key="test-key", host=BASE_URL)
    return EntropyDataClient(config)


@responses.activate
def test_list_resources(client):
    responses.add(responses.GET, f"{BASE_URL}/api/teams", json=[{"id": "t1", "name": "Team 1"}], status=200)
    data, has_next = client.list_resources("teams")
    assert len(data) == 1
    assert data[0]["id"] == "t1"
    assert has_next is False


@responses.activate
def test_list_resources_with_pagination(client):
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/teams",
        json=[{"id": "t1"}],
        status=200,
        headers={"Link": '<https://api.entropy-data.com/api/teams?p=1>; rel="next"'},
    )
    data, has_next = client.list_resources("teams")
    assert has_next is True


@responses.activate
def test_get_resource(client):
    responses.add(responses.GET, f"{BASE_URL}/api/teams/t1", json={"id": "t1", "name": "Team 1"}, status=200)
    data = client.get_resource("teams", "t1")
    assert data["id"] == "t1"


@responses.activate
def test_get_resource_not_found(client):
    responses.add(responses.GET, f"{BASE_URL}/api/teams/nope", json={"message": "Not found"}, status=404)
    with pytest.raises(NotFoundError):
        client.get_resource("teams", "nope")


@responses.activate
def test_put_resource(client):
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/teams/t1",
        status=200,
        headers={"location-html": "https://app.entropy-data.com/teams/t1"},
    )
    location = client.put_resource("teams", "t1", {"id": "t1", "name": "Team 1", "type": "Team"})
    assert location == "https://app.entropy-data.com/teams/t1"


@responses.activate
def test_put_resource_validation_error(client):
    responses.add(responses.PUT, f"{BASE_URL}/api/teams/t1", json={"message": "Invalid"}, status=422)
    with pytest.raises(ValidationError):
        client.put_resource("teams", "t1", {"id": "t1"})


@responses.activate
def test_delete_resource(client):
    responses.add(responses.DELETE, f"{BASE_URL}/api/teams/t1", status=200)
    client.delete_resource("teams", "t1")


@responses.activate
def test_post_action(client):
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/access/a1/approve",
        status=200,
        headers={"location-html": "https://app.entropy-data.com/access/a1"},
    )
    location = client.post_action("access", "a1", "approve")
    assert location == "https://app.entropy-data.com/access/a1"


@responses.activate
def test_post_resource(client):
    responses.add(responses.POST, f"{BASE_URL}/api/test-results", status=200)
    client.post_resource("test-results", {"dataContractId": "dc1", "result": "passed"})


@responses.activate
def test_get_events(client):
    responses.add(responses.GET, f"{BASE_URL}/api/events", json=[{"id": "e1", "type": "created"}], status=200)
    data = client.get_events()
    assert len(data) == 1


@responses.activate
def test_search(client):
    responses.add(responses.GET, f"{BASE_URL}/api/search", json={"results": []}, status=200)
    data = client.search("test query")
    assert "results" in data


@responses.activate
def test_api_key_sent_in_header(client):
    responses.add(responses.GET, f"{BASE_URL}/api/teams", json=[], status=200)
    client.list_resources("teams")
    assert responses.calls[0].request.headers["x-api-key"] == "test-key"


@responses.activate
def test_server_error(client):
    responses.add(responses.GET, f"{BASE_URL}/api/teams", body="Internal Server Error", status=500)
    with pytest.raises(ApiError) as exc_info:
        client.list_resources("teams")
    assert exc_info.value.status_code == 500


def test_negative_page_rejected(client):
    with pytest.raises(ValueError, match="must not be negative"):
        client.list_resources("teams", params={"p": -1})


@responses.activate
def test_html_error_response_cleaned(client):
    html_body = (
        "<!doctype html><html><head><title>HTTP Status 400 – Bad Request</title></head>"
        "<body><h1>Bad Request</h1><p>Request header is too large</p></body></html>"
    )
    responses.add(responses.GET, f"{BASE_URL}/api/teams/long-id", body=html_body, status=400)
    with pytest.raises(ApiError) as exc_info:
        client.get_resource("teams", "long-id")
    assert "HTTP Status 400" in str(exc_info.value)
    assert "<html" not in str(exc_info.value)


@responses.activate
def test_put_resource_overrides_mismatched_body_id(client):
    responses.add(responses.PUT, f"{BASE_URL}/api/teams/correct-id", status=200)
    client.put_resource("teams", "correct-id", {"id": "wrong-id", "name": "Test"})
    sent_body = responses.calls[0].request.body
    import json

    assert json.loads(sent_body)["id"] == "correct-id"


@responses.activate
def test_put_resource_preserves_matching_body_id(client):
    responses.add(responses.PUT, f"{BASE_URL}/api/teams/t1", status=200)
    client.put_resource("teams", "t1", {"id": "t1", "name": "Test"})
    sent_body = responses.calls[0].request.body
    import json

    assert json.loads(sent_body)["id"] == "t1"
