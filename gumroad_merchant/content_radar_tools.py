from __future__ import annotations

"""Read-only Content Radar and Marketing Plan helpers for the seeded demo.

This module only inspects local synthetic SQLite analytics, refund, and UTM
fixtures. It does not search the web, write files, post campaigns, send email,
or mutate Gumroad product data.
"""

import json
import re
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Any

from gumroad_merchant.analytics_tools import (
    build_metrics,
    format_percent,
    load_dashboard_summary,
    load_products,
    money_payload,
    product_ids,
    round_value,
    safe_divide,
)
from gumroad_merchant.database import connect_readonly, row_to_dict
from gumroad_merchant.refund_ops_tools import get_refund_prevention_actions_tool


DEFAULT_TREND_LIMIT = 6
MAX_TREND_LIMIT = 12
DEFAULT_PLAN_WEEKS = 4
MAX_PLAN_WEEKS = 8


TREND_LIBRARY: list[dict[str, Any]] = [
    {
        "id": "creator-operating-system",
        "title": "Creator operating system walkthroughs",
        "category_keywords": ["productivity"],
        "tag_keywords": ["notion", "creator-tools", "planning", "templates"],
        "source_keywords": ["youtube", "newsletter"],
        "channels": ["YouTube", "Newsletter"],
        "fit_rationale": "The seeded buyer intent is around planning launches, sponsor tracking, and repeatable creator systems.",
        "angles": [
            "Show the before/after dashboard a creator gets after installing the workspace.",
            "Turn one launch-planning workflow into a short teardown with the template as the next step.",
            "Use sponsor tracking and monthly revenue review as proof of operational value.",
        ],
        "utm_stem": "creator_systems_walkthrough",
        "kpi": "product-page conversion from tracked creator-system traffic",
        "risk": "Avoid promising a fully managed business system; keep the claim tied to templates and workflows.",
    },
    {
        "id": "landing-page-teardown",
        "title": "Launch-page teardown content",
        "category_keywords": ["design", "landing"],
        "tag_keywords": ["templates", "figma", "saas"],
        "source_keywords": ["product hunt", "twitter", "x / twitter"],
        "channels": ["X / Twitter", "Product Hunt"],
        "fit_rationale": "Template buyers respond to concrete launch examples more than broad design language.",
        "angles": [
            "Break down a weak SaaS landing page and rebuild the first screen with the kit.",
            "Show three launch sections that can be copied into a Gumroad product page.",
            "Frame the kit as a speed play for makers who need a credible first version.",
        ],
        "utm_stem": "launch_page_teardown",
        "kpi": "tracked UTM sales from launch and social channels",
        "risk": "Template claims need screenshots and scope boundaries so buyers know what is included.",
    },
    {
        "id": "sample-pack-session",
        "title": "Sample-pack session breakdowns",
        "category_keywords": ["music", "audio"],
        "tag_keywords": ["music", "samples", "lo-fi", "ableton"],
        "source_keywords": ["beatstars", "instagram"],
        "channels": ["Instagram", "Marketplace"],
        "fit_rationale": "The seeded music product already has strong marketplace and social source signal.",
        "angles": [
            "Build a 30-second loop from only the pack and show the exact files used.",
            "Compare a raw loop with the final mix so producers can hear texture and utility.",
            "Highlight royalty-free usage and DAW compatibility before the sales link.",
        ],
        "utm_stem": "lofi_session_breakdown",
        "kpi": "sales from social demos and marketplace links",
        "risk": "Refund pressure is elevated in the seeded data, so compatibility and included-file details must be explicit.",
    },
    {
        "id": "tiny-launch-diary",
        "title": "Tiny launch diary posts",
        "category_keywords": ["writing", "publishing"],
        "tag_keywords": ["writing", "zines", "publishing"],
        "source_keywords": ["newsletter", "direct"],
        "channels": ["Newsletter", "Direct"],
        "fit_rationale": "Low-volume seeded sales need trust-building content and clean attribution before scaling.",
        "angles": [
            "Publish a short launch diary showing the smallest viable zine launch plan.",
            "Share a pricing and shipping checklist for first-time independent publishers.",
            "Turn one chapter into a preview with a tracked newsletter link.",
        ],
        "utm_stem": "tiny_zine_launch_diary",
        "kpi": "newsletter click-to-sale conversion",
        "risk": "The product is low-priced and low-volume, so one broad campaign can hide whether the message worked.",
    },
    {
        "id": "discover-fit-refresh",
        "title": "Gumroad Discover fit refresh",
        "category_keywords": ["all products", "productivity", "design", "music", "writing"],
        "tag_keywords": ["templates", "creator-tools", "samples", "publishing"],
        "source_keywords": ["gumroad discover", "gumroad"],
        "channels": ["Gumroad Discover"],
        "fit_rationale": "Discover impressions are already available in the seeded metrics, making listing quality and expectation fit measurable.",
        "angles": [
            "Rewrite the first-screen product promise around the buyer outcome, format, and included files.",
            "Add buyer/use-case tags that match the strongest organic discovery path.",
            "Pair the listing refresh with a tracked campaign so Discover is not mixed with direct traffic.",
        ],
        "utm_stem": "discover_fit_refresh",
        "kpi": "Discover conversion and refund-rate stability",
        "risk": "More impressions can amplify refunds if product format, compatibility, and included assets stay vague.",
    },
]


