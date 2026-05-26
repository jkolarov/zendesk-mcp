# Zendesk MCP Server

An unofficial [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for Zendesk. Gives AI assistants (Claude Desktop, KIRO, Cursor, etc.) tools to read and manage Zendesk tickets, users, organizations, views, triggers, automations, and attachments.

## Features

- **30 tools** covering tickets, users, organizations, views, ticket fields, triggers, automations, macros, attachments, and CSAT ratings
- Read and write operations (search, get, edit, solve)
- **Three authentication methods**: OAuth Client Credentials (recommended), API token, or static OAuth access token
- Automatic user name resolution on ticket results
- Rate limit handling with automatic retries
- Cross-platform: works on macOS, Linux, and Windows

## Prerequisites

- Python 3.10+
- A Zendesk account with API access

## Installation

### Option A: pipx (recommended)

[pipx](https://pipx.pypa.io/) installs the package in an isolated environment and puts `zendesk-mcp` on your PATH automatically — no venv management needed.

```bash
pipx install git+https://github.com/jkolarov/zendesk-mcp.git
```

If you don't have pipx: `pip install pipx` or `brew install pipx` (macOS).

### Option B: pip

```bash
# Clone the repository
git clone https://github.com/jkolarov/zendesk-mcp.git
cd zendesk-mcp

# Create and activate a virtual environment (avoids system Python conflicts)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install (creates the 'zendesk-mcp' command)
pip install .
```

Or install directly from GitHub into an active virtualenv:

```bash
pip install git+https://github.com/jkolarov/zendesk-mcp.git
```

> **PATH note:** After installation, `zendesk-mcp` must be on your PATH for MCP clients to find it. With pipx this is automatic. With pip into a venv, activate the venv first — or use the full path to the executable in your MCP client config (e.g. `/home/user/.venv/bin/zendesk-mcp` or `C:\Users\user\.venv\Scripts\zendesk-mcp.exe`).

## Authentication

The server supports three authentication modes. Set exactly one.

| Mode | Env vars | Notes |
|---|---|---|
| **OAuth — Client Credentials** ⭐ recommended | `ZD_SUBDOMAIN` + `ZD_OAUTH_CLIENT_ID` + `ZD_OAUTH_CLIENT_SECRET` | Credentials never expire. Token fetched automatically at startup. |
| **API Token** | `ZD_SUBDOMAIN` + `ZD_EMAIL` + `ZD_API_TOKEN` | Token generated in Admin Center → Zendesk API. |
| **OAuth — Static Token** | `ZD_SUBDOMAIN` + `ZD_OAUTH_TOKEN` | Expires (up to 30 days). Manual rotation required. |

**Priority:** If multiple sets of credentials are present, the order is: Static Token → Client Credentials → API Token.

> ⚠️ `ZD_OAUTH_CLIENT_SECRET` is the OAuth *client secret*, not an access token.
> Do not paste it as `ZD_OAUTH_TOKEN` — they are different values used differently.
> The server automatically exchanges the client secret for a token on every startup.

### Option 1: OAuth — Client Credentials (recommended)

Create an OAuth client in Admin Center > Apps & Integrations > OAuth Clients.

```bash
ZD_SUBDOMAIN=yourcompany
ZD_OAUTH_CLIENT_ID=your_client_id_here
ZD_OAUTH_CLIENT_SECRET=your_client_secret_here
# ZD_OAUTH_SCOPE=read write   # optional, this is the default
```

Client ID and Client Secret **never expire** — configure once and forget.

### Option 2: API Token

Go to Admin Center > Apps and integrations > Zendesk API > Add API Token.

```bash
ZD_SUBDOMAIN=yourcompany
ZD_EMAIL=you@yourcompany.com
ZD_API_TOKEN=your_api_token_here
```

### Option 3: OAuth — Static Access Token

Obtain a token via the OAuth authorization flow. Tokens expire (up to 30 days) and must be rotated manually.

```bash
ZD_SUBDOMAIN=yourcompany
ZD_OAUTH_TOKEN=your_oauth_token_here
```

For more details, see [Zendesk OAuth documentation](https://developer.zendesk.com/documentation/api-basics/authentication/creating-and-using-oauth-tokens-with-the-api/).

## MCP Client Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

**Using OAuth Client Credentials (recommended):**
```json
{
  "mcpServers": {
    "zendesk": {
      "command": "zendesk-mcp",
      "env": {
        "ZD_SUBDOMAIN": "yourcompany",
        "ZD_OAUTH_CLIENT_ID": "your_client_id_here",
        "ZD_OAUTH_CLIENT_SECRET": "your_client_secret_here"
      }
    }
  }
}
```

**Using API token:**
```json
{
  "mcpServers": {
    "zendesk": {
      "command": "zendesk-mcp",
      "env": {
        "ZD_SUBDOMAIN": "yourcompany",
        "ZD_EMAIL": "you@yourcompany.com",
        "ZD_API_TOKEN": "your_api_token_here"
      }
    }
  }
}
```

### Amazon Q Developer CLI / Kiro

Edit `~/.config/amazonq/mcp.json` (Linux/macOS) or `%USERPROFILE%\.config\amazonq\mcp.json` (Windows):

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "zendesk-mcp",
      "env": {
        "ZD_SUBDOMAIN": "yourcompany",
        "ZD_OAUTH_CLIENT_ID": "your_client_id_here",
        "ZD_OAUTH_CLIENT_SECRET": "your_client_secret_here"
      }
    }
  }
}
```

Or with API token: use `"ZD_EMAIL"` and `"ZD_API_TOKEN"` instead of the OAuth vars.

### Cursor

Add to `.cursor/mcp.json` in your project or global config:

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "zendesk-mcp",
      "env": {
        "ZD_SUBDOMAIN": "yourcompany",
        "ZD_OAUTH_CLIENT_ID": "your_client_id_here",
        "ZD_OAUTH_CLIENT_SECRET": "your_client_secret_here"
      }
    }
  }
}
```

