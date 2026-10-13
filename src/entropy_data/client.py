"""The commands' client for the Entropy Data API, built on the Python SDK.

Commands print what the server returns, so this client speaks in paths and dictionaries and leaves
parsing to the output layer. ``sdk`` is the typed SDK client underneath, and ``http`` its HTTP layer
for endpoints without a method here.
"""

import re

from entropy_data_sdk import EntropyDataClient as SdkClient
from entropy_data_sdk.errors import ApiError, NotFoundError, UnprocessableContentError

from entropy_data.config import ConnectionConfig

__all__ = [
    "ApiError",
    "EntropyDataClient",
    "NotFoundError",
    "REQUEST_TIMEOUT",
    "SCHEMA_SPECS",
    "UnprocessableContentError",
]

REQUEST_TIMEOUT = 30
MAX_RESOURCE_ID_LENGTH = 256

SCHEMA_SPECS = ("odcs", "odps")
_SCHEMA_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


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


def _has_next_page(response) -> bool:
    return bool(re.search(r'rel="next"', response.headers.get("Link", "")))


class EntropyDataClient:
    def __init__(self, config: ConnectionConfig, timeout: int | None = None):
        # An explicit --timeout also overrides the longer waits some commands choose for themselves.
        self.timeout_override = timeout
        self.timeout = timeout or REQUEST_TIMEOUT
        self.sdk = SdkClient(config.api_key, config.host, timeout=self.timeout)
        self.http = self.sdk.http

    @property
    def base_url(self) -> str:
        return self.http.base_url

    def list_resources(self, path: str, params: dict | None = None) -> tuple[list[dict], bool]:
        """GET /api/{path}. Returns (items, has_next_page)."""
        if params and "p" in params:
            _validate_page(int(params["p"]))
        response = self.http.request("GET", f"/api/{path}", params=params)
        return response.json(), _has_next_page(response)

    def get_resource(self, path: str, resource_id: str) -> dict:
        """GET /api/{path}/{id}."""
        _validate_resource_id(resource_id)
        return self.http.get_json(f"/api/{path}/{resource_id}")

    def put_resource(self, path: str, resource_id: str, body: dict) -> str | None:
        """PUT /api/{path}/{id}. Returns location-html URL if present."""
        _validate_resource_id(resource_id)
        if "id" in body and body["id"] != resource_id:
            body = {**body, "id": resource_id}
        return self.http.put_json(f"/api/{path}/{resource_id}", body).location_html

    def delete_resource(self, path: str, resource_id: str) -> None:
        """DELETE /api/{path}/{id}."""
        _validate_resource_id(resource_id)
        self.http.delete(f"/api/{path}/{resource_id}")

    def post_action(self, path: str, resource_id: str, action: str) -> str | None:
        """POST /api/{path}/{id}/{action}. Returns location-html URL if present."""
        _validate_resource_id(resource_id)
        return self.http.post_json(f"/api/{path}/{resource_id}/{action}").location_html

    def post_action_json(
        self,
        path: str,
        resource_id: str,
        action: str,
        params: dict | None = None,
        body: dict | None = None,
        timeout: int | None = None,
    ) -> dict:
        """POST /api/{path}/{id}/{action}. Returns response JSON."""
        _validate_resource_id(resource_id)
        response = self.http.request(
            "POST",
            f"/api/{path}/{resource_id}/{action}",
            params=params,
            json=body,
            timeout=self.timeout_override or timeout,
        )
        return response.json()

    def post_resource(self, path: str, body: dict, params: dict | None = None) -> str | None:
        """POST /api/{path}. Returns location-html URL if present."""
        return self.http.post_json(f"/api/{path}", body, params=params).location_html

    def delete_resources(self, path: str, params: dict | None = None) -> dict:
        """DELETE /api/{path} with query params. Returns response JSON."""
        return self.http.delete(f"/api/{path}", params=params).data or {}

    def get_events(self, last_event_id: str | None = None) -> list[dict]:
        """GET /api/events. Returns list of events."""
        return self.http.get_json("/api/events", params={"lastEventId": last_event_id})

    def get_gitconnection(self, path: str, resource_id: str) -> dict:
        """GET /api/{path}/{id}/gitconnection."""
        _validate_resource_id(resource_id)
        return self.http.get_json(f"/api/{path}/{resource_id}/gitconnection")

    def put_gitconnection(self, path: str, resource_id: str, body: dict) -> dict:
        """PUT /api/{path}/{id}/gitconnection."""
        _validate_resource_id(resource_id)
        return self.http.request("PUT", f"/api/{path}/{resource_id}/gitconnection", json=body).json()

    def delete_gitconnection(self, path: str, resource_id: str) -> None:
        """DELETE /api/{path}/{id}/gitconnection."""
        _validate_resource_id(resource_id)
        self.http.delete(f"/api/{path}/{resource_id}/gitconnection")

    def gitconnection_action(
        self,
        path: str,
        resource_id: str,
        action: str,
        body: dict | None = None,
    ) -> dict:
        """POST /api/{path}/{id}/gitconnection/{action}. action ∈ {pull, push, push-pr}."""
        _validate_resource_id(resource_id)
        return self.http.request("POST", f"/api/{path}/{resource_id}/gitconnection/{action}", json=body).json()

    def get_schema(self, spec: str, version: str | None = None, custom: bool = False) -> tuple[str, str | None]:
        """GET /api/schemas/{spec}[-{version}][-custom].schema.json.

        Returns (schema JSON text, served base version from the X-Schema-Version header).
        """
        if spec not in SCHEMA_SPECS:
            raise ValueError(f"Unknown specification '{spec}'. Expected one of: {', '.join(SCHEMA_SPECS)}.")
        if version is not None and not _SCHEMA_VERSION_PATTERN.match(version):
            raise ValueError(f"Invalid schema version '{version}'. Expected a version like 3.1.0.")
        filename = f"{spec}{f'-{version}' if version else ''}{'-custom' if custom else ''}.schema.json"
        response = self.http.request("GET", f"/api/schemas/{filename}")
        return response.text, response.headers.get("X-Schema-Version")

    def search(self, query: str, **params) -> dict:
        """GET /api/search."""
        return self.http.get_json("/api/search", params={**params, "query": query})
