from __future__ import annotations

import json
from contextlib import closing
from pathlib import Path
from typing import Any

from gumroad_merchant.database import connect_readonly
from gumroad_merchant.tracked_campaigns import row_to_campaign


def camel_period(row: Any, sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "views": row["views"],
        "sales": row["sales"],
        "revenueCents": row["revenue_cents"],
        "refunds": row["refunds"],
        "refundCents": row["refund_cents"],
        "discoverImpressions": row["discover_impressions"],
        "sources": sources,
    }


def load_sources(conn: Any, product_id: str, period: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT name, views, sales, revenue_cents
        FROM traffic_sources
        WHERE product_id = ? AND period = ?
        ORDER BY rowid
        """,
        (product_id, period),
    ).fetchall()
    return [
        {
            "name": row["name"],
            "views": row["views"],
            "sales": row["sales"],
            "revenueCents": row["revenue_cents"],
        }
        for row in rows
    ]


def load_period(conn: Any, product_id: str, period: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT views, sales, revenue_cents, refunds, refund_cents, discover_impressions
        FROM period_metrics
        WHERE product_id = ? AND period = ?
        """,
        (product_id, period),
    ).fetchone()
    if not row:
        return {
            "views": 0,
            "sales": 0,
            "revenueCents": 0,
            "refunds": 0,
            "refundCents": 0,
            "discoverImpressions": 0,
            "sources": [],
        }
    return camel_period(row, load_sources(conn, product_id, period))


def load_products(conn: Any) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM products ORDER BY rowid").fetchall()
    products = []
    for row in rows:
        products.append(
            {
                "id": row["id"],
                "name": row["name"],
                "creator": row["creator"],
                "category": row["category"],
                "priceCents": row["price_cents"],
                "currency": row["currency"],
                "tags": json.loads(row["tags_json"] or "[]"),
                "rating": row["rating"],
                "reviewCount": row["review_count"],
                "description": row["description"],
                "current": load_period(conn, row["id"], "current"),
                "previous": load_period(conn, row["id"], "previous"),
            }
        )
    return products


def seeded_utm_reason(row: Any) -> str:
    clicks = row["clicks"] or 0
    sales = row["sales"] or 0
    conversion = (sales / clicks) if clicks else 0
    return (
        f"Because {row['campaign']} is already tracked, this row can separate campaign traffic from direct and Discover traffic. "
        f"It is worth reading when deciding what to repeat because it has {sales:,} sales from {clicks:,} clicks "
        f"({conversion * 100:.1f}% conversion)."
    )


def load_dashboard_data(conn: Any, product_id: str) -> dict[str, Any]:
    churn = conn.execute(
        """
        SELECT active_start, new_subscriptions, canceled, previous_active_start,
               previous_new_subscriptions, previous_canceled, revenue_lost_cents
        FROM churn_metrics
        WHERE product_id = ?
        """,
        (product_id,),
    ).fetchone()
    location_rows = conn.execute(
        """
        SELECT country, region, views, sales, revenue_cents
        FROM locations
        WHERE product_id = ?
        ORDER BY rowid
        """,
        (product_id,),
    ).fetchall()
    utm_rows = conn.execute(
        """
        SELECT source, medium, campaign, destination, clicks, sales, revenue_cents
        FROM utm_links
        WHERE product_id = ?
        ORDER BY rowid
        """,
        (product_id,),
    ).fetchall()
    campaign_rows = conn.execute(
        """
        SELECT *
        FROM tracked_campaigns
        WHERE product_id = ? AND status != 'archived'
        ORDER BY created_at DESC, id DESC
        """,
        (product_id,),
    ).fetchall()
    utm_links = [
        {
            "source": row["source"],
            "medium": row["medium"],
            "campaign": row["campaign"],
            "destination": row["destination"],
            "clicks": row["clicks"],
            "sales": row["sales"],
            "revenueCents": row["revenue_cents"],
            "reason": seeded_utm_reason(row),
            "status": "measured",
        }
        for row in utm_rows
    ]
    for row in campaign_rows:
        campaign = row_to_campaign(row)
        utm_links.append(
            {
                "source": campaign["source"],
                "medium": campaign["medium"],
                "campaign": campaign["campaign"],
                "destination": campaign["destination"],
                "clicks": campaign["clicks"],
                "sales": campaign["sales"],
                "revenueCents": campaign["revenue_cents"],
                "reason": campaign["reason"],
                "status": campaign["status"],
                "trackingUrl": campaign["tracking_url"],
                "htmlLink": campaign["html_link"],
                "createdAt": campaign["created_at"],
                "isDraft": True,
            }
        )
    return {
        "churn": {
            "activeStart": churn["active_start"] if churn else 0,
            "newSubscriptions": churn["new_subscriptions"] if churn else 0,
            "canceled": churn["canceled"] if churn else 0,
            "previousActiveStart": churn["previous_active_start"] if churn else 0,
            "previousNewSubscriptions": churn["previous_new_subscriptions"] if churn else 0,
            "previousCanceled": churn["previous_canceled"] if churn else 0,
            "revenueLostCents": churn["revenue_lost_cents"] if churn else 0,
        },
        "locations": [
            {
                "country": row["country"],
                "region": row["region"],
                "views": row["views"],
                "sales": row["sales"],
                "revenueCents": row["revenue_cents"],
            }
            for row in location_rows
        ],
        "utmLinks": utm_links,
    }


def load_analytics_dashboard_payload(db_path: Path | str) -> dict[str, Any]:
    with closing(connect_readonly(db_path)) as conn:
        products = load_products(conn)
        dashboard_data = {
            product["id"]: load_dashboard_data(conn, product["id"])
            for product in products
        }
        tracked_campaign_count = conn.execute(
            "SELECT COUNT(*) AS count FROM tracked_campaigns WHERE status != 'archived'"
        ).fetchone()["count"]
    return {
        "products": products,
        "dashboardData": dashboard_data,
        "trackedCampaignCount": tracked_campaign_count,
    }
