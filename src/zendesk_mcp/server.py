#!/usr/bin/env python3
import asyncio
import json
from typing import Any

import mcp.server.stdio
from mcp.server import Server
from mcp.types import Tool, TextContent

from .tools import (
    count_tickets, search_tickets, get_ticket, get_ticket_audits, get_ticket_comments,
    edit_ticket, solve_ticket,
    get_user, search_users,
    get_organization, search_organizations,
    get_view, count_view, list_view_tickets,
    list_ticket_fields,
    list_triggers, get_trigger, search_triggers,
    get_ticket_attachments, get_attachment,
    list_automations, get_automation, search_automations,
    get_ticket_metrics,
    list_macros, get_macro, search_macros,
    list_satisfaction_ratings, count_satisfaction_ratings,
)

app = Server("zendesk-mcp")

TOOLS = [
    Tool(
        name="count_tickets",
        description="Count Zendesk tickets matching a search query. Returns exact total count. Query MUST include 'type:ticket'.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Zendesk search query (must include 'type:ticket'). Supports: status, priority, assignee, requester, organization, tags, dates, custom fields."}}, "required": ["query"]},
    ),
    Tool(
        name="search_tickets",
        description="Search Zendesk tickets. Returns full ticket details with names resolved. Query MUST include 'type:ticket'.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Zendesk search query (must include 'type:ticket')."}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25}}, "required": ["query"]},
    ),
    Tool(
        name="get_ticket",
        description="Get full details of a ticket by ID including comments, custom fields, and resolved names.",
        inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer", "description": "Zendesk ticket ID"}}, "required": ["ticket_id"]},
    ),
    Tool(
        name="get_ticket_audits",
        description="Get audit history for a ticket (status changes, reassignments, comments).",
        inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "limit_events": {"type": "integer", "default": 25}}, "required": ["ticket_id"]},
    ),
    Tool(
        name="get_ticket_comments",
        description="Get all comments and internal notes for a ticket.",
        inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "limit": {"type": "integer", "default": 25}}, "required": ["ticket_id"]},
    ),
    Tool(
        name="edit_ticket",
        description="Update ticket fields: status, priority, subject, assignee_id, tags, custom_fields.",
        inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}, "fields": {"type": "object", "description": "Fields to update (status, priority, subject, assignee_id, tags, custom_fields)."}}, "required": ["ticket_id", "fields"]},
    ),
    Tool(
        name="solve_ticket",
        description="Set a ticket's status to solved.",
        inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer"}}, "required": ["ticket_id"]},
    ),
    Tool(
        name="get_user",
        description="Get a Zendesk user by ID.",
        inputSchema={"type": "object", "properties": {"user_id": {"type": "integer"}}, "required": ["user_id"]},
    ),
    Tool(
        name="search_users",
        description="Search Zendesk users by name or email.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string"}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25}}, "required": ["query"]},
    ),
    Tool(
        name="get_organization",
        description="Get a Zendesk organization by ID.",
        inputSchema={"type": "object", "properties": {"org_id": {"type": "integer"}}, "required": ["org_id"]},
    ),
    Tool(
        name="search_organizations",
        description="Search Zendesk organizations by name.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string"}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25}}, "required": ["query"]},
    ),
    Tool(
        name="get_view",
        description="Get details of a Zendesk view by ID.",
        inputSchema={"type": "object", "properties": {"view_id": {"type": "integer"}}, "required": ["view_id"]},
    ),
    Tool(
        name="count_view",
        description="Get ticket count for a Zendesk view.",
        inputSchema={"type": "object", "properties": {"view_id": {"type": "integer"}}, "required": ["view_id"]},
    ),
    Tool(
        name="list_view_tickets",
        description="List tickets in a Zendesk view.",
        inputSchema={"type": "object", "properties": {"view_id": {"type": "integer"}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25}}, "required": ["view_id"]},
    ),
    Tool(
        name="list_ticket_fields",
        description="List all ticket fields including custom fields with their options.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="list_triggers",
        description="List Zendesk triggers (business rules).",
        inputSchema={"type": "object", "properties": {"active_only": {"type": "boolean", "default": False}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 100}}, "required": []},
    ),
    Tool(
        name="get_trigger",
        description="Get a single Zendesk trigger by ID.",
        inputSchema={"type": "object", "properties": {"trigger_id": {"type": "integer"}}, "required": ["trigger_id"]},
    ),
    Tool(
        name="search_triggers",
        description="Search Zendesk triggers by title.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string"}, "active": {"type": "boolean"}}, "required": ["query"]},
    ),
    # Attachments
    Tool(
        name="get_ticket_attachments",
        description="List all attachments across every comment on a ticket. Returns file name, content type, size, and direct download URL for each attachment.",
        inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer", "description": "Zendesk ticket ID"}}, "required": ["ticket_id"]},
    ),
    Tool(
        name="get_attachment",
        description="Get metadata for a single attachment by its ID, including download URL and thumbnails.",
        inputSchema={"type": "object", "properties": {"attachment_id": {"type": "integer", "description": "Zendesk attachment ID"}}, "required": ["attachment_id"]},
    ),
    # Automations
    Tool(
        name="list_automations",
        description="List Zendesk automations (time-based business rules). Optionally filter to active automations only.",
        inputSchema={"type": "object", "properties": {"active_only": {"type": "boolean", "default": False}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 100}}, "required": []},
    ),
    Tool(
        name="get_automation",
        description="Get a single Zendesk automation by ID, including its conditions and actions.",
        inputSchema={"type": "object", "properties": {"automation_id": {"type": "integer", "description": "Zendesk automation ID"}}, "required": ["automation_id"]},
    ),
    Tool(
        name="search_automations",
        description="Search Zendesk automations by title. Optionally filter by active status.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Search query matched against automation titles"}, "active": {"type": "boolean", "description": "If set, filter to only active (true) or inactive (false) automations"}}, "required": ["query"]},
    ),
    # Ticket Metrics
    Tool(
        name="get_ticket_metrics",
        description="Get performance metrics for a ticket: first reply time, full resolution time, agent wait time, on-hold time, number of reopens, and reply count. Times are in both calendar and business-hours minutes.",
        inputSchema={"type": "object", "properties": {"ticket_id": {"type": "integer", "description": "Zendesk ticket ID"}}, "required": ["ticket_id"]},
    ),
    # Macros
    Tool(
        name="list_macros",
        description="List Zendesk macros (canned ticket actions agents can apply in one click). Optionally filter to active macros only.",
        inputSchema={"type": "object", "properties": {"active_only": {"type": "boolean", "default": False}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 100}}, "required": []},
    ),
    Tool(
        name="get_macro",
        description="Get a single Zendesk macro by ID, including all its actions.",
        inputSchema={"type": "object", "properties": {"macro_id": {"type": "integer", "description": "Zendesk macro ID"}}, "required": ["macro_id"]},
    ),
    Tool(
        name="search_macros",
        description="Search Zendesk macros by title. Optionally filter by active status.",
        inputSchema={"type": "object", "properties": {"query": {"type": "string", "description": "Search query matched against macro titles"}, "active": {"type": "boolean", "description": "Filter to only active (true) or inactive (false) macros"}}, "required": ["query"]},
    ),
    # Satisfaction Ratings (CSAT)
    Tool(
        name="list_satisfaction_ratings",
        description="List CSAT satisfaction ratings. Filter by score ('good', 'bad', 'offered', 'received', 'good_with_comment', 'bad_without_comment', etc.) and/or a Unix-epoch date range.",
        inputSchema={"type": "object", "properties": {"score": {"type": "string", "description": "Filter by score: 'good', 'bad', 'offered', 'unoffered', 'received', or variants like 'good_with_comment'"}, "start_time": {"type": "integer", "description": "Start of date range as Unix epoch timestamp"}, "end_time": {"type": "integer", "description": "End of date range as Unix epoch timestamp"}, "page": {"type": "integer", "minimum": 1, "default": 1}, "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "default": 25}}, "required": []},
    ),
    Tool(
        name="count_satisfaction_ratings",
        description="Return an approximate account-level total count of all CSAT ratings. Uses Zendesk's /count endpoint — no filters supported.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
]

TOOL_DISPATCH = {
    "count_tickets": lambda a: count_tickets(a["query"]),
    "search_tickets": lambda a: search_tickets(a["query"], a.get("page", 1), a.get("per_page", 25)),
    "get_ticket": lambda a: get_ticket(a["ticket_id"]),
    "get_ticket_audits": lambda a: get_ticket_audits(a["ticket_id"], a.get("limit_events", 25)),
    "get_ticket_comments": lambda a: get_ticket_comments(a["ticket_id"], a.get("limit", 25)),
    "edit_ticket": lambda a: edit_ticket(a["ticket_id"], a["fields"]),
    "solve_ticket": lambda a: solve_ticket(a["ticket_id"]),
    "get_user": lambda a: get_user(a["user_id"]),
    "search_users": lambda a: search_users(a["query"], a.get("page", 1), a.get("per_page", 25)),
    "get_organization": lambda a: get_organization(a["org_id"]),
    "search_organizations": lambda a: search_organizations(a["query"], a.get("page", 1), a.get("per_page", 25)),
    "get_view": lambda a: get_view(a["view_id"]),
    "count_view": lambda a: count_view(a["view_id"]),
    "list_view_tickets": lambda a: list_view_tickets(a["view_id"], a.get("page", 1), a.get("per_page", 25)),
    "list_ticket_fields": lambda a: list_ticket_fields(),
    "list_triggers": lambda a: list_triggers(a.get("active_only", False), a.get("page", 1), a.get("per_page", 100)),
    "get_trigger": lambda a: get_trigger(a["trigger_id"]),
    "search_triggers": lambda a: search_triggers(a["query"], a.get("active")),
    # Attachments
    "get_ticket_attachments": lambda a: get_ticket_attachments(a["ticket_id"]),
    "get_attachment": lambda a: get_attachment(a["attachment_id"]),
    # Automations
    "list_automations": lambda a: list_automations(a.get("active_only", False), a.get("page", 1), a.get("per_page", 100)),
    "get_automation": lambda a: get_automation(a["automation_id"]),
    "search_automations": lambda a: search_automations(a["query"], a.get("active")),
    # Ticket Metrics
    "get_ticket_metrics": lambda a: get_ticket_metrics(a["ticket_id"]),
    # Macros
    "list_macros": lambda a: list_macros(a.get("active_only", False), a.get("page", 1), a.get("per_page", 100)),
    "get_macro": lambda a: get_macro(a["macro_id"]),
    "search_macros": lambda a: search_macros(a["query"], a.get("active")),
    # Satisfaction Ratings
    "list_satisfaction_ratings": lambda a: list_satisfaction_ratings(a.get("score"), a.get("start_time"), a.get("end_time"), a.get("page", 1), a.get("per_page", 25)),
    "count_satisfaction_ratings": lambda a: count_satisfaction_ratings(),
}


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def handle_call_tool(name: str, arguments: Any) -> list[TextContent]:
    handler = TOOL_DISPATCH.get(name)
    if not handler:
        result = {"error": {"type": "unknown_tool", "message": f"Unknown tool: {name}"}}
    else:
        try:
            result = handler(arguments)
        except Exception as e:
            result = {"error": {"type": "execution_error", "message": str(e)}}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


def main():
    asyncio.run(_run())


async def _run():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    main()
