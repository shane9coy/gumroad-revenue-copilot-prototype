# Money Ops Help-Docs Smoke Conversation

Generated: 2026-04-30T17:49:06.216368+00:00
Mode: deterministic SQL/help-doc fallback via `run_agent_chat(use_fallback=True)`
Product context: `all`
Date range: `30`
Snapshot refreshed: `True`

## Goal

Exercise Gumroad help-doc retrieval for chargebacks, refund/balance impact, payouts, processor context, and fees.

## Checks

- `message_count`: `6`
- `target_range_5_to_10`: `True`
- `assistant_turns_non_empty`: `True`
- `all_turns_have_citations`: `True`
- `deterministic_fallback_used`: `True`
- `passed`: `True`

## Transcript

### Turn 1

**User**

Explain what the loaded Gumroad docs say about chargebacks versus normal refunds. Include what creators can and cannot control, and include source URLs.

**Assistant**

From the loaded Gumroad docs:
- Credits, refunds, chargebacks, and negative balance: The payouts dashboard article says credits are one-off balance adjustments and can include winning a chargeback, VAT refund compensation for connected Stripe or PayPal sales, or backtax collection. It also says Gumroad's payment processor may debit the creator's bank account if the Gumroad balance goes negative because of refunds or chargebacks.
- Start selling docs: The Help Center index lists creator-selling articles under Start selling, including Issuing a refund, Testing a purchase, The sales analytics dashboard, Gumroad Discover, Chargebacks on Gumroad, The sales dashboard, Purchasing Power Parity, Upsells, related products, custom refund policy, and tipping.
- Dispute timeline and customer export: The article says Gumroad starts the dispute process, submits available evidence, and waits for the card provider's decision. Chargebacks appear like full refunds and show in customer exports under the Disputed column.

Sources:
The payouts dashboard - Credits, refunds, chargebacks, and negative balance: https://gumroad.com/help/article/269-balance-page.html
Gumroad Help Center section map - Start selling docs: https://gumroad.com/help/article/226-report-a-creator.html
Chargebacks on Gumroad - Dispute timeline and customer export: https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks.html

**Citations**

- help_doc - The payouts dashboard - Credits, refunds, chargebacks, and negative balance - https://gumroad.com/help/article/269-balance-page.html
- help_doc - Gumroad Help Center section map - Start selling docs - https://gumroad.com/help/article/226-report-a-creator.html
- help_doc - Chargebacks on Gumroad - Dispute timeline and customer export - https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks.html

Model: `gpt-5-nano` · Fallback: `True`

### Turn 2

**User**

If refunds and chargebacks push a creator balance negative, what payout or balance docs should we cite, and where should the operator look next?

**Assistant**

From the loaded Gumroad docs:
- Credits, refunds, chargebacks, and negative balance: The payouts dashboard article says credits are one-off balance adjustments and can include winning a chargeback, VAT refund compensation for connected Stripe or PayPal sales, or backtax collection. It also says Gumroad's payment processor may debit the creator's bank account if the Gumroad balance goes negative because of refunds or chargebacks.
- Start selling docs: The Help Center index lists creator-selling articles under Start selling, including Issuing a refund, Testing a purchase, The sales analytics dashboard, Gumroad Discover, Chargebacks on Gumroad, The sales dashboard, Purchasing Power Parity, Upsells, related products, custom refund policy, and tipping.
- Dispute timeline and customer export: The article says Gumroad starts the dispute process, submits available evidence, and waits for the card provider's decision. Chargebacks appear like full refunds and show in customer exports under the Disputed column.

Sources:
The payouts dashboard - Credits, refunds, chargebacks, and negative balance: https://gumroad.com/help/article/269-balance-page.html
Gumroad Help Center section map - Start selling docs: https://gumroad.com/help/article/226-report-a-creator.html
Chargebacks on Gumroad - Dispute timeline and customer export: https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks.html

**Citations**

- help_doc - The payouts dashboard - Credits, refunds, chargebacks, and negative balance - https://gumroad.com/help/article/269-balance-page.html
- help_doc - Gumroad Help Center section map - Start selling docs - https://gumroad.com/help/article/226-report-a-creator.html
- help_doc - Chargebacks on Gumroad - Dispute timeline and customer export - https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks.html

Model: `gpt-5-nano` · Fallback: `True`

### Turn 3

**User**

What are Gumroad fees for direct sales versus Discover, and how should that affect a Refund Ops product decision? Keep policy claims sourced.

**Assistant**

From the loaded Gumroad docs:
- Profile and direct-link transaction fees: Gumroad's pricing page says profile sales and direct-link sales use a 10% plus $0.50 per-transaction fee. The page also says Gumroad does not charge a monthly fee; fees are deducted from each sale.
- Credits, refunds, chargebacks, and negative balance: The payouts dashboard article says credits are one-off balance adjustments and can include winning a chargeback, VAT refund compensation for connected Stripe or PayPal sales, or backtax collection. It also says Gumroad's payment processor may debit the creator's bank account if the Gumroad balance goes negative because of refunds or chargebacks.
- Discover marketplace transaction fees: Gumroad's pricing page lists a 30% per-transaction fee when a new customer finds and buys through the Gumroad Discover marketplace.

Sources:
Gumroad pricing, fees, and Merchant of Record taxes - Profile and direct-link transaction fees: https://gumroad.com/pricing
The payouts dashboard - Credits, refunds, chargebacks, and negative balance: https://gumroad.com/help/article/269-balance-page.html
Gumroad pricing, fees, and Merchant of Record taxes - Discover marketplace transaction fees: https://gumroad.com/pricing

**Citations**

- help_doc - Gumroad pricing, fees, and Merchant of Record taxes - Profile and direct-link transaction fees - https://gumroad.com/pricing
- help_doc - The payouts dashboard - Credits, refunds, chargebacks, and negative balance - https://gumroad.com/help/article/269-balance-page.html
- help_doc - Gumroad pricing, fees, and Merchant of Record taxes - Discover marketplace transaction fees - https://gumroad.com/pricing

Model: `gpt-5-nano` · Fallback: `True`
