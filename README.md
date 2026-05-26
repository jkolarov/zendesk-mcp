# Zendesk MCP Server

An unofficial [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for Zendesk. Gives AI assistants (Claude Desktop, KIRO, Cursor, etc.) tools to read and manage Zendesk tickets, users, organizations, views, triggers, automations, and attachments.

## Features

- **23 tools** covering tickets, users, organizations, views, ticket fields, triggers, automations, and attachments
- Read and write operations (search, get, edit, solve)
- **Two authentication methods**: API token (admin) or OAuth access token (scoped)
- Automatic user name resolution on ticket results
- Rate limit handling with automatic retries
- Cross-platform: works on macOS, Linux, and Windows

## Prerequisites

- Python 3.10+
- A Zendesk account with API access

## Installation

```bash
# Clone the repository
git clone https://github.com/jkolarov/zendesk-mcp.git
cd zendesk-mcp

# Install (creates the 'zendesk-mcp' command)
pip install .
```

Or install directly from GitHub:

```bash
pip install git+https://github.com/jkolarov/zendesk-mcp.git
```

## Authentication

The server supports two authentication methods. You only need one.

### Option 1: API Token (Admin)

Requires admin access. Go to Admin Center > Apps and integrations > Zendesk API > Add API Token.

```bash
ZD_SUBDOMAIN=yourcompany
ZD_EMAIL=you@yourcompany.com
ZD_API_TOKEN=your_api_token_here
```

### Option 2: OAuth Access Token (Recommended for agents)

More secure — uses scoped permissions and is easily revocable. Does not require admin access to *use* (but an admin must create the OAuth client and token initially).

**Setup steps:**

1. **Create an OAuth client** in Admin Center > Apps and integrations > APIs > Zendesk API > OAuth Clients > Add OAuth Client
2. **Create an access token** via the API (replace `12345` with your OAuth client's numeric ID from the clients list):
   ```bash
   curl https://yourcompany.zendesk.com/api/v2/oauth/tokens.json \
     -X POST \
     -u admin@yourcompany.com/token:ADMIN_API_TOKEN \
     -H "Content-Type: application/json" \
     -d '{
       "token": {
         "client_id": 12345,
         "scopes": ["read", "write"]
       }
     }'
   ```
3. Copy the `full_token` from the response.

```bash
ZD_SUBDOMAIN=yourcompany
ZD_OAUTH_TOKEN=your_oauth_token_here
```

> **Note:** If both `ZD_OAUTH_TOKEN` and `ZD_API_TOKEN` are set, OAuth takes precedence.

For more details, see [Zendesk OAuth documentation](https://developer.zendesk.com/documentation/api-basics/authentication/creating-and-using-oauth-tokens-with-the-api/).

## MCP Client Configuration

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

**Using OAuth token:**
```json
{
  "mcpServers": {
    "zendesk": {
      "command": "zendesk-mcp",
      "env": {
        "ZD_SUBDOMAIN": "yourcompany",
        "ZD_OAUTH_TOKEN": "your_oauth_token_here"
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
        "ZD_OAUTH_TOKEN": "your_oauth_token_here"
      }
    }
  }
}
```

Or with API token: use `"ZD_EMAIL"` and `"ZD_API_TOKEN"` instead of `"ZD_OAUTH_TOKEN"`.

### Cursor

Add to `.cursor/mcp.json` in your project or global config:

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "zendesk-mcp",
      "env": {
        "ZD_SUBDOMAIN": "yourcompany",
        "ZD_OAUTH_TOKEN": "your_oauth_token_here"
      }
    }
  }
}
```

Or with API token: use `"ZD_EMAIL"` and `"ZD_API_TOKEN"` instead of `"ZD_OAUTH_TOKEN"`.

> **Note:** If `zendesk-mcp` is not on your PATH, use the full path to the executable (e.g., `/home/user/.local/bin/zendesk-mcp` or `C:\Users\user\AppData\Local\Programs\Python\Python311\Scripts\zendesk-mcp.exe`).

## Available Tools

| Tool | Description |
|------|-------------|
| `count_tickets` | Count tickets matching a search query |
| `search_tickets` | Search tickets with full details |
| `get_ticket` | Get a single ticket with comments |
| `get_ticket_audits` | Get ticket audit/change history |
| `get_ticket_comments` | Get ticket comments and notes |
| `edit_ticket` | Update ticket fields |
| `solve_ticket` | Set ticket status to solved |
| `get_user` | Get user by ID |
| `search_users` | Search users by name/email |
| `get_organization` | Get organization by ID |
| `search_organizations` | Search organizations by name |
| `get_view` | Get view details |
| `count_view` | Get ticket count for a view |
| `list_view_tickets` | List tickets in a view |
| `list_ticket_fields` | List all ticket fields |
| `list_triggers` | List triggers (business rules) |
| `get_trigger` | Get trigger details |
| `search_triggers` | Search triggers by title |
| `list_automations` | List automations (time-based rules) |
| `get_automation` | Get automation details |
| `search_automations` | Search automations by title |
| `get_ticket_attachments` | List all attachments on a ticket |
| `get_attachment` | Get metadata and download URL for an attachment |

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
