# Submission Email

Subject: Gumroad Merchant submission

Hi Gumroad team,

I’m submitting Gumroad Merchant, a working local prototype for a creator-facing personal agent layer inside Gumroad.

The core idea is simple: most AI creator tools give you either a dashboard or a blank chat box and expect you to know what to ask. I think Gumroad can flip that. The agent should teach the interface, explain what is happening in the business, show the evidence, and help the creator move from “what changed?” to “what should I do next?”

Repo:

```text
https://github.com/shane9coy/gumroad-revenue-copilot-prototype
```

To run the project:

```bash
git clone https://github.com/shane9coy/gumroad-revenue-copilot-prototype.git
cd gumroad-revenue-copilot-prototype
git pull origin main
```

I’m including a temporary OpenAI API key for the live chatbot demo:

```text
<TEMP_OPENAI_API_KEY>
```

Paste that key into the checked-in `.env.local` file:

```text
OPENAI_API_KEY=<TEMP_OPENAI_API_KEY>
```

Then start the full demo with one command:

```bash
./scripts/start-gumroad-merchant.sh
```

That launcher installs Python dependencies, handles npm dependencies if any are declared, starts the backend API, starts the browser UI, refreshes the seeded data, runs the MCP smoke test, prints the local URLs, and keeps the services alive until `Ctrl-C`.

Important MCP detail: the MCP server is stdio-based, not a normal HTTP server. The default launcher verifies MCP through the smoke test. For Codex, Claude, Cursor, or another MCP-capable host, configure the MCP command as:

```bash
./scripts/start-gumroad-merchant.sh --mcp-stdio
```

I also built against the open Gumroad GitHub issue #4677, “Gumroad admin CLI.” The MCP server and MCP Merchant automation tab show how that direction could work: the same Gumroad Merchant tool surface can run inside Codex, Claude, Cursor, or another agent setup, with scoped permissions, confirmations, and audit logs instead of loose dashboard clicks.

The key docs are:

- `README.md`
- `SUBMISSION_SUMMARY.md`
- `MCPGuide.md`
- `MCPConversationSample.md`
- `AgentConversationSample.md`

My future development roadmap would be to push this further in three directions.

First, I would build out the agent intuition layer. The agent should get better at understanding what kind of creator is using Gumroad, what their product mix looks like, what signals usually matter for that business, and which next actions are actually worth interrupting them for.

Second, I would add document and image creation abilities. A creator should be able to ask Gumroad Merchant to generate product images, launch assets, customer-facing documents, refund or dispute packets, product update drafts, campaign briefs, and other business materials directly from the same Gumroad context.

Third, I would connect the agent to real product changes in the user UI. The current demo prepares, explains, and stages actions. The next version should let the creator approve the change and then have the agent update the product page, draft or publish a post, adjust pricing, prepare a refund, update a campaign, or make other scoped changes through Gumroad itself with confirmation and audit logs.

My bigger vision is that this is the move for 2026. Creators are going to bring personal agents into their business workflows either way. If Gumroad does not own that agent layer, it will happen around Gumroad and Gumroad risks becoming just the data source. If Gumroad does own it, Gumroad becomes the operating layer for creator businesses: analytics, refunds, disputes, posts, pricing, subscriptions, payouts, growth actions, and support all routed through a trusted merchant agent.

That is what this prototype is meant to make concrete.

Thanks,
Shane
