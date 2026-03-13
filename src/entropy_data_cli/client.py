"""HTTP client for the Entropy Data API."""

import json
import re

import requests

from entropy_data_cli.config import ConnectionConfig

RESPONSE_HEADER_LOCATION_HTML = "location-html"


class ApiError(Exception):
    """HTTP error from the Entropy Data API."""

    def __init__(self, status_code: int, message: str, url: str):
        self.status_code = status_code
        self.url = url
        super().__init__(f"HTTP {status_code} from {url}: {message}")


class NotFoundError(ApiError):
    """404 from the API."""


class ValidationError(ApiError):
    """422 from the API."""


def _raise_for_status(response: requests.Response) -> None:
    """Raise appropriate ApiError subclass for non-2xx responses."""
    if response.ok:
        return
    message = response.text
    try:
        message = response.json().get("message", response.text)
    except (json.JSONDecodeError, AttributeError):
        pass
    if response.status_code == 404:
        raise NotFoundError(response.status_code, message, response.url)
    if response.status_code == 422:
        raise ValidationError(response.status_code, message, response.url)
    raise ApiError(response.status_code, message, response.url)


def _has_next_page(response: requests.Response) -> bool:
    """Check if the Link header contains rel="next"."""
    link = response.headers.get("Link", "")
    return bool(re.search(r'rel="next"', link))


class EntropyDataClient:
    def __init__(self, config: ConnectionConfig):
        self.base_url = config.host.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-api-key": config.api_key,
                "Content-Type": "application/json",
            }
        )

    def list_resources(self, path: str, params: dict | None = None) -> tuple[list[dict], bool]:
        """GET /api/{path}. Returns (items, has_next_page)."""
        response = self.session.get(f"{self.base_url}/api/{path}", params=params)
        _raise_for_status(response)
        return response.json(), _has_next_page(response)

    def get_resource(self, path: str, resource_id: str) -> dict:
        """GET /api/{path}/{id}."""
        response = self.session.get(f"{self.base_url}/api/{path}/{resource_id}")
        _raise_for_status(response)
        return response.json()

    def put_resource(self, path: str, resource_id: str, body: dict) -> str | None:
        """PUT /api/{path}/{id}. Returns location-html URL if present."""
        response = self.session.put(f"{self.base_url}/api/{path}/{resource_id}", json=body)
        _raise_for_status(response)
        return response.headers.get(RESPONSE_HEADER_LOCATION_HTML)

    def delete_resource(self, path: str, resource_id: str) -> None:
        """DELETE /api/{path}/{id}."""
        response = self.session.delete(f"{self.base_url}/api/{path}/{resource_id}")
        _raise_for_status(response)

    def post_action(self, path: str, resource_id: str, action: str) -> str | None:
        """POST /api/{path}/{id}/{action}. Returns location-html URL if present."""
        response = self.session.post(f"{self.base_url}/api/{path}/{resource_id}/{action}")
        _raise_for_status(response)
        return response.headers.get(RESPONSE_HEADER_LOCATION_HTML)

    def post_resource(self, path: str, body: dict) -> str | None:
        """POST /api/{path}. Returns location-html URL if present."""
        response = self.session.post(f"{self.base_url}/api/{path}", json=body)
        _raise_for_status(response)
        return response.headers.get(RESPONSE_HEADER_LOCATION_HTML)

    def get_events(self, last_event_id: str | None = None) -> list[dict]:
        """GET /api/events. Returns list of events."""
        params = {}
        if last_event_id:
            params["lastEventId"] = last_event_id
        response = self.session.get(f"{self.base_url}/api/events", params=params)
        _raise_for_status(response)
        return response.json()

    def search(self, query: str, **params) -> dict:
        """GET /api/search."""
        params["query"] = query
        response = self.session.get(f"{self.base_url}/api/search", params=params)
        _raise_for_status(response)
        return response.json()
