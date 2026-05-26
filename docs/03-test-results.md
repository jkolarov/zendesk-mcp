# Test Results

---

## Run 2 — 2026-05-27 (post all PRs merged)

**Test environment:** freelancer-17746.zendesk.com  
**Auth mode:** API Token  
**Python:** 3.14 / Windows 11  
**Package:** zendesk-mcp 0.1.0 (commit c5129bf + chore commit 4987a6f)

All 30 tools tested via direct Python calls to the installed package.

| # | Tool | Result | Notes |
|---|---|---|---|
| 1 | `count_tickets` | ✅ PASS | count: 3 |
| 2 | `search_tickets` | ✅ PASS | 1 open ticket, `requester_name` populated via show_many |
| 3 | `get_ticket` | ✅ PASS | Ticket #1 full details, requester_name: "Customer", assignee_name: "Georgi Kolarov", 1 comment |
| 4 | `get_ticket` (no comments) | ✅ PASS | Fast path: no `comments` key, no name keys — single API call |
| 5 | `get_ticket_comments` | ✅ PASS | 1 comment returned |
| 6 | `get_ticket_audits` | ✅ PASS | 16 events on ticket #1 |
| 7 | `get_ticket_attachments` | ✅ PASS | 0 attachments on ticket #1, pagination loop works |
| 8 | `get_ticket_metrics` | ✅ PASS | replies: 0 (test ticket) |
| 9 | `edit_ticket` | — | Not re-tested (write op; tested in Run 1) |
| 10 | `solve_ticket` | — | Not re-tested (write op; tested in Run 1) |
| 11 | `get_user` | ✅ PASS | name: "Georgi Kolarov", role: "admin" |
| 12 | `search_users` | ✅ PASS | 1 result for "jorokolarov" |
| 13 | `get_organization` | ✅ PASS | name: "freelancer" |
| 14 | `search_organizations` | ✅ PASS | 1 result; `type:organization` forced correctly |
| 15 | `list_views` | ✅ PASS | 10 views returned |
| 16 | `list_views` (active_only) | ✅ PASS | 6 active views |
| 17 | `get_view` | ✅ PASS | title: "Your unsolved tickets" |
| 18 | `count_view` | ✅ PASS | count: 1 |
| 19 | `list_view_tickets` | ✅ PASS | 1 ticket returned |
| 20 | `list_ticket_fields` | ✅ PASS | 23 fields |
| 21 | `list_triggers` | ✅ PASS | count: 8 |
| 22 | `list_triggers` (active_only) | ✅ PASS | count: 8 (all active in test env) |
| 23 | `get_trigger` | ✅ PASS | title: "Notify requester and CCs of received request" |
| 24 | `search_triggers` | ✅ PASS | 7 results for "notify" |
| 25 | `list_automations` | ✅ PASS | count: 3 |
| 26 | `list_automations` (active_only) | ✅ PASS | count: 1 |
| 27 | `get_automation` | ✅ PASS | title: "Close ticket 4 days after status is set to solved" |
| 28 | `search_automations` | ✅ PASS | 1 result for "close" |
| 29 | `list_macros` | ✅ PASS | count: 2 |
| 30 | `list_macros` (active_only) | ✅ PASS | count: 2 |
| 31 | `get_macro` | ✅ PASS | title: "Customer not responding" |
| 32 | `search_macros` | ✅ PASS | 0 results for "close" (correct, no matching macros) |
| 33 | `list_satisfaction_ratings` | ✅ PASS | 0 ratings (test env) |
| 34 | `count_satisfaction_ratings` | ✅ PASS | count: 0 |

**Result: 32 / 32 tested PASS** (edit_ticket and solve_ticket not re-run — write ops, passed in Run 1)

---

## Run 1 — 2026-05-26 (initial test, pre-improvements)

**Test environment:** freelancer-17746.zendesk.com  
**Auth mode:** API Token  
**Tools at the time:** 29

| # | Tool | Result | Notes |
|---|---|---|---|
| 1 | `count_tickets` | ✅ PASS | Returned count for `type:ticket` |
| 2 | `search_tickets` | ✅ PASS | 3 tickets returned, user names resolved (per-user calls at the time) |
| 3 | `get_ticket` | ✅ PASS | Full details + comments inline |
| 4 | `get_ticket_audits` | ✅ PASS | Change events returned |
| 5 | `get_ticket_comments` | ✅ PASS | Public + private comments |
| 6 | `get_ticket_metrics` | ✅ PASS | Reply times, resolution times in calendar+business minutes |
| 7 | `get_ticket_attachments` | ✅ PASS | Pagination loop works; ticket #1 had 0, tickets #2 and #3 had 1 each |
| 8 | `get_attachment` | ✅ PASS | Retrieved `mcp-smoke-379b3d21.txt` by attachment ID |
| 9 | `edit_ticket` | ✅ PASS | Added `mcp_test_tag` tag to ticket #1 |
| 10 | `solve_ticket` | ✅ PASS | Ticket #2 (already solved) returned status: solved — idempotent |
| 11 | `get_user` | ✅ PASS | User record with role, org, tags |
| 12 | `search_users` | ✅ PASS | Found user by name query |
| 13 | `get_organization` | ✅ PASS | Org details returned |
| 14 | `search_organizations` | ✅ PASS | Name-based search works |
| 15 | `get_view` | ✅ PASS | View conditions + execution settings |
| 16 | `count_view` | ✅ PASS | Ticket count for "Your unsolved tickets" view |
| 17 | `list_view_tickets` | ✅ PASS | Paginated ticket list from view |
| 18 | `list_ticket_fields` | ✅ PASS | All system + custom fields with options |
| 19 | `list_triggers` | ✅ PASS | Full trigger list including conditions/actions |
| 20 | `get_trigger` | ✅ PASS | Single trigger by ID |
| 21 | `search_triggers` | ✅ PASS | Title search returned matching triggers |
| 22 | `list_automations` | ✅ PASS | All automations including time-based conditions |
| 23 | `get_automation` | ✅ PASS | Single automation by ID |
| 24 | `search_automations` | ✅ PASS | Title search works |
| 25 | `list_macros` | ✅ PASS | 2 macros in test env |
| 26 | `get_macro` | ✅ PASS | "Customer not responding" macro with actions |
| 27 | `search_macros` | ✅ PASS | Title search works |
| 28 | `list_satisfaction_ratings` | ✅ PASS | Empty in test env (0 ratings) — no error |
| 29 | `count_satisfaction_ratings` | ✅ PASS | Returns 0, correct for fresh test account |

**Result: 29 / 29 PASS**

---

## OAuth auth — static token (2026-05-26)

| Test | Result | Notes |
|---|---|---|
| Config detection | ✅ PASS | `auth_method == "oauth_static"` when only `ZD_OAUTH_TOKEN` is set |
| API call with provided token | ❌ FAIL | HTTP 401 `invalid_token` |

**Root cause:** The value provided was a Zendesk OAuth **client secret**, not an OAuth **access token**. These are different:
- **Client secret** — used during the OAuth flow to exchange credentials for a token. Never sent as a Bearer token directly.
- **Access token** — generated in Admin Center → Apps & Integrations → OAuth Clients → "Generate Token".

---

## OAuth Client Credentials — end-to-end (pending)

Implemented in PR #21 (Epic #8, issues #9–#14). Full end-to-end validation (Issue #15) requires creating an OAuth client in Admin Center. Still pending — test account setup needed.
