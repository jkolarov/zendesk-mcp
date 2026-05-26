"""Unit tests for ZendeskClient._fetch_client_credentials_token().

All HTTP calls are mocked. No real network access.
"""
import pytest
import httpx
from unittest.mock import patch, MagicMock

from zendesk_mcp.client import ZendeskClient, ZendeskError


# ── Helpers ────────────────────────────────────────────────────────────────

def _mock_resp(status: int, body: dict) -> MagicMock:
    """Build a fake httpx.Response-like object."""
    m = MagicMock(spec=httpx.Response)
    m.status_code = status
    m.json.return_value = body
    m.text = str(body)
    if status >= 400:
        m.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=m
        )
    else:
        m.raise_for_status.return_value = None
    return m


def _uninitialised_client() -> ZendeskClient:
    """Return a ZendeskClient that skipped __init__ (no self.client, no HTTP calls)."""
    obj = ZendeskClient.__new__(ZendeskClient)
    # _fetch_client_credentials_token uses settings.zd_subdomain, not self.base_url
    return obj


ENV = {
    "ZD_SUBDOMAIN": "test-acme",
    "ZD_OAUTH_CLIENT_ID": "my_client_id",
    "ZD_OAUTH_CLIENT_SECRET": "my_client_secret",
}


# ── Test cases ─────────────────────────────────────────────────────────────

@patch.dict("os.environ", ENV, clear=False)
def test_happy_path_returns_token(monkeypatch):
    """200 response with access_token → token string returned."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli
    # Must patch the settings reference in client.py — that's what the method reads
    new_settings = cfg.Settings()
    monkeypatch.setattr(cli, "settings", new_settings)

    mock_resp = _mock_resp(200, {"access_token": "tok_abc123", "token_type": "Bearer"})
    with patch("zendesk_mcp.client.httpx.post", return_value=mock_resp) as mock_post:
        token = _uninitialised_client()._fetch_client_credentials_token()

    assert token == "tok_abc123"
    mock_post.assert_called_once()
    call_data = mock_post.call_args.kwargs.get("data", {})
    assert call_data["grant_type"] == "client_credentials"
    assert call_data["client_id"] == "my_client_id"
    assert call_data["client_secret"] == "my_client_secret"


@patch.dict("os.environ", ENV, clear=False)
def test_401_raises_zendesk_error(monkeypatch):
    """401 from token endpoint → ZendeskError(401) with hint about credentials."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli
    monkeypatch.setattr(cli, "settings", cfg.Settings())

    mock_resp = _mock_resp(401, {"error": "invalid_client"})
    with patch("zendesk_mcp.client.httpx.post", return_value=mock_resp):
        with pytest.raises(ZendeskError) as exc_info:
            _uninitialised_client()._fetch_client_credentials_token()

    assert exc_info.value.status == 401
    assert "CLIENT_ID" in exc_info.value.hint or "CLIENT_SECRET" in exc_info.value.hint


@patch.dict("os.environ", ENV, clear=False)
def test_400_includes_error_description(monkeypatch):
    """400 response → ZendeskError(400) and error_description surfaced in message."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli
    monkeypatch.setattr(cli, "settings", cfg.Settings())

    mock_resp = _mock_resp(400, {
        "error": "invalid_scope",
        "error_description": "The requested scope is invalid or unknown",
    })
    with patch("zendesk_mcp.client.httpx.post", return_value=mock_resp):
        with pytest.raises(ZendeskError) as exc_info:
            _uninitialised_client()._fetch_client_credentials_token()

    assert exc_info.value.status == 400
    assert "invalid or unknown" in exc_info.value.message


@patch.dict("os.environ", ENV, clear=False)
def test_network_error_raises_500(monkeypatch):
    """httpx.RequestError (timeout, DNS) → ZendeskError(500)."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli
    monkeypatch.setattr(cli, "settings", cfg.Settings())

    with patch("zendesk_mcp.client.httpx.post", side_effect=httpx.RequestError("connection timeout")):
        with pytest.raises(ZendeskError) as exc_info:
            _uninitialised_client()._fetch_client_credentials_token()

    assert exc_info.value.status == 500
    hint_lower = exc_info.value.hint.lower()
    assert "connectivity" in hint_lower or "network" in hint_lower or "subdomain" in hint_lower