CHANNEL_DEFAULTS: dict[str, dict[str, str]] = {
    "YouTube": {"source": "youtube", "medium": "video"},
    "Newsletter": {"source": "newsletter", "medium": "email"},
    "X / Twitter": {"source": "twitter", "medium": "social"},
    "Product Hunt": {"source": "producthunt", "medium": "launch"},
    "Instagram": {"source": "instagram", "medium": "social"},
    "Marketplace": {"source": "marketplace", "medium": "marketplace"},
    "Gumroad Discover": {"source": "gumroad", "medium": "discover"},
    "Direct": {"source": "direct", "medium": "direct"},
}


def clamp_limit(limit: int | str | None, default: int = DEFAULT_TREND_LIMIT, maximum: int = MAX_TREND_LIMIT) -> int:
    try:
        value = int(limit) if limit is not None else default
    except (TypeError, ValueError):
        value = default
    return max(1, min(maximum, value))


def normalize_plan_weeks(weeks: int | str | None) -> int:
    try:
        value = int(weeks) if weeks is not None else DEFAULT_PLAN_WEEKS
    except (TypeError, ValueError):
        value = DEFAULT_PLAN_WEEKS
    return max(2, min(MAX_PLAN_WEEKS, value))


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower())
    return re.sub(r"_+", "_", slug).strip("_") or "campaign"


def parse_tags(product: dict[str, Any]) -> list[str]:
    tags = product.get("tags")
    if isinstance(tags, list):
        return [str(tag).lower() for tag in tags]
    raw = product.get("tags_json")
    if not raw:
        return []
    try:
        return [str(tag).lower() for tag in json.loads(raw)]
    except (TypeError, json.JSONDecodeError):
        return []


def load_product_rows(db_path: Path | str, product_id: str = "all") -> list[dict[str, Any]]:
    with closing(connect_readonly(db_path)) as conn:
        ids = product_ids(conn, product_id)
        return load_products(conn, ids)


