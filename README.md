# Gumroad Revenue Copilot Prototype

Build-ready handoff for a Gumroad open-source competition prototype.

Start here:

- [SUBMISSION_SUMMARY.md](SUBMISSION_SUMMARY.md)
- [MCPGuide.md](MCPGuide.md)
- [MCPConversationSample.md](MCPConversationSample.md)
- [AgentConversationSample.md](AgentConversationSample.md)

Run the local static demo:

```bash
npm run demo
```

Then open `http://localhost:8080/`.

Run the Gumroad Merchant backend in a second terminal:

```bash
python3 -m pip install -r requirements.txt
python3 -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

Run Gumroad Merchant as a local MCP server for the no-web-UI demo path:

```bash
scripts/gumroad-merchant-mcp.sh
```

Once configured in Codex, ask: `Use Gumroad Merchant to show me what I can do.`
The MCP server exposes a `get_gumroad_merchant_help_menu` tool for terminal
guidance.

See [MCPGuide.md](MCPGuide.md) for the repo-relative MCP host config, supported tools,
and smoke-test flow. For a real five-pass MCP transcript, see
[MCPConversationSample.md](MCPConversationSample.md).

The chat UI reads `OPENAI_API_KEY` from local env or `.env.local`. If the key or
OpenAI Agents SDK is unavailable, the backend falls back to deterministic
SQLite-backed answers from the seeded demo analytics.

Gumroad Merchant also seeds official Gumroad help/pricing sections into the same
local SQLite database with FTS search. Help-doc answers cover creator money-ops
questions such as fees, payouts, Stripe/PayPal processor references,
chargebacks, refunds/payout-balance impact, taxes, Merchant of Record notes, and
where to find related docs. The indexed sections are documented in
[`GUMROAD_HELP_RAG_SECTIONS.md`](GUMROAD_HELP_RAG_SECTIONS.md).

The dashboard includes four creator-facing agent lanes beyond core analytics:

- Refund Ops for refund reduction, refund request triage, chargeback dispute
  evidence packets, and audit notes.
- Content Radar for seeded trend angles, marketing plans, campaign drafts, UTM
  names, and KPI watchlists.
- Retention Saver for membership pause-offer estimates tied to Gumroad issue
  `#4884`.
- Shortest QA for natural-language test journeys covering these lanes and chat
  fallback routing.

The MCP Server tab carries the admin/API/CLI lane as `MCP Merchant automation`,
with the seeded demo boundary separated from the production direction: scoped
read-write merchant tools with confirmations, role checks, and audit notes.

Most lanes are read-only and synthetic in this prototype. The agent action lane
can write only to local test-profile tables/artifacts: pending `agent_actions`,
local `tracked_campaigns`, downloadable roadmaps, and generated architecture
diagrams. Real Gumroad writes stay out of the seeded demo, but the MCP product
path is read-write automation for refunds, disputes, emails, posts, product
edits, pricing changes, subscriptions, payouts, product catalog updates, and sales workflows
behind scoped permissions and explicit confirmation.

Defaults are set for cheap local testing: chat uses `gpt-5.4-nano`, low
verbosity, and 5 live agent turns by default. The
optional image smoke script uses `gpt-image-1-mini` with `low` quality. The GPT
Image API's smallest current direct output is `1024x1024`, so the script
downscales the saved test image to `480px` locally.

Run one compact daily Merchant Op brief with the existing `.env.local`
`OPENAI_API_KEY`:

```bash
python3 scripts/run_daily_merchant_brief.py
```

Dry-run the prompt, model, and cost note without spending tokens:

```bash
python3 scripts/run_daily_merchant_brief.py --dry-run
```

Daily Merchant Op cost note, using current OpenAI standard token pricing:
`gpt-5.4-nano` is $0.20 / 1M input tokens and $1.25 / 1M output tokens;
`gpt-5.4-mini` is $0.75 / 1M input tokens and $4.50 / 1M output tokens.
OpenAI also lists lower Batch/Flex pricing for async or lower-priority jobs.
Source: [OpenAI pricing](https://developers.openai.com/api/docs/pricing).

| Run size | Nano cost | Mini cost |
| --- | ---: | ---: |
| 10k input + 1k output | ~$0.003 | ~$0.012 |
| 20k input + 2k output | ~$0.0065 | ~$0.024 |
| 50k input + 5k output | ~$0.016 | ~$0.06 |

The cost shape is intentional: compute revenue, churn, refunds, UTM, source,
and location metrics deterministically; pass the model a compact merchant brief;
ask for analysis, recommended actions, and action drafts; run deeper analysis
only when thresholds fire or the merchant clicks a signal.

When the chat opens, the UI calls:

```text
POST /api/agent/data/refresh?force=true
```

That refreshes the selected local SQLite profile from the seeded analytics
snapshot. `GUMROAD_MERCHANT_PROFILE=test` uses the copied write-enabled test
DBs, while explicit `GUMROAD_MERCHANT_DB` and `GUMROAD_MERCHANT_CHAT_DB` values
still override the profile defaults.

Refund Ops read-only smoke endpoints:

```text
GET /api/refund-ops/summary
GET /api/refund-ops/cases
GET /api/refund-ops/cases/{case_id}
GET /api/refund-ops/cases/{case_id}/dispute-evidence
GET /api/refund-ops/cases/{case_id}/buyer-reply
GET /api/refund-ops/prevention-actions
```

New growth/admin/QA endpoints:

```text
GET /api/content-radar/summary
GET /api/content-radar/trends
GET /api/content-radar/plan
GET /api/content-radar/drafts
GET /api/retention-saver/summary
GET /api/retention-saver/risks
GET /api/retention-saver/pause-plan
GET /api/retention-saver/estimate
GET /api/admin-preview/summary
GET /api/admin-preview/api-cli-recommendation
GET /api/admin-preview/templates
GET /api/admin-preview/command
GET /api/admin-preview/preview
GET /api/shortest-qa/summary
GET /api/shortest-qa/suites
GET /api/shortest-qa/tests
GET /api/agent/actions
POST /api/agent/actions/{action_id}/apply
POST /api/tracked-campaigns
POST /api/roadmaps
POST /api/architecture-diagrams
GET /api/artifacts/{artifact_type}/{filename}
```

Agent action smoke:

```bash
python3 scripts/run_agent_action_smoke.py
```

Optional low-cost image smoke:

```bash
python3 scripts/generate_merchant_test_image.py
```

Analytics plus help-doc RAG smoke transcript:

```bash
python3 scripts/run_gumroad_merchant_help_rag_smoke.py
```

Core idea:

Gumroad already shows creators what happened. Gumroad Merchant tells them what
to do next by turning product analytics into evidence-backed, action-ready
revenue actions: realistic 3- or 6-month sales goals, Refund Ops packets,
content campaigns, retention save plans, admin action previews, and QA journeys.
