"""Tests for the rewritten search_organizations: uses Zendesk Search syntax."""
from unittest.mock import Mock

import zendesk_mcp.tools as tools
from zendesk_mcp.client import ZendeskError


def test_bare_term_is_scoped_to_type_organization(monkeypatch):
    """A query without 'type:' is auto-prefixed with 'type:organization'."""
    mock_client = Mock()
    mock_client.get.return_value = {
        "results": [
            {"result_type": "organization", "id": 1, "name": "Acme Corp", "details": "a", "tags": ["vip"]},
            {"result_type": "organization", "id": 2, "name": "Acme Inc",  "details": "b", "tags": []},
        ],
        "count": 2,
    }
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.search_organizations("acme")

    mock_client.get.assert_called_once_with(
        "/api/v2/search.json",
        params={"query": "type:organization acme", "page": 1, "per_page": 25},
    )
    assert result["returned"] == 2
    assert result["organizations"][0]["name"] == "Acme Corp"


def test_explicit_type_organization_is_normalised(monkeypatch):
    """Caller writes 'type:organization tags:vip' — we strip the redundant
    type clause and re-prefix canonically, so the final query has exactly
    one type:organization (no double-prefix)."""
    mock_client = Mock()
    mock_client.get.return_value = {"results": [], "count": 0}
    monkeypatch.setattr(tools, "client", mock_client)

    tools.search_organizations("type:organization tags:vip notes:partner")

    mock_client.get.assert_called_once_with(
        "/api/v2/search.json",
        params={"query": "type:organization tags:vip notes:partner", "page": 1, "per_page": 25},
    )


def test_explicit_type_user_is_stripped_and_replaced(monkeypatch):
    """A caller cannot redirect the tool to a different search type.

    search_organizations('type:user alice') must NOT run a user search.
    The tool contract is to search organizations; we strip the bogus
    type clause and force type:organization.
    """
    mock_client = Mock()
    mock_client.get.return_value = {"results": [], "count": 0}
    monkeypatch.setattr(tools, "client", mock_client)

    tools.search_organizations("type:user alice")

    params = mock_client.get.call_args.kwargs["params"]
    assert params["query"] == "type:organization alice"


def test_explicit_type_ticket_is_stripped_and_replaced(monkeypatch):
    mock_client = Mock()
    mock_client.get.return_value = {"results": [], "count": 0}
    monkeypatch.setattr(tools, "client", mock_client)

    tools.search_organizations("type:ticket status:open")

    params = mock_client.get.call_args.kwargs["params"]
    assert params["query"] == "type:organization status:open"


def test_only_type_clause_query_becomes_bare_type_organization(monkeypatch):
    """Edge case: caller passes ONLY a type:X clause with no extra filters."""
    mock_client = Mock()
    mock_client.get.return_value = {"results": [], "count": 0}
    monkeypatch.setattr(tools, "client", mock_client)

    tools.search_organizations("type:user")

    params = mock_client.get.call_args.kwargs["params"]
    assert params["query"] == "type:organization"


def test_non_organization_results_are_filtered_out(monkeypatch):
    """A defensive filter excludes anything that isn't a true organization result."""
    mock_client = Mock()
    mock_client.get.return_value = {
        "results": [
            {"result_type": "organization", "id": 1, "name": "Acme", "details": "", "tags": []},
            {"result_type": "user",         "id": 9, "name": "Alice"},
            {"result_type": "ticket",       "id": 99, "subject": "stray ticket"},
        ],
        "count": 3,
    }
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.search_organizations("acme")

    assert result["returned"] == 1
    assert result["organizations"][0]["id"] == 1


def test_per_page_capped_to_max(monkeypatch):
    mock_client = Mock()
    mock_client.get.return_value = {"results": [], "count": 0}
    monkeypatch.setattr(tools, "client", mock_client)

    tools.search_organizations("acme", per_page=500)

    call_params = mock_client.get.call_args.kwargs["params"]
    assert call_params["per_page"] == 100


def test_returns_error_envelope_on_zendesk_error(monkeypatch):
    mock_client = Mock()
    mock_client.get.side_effect = ZendeskError(403, "Forbidden", "Token lacks search:read")
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.search_organizations("acme")

    assert "error" in result
    assert result["error"]["type"] == "zendesk_error"
    assert result["error"]["message"] == "Forbidden"


def test_pagination_passes_through(monkeypatch):
    mock_client = Mock()
    mock_client.get.return_value = {"results": [], "count": 0}
    monkeypatch.setattr(tools, "client", mock_client)

    tools.search_organizations("acme", page=3, per_page=50)

    call_params = mock_client.get.call_args.kwargs["params"]
    assert call_params["page"] == 3
    assert call_params["per_page"] == 50
