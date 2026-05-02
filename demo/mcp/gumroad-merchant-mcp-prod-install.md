# Gumroad Merchant MCP Production Install

You are helping me connect my agent to Gumroad Merchant MCP.

This is the production-style install prompt for someone using a cloned GitHub
checkout or, later, a hosted Gumroad Merchant MCP URL. Do not look for Shane's
local repo and do not use `/Users/sc/Project Files/gumroad`.

## Server

Use this server name:

```text
gumroad_merchant
```

## Repo Routes

If the user downloaded or cloned this project, first find the project root. The
project root is the folder that contains:

```text
README.md
requirements.txt
MCPGuide.md
MCPConversationSample.md
AgentConversationSample.md
scripts/gumroad-merchant-mcp.sh
gumroad_merchant/mcp_server.py
demo/mcp/gumroad-merchant-agent-skill/SKILL.md
```

Use these repo-relative paths:

```text
<PROJECT_ROOT>/scripts/gumroad-merchant-mcp.sh
<PROJECT_ROOT>/gumroad_merchant/mcp_server.py
<PROJECT_ROOT>/requirements.txt
<PROJECT_ROOT>/MCPGuide.md
<PROJECT_ROOT>/MCPConversationSample.md
<PROJECT_ROOT>/AgentConversationSample.md
<PROJECT_ROOT>/demo/mcp/gumroad-merchant-agent-skill/SKILL.md
```

The local GitHub checkout runs as a stdio MCP server. It does not expose an HTTP
port. The MCP host starts the launcher script and talks to it over stdio.

## Your Job

1. Detect the MCP-capable host you are running inside: Codex, Claude, Cursor, or another local agent app.
2. Inspect the host's MCP config format before editing anything.
3. Preserve existing MCP servers.
4. Prefer the local cloned repo route if `<PROJECT_ROOT>/scripts/gumroad-merchant-mcp.sh` exists.
5. If the user provides a hosted Gumroad Merchant MCP URL, configure the hosted URL instead.
6. Reload or restart the MCP host if required.
7. Confirm the server is available by asking Gumroad Merchant for its help menu.

## Local GitHub Checkout Install

From the cloned repo:

```bash
cd "<PROJECT_ROOT>"
python3 -m pip install -r requirements.txt
test -x scripts/gumroad-merchant-mcp.sh
python3 scripts/run_mcp_smoke.py
```

If the launcher is not executable:

```bash
cd "<PROJECT_ROOT>"
chmod +x scripts/gumroad-merchant-mcp.sh
```

Configure the MCP host to run:

```text
<PROJECT_ROOT>/scripts/gumroad-merchant-mcp.sh
```

For TOML-style MCP hosts:

```toml
[mcp_servers.gumroad_merchant]
command = "<PROJECT_ROOT>/scripts/gumroad-merchant-mcp.sh"
```

For JSON-style MCP hosts:

```json
{
  "mcpServers": {
    "gumroad_merchant": {
      "command": "<PROJECT_ROOT>/scripts/gumroad-merchant-mcp.sh"
    }
  }
}
```

The repo-local server uses seeded local data. Do not add production Gumroad
credentials to this local demo.

## Hosted Production URL Install

If the user provides a hosted Gumroad Merchant MCP URL, use it instead of the
local stdio launcher:

```text
<GUMROAD_MERCHANT_MCP_URL>
```

If the user has not provided the URL yet and wants the hosted production server,
ask for the official Gumroad Merchant MCP URL. Do not invent credentials,
package names, or private endpoints.

If the host supports remote MCP servers, use this shape:

```json
{
  "mcpServers": {
    "gumroad_merchant": {
      "url": "<GUMROAD_MERCHANT_MCP_URL>"
    }
  }
}
```

## Future Auth Flow

When the production auth layer is available, use browser-based login instead of
static API keys:

- Start a Gumroad MCP login flow from the CLI or agent host.
- Open the Gumroad login and consent link in the user's web browser.
- Let the user choose the Gumroad account and the MCP permission profile.
- Store only short-lived scoped tokens through the host's secure credential store.
- Never paste Gumroad passwords, browser cookies, or long-lived admin keys into MCP config.

## Permission Model

The production UI should let the Gumroad user control access by activity:

- monthly sales: read
- customer and purchase lookup: read
- product catalog: read or write
- refunds: read, draft, or execute after confirmation
- disputes: read, draft, or submit after confirmation
- emails and receipts: draft or send after confirmation
- posts and announcements: draft or publish after confirmation
- product edits and pricing: draft or apply after confirmation
- subscriptions and payouts: read, draft, or execute with higher-risk confirmation

## First Prompt After Install

After reload, ask:

```text
Use Gumroad Merchant to show me what I can do.
```

The server should return available tools, permission scopes, auth state, next
actions, and any missing setup steps.
