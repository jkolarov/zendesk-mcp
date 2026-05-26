# Tool Reference

29 tools across 8 categories. All tools follow the same error envelope:
```json
{ "error": { "type": "zendesk_error|validation_error|pagination_limit", "message": "...", "hint": "..." } }
```

---

## Tickets (7 tools)

### `count_tickets`
Count tickets matching a Zendesk search query.  
**Required:** `query` (string, must contain `type:ticket`)  
**Returns:** `{ "count": 42, "query": "..." }`  
**Example:** `count_tickets("type:ticket status:open assignee:me")`

---

### `search_tickets`
Search tickets with full details and resolved user names.  
**Required:** `query` | **Optional:** `page` (default 1), `per_page` (default 25, max 100)  
**Returns:** `{ page, per_page, total, returned, items: [...], truncated? }`  
Each item includes: id, subject, status, priority, requester_id, **requester_name**, assignee_id, **assignee_name**, organization_id, tags, created_at, updated_at  
**Note:** User names are resolved with extra API calls per unique ID.

---

### `get_ticket`
Get ticket details. Two modes controlled by `include_comments`:

| Parameter | Type | Default | Effect |
|---|---|---|---|
| `ticket_id` | integer | — (required) | Zendesk ticket ID |
| `include_comments` | boolean | `true` | When `true`: full enrichment path. When `false`: single-call fast path. |

**Mode 1 — Full enrichment (`include_comments=true`, default):**
- 3+ API calls: ticket + comments + requester name + assignee name
- Returns: full ticket object including `requester_name`, `assignee_name`, and a `comments` array (up to 50 comments fetched inline)

**Mode 2 — Single-call fast path (`include_comments=false`):**
- **Exactly 1 API call** (the ticket GET)
- Returns: ticket object **without** `requester_name`, `assignee_name`, or `comments` keys
- `requester_id` and `assignee_id` are still returned, so callers can resolve names themselves (e.g. via `get_user` or batched lookup) when needed.

**Use the fast path when** you only need ticket metadata (status, priority, tags, custom fields) and would otherwise pay for name lookups and a comments fetch you'll never read.

---

### `get_ticket_audits`
Get the change history of a ticket.  
**Required:** `ticket_id` | **Optional:** `limit_events` (default 25)  
**Returns:** `{ id, events: [{ type, from, to, at } | { type:"comment", public, body[:200], at }] }`

---

### `get_ticket_comments`
Get all comments and internal notes.  
**Required:** `ticket_id` | **Optional:** `limit` (default 25)  
**Returns:** `{ ticket_id, comments: [{ id, body, public, author_id, created_at, attachments? }], returned }`

---

### `edit_ticket`
Update one or more ticket fields in a single PUT call.  
**Required:** `ticket_id`, `fields` (object)  
**Allowed fields:** `status`, `priority`, `subject`, `assignee_id`, `tags`, `custom_fields`  
**Blocked fields:** `requester_id`, `submitter_id` (validation error returned, not sent to API)  
**Valid statuses:** open, pending, hold, solved, closed  
**Valid priorities:** low, normal, high, urgent  
**Returns:** Updated ticket summary.

---

### `solve_ticket`
Shorthand to set status → solved.  
**Required:** `ticket_id`  
**Returns:** `{ ticket: { id, subject, status: "solved", updated_at } }`

---

## Ticket Metrics (1 tool)

### `get_ticket_metrics`
Performance metrics for a single ticket.  
**Required:** `ticket_id`  
**Returns:**
```json
{
  "metrics": {
    "replies": 2,
    "reopens": 0,
    "first_reply_time_minutes": { "calendar": 15, "business": 10 },
    "full_resolution_time_minutes": { "calendar": 120, "business": 80 },
    "agent_wait_time_minutes": ...,
    "on_hold_time_minutes": ...,
    "solved_at": "2026-05-20T..."
  }
}
```

---

## Users (2 tools)

### `get_user`
Get a user by ID.  
**Required:** `user_id`  
**Returns:** `{ user: { id, name, email, role, organization_id, active, tags, created_at } }`

---

### `search_users`
Search by name or email.  
**Required:** `query` | **Optional:** `page`, `per_page`  
**Returns:** `{ page, per_page, total, returned, users: [...] }`

---

## Organizations (2 tools)

### `get_organization`
Get an organization by ID.  
**Required:** `org_id`  
**Returns:** `{ organization: { id, name, details, notes, tags, created_at } }`

---

### `search_organizations`
Search organizations by name (uses `/organizations/search` endpoint with `name=` param, not Zendesk Search).  
**Required:** `query` | **Optional:** `page`, `per_page`

---

## Views (3 tools)

> **Note:** There is no "list all views" tool. You need a view ID. Obtain IDs from the Zendesk Admin UI or via the Zendesk API directly.

### `get_view`
Get view metadata including conditions and execution settings.  
**Required:** `view_id`

### `count_view`
Get the current ticket count for a view.  
**Required:** `view_id` → `{ view_id, count: N }`

### `list_view_tickets`
List tickets in a view (paginated).  
**Required:** `view_id` | **Optional:** `page`, `per_page`

---

## Ticket Fields (1 tool)

### `list_ticket_fields`
List all system and custom fields with types, descriptions, and dropdown options.  
**No inputs required.**  
**Returns:** `{ ticket_fields: [...], count: N }`  
Useful for knowing custom field IDs before calling `edit_ticket`.

---

## Triggers (3 tools)

### `list_triggers`
List all triggers (or active only).  
**Optional:** `active_only` (bool, default false), `page`, `per_page` (default 100)  
**Returns:** Full trigger objects including conditions and actions.

### `get_trigger`
Get a single trigger by ID.  
**Required:** `trigger_id`

### `search_triggers`
Search triggers by title.  
**Required:** `query` | **Optional:** `active` (bool filter)

---

## Automations (3 tools)

Time-based business rules (fire when ticket conditions are met after a time delay).

### `list_automations`
List all automations.  
**Optional:** `active_only`, `page`, `per_page` (default 100)

### `get_automation`
Get a single automation by ID.  
**Required:** `automation_id`

### `search_automations`
Search automations by title.  
**Required:** `query` | **Optional:** `active` (bool)

---

## Macros (3 tools)

Canned actions agents apply to tickets in one click.

### `list_macros`
List all macros.  
**Optional:** `active_only`, `page`, `per_page` (default 100)

### `get_macro`
Get a single macro by ID including its actions.  
**Required:** `macro_id`

### `search_macros`
Search macros by title.  
**Required:** `query` | **Optional:** `active` (bool)

---

## Attachments (2 tools)

### `get_ticket_attachments`
Return ALL attachments across every comment on a ticket, paginating through all comment pages.  
**Required:** `ticket_id`  
**Returns:** `{ ticket_id, attachments: [{ id, file_name, content_type, size, url, inline, comment_id, comment_created_at }], count }`

### `get_attachment`
Get metadata for one attachment by its ID.  
**Required:** `attachment_id`  
**Returns:** Attachment object with `thumbnails` array.

---

## Satisfaction Ratings / CSAT (2 tools)

### `list_satisfaction_ratings`
List CSAT ratings with optional filters.  
**Optional:** `score` (good/bad/offered/unoffered/received/good_with_comment/bad_without_comment), `start_time`/`end_time` (Unix epoch), `page`, `per_page`

### `count_satisfaction_ratings`
Get the approximate total count of all CSAT ratings (fast cached endpoint, no filters).  
**No inputs required.**
