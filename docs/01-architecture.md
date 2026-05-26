# Architecture

## File structure

```
src/zendesk_mcp/
├── config.py      Settings (pydantic-settings, reads .env or env vars)
├── client.py      ZendeskClient — HTTP, auth, path whitelist, retry
├── tools.py       30 tool functions (pure Python, no async)
└── server.py      MCP server registration + dispatcher
pyproject.toml     Dependencies, entry point: zendesk-mcp → server:main
```

## Startup flow

```
1. pydantic-settings loads env vars → Settings()
2. Settings.validate_auth() runs at import → fails fast if misconfigured
3. ZendeskClient.__init__() builds httpx.Client with the correct auth header
4. MCP server registers 30 Tool descriptors
5. Requests arrive as JSON-RPC → TOOL_DISPATCH dict → tool function → JSON response
```

## Authentication

The server supports three mutually-exclusive modes, selected automatically by `Settings.auth_method`:

| Priority | Mode | Env vars required | How it works |
|---|---|---|---|
| 1 | **OAuth — Static Token** | `ZD_SUBDOMAIN` + `ZD_OAUTH_TOKEN` | `Authorization: Bearer <token>` (token pre-supplied) |
| 2 | **OAuth — Client Credentials** | `ZD_SUBDOMAIN` + `ZD_OAUTH_CLIENT_ID` + `ZD_OAUTH_CLIENT_SECRET` | `POST /oauth/tokens` at startup → `Authorization: Bearer <token>` |
| 3 | **API Token** | `ZD_SUBDOMAIN` + `ZD_EMAIL` + `ZD_API_TOKEN` | HTTP Basic: `email/token : api_token` |

**Priority:** Static Token wins over Client Credentials which wins over API Token. If partial credentials are present (e.g. `ZD_OAUTH_CLIENT_ID` without `ZD_OAUTH_CLIENT_SECRET`), startup fails immediately.

**Token fetch (Client Credentials):** `ZendeskClient._fetch_client_credentials_token()` is called once inside `__init__()`. It uses a bare `httpx.post()` (not `self.client`, which doesn't exist yet) and posts `application/x-www-form-urlencoded` to `/oauth/tokens`. The resulting access token is stored only in the `Authorization` header of `self.client` — never written to disk.

**Token refresh (Client Credentials):** If a `get()` or `put()` call receives a 401, the client automatically re-mints a fresh token via `_refresh_client_credentials_token()` and retries once. This handles token expiry in long-running MCP processes.

**Fail-fast:** the `@model_validator(mode="after")` on `Settings` calls `self.auth_method` at import time, so misconfiguration causes an immediate startup error rather than a silent failure on the first tool call.

> ⚠️ **Important:** `ZD_OAUTH_TOKEN` must be a Zendesk **access token** (obtained via the OAuth authorization flow or generated in Admin Center → Apps & Integrations → OAuth Clients → "Generate Token"). It is **not** the OAuth client secret.

## Security: API path whitelist

`client.py` maintains an explicit `ALLOWED_PATHS` set. Every request is validated against it before being sent to Zendesk. Paths with numeric IDs use regex (`{id}` → `\d+`). Any unlisted path returns a `ZendeskError(403)` — so even if a tool bug tried to call an arbitrary endpoint, it would be blocked.

**Current whitelist covers:** search, tickets, comments, audits, metrics, users (including `show_many`), organizations, views (list + active + by ID), ticket_fields, triggers, automations, attachments, macros, satisfaction_ratings.

## Retry & rate limiting

`client.get()` uses `tenacity` with:
- 3 attempts max
- Exponential backoff: 2–10 s
- Only retries on `httpx.HTTPStatusError`
- 429 responses → `ZendeskError(429)` with `Retry-After` header value surfaced as hint

`client.put()` uses a manual retry loop (3 attempts) that:
- **Only retries on 429** (write operations must not be silently retried on other errors)
- Respects the `Retry-After` header — handles both delta-seconds and HTTP-date formats (RFC 7231 §7.1.3)
- Caps wait time at 90 s per attempt to avoid indefinite blocking
- On 401 with `oauth_client_credentials` mode, re-mints the token and retries once

## User name resolution

User IDs in ticket responses are resolved to human-readable names via `_resolve_user_names()`:
- Collects all unique requester/assignee IDs from the response
- De-duplicates, filters out falsy values (None, 0)
- Batches up to 100 IDs per request to `/api/v2/users/show_many.json`
- Chunks automatically if more than 100 unique IDs (e.g. 250 IDs → 3 calls)
- Per-chunk error handling: if one chunk fails, others still return their names (graceful degradation)

`get_ticket(include_comments=False)` skips name resolution entirely — single API call fast path.

## Data model / response shapes

All tools return a `Dict[str, Any]` with either:
- A **success shape**: named key matching the resource (`ticket`, `tickets`, `user`, etc.)
- An **error shape**: `{"error": {"type": str, "message": str, "hint": str}}`

## Pagination limits

Controlled via `Settings`:
- `TOOLS_MAX_PER_PAGE` (default 100) — cap on per_page parameter
- `TOOLS_MAX_PAGES` (default 100) — search_tickets page guard

These can be overridden via env vars without code changes.
