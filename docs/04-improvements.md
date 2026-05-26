# Possible Improvements

## Completed (as of 2026-05-27)

| # | Issue | PR | Description |
|---|---|---|---|
| ✅ | #16 | #24 | `client.put()` 429-only retry with RFC 7231 `Retry-After` parsing (delta-seconds and HTTP-date) |
| ✅ | #17 | #23 | `list_views` tool + `/api/v2/views.json` and `/api/v2/views/active.json` added to whitelist |
| ✅ | #18 | #25 | `search_organizations` now uses Zendesk Search (`type:organization`), strips any caller-supplied `type:X` clauses |
| ✅ | #19 | #26 | Batched user name resolution via `show_many` — single call for all unique IDs, chunked at 100 per request, graceful per-chunk degradation |
| ✅ | #20 | #22 | `get_ticket(include_comments=False)` is a true single-call fast path — skips both name resolution and comments fetch |
| ✅ | #8–#14 | #21 | OAuth Client Credentials auth mode (`ZD_OAUTH_CLIENT_ID` + `ZD_OAUTH_CLIENT_SECRET`), token auto-refresh on 401 |

---

## Open — features / nice-to-haves

| Feature | Priority | Notes |
|---|---|---|
| `create_ticket` tool | High | Currently read-mostly; creation would unlock many more use cases |
| `add_comment` tool | High | Can't reply to tickets without this |
| OAuth Client Credentials end-to-end test | High | Issue #15 — requires OAuth client created in Admin Center |
| `list_groups` tool | Medium | Needed for `assignee_group_id` in `edit_ticket` |
| `apply_macro` tool | Medium | Macros are listed but can't be applied via MCP |
| `get_attachment` by URL | Low | Currently only by numeric ID |
| Ticket creation with attachment | Low | Requires multipart upload |
| Response caching | Low | Cache user names / ticket fields within a session |
| Async client | Low | Current `httpx.Client` is sync; `AsyncClient` would allow parallel batch lookups |

---

## Security suggestions

- **Env var validation at install time:** A `zendesk-mcp --check` command that validates credentials and prints the auth method in use.
- **Read-only mode flag:** An `--read-only` env var that disables all PUT operations, for monitoring/reporting setups.
- **Audit logging:** Optionally log all PUT operations (ticket ID, fields changed, timestamp) for compliance.
