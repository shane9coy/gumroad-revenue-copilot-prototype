from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

from gumroad_merchant.database import connect_readonly, row_to_dict


MIN_DESCRIPTION_LENGTH = 90
IDEAL_TAG_COUNT = 4
HIGH_TRAFFIC_VIEWS = 500
MIN_SOURCE_SALES = 5
REFUND_WARNING_RATE = 0.08
DATE_RANGE_SCALES = {"30": 1.0, "90": 2.75, "180": 5.4, "all": 6.4}


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def round_value(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def percent_delta(current: float, previous: float) -> float:
    if previous > 0:
        return (current - previous) / previous
    return 1.0 if current > 0 else 0.0


def format_currency(cents: int, currency: str = "USD") -> str:
    prefix = "$" if currency == "USD" else f"{currency} "
    return f"{prefix}{cents / 100:,.2f}"


def format_percent(value: float) -> str:
    rendered = f"{value * 100:.1f}".rstrip("0").rstrip(".")
    return f"{rendered}%"


def money_payload(cents: int, currency: str = "USD") -> dict[str, Any]:
    return {
        "cents": int(cents),
        "amount": round_value(int(cents) / 100, 2),
        "formatted": format_currency(int(cents), currency),
    }


def date_scale(date_range: str | None) -> float:
    raw = str(date_range or "30")
    if raw in DATE_RANGE_SCALES:
        return DATE_RANGE_SCALES[raw]
    try:
        days = int(raw)
    except (TypeError, ValueError):
        return 1.0
    return max(0.25, min(DATE_RANGE_SCALES["all"], days / 30))


def scale_int(value: int, scale: float) -> int:
    return max(0, round(int(value) * scale))


def product_ids(conn: sqlite3.Connection, product_id: str = "all") -> list[str]:
    if product_id and product_id != "all":
        row = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        return [row["id"]] if row else []
    rows = conn.execute("SELECT id FROM products ORDER BY id").fetchall()
    return [row["id"] for row in rows]


def load_products(conn: sqlite3.Connection, ids: list[str]) -> list[dict[str, Any]]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM products WHERE id IN ({placeholders}) ORDER BY id",
        ids,
    ).fetchall()
    products = []
    for row in rows:
        item = row_to_dict(row)
        item["tags"] = json.loads(item.pop("tags_json") or "[]")
        products.append(item)
    return products


def load_period(conn: sqlite3.Connection, ids: list[str], period: str, scale: float) -> dict[str, int]:
    if not ids:
        return {"views": 0, "sales": 0, "revenue_cents": 0, "refunds": 0, "refund_cents": 0, "discover_impressions": 0}
    placeholders = ",".join("?" for _ in ids)
    row = conn.execute(
        f"""
        SELECT
            SUM(views) AS views,
            SUM(sales) AS sales,
            SUM(revenue_cents) AS revenue_cents,
            SUM(refunds) AS refunds,
            SUM(refund_cents) AS refund_cents,
            SUM(discover_impressions) AS discover_impressions
        FROM period_metrics
        WHERE product_id IN ({placeholders}) AND period = ?
        """,
        [*ids, period],
    ).fetchone()
    return {
        "views": scale_int(row["views"] or 0, scale),
        "sales": scale_int(row["sales"] or 0, scale),
        "revenue_cents": scale_int(row["revenue_cents"] or 0, scale),
        "refunds": scale_int(row["refunds"] or 0, scale),
        "refund_cents": scale_int(row["refund_cents"] or 0, scale),
        "discover_impressions": scale_int(row["discover_impressions"] or 0, scale),
    }


