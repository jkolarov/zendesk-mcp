"""Tests for batched user-name resolution in search_tickets and get_ticket."""
from unittest.mock import Mock

import zendesk_mcp.tools as tools
from zendesk_mcp.client import ZendeskError


def _make_user(uid, name):
    return {"id": uid, "name": name}


# ── _resolve_user_names ────────────────────────────────────────────────────

def test_resolve_user_names_makes_one_batched_call(monkeypatch):
    mock_client = Mock()
    mock_client.get.return_value = {
        "users": [_make_user(1, "Alice"), _make_user(2, "Bob"), _make_user(3, "Carol")]
    }
    monkeypatch.setattr(tools, "client", mock_client)

    names = tools._resolve_user_names([1, 2, 3])

    assert names == {1: "Alice", 2: "Bob", 3: "Carol"}
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    assert call_args.args[0] == "/api/v2/users/show_many.json"
    # ids string is order-independent (set under the hood) — just check membership
    ids_str = call_args.kwargs["params"]["ids"]
    assert set(ids_str.split(",")) == {"1", "2", "3"}


def test_resolve_user_names_dedupes(monkeypatch):
    """Duplicate IDs in input shouldn't appear twice in the request."""
    mock_client = Mock()
    mock_client.get.return_value = {"users": [_make_user(1, "Alice")]}
    monkeypatch.setattr(tools, "client", mock_client)

    tools._resolve_user_names([1, 1, 1])

    ids_str = mock_client.get.call_args.kwargs["params"]["ids"]
    assert ids_str == "1"


def test_resolve_user_names_filters_falsy_ids(monkeypatch):
    """None and 0 should not be sent to the API."""
    mock_client = Mock()
    mock_client.get.return_value = {"users": [_make_user(5, "Dave")]}
    monkeypatch.setattr(tools, "client", mock_client)

    tools._resolve_user_names([None, 0, 5])

    ids_str = mock_client.get.call_args.kwargs["params"]["ids"]
    assert ids_str == "5"


def test_resolve_user_names_empty_input_makes_zero_calls(monkeypatch):
    mock_client = Mock()
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools._resolve_user_names([])

    assert result == {}
    mock_client.get.assert_not_called()


def test_resolve_user_names_degrades_to_empty_dict_on_error(monkeypatch):
    """If show_many fails (permissions, network), tools that call it must not crash."""
    mock_client = Mock()
    mock_client.get.side_effect = ZendeskError(403, "Forbidden", "Token lacks users:read")
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools._resolve_user_names([1, 2])

    assert result == {}   # graceful degradation


def test_resolve_user_names_skips_users_without_id(monkeypatch):
    """Defensive: a malformed user object without an id should be ignored."""
    mock_client = Mock()
    mock_client.get.return_value = {
        "users": [_make_user(1, "Alice"), {"name": "Mystery"}, _make_user(2, "Bob")]
    }
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools._resolve_user_names([1, 2])

    assert result == {1: "Alice", 2: "Bob"}


# ── show_many 100-ID cap → chunking ────────────────────────────────────────

def test_resolve_user_names_chunks_ids_at_100_per_request(monkeypatch):
    """250 IDs → 3 show_many calls (100 + 100 + 50)."""
    mock_client = Mock()
    # 250 unique IDs
    ids = list(range(1, 251))
    expected_names = {uid: f"User{uid}" for uid in ids}

    def fake_get(path, params=None):
        # Echo back a 'users' list for whatever IDs were asked for in this chunk
        requested = [int(s) for s in params["ids"].split(",")]
        return {"users": [_make_user(uid, expected_names[uid]) for uid in requested]}

    mock_client.get.side_effect = fake_get
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools._resolve_user_names(ids)

    # 250 -> 3 calls (100 + 100 + 50)
    assert mock_client.get.call_count == 3
    # No chunk exceeds 100 IDs
    for call in mock_client.get.call_args_list:
        chunk_size = len(call.kwargs["params"]["ids"].split(","))
        assert chunk_size <= 100
    # All 250 names present
    assert result == expected_names


def test_resolve_user_names_partial_failure_returns_what_succeeded(monkeypatch):
    """If chunk 2 fails, chunks 1 and 3 still return their names."""
    ids = list(range(1, 251))
    expected_names = {uid: f"User{uid}" for uid in ids}

    call_count = {"n": 0}

    def fake_get(path, params=None):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise ZendeskError(500, "Transient", "Try again")
        requested = [int(s) for s in params["ids"].split(",")]
        return {"users": [_make_user(uid, expected_names[uid]) for uid in requested]}

    mock_client = Mock()
    mock_client.get.side_effect = fake_get
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools._resolve_user_names(ids)

    # Chunk 1: IDs 1-100. Chunk 2: 101-200 (failed). Chunk 3: 201-250.
    assert len(result) == 150  # 100 + 0 + 50
    assert result[1] == "User1"
    assert result[250] == "User250"
    assert 101 not in result
    assert 200 not in result


