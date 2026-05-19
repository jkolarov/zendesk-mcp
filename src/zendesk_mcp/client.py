import re
from typing import Any, Dict, cast

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import settings

ALLOWED_PATHS = {
    "/api/v2/search.json",
    "/api/v2/search/count.json",
    "/api/v2/tickets/{id}.json",
    "/api/v2/tickets/{id}/audits.json",
    "/api/v2/tickets/{id}/comments.json",
    "/api/v2/users/{id}.json",
    "/api/v2/users/search.json",
    "/api/v2/organizations/{id}.json",
    "/api/v2/organizations/search.json",
    "/api/v2/views/{id}.json",
    "/api/v2/views/{id}/count.json",
    "/api/v2/views/{id}/tickets.json",
    "/api/v2/ticket_fields.json",
    "/api/v2/triggers.json",
    "/api/v2/triggers/active.json",
    "/api/v2/triggers/search.json",
    "/api/v2/triggers/{id}.json",
}


class ZendeskError(Exception):
    def __init__(self, status: int, message: str, hint: str = ""):
        self.status = status
        self.message = message
        self.hint = hint
        super().__init__(message)


class ZendeskClient:
    def __init__(self):
        self.base_url = settings.zendesk_base_url
        auth_method = settings.auth_method

        client_kwargs = {
            "base_url": self.base_url,
            "timeout": 30.0,
            "headers": {"Accept": "application/json"},
        }

        if auth_method == "oauth":
            client_kwargs["headers"]["Authorization"] = f"Bearer {cast(str, settings.zd_oauth_token)}"
        else:
            client_kwargs["auth"] = (f"{settings.zd_email}/token", settings.zd_api_token)

        self.client = httpx.Client(**client_kwargs)

    def _validate_path(self, path: str) -> None:
        normalized = path.split("?")[0]
        for allowed in ALLOWED_PATHS:
            if "{id}" in allowed:
                pattern = allowed.replace("{id}", r"\d+").replace(".", r"\.")
                if re.match(pattern, normalized):
                    return
            elif normalized == allowed:
                return
        raise ZendeskError(403, f"Path not allowed: {path}", "Only permitted endpoints are allowed")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True,
    )
    def get(self, path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        self._validate_path(path)
        try:
            response = self.client.get(path, params=params)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise ZendeskError(429, "Rate limit exceeded", f"Retry after {retry_after} seconds")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                raise ZendeskError(401, "Authentication failed", "Check your API token or OAuth token")
            elif status == 403:
                raise ZendeskError(403, "Access denied", "Token lacks required permissions")
            elif status == 404:
                raise ZendeskError(404, "Resource not found", "Check the ID or query")
            raise ZendeskError(status, str(e), "")
        except httpx.RequestError as e:
            raise ZendeskError(500, f"Request failed: {e}", "Check network connectivity")

    def put(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        self._validate_path(path)
        try:
            response = self.client.put(path, json=body, headers={"Content-Type": "application/json"})
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise ZendeskError(429, "Rate limit exceeded", f"Retry after {retry_after} seconds")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                raise ZendeskError(401, "Authentication failed", "Check your API token or OAuth token")
            elif status == 403:
                raise ZendeskError(403, "Access denied", "Token lacks required permissions")
            elif status == 404:
                raise ZendeskError(404, "Resource not found", "Check the ID")
            raise ZendeskError(status, str(e), "")
        except httpx.RequestError as e:
            raise ZendeskError(500, f"Request failed: {e}", "Check network connectivity")


client = ZendeskClient()