def load_sources(conn: sqlite3.Connection, ids: list[str], period: str, scale: float) -> list[dict[str, Any]]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT name, SUM(views) AS views, SUM(sales) AS sales, SUM(revenue_cents) AS revenue_cents
        FROM traffic_sources
        WHERE product_id IN ({placeholders}) AND period = ?
        GROUP BY LOWER(name), name
        ORDER BY revenue_cents DESC, sales DESC
        """,
        [*ids, period],
    ).fetchall()
    output = []
    for row in rows:
        views = scale_int(row["views"] or 0, scale)
        sales = scale_int(row["sales"] or 0, scale)
        revenue_cents = scale_int(row["revenue_cents"] or 0, scale)
        output.append(
            {
                "name": row["name"],
                "views": views,
                "sales": sales,
                "revenue": money_payload(revenue_cents),
                "revenue_cents": revenue_cents,
                "conversion": round_value(safe_divide(sales, views)),
                "average_order_cents": round(safe_divide(revenue_cents, sales)),
                "average_order": money_payload(round(safe_divide(revenue_cents, sales))),
            }
        )
    return output


def metadata_completeness(product: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("Category", bool(str(product.get("category") or "").strip())),
        ("Tags", len(product.get("tags") or []) >= IDEAL_TAG_COUNT),
        ("Description", len(str(product.get("description") or "").strip()) >= MIN_DESCRIPTION_LENGTH),
        ("Rating", float(product.get("rating") or 0) >= 4.3),
        ("Reviews", int(product.get("review_count") or 0) >= 10),
    ]
    completed = sum(1 for _, passed in checks if passed)
    missing = [label for label, passed in checks if not passed]
    return {"score": round_value(completed / len(checks), 2), "completed": completed, "total": len(checks), "missing": missing}


def aggregate_product(products: list[dict[str, Any]], current: dict[str, int]) -> dict[str, Any]:
    if len(products) == 1:
        return products[0]
    review_count = sum(int(product["review_count"]) for product in products)
    rating = safe_divide(sum(float(product["rating"]) * int(product["review_count"]) for product in products), review_count)
    return {
        "id": "all",
        "name": "All products",
        "creator": "Portfolio overview",
        "category": "All products",
        "price_cents": round(safe_divide(current["revenue_cents"], current["sales"])),
        "currency": "USD",
        "tags": ["all-products", "sales", "churn", "utm"],
        "rating": round_value(rating, 1),
        "review_count": review_count,
        "description": "Portfolio-wide analytics across every seeded product before drilling into a product.",
    }


def build_metrics(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    scale = date_scale(date_range)
    with closing(connect_readonly(db_path)) as conn:
        ids = product_ids(conn, product_id)
        products = load_products(conn, ids)
        current = load_period(conn, ids, "current", scale)
        previous = load_period(conn, ids, "previous", scale)
        current_sources = load_sources(conn, ids, "current", scale)
        previous_sources = load_sources(conn, ids, "previous", scale)
    product = aggregate_product(products, current)
    current_conversion = round_value(safe_divide(current["sales"], current["views"]))
    previous_conversion = round_value(safe_divide(previous["sales"], previous["views"]))
    current_refund_rate = round_value(safe_divide(current["refunds"], current["sales"]))
    previous_refund_rate = round_value(safe_divide(previous["refunds"], previous["sales"]))
    return {
        "product": product,
        "product_ids": ids,
        "date_range": date_range,
        "current": current,
        "previous": previous,
        "current_sources": current_sources,
        "previous_sources": previous_sources,
        "derived": {
            "current_conversion": current_conversion,
            "previous_conversion": previous_conversion,
            "conversion_delta_percent": round_value(percent_delta(current_conversion, previous_conversion)),
            "views_delta_percent": round_value(percent_delta(current["views"], previous["views"])),
            "sales_delta_percent": round_value(percent_delta(current["sales"], previous["sales"])),
            "revenue_delta_percent": round_value(percent_delta(current["revenue_cents"], previous["revenue_cents"])),
            "current_refund_rate": current_refund_rate,
            "previous_refund_rate": previous_refund_rate,
            "average_order_cents": round(safe_divide(current["revenue_cents"], current["sales"])),
            "metadata_completeness": metadata_completeness(product),
        },
    }


def signal_item(id_: str, label: str, title: str, confidence: str, recommendation: str, evidence: list[dict[str, str]], action: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": id_,
        "label": label,
        "title": title,
        "confidence": confidence,
        "recommendation": recommendation,
        "evidence": evidence,
        "action": action,
    }


def detect_signals_for_metrics(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    product = metrics["product"]
    current = metrics["current"]
    derived = metrics["derived"]
    signals: list[dict[str, Any]] = []
    conversion_falling = derived["previous_conversion"] > 0 and derived["current_conversion"] < derived["previous_conversion"] * 0.8
    traffic_high_or_growing = current["views"] >= HIGH_TRAFFIC_VIEWS or derived["views_delta_percent"] >= 0.3
    if traffic_high_or_growing and conversion_falling:
        signals.append(
            signal_item(
                "tighten-positioning",
                "Conversion",
                "Tighten the first-screen positioning",
                "high",
                "Move the buyer outcome into the first sentence and align the preview copy with the strongest traffic source.",
                [
                    {"label": "Current views", "value": f"{current['views']:,}", "comparison": f"{format_percent(derived['views_delta_percent'])} vs previous"},
                    {"label": "Conversion", "value": format_percent(derived["current_conversion"]), "comparison": f"down from {format_percent(derived['previous_conversion'])}"},
                ],
                {
                    "kind": "edit_description",
                    "label": "Update product description",
                    "copy_text": "Lead with the buyer outcome, then mirror the top-converting source's language in the first screen.",
                    "steps": ["Open the product description editor.", "Move the buyer outcome into the first sentence.", "Keep the price unchanged until the next analytics window."],
                },
            )
        )
    outperforming = next((source for source in metrics["current_sources"] if source["sales"] >= MIN_SOURCE_SALES and source["conversion"] >= derived["current_conversion"] * 1.5), None)
    if outperforming:
        signals.append(
            signal_item(
                "double-down-on-source",
                "Traffic source",
                f"Lean into {outperforming['name']}",
                "medium",
                "Reuse the source's winning message, examples, or offer framing in the product page and next promotion.",
                [
                    {"label": f"{outperforming['name']} conversion", "value": format_percent(outperforming["conversion"]), "comparison": f"product average is {format_percent(derived['current_conversion'])}"},
                    {"label": f"{outperforming['name']} revenue", "value": format_currency(outperforming["revenue_cents"], product["currency"])},
                ],
                {
                    "kind": "review_source",
                    "label": f"Review {outperforming['name']} traffic",
                    "copy_text": f"Use the {outperforming['name']} angle in the next product-page edit and promotion, then compare conversion against the product average.",
                    "steps": [f"Review the promise or audience used in {outperforming['name']}.", "Reuse the winning message in the product page or next promotion.", "Track whether the source continues to beat the product average."],
                },
            )
        )
    metadata = derived["metadata_completeness"]
    if current["discover_impressions"] >= 500 and metadata["score"] < 0.8:
        missing = ", ".join(metadata["missing"])
        signals.append(
            signal_item(
                "complete-discover-metadata",
                "Discover",
                "Make the Discover listing easier to classify",
                "medium",
                "Fill missing metadata and add specific tags for buyer, use case, and format.",
                [
                    {"label": "Discover impressions", "value": f"{current['discover_impressions']:,}"},
                    {"label": "Metadata completeness", "value": format_percent(metadata["score"]), "comparison": f"missing: {missing}" if missing else ""},
                ],
                {
                    "kind": "edit_metadata",
                    "label": "Update category and tags",
                    "copy_text": "Add tags that describe the buyer, use case, and product format instead of broad one-word labels.",
                    "steps": ["Fill the missing category if it is blank.", "Add at least four specific tags.", "Keep tags tied to actual product content."],
                },
            )
        )
    refund_jumped = derived["current_refund_rate"] >= derived["previous_refund_rate"] * 1.5 if derived["previous_refund_rate"] > 0 else derived["current_refund_rate"] > 0
    if current["refunds"] >= 3 and derived["current_refund_rate"] >= REFUND_WARNING_RATE and refund_jumped:
        signals.append(
            signal_item(
                "clarify-expectations",
                "Refunds",
                "Clarify what buyers get before checkout",
                "high",
                "Add a short contents section, compatibility notes, and clearer refund expectations near checkout.",
                [
                    {"label": "Refund rate", "value": format_percent(derived["current_refund_rate"]), "comparison": f"was {format_percent(derived['previous_refund_rate'])}"},
                    {"label": "Refunded amount", "value": format_currency(current["refund_cents"], product["currency"])},
                ],
                {
                    "kind": "edit_product_page",
                    "label": "Clarify included files and expectations",
                    "copy_text": "Includes the full file list, compatibility notes, setup steps, and refund expectations before checkout.",
                    "steps": ["Add a short contents section near the buy button.", "Call out compatibility or usage requirements.", "Set refund expectations before purchase."],
                },
            )
        )
    price_cents = int(product["price_cents"])
    packaging_useful = price_cents >= 1500 and current["views"] >= 300 and (derived["conversion_delta_percent"] <= -0.15 or derived["current_refund_rate"] >= 0.06 or (price_cents >= 4000 and derived["current_conversion"] < 0.035))
    if packaging_useful:
        signals.append(
            signal_item(
                "test-packaging",
                "Pricing",
                "Test a clearer package ladder",
                "low",
                "Keep the current offer as the base and test a higher-value bundle with clearer bonuses or commercial-use terms.",
                [
                    {"label": "Current price", "value": format_currency(price_cents, product["currency"])},
                    {"label": "Average order", "value": format_currency(derived["average_order_cents"], product["currency"])},
                ],
                {
                    "kind": "create_experiment",
                    "label": "Draft a packaging experiment",
                    "copy_text": "Keep the current product as the base offer and test a higher-value bundle with examples, bonuses, or a commercial-use tier.",
                    "steps": ["Keep the existing product and price live.", "Draft one higher-value package with clear added value.", "Run the test as an experiment before changing the base offer."],
                },
            )
        )
    if not signals:
        signals.append(
            signal_item(
                "collect-more-signal",
                "Baseline",
                "Keep collecting signal before changing the offer",
                "low",
                "Hold pricing steady and run one focused promotion so the next analytics period is easier to read.",
                [
                    {"label": "Current views", "value": f"{current['views']:,}"},
                    {"label": "Current sales", "value": f"{current['sales']:,}", "comparison": f"{format_percent(derived['current_conversion'])} conversion"},
                ],
                {
                    "kind": "plan_promotion",
                    "label": "Plan one focused promotion",
                    "copy_text": "Run one focused promotion for a single audience so the next analytics period is easier to interpret.",
                    "steps": ["Choose one audience and one channel.", "Keep the product page stable during the promotion.", "Review views, sales, and conversion after the next period."],
                },
            )
        )
    return signals


def get_database_inventory_tool(db_path: Path | str) -> dict[str, Any]:
    with closing(connect_readonly(db_path)) as conn:
        product_count = conn.execute("SELECT COUNT(*) AS n FROM products").fetchone()["n"]
        source_count = conn.execute("SELECT COUNT(*) AS n FROM traffic_sources").fetchone()["n"]
        sale_count = conn.execute("SELECT COUNT(*) AS n FROM customer_sales").fetchone()["n"]
        help_doc_count = conn.execute("SELECT COUNT(*) AS n FROM help_docs").fetchone()["n"]
        help_chunk_count = conn.execute("SELECT COUNT(*) AS n FROM help_doc_chunks").fetchone()["n"]
        snapshot = conn.execute(
            """
            SELECT source, source_hash, refreshed_at
            FROM analytics_snapshots
            ORDER BY refreshed_at DESC
            LIMIT 1
            """
        ).fetchone()
        current = load_period(conn, product_ids(conn, "all"), "current", 1.0)
    return {
        "product_count": product_count,
        "traffic_source_rows": source_count,
        "customer_sale_rows": sale_count,
        "help_doc_count": help_doc_count,
        "help_chunk_count": help_chunk_count,
        "current_views": current["views"],
        "current_sales": current["sales"],
        "current_revenue_cents": current["revenue_cents"],
        "snapshot": row_to_dict(snapshot) if snapshot else {},
        "access": "seeded local SQLite analytics and official Gumroad help-doc corpus through read-only tools",
    }


def get_product_metrics_tool(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    return build_metrics(db_path, product_id=product_id, date_range=date_range)


def get_traffic_sources_tool(db_path: Path | str, product_id: str = "all", date_range: str = "30", limit: int = 6) -> list[dict[str, Any]]:
    return build_metrics(db_path, product_id=product_id, date_range=date_range)["current_sources"][: max(1, min(12, int(limit or 6)))]


def get_detected_signals_tool(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> list[dict[str, Any]]:
    return detect_signals_for_metrics(build_metrics(db_path, product_id=product_id, date_range=date_range))


def get_action_review_tool(db_path: Path | str, signal_id: str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    signals = get_detected_signals_tool(db_path, product_id=product_id, date_range=date_range)
    for signal in signals:
        if signal["id"] == signal_id:
            return {"found": True, **signal}
    return {"found": False, "signal_id": signal_id}


def load_customer_sales_summary(db_path: Path | str, product_id: str = "all") -> dict[str, Any]:
    with closing(connect_readonly(db_path)) as conn:
        ids = product_ids(conn, product_id)
        if not ids:
            return {"sample_row_count": 0, "top_referrers": [], "top_campaigns": [], "countries": []}
        placeholders = ",".join("?" for _ in ids)
        row = conn.execute(
            f"""
            SELECT
                COUNT(*) AS row_count,
                SUM(net_total_cents) AS net_revenue_cents,
                SUM(refunded) AS refunded_rows,
                SUM(partial_refund_cents) AS partial_refund_cents,
                SUM(recurring_charge) AS recurring_rows,
                SUM(do_not_contact) AS do_not_contact_rows,
                SUM(ppp_discounted) AS ppp_discounted_rows,
                SUM(upsold) AS upsold_rows,
                SUM(sent_abandoned_cart_email) AS abandoned_cart_email_rows
            FROM customer_sales
            WHERE product_id IN ({placeholders})
            """,
            ids,
        ).fetchone()
        top_referrers = conn.execute(
            f"""
            SELECT referrer, COUNT(*) AS purchases, SUM(net_total_cents) AS net_revenue_cents
            FROM customer_sales
            WHERE product_id IN ({placeholders})
            GROUP BY referrer
            ORDER BY net_revenue_cents DESC, purchases DESC
            LIMIT 6
            """,
            ids,
        ).fetchall()
        top_campaigns = conn.execute(
            f"""
            SELECT utm_source, utm_medium, utm_campaign, COUNT(*) AS purchases, SUM(net_total_cents) AS net_revenue_cents
            FROM customer_sales
            WHERE product_id IN ({placeholders})
            GROUP BY utm_source, utm_medium, utm_campaign
            ORDER BY net_revenue_cents DESC, purchases DESC
            LIMIT 6
            """,
            ids,
        ).fetchall()
        countries = conn.execute(
            f"""
            SELECT country, COUNT(*) AS purchases, SUM(net_total_cents) AS net_revenue_cents
            FROM customer_sales
            WHERE product_id IN ({placeholders})
            GROUP BY country
            ORDER BY net_revenue_cents DESC, purchases DESC
            LIMIT 6
            """,
            ids,
        ).fetchall()
    row_count = int(row["row_count"] or 0) if row else 0
    return {
        "sample_only": True,
        "sample_row_count": row_count,
        "sample_net_revenue_cents": int(row["net_revenue_cents"] or 0) if row else 0,
        "sample_refunded_rows": int(row["refunded_rows"] or 0) if row else 0,
        "sample_partial_refund_cents": int(row["partial_refund_cents"] or 0) if row else 0,
        "sample_recurring_rows": int(row["recurring_rows"] or 0) if row else 0,
        "sample_do_not_contact_rows": int(row["do_not_contact_rows"] or 0) if row else 0,
        "sample_ppp_discounted_rows": int(row["ppp_discounted_rows"] or 0) if row else 0,
        "sample_upsold_rows": int(row["upsold_rows"] or 0) if row else 0,
        "sample_abandoned_cart_email_rows": int(row["abandoned_cart_email_rows"] or 0) if row else 0,
        "sample_average_net_order_cents": round(safe_divide(int(row["net_revenue_cents"] or 0), row_count)) if row else 0,
        "top_referrers": [
            {**row_to_dict(item), "sample_net_revenue": money_payload(item["net_revenue_cents"] or 0)}
            for item in top_referrers
        ],
        "top_campaigns": [
            {**row_to_dict(item), "sample_net_revenue": money_payload(item["net_revenue_cents"] or 0)}
            for item in top_campaigns
        ],
        "countries": [
            {**row_to_dict(item), "sample_net_revenue": money_payload(item["net_revenue_cents"] or 0)}
            for item in countries
        ],
        "summary_warning": "These are synthetic sample export rows, not source-of-truth revenue totals. Use product metrics for revenue, sales, conversion, refunds, and AOV.",
        "privacy_note": "customer-level demo rows are summarized for strategy; buyer names and emails are not returned by this tool",
    }


def search_products_tool(db_path: Path | str, query: str = "", limit: int = 5) -> list[dict[str, Any]]:
    needle = f"%{(query or '').strip().lower()}%"
    with closing(connect_readonly(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT id, name, creator, category, price_cents, currency, tags_json, rating, review_count
            FROM products
            WHERE LOWER(name) LIKE ? OR LOWER(creator) LIKE ? OR LOWER(category) LIKE ? OR LOWER(tags_json) LIKE ?
            ORDER BY name
            LIMIT ?
            """,
            (needle, needle, needle, needle, max(1, min(20, int(limit or 5)))),
        ).fetchall()
    output = []
    for row in rows:
        item = row_to_dict(row)
        item["tags"] = json.loads(item.pop("tags_json") or "[]")
        output.append(item)
    return output


