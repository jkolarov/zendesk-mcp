# Zendesk MCP Server

An unofficial [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for Zendesk. Gives AI assistants (Claude Desktop, Amazon Q Developer, Cursor, etc.) tools to read and manage Zendesk tickets, users, organizations, views, and triggers.

## Features

- **18 tools** covering tickets, users, organizations, views, ticket fields, and triggers
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
2. **Create an access token** via the API:
   ```bash
   curl https://yourcompany.zendesk.com/api/v2/oauth/tokens.json \
     -X POST \
     -u admin@yourcompany.com/token:ADMIN_API_TOKEN \
     -H "Content-Type: application/json" \
     -d '{
       "token": {
         "client_id": YOUR_CLIENT_ID,
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

## Security

- Only whitelisted Zendesk API paths are accessible (no arbitrary API calls)
- API tokens are never logged or exposed in responses
- All requests use HTTPS
- OAuth tokens support scoped access (e.g., read-only)

## License

MIT
