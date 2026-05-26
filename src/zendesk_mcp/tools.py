from typing import Any, Dict

from .client import client, ZendeskError
from .config import settings


def _get_user_name(user_id: int) -> str | None:
    if not user_id:
        return None
    try:
        result = client.get(f"/api/v2/users/{user_id}.json")
        return result.get("user", {}).get("name")
    except Exception:
        return None


def _validate_ticket_query(query: str) -> None:
    if "type:ticket" not in query:
        raise ValueError("Query must include 'type:ticket'")


# --- Tickets ---


def count_tickets(query: str) -> Dict[str, Any]:
    _validate_ticket_query(query)
    try:
        result = client.get("/api/v2/search/count.json", params={"query": query})
        return {"count": result.get("count", 0), "query": query}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def search_tickets(query: str, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    _validate_ticket_query(query)
    per_page = min(per_page, settings.tools_max_per_page)
    if page > settings.tools_max_pages:
        return {"error": {"type": "pagination_limit", "message": f"Page {page} exceeds maximum of {settings.tools_max_pages}"}}

    try:
        result = client.get("/api/v2/search.json", params={"query": query, "page": page, "per_page": per_page})

        user_ids = set()
        for item in result.get("results", []):
            if item.get("requester_id"):
                user_ids.add(item["requester_id"])
            if item.get("assignee_id"):
                user_ids.add(item["assignee_id"])

        user_names = {}
        for uid in user_ids:
            name = _get_user_name(uid)
            if name:
                user_names[uid] = name

        tickets = []
        for item in result.get("results", []):
            tickets.append({
                "id": item.get("id"),
                "subject": item.get("subject"),
                "status": item.get("status"),
                "priority": item.get("priority"),
                "requester_id": item.get("requester_id"),
                "requester_name": user_names.get(item.get("requester_id")),
                "assignee_id": item.get("assignee_id"),
                "assignee_name": user_names.get(item.get("assignee_id")),
                "organization_id": item.get("organization_id"),
                "tags": item.get("tags", []),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
            })

        total = result.get("count", len(tickets))
        response = {"page": page, "per_page": per_page, "total": total, "returned": len(tickets), "items": tickets}
        if total > page * per_page:
            response["truncated"] = True
        return response
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def get_ticket(ticket_id: int) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/tickets/{ticket_id}.json")
        ticket = result.get("ticket", {})
        ticket_data = {
            "id": ticket.get("id"),
            "subject": ticket.get("subject"),
            "description": ticket.get("description"),
            "status": ticket.get("status"),
            "priority": ticket.get("priority"),
            "type": ticket.get("type"),
            "requester_id": ticket.get("requester_id"),
            "requester_name": _get_user_name(ticket.get("requester_id")),
            "assignee_id": ticket.get("assignee_id"),
            "assignee_name": _get_user_name(ticket.get("assignee_id")),
            "organization_id": ticket.get("organization_id"),
            "tags": ticket.get("tags", []),
            "custom_fields": ticket.get("custom_fields", []),
            "created_at": ticket.get("created_at"),
            "updated_at": ticket.get("updated_at"),
        }
        comments_result = get_ticket_comments(ticket_id, limit=50)
        if "error" not in comments_result:
            ticket_data["comments"] = comments_result.get("comments", [])
        return {"ticket": ticket_data}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def get_ticket_audits(ticket_id: int, limit_events: int = 25) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/tickets/{ticket_id}/audits.json")
        events = []
        for audit in result.get("audits", []):
            for event in audit.get("events", []):
                if event.get("type") == "Change":
                    events.append({"type": f"{event.get('field_name')}_change", "from": event.get("previous_value"), "to": event.get("value"), "at": audit.get("created_at")})
                elif event.get("type") == "Comment":
                    events.append({"type": "comment", "public": event.get("public", False), "body": event.get("body", "")[:200], "at": audit.get("created_at")})
                if len(events) >= limit_events:
                    break
            if len(events) >= limit_events:
                break
        return {"id": ticket_id, "events": events}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def get_ticket_comments(ticket_id: int, limit: int = 25) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/tickets/{ticket_id}/comments.json")
        comments = []
        for comment in result.get("comments", [])[:limit]:
            obj = {
                "id": comment.get("id"),
                "body": comment.get("body"),
                "public": comment.get("public", False),
                "author_id": comment.get("author_id"),
                "created_at": comment.get("created_at"),
            }
            attachments = comment.get("attachments", [])
            if attachments:
                obj["attachments"] = [{"file_name": a.get("file_name"), "content_type": a.get("content_type"), "size": a.get("size"), "url": a.get("content_url")} for a in attachments]
            comments.append(obj)
        return {"ticket_id": ticket_id, "comments": comments, "returned": len(comments)}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


RECOGNISED_FIELDS = {"status", "priority", "subject", "assignee_id", "tags", "custom_fields"}
VALID_STATUSES = {"open", "pending", "hold", "solved", "closed"}
VALID_PRIORITIES = {"low", "normal", "high", "urgent"}


def edit_ticket(ticket_id: int, fields: Dict[str, Any]) -> Dict[str, Any]:
    if not fields or not (set(fields.keys()) & RECOGNISED_FIELDS):
        return {"error": {"type": "validation_error", "message": f"fields must contain at least one of: {', '.join(sorted(RECOGNISED_FIELDS))}"}}
    if {"requester_id", "submitter_id"} & set(fields.keys()):
        return {"error": {"type": "validation_error", "message": "requester_id and submitter_id cannot be changed"}}
    if "status" in fields and fields["status"] not in VALID_STATUSES:
        return {"error": {"type": "validation_error", "message": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}"}}
    if "priority" in fields and fields["priority"] not in VALID_PRIORITIES:
        return {"error": {"type": "validation_error", "message": f"Invalid priority. Must be one of: {', '.join(sorted(VALID_PRIORITIES))}"}}

    try:
        result = client.put(f"/api/v2/tickets/{ticket_id}.json", {"ticket": fields})
        ticket = result.get("ticket", {})
        return {"ticket": {"id": ticket.get("id"), "subject": ticket.get("subject"), "status": ticket.get("status"), "priority": ticket.get("priority"), "tags": ticket.get("tags", []), "updated_at": ticket.get("updated_at")}}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def solve_ticket(ticket_id: int) -> Dict[str, Any]:
    try:
        result = client.put(f"/api/v2/tickets/{ticket_id}.json", {"ticket": {"status": "solved"}})
        ticket = result.get("ticket", {})
        return {"ticket": {"id": ticket.get("id"), "subject": ticket.get("subject"), "status": "solved", "updated_at": ticket.get("updated_at")}}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


# --- Users ---


def get_user(user_id: int) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/users/{user_id}.json")
        user = result.get("user", {})
        return {"user": {"id": user.get("id"), "name": user.get("name"), "email": user.get("email"), "role": user.get("role"), "organization_id": user.get("organization_id"), "active": user.get("active"), "tags": user.get("tags", []), "created_at": user.get("created_at")}}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def search_users(query: str, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    per_page = min(per_page, settings.tools_max_per_page)
    try:
        result = client.get("/api/v2/users/search.json", params={"query": query, "page": page, "per_page": per_page})
        users = [{"id": u.get("id"), "name": u.get("name"), "email": u.get("email"), "role": u.get("role"), "organization_id": u.get("organization_id"), "active": u.get("active")} for u in result.get("users", [])]
        return {"page": page, "per_page": per_page, "total": result.get("count", len(users)), "returned": len(users), "users": users}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


# --- Organizations ---


def get_organization(org_id: int) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/organizations/{org_id}.json")
        org = result.get("organization", {})
        return {"organization": {"id": org.get("id"), "name": org.get("name"), "details": org.get("details"), "notes": org.get("notes"), "tags": org.get("tags", []), "created_at": org.get("created_at")}}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def search_organizations(query: str, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    per_page = min(per_page, settings.tools_max_per_page)
    try:
        result = client.get("/api/v2/organizations/search.json", params={"query": query, "page": page, "per_page": per_page})
        orgs = [{"id": o.get("id"), "name": o.get("name"), "details": o.get("details"), "tags": o.get("tags", [])} for o in result.get("organizations", [])]
        return {"page": page, "per_page": per_page, "total": result.get("count", len(orgs)), "returned": len(orgs), "organizations": orgs}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


# --- Views ---


def get_view(view_id: int) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/views/{view_id}.json")
        view = result.get("view", {})
        return {"view": {"id": view.get("id"), "title": view.get("title"), "active": view.get("active"), "description": view.get("description"), "conditions": view.get("conditions"), "execution": view.get("execution")}}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def count_view(view_id: int) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/views/{view_id}/count.json")
        return {"view_id": view_id, "count": result.get("view_count", {}).get("value", 0)}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def list_view_tickets(view_id: int, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    per_page = min(per_page, settings.tools_max_per_page)
    try:
        result = client.get(f"/api/v2/views/{view_id}/tickets.json", params={"page": page, "per_page": per_page})
        tickets = [{"id": t.get("id"), "subject": t.get("subject"), "status": t.get("status"), "priority": t.get("priority"), "created_at": t.get("created_at"), "updated_at": t.get("updated_at")} for t in result.get("tickets", [])]
        return {"view_id": view_id, "page": page, "per_page": per_page, "returned": len(tickets), "tickets": tickets}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


# --- Ticket Fields ---


def list_ticket_fields() -> Dict[str, Any]:
    try:
        result = client.get("/api/v2/ticket_fields.json")
        fields = [{"id": f.get("id"), "type": f.get("type"), "title": f.get("title"), "description": f.get("description"), "active": f.get("active"), "required": f.get("required"), "custom_field_options": f.get("custom_field_options", [])} for f in result.get("ticket_fields", [])]
        return {"ticket_fields": fields, "count": len(fields)}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


# --- Triggers ---


def list_triggers(active_only: bool = False, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    path = "/api/v2/triggers/active.json" if active_only else "/api/v2/triggers.json"
    try:
        result = client.get(path, params={"page": page, "per_page": per_page})
        triggers = [{"id": t.get("id"), "title": t.get("title"), "active": t.get("active"), "description": t.get("description"), "position": t.get("position"), "conditions": t.get("conditions"), "actions": t.get("actions")} for t in result.get("triggers", [])]
        return {"page": page, "per_page": per_page, "count": result.get("count", len(triggers)), "triggers": triggers}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def get_trigger(trigger_id: int) -> Dict[str, Any]:
    try:
        result = client.get(f"/api/v2/triggers/{trigger_id}.json")
        t = result.get("trigger", {})
        return {"trigger": {"id": t.get("id"), "title": t.get("title"), "active": t.get("active"), "description": t.get("description"), "conditions": t.get("conditions"), "actions": t.get("actions")}}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def search_triggers(query: str, active: bool = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {"query": query}
    if active is not None:
        params["active"] = active
    try:
        result = client.get("/api/v2/triggers/search.json", params=params)
        triggers = [{"id": t.get("id"), "title": t.get("title"), "active": t.get("active"), "conditions": t.get("conditions"), "actions": t.get("actions")} for t in result.get("triggers", [])]
        return {"count": result.get("count", len(triggers)), "triggers": triggers}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


# --- Attachments ---


def get_ticket_attachments(ticket_id: int) -> Dict[str, Any]:
    """Return all attachments across every comment on a ticket, paginating through all comment pages."""
    try:
        attachments = []
        page = 1
        while True:
            result = client.get(f"/api/v2/tickets/{ticket_id}/comments.json", params={"page": page, "per_page": 100})
            for comment in result.get("comments", []):
                for a in comment.get("attachments", []):
                    attachments.append({
                        "id": a.get("id"),
                        "file_name": a.get("file_name"),
                        "content_type": a.get("content_type"),
                        "size": a.get("size"),
                        "url": a.get("content_url"),
                        "inline": a.get("inline", False),
                        "comment_id": comment.get("id"),
                        "comment_created_at": comment.get("created_at"),
                    })
            # Stop when there are no more pages
            if not result.get("next_page"):
                break
            page += 1
        return {"ticket_id": ticket_id, "attachments": attachments, "count": len(attachments)}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def get_attachment(attachment_id: int) -> Dict[str, Any]:
    """Get metadata for a specific attachment by ID."""
    try:
        result = client.get(f"/api/v2/attachments/{attachment_id}.json")
        a = result.get("attachment", {})
        return {
            "attachment": {
                "id": a.get("id"),
                "file_name": a.get("file_name"),
                "content_type": a.get("content_type"),
                "size": a.get("size"),
                "url": a.get("content_url"),
                "inline": a.get("inline", False),
                "thumbnails": [
                    {"file_name": t.get("file_name"), "content_type": t.get("content_type"), "url": t.get("content_url")}
                    for t in a.get("thumbnails", [])
                ],
            }
        }
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


# --- Automations ---


def _format_automation(a: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an automation object from the Zendesk API response."""
    return {
        "id": a.get("id"),
        "title": a.get("title"),
        "active": a.get("active"),
        "position": a.get("position"),
        "conditions": a.get("conditions"),
        "actions": a.get("actions"),
    }


def list_automations(active_only: bool = False, page: int = 1, per_page: int = 100) -> Dict[str, Any]:
    """List automations (time-based business rules), optionally filtered to active ones only."""
    path = "/api/v2/automations/active.json" if active_only else "/api/v2/automations.json"
    try:
        result = client.get(path, params={"page": page, "per_page": per_page})
        automations = [_format_automation(a) for a in result.get("automations", [])]
        return {"page": page, "per_page": per_page, "count": result.get("count", len(automations)), "automations": automations}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def get_automation(automation_id: int) -> Dict[str, Any]:
    """Get a single automation by ID including its conditions and actions."""
    try:
        result = client.get(f"/api/v2/automations/{automation_id}.json")
        return {"automation": _format_automation(result.get("automation", {}))}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}


def search_automations(query: str, active: bool = None) -> Dict[str, Any]:
    """Search automations by title, with an optional active-status filter."""
    params: Dict[str, Any] = {"query": query}
    if active is not None:
        params["active"] = active
    try:
        result = client.get("/api/v2/automations/search.json", params=params)
        automations = [_format_automation(a) for a in result.get("automations", [])]
        return {"count": result.get("count", len(automations)), "automations": automations}
    except ZendeskError as e:
        return {"error": {"type": "zendesk_error", "message": e.message, "hint": e.hint}}
