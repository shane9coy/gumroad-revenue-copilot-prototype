# Gumroad Merchant

I built Gumroad Merchant because the default shape of "AI for creators" still feels backwards to me.

Most tools either give you a dashboard full of numbers with no clear actionable signal or a blank chat box and then expect you to know what to ask. That works for a power user who already knows the business questions. It does not work as well for your average artist and creator who is trying to understand a refund spike, a customer issue, a content opportunity, or a Gumroad policy question while also running the rest of their business.

That was the core product insight behind this prototype: the agent should help teach the interface. The UI should not make the creator start from a perfect prompt. It should give them obvious paths into the work, then let the agent explain what is happening, what evidence it used, and what the creator can do next.

That led me to make the demo chat-first without making everything depend on an open-ended chat prompt. I treated the action cards as structured entry points into workflows a Gumroad creator would already recognize: Refund Ops, Content Radar, Retention Saver, Admin Actions, QA, analytics, and help-doc search.

When someone clicks into one of those paths, Gumroad Merchant starts with the context for that workflow. It explains the situation, cites the seeded facts or help docs it used, and turns that into an action-ready next step.

## What I Built

Gumroad Merchant is an action-ready revenue copilot for creators. It uses seeded Gumroad-style analytics, a local Gumroad help-doc corpus, and a constrained tool layer to turn business signals into practical next actions.

It can:

- summarize product, revenue, conversion, traffic, refund, churn, UTM, and customer-sale data
- detect useful business signals from that data
- generate cited growth plans and conversion ideas
- help draft refund replies and chargeback evidence packets
- build content campaign ideas from product and traffic signals
- preview retention-save plans
- generate admin command workflows
- create natural-language QA journeys
- answer Gumroad money-ops questions from seeded help docs
- expose the same capabilities through MCP for agent and terminal workflows

The seeded prototype keeps production writes out of the demo: refunds, emails, pricing, product edits, chargeback disputes, payout changes, and admin commands are modeled as reviewed actions instead of live operations.

That is a demo boundary, not the product ceiling. The MCP path is where this turns into scoped read-write automation: summarize the business, stage the action, show the exact risk, then execute through permissions, confirmations, and audit logs.

I tried to keep one line clear the whole time: the system can recommend, explain, draft, and preview, but a human still reviews the action.

## How I Thought About It

Gumroad already helps creators see what happened in their business. The place where AI can add value is the next layer up: connecting those facts to a decision.

For example, if refunds increase, "refunds are up" is only the starting point. A creator needs to know which product or customer pattern is driving it, whether there is enough evidence to act, what the best reply might say, and whether the issue belongs in product copy, support, pricing, or policy review.

Because of that, I did not want the agent to invent business facts or calculate important metrics inside a freeform answer. The facts should come from the system first. The agent's job is to explain those facts, rank the options, and package the next move in a way a creator can actually use.

The interface follows the same idea. Instead of asking the creator to think like an analyst, the product gives them a small set of useful operational paths. The agent then teaches what each path means as the creator uses it.

## Product Shape

The production version would fit naturally into Gumroad's existing product surface:

```text
Rails models/database
-> metrics builder
-> signal detector
-> AI suggestion service
-> action-ready creator UI
```

The important boundary is that the AI layer explains and prioritizes precomputed facts. It does not become the source of truth for business metrics, and it does not mutate Gumroad state.

That boundary matters because creators trust Gumroad with real revenue, customer relationships, subscriptions, refunds, and payouts. If AI is going to be useful in that environment, it has to be constrained before it is powerful.

## MCP Add-On

I also exposed the same tool layer through MCP because Gumroad's open issues pointed toward API, CLI, and admin workflows that reduce dependence on the web UI.

The MCP server exposes the same capabilities as the demo UI:

- analytics
- Refund Ops
- Content Radar
- Retention Saver
- Admin Actions
- Shortest QA
- Gumroad help-doc search

For the seeded demo, the MCP tools return execution mode, confirmation state,
and audit context. A small local action path can write only to repo-local test
rows or generated artifacts, which lets the demo prove the action contract
without touching a real Gumroad account.

I included this because the same underlying tools should be usable from more
than one interface. A creator might use the web UI. An internal teammate might
use a terminal workflow. An agent inside Codex, Claude, or Cursor might call the
same tool surface. The important part is that all of those paths share the same
permissions, confirmations, and audit boundary.

## Demo Path

A reviewer can run the local demo, open the dashboard, and ask Gumroad Merchant for a realistic sales plan. The answer cites seeded product metrics instead of making up a story.

They can also resolve refund cases, generate a chargeback evidence packet, build a content campaign, prepare a retention save plan, inspect admin command workflows, generate natural-language QA tests, and ask money-ops questions against the seeded Gumroad help docs.

The demo is intentionally fixture-backed. The point is not to pretend it is already wired into production Gumroad data. The point is to show the workflow shape, execution scope, and interface pattern before connecting it to the real data paths.

## Why I Think It Matters

The obvious AI feature for Gumroad would be a chatbot that summarizes sales. That would be useful, but it would still leave too much work on the creator.

The version I wanted to test helps the creator move through the full decision:

- what changed
- why it matters
- what evidence supports it
- what options are available
- what can be prepared, confirmed, applied, or copied
- what should remain human-controlled

That practical difference is what I was aiming for. Gumroad Merchant is a working prototype for a product direction where Gumroad becomes more useful as an operating layer for creator businesses.

If the same workflow were connected to Gumroad's real internal analytics and API surface, the agent could become a guide inside the product instead of a separate layer the creator has to translate back into Gumroad. The demo is meant to make that product shape concrete.