def build_correlation_insights(product: dict[str, Any], metrics: dict[str, Any], dashboard: dict[str, Any]) -> list[dict[str, Any]]:
    top_source = metrics["current_sources"][0] if metrics["current_sources"] else None
    top_location = dashboard["locations"][0] if dashboard["locations"] else None
    top_utm = dashboard["utm_links"][0] if dashboard["utm_links"] else None
    direct_source = next((source for source in metrics["current_sources"] if source["name"].lower() == "direct"), None)
    location_revenue = sum(int(location["revenue_cents"]) for location in dashboard["locations"])
    utm_revenue = sum(int(link["revenue_cents"]) for link in dashboard["utm_links"])
    top_location_share = safe_divide(int(top_location["revenue_cents"]) if top_location else 0, location_revenue)
    top_utm_share = safe_divide(int(top_utm["revenue_cents"]) if top_utm else 0, utm_revenue)
    top_utm_conversion = safe_divide(int(top_utm["sales"]) if top_utm else 0, int(top_utm["clicks"]) if top_utm else 0)
    refund_and_churn_risk = metrics["derived"]["current_refund_rate"] >= 0.08 and dashboard["churn"]["rate"] >= 0.05
    return [
        {
            "label": "Referrer x location",
            "title": f"{top_source['name'] if top_source else 'Top referrer'} is strongest where revenue is concentrated",
            "detail": (
                f"{top_source['name'] if top_source else 'The top referrer'} leads current revenue while "
                f"{top_location['region'] if top_location else 'the top region'} carries {format_percent(top_location_share)} "
                "of location-tracked sales. Treat this as audience-fit signal, not proof of causation."
            ),
            "evidence": [
                f"{top_source['name'] if top_source else 'Top referrer'}: {format_currency(int(top_source['revenue_cents']) if top_source else 0, product['currency'])}",
                f"{top_location['country'] if top_location else 'Top market'}: {format_currency(int(top_location['revenue_cents']) if top_location else 0, product['currency'])}",
            ],
        },
        {
            "label": "UTM x conversion",
            "title": f"{top_utm['campaign'] if top_utm else 'Tracked campaign'} is the cleanest campaign read",
            "detail": (
                f"{top_utm['source'] if top_utm else 'The top UTM source'} / {top_utm['medium'] if top_utm else 'medium'} "
                f"converts at {format_percent(top_utm_conversion)}, compared with "
                f"{format_percent(metrics['derived']['current_conversion'])} overall. Reuse the offer framing before widening spend."
            ),
            "evidence": [
                f"{int(top_utm['clicks']) if top_utm else 0:,} clicks",
                f"{format_percent(top_utm_share)} of UTM revenue",
            ],
        },
        {
            "label": "Churn x refunds",
            "title": "Retention and refunds are pointing at expectation mismatch" if refund_and_churn_risk else "Retention and refund pressure are readable together",
            "detail": (
                f"Churn is {format_percent(dashboard['churn']['rate'])} and refund rate is "
                f"{format_percent(metrics['derived']['current_refund_rate'])}. If both rise together, review promises, onboarding, and compatibility notes before changing price."
            ),
            "evidence": [
                f"{int(dashboard['churn']['canceled']):,} churned users",
                f"{int(metrics['current']['refunds']):,} refunds",
            ],
        },
        {
            "label": "Direct x UTM gap",
            "title": "Direct traffic needs attribution cleanup before it gets credit",
            "detail": (
                f"Direct shows {format_currency(int(direct_source['revenue_cents']) if direct_source else 0, product['currency'])} in revenue, "
                "but that bucket can hide apps, email, mobile clients, bookmarks, and private shares. Use tracked links before calling it organic demand."
            ),
            "evidence": [
                f"{int(direct_source['views']) if direct_source else 0:,} direct views",
                f"{int(metrics['current']['discover_impressions']):,} Discover impressions",
            ],
        },
    ]