def load_utm_rows(
    conn: sqlite3.Connection,
    ids: list[str],
    product_id: str = "all",
    limit: int = 12,
) -> list[dict[str, Any]]:
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT
            product_id,
            source,
            medium,
            campaign,
            destination,
            SUM(clicks) AS clicks,
            SUM(sales) AS sales,
            SUM(revenue_cents) AS revenue_cents
        FROM utm_links
        WHERE product_id IN ({placeholders})
        GROUP BY product_id, source, medium, campaign, destination
        ORDER BY revenue_cents DESC, sales DESC, clicks DESC
        LIMIT ?
        """,
        [*ids, max(1, min(30, int(limit or 12)))],
    ).fetchall()
    product_currency = "USD"
    if product_id != "all" and ids:
        product_row = conn.execute("SELECT currency FROM products WHERE id = ?", (ids[0],)).fetchone()
        if product_row:
            product_currency = product_row["currency"]
    output = []
    for row in rows:
        item = row_to_dict(row)
        item["conversion"] = round_value(safe_divide(item["sales"], item["clicks"]))
        item["revenue"] = money_payload(item["revenue_cents"], product_currency)
        output.append(item)
    return output


def load_content_radar_context(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    dashboard = load_dashboard_summary(db_path, product_id=product_id, date_range=date_range)
    products = load_product_rows(db_path, product_id=product_id)
    refund_actions = get_refund_prevention_actions_tool(db_path, product_id=product_id, date_range=date_range)
    with closing(connect_readonly(db_path)) as conn:
        utm_rows = load_utm_rows(conn, metrics["product_ids"], product_id=product_id)
    return {
        "metrics": metrics,
        "dashboard": dashboard,
        "products": products,
        "utm_rows": utm_rows,
        "refund_actions": refund_actions,
    }


def product_keyword_score(product: dict[str, Any], trend: dict[str, Any]) -> int:
    category = str(product.get("category") or "").lower()
    tags = set(parse_tags(product))
    score = 0
    if any(keyword in category for keyword in trend["category_keywords"]):
        score += 3
    score += min(4, sum(1 for keyword in trend["tag_keywords"] if keyword in tags))
    if not category and "templates" in trend["tag_keywords"]:
        score += 1
    return score


def source_keyword_score(sources: list[dict[str, Any]], trend: dict[str, Any]) -> int:
    score = 0
    for source in sources[:4]:
        name = str(source.get("name") or "").lower()
        if any(keyword in name for keyword in trend["source_keywords"]):
            score += 2
            if int(source.get("sales") or 0) >= 5:
                score += 1
    return score


def trend_channel(trend: dict[str, Any], sources: list[dict[str, Any]], utm_rows: list[dict[str, Any]]) -> str:
    candidates = trend["channels"]
    source_names = [str(source.get("name") or "").lower() for source in sources]
    utm_names = [f"{row.get('source')} {row.get('medium')}".lower() for row in utm_rows]
    for channel in candidates:
        lower_channel = channel.lower()
        if any(lower_channel in name or name in lower_channel for name in source_names + utm_names):
            return channel
    return candidates[0]


def best_utm_for_channel(channel: str, utm_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    defaults = CHANNEL_DEFAULTS.get(channel, {})
    expected_source = defaults.get("source", "").lower()
    expected_medium = defaults.get("medium", "").lower()
    for row in utm_rows:
        source = str(row.get("source") or "").lower()
        medium = str(row.get("medium") or "").lower()
        if expected_source and expected_source in source:
            return row
        if expected_medium and expected_medium in medium:
            return row
    return utm_rows[0] if utm_rows else None


def campaign_name(trend: dict[str, Any], channel: str, product: dict[str, Any], utm_row: dict[str, Any] | None) -> str:
    if utm_row:
        seed = f"{utm_row['source']}_{utm_row['medium']}_{trend['utm_stem']}"
    else:
        defaults = CHANNEL_DEFAULTS.get(channel, {"source": channel, "medium": "content"})
        seed = f"{defaults['source']}_{defaults['medium']}_{trend['utm_stem']}"
    product_stem = slugify(str(product.get("name") or product.get("id") or "portfolio"))[:28]
    return slugify(f"content_radar_{product_stem}_{seed}")[:80]


def trend_score(
    trend: dict[str, Any],
    product: dict[str, Any],
    metrics: dict[str, Any],
    dashboard: dict[str, Any],
) -> float:
    source_score = source_keyword_score(metrics["current_sources"], trend)
    keyword_score = product_keyword_score(product, trend)
    current = metrics["current"]
    derived = metrics["derived"]
    discovery_score = 2 if "discover" in " ".join(trend["source_keywords"]) and current["discover_impressions"] >= 500 else 0
    utm_score = 1 if dashboard.get("utm_links") else 0
    conversion_room = 2 if derived["conversion_delta_percent"] < 0 or derived["current_conversion"] < 0.04 else 0
    refund_penalty = 1 if derived["current_refund_rate"] >= 0.08 and "compatibility" not in trend["risk"].lower() else 0
    return float(keyword_score + source_score + discovery_score + utm_score + conversion_room - refund_penalty)


def evidence_for_trend(
    metrics: dict[str, Any],
    dashboard: dict[str, Any],
    utm_row: dict[str, Any] | None,
    refund_actions: list[dict[str, Any]],
) -> list[dict[str, str]]:
    current = metrics["current"]
    derived = metrics["derived"]
    top_source = metrics["current_sources"][0] if metrics["current_sources"] else {}
    top_utm = utm_row or (dashboard.get("utm_links") or [{}])[0]
    evidence = [
        {
            "label": "Current run",
            "value": f"{current['views']:,} views / {current['sales']:,} sales",
            "comparison": f"{format_percent(derived['current_conversion'])} conversion",
        },
        {
            "label": "Top source",
            "value": str(top_source.get("name") or "No source"),
            "comparison": f"{int(top_source.get('sales') or 0):,} sales",
        },
    ]
    if top_utm:
        evidence.append(
            {
                "label": "Tracked UTM",
                "value": f"{top_utm.get('source')} / {top_utm.get('medium')}",
                "comparison": f"{top_utm.get('campaign')} at {format_percent(top_utm.get('conversion') or safe_divide(top_utm.get('sales') or 0, top_utm.get('clicks') or 0))}",
            }
        )
    if refund_actions:
        evidence.append(
            {
                "label": "Refund check",
                "value": refund_actions[0]["title"],
                "comparison": "check before scaling",
            }
        )
    return evidence


def expected_kpi_payload(metrics: dict[str, Any], utm_row: dict[str, Any] | None, trend: dict[str, Any]) -> dict[str, Any]:
    derived = metrics["derived"]
    current_conversion = derived["current_conversion"]
    baseline_utm_conversion = safe_divide(utm_row.get("sales") or 0, utm_row.get("clicks") or 0) if utm_row else 0
    baseline = baseline_utm_conversion or current_conversion
    target = min(0.25, baseline * 1.12 if baseline else current_conversion + 0.01)
    return {
        "name": trend["kpi"],
        "baseline": round_value(baseline),
        "baseline_formatted": format_percent(baseline),
        "target": round_value(target),
        "target_formatted": format_percent(target),
        "measurement_window": "next seeded analytics period",
    }


def draft_outline_payload(product: dict[str, Any], trend: dict[str, Any], channel: str, campaign: str) -> list[dict[str, Any]]:
    product_name = product.get("name") or "Selected product"
    primary_angle = trend["angles"][0]
    return [
        {
            "asset_type": "short_post",
            "channel": channel,
            "title": f"{product_name}: {trend['title']}",
            "copyable_outline": [
                f"Open with the buyer problem: {primary_angle}",
                "Show one specific before/after or included asset.",
                "Close with who it is for, who it is not for, and the tracked Gumroad link.",
            ],
            "draft_copy": (
                f"{primary_angle}\n\n"
                f"I built {product_name} for buyers who want the useful version without rebuilding the whole system. "
                "The preview should show exactly what is included, where it fits, and what to check before buying.\n\n"
                f"Track with utm_campaign={campaign}."
            ),
        },
        {
            "asset_type": "email",
            "channel": "Newsletter",
            "title": f"Show the use case before the product link",
            "copyable_outline": [
                "Subject: one concrete outcome, not the product name alone.",
                "Paragraph 1: describe the buyer situation.",
                "Paragraph 2: show the asset/workflow/example from the product.",
                "CTA: one tracked Gumroad link and a clear expectation note.",
            ],
            "draft_copy": (
                f"Subject: A faster way to handle {slugify(str(product_name)).replace('_', ' ')}\n\n"
                "I want to show the workflow before the sales page, because the useful part is easier to judge when you can see it in context.\n\n"
                f"{trend['angles'][1] if len(trend['angles']) > 1 else primary_angle}\n\n"
                f"Review the product page with utm_campaign={campaign}."
            ),
        },
        {
            "asset_type": "product_page_note",
            "channel": "Gumroad product page",
            "title": "Expectation-fit note",
            "copyable_outline": [
                "State the exact format and included assets.",
                "Name the buyer/use case the product is best for.",
                "Add compatibility, usage rights, or setup constraints before checkout.",
            ],
            "draft_copy": (
                f"{product_name} includes the assets described on this page and is best for buyers who need "
                f"{trend['fit_rationale'].lower()} Check the included files, compatibility notes, and examples before buying."
            ),
        },
    ]


def risk_payload(metrics: dict[str, Any], refund_actions: list[dict[str, Any]], trend: dict[str, Any]) -> list[dict[str, str]]:
    risks = [{"label": "Trend risk", "detail": trend["risk"]}]
    if metrics["derived"]["current_refund_rate"] >= 0.08:
        risks.append(
            {
                "label": "Refund pressure",
                "detail": f"Seeded refund rate is {format_percent(metrics['derived']['current_refund_rate'])}; clarify expectations before broadening reach.",
            }
        )
    if refund_actions:
        risks.append({"label": "Refund check", "detail": refund_actions[0]["recommended_action"]})
    if metrics["product"]["id"] == "all":
        risks.append({"label": "Portfolio blend", "detail": "All-products output mixes categories; validate the plan against one product before using copy."})
    return risks


def build_trend_record(
    db_path: Path | str,
    product_id: str,
    date_range: str,
    product: dict[str, Any],
    trend: dict[str, Any],
) -> dict[str, Any]:
    metrics = build_metrics(db_path, product_id=product["id"], date_range=date_range)
    dashboard = load_dashboard_summary(db_path, product_id=product["id"], date_range=date_range)
    refund_actions = get_refund_prevention_actions_tool(db_path, product_id=product["id"], date_range=date_range)
    with closing(connect_readonly(db_path)) as conn:
        utm_rows = load_utm_rows(conn, [product["id"]], product_id=product["id"])
    channel = trend_channel(trend, metrics["current_sources"], utm_rows)
    utm_row = best_utm_for_channel(channel, utm_rows)
    campaign = campaign_name(trend, channel, product, utm_row)
    score = trend_score(trend, product, metrics, dashboard)
    fit_score = max(0.0, min(100.0, score * 5))
    return {
        "id": f"{product['id']}::{trend['id']}",
        "trend_id": trend["id"],
        "product_id": product["id"],
        "product_name": product["name"],
        "title": trend["title"],
        "trend_angle": trend["angles"][0],
        "angles": trend["angles"],
        "fit_rationale": trend["fit_rationale"],
        "channel": channel,
        "campaign_utm_name": campaign,
        "utm": {
            "source": (utm_row or CHANNEL_DEFAULTS.get(channel, {})).get("source", slugify(channel)),
            "medium": (utm_row or CHANNEL_DEFAULTS.get(channel, {})).get("medium", "content"),
            "campaign": campaign,
            "based_on_seeded_campaign": utm_row.get("campaign") if utm_row else None,
        },
        "expected_kpi": expected_kpi_payload(metrics, utm_row, trend),
        "evidence": evidence_for_trend(metrics, dashboard, utm_row, refund_actions),
        "risks": risk_payload(metrics, refund_actions, trend),
        "draft_outlines": draft_outline_payload(product, trend, channel, campaign),
        "score": round_value(fit_score, 2),
        "raw_score": round_value(score, 2),
        "score_formatted": f"{round_value(fit_score, 0):.0f}/100",
        "read_only": True,
    }


def derived_trend_records(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> list[dict[str, Any]]:
    products = load_product_rows(db_path, product_id=product_id)
    records: list[dict[str, Any]] = []
    for product in products:
        for trend in TREND_LIBRARY:
            score = product_keyword_score(product, trend)
            if score > 0 or trend["id"] == "discover-fit-refresh":
                records.append(build_trend_record(db_path, product_id, date_range, product, trend))
    return sorted(records, key=lambda item: (item["score"], item["expected_kpi"]["target"]), reverse=True)


def summarize_channels(trends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(trend["channel"] for trend in trends)
    return [{"channel": channel, "trend_count": count} for channel, count in counts.most_common()]


def summarize_opportunities(trends: list[dict[str, Any]]) -> list[dict[str, str]]:
    output = []
    for trend in trends[:3]:
        output.append(
            {
                "title": trend["title"],
                "product": trend["product_name"],
                "channel": trend["channel"],
                "why": trend["fit_rationale"],
                "utm_campaign": trend["campaign_utm_name"],
            }
        )
    return output


def get_content_radar_summary(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    context = load_content_radar_context(db_path, product_id=product_id, date_range=date_range)
    trends = derived_trend_records(db_path, product_id=product_id, date_range=date_range)
    metrics = context["metrics"]
    dashboard = context["dashboard"]
    top_utm = dashboard.get("utm_links", [{}])[0] if dashboard.get("utm_links") else {}
    return {
        "product": metrics["product"],
        "date_range": date_range,
        "trend_count": len(trends),
        "top_opportunities": summarize_opportunities(trends),
        "channel_mix": summarize_channels(trends),
        "analytics_baseline": {
            "views": metrics["current"]["views"],
            "sales": metrics["current"]["sales"],
            "revenue": money_payload(metrics["current"]["revenue_cents"], metrics["product"]["currency"]),
            "conversion": metrics["derived"]["current_conversion"],
            "conversion_formatted": format_percent(metrics["derived"]["current_conversion"]),
            "refund_rate": metrics["derived"]["current_refund_rate"],
            "refund_rate_formatted": format_percent(metrics["derived"]["current_refund_rate"]),
            "top_source": metrics["current_sources"][0] if metrics["current_sources"] else None,
            "top_utm": top_utm or None,
        },
        "refund_checks": context["refund_actions"][:3],
        "read_only": True,
        "boundary": "Seeded local Content Radar only; no web searches, posting, emails, product edits, refunds, or external API calls are performed.",
    }


def list_content_trends(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    limit: int | str = DEFAULT_TREND_LIMIT,
) -> list[dict[str, Any]]:
    return derived_trend_records(db_path, product_id=product_id, date_range=date_range)[: clamp_limit(limit)]


def build_marketing_plan(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    horizon_weeks: int | str = DEFAULT_PLAN_WEEKS,
) -> dict[str, Any]:
    weeks = normalize_plan_weeks(horizon_weeks)
    summary = get_content_radar_summary(db_path, product_id=product_id, date_range=date_range)
    trends = list_content_trends(db_path, product_id=product_id, date_range=date_range, limit=min(4, weeks))
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    baseline_sales = metrics["current"]["sales"]
    baseline_conversion = metrics["derived"]["current_conversion"]
    plan_steps = []
    for index, trend in enumerate(trends, start=1):
        plan_steps.append(
            {
                "week": index,
                "focus": trend["title"],
                "product_id": trend["product_id"],
                "channel": trend["channel"],
                "campaign_utm_name": trend["campaign_utm_name"],
                "move": trend["trend_angle"],
                "draft_to_prepare": trend["draft_outlines"][0],
                "expected_kpi": trend["expected_kpi"],
                "risk_check": trend["risks"][0],
                "action_ready": True,
            }
        )
    while len(plan_steps) < weeks:
        week = len(plan_steps) + 1
        previous = plan_steps[-1] if plan_steps else None
        plan_steps.append(
            {
                "week": week,
                "focus": "Measure and tighten attribution",
                "product_id": product_id,
                "channel": previous["channel"] if previous else "Newsletter",
                "campaign_utm_name": f"content_radar_week_{week}_measurement",
                "move": "Compare tracked clicks, sales, conversion, and refunds before starting another broad campaign.",
                "draft_to_prepare": {
                    "asset_type": "measurement_note",
                    "channel": "Internal review",
                    "title": "Campaign readout",
                    "copyable_outline": [
                        "List tracked campaign clicks, sales, and conversion.",
                        "Compare refund rate against the baseline.",
                        "Keep the winning message; retire weak channels before scaling.",
                    ],
                },
                "expected_kpi": {
                    "name": "attribution cleanliness",
                    "baseline": round_value(baseline_conversion),
                    "baseline_formatted": format_percent(baseline_conversion),
                    "target": round_value(min(0.25, baseline_conversion * 1.05 if baseline_conversion else 0.02)),
                    "target_formatted": format_percent(min(0.25, baseline_conversion * 1.05 if baseline_conversion else 0.02)),
                    "measurement_window": "weekly seeded review",
                },
                "risk_check": {
                    "label": "Attribution risk",
                    "detail": "Do not treat direct traffic as campaign lift unless the link is tracked.",
                },
                "action_ready": True,
            }
        )
    target_sales = round(baseline_sales * (1 + 0.04 * weeks))
    return {
        "product": summary["product"],
        "date_range": date_range,
        "horizon_weeks": weeks,
        "objective": (
            f"Run {weeks} content tests tied to tracked UTM names, aiming to move from "
            f"{baseline_sales:,} seeded sales toward about {target_sales:,} sales while holding refund quality steady."
        ),
        "baseline": summary["analytics_baseline"],
        "plan_steps": plan_steps,
        "trend_backlog": trends,
        "measurement_rules": [
            "Use one UTM campaign name per content angle.",
            "Review conversion, sales, refund rate, and top-source mix before reusing a campaign.",
            "Do not send, post, edit listings, or refund buyers from this module.",
        ],
        "read_only": True,
    }


def find_trend(trends: list[dict[str, Any]], trend_id: str | None = None, channel: str | None = None) -> dict[str, Any] | None:
    if trend_id:
        normalized = trend_id.strip().lower()
        for trend in trends:
            if trend["id"].lower() == normalized or trend["trend_id"].lower() == normalized:
                return trend
    if channel:
        normalized_channel = channel.strip().lower()
        for trend in trends:
            if trend["channel"].lower() == normalized_channel:
                return trend
    return trends[0] if trends else None


def draft_campaign_assets(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    trend_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    trends = list_content_trends(db_path, product_id=product_id, date_range=date_range, limit=MAX_TREND_LIMIT)
    trend = find_trend(trends, trend_id=trend_id, channel=channel)
    if not trend:
        return {
            "found": False,
            "trend_id": trend_id,
            "channel": channel,
            "assets": [],
            "read_only": True,
        }
    return {
        "found": True,
        "trend": {
            "id": trend["id"],
            "trend_id": trend["trend_id"],
            "title": trend["title"],
            "product_id": trend["product_id"],
            "product_name": trend["product_name"],
            "channel": trend["channel"],
            "campaign_utm_name": trend["campaign_utm_name"],
            "expected_kpi": trend["expected_kpi"],
            "risks": trend["risks"],
        },
        "assets": trend["draft_outlines"],
        "review_checklist": [
            "Confirm the copy matches the product contents and support boundaries.",
            "Confirm the UTM campaign name is unique for this content angle.",
            "Check refund pressure before widening reach.",
        ],
        "read_only": True,
        "boundary": "Draft assets are campaign-ready outlines with explicit execution steps.",
    }


def content_radar_overview_sentence(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> str:
    summary = get_content_radar_summary(db_path, product_id=product_id, date_range=date_range)
    opportunity = summary["top_opportunities"][0] if summary["top_opportunities"] else None
    if not opportunity:
        return f"{summary['product']['name']} has no seeded Content Radar trend records for this selection."
    return (
        f"{summary['product']['name']} has {summary['trend_count']} seeded Content Radar trends; "
        f"the top opportunity is {opportunity['title']} for {opportunity['product']} on "
        f"{opportunity['channel']} using utm_campaign={opportunity['utm_campaign']}."
    )


def get_content_radar_summary_tool(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    return get_content_radar_summary(db_path, product_id=product_id, date_range=date_range)


def list_content_trends_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    limit: int | str = DEFAULT_TREND_LIMIT,
) -> list[dict[str, Any]]:
    return list_content_trends(db_path, product_id=product_id, date_range=date_range, limit=limit)


def build_marketing_plan_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    horizon_weeks: int | str = DEFAULT_PLAN_WEEKS,
) -> dict[str, Any]:
    return build_marketing_plan(db_path, product_id=product_id, date_range=date_range, horizon_weeks=horizon_weeks)


def draft_campaign_assets_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    trend_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    return draft_campaign_assets(
        db_path,
        product_id=product_id,
        date_range=date_range,
        trend_id=trend_id,
        channel=channel,
    )
