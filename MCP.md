# Gumroad Merchant MCP

Gumroad Merchant MCP exposes the local seeded Gumroad Merchant agent tools through
Model Context Protocol over stdio. This is the no-web-UI path for the demo:
Codex, Claude, Cursor, or another MCP-capable agent can call the same analytics,
Refund Ops, Content Radar, Retention Saver, Admin Preview, Shortest QA, and help
search tools without opening the dashboard.

## Issue 4677 Alignment

The admin lane is aimed at
[antiwork/gumroad #4677](https://github.com/antiwork/gumroad/issues/4677):
exposing Gumroad admin functionality through an API and/or CLI so internal
operations do not require the web UI.

`get_admin_api_cli_recommendation` resolves the issue's open questions with the
pinned direction from the GitHub thread:

- prioritize exact user/purchase lookup, refund/compliance review packets, then
  gated fee/risk writes
- use short-lived scoped admin CLI tokens from existing admin identity, not
  static API keys or browser cookies
- create a separate `/internal/admin` API contract rather than extending the
  public v2 API
- expose commands under `gumroad admin` in the existing CLI
- use the seeded demo as review-only contract proof, then graduate production
  operations into scoped read-write tools with confirmation, audit logs, and
  role-based permissions

## Run Locally

Install dependencies:

```bash
cd "<PROJECT_ROOT>"
python3 -m pip install -r requirements.txt
```

MCP requires Python 3.10 or newer. If your agent environment has a managed
Python runtime, install the requirements there from the project root.

```bash
cd "<PROJECT_ROOT>"
python3 -m pip install -r requirements.txt
```

To force a specific interpreter:

```bash
GUMROAD_MERCHANT_PYTHON=/path/to/python3 scripts/gumroad-merchant-mcp.sh
```

Run the MCP server directly:

```bash
python3 -m gumroad_merchant.mcp_server
```

The server uses stdio, so it waits for MCP JSON-RPC messages. Do not expect it
to print an HTTP URL.

For a direct launcher:

```bash
scripts/gumroad-merchant-mcp.sh
```

## Drag-and-Drop Agent Install

The demo includes an agent handoff folder:

```text
demo/mcp/
|-- gumroad-merchant-mcp-agent-install.md
`-- gumroad-merchant-mcp-prod-install.md
```

Open `demo/mcp/` in Finder and drag
`gumroad-merchant-mcp-agent-install.md` into a local agent chat window for this
machine's personal seeded setup. Use `gumroad-merchant-mcp-prod-install.md` for
the generic production handoff: it points an agent at a hosted MCP server URL and
describes the future browser-based Gumroad auth flow.

This is intentionally just an installer prompt. MCP does not require a separate
skill file: the host config registers the server, the server exposes tool
metadata and input schemas, and `get_gumroad_merchant_help_menu` provides the
operating menu after install.

## Host Config

Use the launcher inside the current project checkout. Replace
`<PROJECT_ROOT>` with the absolute path to this repo on your machine.

For TOML-style MCP hosts:

```toml
[mcp_servers.gumroad_merchant]
command = "<PROJECT_ROOT>/scripts/gumroad-merchant-mcp.sh"
```

Do not add production Gumroad credentials for this seeded v1. The wrapper sets:

```bash
GUMROAD_MERCHANT_MODE=seeded
```

## Demo Prompts

After the server is configured in Codex, try:

```text
Use Gumroad Merchant to show me what I can do.
```

```text
List the Gumroad Merchant MCP tools.
```

```text
Use Gumroad Merchant to build a chargeback dispute packet.
```

```text
Use Gumroad Merchant to build a marketing plan for the highest-opportunity product.
```

```text
Use Gumroad Merchant to preview the admin action for the highest-risk refund case.
```

```text
Use Gumroad Merchant to answer Gumroad issue #4677's admin API/CLI open questions.
```

```text
Use Gumroad Merchant to generate natural-language QA tests for Refund Ops and Content Radar.
```

## Tool Surface

The current MCP server exposes read-only tools plus explicit local test-write tools for:

- Help: `get_gumroad_merchant_help_menu` returns terminal-friendly guidance,
  starter prompts, tool names, common parameters, and safety boundaries.
- Core analytics: product metrics, traffic sources, detected signals, dashboard
  summary, strategy plans, and signal action reviews.
- Refund Ops: summary, case queue, case details, buyer reply drafts, chargeback
  dispute evidence packets, and prevention actions.
- Content Radar: opportunity summary, seeded trend angles, marketing plans,
  campaign drafts, tracked-campaign staging, tracked-campaign creation, and
  local tracked-campaign listing.
- Agent actions/artifacts: pending/applied action listing, explicit pending
  action apply, downloadable roadmap generation, and repo-local architecture
  diagram generation.
- Retention Saver: membership churn summary, cancellation risks, pause-offer
  plans, and modeled revenue-saved estimates.
- Admin Preview: simulated `gumroad-admin` templates, command previews, and full
  action previews, plus the Gumroad issue `#4677` direction for turning admin
  work into scoped API/CLI/MCP contracts.
- Shortest QA: suite metadata and deterministic natural-language QA journeys.
- Help/search: seeded product search and official Gumroad help-doc search.

The production MCP path should add scoped read-write merchant tools for monthly
sales, product catalog updates, refunds, disputes, buyer emails, posts, product
edits, pricing changes, subscription changes, payout operations, and
account-impacting admin workflows. The point is not to make MCP permanently read-only. The point is
to make the agent operate the business through explicit tools instead of loose
prompts and dashboard clicks.

Every tool returns the same top-level envelope:

```json
{
  "ok": true,
  "tool": "tool_name",
  "data_source": "seeded_demo",
  "review_only": true,
  "will_execute": false,
  "mode": "seeded",
  "result": {}
}
```

List-style tools return `result.items`.

Expected failures return:

```json
{
  "ok": false,
  "tool": "tool_name",
  "data_source": "seeded_demo",
  "review_only": true,
  "will_execute": false,
  "mode": "seeded",
  "error": {
    "message": "What failed",
    "next_step": "How to correct the call"
  },
  "result": {}
}
```

## Safety Boundary

V1 is local seeded stdio only. It does not call Gumroad production services and
does not read production creator data.

For the seeded demo, production-impacting actions return previews,
preflight checks, blocked reasons, and audit-note copy. They should return
`review_only: true` and `will_execute: false` when they would affect a real
Gumroad account.

For production, write tools should be classified by risk instead of blocked by
default:

- safe reads can run directly and return concise business context
- write tools should support `dry_run`, `confirm`, and `apply` modes
- real writes require scoped merchant/admin tokens, role checks, preflight
  validation, idempotency keys, and audit logs
- high-risk writes, including refunds, payout changes, subscription access,
  pricing changes, mass email, and product edits, require explicit confirmation
  with the exact object and effect shown first

## Smoke Test

Run:

```bash
python3 scripts/run_mcp_smoke.py
```

The smoke test starts the MCP server over stdio, lists available tools, and calls
representative workflows for Refund Ops, dispute evidence, Content Radar,
Retention Saver, Admin Preview, issue `#4677` open-question resolution, and
Shortest QA. It also verifies the MCP help menu is available. Use
`python3 scripts/run_agent_action_smoke.py` for the local write/action-artifact
regression path.
