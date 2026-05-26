"""Tests for the targeted 429-only retry behaviour on ZendeskClient.put().

A 429 from Zendesk means the request was rejected before being processed,
so retrying is safe even for non-idempotent writes (no duplicate side
effects). Any other status (404, 422, 500, etc.) must NOT retry — that
would risk duplicate work.
"""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from zendesk_mcp.client import ZendeskClient, ZendeskError


def _make_response(status: int, body: dict = None, retry_after: str = None) -> MagicMock:
    m = MagicMock(spec=httpx.Response)
    m.status_code = status
    m.json.return_value = body or {}
    m.text = str(body or {})
    m.headers = {"Retry-After": retry_after} if retry_after else {}
    if status >= 400 and status != 429:
        m.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=m
        )
    else:
        m.raise_for_status.return_value = None
    return m


@pytest.fixture
def client_with_no_sleep(monkeypatch):
    """A ZendeskClient instance where time.sleep is a no-op so the suite is fast."""
    monkeypatch.setattr("zendesk_mcp.client.time.sleep", lambda *_: None)
    c = ZendeskClient()
    return c


def test_put_retries_on_429_and_succeeds(client_with_no_sleep):
    """429 then 200 → second call returns parsed JSON."""
    responses = [
        _make_response(429, retry_after="1"),
        _make_response(200, {"ticket": {"id": 42}}),
    ]
    with patch.object(client_with_no_sleep.client, "put", side_effect=responses) as mock_put:
        result = client_with_no_sleep.put("/api/v2/tickets/42.json", {"ticket": {"status": "solved"}})

    assert result == {"ticket": {"id": 42}}
    assert mock_put.call_count == 2


def test_put_retries_up_to_three_attempts_then_raises(client_with_no_sleep):
    """Three consecutive 429s → ZendeskError(429) with 'retries exhausted'."""
    responses = [_make_response(429, retry_after="2") for _ in range(3)]
    with patch.object(client_with_no_sleep.client, "put", side_effect=responses) as mock_put:
        with pytest.raises(ZendeskError) as exc_info:
            client_with_no_sleep.put("/api/v2/tickets/42.json", {"ticket": {"status": "solved"}})

    assert exc_info.value.status == 429
    assert "exhausted" in exc_info.value.message.lower()
    assert mock_put.call_count == 3


def test_put_does_not_retry_on_422_validation_error(client_with_no_sleep):
    """422 (validation error) must not retry — it's the caller's fault, not transient."""
    response_422 = _make_response(422, {"description": "Invalid status value"})
    with patch.object(client_with_no_sleep.client, "put", return_value=response_422) as mock_put:
        with pytest.raises(ZendeskError) as exc_info:
            client_with_no_sleep.put("/api/v2/tickets/42.json", {"ticket": {"status": "bogus"}})

    assert exc_info.value.status == 422
    assert mock_put.call_count == 1


def test_put_does_not_retry_on_404(client_with_no_sleep):
    """404 → no retry; the resource doesn't exist."""
    response_404 = _make_response(404, {"error": "RecordNotFound"})
    with patch.object(client_with_no_sleep.client, "put", return_value=response_404) as mock_put:
        with pytest.raises(ZendeskError) as exc_info:
            client_with_no_sleep.put("/api/v2/tickets/99999.json", {"ticket": {"status": "solved"}})

    assert exc_info.value.status == 404
    assert mock_put.call_count == 1


def test_put_does_not_retry_on_401(client_with_no_sleep):
    """401 → no retry; credentials are bad, won't fix themselves."""
    response_401 = _make_response(401, {"error": "Couldn't authenticate"})
    with patch.object(client_with_no_sleep.client, "put", return_value=response_401) as mock_put:
        with pytest.raises(ZendeskError) as exc_info:
            client_with_no_sleep.put("/api/v2/tickets/42.json", {"ticket": {"status": "solved"}})

    assert exc_info.value.status == 401
    assert mock_put.call_count == 1


def test_put_honours_retry_after_header(monkeypatch):
    """The Retry-After value (capped) is used as the sleep duration."""
    sleep_calls = []
    monkeypatch.setattr("zendesk_mcp.client.time.sleep", lambda s: sleep_calls.append(s))

    client = ZendeskClient()
    responses = [
        _make_response(429, retry_after="5"),
        _make_response(200, {"ticket": {"id": 1}}),
    ]
    with patch.object(client.client, "put", side_effect=responses):
        client.put("/api/v2/tickets/1.json", {"ticket": {"status": "open"}})

    assert sleep_calls == [5]


def test_put_caps_excessive_retry_after_at_90s(monkeypatch):
    """A pathological Retry-After (e.g. 3600s) is capped at PUT_429_MAX_WAIT_SECONDS."""
    sleep_calls = []
    monkeypatch.setattr("zendesk_mcp.client.time.sleep", lambda s: sleep_calls.append(s))

    client = ZendeskClient()
    responses = [
        _make_response(429, retry_after="3600"),
        _make_response(200, {"ticket": {"id": 1}}),
    ]
    with patch.object(client.client, "put", side_effect=responses):
        client.put("/api/v2/tickets/1.json", {"ticket": {"status": "open"}})

    assert sleep_calls == [client.PUT_429_MAX_WAIT_SECONDS]


# ── Retry-After HTTP-date form (RFC 7231 §7.1.3) ───────────────────────────

def test_parse_retry_after_delta_seconds():
    from zendesk_mcp.client import _parse_retry_after
    assert _parse_retry_after("60") == 60
    assert _parse_retry_after("0") == 0
    assert _parse_retry_after("5") == 5


def test_parse_retry_after_http_date_in_future():
    """An HTTP-date 30s in the future yields ~30."""
    from datetime import datetime, timezone, timedelta
    from email.utils import format_datetime
    from zendesk_mcp.client import _parse_retry_after

    future = datetime.now(timezone.utc) + timedelta(seconds=30)
    header = format_datetime(future, usegmt=True)
    parsed = _parse_retry_after(header)
    # Allow some slack for the second tick during test execution
    assert 28 <= parsed <= 31


def test_parse_retry_after_http_date_in_past_returns_zero():
    """An HTTP-date in the past clamps to 0 — never negative."""
    from datetime import datetime, timezone, timedelta
    from email.utils import format_datetime
    from zendesk_mcp.client import _parse_retry_after

    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    header = format_datetime(past, usegmt=True)
    assert _parse_retry_after(header) == 0


def test_parse_retry_after_unparseable_falls_back_to_60():
    from zendesk_mcp.client import _parse_retry_after
    assert _parse_retry_after("not-a-valid-thing") == 60
    assert _parse_retry_after("") == 60


def test_put_honours_retry_after_http_date(monkeypatch):
    """End-to-end: an HTTP-date Retry-After is parsed and used as the sleep duration."""
    from datetime import datetime, timezone, timedelta
    from email.utils import format_datetime

    sleep_calls = []
    monkeypatch.setattr("zendesk_mcp.client.time.sleep", lambda s: sleep_calls.append(s))

    client = ZendeskClient()
    future = datetime.now(timezone.utc) + timedelta(seconds=20)
    http_date = format_datetime(future, usegmt=True)

    responses = [
        _make_response(429, retry_after=http_date),
        _make_response(200, {"ticket": {"id": 1}}),
    ]
    with patch.object(client.client, "put", side_effect=responses):
        client.put("/api/v2/tickets/1.json", {"ticket": {"status": "open"}})

    # One sleep call, within ~2s of the requested 20s (tolerance for tick timing)
    assert len(sleep_calls) == 1
    assert 18 <= sleep_calls[0] <= 21
