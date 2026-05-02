from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import quote

from gumroad_merchant.fixtures import DASHBOARD_DATA, PRODUCTS
from gumroad_merchant.help_corpus import HELP_CORPUS_VERSION, HELP_DOCS, iter_help_chunks


SNAPSHOT_ID = "seeded-demo"
REFUND_OPS_VERSION = "refund-ops-v1"


@dataclass(frozen=True)
class SnapshotStatus:
    refreshed: bool
    source: str
    source_hash: str
    product_count: int
    traffic_source_rows: int
    customer_sale_rows: int
    refreshed_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "refreshed": self.refreshed,
            "source": self.source,
            "source_hash": self.source_hash,
            "product_count": self.product_count,
            "traffic_source_rows": self.traffic_source_rows,
            "customer_sale_rows": self.customer_sale_rows,
            "refreshed_at": self.refreshed_at,
        }


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fixture_snapshot_hash() -> str:
    payload = json.dumps(
        {
            "products": PRODUCTS,
            "dashboard": DASHBOARD_DATA,
            "help_corpus_version": HELP_CORPUS_VERSION,
            "help_docs": HELP_DOCS,
            "refund_ops_version": REFUND_OPS_VERSION,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    return sha256(payload.encode("utf-8")).hexdigest()


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    return conn


def connect_readonly(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path).resolve()
    if not path.exists():
        seed_database(path)
    uri = f"file:{quote(str(path), safe='/')}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            creator TEXT NOT NULL,
            category TEXT NOT NULL,
            price_cents INTEGER NOT NULL,
            currency TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            rating REAL NOT NULL,
            review_count INTEGER NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS period_metrics (
            product_id TEXT NOT NULL,
            period TEXT NOT NULL CHECK(period IN ('current', 'previous')),
            views INTEGER NOT NULL,
            sales INTEGER NOT NULL,
            revenue_cents INTEGER NOT NULL,
            refunds INTEGER NOT NULL,
            refund_cents INTEGER NOT NULL,
            discover_impressions INTEGER NOT NULL,
            PRIMARY KEY(product_id, period),
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS traffic_sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            period TEXT NOT NULL CHECK(period IN ('current', 'previous')),
            name TEXT NOT NULL,
            views INTEGER NOT NULL,
            sales INTEGER NOT NULL,
            revenue_cents INTEGER NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS churn_metrics (
            product_id TEXT PRIMARY KEY,
            active_start INTEGER NOT NULL,
            new_subscriptions INTEGER NOT NULL,
            canceled INTEGER NOT NULL,
            previous_active_start INTEGER NOT NULL,
            previous_new_subscriptions INTEGER NOT NULL,
            previous_canceled INTEGER NOT NULL,
            revenue_lost_cents INTEGER NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            country TEXT NOT NULL,
            region TEXT NOT NULL,
            views INTEGER NOT NULL,
            sales INTEGER NOT NULL,
            revenue_cents INTEGER NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS utm_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            source TEXT NOT NULL,
            medium TEXT NOT NULL,
            campaign TEXT NOT NULL,
            destination TEXT NOT NULL,
            clicks INTEGER NOT NULL,
            sales INTEGER NOT NULL,
            revenue_cents INTEGER NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS tracked_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            title TEXT NOT NULL,
            source TEXT NOT NULL,
            medium TEXT NOT NULL,
            campaign TEXT NOT NULL,
            destination TEXT NOT NULL,
            destination_source TEXT NOT NULL DEFAULT 'demo_generated',
            tracking_url TEXT NOT NULL,
            html_link TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('draft', 'active', 'archived')) DEFAULT 'draft',
            clicks INTEGER NOT NULL DEFAULT 0,
            sales INTEGER NOT NULL DEFAULT 0,
            revenue_cents INTEGER NOT NULL DEFAULT 0,
            created_by TEXT NOT NULL DEFAULT 'merchant-agent',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_actions (
            id TEXT PRIMARY KEY,
            action_type TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'applied', 'rejected', 'failed')),
            idempotency_key TEXT NOT NULL UNIQUE,
            product_id TEXT NOT NULL DEFAULT 'all',
            date_range TEXT NOT NULL DEFAULT '30',
            payload_json TEXT NOT NULL,
            result_json TEXT NOT NULL DEFAULT '{}',
            error TEXT,
            created_by TEXT NOT NULL DEFAULT 'merchant-agent',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            applied_at TEXT,
            rejected_at TEXT
        );

        CREATE TABLE IF NOT EXISTS action_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            event_type TEXT NOT NULL,
            note TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(action_id) REFERENCES agent_actions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS customer_sales (
            purchase_id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            buyer_name TEXT NOT NULL,
            buyer_email TEXT NOT NULL,
            do_not_contact INTEGER NOT NULL,
            purchase_date TEXT NOT NULL,
            purchase_time_utc TEXT NOT NULL,
            subtotal_cents INTEGER NOT NULL,
            tax_cents INTEGER NOT NULL,
            sale_price_cents INTEGER NOT NULL,
            fee_cents INTEGER NOT NULL,
            net_total_cents INTEGER NOT NULL,
            state TEXT NOT NULL,
            country TEXT NOT NULL,
            referrer TEXT NOT NULL,
            refunded INTEGER NOT NULL,
            partial_refund_cents INTEGER NOT NULL,
            variant TEXT NOT NULL,
            discount_code TEXT NOT NULL,
            recurring_charge INTEGER NOT NULL,
            recurrence TEXT NOT NULL,
            affiliate TEXT NOT NULL,
            affiliate_commission_cents INTEGER NOT NULL,
            payment_type TEXT NOT NULL,
            discover INTEGER NOT NULL,
            utm_source TEXT NOT NULL,
            utm_medium TEXT NOT NULL,
            utm_campaign TEXT NOT NULL,
            utm_destination TEXT NOT NULL,
            ppp_discounted INTEGER NOT NULL,
            upsold INTEGER NOT NULL,
            sent_abandoned_cart_email INTEGER NOT NULL,
            rating REAL NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS refund_cases (
            case_id TEXT PRIMARY KEY,
            purchase_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            case_type TEXT NOT NULL CHECK(case_type IN ('refund_request', 'voluntary_refund_review', 'chargeback_dispute')),
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            payment_type TEXT NOT NULL,
            source_name TEXT NOT NULL,
            buyer_issue TEXT NOT NULL,
            due_at TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            evidence_score INTEGER NOT NULL,
            recommended_action TEXT NOT NULL,
            buyer_reply TEXT NOT NULL,
            dispute_evidence TEXT NOT NULL,
            audit_note TEXT NOT NULL,
            delivery_evidence TEXT NOT NULL,
            policy_snapshot TEXT NOT NULL,
            timeline_json TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE,
            FOREIGN KEY(purchase_id) REFERENCES customer_sales(purchase_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS refund_audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES refund_cases(case_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS analytics_snapshots (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            product_count INTEGER NOT NULL,
            traffic_source_rows INTEGER NOT NULL,
            customer_sale_rows INTEGER NOT NULL,
            refreshed_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS help_docs (
            doc_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            category TEXT NOT NULL,
            source_type TEXT NOT NULL,
            seeded_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS help_doc_chunks (
            chunk_id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            section_id TEXT NOT NULL,
            title TEXT NOT NULL,
            section_heading TEXT NOT NULL,
            url TEXT NOT NULL,
            category TEXT NOT NULL,
            source_type TEXT NOT NULL,
            content TEXT NOT NULL,
            example_questions_json TEXT NOT NULL,
            FOREIGN KEY(doc_id) REFERENCES help_docs(doc_id) ON DELETE CASCADE
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS help_doc_chunks_fts
        USING fts5(
            chunk_id UNINDEXED,
            title,
            section_heading,
            content,
            category UNINDEXED,
            url UNINDEXED
        );
        """
    )
    ensure_column(conn, "tracked_campaigns", "destination_source", "TEXT NOT NULL DEFAULT 'demo_generated'")
    conn.commit()


def ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def generated_customer_sales(product: dict[str, Any]) -> list[dict[str, Any]]:
    dashboard = DASHBOARD_DATA[product["id"]]
    locations = dashboard["locations"]
    utm_links = dashboard["utm_links"]
    customers = [
        ("Sana Patel", "sana.patel@example.com"),
        ("Luis Moreno", "luis.moreno@example.com"),
        ("Avery Novak", "avery.novak@example.com"),
        ("Noor Williams", "noor.williams@example.com"),
        ("Elena Park", "elena.park@example.com"),
        ("Marcus Bell", "marcus.bell@example.com"),
    ]
    sources = product["current"]["sources"][:6]
    sales: list[dict[str, Any]] = []
    sample_refund_count = round((product["current"]["refunds"] / product["current"]["sales"]) * len(sources)) if product["current"]["sales"] else 0
    for index, source in enumerate(sources):
        location = locations[index % len(locations)]
        utm = utm_links[index % len(utm_links)]
        sale_price_cents = round(source["revenue_cents"] / (source["sales"] or 1))
        fee_cents = round(sale_price_cents * 0.1)
        tax_cents = round(sale_price_cents * 0.06)
        refunded = 1 if index < sample_refund_count else 0
        buyer_name, buyer_email = customers[index % len(customers)]
        affiliate_commission_cents = round(sale_price_cents * 0.2) if index % 4 == 1 else 0
        sales.append(
            {
                "purchase_id": f"demo-{product['id']}-{index + 1}",
                "product_id": product["id"],
                "item_name": product["name"],
                "buyer_name": buyer_name,
                "buyer_email": buyer_email,
                "do_not_contact": 1 if index % 5 == 0 else 0,
                "purchase_date": f"2026-04-{20 + index:02d}",
                "purchase_time_utc": f"{14 + index:02d}:30:00",
                "subtotal_cents": sale_price_cents,
                "tax_cents": tax_cents,
                "sale_price_cents": sale_price_cents,
                "fee_cents": fee_cents,
                "net_total_cents": sale_price_cents - fee_cents,
                "state": location["region"],
                "country": location["country"],
                "referrer": source["name"],
                "refunded": refunded,
                "partial_refund_cents": round(sale_price_cents / 2) if refunded else 0,
                "variant": "standard" if index % 2 == 0 else "extended",
                "discount_code": "LAUNCH10" if index % 3 == 0 else "",
                "recurring_charge": 1 if index % 4 == 0 else 0,
                "recurrence": "Monthly" if index % 4 == 0 else "",
                "affiliate": "partner@example.com" if index % 4 == 1 else "",
                "affiliate_commission_cents": affiliate_commission_cents,
                "payment_type": "PayPal" if index % 3 == 0 else "Card",
                "discover": 1 if "discover" in source["name"].lower() else 0,
                "utm_source": utm["source"],
                "utm_medium": utm["medium"],
                "utm_campaign": utm["campaign"],
                "utm_destination": utm["destination"],
                "ppp_discounted": 1 if index % 5 == 2 else 0,
                "upsold": 1 if index % 4 == 2 else 0,
                "sent_abandoned_cart_email": 1 if index % 3 == 2 else 0,
                "rating": product["rating"],
            }
        )
    return sales


def refund_case_reason(product: dict[str, Any]) -> str:
    reasons = {
        "prod-creator-os": "Expectation mismatch: buyer expected onboarding videos and a setup checklist.",
        "prod-design-kit": "Template scope mismatch: buyer expected a custom implementation service.",
        "prod-audio-pack": "Compatibility mismatch: buyer expected Logic-ready stems instead of WAV and Ableton files.",
        "prod-zine-guide": "Duplicate purchase review: buyer bought twice from direct traffic.",
    }
    return reasons.get(product["id"], "Buyer expectation mismatch before checkout.")


def refund_prevention_copy(product: dict[str, Any], case_type: str) -> tuple[str, str, str]:
    product_name = product["name"]
    if case_type == "chargeback_dispute":
        return (
            "Chargeback dispute",
            (
                f"Compile purchase, delivery, product-page, and support evidence for {product_name}. "
                "Prepare the dispute packet with the required evidence and audit context."
            ),
            (
                "Refund balance evidence note: purchase delivered, product page reviewed, support timeline attached, "
                "and dispute response prepared for manual review."
            ),
        )
    if case_type == "voluntary_refund_review":
        return (
            "Refund review",
            (
                f"Offer a support-first resolution for {product_name}: clarify access, include setup help, "
                "and approve a refund only if the buyer still cannot use the product."
            ),
            (
                "Refund request reviewed with purchase, delivery, support, and product-page context. "
                "No automatic refund was issued."
            ),
        )
    return (
        "Refund request",
        (
            f"Respond with the included-file list, compatibility notes, and support path for {product_name}; "
            "keep the refund decision manual."
        ),
        (
            "Buyer refund request triaged with purchase facts, delivery evidence, and policy context. "
            "Awaiting manual decision."
        ),
    )


def generated_refund_cases(product: dict[str, Any], sales: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not sales or not product["current"]["sales"]:
        return []
    refund_rate = product["current"]["refunds"] / product["current"]["sales"]
    if product["current"]["refunds"] <= 0 and refund_rate < 0.04:
        return []

    refunded_sales = [sale for sale in sales if sale["refunded"]] or sales
    templates: list[tuple[str, str, int]] = []
    if product["current"]["refunds"] > 0:
        templates.append(("refund_request", "needs_review", 0))
    if product["current"]["refunds"] >= 2 or refund_rate >= 0.06:
        templates.append(("chargeback_dispute", "evidence_due", 1))
    if product["current"]["refunds"] >= 3:
        templates.append(("voluntary_refund_review", "reply_drafted", 2))

    cases: list[dict[str, Any]] = []
    for index, (case_type, status, sale_index) in enumerate(templates, start=1):
        sale = refunded_sales[sale_index % len(refunded_sales)]
        title, recommended_action, audit_note = refund_prevention_copy(product, case_type)
        amount_cents = sale["sale_price_cents"] if case_type == "chargeback_dispute" else max(sale["partial_refund_cents"], round(sale["sale_price_cents"] / 2))
        risk_score = min(96, round(refund_rate * 720) + 24 + (8 if sale["discover"] else 0) + (6 if case_type == "chargeback_dispute" else 0))
        payment_type = "Card" if case_type == "chargeback_dispute" else sale["payment_type"]
        evidence_score = min(94, 62 + (10 if payment_type == "Card" else 5) + (8 if sale["utm_campaign"] else 0) + (6 if sale["refunded"] else 0))
        case_id = f"refund-{product['id']}-{index}"
        policy_snapshot = (
            "Refunds and chargebacks can affect payout balance. Chargebacks are payment disputes, "
            "not normal Gumroad refund requests, and evidence must be reviewed before submission."
        )
        delivery_evidence = (
            f"Purchase {sale['purchase_id']} was recorded on {sale['purchase_date']} at "
            f"{sale['purchase_time_utc']} UTC with product access available after checkout."
        )
        timeline = [
            {"label": "Purchase", "value": f"{sale['purchase_date']} {sale['purchase_time_utc']} UTC"},
            {"label": "Access", "value": "Download access created after checkout"},
            {"label": "Case opened", "value": f"2026-04-{23 + index:02d}"},
            {"label": "Due", "value": f"2026-04-{27 + index:02d}"},
        ]
        evidence = [
            {"label": "Purchase record", "status": "ready", "detail": sale["purchase_id"]},
            {"label": "Delivery/access proof", "status": "ready", "detail": "Access event present in seeded demo facts"},
            {"label": "Product page promise", "status": "review", "detail": "Compare buyer issue with included files and compatibility copy"},
            {"label": "Support contact", "status": "review", "detail": "Attach the support thread before dispute submission"},
        ]
        buyer_reply = (
            f"Thanks for reaching out. I checked your {product['name']} purchase and can help with the issue before we make a refund decision. "
            f"The product includes the files described on the checkout page; based on your note, the likely issue is: {refund_case_reason(product)} "
            "Reply with what you were trying to do and I will either help resolve it or review the refund request manually."
        )
        dispute_evidence = (
            f"{title} evidence packet for {product['name']}: purchase {sale['purchase_id']}, "
            f"{payment_type} payment, {sale['referrer']} source, {delivery_evidence} "
            f"Buyer issue: {refund_case_reason(product)} Recommended action: {recommended_action}"
        )
        cases.append(
            {
                "case_id": case_id,
                "purchase_id": sale["purchase_id"],
                "product_id": product["id"],
                "case_type": case_type,
                "status": status,
                "reason": refund_case_reason(product),
                "amount_cents": amount_cents,
                "payment_type": payment_type,
                "source_name": sale["referrer"],
                "buyer_issue": refund_case_reason(product),
                "due_at": f"2026-04-{27 + index:02d}T17:00:00+00:00",
                "risk_score": risk_score,
                "evidence_score": evidence_score,
                "recommended_action": recommended_action,
                "buyer_reply": buyer_reply,
                "dispute_evidence": dispute_evidence,
                "audit_note": audit_note,
                "delivery_evidence": delivery_evidence,
                "policy_snapshot": policy_snapshot,
                "timeline_json": json.dumps(timeline, ensure_ascii=True),
                "evidence_json": json.dumps(evidence, ensure_ascii=True),
                "created_at": f"2026-04-{22 + index:02d}T15:00:00+00:00",
            }
        )
    return cases


def generated_refund_audit_events(refund_case: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "case_id": refund_case["case_id"],
            "actor": "Gumroad Merchant",
            "action": "case_detected",
            "amount_cents": refund_case["amount_cents"],
            "note": f"Refund Ops detected {refund_case['case_type'].replace('_', ' ')} from seeded purchase facts.",
            "created_at": refund_case["created_at"],
        },
        {
            "case_id": refund_case["case_id"],
            "actor": "Gumroad Merchant",
            "action": "review_packet_prepared",
            "amount_cents": refund_case["amount_cents"],
            "note": refund_case["audit_note"],
            "created_at": refund_case["due_at"],
        },
    ]


def seed_database(db_path: Path | str) -> None:
    conn = connect(db_path)
    try:
        ensure_schema(conn)
        conn.executescript(
            """
            DELETE FROM analytics_snapshots;
            DELETE FROM help_doc_chunks_fts;
            DELETE FROM help_doc_chunks;
            DELETE FROM help_docs;
            DELETE FROM refund_audit_events;
            DELETE FROM refund_cases;
            DELETE FROM customer_sales;
            DELETE FROM utm_links;
            DELETE FROM locations;
            DELETE FROM churn_metrics;
            DELETE FROM traffic_sources;
            DELETE FROM period_metrics;
            DELETE FROM products;
            """
        )
        for product in PRODUCTS:
            conn.execute(
                """
                INSERT INTO products(
                    id, name, creator, category, price_cents, currency,
                    tags_json, rating, review_count, description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product["id"],
                    product["name"],
                    product["creator"],
                    product["category"],
                    product["price_cents"],
                    product["currency"],
                    json.dumps(product["tags"], ensure_ascii=True),
                    product["rating"],
                    product["review_count"],
                    product["description"],
                ),
            )
            for period in ("current", "previous"):
                metrics = product[period]
                conn.execute(
                    """
                    INSERT INTO period_metrics(
                        product_id, period, views, sales, revenue_cents, refunds,
                        refund_cents, discover_impressions
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product["id"],
                        period,
                        metrics["views"],
                        metrics["sales"],
                        metrics["revenue_cents"],
                        metrics["refunds"],
                        metrics["refund_cents"],
                        metrics["discover_impressions"],
                    ),
                )
                for source in metrics["sources"]:
                    conn.execute(
                        """
                        INSERT INTO traffic_sources(product_id, period, name, views, sales, revenue_cents)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            product["id"],
                            period,
                            source["name"],
                            source["views"],
                            source["sales"],
                            source["revenue_cents"],
                        ),
                    )
            dashboard = DASHBOARD_DATA[product["id"]]
            churn = dashboard["churn"]
            conn.execute(
                """
                INSERT INTO churn_metrics(
                    product_id, active_start, new_subscriptions, canceled,
                    previous_active_start, previous_new_subscriptions,
                    previous_canceled, revenue_lost_cents
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product["id"],
                    churn["active_start"],
                    churn["new_subscriptions"],
                    churn["canceled"],
                    churn["previous_active_start"],
                    churn["previous_new_subscriptions"],
                    churn["previous_canceled"],
                    churn["revenue_lost_cents"],
                ),
            )
            for location in dashboard["locations"]:
                conn.execute(
                    """
                    INSERT INTO locations(product_id, country, region, views, sales, revenue_cents)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product["id"],
                        location["country"],
                        location["region"],
                        location["views"],
                        location["sales"],
                        location["revenue_cents"],
                    ),
                )
            for link in dashboard["utm_links"]:
                conn.execute(
                    """
                    INSERT INTO utm_links(
                        product_id, source, medium, campaign, destination,
                        clicks, sales, revenue_cents
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        product["id"],
                        link["source"],
                        link["medium"],
                        link["campaign"],
                        link["destination"],
                        link["clicks"],
                        link["sales"],
                        link["revenue_cents"],
                    ),
                )
            sales = generated_customer_sales(product)
            for sale in sales:
                conn.execute(
                    """
                    INSERT INTO customer_sales(
                        purchase_id, product_id, item_name, buyer_name, buyer_email,
                        do_not_contact, purchase_date, purchase_time_utc,
                        subtotal_cents, tax_cents, sale_price_cents, fee_cents,
                        net_total_cents, state, country, referrer, refunded,
                        partial_refund_cents, variant, discount_code, recurring_charge,
                        recurrence, affiliate, affiliate_commission_cents, payment_type,
                        discover, utm_source, utm_medium, utm_campaign, utm_destination,
                        ppp_discounted, upsold, sent_abandoned_cart_email, rating
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        sale["purchase_id"],
                        sale["product_id"],
                        sale["item_name"],
                        sale["buyer_name"],
                        sale["buyer_email"],
                        sale["do_not_contact"],
                        sale["purchase_date"],
                        sale["purchase_time_utc"],
                        sale["subtotal_cents"],
                        sale["tax_cents"],
                        sale["sale_price_cents"],
                        sale["fee_cents"],
                        sale["net_total_cents"],
                        sale["state"],
                        sale["country"],
                        sale["referrer"],
                        sale["refunded"],
                        sale["partial_refund_cents"],
                        sale["variant"],
                        sale["discount_code"],
                        sale["recurring_charge"],
                        sale["recurrence"],
                        sale["affiliate"],
                        sale["affiliate_commission_cents"],
                        sale["payment_type"],
                        sale["discover"],
                        sale["utm_source"],
                        sale["utm_medium"],
                        sale["utm_campaign"],
                        sale["utm_destination"],
                        sale["ppp_discounted"],
                        sale["upsold"],
                        sale["sent_abandoned_cart_email"],
                        sale["rating"],
                    ),
                )
            for refund_case in generated_refund_cases(product, sales):
                conn.execute(
                    """
                    INSERT INTO refund_cases(
                        case_id, purchase_id, product_id, case_type, status, reason,
                        amount_cents, payment_type, source_name, buyer_issue, due_at,
                        risk_score, evidence_score, recommended_action, buyer_reply,
                        dispute_evidence, audit_note, delivery_evidence, policy_snapshot,
                        timeline_json, evidence_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        refund_case["case_id"],
                        refund_case["purchase_id"],
                        refund_case["product_id"],
                        refund_case["case_type"],
                        refund_case["status"],
                        refund_case["reason"],
                        refund_case["amount_cents"],
                        refund_case["payment_type"],
                        refund_case["source_name"],
                        refund_case["buyer_issue"],
                        refund_case["due_at"],
                        refund_case["risk_score"],
                        refund_case["evidence_score"],
                        refund_case["recommended_action"],
                        refund_case["buyer_reply"],
                        refund_case["dispute_evidence"],
                        refund_case["audit_note"],
                        refund_case["delivery_evidence"],
                        refund_case["policy_snapshot"],
                        refund_case["timeline_json"],
                        refund_case["evidence_json"],
                        refund_case["created_at"],
                    ),
                )
                for event in generated_refund_audit_events(refund_case):
                    conn.execute(
                        """
                        INSERT INTO refund_audit_events(
                            case_id, actor, action, amount_cents, note, created_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event["case_id"],
                            event["actor"],
                            event["action"],
                            event["amount_cents"],
                            event["note"],
                            event["created_at"],
                        ),
                    )
        seeded_at = now_iso()
        for doc in HELP_DOCS:
            conn.execute(
                """
                INSERT INTO help_docs(doc_id, title, url, category, source_type, seeded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    doc["doc_id"],
                    doc["title"],
                    doc["url"],
                    doc["category"],
                    doc["source_type"],
                    seeded_at,
                ),
            )
        for chunk in iter_help_chunks():
            conn.execute(
                """
                INSERT INTO help_doc_chunks(
                    chunk_id, doc_id, section_id, title, section_heading, url,
                    category, source_type, content, example_questions_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk["chunk_id"],
                    chunk["doc_id"],
                    chunk["section_id"],
                    chunk["title"],
                    chunk["section_heading"],
                    chunk["url"],
                    chunk["category"],
                    chunk["source_type"],
                    chunk["content"],
                    json.dumps(chunk["example_questions"], ensure_ascii=True),
                ),
            )
            conn.execute(
                """
                INSERT INTO help_doc_chunks_fts(chunk_id, title, section_heading, content, category, url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk["chunk_id"],
                    chunk["title"],
                    chunk["section_heading"],
                    chunk["content"],
                    chunk["category"],
                    chunk["url"],
                ),
            )
        conn.execute(
            """
            INSERT INTO analytics_snapshots(
                id, source, source_hash, product_count,
                traffic_source_rows, customer_sale_rows, refreshed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                SNAPSHOT_ID,
                "seeded local demo fixtures",
                fixture_snapshot_hash(),
                len(PRODUCTS),
                sum(len(product["current"]["sources"]) + len(product["previous"]["sources"]) for product in PRODUCTS),
                sum(len(product["current"]["sources"][:6]) for product in PRODUCTS),
                now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def current_snapshot_status(db_path: Path | str, refreshed: bool = False) -> SnapshotStatus:
    with closing(connect(db_path)) as conn:
        ensure_schema(conn)
        row = conn.execute(
            """
            SELECT source, source_hash, product_count, traffic_source_rows,
                   customer_sale_rows, refreshed_at
            FROM analytics_snapshots
            WHERE id = ?
            """,
            (SNAPSHOT_ID,),
        ).fetchone()
        if not row:
            return SnapshotStatus(
                refreshed=refreshed,
                source="none",
                source_hash="",
                product_count=0,
                traffic_source_rows=0,
                customer_sale_rows=0,
                refreshed_at="",
            )
        return SnapshotStatus(
            refreshed=refreshed,
            source=row["source"],
            source_hash=row["source_hash"],
            product_count=int(row["product_count"]),
            traffic_source_rows=int(row["traffic_source_rows"]),
            customer_sale_rows=int(row["customer_sale_rows"]),
            refreshed_at=row["refreshed_at"],
        )


def expected_seeded_counts() -> dict[str, int]:
    customer_sales = [sale for product in PRODUCTS for sale in generated_customer_sales(product)]
    refund_cases = [
        refund_case
        for product in PRODUCTS
        for refund_case in generated_refund_cases(product, generated_customer_sales(product))
    ]
    return {
        "products": len(PRODUCTS),
        "period_metrics": len(PRODUCTS) * 2,
        "traffic_sources": sum(
            len(product["current"]["sources"]) + len(product["previous"]["sources"]) for product in PRODUCTS
        ),
        "customer_sales": len(customer_sales),
        "refund_cases": len(refund_cases),
        "help_docs": len(HELP_DOCS),
        "help_doc_chunks": len(iter_help_chunks()),
    }


def seeded_tables_are_complete(db_path: Path | str) -> bool:
    expected = expected_seeded_counts()
    try:
        with closing(connect(db_path)) as conn:
            ensure_schema(conn)
            for table, expected_count in expected.items():
                row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
                if int(row["n"] if row else 0) != expected_count:
                    return False
    except sqlite3.DatabaseError:
        return False
    return True


def refresh_database(db_path: Path | str, force: bool = False) -> SnapshotStatus:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    current_hash = fixture_snapshot_hash()
    status = current_snapshot_status(path)
    should_refresh = (
        force
        or not status.source_hash
        or status.source_hash != current_hash
        or not seeded_tables_are_complete(path)
    )
    if should_refresh:
        seed_database(path)
        return current_snapshot_status(path, refreshed=True)
    return status


def table_count(db_path: Path | str, table: str) -> int:
    with closing(connect_readonly(db_path)) as conn:
        row = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()
        return int(row["n"] if row else 0)