@patch.dict("os.environ", ENV, clear=False)
def test_missing_access_token_in_200_response(monkeypatch):
    """200 response without access_token key → ZendeskError(500)."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli
    monkeypatch.setattr(cli, "settings", cfg.Settings())

    mock_resp = _mock_resp(200, {"token_type": "Bearer"})  # no access_token
    with patch("zendesk_mcp.client.httpx.post", return_value=mock_resp):
        with pytest.raises(ZendeskError) as exc_info:
            _uninitialised_client()._fetch_client_credentials_token()

    assert exc_info.value.status == 500
    assert "access_token" in exc_info.value.message


@patch.dict("os.environ", ENV, clear=False)
def test_unexpected_status_code_raises(monkeypatch):
    """Non-200/400/401 status (e.g. 503) → ZendeskError with that status code."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli
    monkeypatch.setattr(cli, "settings", cfg.Settings())

    mock_resp = _mock_resp(503, {"error": "service_unavailable"})
    with patch("zendesk_mcp.client.httpx.post", return_value=mock_resp):
        with pytest.raises(ZendeskError) as exc_info:
            _uninitialised_client()._fetch_client_credentials_token()

    assert exc_info.value.status == 503


# ── Token refresh on 401 (long-lived MCP server scenario) ──────────────────

@patch.dict("os.environ", ENV, clear=False)
def test_get_refreshes_token_on_401_in_client_credentials_mode(monkeypatch):
    """A 401 from a tool call triggers one re-mint + retry in client_credentials mode."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli

    monkeypatch.setattr(cli, "settings", cfg.Settings())

    # Build a real ZendeskClient with mocked startup token fetch
    initial_token_resp = _mock_resp(200, {"access_token": "first_token"})
    refreshed_token_resp = _mock_resp(200, {"access_token": "second_token"})

    with patch("zendesk_mcp.client.httpx.post",
               side_effect=[initial_token_resp, refreshed_token_resp]):
        client_obj = cli.ZendeskClient()

    assert client_obj.client.headers["Authorization"] == "Bearer first_token"

    # First GET returns 401 (token expired), second GET returns 200
    first_resp = _mock_resp(401, {"error": "invalid_token"})
    second_resp = _mock_resp(200, {"tickets": []})

    with patch.object(client_obj.client, "get", side_effect=[first_resp, second_resp]) as mock_get, \
         patch("zendesk_mcp.client.httpx.post", return_value=refreshed_token_resp):
        result = client_obj.get("/api/v2/search.json", params={"query": "type:ticket"})

    assert result == {"tickets": []}
    assert mock_get.call_count == 2
    assert client_obj.client.headers["Authorization"] == "Bearer second_token"


@patch.dict("os.environ", ENV, clear=False)
def test_get_does_not_refresh_on_401_for_oauth_static_mode(monkeypatch):
    """oauth_static mode must NOT trigger a re-mint on 401 — there is no client_id/secret."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli

    static_env = {"ZD_SUBDOMAIN": "test-acme", "ZD_OAUTH_TOKEN": "static_token_abc"}
    with patch.dict("os.environ", static_env, clear=True):
        monkeypatch.setattr(cli, "settings", cfg.Settings())
        client_obj = cli.ZendeskClient()

    assert client_obj.auth_method == "oauth_static"

    error_resp = _mock_resp(401, {"error": "invalid_token"})
    with patch.object(client_obj.client, "get", return_value=error_resp), \
         patch("zendesk_mcp.client.httpx.post") as mock_post:
        with pytest.raises(ZendeskError) as exc_info:
            client_obj.get("/api/v2/search.json", params={"query": "type:ticket"})

    assert exc_info.value.status == 401
    mock_post.assert_not_called()   # token endpoint must NOT be hit


@patch.dict("os.environ", ENV, clear=False)
def test_put_refreshes_token_on_401_in_client_credentials_mode(monkeypatch):
    """Same one-shot refresh logic must apply to PUT (write operations)."""
    import zendesk_mcp.config as cfg
    import zendesk_mcp.client as cli

    monkeypatch.setattr(cli, "settings", cfg.Settings())

    initial_token_resp = _mock_resp(200, {"access_token": "first_token"})
    refreshed_token_resp = _mock_resp(200, {"access_token": "second_token"})

    with patch("zendesk_mcp.client.httpx.post",
               side_effect=[initial_token_resp, refreshed_token_resp]):
        client_obj = cli.ZendeskClient()

    first_resp = _mock_resp(401, {"error": "invalid_token"})
    second_resp = _mock_resp(200, {"ticket": {"id": 42}})

    with patch.object(client_obj.client, "put", side_effect=[first_resp, second_resp]) as mock_put, \
         patch("zendesk_mcp.client.httpx.post", return_value=refreshed_token_resp):
        result = client_obj.put("/api/v2/tickets/42.json", body={"ticket": {"status": "solved"}})

    assert result == {"ticket": {"id": 42}}
    assert mock_put.call_count == 2
