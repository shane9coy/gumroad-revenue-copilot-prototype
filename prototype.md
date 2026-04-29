# Gumroad Revenue Copilot Prototype

Status: planning handoff  
Date: 2026-04-29  
Primary goal: build a working, forward-facing Gumroad prototype that turns product analytics into evidence-backed revenue actions for creators.

## One-sentence pitch

Gumroad already shows creators what happened. Revenue Copilot tells them what to do next.

## Core thesis

Creators do not want to live inside dashboards. Gumroad analytics already frame the product around helping creators "understand and act on the data that matters." This prototype makes the "act" part real by turning Gumroad's existing product, traffic, sales, review, refund, and Discover signals into specific next moves.

The strongest submission is not a generic AI wrapper. It is a data-grounded product experience:

- compute the facts in Rails
- detect meaningful revenue signals deterministically
- use an LLM only to explain and package recommendations
- require every recommendation to cite the metric that supports it
- give the creator an obvious next action

## Recommended submission title

Creator Revenue Copilot: Data-Grounded Product Optimization for Gumroad

Alternative title:

From Analytics to Action: A Revenue Copilot for Gumroad Creators

## Why this is the right flagship project

This combines the best pieces of the research:

- It maps directly to creator revenue.
- It aligns with open issue #4872, "AI-powered product page optimization suggestions based on sales data."
- It extends Gumroad's existing AI product creation work into post-launch product improvement.
- It is visible and demoable in the product UI.
- It fits Gumroad's small-team, high-leverage product direction.
- It gives the reviewer a concrete implementation rather than just a proposal.

Avoid leading with internal-only ideas such as admin CLI, fraud review, or moderation evals. Those are useful, but Revenue Copilot is more visible, safer for a public prototype, and easier to judge quickly.

## Repo and platform context

Observed Gumroad repo/platform signals:

- Rails 7.1 plus TypeScript/React/Inertia full-stack ecommerce app.
- MySQL, Redis, Sidekiq, Mongo, Elasticsearch, AnyCable, Stripe, PayPal, Braintree.
- OpenAI is already used for product details, product images, refund-policy classification, usernames, and community chat recaps.
- Gumroad has an agent-oriented engineering culture through `.agents/skills`, `bin/test-confidence`, and the public Gumclaw/autoresearch workflow.
- Discover/search currently relies heavily on Elasticsearch plus sales/co-purchase recommendation logic.
- Analytics are descriptive and already include product views, sales, referrers, locations, churn, and related reporting surfaces.
- Contribution guidelines require clear PR descriptions, tests, demo/video evidence, and AI disclosure.

Issue status as of 2026-04-29:

- #4872 Product page optimization: open.
- #4677 Gumroad admin CLI: open.
- #19 Email marketing improvements: closed as not planned, but useful historical direction.
- #1833 Content editor per-page analytics: closed as not planned, but useful historical direction.
- #4353 Fraud pattern rules engine: closed as completed, so any risk idea should be framed as an extension.

## Product concept

Add a Revenue Copilot panel to Gumroad that helps a creator optimize one product at a time.

Primary placement:

- Product analytics page.

Secondary placement:

- Product edit page.

The creator sees a small module called "Next moves" or "Revenue Copilot." When clicked, Gumroad analyzes that product and returns several recommendation cards. Each card includes:

- a clear recommendation
- the metric evidence behind it
- why it matters
- suggested action
- confidence level
- optional apply, dismiss, or create experiment action

Example card:

```text
Fix conversion

Your product views increased 42% over the previous period, but sales were flat.
Conversion fell from 4.1% to 2.6%.

Next move:
Move the concrete buyer outcome into the first sentence of the description and
test a shorter product title.

Evidence:
- 1,240 views in the selected period
- 32 sales
- 2.6% conversion
- prior period conversion: 4.1%
```

## MVP scope

Build a working first version that can be demoed locally.

MVP must include:

- Backend metrics builder for a single product.
- Product optimization service under the existing AI namespace.
- Structured JSON response with evidence-backed suggestions.
- Product analytics or product edit UI module.
- At least 3 recommendation types.
- Tests for the metrics builder and service behavior.
- Demo seed path or instructions.
- Feature flag around the feature.

Recommended MVP suggestion types:

1. High traffic, low conversion.
2. Referrer/source outperformance.
3. Discover/tag/category improvement.
4. Refund or rating/review warning.
5. Price experiment suggestion.

Keep the first implementation focused. Do not auto-send emails, auto-change price, or touch fraud/risk workflows in the MVP.

## Non-goals for MVP

- No full vector database integration.
- No Discover ranking rewrite.
- No autonomous price changes.
- No autonomous email sends.
- No admin/risk decisions.
- No moderation eval dashboard.
- No mobile push notifications.
- No large migration touching high-risk tables such as `users` or `purchases`.

## Data inputs

Use data Gumroad already has. The LLM should not calculate metrics.

Core product fields:

- name/title
- description
- price
- currency
- tags
- taxonomy/category
- product type
- ratings/review count
- refund policy if available

Analytics fields:

- product page views
- sales count
- gross revenue
- conversion rate
- prior-period conversion
- referrer performance
- UTM/source performance
- refund count/rate
- review count/rating
- churn for memberships/subscriptions if available
- workflow/email outcomes if available

Discover/search fields:

- category completeness
- tag completeness
- rating eligibility
- sales threshold/eligibility signals if available
- product recommendation/search fields

## Signal detection

Compute signals deterministically before calling the LLM.

Minimum useful calculations:

- period-over-period deltas
- conversion rate
- referrer conversion rates
- refund rate
- review coverage
- moving averages where available
- z-score anomaly where enough history exists

Simple rule examples:

```text
high_traffic_low_conversion:
  views_current >= 100
  conversion_current < conversion_previous * 0.75

referrer_outperforming:
  referrer_conversion >= overall_conversion * 1.5
  referrer_sales >= minimum_sales_threshold

refund_warning:
  refund_rate_current >= refund_rate_previous * 1.5
  refund_count_current >= minimum_refund_count

discover_metadata_gap:
  product has missing or overly broad tags/category
  product has sales/reviews but weak metadata completeness
```

Use conservative thresholds. It is better to show fewer high-confidence cards than many weak cards.

## LLM constraints

The LLM is a writing and prioritization layer, not the source of truth.

Rules:

- It receives precomputed facts only.
- It must return strict JSON.
- It cannot invent metrics.
- Every recommendation must cite at least one evidence metric.
- It should output creator-facing language, not internal diagnostics.
- It should avoid promises such as "this will increase revenue."
- It should phrase actions as experiments when impact is uncertain.

Suggested JSON shape:

```json
{
  "summary": "This product has strong traffic but weaker conversion than the prior period.",
  "suggestions": [
    {
      "type": "conversion",
      "title": "Tighten the product positioning",
      "recommendation": "Move the buyer outcome into the first sentence of the description.",
      "why_it_matters": "Views are up, but conversion is down compared with the previous period.",
      "evidence": [
        {
          "label": "Views",
          "value": "1,240",
          "period": "selected period"
        },
        {
          "label": "Conversion",
          "value": "2.6%",
          "comparison": "down from 4.1%"
        }
      ],
      "confidence": "medium",
      "action": {
        "kind": "edit_description",
        "safe_to_apply": false
      }
    }
  ]
}
```

## Backend implementation plan

Use repo patterns first. Confirm exact names before editing with `rg`.

Likely new files:

- `app/services/ai/product_page_optimizer_service.rb`
- `app/services/products/product_optimization_metrics_builder.rb`
- `app/services/products/product_optimization_signal_detector.rb`
- `app/jobs/product_optimization_job.rb`
- `app/controllers/products/optimizations_controller.rb` or equivalent nested controller
- request/service specs under `spec/`

Likely touched files:

- `config/routes.rb`
- product analytics controller/page
- product edit page component
- feature flag config if needed

Suggested service boundaries:

```text
Products::ProductOptimizationMetricsBuilder
  Input: seller/current user, product, selected date range
  Output: deterministic metrics hash

Products::ProductOptimizationSignalDetector
  Input: metrics hash
  Output: candidate signals with evidence

Ai::ProductPageOptimizerService
  Input: product facts, metrics, candidate signals
  Output: strict structured suggestions

ProductOptimizationJob
  Runs async when needed, low priority queue

Products::OptimizationsController
  POST /products/:id/optimize
  Authenticates seller ownership
  Returns suggestions JSON for Inertia/React UI
```

MVP can avoid a database migration by generating suggestions on demand. If persistence is needed, add it after the demo works.

Optional persistence model for v1:

```text
ProductOptimizationSuggestion
  product_id
  user_id
  status: generated, applied, dismissed
  suggestion_type
  title
  recommendation
  evidence_json
  action_json
  generated_at
  applied_at
```

Optional experiment model for later:

```text
ProductExperiment
  product_id
  user_id
  suggestion_id
  metric_name
  baseline_value
  started_at
  ended_at
  result_json
```

## Frontend product design

UI surface:

- A compact panel on product analytics called "Next moves."
- Button: "Generate insights" or "Optimize this product."
- Loading state while suggestions are generated.
- 3 to 5 cards, not a long report.

Card anatomy:

- icon or compact label for category
- title
- one-sentence recommendation
- evidence metrics
- confidence
- primary action
- secondary dismiss action

Example categories:

- Conversion
- Discover
- Traffic
- Pricing
- Retention
- Refunds
- Reviews

Suggested UI copy:

```text
Next moves
Evidence-backed suggestions based on this product's recent performance.
```

Avoid copy that sounds like magic. The UI should feel like a serious creator tool.

Possible actions:

- Edit title
- Edit description
- Update tags
- Review price
- Create email draft
- Create experiment
- Dismiss

For MVP, keep actions safe:

- navigate to edit field
- show suggested copy
- copy suggestion
- dismiss

Do not auto-apply price changes in the first version.

## User flow

1. Seller opens product analytics.
2. Seller clicks "Generate insights."
3. Backend builds metrics for selected product/date range.
4. Signal detector selects candidate signals.
5. AI service turns candidate signals into structured suggestions.
6. UI displays cards with evidence.
7. Seller applies, copies, edits, or dismisses a suggestion.
8. Later version tracks whether applied suggestions changed conversion.