def load_dashboard_summary(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    scale = date_scale(date_range)
    base_scale = scale ** 0.5
    with closing(connect_readonly(db_path)) as conn:
        ids = product_ids(conn, product_id)
        if not ids:
            return {"churn": {}, "locations": [], "utm_links": [], "customer_sales": {}, "correlations": []}
        placeholders = ",".join("?" for _ in ids)
        churn_rows = conn.execute(
            f"SELECT * FROM churn_metrics WHERE product_id IN ({placeholders})",
            ids,
        ).fetchall()
        churn = defaultdict(int)
        for row in churn_rows:
            for key in ("active_start", "new_subscriptions", "canceled", "previous_active_start", "previous_new_subscriptions", "previous_canceled", "revenue_lost_cents"):
                churn[key] += int(row[key])
        locations = conn.execute(
            f"""
            SELECT country, region, SUM(views) AS views, SUM(sales) AS sales, SUM(revenue_cents) AS revenue_cents
            FROM locations
            WHERE product_id IN ({placeholders})
            GROUP BY country, region
            ORDER BY revenue_cents DESC
            """,
            ids,
        ).fetchall()
        utm_links = conn.execute(
            f"""
            SELECT source, medium, campaign, destination, SUM(clicks) AS clicks, SUM(sales) AS sales, SUM(revenue_cents) AS revenue_cents
            FROM utm_links
            WHERE product_id IN ({placeholders})
            GROUP BY source, medium, campaign, destination
            ORDER BY revenue_cents DESC
            """,
            ids,
        ).fetchall()
    churn_dict = dict(churn)
    if scale != 1:
        for key in ("active_start", "previous_active_start"):
            churn_dict[key] = scale_int(churn_dict.get(key, 0), base_scale)
        for key in ("new_subscriptions", "canceled", "previous_new_subscriptions", "previous_canceled", "revenue_lost_cents"):
            churn_dict[key] = scale_int(churn_dict.get(key, 0), scale)
    location_items = [row_to_dict(row) for row in locations]
    utm_items = [row_to_dict(row) for row in utm_links]
    if scale != 1:
        for item in location_items:
            for key in ("views", "sales", "revenue_cents"):
                item[key] = scale_int(item[key], scale)
        for item in utm_items:
            for key in ("clicks", "sales", "revenue_cents"):
                item[key] = scale_int(item[key], scale)
    for item in utm_items:
        item["conversion"] = round_value(safe_divide(item["sales"], item["clicks"]))
    product_currency = "USD"
    with closing(connect_readonly(db_path)) as conn:
        product_rows = load_products(conn, ids)
        if len(product_rows) == 1:
            product_currency = product_rows[0]["currency"]
    for item in location_items:
        item["revenue"] = money_payload(item["revenue_cents"], product_currency)
    for item in utm_items:
        item["revenue"] = money_payload(item["revenue_cents"], product_currency)
    churn_base = churn_dict["active_start"] + churn_dict["new_subscriptions"]
    previous_churn_base = churn_dict["previous_active_start"] + churn_dict["previous_new_subscriptions"]
    summary = {
        "churn": {
            **churn_dict,
            "rate": round_value(safe_divide(churn_dict["canceled"], churn_base)),
            "previous_rate": round_value(safe_divide(churn_dict["previous_canceled"], previous_churn_base)),
            "formula": f"{churn_dict['canceled']} canceled / ({churn_dict['active_start']} active + {churn_dict['new_subscriptions']} new)",
        },
        "locations": location_items,
        "utm_links": utm_items,
        "customer_sales": load_customer_sales_summary(db_path, product_id=product_id),
    }
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    summary["correlations"] = build_correlation_insights(metrics["product"], metrics, summary)
    return summary


def get_dashboard_summary_tool(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    summary = load_dashboard_summary(db_path, product_id=product_id, date_range=date_range)
    return {
        "churn": summary["churn"],
        "top_locations": summary["locations"][:6],
        "top_utm_links": summary["utm_links"][:6],
        "customer_sales": summary["customer_sales"],
        "correlations": summary["correlations"],
        "money_note": "All *_cents fields are cents. Use the nested formatted money fields when writing dollar amounts.",
    }


def strategy_growth_rate(metrics: dict[str, Any], dashboard: dict[str, Any]) -> float:
    derived = metrics["derived"]
    churn_rate = dashboard.get("churn", {}).get("rate", 0)
    growth_rate = 0.12
    if derived["revenue_delta_percent"] >= 0.25 and derived["current_refund_rate"] < 0.06 and churn_rate < 0.05:
        growth_rate = 0.16
    if derived["conversion_delta_percent"] <= -0.15 or derived["current_refund_rate"] >= 0.08 or churn_rate >= 0.07:
        growth_rate = 0.08
    if metrics["current"]["views"] < 250:
        growth_rate = min(growth_rate, 0.1)
    return growth_rate


def normalize_horizon(horizon_months: int | str) -> int:
    try:
        value = int(horizon_months)
    except (TypeError, ValueError):
        value = 3
    if value <= 3:
        return 3
    return 6


def build_strategy_plan_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    horizon_months: int | str = 3,
) -> dict[str, Any]:
    horizon = normalize_horizon(horizon_months)
    monthly_metrics = build_metrics(db_path, product_id=product_id, date_range="30")
    selected_metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    dashboard = load_dashboard_summary(db_path, product_id=product_id, date_range=date_range)
    signals = detect_signals_for_metrics(selected_metrics)
    product = selected_metrics["product"]
    growth_rate = strategy_growth_rate(selected_metrics, dashboard)
    base_revenue = monthly_metrics["current"]["revenue_cents"]
    base_sales = monthly_metrics["current"]["sales"]
    base_views = monthly_metrics["current"]["views"]
    average_order_cents = max(1, monthly_metrics["derived"]["average_order_cents"])
    monthly_targets = []
    for month in range(1, horizon + 1):
        multiplier = (1 + growth_rate) ** month
        revenue_cents = round(base_revenue * multiplier)
        sales = round(revenue_cents / average_order_cents)
        target_conversion = min(0.25, monthly_metrics["derived"]["current_conversion"] * (1 + min(0.25, growth_rate * 1.6)))
        views = round(safe_divide(sales, target_conversion))
        monthly_targets.append(
            {
                "month": month,
                "revenue_cents": revenue_cents,
                "sales": sales,
                "views": views,
                "target_conversion": round_value(target_conversion),
            }
        )
    top_source = selected_metrics["current_sources"][0] if selected_metrics["current_sources"] else None
    strongest_source = next(
        (
            source
            for source in selected_metrics["current_sources"]
            if source["sales"] >= MIN_SOURCE_SALES and source["conversion"] >= selected_metrics["derived"]["current_conversion"] * 1.5
        ),
        top_source,
    )
    top_utm = dashboard["utm_links"][0] if dashboard["utm_links"] else None
    top_location = dashboard["locations"][0] if dashboard["locations"] else None
    pillars = [
        {
            "name": "Monthly overview",
            "move": (
                f"Start from {format_currency(base_revenue, product['currency'])}/month, "
                f"{base_sales:,} sales, {format_percent(monthly_metrics['derived']['current_conversion'])} conversion, "
                f"and {format_currency(average_order_cents, product['currency'])} average order value."
            ),
            "why": "This keeps the plan anchored to the actual current run rate instead of a made-up revenue target.",
        },
        {
            "name": "Conversion and positioning",
            "move": signals[0]["recommendation"],
            "why": signals[0]["title"],
        },
        {
            "name": "Channel focus",
            "move": (
                f"Use {strongest_source['name']} as the next controlled acquisition test; it is currently producing "
                f"{strongest_source['sales']:,} sales at {format_percent(strongest_source['conversion'])} conversion."
                if strongest_source
                else "Run one channel test at a time so source quality is readable."
            ),
            "why": "Source quality matters more than raw traffic; the bot prioritizes conversion, revenue, and attribution cleanliness.",
        },
        {
            "name": "Retention and expectation fit",
            "move": (
                f"Watch {format_percent(dashboard['churn']['rate'])} churn and "
                f"{format_percent(selected_metrics['derived']['current_refund_rate'])} refund rate before changing price."
            ),
            "why": "Refunds and churn are usually promise, onboarding, compatibility, or audience-fit signals before they are pricing signals.",
        },
        {
            "name": "Measurement",
            "move": (
                f"Keep UTM discipline around {top_utm['source']} / {top_utm['medium']} and compare it with direct traffic."
                if top_utm
                else "Use tracked links on every campaign before broadening spend."
            ),
            "why": "Attribution cleanup prevents direct traffic from hiding email, private-share, app, and social traffic.",
        },
    ]
    target = monthly_targets[-1]
    return {
        "product": product,
        "date_range": date_range,
        "horizon_months": horizon,
        "growth_rate": round_value(growth_rate),
        "realistic_goal": (
            f"Reach about {format_currency(target['revenue_cents'], product['currency'])}/month by month {horizon}, "
            f"requiring about {target['sales']:,} sales and {target['views']:,} visits at "
            f"{format_percent(target['target_conversion'])} conversion."
        ),
        "baseline": {
            "monthly_revenue_cents": base_revenue,
            "monthly_sales": base_sales,
            "monthly_views": base_views,
            "conversion": monthly_metrics["derived"]["current_conversion"],
            "average_order_cents": average_order_cents,
            "top_source": top_source,
            "top_location": top_location,
        },
        "monthly_targets": monthly_targets,
        "pillars": pillars,
        "signals": signals[:4],
        "questions_to_offer": [
            "Do you want a monthly overview?",
            "Do you want the past three months?",
            "Do you want a realistic three-month sales goal?",
            "Do you want a six-month plan?",
        ],
    }
