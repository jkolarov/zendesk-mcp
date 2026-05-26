"""Unit tests for config.py — auth_method property and validation logic."""
import pytest
from zendesk_mcp.config import Settings


def cfg(**kwargs):
    """Helper: build a Settings object with zd_subdomain always set."""
    return Settings(**{"zd_subdomain": "test", **kwargs})


# ── auth_method happy paths ────────────────────────────────────────────────

def test_api_token_mode():
    s = cfg(zd_email="a@b.com", zd_api_token="tok")
    assert s.auth_method == "api_token"


def test_oauth_static_mode():
    s = cfg(zd_oauth_token="mytoken")
    assert s.auth_method == "oauth_static"


def test_oauth_client_credentials_mode():
    s = cfg(zd_oauth_client_id="id123", zd_oauth_client_secret="sec456")
    assert s.auth_method == "oauth_client_credentials"


def test_oauth_client_credentials_wins_over_api_token():
    """Client credentials take priority over API token when both are set."""
    s = cfg(
        zd_oauth_client_id="id",
        zd_oauth_client_secret="sec",
        zd_email="a@b.com",
        zd_api_token="apitok",
    )
    assert s.auth_method == "oauth_client_credentials"


def test_oauth_static_wins_over_client_credentials():
    """Static token takes priority over client credentials when both are set."""
    s = cfg(zd_oauth_token="tok", zd_oauth_client_id="id", zd_oauth_client_secret="sec")
    assert s.auth_method == "oauth_static"


def test_oauth_static_wins_over_api_token():
    s = cfg(zd_oauth_token="tok", zd_email="a@b.com", zd_api_token="apitok")
    assert s.auth_method == "oauth_static"


# ── ZD_OAUTH_SCOPE ─────────────────────────────────────────────────────────

def test_scope_defaults_to_read_write():
    s = cfg(zd_oauth_client_id="id", zd_oauth_client_secret="sec")
    assert s.zd_oauth_scope == "read write"


def test_scope_custom_value():
    s = cfg(zd_oauth_client_id="id", zd_oauth_client_secret="sec", zd_oauth_scope="read")
    assert s.zd_oauth_scope == "read"


# ── zendesk_base_url helper ────────────────────────────────────────────────

def test_base_url():
    s = cfg(zd_oauth_token="tok")
    assert s.zendesk_base_url == "https://test.zendesk.com"


# ── validation errors ──────────────────────────────────────────────────────
# These tests need a clean environment so pydantic-settings doesn't pick up
# ZD_EMAIL / ZD_API_TOKEN / ZD_OAUTH_TOKEN set in the outer shell process.

ZD_VARS = ["ZD_EMAIL", "ZD_API_TOKEN", "ZD_OAUTH_TOKEN",
           "ZD_OAUTH_CLIENT_ID", "ZD_OAUTH_CLIENT_SECRET"]


def test_no_auth_raises(monkeypatch):
    for v in ZD_VARS:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ValueError, match="Authentication not configured"):
        cfg()


def test_partial_client_creds_id_only(monkeypatch):
    for v in ZD_VARS:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ValueError, match="ZD_OAUTH_CLIENT_SECRET"):
        cfg(zd_oauth_client_id="id")


def test_partial_client_creds_secret_only(monkeypatch):
    for v in ZD_VARS:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ValueError, match="ZD_OAUTH_CLIENT_ID"):
        cfg(zd_oauth_client_secret="sec")


def test_api_token_without_email(monkeypatch):
    for v in ZD_VARS:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ValueError, match="ZD_EMAIL"):
        cfg(zd_api_token="tok")


def test_email_without_api_token(monkeypatch):
    for v in ZD_VARS:
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(ValueError, match="ZD_API_TOKEN"):
        cfg(zd_email="a@b.com")