Or with API token: use `"ZD_EMAIL"` and `"ZD_API_TOKEN"` instead of the OAuth vars.

## Available Tools (30)

### Tickets (7)

| Tool | Description |
|------|-------------|
| `count_tickets` | Count tickets matching a Zendesk search query |
| `search_tickets` | Search tickets with full details and resolved user names |
| `get_ticket` | Get a single ticket with all comments and custom fields |
| `get_ticket_audits` | Get ticket audit/change history |
| `get_ticket_comments` | Get ticket comments and internal notes |
| `edit_ticket` | Update ticket fields (status, priority, tags, assignee, custom fields) |
| `solve_ticket` | Shorthand to set ticket status to solved |

### Ticket Metrics (1)

| Tool | Description |
|------|-------------|
| `get_ticket_metrics` | Get reply times, resolution time, reopens, and SLA data for a ticket |

### Users (2)

| Tool | Description |
|------|-------------|
| `get_user` | Get a user by ID |
| `search_users` | Search users by name or email |

### Organizations (2)

| Tool | Description |
|------|-------------|
| `get_organization` | Get an organization by ID |
| `search_organizations` | Search organizations by name |

### Views (4)

| Tool | Description |
|------|-------------|
| `list_views` | List views so agents can discover view IDs |
| `get_view` | Get view details including conditions and execution settings |
| `count_view` | Get the current ticket count for a view |
| `list_view_tickets` | List tickets in a view (paginated) |

### Ticket Fields (1)

| Tool | Description |
|------|-------------|
| `list_ticket_fields` | List all system and custom fields with types, descriptions, and options |

### Triggers (3)

| Tool | Description |
|------|-------------|
| `list_triggers` | List all triggers (or active only) |
| `get_trigger` | Get a single trigger by ID |
| `search_triggers` | Search triggers by title |

### Automations (3)

| Tool | Description |
|------|-------------|
| `list_automations` | List all automations (time-based business rules) |
| `get_automation` | Get a single automation by ID |
| `search_automations` | Search automations by title |

### Macros (3)

| Tool | Description |
|------|-------------|
| `list_macros` | List all macros (canned agent actions) |
| `get_macro` | Get a single macro by ID including its actions |
| `search_macros` | Search macros by title |

### Attachments (2)

| Tool | Description |
|------|-------------|
| `get_ticket_attachments` | List all attachments across every comment on a ticket |
| `get_attachment` | Get metadata and download URL for a single attachment |

### Satisfaction Ratings / CSAT (2)

| Tool | Description |
|------|-------------|
| `list_satisfaction_ratings` | List CSAT ratings with optional score/date filters |
| `count_satisfaction_ratings` | Get the total count of all CSAT ratings (fast cached endpoint) |

---

## What's new

Six tools added since v0.1:
- `get_ticket_metrics` — reply times, resolution time, reopens, SLA data
- `list_macros` / `get_macro` / `search_macros` — canned agent actions
- `list_satisfaction_ratings` / `count_satisfaction_ratings` — CSAT data

## Building Your Own Tools

The generic tools above are a solid starting point, but the **best use of this MCP is to add tools that are tailored to your company's specific Zendesk setup**. Because a tool has a name, a description, and typed inputs, an AI assistant can invoke it with exactly the right intent — no prompt engineering required at call time.

### What company-specific tools look like

Instead of asking an AI to construct a query from scratch, you encode your team's domain knowledge directly into a tool:

```python
# A generic approach — the AI has to know your conventions
search_tickets('type:ticket tags:escalation assignee:oncall-team status:open')

# A company-specific tool — the AI just calls it by name
get_open_escalations()
```

The tool internally knows which tag your team uses for escalations (`vip_escalation`), which group is on-call, and which statuses matter. The AI only needs to decide *when* to call it.

### Examples of high-value custom tools

| Tool name | What it encodes |
|-----------|-----------------|
| `get_open_escalations` | Your escalation tag(s), priority thresholds, and responsible team |
| `get_tickets_pending_customer` | The exact status + tag combination your team uses for "waiting on customer" |
| `get_sla_breached_tickets` | Your SLA view IDs or the custom field that tracks breach status |
| `get_tickets_for_account` | Maps a company name to your `organization_id` automatically |
| `get_oncall_queue` | Hardcodes the right group/assignee IDs for the current rotation |
| `summarise_vip_account` | Fetches org + open tickets + recent comments for a named account in one shot |

### How to add a custom tool

1. Add a function to `src/zendesk_mcp/tools.py` that calls the existing primitives (`client.get`, `search_tickets`, etc.) with your company's hardcoded values.
2. Register it in `server.py` — add an entry to `TOOLS` (with a clear `description` the AI will use to decide when to call it) and one line in `TOOL_DISPATCH`.
3. If it needs a new Zendesk endpoint, add the path to `ALLOWED_PATHS` in `client.py`.

The payoff: once a tool exists, the AI can use it precisely and reliably without you having to explain your internal conventions every time.

## Security

- Only whitelisted Zendesk API paths are accessible (no arbitrary API calls)
- API tokens are never logged or exposed in responses
- All requests use HTTPS
- OAuth tokens support scoped access (e.g., read-only)

## License

MIT
