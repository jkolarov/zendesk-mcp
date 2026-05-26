"""Unit tests for the new list_views tool."""
from unittest.mock import Mock

import zendesk_mcp.tools as tools


def test_list_views_default_uses_all_views_endpoint(monkeypatch):
    mock_client = Mock()
    mock_client.get.return_value = {
        "views": [
            {"id": 1, "title": "Unsolved tickets", "active": True, "position": 1, "description": "All open"},
            {"id": 2, "title": "VIP escalations", "active": False, "position": 2, "description": None},
        ]
    }
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.list_views()

    mock_client.get.assert_called_once_with(
        "/api/v2/views.json", params={"page": 1, "per_page": 100}
    )
    assert result["returned"] == 2
    assert result["views"][0] == {
        "id": 1,
        "title": "Unsolved tickets",
        "active": True,
        "position": 1,
        "description": "All open",
    }


def test_list_views_active_only_uses_active_endpoint(monkeypatch):
    mock_client = Mock()
    mock_client.get.return_value = {
        "views": [{"id": 1, "title": "Active only", "active": True, "position": 1, "description": ""}]
    }
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.list_views(active_only=True, page=2, per_page=50)

    mock_client.get.assert_called_once_with(
        "/api/v2/views/active.json", params={"page": 2, "per_page": 50}
    )
    assert result["page"] == 2
    assert result["per_page"] == 50
    assert result["returned"] == 1


def test_list_views_per_page_capped_to_max(monkeypatch):
    """per_page must be clamped to settings.tools_max_per_page (default 100)."""
    mock_client = Mock()
    mock_client.get.return_value = {"views": []}
    monkeypatch.setattr(tools, "client", mock_client)

    tools.list_views(per_page=500)

    call_params = mock_client.get.call_args.kwargs["params"]
    assert call_params["per_page"] == 100  # capped


def test_list_views_returns_error_envelope_on_zendesk_failure(monkeypatch):
    from zendesk_mcp.client import ZendeskError

    mock_client = Mock()
    mock_client.get.side_effect = ZendeskError(403, "Forbidden", "Token lacks views:read")
    monkeypatch.setattr(tools, "client", mock_client)

    result = tools.list_views()

    assert "error" in result
    assert result["error"]["type"] == "zendesk_error"
    assert result["error"]["message"] == "Forbidden"
