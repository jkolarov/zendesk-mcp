import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, cast

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .config import settings


def _parse_retry_after(value: str) -> int:
    """Parse a Retry-After header into seconds."""
    if not value:
        return 60
    try:
        return max(0, int(value))
    except ValueError:
        pass
    try:
        target = parsedate_to_datetime(value)
        if target is None:
            return 60
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        delta = (target - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(delta))
    except (TypeError, ValueError):
        return 60

ALLOWED_PATHS = {
    "/api/v2/search.json",
    "/api/v2/search/count.json",
    "/api/v2/tickets/{id}.json",
    "/api/v2/tickets/{id}/audits.json",
    "/api/v2/tickets/{id}/comments.json",
    "/api/v2/users/{id}.json",
    "/api/v2/users/search.json",
    "/api/v2/users/show_many.json",
    "/api/v2/organizations/{id}.json",
    "/api/v2/organizations/search.json",
    "/api/v2/views.json",
    "/api/v2/views/active.json",
    "/api/v2/views/{id}.json",
    "/api/v2/views/{id}/count.json",
    "/api/v2/views/{id}/tickets.json",
    "/api/v2/ticket_fields.json",
    "/api/v2/triggers.json",
    "/api/v2/triggers/active.json",
    "/api/v2/triggers/search.json",
    "/api/v2/triggers/{id}.json",
    # Attachments
    "/api/v2/attachments/{id}.json",
    # Automations
    "/api/v2/automations.json",
    "/api/v2/automations/active.json",
    "/api/v2/automations/search.json",
    "/api/v2/automations/{id}.json",
    # Ticket metrics
    "/api/v2/tickets/{id}/metrics.json",
    # Macros
    "/api/v2/macros.json",
    "/api/v2/macros/active.json",
    "/api/v2/macros/search.json",
    "/api/v2/macros/{id}.json",
    # Satisfaction ratings
    "/api/v2/satisfaction_ratings.json",
    "/api/v2/satisfaction_ratings/count.json",
    "/api/v2/satisfaction_ratings/{id}.json",
}


class ZendeskError(Exception):
    def __init__(self, status: int, message: str, hint: str = ""):
        self.status = status
        self.message = message
        self.hint = hint
        super().__init__(message)


class ZendeskClient:
    def _fetch_client_credentials_token(self) -> str:
        """Mint a fresh OAuth access token using the Client Credentials grant.

        POSTs to ``{base_url}/oauth/tokens`` — this endpoint is intentionally
        bypassed from the ALLOWED_PATHS whitelist because it is an auth
        bootstrap call, not a data endpoint.

        Raises:
            ZendeskError: on HTTP error or if the response lacks an
                ``access_token`` field.
        """
        try:
            resp = httpx.post(
                f"https://{settings.zd_subdomain}.zendesk.com/oauth/tokens",
                data={
                    "grant_type": "client_credentials",
                    "client_id": settings.zd_oauth_client_id,
                    "client_secret": settings.zd_oauth_client_secret,
                    "scope": settings.zd_oauth_scope,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=15.0,
            )
        except httpx.RequestError as e:
            raise ZendeskError(
                500,
                f"OAuth token request failed: {e}",
                "Check network connectivity and ZD_SUBDOMAIN",
            )

        if resp.status_code == 401:
            raise ZendeskError(
                401,
                "OAuth client credentials rejected by Zendesk",
                "Check ZD_OAUTH_CLIENT_ID and ZD_OAUTH_CLIENT_SECRET",
            )
        if resp.status_code == 400:
            detail = resp.json().get("error_description") or resp.text
            raise ZendeskError(
                400,
                f"OAuth token request failed: {detail}",
                "Check ZD_OAUTH_CLIENT_ID, ZD_OAUTH_CLIENT_SECRET, and ZD_OAUTH_SCOPE",
            )
        if resp.status_code != 200:
            raise ZendeskError(
                resp.status_code,
                f"Unexpected response from OAuth token endpoint: HTTP {resp.status_code}",
                "",
            )

        token = resp.json().get("access_token")
        if not token:
            raise ZendeskError(
                500,
                "OAuth response did not contain an access_token",
                "Unexpected Zendesk response format — please report this as a bug",
            )
        return token

    def __init__(self):
        self.base_url = settings.zendesk_base_url
        self.auth_method = settings.auth_method

        client_kwargs: Dict[str, Any] = {
            "base_url": self.base_url,
            "timeout": 30.0,
            "headers": {"Accept": "application/json"},
        }

        if self.auth_method == "oauth_client_credentials":
            token = self._fetch_client_credentials_token()
            client_kwargs["headers"]["Authorization"] = f"Bearer {token}"
        elif self.auth_method == "oauth_static":
            client_kwargs["headers"]["Authorization"] = f"Bearer {cast(str, settings.zd_oauth_token)}"
        else:
            client_kwargs["auth"] = (f"{settings.zd_email}/token", settings.zd_api_token)

        self.client = httpx.Client(**client_kwargs)

    def _refresh_client_credentials_token(self) -> None:
        """Re-mint the access token and update the in-memory Authorization header.

        Called once on a 401 when ``auth_method == "oauth_client_credentials"``.
        Zendesk OAuth access tokens have a finite TTL, so a long-lived MCP server
        will eventually outlive its initial token. Re-minting recovers transparently
        on the next call.
        """
        token = self._fetch_client_credentials_token()
        self.client.headers["Authorization"] = f"Bearer {token}"

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
            if response.status_code == 401 and self.auth_method == "oauth_client_credentials":
                # Token may have expired — re-mint once and retry the request
                self._refresh_client_credentials_token()
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

    PUT_429_MAX_WAIT_SECONDS = 90

    def put(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """PUT with targeted 429-only retry."""
        self._validate_path(path)
        max_attempts = 3
        last_retry_after = "60"
        for attempt in range(max_attempts):
            try:
                response = self.client.put(
                    path, json=body, headers={"Content-Type": "application/json"}
                )
                if response.status_code == 401 and self.auth_method == "oauth_client_credentials":
                    self._refresh_client_credentials_token()
                    response = self.client.put(
                        path, json=body, headers={"Content-Type": "application/json"}
                    )
                if response.status_code == 429:
                    last_retry_after = response.headers.get("Retry-After", "60")
                    if attempt < max_attempts - 1:
                        wait_seconds = min(
                            _parse_retry_after(last_retry_after),
                            self.PUT_429_MAX_WAIT_SECONDS,
                        )
                        time.sleep(wait_seconds)
                        continue
                    raise ZendeskError(
                        429,
                        "Rate limit exceeded (retries exhausted)",
                        f"Server asked to retry after {last_retry_after}",
                    )
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
