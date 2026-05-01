from __future__ import annotations

import html
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from gumroad_merchant.content_radar_tools import list_content_trends_tool
from gumroad_merchant.database import connect, connect_readonly, ensure_schema, now_iso


def slugify(value: str, separator: str = "-") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", separator, str(value).lower()).strip(separator)
    return cleaned or "campaign"


def campaign_slug(value: str) -> str:
    return slugify(value, separator="-")[:80]


def load_product(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row:
    if product_id and product_id != "all":
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row:
            return row
    row = conn.execute("SELECT * FROM products ORDER BY rowid LIMIT 1").fetchone()
    if not row:
        raise ValueError("No products are available in the local analytics store.")
    return row


def lead_campaign_context(db_path: Path | str, product_id: str, date_range: str) -> dict[str, Any]:
    trends = list_content_trends_tool(db_path, product_id=product_id, date_range=date_range, limit=1)
    trend = trends[0] if trends else {}
    return {
        "product_id": trend.get("product_id") or (product_id if product_id != "all" else ""),
        "title": trend.get("title") or "Focused creator campaign",
        "channel": trend.get("channel") or "Newsletter",
        "campaign": trend.get("campaign_utm_name") or "",
        "expected_kpi": trend.get("expected_kpi") or {},
        "rationale": trend.get("rationale") or "",
    }


def unique_campaign(conn: sqlite3.Connection, product_id: str, campaign: str) -> str:
    base = campaign_slug(campaign)
    existing = {
        row["campaign"]
        for row in conn.execute(
            "SELECT campaign FROM tracked_campaigns WHERE product_id = ?",
            (product_id,),
        ).fetchall()
    }
    if base not in existing:
        return base
    for index in range(2, 100):
        suffix = f"-{index}"
        candidate = f"{base[:80 - len(suffix)]}{suffix}"
        if candidate not in existing:
            return candidate
    raise ValueError("Could not create a unique campaign name.")


def product_destination_url(product_name: str) -> str:
    return f"https://gumroad.com/l/{slugify(product_name)}"


def product_destination(product: sqlite3.Row, explicit_url: str | None = None) -> tuple[str, str]:
    if explicit_url and explicit_url.strip():
        return explicit_url.strip(), "provided"
    keys = set(product.keys())
    for field in ("product_url", "permalink", "url"):
        if field in keys and str(product[field] or "").strip():
            return str(product[field]).strip(), field
    return product_destination_url(product["name"]), "demo_generated"


def tracking_url(destination_url: str, source: str, medium: str, campaign: str) -> str:
    separator = "&" if "?" in destination_url else "?"
    return f"{destination_url}{separator}{urlencode({'utm_source': source, 'utm_medium': medium, 'utm_campaign': campaign})}"


def row_to_campaign(row: sqlite3.Row) -> dict[str, Any]:
    keys = set(row.keys())
    destination_source = row["destination_source"] if "destination_source" in keys else "demo_generated"
    if destination_source == "provided" and row["destination"] == product_destination_url(row["product_name"]):
        destination_source = "demo_generated"
    return {
        "id": row["id"],
        "product_id": row["product_id"],
        "product_name": row["product_name"],
        "title": row["title"],
        "source": row["source"],
        "medium": row["medium"],
        "campaign": row["campaign"],
        "destination": row["destination"],
        "destination_source": destination_source,
        "tracking_url": row["tracking_url"],
        "html_link": row["html_link"],
        "reason": row["reason"],
        "status": row["status"],
        "clicks": row["clicks"],
        "sales": row["sales"],
        "revenue_cents": row["revenue_cents"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "attribution_window_days": 7,
    }


def build_tracked_campaign_payload(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    title: str | None = None,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    destination_url: str | None = None,
    destination_source: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    context = lead_campaign_context(db_path, product_id=product_id, date_range=date_range)
    target_product_id = context["product_id"] or product_id
    with closing(connect_readonly(db_path)) as conn:
        product = load_product(conn, target_product_id)
        destination, inferred_destination_source = product_destination(product, explicit_url=destination_url)
        destination_source = destination_source or inferred_destination_source
        product_name = product["name"]
    title = (title or context["title"] or f"{product_name} tracked campaign").strip()
    source = slugify(source or context["channel"] or "newsletter")
    medium = slugify(medium or "content")
    campaign = campaign_slug(campaign or context["campaign"] or title)
    expected_kpi = context.get("expected_kpi") or {}
    kpi_name = expected_kpi.get("name") or "tracked clicks, sales, and conversion"
    kpi_target = expected_kpi.get("target_formatted")
    target = f"{kpi_name} toward {kpi_target}" if kpi_target else kpi_name
    reason = (
        reason
        or (
            f"Because {title} is the highest-fit Content Radar move for {product_name}, this link isolates the campaign "
            f"from direct and Discover traffic. Here is why we recommend creating it: the next read should compare {target} "
            "before you reuse the angle or widen promotion."
        )
    ).strip()
    return {
        "product_id": target_product_id,
        "date_range": date_range,
        "product_name": product_name,
        "title": title,
        "source": source,
        "medium": medium,
        "campaign": campaign,
        "destination_url": destination,
        "destination_source": destination_source,
        "reason": reason,
        "expected_kpi": expected_kpi,
    }


def list_tracked_campaigns(
    db_path: Path | str,
    product_id: str = "all",
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 100))
    with closing(connect_readonly(db_path)) as conn:
        if product_id and product_id != "all":
            rows = conn.execute(
                """
                SELECT * FROM tracked_campaigns
                WHERE product_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (product_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM tracked_campaigns
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [row_to_campaign(row) for row in rows]


def create_tracked_campaign(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    title: str | None = None,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    destination_url: str | None = None,
    destination_source: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload = build_tracked_campaign_payload(
        db_path,
        product_id=product_id,
        date_range=date_range,
        title=title,
        source=source,
        medium=medium,
        campaign=campaign,
        destination_url=destination_url,
        destination_source=destination_source,
        reason=reason,
    )
    with closing(connect(db_path)) as conn:
        ensure_schema(conn)
        product = load_product(conn, payload["product_id"])
        product_id = product["id"]
        product_name = product["name"]
        title = payload["title"]
        source = payload["source"]
        medium = payload["medium"]
        campaign = unique_campaign(conn, product_id, payload["campaign"])
        destination = payload["destination_url"]
        destination_source = payload["destination_source"]
        url = tracking_url(destination, source, medium, campaign)
        reason = payload["reason"]
        now = now_iso()
        html_link = f'<a href="{html.escape(url, quote=True)}">{html.escape(title)}</a>'
        cursor = conn.execute(
            """
            INSERT INTO tracked_campaigns(
                product_id, product_name, title, source, medium, campaign,
                destination, destination_source, tracking_url, html_link, reason, status,
                clicks, sales, revenue_cents, created_by, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 0, 0, 0, 'merchant-agent', ?, ?)
            """,
            (
                product_id,
                product_name,
                title,
                source,
                medium,
                campaign,
                destination,
                destination_source,
                url,
                html_link,
                reason,
                now,
                now,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tracked_campaigns WHERE id = ?", (cursor.lastrowid,)).fetchone()
        if not row:
            raise RuntimeError("Tracked campaign was not saved.")
        return row_to_campaign(row)


def list_tracked_campaigns_tool(db_path: Path | str, product_id: str = "all", limit: int = 50) -> list[dict[str, Any]]:
    return list_tracked_campaigns(db_path, product_id=product_id, limit=limit)


def create_tracked_campaign_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    title: str | None = None,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    destination_url: str | None = None,
    destination_source: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return create_tracked_campaign(
        db_path,
        product_id=product_id,
        date_range=date_range,
        title=title,
        source=source,
        medium=medium,
        campaign=campaign,
        destination_url=destination_url,
        destination_source=destination_source,
        reason=reason,
    )
