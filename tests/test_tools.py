from unittest.mock import Mock

import zendesk_mcp.tools as tools


def test_get_ticket_includes_comments_by_default(monkeypatch):
    """Default behaviour: include comments AND resolve requester/assignee names."""
    mock_client = Mock()
    mock_client.get.return_value = {
        "ticket": {
            "id": 42,
            "subject": "Example",
            "description": "Body",
            "status": "open",
            "priority": "normal",
            "type": "question",
            "requester_id": 101,
            "assignee_id": 202,
            "organization_id": 303,
            "tags": ["vip"],
            "custom_fields": [{"id": 1, "value": "x"}],
            "created_at": "2026-05-26T00:00:00Z",
            "updated_at": "2026-05-26T01:00:00Z",
        }
    }
    mock_comments = Mock(return_value={"ticket_id": 42, "comments": [{"id": 1, "body": "hi"}], "returned": 1})

    monkeypatch.setattr(tools, "client", mock_client)
    monkeypatch.setattr(tools, "_get_user_name", lambda user_id: {101: "Requester", 202: "Assignee"}.get(user_id))
    monkeypatch.setattr(tools, "get_ticket_comments", mock_comments)

    result = tools.get_ticket(42)

    assert result["ticket"]["comments"] == [{"id": 1, "body": "hi"}]
    assert result["ticket"]["requester_name"] == "Requester"
    assert result["ticket"]["assignee_name"] == "Assignee"
    mock_client.get.assert_called_once_with("/api/v2/tickets/42.json")
    mock_comments.assert_called_once_with(42, limit=50)


def test_get_ticket_skips_comments_and_name_resolution_when_disabled(monkeypatch):
    """include_comments=False must be a single-API-call fast path.

    Skips both:
      - the comments fetch (1 extra call)
      - requester/assignee name resolution via _get_user_name (2 extra calls)
    """
    mock_client = Mock()
    mock_client.get.return_value = {
        "ticket": {
            "id": 42,
            "subject": "Example",
            "description": "Body",
            "status": "open",
            "priority": "normal",
            "type": "question",
            "requester_id": 101,
            "assignee_id": 202,
            "organization_id": 303,
            "tags": ["vip"],
            "custom_fields": [{"id": 1, "value": "x"}],
            "created_at": "2026-05-26T00:00:00Z",
            "updated_at": "2026-05-26T01:00:00Z",
        }
    }
    mock_comments = Mock()
    mock_get_user_name = Mock()

    monkeypatch.setattr(tools, "client", mock_client)
    monkeypatch.setattr(tools, "_get_user_name", mock_get_user_name)
    monkeypatch.setattr(tools, "get_ticket_comments", mock_comments)

    result = tools.get_ticket(42, include_comments=False)

    # The ticket payload must NOT include comments or resolved names
    assert "comments" not in result["ticket"]
    assert "requester_name" not in result["ticket"]
    assert "assignee_name" not in result["ticket"]
    # IDs are still present so callers can resolve names themselves if they want
    assert result["ticket"]["requester_id"] == 101
    assert result["ticket"]["assignee_id"] == 202
    # Exactly one API call: the ticket GET. No comments, no user lookups.
    mock_client.get.assert_called_once_with("/api/v2/tickets/42.json")
    mock_comments.assert_not_called()
    mock_get_user_name.assert_not_called()
