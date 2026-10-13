"""Tests for the HTTP client."""

import json

import httpx
import pytest
import respx

from entropy_data.client import ApiError, EntropyDataClient, NotFoundError, UnprocessableContentError
from entropy_data.config import ConnectionConfig

BASE_URL = "https://api.entropy-data.com"


@pytest.fixture
def client():
    config = ConnectionConfig(api_key="test-key", host=BASE_URL)
    return EntropyDataClient(config)


@respx.mock
def test_list_resources(client):
    respx.get(f"{BASE_URL}/api/teams").mock(return_value=httpx.Response(200, json=[{"id": "t1", "name": "Team 1"}]))
    data, has_next = client.list_resources("teams")
    assert len(data) == 1
    assert data[0]["id"] == "t1"
    assert has_next is False


@respx.mock
def test_list_resources_with_pagination(client):
    respx.get(f"{BASE_URL}/api/teams").mock(
        return_value=httpx.Response(
            200,
            json=[{"id": "t1"}],
            headers={"Link": '<https://api.entropy-data.com/api/teams?p=1>; rel="next"'},
        )
    )
    data, has_next = client.list_resources("teams")
    assert has_next is True


@respx.mock
def test_get_resource(client):
    respx.get(f"{BASE_URL}/api/teams/t1").mock(return_value=httpx.Response(200, json={"id": "t1", "name": "Team 1"}))
    data = client.get_resource("teams", "t1")
    assert data["id"] == "t1"


@respx.mock
def test_get_resource_not_found(client):
    respx.get(f"{BASE_URL}/api/teams/nope").mock(return_value=httpx.Response(404, json={"message": "Not found"}))
    with pytest.raises(NotFoundError):
        client.get_resource("teams", "nope")


@respx.mock
def test_put_resource(client):
    respx.put(f"{BASE_URL}/api/teams/t1").mock(
        return_value=httpx.Response(200, headers={"location-html": "https://app.entropy-data.com/teams/t1"})
    )
    location = client.put_resource("teams", "t1", {"id": "t1", "name": "Team 1", "type": "Team"})
    assert location == "https://app.entropy-data.com/teams/t1"


@respx.mock
def test_put_resource_validation_error(client):
    respx.put(f"{BASE_URL}/api/teams/t1").mock(return_value=httpx.Response(422, json={"message": "Invalid"}))
    with pytest.raises(UnprocessableContentError):
        client.put_resource("teams", "t1", {"id": "t1"})


@respx.mock
def test_delete_resource(client):
    respx.delete(f"{BASE_URL}/api/teams/t1").mock(return_value=httpx.Response(200))
    client.delete_resource("teams", "t1")


@respx.mock
def test_post_action(client):
    respx.post(f"{BASE_URL}/api/access/a1/approve").mock(
        return_value=httpx.Response(200, headers={"location-html": "https://app.entropy-data.com/access/a1"})
    )
    location = client.post_action("access", "a1", "approve")
    assert location == "https://app.entropy-data.com/access/a1"


@respx.mock
def test_post_resource(client):
    respx.post(f"{BASE_URL}/api/test-results").mock(return_value=httpx.Response(200))
    client.post_resource("test-results", {"dataContractId": "dc1", "result": "passed"})


@respx.mock
def test_get_events(client):
    respx.get(f"{BASE_URL}/api/events").mock(return_value=httpx.Response(200, json=[{"id": "e1", "type": "created"}]))
    data = client.get_events()
    assert len(data) == 1


@respx.mock
def test_search(client):
    respx.get(f"{BASE_URL}/api/search").mock(return_value=httpx.Response(200, json={"results": []}))
    data = client.search("test query")
    assert "results" in data


@respx.mock
def test_api_key_sent_in_header(client):
    respx.get(f"{BASE_URL}/api/teams").mock(return_value=httpx.Response(200, json=[]))
    client.list_resources("teams")
    assert respx.calls[0].request.headers["x-api-key"] == "test-key"


@respx.mock
def test_server_error(client):
    respx.get(f"{BASE_URL}/api/teams").mock(return_value=httpx.Response(500, text="Internal Server Error"))
    with pytest.raises(ApiError) as exc_info:
        client.list_resources("teams")
    assert exc_info.value.status_code == 500


def test_negative_page_rejected(client):
    with pytest.raises(ValueError, match="must not be negative"):
        client.list_resources("teams", params={"p": -1})


@respx.mock
def test_html_error_response_cleaned(client):
    html_body = (
        "<!doctype html><html><head><title>HTTP Status 400 – Bad Request</title></head>"
        "<body><h1>Bad Request</h1><p>Request header is too large</p></body></html>"
    )
    respx.get(f"{BASE_URL}/api/teams/long-id").mock(return_value=httpx.Response(400, text=html_body))
    with pytest.raises(ApiError) as exc_info:
        client.get_resource("teams", "long-id")
    assert "HTTP Status 400" in str(exc_info.value)
    assert "<html" not in str(exc_info.value)


@respx.mock
def test_put_resource_overrides_mismatched_body_id(client):
    respx.put(f"{BASE_URL}/api/teams/correct-id").mock(return_value=httpx.Response(200))
    client.put_resource("teams", "correct-id", {"id": "wrong-id", "name": "Test"})
    assert json.loads(respx.calls[0].request.content)["id"] == "correct-id"


@respx.mock
def test_put_resource_preserves_matching_body_id(client):
    respx.put(f"{BASE_URL}/api/teams/t1").mock(return_value=httpx.Response(200))
    client.put_resource("teams", "t1", {"id": "t1", "name": "Test"})
    assert json.loads(respx.calls[0].request.content)["id"] == "t1"


@respx.mock
def test_host_with_path_prefix_is_kept(client):
    config = ConnectionConfig(api_key="test-key", host="https://proxy.example.test/entropy-data/")
    route = respx.get("https://proxy.example.test/entropy-data/api/teams").mock(
        return_value=httpx.Response(200, json=[])
    )
    EntropyDataClient(config).list_resources("teams")
    assert route.called
