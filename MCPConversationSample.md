# MCP Sample

This is a reviewer-facing sample from the Gumroad Merchant MCP path. It shows
the no-web-UI version of the demo: an MCP-capable agent discovers the available
tools, calls the local Gumroad Merchant server, and turns seeded business data
into concrete next steps.

This is stdio MCP, not an HTTP server. The agent host launches the repo command
below and talks to it through MCP tool discovery and tool calls.

The sample uses seeded local SQLite data only. It does not call Gumroad
production services, read real creator records, send emails, submit disputes,
issue refunds, change pricing, or perform admin writes.

```text
Transport: stdio
Launcher: <PROJECT_ROOT>/scripts/gumroad-merchant-mcp.sh
Tools discovered: 41
```

## Five-Pass Transcript

### Pass 1

User:

```text
Use Gumroad Merchant to show me what I can do.
```

MCP calls:

```text
get_gumroad_merchant_help_menu({"section": "all"})
```

Agent:

```text
MCP discovered 41 tools.
Main sections: analytics, refund_ops, growth, actions, retention, admin, qa, search.
It exposes analytics, Refund Ops, Content Radar, retention, admin actions, QA, and help search from the local seeded data.
```

### Pass 2

User:

```text
How is the business doing over the last 30 days, and where is traffic coming from?
```

MCP calls:

```text
get_product_metrics({"date_range": "30", "product_id": "all"})
get_traffic_sources({"date_range": "30", "limit": 3, "product_id": "all"})
```

Agent:

```text
30-day sales: 129 orders and $3,881.00 revenue.
Conversion: 3.9%; refund rate: 7.8%.
Top traffic returned: Gumroad Discover: 31 sales / $939.00, YouTube: 17 sales / $833.00, Newsletter: 12 sales / $508.00.
```

### Pass 3

User:

```text
What refunds or disputes need attention, and can you build the first evidence packet?
```

MCP calls:

```text
get_refund_ops_summary({"date_range": "30", "product_id": "all"})
list_refund_cases({"date_range": "30", "limit": 3, "mode": "dispute", "product_id": "all"})
build_dispute_evidence_pack({"case_id": "refund-prod-audio-pack-2"})
```

Agent:

```text
Cases needing review: 6 across 6 seeded cases.
First dispute case: refund-prod-audio-pack-2 for prod-audio-pack.
Evidence packet: Chargeback dispute evidence packet for Cinematic Lo-Fi Sample Pack: purchase demo-prod-audio-pack-1...
```

### Pass 4

User:

```text
What campaign should I run next, and can you draft an asset for it?
```

MCP calls:

```text
build_marketing_plan({"date_range": "30", "horizon_weeks": 4, "product_id": "all"})
draft_campaign_assets({"date_range": "30", "product_id": "all", "trend_id": "sample-pack-session"})
```

Agent:

```text
Campaign focus: Sample-pack session breakdowns.
Draft asset: Cinematic Lo-Fi Sample Pack: Sample-pack session breakdowns.
Boundary: draft only; it does not post, send, save, or update anything.
```

### Pass 5

User:

```text
For admin/API/CLI direction, what would MCP do and what QA should we run?
```

MCP calls:

```text
get_admin_api_cli_recommendation({})
preview_admin_action({"action_id": "refund_review", "case_id": "refund-prod-audio-pack-2"})
generate_shortest_qa_tests({"limit": 2, "suite_id": "refund_ops"})
```

Agent:

```text
API surface: Create a separate internal admin API under /internal/admin, not the public v2 API.
CLI command: gumroad-admin refunds prepare --case-id refund-prod-audio-pack-2 --purchase-id demo-prod-audio-pack-1 --confirm-required.
QA tests returned: 2; first test: Chargeback evidence packet can be reviewed without being submitted.
```

## Verification

The sample was generated after these checks passed:

```text
npm run check
python3 -m py_compile gumroad_merchant/database.py gumroad_merchant/mcp_server.py
python3 scripts/run_mcp_smoke.py
```

The seeded database self-heal path was also checked against a deliberately
incomplete temporary SQLite database.
