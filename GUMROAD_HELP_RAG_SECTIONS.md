# Gumroad Help-Docs RAG Sections

## Corpus summary

Gumroad Merchant now seeds a local, read-only SQLite FTS corpus for official Gumroad creator money-ops questions. The v1 corpus is lexical/BM25 only: no embeddings, no live web lookup, and no production Gumroad data.

Corpus version: `gumroad-help-money-ops-2026-04-30`

Primary supported areas:

- pricing and fees
- payouts dashboard and payout timing
- refunds, chargebacks, credits, and payout-balance impact
- Stripe, PayPal, and payment-processor references
- sales tax and Merchant of Record notes
- Help Center navigation for related creator money-ops docs

## Included URLs

| Doc ID | Official URL | Category | Purpose |
| --- | --- | --- | --- |
| `pricing-fees-and-taxes` | https://gumroad.com/pricing | `money_ops` | Pricing, direct fees, Discover fees, Merchant of Record tax notes |
| `payouts-dashboard` | https://gumroad.com/help/article/269-balance-page.html | `money_ops` | Payout dashboard, exports, PayPal payouts, credits, refunds/chargebacks, payout period |
| `chargebacks` | https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks.html | `money_ops` | Chargeback definition, Stripe/PayPal Connect disputes, dispute timeline, chargeback reduction |
| `account-suspension-and-processor-review` | https://gumroad.com/help/article/160-suspension.html | `money_ops` | First payout review, high-risk sales, high chargebacks, Stripe/PayPal processor review |
| `help-center-section-map` | https://gumroad.com/help/article/226-report-a-creator.html | `money_ops` | Help Center section map for Start selling and Get paid docs |

## Section inventory

| Doc ID | Section ID | Section | Example prompts |
| --- | --- | --- | --- |
| `pricing-fees-and-taxes` | `direct-sales-fees` | Profile and direct-link transaction fees | "What are Gumroad's fees?"; "Is there a monthly fee?"; "How much does Gumroad take on direct sales?" |
| `pricing-fees-and-taxes` | `discover-marketplace-fees` | Discover marketplace transaction fees | "What does Gumroad Discover cost?"; "Why is the Discover fee higher?"; "Is Discover priced differently from direct sales?" |
| `pricing-fees-and-taxes` | `merchant-of-record-taxes` | Merchant of Record and tax handling | "Does Gumroad handle sales tax?"; "What changed with Merchant of Record?"; "Do I still need product tax settings?" |
| `payouts-dashboard` | `payouts-dashboard-navigation` | Navigating the payouts dashboard | "Where do I find payout reports?"; "Can I export payout activity?"; "Why does the payout page show different timing from analytics?" |
| `payouts-dashboard` | `paypal-payouts` | PayPal payouts | "How do PayPal payouts show up?"; "Why is PayPal subtracted from my payout table?"; "Do PayPal sales go to my payout balance?" |
| `payouts-dashboard` | `credits-refunds-chargebacks` | Credits, refunds, chargebacks, and negative balance | "How do refunds affect payout balance?"; "What happens if refunds make my balance negative?"; "Where do chargeback credits appear?" |
| `payouts-dashboard` | `payout-period` | Understanding payout timing | "When do I get paid?"; "Why did this week's sale not pay out yet?"; "How does the Friday payout period work?" |
| `payouts-dashboard` | `account-under-review` | Account under review | "Why is my payout delayed for review?"; "Why do I not see a payout date?"; "What does account under review mean on payouts?" |
| `chargebacks` | `chargeback-definition` | What a chargeback is | "What is a chargeback?"; "Is a chargeback the same as a refund?"; "Who covers chargeback costs?" |
| `chargebacks` | `stripe-paypal-connect-disputes` | Stripe Connect and PayPal Connect disputes | "Do I handle Stripe Connect chargebacks?"; "Do PayPal Connect disputes go through PayPal?"; "Who fights a connected-account dispute?" |
| `chargebacks` | `chargeback-timeline-and-export` | Dispute timeline and customer export | "Where do chargebacks appear in exports?"; "Can Gumroad tell me when a dispute will finish?"; "What happens after a chargeback starts?" |
| `chargebacks` | `lower-chargeback-rate` | How to lower chargeback rate | "How can I lower chargebacks?"; "Why would payouts pause because of chargebacks?"; "What should I change on the product page to reduce disputes?" |
| `account-suspension-and-processor-review` | `first-payout-review` | Review before first payout | "Why is my first payout under review?"; "When do I get my first payout after review?"; "What does payout review mean?" |
| `account-suspension-and-processor-review` | `high-risk-sales-and-chargebacks` | High-risk sales and high chargebacks | "Can high chargebacks stop payouts?"; "Why would Gumroad hold my balance?"; "What happens with high-risk sales?" |
| `account-suspension-and-processor-review` | `stripe-paypal-processor-review` | Stripe and PayPal processor approval | "Do I need Stripe or PayPal to get paid?"; "Why is Stripe or PayPal reviewing my account?"; "Can processor approval block payout?" |
| `help-center-section-map` | `start-selling-section` | Start selling docs | "Where do I find the sales analytics dashboard docs?"; "Where can I learn about refunds?"; "Where are Discover and chargeback docs?" |
| `help-center-section-map` | `get-paid-section` | Get paid docs | "Where can I find payout delay docs?"; "Where are Gumroad fee docs?"; "Where are Stripe and PayPal docs?" |

## Source-citation rule

Any Gumroad help/policy answer must cite loaded official docs. In chat responses, Gumroad Merchant should include source URLs inline and return `help_doc` citations with:

- `chunk_id`
- title and section heading
- official source URL

If the policy answer is not in the seeded corpus, the agent must say: "I do not know that from the loaded Gumroad docs." It should not infer a new Gumroad policy from analytics data or model memory.

## Out-of-scope docs for later expansion

- Full refund workflow and custom refund policy article detail
- Full "Getting paid by Gumroad" article detail
- Full "Payout delays" article detail
- Full "Connect your Stripe account to Gumroad" article detail
- PayPal checkout setup article detail
- Country-specific tax articles beyond the pricing-page Merchant of Record note
- Buyer-side purchase, receipt, library, and cancellation docs
- API docs and OAuth docs
- Live help-doc crawling or scheduled refresh
- Embeddings, hybrid BM25+dense retrieval, RRF, or reranking
