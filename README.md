# Gumroad Merchant

Gumroad Merchant is a local-first prototype for a creator-facing merchant agent.
The core idea is that Gumroad should not just show creators what happened in
their business. It should help them understand the signal, see the evidence, and
take the next action.

Most AI creator tools either drop a dashboard on you or hand you a blank chat
box. This project tests the opposite shape: a chat-first interface with clear
workflow cards, plus an MCP server so the same Gumroad Merchant tools can run
inside a local agent like Codex, Claude, Cursor, or another MCP-capable app.

## Start Here

- [SUBMISSION_SUMMARY.md](SUBMISSION_SUMMARY.md) explains the product thinking
  and submission story.
- [MCPGuide.md](MCPGuide.md) shows how to run the Gumroad Merchant MCP server.
- [MCPConversationSample.md](MCPConversationSample.md) is a real five-pass MCP
  transcript from the stdio server.
- [AgentConversationSample.md](AgentConversationSample.md) is a real agent smoke
  transcript using the seeded local data.
- [AGENT-GUMROAD-MERCHANT-DEMO.md](AGENT-GUMROAD-MERCHANT-DEMO.md) is the
  reviewer demo script for the browser UI.

## Run Everything

From the repo root, run one command:

```bash
./scripts/start-gumroad-merchant.sh
```

That script installs Python/npm dependencies, starts the backend API, starts the
browser UI, verifies the MCP server with the smoke test, prints the local URLs,
and keeps the services running until you press `Ctrl-C`.

For the live chatbot path, paste the temporary OpenAI key into `.env.local`:

```text
OPENAI_API_KEY=<TEMP_OPENAI_API_KEY_FROM_SUBMISSION_EMAIL>
```

```text
Browser UI:  http://127.0.0.1:8080/
Backend API: http://127.0.0.1:8001/api/health
```

For a one-time startup verification that exits after the checks:

```bash
./scripts/start-gumroad-merchant.sh --once
```

The chat UI reads `OPENAI_API_KEY` from local env or `.env.local`. If the key or
OpenAI Agents SDK is unavailable, the backend falls back to deterministic
SQLite-backed answers from the seeded demo analytics.

## Run the MCP Server

The MCP server is stdio-based, so an MCP-capable host normally launches it as a
command instead of connecting to a long-running HTTP port. Use this command in
Codex, Claude, Cursor, or another MCP-capable app:

```bash
./scripts/start-gumroad-merchant.sh --mcp-stdio
```

Once it is configured in an MCP-capable agent, ask:

```text
Use Gumroad Merchant to show me what I can do.
```

The MCP server exposes a `get_gumroad_merchant_help_menu` tool, 41 current tools,
repo-relative install instructions, and the same seeded merchant workflows used
by the browser demo. See [MCPGuide.md](MCPGuide.md) for setup details.

## What Works

The browser UI and MCP server cover:

- product, revenue, conversion, traffic-source, UTM, churn, refund, and customer
  sale analysis
- Refund Ops for triage, buyer replies, chargeback evidence packets, and audit
  notes
- Content Radar for marketing plans, campaign drafts, tracked campaigns, and KPI
  watchlists
- Retention Saver for pause-before-cancel estimates tied to Gumroad issue `#4884`
- MCP Merchant automation for the Gumroad admin API/CLI direction tied to open
  Gumroad issue `#4677`
- Shortest QA for natural-language workflow tests
- Gumroad help-doc search through a local SQLite FTS corpus
- local action artifacts such as `agent_actions`, `tracked_campaigns`, roadmap
  files, and generated architecture diagrams

## Data Boundary

This repo uses seeded local data only. It does not scrape Gumroad, call Gumroad
production services, read real creator records, send emails, submit disputes,
issue refunds, change pricing, alter subscriptions, touch payouts, or execute
admin writes.

The seeded demo keeps real Gumroad writes out of scope. The product direction is
not permanently read-only, though. The MCP path is designed for scoped
read-write merchant automation: low-risk reads can run directly, while refunds,
disputes, emails, posts, product edits, pricing changes, subscription changes,
payout operations, and other sensitive actions require scoped auth, preflight
checks, explicit confirmation, and audit logs.

## Smoke Tests

Run the core syntax and Python compile check:

```bash
npm run check
```

Run the MCP smoke test:

```bash
python3 scripts/run_mcp_smoke.py
```

Run the local agent action smoke:

```bash
python3 scripts/run_agent_action_smoke.py
```

Run the live question-context smoke against the API:

```bash
python3 scripts/run_agent_question_context_smoke.py
```

## Main Local Routes

```text
GET /api/dashboard
POST /api/agent/chat
GET /api/refund-ops/summary
GET /api/refund-ops/cases
GET /api/content-radar/summary
GET /api/retention-saver/summary
GET /api/admin-preview/api-cli-recommendation
GET /api/shortest-qa/summary
GET /api/agent/actions
POST /api/agent/actions/{action_id}/apply
POST /api/tracked-campaigns
POST /api/roadmaps
POST /api/architecture-diagrams
GET /api/artifacts/{artifact_type}/{filename}
```

## Core Idea

Gumroad already helps creators see what happened. Gumroad Merchant helps them
decide what to do next by turning product analytics into evidence-backed,
action-ready revenue workflows.