## Testing plan

Do not rely on live OpenAI calls in tests.

Recommended tests:

- Metrics builder spec with seeded product views/sales/refunds.
- Signal detector spec for each signal type.
- AI service spec with mocked OpenAI response.
- Request spec for authorization and response shape.
- UI smoke test if the repo has an established frontend test path for the target component.

Test cases:

- seller can optimize own product
- seller cannot optimize another seller's product
- low-data product returns a safe "not enough signal yet" response
- high views plus falling conversion returns a conversion signal
- referrer outperformance returns source signal
- malformed AI response fails gracefully
- OpenAI timeout returns a user-safe error

Expected validation commands:

```bash
bin/rails spec spec/services/products/product_optimization_metrics_builder_spec.rb
bin/rails spec spec/services/products/product_optimization_signal_detector_spec.rb
bin/rails spec spec/services/ai/product_page_optimizer_service_spec.rb
bin/rails spec spec/requests/products/optimizations_spec.rb
bin/test-confidence
```

Adjust exact commands to repo conventions.

## Demo plan

The demo should show a creator-facing product moment, not just logs.

Demo script:

1. Start local Gumroad.
2. Log in as seeded seller.
3. Open a product with seeded views/sales.
4. Open product analytics.
5. Click "Generate insights."
6. Show 3 recommendation cards.
7. Open one card and show the cited metric evidence.
8. Click a safe action, such as edit description or copy suggestion.
9. Show tests passing.

Submission assets:

- short video under 3 minutes
- branch/fork link
- concise README section or PR description
- architecture note explaining future expansion
- AI disclosure following Gumroad contribution guidelines

## Acceptance criteria

The prototype is successful if:

- a reviewer can run it locally
- a seller can see Revenue Copilot in the UI
- suggestions are generated from real product metrics
- every suggestion cites evidence
- low-data products do not hallucinate recommendations
- the code is feature-flagged or easy to disable
- tests cover metrics, signals, service output, and authorization

## Future expansion lanes

Keep these in the written submission as the bigger vision, but do not build all of them in the first PR.

### 1. Hybrid Semantic Discover

Use the same signal layer plus embeddings to improve Discover and marketplace recommendations. Combine BM25, dense vectors, sales signals, ratings, freshness, and conversion-aware reranking.

### 2. Email and Audience Copilot

Turn Revenue Copilot suggestions into suggested creator campaigns:

- "email buyers of product A who have not bought product B"
- "send a launch reminder to high-intent clickers"
- "offer a discount to abandoned checkout users"

Use strict segment schemas and dry-run audience previews before any send.

### 3. Support RAG Assistant

Index Gumroad help docs and account state so creators can ask:

- why am I not eligible for Discover?
- where is my payout?
- why did this customer not receive a receipt?

Return cited answers and safe next actions.

### 4. Experiment Tracking

After applying a suggestion, track before/after conversion, sales, refund rate, or churn. This turns the tool from advice into a learning loop.

### 5. Mobile Digest

For Gumroad's upcoming Expo mobile app, send a weekly digest:

- top win
- biggest drop
- one recommended action
- one product to review

### 6. Moderation Eval Lab

Separate from the MVP. Add eval infrastructure for AI moderation:

- labeled fixture sets
- threshold diff reports
- false-positive/false-negative tracking
- policy regression checks

This is a strong secondary idea, but not the main public-facing prototype.

## Recommended PR framing

PR title:

```text
Add AI product optimization suggestions backed by analytics signals
```

PR description:

```text
This adds a prototype Revenue Copilot flow for product optimization. It analyzes a seller's product metrics, detects actionable revenue signals, and returns structured recommendations with cited evidence. The goal is to help creators move from analytics to action without requiring them to interpret every chart manually.
```

AI disclosure:

```text
AI tools were used to help draft the implementation plan, generate initial service/test scaffolding, and review edge cases. Final code was manually reviewed and tested.
```

## Next-agent pickup checklist

1. Open the Gumroad repo.
2. Read `README.md`, `CONTRIBUTING.md`, `AGENTS.md`, and `docs/testing.md`.
3. Search current product analytics/editing surfaces:

```bash
rg "analytics" app/controllers app/javascript
rg "ProductPageView|CreatorAnalytics" app spec
rg "ai_product_generation|ProductDetailsGenerator" app spec
rg "Flipper|feature" app config
```

4. Locate the safest UI insertion point.
5. Build metrics builder first without OpenAI.
6. Add signal detector tests.
7. Add AI service with mocked responses.
8. Add endpoint and authorization.
9. Add UI cards.
10. Run focused specs and `bin/test-confidence`.
11. Record demo video and write PR description.

## Strategic positioning for the competition

Lead with this:

```text
Gumroad has already invested in analytics, AI product creation, Discover, email, and support. The missing layer is execution intelligence: a system that turns Gumroad's own data into clear next actions for creators. Revenue Copilot starts with product optimization, then expands into experiments, Discover, email, support, and mobile digests.
```

This makes the submission look like a product system, not a one-off AI feature.