def test_resolve_user_names_exact_100_ids_is_one_call(monkeypatch):
    """Boundary: 100 IDs fits in one chunk."""
    ids = list(range(1, 101))
    mock_client = Mock()
    mock_client.get.return_value = {
        "users": [_make_user(uid, f"User{uid}") for uid in ids]
    }
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools._resolve_user_names(ids)

    assert mock_client.get.call_count == 1
    assert len(result) == 100


def test_resolve_user_names_101_ids_is_two_calls(monkeypatch):
    """Boundary: 101 IDs needs two chunks."""
    ids = list(range(1, 102))
    mock_client = Mock()

    def fake_get(path, params=None):
        requested = [int(s) for s in params["ids"].split(",")]
        return {"users": [_make_user(uid, f"User{uid}") for uid in requested]}

    mock_client.get.side_effect = fake_get
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools._resolve_user_names(ids)

    assert mock_client.get.call_count == 2
    assert len(result) == 101


# ── search_tickets integration ─────────────────────────────────────────────

def test_search_tickets_uses_at_most_two_api_calls(monkeypatch):
    """search.json + ONE show_many.json — never per-user GETs."""
    mock_client = Mock()
    mock_client.get.side_effect = [
        # 1st call: the search itself
        {
            "results": [
                {"id": 100, "subject": "A", "status": "open", "priority": "normal",
                 "requester_id": 1, "assignee_id": 2, "tags": [], "created_at": "", "updated_at": ""},
                {"id": 101, "subject": "B", "status": "open", "priority": "normal",
                 "requester_id": 1, "assignee_id": 3, "tags": [], "created_at": "", "updated_at": ""},
                {"id": 102, "subject": "C", "status": "open", "priority": "normal",
                 "requester_id": 4, "assignee_id": 2, "tags": [], "created_at": "", "updated_at": ""},
            ],
            "count": 3,
        },
        # 2nd call: the batched user lookup
        {"users": [_make_user(1, "Req1"), _make_user(2, "Asg2"),
                   _make_user(3, "Asg3"), _make_user(4, "Req4")]},
    ]
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.search_tickets("type:ticket", per_page=3)

    assert mock_client.get.call_count == 2

    # All four unique IDs should appear in the show_many call
    second_call = mock_client.get.call_args_list[1]
    assert second_call.args[0] == "/api/v2/users/show_many.json"
    ids_str = second_call.kwargs["params"]["ids"]
    assert set(ids_str.split(",")) == {"1", "2", "3", "4"}

    # Names are populated correctly
    items = {t["id"]: t for t in result["items"]}
    assert items[100]["requester_name"] == "Req1"
    assert items[100]["assignee_name"] == "Asg2"
    assert items[101]["assignee_name"] == "Asg3"
    assert items[102]["requester_name"] == "Req4"


def test_search_tickets_degrades_names_to_none_if_batch_fails(monkeypatch):
    """If show_many fails, search_tickets still returns ticket data — just with name=None."""
    call_count = {"n": 0}

    def fake_get(path, params=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "results": [
                    {"id": 100, "subject": "A", "status": "open", "priority": "normal",
                     "requester_id": 1, "assignee_id": 2, "tags": [], "created_at": "", "updated_at": ""},
                ],
                "count": 1,
            }
        # 2nd call is the show_many — simulate failure
        raise ZendeskError(403, "Forbidden", "Token lacks users:read")

    mock_client = Mock()
    mock_client.get.side_effect = fake_get
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.search_tickets("type:ticket")

    # No crash; ticket data preserved; names degrade to None
    assert "items" in result
    assert result["items"][0]["id"] == 100
    assert result["items"][0]["requester_name"] is None
    assert result["items"][0]["assignee_name"] is None


# ── get_ticket integration ─────────────────────────────────────────────────

def test_get_ticket_uses_one_batched_user_call(monkeypatch):
    """get_ticket should issue: ticket GET + show_many(requester+assignee) + comments GET = 3 calls."""
    mock_client = Mock()
    mock_client.get.side_effect = [
        # 1st: the ticket
        {"ticket": {
            "id": 42, "subject": "S", "description": "D", "status": "open",
            "priority": "normal", "type": "question",
            "requester_id": 7, "assignee_id": 8, "organization_id": 99,
            "tags": [], "custom_fields": [], "created_at": "", "updated_at": "",
        }},
        # 2nd: show_many for both user IDs in ONE call
        {"users": [_make_user(7, "Reqie"), _make_user(8, "Asgie")]},
        # 3rd: the comments fetch
        {"comments": []},
    ]
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.get_ticket(42)

    assert mock_client.get.call_count == 3
    show_many_call = mock_client.get.call_args_list[1]
    assert show_many_call.args[0] == "/api/v2/users/show_many.json"
    ids_str = show_many_call.kwargs["params"]["ids"]
    assert set(ids_str.split(",")) == {"7", "8"}

    assert result["ticket"]["requester_name"] == "Reqie"
    assert result["ticket"]["assignee_name"] == "Asgie"
