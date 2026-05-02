# Gumroad Revenue Copilot Demo

This demo is a fast, standalone proof of the Revenue Copilot data flow. It is intentionally local-first and static: no Gumroad scraping, no production Gumroad data, and no network access to Gumroad is required.

The primary no-web-UI path is now Gumroad Merchant MCP. Configure the stdio
server from `MCPGuide.md`, then ask Codex to call the Gumroad Merchant tools directly.
The dashboard remains useful as a visual proof surface.

## Run Locally

From this repo root:

```bash
cd "<PROJECT_ROOT>"
python3 -m pip install -r requirements.txt
cp .env.example .env.local
```

Put your local `OPENAI_API_KEY` in `.env.local`, then start the backend:

```bash
python3 -m uvicorn backend.api:app --host 127.0.0.1 --port 8001
```

The default chat smoke model is `gpt-5.4-nano` with low verbosity and 5 live
agent turns for low-cost API checks. Optional image tests use `gpt-image-1-mini`,
`low` quality, `1024x1024` API output, and local downscaling to `480px`:

```bash
python3 scripts/generate_merchant_test_image.py
```

Run the compact daily Merchant Op script with the existing `.env.local`
`OPENAI_API_KEY`:

```bash
python3 scripts/run_daily_merchant_brief.py
```

In a second terminal, start the static dashboard:

```bash
python3 -m http.server 8080 --directory demo
```

Open:

```text
http://localhost:8080/
```

Architecture diagram:

```text
http://localhost:8080/architecture.html
```

MCP setup page:

```text
http://localhost:8080/mcp.html
```

The dashboard side nav also includes an `MCP Server` tab beside Architecture,
Chatflow, and Brief. That page shows the drag-and-drop installer prompt from
`demo/mcp/`.

If port `8080` is already in use, choose another port:

```bash
python3 -m http.server 8090 --directory demo
```

Then open `http://localhost:8090/`.

## Data Boundary

The demo uses seeded local demo data only. The sample products, views, sales,
refunds, referrers, Refund Ops cases, Content Radar trend angles, Retention
Saver estimates, Admin Actions templates, Shortest QA scenarios, audit notes, and
recommendation evidence are synthetic fixtures created to prove the product
experience and data flow.

This demo does not:

- scrape Gumroad
- call Gumroad production services
- read production creator data
- make autonomous refunds, chargeback dispute submissions, pricing changes,
  emails, posts, subscription changes, admin action executions, payout changes, or
  product-page changes

Gumroad Merchant stores demo chat history in local SQLite and uses Redis only as
optional runtime support for session TTL, rate limiting, and in-flight locks.
Redis is not the durable chat history source.

The analytics database is `data/gumroad_merchant.sqlite`. It is seeded from the
local product, traffic-source, churn, location, UTM, and synthetic customer-sales
fixtures. It also seeds a read-only official Gumroad help-doc FTS corpus for
fees, payouts, Stripe/PayPal processor references, chargebacks, refund/payout
impact, taxes, Merchant of Record notes, and related Help Center navigation. The
loaded sections are listed in `GUMROAD_HELP_RAG_SECTIONS.md`.

The browser refreshes that analytics and help-doc snapshot when the chat opens via:

```text
POST /api/agent/data/refresh?force=true
```

The conversation history database is `data/gumroad_merchant_chat.sqlite`, so
refreshing analytics does not wipe the chat session.

Refund Ops adds read-only endpoints for summary metrics, case queues, case
details, chargeback dispute evidence packets, draft buyer replies, and prevention
actions. Every Refund Ops output is a draft or review packet; no endpoint mutates
real Gumroad data.

Content Radar, Retention Saver, Shortest QA, and the MCP merchant-automation
panel keep their seeded-demo actions local. The agent action lane can now
stage/apply local `agent_actions`, create `tracked_campaigns` rows, and generate
downloadable roadmap or architecture artifacts in the test profile. Real
Gumroad writes are not executed by this prototype, but the MCP direction is
read-write automation for refunds, disputes, emails, posts, product edits,
pricing changes, subscription changes, payout operations, product catalog
updates, and monthly sales workflows behind scoped permissions and confirmation.

Smoke-test the 10-prompt analytics plus help-doc transcript:

```bash
python3 scripts/run_gumroad_merchant_help_rag_smoke.py
```

Smoke-test local agent actions, duplicate prevention, refresh preservation, and
artifact generation:

```bash
python3 scripts/run_agent_action_smoke.py
```

## Intended Product Path

The standalone demo proves the shape of the real system without coupling to production infrastructure. The intended Gumroad implementation path is:

```text
Gumroad Rails models/database
  -> metrics builder
  -> signal detector
  -> AI suggestion service
  -> UI
```

In the real product, Rails owns the source-of-truth facts from existing models and reporting tables. A metrics builder computes creator/product metrics deterministically. A signal detector finds high-confidence revenue opportunities from those facts. An AI suggestion service packages the approved signals into creator-facing recommendations with cited evidence. The UI renders those suggestions as action-ready next moves.

The AI layer should not calculate business metrics or invent evidence. It should only explain and prioritize precomputed facts.

## Reviewer Demo Script

1. Start the static server with `python3 -m http.server 8080 --directory demo`.
2. Start the backend with `python3 -m uvicorn backend.api:app --host 127.0.0.1 --port 8001`.
3. Open `http://localhost:8080/` and confirm the dashboard loads.
4. Ask Gumroad Merchant: `Set a realistic three-month sales goal and show how we get there.`
5. Show that the response cites seeded local metrics such as monthly revenue, conversion, traffic sources, refunds, churn, or metadata gaps.
6. Click `Review` on a suggestion to open the safe action review panel.
7. Open the Refund Ops section, switch between `Prevent`, `Review`, and `Dispute`, and copy a buyer reply, dispute evidence packet, or audit note.
8. Ask Gumroad Merchant: `Build a dispute packet for our refunds.`
9. Open Content Radar and copy the campaign brief or UTM plan.
10. Open Retention Saver and show the `#4884` pause-offer estimate.
11. Open Shortest QA and copy one natural-language QA scenario.
12. Open the MCP Server tab, click `MCP Merchant automation`, and show the
    seeded demo boundary plus the scoped read-write production direction.
13. Ask Gumroad Merchant: `Generate natural-language QA tests for Refund Ops and Content Radar.`
14. Call out that this is not scraped Gumroad data and not production data.
15. Open `http://localhost:8080/architecture.html` to explain the demo data flow.
16. Close with the real-product path: Rails models/database -> metrics builder -> signal detector -> AI suggestion service -> UI.
