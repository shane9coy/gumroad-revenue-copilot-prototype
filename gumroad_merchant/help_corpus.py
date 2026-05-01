from __future__ import annotations

from typing import Any


HELP_CORPUS_VERSION = "gumroad-help-money-ops-2026-04-30"
DEFAULT_HELP_CATEGORY = "money_ops"


HELP_DOCS: list[dict[str, Any]] = [
    {
        "doc_id": "pricing-fees-and-taxes",
        "title": "Gumroad pricing, fees, and Merchant of Record taxes",
        "url": "https://gumroad.com/pricing",
        "category": "money_ops",
        "source_type": "official_pricing_page",
        "sections": [
            {
                "section_id": "direct-sales-fees",
                "heading": "Profile and direct-link transaction fees",
                "content": (
                    "Gumroad's pricing page says profile sales and direct-link sales use a "
                    "10% plus $0.50 per-transaction fee. The page also says Gumroad does not "
                    "charge a monthly fee; fees are deducted from each sale."
                ),
                "example_questions": [
                    "What are Gumroad's fees?",
                    "Is there a monthly fee?",
                    "How much does Gumroad take on direct sales?",
                ],
            },
            {
                "section_id": "discover-marketplace-fees",
                "heading": "Discover marketplace transaction fees",
                "content": (
                    "Gumroad's pricing page lists a 30% per-transaction fee when a new customer "
                    "finds and buys through the Gumroad Discover marketplace."
                ),
                "example_questions": [
                    "What does Gumroad Discover cost?",
                    "Why is the Discover fee higher?",
                    "Is Discover priced differently from direct sales?",
                ],
            },
            {
                "section_id": "merchant-of-record-taxes",
                "heading": "Merchant of Record and tax handling",
                "content": (
                    "The pricing page says Gumroad became the Merchant of Record on January 1, "
                    "2025, and handles sales tax collection and remittance where Gumroad has "
                    "merchant-of-record tax obligations. It also notes that old creator tax "
                    "settings are automatically disabled because Gumroad handles tax collection."
                ),
                "example_questions": [
                    "Does Gumroad handle sales tax?",
                    "What changed with Merchant of Record?",
                    "Do I still need product tax settings?",
                ],
            },
        ],
    },
    {
        "doc_id": "payouts-dashboard",
        "title": "The payouts dashboard",
        "url": "https://gumroad.com/help/article/269-balance-page.html",
        "category": "money_ops",
        "source_type": "official_help_article",
        "sections": [
            {
                "section_id": "payouts-dashboard-navigation",
                "heading": "Navigating the payouts dashboard",
                "content": (
                    "The payouts dashboard shows payout periods with sale date range, total "
                    "sales, deductions, and net payout amount. The article says paid payout "
                    "reports can be exported as CSV from the payout row download button, and "
                    "multiple payout reports can be downloaded from the top-right download button."
                ),
                "example_questions": [
                    "Where do I find payout reports?",
                    "Can I export payout activity?",
                    "Why does the payout page show different timing from analytics?",
                ],
            },
            {
                "section_id": "paypal-payouts",
                "heading": "PayPal payouts",
                "content": (
                    "The payouts dashboard article says that when a PayPal account is connected "
                    "from payment settings, the net sale amount goes immediately to PayPal. Those "
                    "PayPal amounts appear in the payout table and are subtracted from total sales "
                    "because they have already been paid out."
                ),
                "example_questions": [
                    "How do PayPal payouts show up?",
                    "Why is PayPal subtracted from my payout table?",
                    "Do PayPal sales go to my payout balance?",
                ],
            },
            {
                "section_id": "credits-refunds-chargebacks",
                "heading": "Credits, refunds, chargebacks, and negative balance",
                "content": (
                    "The payouts dashboard article says credits are one-off balance adjustments "
                    "and can include winning a chargeback, VAT refund compensation for connected "
                    "Stripe or PayPal sales, or backtax collection. It also says Gumroad's payment "
                    "processor may debit the creator's bank account if the Gumroad balance goes "
                    "negative because of refunds or chargebacks."
                ),
                "example_questions": [
                    "How do refunds affect payout balance?",
                    "What happens if refunds make my balance negative?",
                    "Where do chargeback credits appear?",
                ],
            },
            {
                "section_id": "payout-period",
                "heading": "Understanding payout timing",
                "content": (
                    "The payouts dashboard article says each payout covers sales made up to the "
                    "previous Friday, and net sale amounts sit in balance for at least seven days. "
                    "If a payday is Friday the 14th, the payout covers sales up to midnight on "
                    "Friday the 7th, UTC; later sales roll into the following payout."
                ),
                "example_questions": [
                    "When do I get paid?",
                    "Why did this week's sale not pay out yet?",
                    "How does the Friday payout period work?",
                ],
            },
            {
                "section_id": "account-under-review",
                "heading": "Account under review",
                "content": (
                    "The payouts dashboard article says recently started sellers or accounts with "
                    "irregularities may see an account-under-review state. The payout date appears "
                    "after account review is complete."
                ),
                "example_questions": [
                    "Why is my payout delayed for review?",
                    "Why do I not see a payout date?",
                    "What does account under review mean on payouts?",
                ],
            },
        ],
    },
    {
        "doc_id": "chargebacks",
        "title": "Chargebacks on Gumroad",
        "url": "https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks.html",
        "category": "money_ops",
        "source_type": "official_help_article",
        "sections": [
            {
                "section_id": "chargeback-definition",
                "heading": "What a chargeback is",
                "content": (
                    "Gumroad's chargeback article explains that a chargeback is a card-provider "
                    "reversal initiated by a customer, not a normal Gumroad refund request. The "
                    "creator covers the reversed amount and payment-processing fees, while Gumroad "
                    "returns its platform fee."
                ),
                "example_questions": [
                    "What is a chargeback?",
                    "Is a chargeback the same as a refund?",
                    "Who covers chargeback costs?",
                ],
            },
            {
                "section_id": "stripe-paypal-connect-disputes",
                "heading": "Stripe Connect and PayPal Connect disputes",
                "content": (
                    "The chargeback article says Stripe Connect and PayPal Connect disputes are "
                    "the creator's responsibility because the customer paid directly to the connected "
                    "account. For those purchases, the creator must fight the dispute through the "
                    "corresponding Stripe or PayPal account."
                ),
                "example_questions": [
                    "Do I handle Stripe Connect chargebacks?",
                    "Do PayPal Connect disputes go through PayPal?",
                    "Who fights a connected-account dispute?",
                ],
            },
            {
                "section_id": "chargeback-timeline-and-export",
                "heading": "Dispute timeline and customer export",
                "content": (
                    "The article says Gumroad starts the dispute process, submits available evidence, "
                    "and waits for the card provider's decision. Chargebacks appear like full refunds "
                    "and show in customer exports under the Disputed column."
                ),
                "example_questions": [
                    "Where do chargebacks appear in exports?",
                    "Can Gumroad tell me when a dispute will finish?",
                    "What happens after a chargeback starts?",
                ],
            },
            {
                "section_id": "lower-chargeback-rate",
                "heading": "How to lower chargeback rate",
                "content": (
                    "The article says payouts are automatically paused when chargeback rate exceeds "
                    "1%. It recommends clear product descriptions, transparent pricing and billing, "
                    "reliable delivery, clear refund policies, responsive support, avoiding misleading "
                    "marketing, and keeping proof of delivery and communications."
                ),
                "example_questions": [
                    "How can I lower chargebacks?",
                    "Why would payouts pause because of chargebacks?",
                    "What should I change on the product page to reduce disputes?",
                ],
            },
        ],
    },
    {
        "doc_id": "account-suspension-and-processor-review",
        "title": "Account suspension FAQ",
        "url": "https://gumroad.com/help/article/160-suspension.html",
        "category": "money_ops",
        "source_type": "official_help_article",
        "sections": [
            {
                "section_id": "first-payout-review",
                "heading": "Review before first payout",
                "content": (
                    "The account suspension FAQ says accounts are reviewed before the first payout. "
                    "If Gumroad reviews and verifies the account, the first payout should arrive "
                    "within seven days of that review."
                ),
                "example_questions": [
                    "Why is my first payout under review?",
                    "When do I get my first payout after review?",
                    "What does payout review mean?",
                ],
            },
            {
                "section_id": "high-risk-sales-and-chargebacks",
                "heading": "High-risk sales and high chargebacks",
                "content": (
                    "The FAQ says high-risk or fraudulent sales can block payouts. It also says "
                    "accounts with high chargeback amounts can be categorized as high risk, which "
                    "can force Gumroad to suspend sales and hold the balance for 30 to 45 days to "
                    "allow for additional chargebacks."
                ),
                "example_questions": [
                    "Can high chargebacks stop payouts?",
                    "Why would Gumroad hold my balance?",
                    "What happens with high-risk sales?",
                ],
            },
            {
                "section_id": "stripe-paypal-processor-review",
                "heading": "Stripe and PayPal processor approval",
                "content": (
                    "The FAQ says entering payout information sets up an account with Stripe and/or "
                    "PayPal. Those processors also review account risk. If they will not allow the "
                    "account to be paid, Gumroad says it has no way to send the money through that "
                    "processor path."
                ),
                "example_questions": [
                    "Do I need Stripe or PayPal to get paid?",
                    "Why is Stripe or PayPal reviewing my account?",
                    "Can processor approval block payout?",
                ],
            },
        ],
    },
    {
        "doc_id": "help-center-section-map",
        "title": "Gumroad Help Center section map",
        "url": "https://gumroad.com/help/article/226-report-a-creator.html",
        "category": "money_ops",
        "source_type": "official_help_center_index",
        "sections": [
            {
                "section_id": "start-selling-section",
                "heading": "Start selling docs",
                "content": (
                    "The Help Center index lists creator-selling articles under Start selling, "
                    "including Issuing a refund, Testing a purchase, The sales analytics dashboard, "
                    "Gumroad Discover, Chargebacks on Gumroad, The sales dashboard, Purchasing "
                    "Power Parity, Upsells, related products, custom refund policy, and tipping."
                ),
                "example_questions": [
                    "Where do I find the sales analytics dashboard docs?",
                    "Where can I learn about refunds?",
                    "Where are Discover and chargeback docs?",
                ],
            },
            {
                "section_id": "get-paid-section",
                "heading": "Get paid docs",
                "content": (
                    "The Help Center index lists money articles under Get paid, including Getting "
                    "paid by Gumroad, forms 1099-K and 1099-MISC, currency, Gumroad's fees, sales "
                    "tax, account suspension, fraud, payout methods, the payouts dashboard, PayPal "
                    "checkout, payout delays, fraudulent purchases, indirect taxes on Discover, "
                    "Stripe connection, and Singapore GST."
                ),
                "example_questions": [
                    "Where can I find payout delay docs?",
                    "Where are Gumroad fee docs?",
                    "Where are Stripe and PayPal docs?",
                ],
            },
        ],
    },
]


def iter_help_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for doc in HELP_DOCS:
        for section in doc["sections"]:
            chunk_id = f"{doc['doc_id']}::{section['section_id']}"
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "url": doc["url"],
                    "category": doc["category"],
                    "source_type": doc["source_type"],
                    "section_id": section["section_id"],
                    "section_heading": section["heading"],
                    "content": section["content"],
                    "example_questions": list(section["example_questions"]),
                }
            )
    return chunks
