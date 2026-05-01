# Gumroad Merchant MCP Agent Install

You are helping me connect this local Gumroad Merchant prototype to an MCP-capable agent.

The repo is here:

```text
/Users/sc/Project Files/gumroad
```

The MCP launcher is here:

```text
/Users/sc/Project Files/gumroad/scripts/gumroad-merchant-mcp.sh
```

Your job is to install or configure the local MCP server for the agent host you are running inside. Do not guess the host config format. Inspect the local environment first, preserve existing MCP servers, and only add a `gumroad_merchant` server entry.

## What This Server Does

Gumroad Merchant MCP exposes the same local demo capabilities as the browser prototype:

- analytics and product metrics
- Refund Ops and chargeback dispute packets
- Content Radar and marketing plans
- Retention Saver
- Admin Preview
- Shortest QA
- Gumroad help-doc search
- local agent action artifacts

The point is to let a local agent call the same merchant workflow tools instead of trying to infer everything from a prompt. In this seeded prototype, production-impacting actions stay in review mode. In the product direction, the same MCP shape becomes a scoped read-write automation layer for a real Gumroad business.

## Safety Protocol

Before installing or using this seeded server, preserve these boundaries:

- Run the server in seeded mode.
- Do not add production Gumroad credentials.
- Do not call Gumroad production services.
- Do not read real creator records.
- Treat generated production-impacting actions as review-only unless the tool explicitly says it is a local test write.
- Admin Preview may return command text, preflight checks, blocked reasons, and audit-note copy, but this seeded server must not execute real admin commands.
- Seeded MCP responses that would affect a real Gumroad account should return `review_only: true` and `will_execute: false`.
- Local write tools may only write test-profile rows or generated artifacts inside this repo.

Product direction:

- Add scoped read-write tools for refunds, disputes, emails, posts, product edits, pricing changes, subscription changes, payout operations, product catalog updates, and monthly sales workflows.
- Split write tools into `dry_run`, `confirm`, and `apply` modes so the agent can summarize the action before it executes.
- Require scoped merchant/admin tokens, role checks, idempotency keys, preflight validation, and audit notes for real writes.
- Let safe reads run directly; require explicit confirmation for refunds, payout changes, subscription edits, pricing changes, and other account-impacting actions.
- Return the intended action, affected object, risk level, confirmation state, audit trail, and next safe action in every write response.

## Install Steps

1. Verify the repo and launcher exist:

```bash
cd "/Users/sc/Project Files/gumroad"
test -x scripts/gumroad-merchant-mcp.sh
```

2. Install Python dependencies if needed:

```bash
cd "/Users/sc/Project Files/gumroad"
python3 -m pip install -r requirements.txt
```

If this machine has the bundled Codex runtime, this is also valid:

```bash
cd "/Users/sc/Project Files/gumroad"
/Users/sc/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pip install -r requirements.txt
```

3. Configure the current MCP host to run this command:

```text
/Users/sc/Project Files/gumroad/scripts/gumroad-merchant-mcp.sh
```

For Codex, add this to `~/.codex/config.toml`:

```toml
[mcp_servers.gumroad_merchant]
command = "/Users/sc/Project Files/gumroad/scripts/gumroad-merchant-mcp.sh"
```

For other MCP hosts, add a server named `gumroad_merchant` with the same command. If the host uses JSON, YAML, or TOML, preserve its existing config and add only this server entry.

4. Restart or reload the MCP host.

5. Confirm the server is available by asking:

```text
Use Gumroad Merchant to show me what I can do.
```

The first tool to call is:

```text
get_gumroad_merchant_help_menu
```

## Smoke Test

From the repo, run:

```bash
python3 scripts/run_mcp_smoke.py
```

The smoke test starts the MCP server over stdio, lists tools, and checks representative workflows for Refund Ops, dispute evidence, Content Radar, Retention Saver, Admin Preview, issue #4677 guidance, Shortest QA, and the MCP help menu.

## Useful Prompts After Install

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

## Expected Response Shape

Successful tool calls use this envelope:

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

Expected failures should be returned as agent-actionable errors with a suggested next step, not raw stack traces.
