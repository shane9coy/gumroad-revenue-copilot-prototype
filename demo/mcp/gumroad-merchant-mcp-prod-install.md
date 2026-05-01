# Gumroad Merchant MCP Production Install

You are helping me connect my agent to Gumroad Merchant MCP.

This is the production-style install path. Do not look for Shane's local repo and do not use `/Users/sc/Project Files/gumroad`. Configure the MCP host to point at the hosted Gumroad Merchant MCP server.

## Server

Use this server name:

```text
gumroad_merchant
```

Use the Gumroad Merchant MCP URL I provide:

```text
<GUMROAD_MERCHANT_MCP_URL>
```

If I have not provided the URL yet, ask me for the official Gumroad Merchant MCP URL. Do not invent credentials, package names, or private endpoints.

## Your Job

1. Detect the MCP-capable host you are running inside: Codex, Claude, Cursor, or another local agent app.
2. Inspect the host's MCP config format before editing anything.
3. Preserve existing MCP servers.
4. Add a `gumroad_merchant` server entry that points to the hosted MCP server URL.
5. Reload or restart the MCP host if required.
6. Confirm the server is available by asking Gumroad Merchant for its help menu.

## Future Auth Flow

When the production auth layer is available, use browser-based login instead of static API keys:

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

## Config Shape

If the host supports remote MCP servers, use the hosted URL directly:

```json
{
  "mcpServers": {
    "gumroad_merchant": {
      "url": "<GUMROAD_MERCHANT_MCP_URL>"
    }
  }
}
```

If the host only supports local stdio servers, ask for the official Gumroad CLI bridge command once it exists. Do not make up a package name.

## First Prompt After Install

After reload, ask:

```text
Use Gumroad Merchant to show me what I can do.
```

The server should return available tools, permission scopes, auth state, safe next actions, and any missing setup steps.
