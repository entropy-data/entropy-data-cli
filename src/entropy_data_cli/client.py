"""HTTP client for the Entropy Data API."""

import json
import re

import requests

from entropy_data_cli.config import ConnectionConfig

RESPONSE_HEADER_LOCATION_HTML = "location-html"
REQUEST_TIMEOUT = 30


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
        body = response.json()
        message = body.get("detail") or body.get("message") or body.get("title") or response.text
    except (json.JSONDecodeError, AttributeError):
        # If the response is HTML, extract a useful message instead of dumping raw markup
        if "<html" in message.lower():
            match = re.search(r"<title>([^<]+)</title>", message, re.IGNORECASE)
            message = match.group(1).strip() if match else response.reason or "Server error"
    if response.status_code == 404:
        raise NotFoundError(response.status_code, message, response.url)
    if response.status_code == 422:
        raise ValidationError(response.status_code, message, response.url)
    raise ApiError(response.status_code, message, response.url)


def _has_next_page(response: requests.Response) -> bool:
    """Check if the Link header contains rel="next"."""
    link = response.headers.get("Link", "")
    return bool(re.search(r'rel="next"', link))


MAX_RESOURCE_ID_LENGTH = 256


def _validate_resource_id(resource_id: str) -> None:
    """Reject empty, too-long, or path-traversal resource IDs."""
    if not resource_id:
        raise ValueError("Resource ID must not be empty.")
    if len(resource_id) > MAX_RESOURCE_ID_LENGTH:
        raise ValueError(f"Resource ID must not exceed {MAX_RESOURCE_ID_LENGTH} characters.")
    if ".." in resource_id.split("/"):
        raise ValueError(f"Resource ID must not contain path traversal: '{resource_id}'")


def _validate_page(page: int) -> None:
    """Reject negative page numbers."""
    if page < 0:
        raise ValueError(f"Page number must not be negative: {page}")


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
        if params and "p" in params:
            _validate_page(int(params["p"]))
        response = self.session.get(f"{self.base_url}/api/{path}", params=params, timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.json(), _has_next_page(response)

    def get_resource(self, path: str, resource_id: str) -> dict:
        """GET /api/{path}/{id}."""
        _validate_resource_id(resource_id)
        response = self.session.get(f"{self.base_url}/api/{path}/{resource_id}", timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.json()

    def put_resource(self, path: str, resource_id: str, body: dict) -> str | None:
        """PUT /api/{path}/{id}. Returns location-html URL if present."""
        _validate_resource_id(resource_id)
        if "id" in body and body["id"] != resource_id:
            body = {**body, "id": resource_id}
        response = self.session.put(f"{self.base_url}/api/{path}/{resource_id}", json=body, timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.headers.get(RESPONSE_HEADER_LOCATION_HTML)

    def delete_resource(self, path: str, resource_id: str) -> None:
        """DELETE /api/{path}/{id}."""
        _validate_resource_id(resource_id)
        response = self.session.delete(f"{self.base_url}/api/{path}/{resource_id}", timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)

    def post_action(self, path: str, resource_id: str, action: str) -> str | None:
        """POST /api/{path}/{id}/{action}. Returns location-html URL if present."""
        _validate_resource_id(resource_id)
        response = self.session.post(f"{self.base_url}/api/{path}/{resource_id}/{action}", timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.headers.get(RESPONSE_HEADER_LOCATION_HTML)

    def post_action_json(self, path: str, resource_id: str, action: str, params: dict | None = None,
                         timeout: int = REQUEST_TIMEOUT) -> dict:
        """POST /api/{path}/{id}/{action} with query params. Returns response JSON."""
        _validate_resource_id(resource_id)
        response = self.session.post(
            f"{self.base_url}/api/{path}/{resource_id}/{action}", params=params, timeout=timeout,
        )
        _raise_for_status(response)
        return response.json()

    def post_resource(self, path: str, body: dict, params: dict | None = None) -> str | None:
        """POST /api/{path}. Returns location-html URL if present."""
        response = self.session.post(f"{self.base_url}/api/{path}", json=body, params=params, timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.headers.get(RESPONSE_HEADER_LOCATION_HTML)

    def delete_resources(self, path: str, params: dict | None = None) -> dict:
        """DELETE /api/{path} with query params. Returns response JSON."""
        response = self.session.delete(f"{self.base_url}/api/{path}", params=params, timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        try:
            return response.json()
        except Exception:
            return {}

    def get_events(self, last_event_id: str | None = None) -> list[dict]:
        """GET /api/events. Returns list of events."""
        params = {}
        if last_event_id:
            params["lastEventId"] = last_event_id
        response = self.session.get(f"{self.base_url}/api/events", params=params, timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.json()

    def search(self, query: str, **params) -> dict:
        """GET /api/search."""
        params["query"] = query
        response = self.session.get(f"{self.base_url}/api/search", params=params, timeout=REQUEST_TIMEOUT)
        _raise_for_status(response)
        return response.json()
