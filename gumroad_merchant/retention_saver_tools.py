"""Review-only Retention Saver estimators for Gumroad issue #4884.

This module uses seeded/synthetic demo analytics to estimate whether offering
buyers a membership pause could reduce cancellations. It never edits
subscriptions, charges buyers, sends email, or contacts buyers.
"""

from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

from gumroad_merchant.analytics_tools import (
    build_metrics,
    date_scale,
    format_percent,
    money_payload,
    percent_delta,
    product_ids,
    round_value,
    safe_divide,
    scale_int,
)
from gumroad_merchant.database import connect_readonly, row_to_dict


DEFAULT_PAUSE_SAVE_RATE = 0.096
CONSERVATIVE_SAVE_RATE_MULTIPLIER = 0.75
OPTIMISTIC_SAVE_RATE_MULTIPLIER = 1.25
READ_ONLY_BOUNDARY = (
    "Review-only seeded estimator. No subscription pause, cancellation, charge, "
    "email, webhook, or buyer contact is performed."
)


def source_context() -> dict[str, Any]:
    return {
        "source": "Gumroad issue #4884",
        "issue_id": 4884,
        "issue_url": "https://github.com/antiwork/gumroad/issues/4884",
        "issue_title": "Let buyers pause memberships instead of cancelling",
        "prototype_scope": "Synthetic Retention Saver estimator for the local Gumroad Merchant demo DB.",
        "data_sources": [
            "products",
            "period_metrics",
            "churn_metrics",
            "customer_sales recurring-charge samples",
            "refund_cases",
        ],
        "read_only_boundary": READ_ONLY_BOUNDARY,
    }


def normalize_save_rate(save_rate: float | int | str | None = None) -> float:
    if save_rate is None:
        return DEFAULT_PAUSE_SAVE_RATE
    try:
        if isinstance(save_rate, str):
            value = save_rate.strip()
            is_percent = value.endswith("%")
            parsed = float(value.rstrip("%").strip())
            if is_percent or parsed > 1:
                parsed = parsed / 100
        else:
            parsed = float(save_rate)
    except (TypeError, ValueError):
        return DEFAULT_PAUSE_SAVE_RATE
    return round_value(max(0.0, min(0.4, parsed)), 4)


def bounded_limit(limit: int | str | None, default: int = 10, maximum: int = 25) -> int:
    try:
        value = int(limit or default)
    except (TypeError, ValueError):
        value = default
    return max(1, min(maximum, value))


def _scaled(value: Any, scale: float) -> int:
    return scale_int(int(value or 0), scale)


def _load_retention_rows(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> list[dict[str, Any]]:
    scale = date_scale(date_range)
    base_scale = scale ** 0.5
    with closing(connect_readonly(db_path)) as conn:
        ids = product_ids(conn, product_id)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT
                p.id,
                p.name,
                p.creator,
                p.category,
                p.price_cents,
                p.currency,
                c.active_start,
                c.new_subscriptions,
                c.canceled,
                c.previous_active_start,
                c.previous_new_subscriptions,
                c.previous_canceled,
                c.revenue_lost_cents,
                pm_current.sales AS current_sales,
                pm_current.revenue_cents AS current_revenue_cents,
                pm_current.refunds AS current_refunds,
                pm_current.refund_cents AS current_refund_cents,
                pm_previous.sales AS previous_sales,
                pm_previous.revenue_cents AS previous_revenue_cents,
                pm_previous.refunds AS previous_refunds,
                pm_previous.refund_cents AS previous_refund_cents
            FROM products p
            JOIN churn_metrics c ON c.product_id = p.id
            LEFT JOIN period_metrics pm_current
                ON pm_current.product_id = p.id AND pm_current.period = 'current'
            LEFT JOIN period_metrics pm_previous
                ON pm_previous.product_id = p.id AND pm_previous.period = 'previous'
            WHERE p.id IN ({placeholders})
            ORDER BY p.id
            """,
            ids,
        ).fetchall()
        refund_rows = conn.execute(
            f"""
            SELECT
                product_id,
                COUNT(*) AS case_count,
                SUM(amount_cents) AS case_amount_cents,
                AVG(risk_score) AS average_case_risk,
                SUM(CASE WHEN case_type = 'chargeback_dispute' THEN 1 ELSE 0 END) AS dispute_count
            FROM refund_cases
            WHERE product_id IN ({placeholders})
            GROUP BY product_id
            """,
            ids,
        ).fetchall()
        sample_rows = conn.execute(
            f"""
            SELECT
                product_id,
                COUNT(*) AS sample_sale_rows,
                SUM(recurring_charge) AS recurring_sample_rows,
                SUM(refunded) AS refunded_sample_rows,
                SUM(do_not_contact) AS do_not_contact_rows,
                SUM(net_total_cents) AS sample_net_revenue_cents
            FROM customer_sales
            WHERE product_id IN ({placeholders})
            GROUP BY product_id
            """,
            ids,
        ).fetchall()
        source_rows = conn.execute(
            f"""
            SELECT product_id, name, views, sales, revenue_cents
            FROM traffic_sources
            WHERE product_id IN ({placeholders}) AND period = 'current'
            ORDER BY product_id ASC, revenue_cents DESC, sales DESC
            """,
            ids,
        ).fetchall()

    refund_by_product = {row["product_id"]: row_to_dict(row) for row in refund_rows}
    sample_by_product = {row["product_id"]: row_to_dict(row) for row in sample_rows}
    top_source_by_product: dict[str, dict[str, Any]] = {}
    for row in source_rows:
        if row["product_id"] not in top_source_by_product:
            top_source_by_product[row["product_id"]] = row_to_dict(row)

    output = []
    for row in rows:
        refund = refund_by_product.get(row["id"], {})
        sample = sample_by_product.get(row["id"], {})
        top_source = top_source_by_product.get(row["id"], {})
        active_start = _scaled(row["active_start"], base_scale)
        new_subscriptions = _scaled(row["new_subscriptions"], scale)
        canceled = _scaled(row["canceled"], scale)
        previous_active_start = _scaled(row["previous_active_start"], base_scale)
        previous_new_subscriptions = _scaled(row["previous_new_subscriptions"], scale)
        previous_canceled = _scaled(row["previous_canceled"], scale)
        revenue_lost_cents = _scaled(row["revenue_lost_cents"], scale)
        current_sales = _scaled(row["current_sales"], scale)
        current_revenue_cents = _scaled(row["current_revenue_cents"], scale)
        current_refunds = _scaled(row["current_refunds"], scale)
        current_refund_cents = _scaled(row["current_refund_cents"], scale)
        previous_sales = _scaled(row["previous_sales"], scale)
        previous_refunds = _scaled(row["previous_refunds"], scale)
        churn_base = active_start + new_subscriptions
        previous_churn_base = previous_active_start + previous_new_subscriptions
        churn_rate = round_value(safe_divide(canceled, churn_base))
        previous_churn_rate = round_value(safe_divide(previous_canceled, previous_churn_base))
        refund_rate = round_value(safe_divide(current_refunds, current_sales))
        previous_refund_rate = round_value(safe_divide(previous_refunds, previous_sales))
        average_monthly_value_cents = round(safe_divide(revenue_lost_cents, canceled)) if canceled else int(row["price_cents"] or 0)
        item = {
            "product": {
                "id": row["id"],
                "name": row["name"],
                "creator": row["creator"],
                "category": row["category"],
                "price_cents": int(row["price_cents"] or 0),
                "price": money_payload(int(row["price_cents"] or 0), row["currency"]),
                "currency": row["currency"],
            },
            "active_start": active_start,
            "new_subscriptions": new_subscriptions,
            "canceled": canceled,
            "churn_base": churn_base,
            "churn_rate": churn_rate,
            "churn_rate_formatted": format_percent(churn_rate),
            "previous_active_start": previous_active_start,
            "previous_new_subscriptions": previous_new_subscriptions,
            "previous_canceled": previous_canceled,
            "previous_churn_base": previous_churn_base,
            "previous_churn_rate": previous_churn_rate,
            "previous_churn_rate_formatted": format_percent(previous_churn_rate),
            "churn_delta_percent": round_value(percent_delta(churn_rate, previous_churn_rate)),
            "revenue_lost_cents": revenue_lost_cents,
            "revenue_lost": money_payload(revenue_lost_cents, row["currency"]),
            "average_monthly_value_cents": average_monthly_value_cents,
            "average_monthly_value": money_payload(average_monthly_value_cents, row["currency"]),
            "current_sales": current_sales,
            "current_revenue_cents": current_revenue_cents,
            "current_revenue": money_payload(current_revenue_cents, row["currency"]),
            "current_refunds": current_refunds,
            "current_refund_cents": current_refund_cents,
            "current_refund_amount": money_payload(current_refund_cents, row["currency"]),
            "current_refund_rate": refund_rate,
            "current_refund_rate_formatted": format_percent(refund_rate),
            "previous_refund_rate": previous_refund_rate,
            "previous_refund_rate_formatted": format_percent(previous_refund_rate),
            "refund_case_count": int(refund.get("case_count") or 0),
            "refund_case_amount_cents": int(refund.get("case_amount_cents") or 0),
            "refund_case_amount": money_payload(int(refund.get("case_amount_cents") or 0), row["currency"]),
            "average_refund_case_risk": round_value(float(refund.get("average_case_risk") or 0), 2),
            "chargeback_dispute_count": int(refund.get("dispute_count") or 0),
            "sample_sale_rows": int(sample.get("sample_sale_rows") or 0),
            "recurring_sample_rows": int(sample.get("recurring_sample_rows") or 0),
            "refunded_sample_rows": int(sample.get("refunded_sample_rows") or 0),
            "do_not_contact_rows": int(sample.get("do_not_contact_rows") or 0),
            "sample_net_revenue_cents": int(sample.get("sample_net_revenue_cents") or 0),
            "top_source": {
                "name": top_source.get("name", ""),
                "views": _scaled(top_source.get("views"), scale),
                "sales": _scaled(top_source.get("sales"), scale),
                "revenue_cents": _scaled(top_source.get("revenue_cents"), scale),
                "revenue": money_payload(_scaled(top_source.get("revenue_cents"), scale), row["currency"]),
            },
        }
        output.append(item)
    return output


def _aggregate_retention(rows: list[dict[str, Any]], currency: str = "USD") -> dict[str, Any]:
    totals: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        for key in (
            "active_start",
            "new_subscriptions",
            "canceled",
            "previous_active_start",
            "previous_new_subscriptions",
            "previous_canceled",
            "revenue_lost_cents",
            "current_sales",
            "current_revenue_cents",
            "current_refunds",
            "current_refund_cents",
            "refund_case_count",
            "refund_case_amount_cents",
            "chargeback_dispute_count",
            "sample_sale_rows",
            "recurring_sample_rows",
            "refunded_sample_rows",
            "do_not_contact_rows",
        ):
            totals[key] += int(row.get(key) or 0)
    churn_base = totals["active_start"] + totals["new_subscriptions"]
    previous_churn_base = totals["previous_active_start"] + totals["previous_new_subscriptions"]
    churn_rate = round_value(safe_divide(totals["canceled"], churn_base))
    previous_churn_rate = round_value(safe_divide(totals["previous_canceled"], previous_churn_base))
    refund_rate = round_value(safe_divide(totals["current_refunds"], totals["current_sales"]))
    average_monthly_value_cents = round(safe_divide(totals["revenue_lost_cents"], totals["canceled"])) if totals["canceled"] else 0
    return {
        "active_start": totals["active_start"],
        "new_subscriptions": totals["new_subscriptions"],
        "canceled": totals["canceled"],
        "churn_base": churn_base,
        "churn_rate": churn_rate,
        "churn_rate_formatted": format_percent(churn_rate),
        "previous_active_start": totals["previous_active_start"],
        "previous_new_subscriptions": totals["previous_new_subscriptions"],
        "previous_canceled": totals["previous_canceled"],
        "previous_churn_base": previous_churn_base,
        "previous_churn_rate": previous_churn_rate,
        "previous_churn_rate_formatted": format_percent(previous_churn_rate),
        "churn_delta_percent": round_value(percent_delta(churn_rate, previous_churn_rate)),
        "revenue_lost_cents": totals["revenue_lost_cents"],
        "revenue_lost": money_payload(totals["revenue_lost_cents"], currency),
        "average_monthly_value_cents": average_monthly_value_cents,
        "average_monthly_value": money_payload(average_monthly_value_cents, currency),
        "current_revenue_cents": totals["current_revenue_cents"],
        "current_revenue": money_payload(totals["current_revenue_cents"], currency),
        "current_sales": totals["current_sales"],
        "current_refunds": totals["current_refunds"],
        "current_refund_cents": totals["current_refund_cents"],
        "current_refund_amount": money_payload(totals["current_refund_cents"], currency),
        "current_refund_rate": refund_rate,
        "current_refund_rate_formatted": format_percent(refund_rate),
        "refund_case_count": totals["refund_case_count"],
        "refund_case_amount_cents": totals["refund_case_amount_cents"],
        "refund_case_amount": money_payload(totals["refund_case_amount_cents"], currency),
        "chargeback_dispute_count": totals["chargeback_dispute_count"],
        "sample_sale_rows": totals["sample_sale_rows"],
        "recurring_sample_rows": totals["recurring_sample_rows"],
        "refunded_sample_rows": totals["refunded_sample_rows"],
        "do_not_contact_rows": totals["do_not_contact_rows"],
    }


def _confidence_label(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"


def _confidence_payload(rows: list[dict[str, Any]], date_range: str = "30") -> dict[str, Any]:
    canceled = sum(int(row["canceled"]) for row in rows)
    recurring_samples = sum(int(row["recurring_sample_rows"]) for row in rows)
    revenue_lost_cents = sum(int(row["revenue_lost_cents"]) for row in rows)
    score = 0.32
    basis = ["Synthetic seeded churn table is available"]
    if canceled >= 10:
        score += 0.18
        basis.append("At least 10 seeded cancellations in scope")
    elif canceled >= 3:
        score += 0.12
        basis.append("At least 3 seeded cancellations in scope")
    if recurring_samples:
        score += 0.12
        basis.append("Customer export samples include recurring-charge rows")
    if revenue_lost_cents:
        score += 0.12
        basis.append("Revenue-lost estimate is present in churn metrics")
    if str(date_range or "30") == "30":
        score += 0.06
        basis.append("Using the native 30-day demo window")
    elif str(date_range or "30") in {"90", "all"}:
        basis.append("Date range is scaled from seeded 30-day facts")
    score = min(0.82, score)
    return {"label": _confidence_label(score), "score": round_value(score, 2), "basis": basis}


def _risk_level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 50:
        return "elevated"
    if score >= 25:
        return "watch"
    return "low"


def _risk_score(row: dict[str, Any]) -> int:
    churn_delta = max(0.0, float(row["churn_delta_percent"]))
    score = 8
    score += min(42, row["churn_rate"] * 520)
    score += min(18, churn_delta * 14)
    score += min(16, row["current_refund_rate"] * 140)
    score += min(9, row["refund_case_count"] * 3)
    score += 5 if row["recurring_sample_rows"] else 0
    score += 4 if row["revenue_lost_cents"] else 0
    if row["canceled"] <= 0:
        score = min(score, 18)
    return max(0, min(100, round(score)))


def _risk_drivers(row: dict[str, Any]) -> list[str]:
    drivers = []
    if row["canceled"]:
        drivers.append(
            f"{row['canceled']:,} cancellations from a {row['churn_base']:,} membership base "
            f"({row['churn_rate_formatted']} churn)"
        )
    if row["previous_churn_rate"] and row["churn_rate"] > row["previous_churn_rate"] * 1.2:
        drivers.append(f"Churn is up from {row['previous_churn_rate_formatted']} in the previous window")
    if row["current_refund_rate"] >= 0.06:
        drivers.append(f"Refund pressure is {row['current_refund_rate_formatted']} of current sales")
    if row["refund_case_count"]:
        drivers.append(f"{row['refund_case_count']} seeded Refund Ops cases overlap this product")
    if row["recurring_sample_rows"]:
        drivers.append(f"{row['recurring_sample_rows']} recurring-charge rows appear in the synthetic customer export")
    if not drivers:
        drivers.append("No elevated cancellation pattern in the seeded churn metrics")
    return drivers


def _recommended_pause_offer(row: dict[str, Any]) -> dict[str, Any]:
    if row["canceled"] <= 0:
        return {
            "option_id": "monitor-only",
            "label": "Monitor only",
            "reason": "No seeded cancellations are present for this product.",
        }
    if row["churn_rate"] >= 0.06 or row["current_refund_rate"] >= 0.08 or row["chargeback_dispute_count"] > 0:
        return {
            "option_id": "pause-3-month",
            "label": "3-month pause",
            "reason": "Use for buyers who likely need time, setup help, or product-fit review before deciding.",
        }
    return {
        "option_id": "pause-1-month",
        "label": "1-month pause",
        "reason": "Use as the default low-friction alternative at cancellation intent.",
    }


def pause_offer_options(
    revenue_lost_cents: int = 0,
    currency: str = "USD",
    save_rate: float | int | str | None = None,
) -> list[dict[str, Any]]:
    normalized_rate = normalize_save_rate(save_rate)
    estimated_saved_cents = round(int(revenue_lost_cents or 0) * normalized_rate)
    return [
        {
            "id": "pause-1-month",
            "label": "1-month pause",
            "pause_months": 1,
            "save_rate_assumption": normalized_rate,
            "save_rate_assumption_formatted": format_percent(normalized_rate),
            "estimated_revenue_saved_cents": estimated_saved_cents,
            "estimated_revenue_saved": money_payload(estimated_saved_cents, currency),
            "estimated_revenue_deferred_during_pause_cents": estimated_saved_cents,
            "estimated_revenue_deferred_during_pause": money_payload(estimated_saved_cents, currency),
            "confidence": "medium",
            "best_for": "Buyers who are budget-constrained or temporarily not using the membership.",
            "merchant_review_prompt": "Review a cancellation-screen draft that offers one skipped month before a buyer confirms cancellation.",
            "review_only": True,
        },
        {
            "id": "pause-3-month",
            "label": "3-month pause",
            "pause_months": 3,
            "save_rate_assumption": normalized_rate,
            "save_rate_assumption_formatted": format_percent(normalized_rate),
            "estimated_revenue_saved_cents": estimated_saved_cents,
            "estimated_revenue_saved": money_payload(estimated_saved_cents, currency),
            "estimated_revenue_deferred_during_pause_cents": estimated_saved_cents * 3,
            "estimated_revenue_deferred_during_pause": money_payload(estimated_saved_cents * 3, currency),
            "confidence": "low",
            "best_for": "Buyers who need a longer break because of onboarding friction, seasonality, or product-fit uncertainty.",
            "merchant_review_prompt": "Review eligibility and messaging carefully because this option defers more near-term revenue.",
            "review_only": True,
        },
    ]


def _estimate_from_rows(
    rows: list[dict[str, Any]],
    currency: str = "USD",
    save_rate: float | int | str | None = None,
    date_range: str = "30",
) -> dict[str, Any]:
    normalized_rate = normalize_save_rate(save_rate)
    revenue_lost_cents = sum(int(row["revenue_lost_cents"]) for row in rows)
    canceled = sum(int(row["canceled"]) for row in rows)
    estimated_saved_cents = round(revenue_lost_cents * normalized_rate)
    conservative_rate = round_value(normalized_rate * CONSERVATIVE_SAVE_RATE_MULTIPLIER)
    optimistic_rate = round_value(normalized_rate * OPTIMISTIC_SAVE_RATE_MULTIPLIER)
    per_product = []
    for row in rows:
        saved_cents = round(row["revenue_lost_cents"] * normalized_rate)
        risk_score = _risk_score(row)
        per_product.append(
            {
                "product_id": row["product"]["id"],
                "product_name": row["product"]["name"],
                "canceled": row["canceled"],
                "revenue_lost_cents": row["revenue_lost_cents"],
                "revenue_lost": row["revenue_lost"],
                "estimated_saved_memberships": round_value(row["canceled"] * normalized_rate, 2),
                "estimated_revenue_saved_cents": saved_cents,
                "estimated_revenue_saved": money_payload(saved_cents, row["product"]["currency"]),
                "risk_score": risk_score,
                "risk_level": _risk_level(risk_score),
                "recommended_pause_offer": _recommended_pause_offer(row),
            }
        )
    per_product.sort(key=lambda item: (item["risk_score"], item["estimated_revenue_saved_cents"]), reverse=True)
    return {
        "date_range": date_range,
        "source_context": source_context(),
        "save_rate_assumption": normalized_rate,
        "save_rate_assumption_formatted": format_percent(normalized_rate),
        "method": "estimated_revenue_saved = seeded churn_metrics.revenue_lost_cents * pause save-rate assumption",
        "at_risk_cancellations": canceled,
        "estimated_saved_memberships": round_value(canceled * normalized_rate, 2),
        "revenue_at_risk_cents": revenue_lost_cents,
        "revenue_at_risk": money_payload(revenue_lost_cents, currency),
        "estimated_revenue_saved_cents": estimated_saved_cents,
        "estimated_revenue_saved": money_payload(estimated_saved_cents, currency),
        "scenario_range": {
            "conservative": {
                "save_rate": conservative_rate,
                "save_rate_formatted": format_percent(conservative_rate),
                "estimated_revenue_saved_cents": round(revenue_lost_cents * conservative_rate),
                "estimated_revenue_saved": money_payload(round(revenue_lost_cents * conservative_rate), currency),
            },
            "base": {
                "save_rate": normalized_rate,
                "save_rate_formatted": format_percent(normalized_rate),
                "estimated_revenue_saved_cents": estimated_saved_cents,
                "estimated_revenue_saved": money_payload(estimated_saved_cents, currency),
            },
            "optimistic": {
                "save_rate": optimistic_rate,
                "save_rate_formatted": format_percent(optimistic_rate),
                "estimated_revenue_saved_cents": round(revenue_lost_cents * optimistic_rate),
                "estimated_revenue_saved": money_payload(round(revenue_lost_cents * optimistic_rate), currency),
            },
        },
        "per_product": per_product,
        "confidence": _confidence_payload(rows, date_range=date_range),
        "read_only": True,
        "boundary": READ_ONLY_BOUNDARY,
    }


def list_cancellation_risks(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    limit: int = 10,
) -> list[dict[str, Any]]:
    rows = _load_retention_rows(db_path, product_id=product_id, date_range=date_range)
    risks = []
    for row in rows:
        risk_score = _risk_score(row)
        saved_cents = round(row["revenue_lost_cents"] * DEFAULT_PAUSE_SAVE_RATE)
        risks.append(
            {
                "id": f"retention-risk-{row['product']['id']}",
                "product": row["product"],
                "title": f"{row['product']['name']} cancellation pause review",
                "risk_score": risk_score,
                "risk_level": _risk_level(risk_score),
                "canceled": row["canceled"],
                "churn_rate": row["churn_rate"],
                "churn_rate_formatted": row["churn_rate_formatted"],
                "previous_churn_rate": row["previous_churn_rate"],
                "previous_churn_rate_formatted": row["previous_churn_rate_formatted"],
                "revenue_lost_cents": row["revenue_lost_cents"],
                "revenue_lost": row["revenue_lost"],
                "estimated_revenue_saved_cents": saved_cents,
                "estimated_revenue_saved": money_payload(saved_cents, row["product"]["currency"]),
                "save_rate_assumption": DEFAULT_PAUSE_SAVE_RATE,
                "save_rate_assumption_formatted": format_percent(DEFAULT_PAUSE_SAVE_RATE),
                "drivers": _risk_drivers(row),
                "refund_pressure": {
                    "refund_rate": row["current_refund_rate"],
                    "refund_rate_formatted": row["current_refund_rate_formatted"],
                    "refund_case_count": row["refund_case_count"],
                    "chargeback_dispute_count": row["chargeback_dispute_count"],
                },
                "membership_sample": {
                    "sample_sale_rows": row["sample_sale_rows"],
                    "recurring_sample_rows": row["recurring_sample_rows"],
                    "do_not_contact_rows": row["do_not_contact_rows"],
                    "privacy_note": "Synthetic export counts only; buyer names and emails are not returned.",
                },
                "top_source": row["top_source"],
                "recommended_pause_offer": _recommended_pause_offer(row),
                "recommended_review_steps": [
                    "Review whether the cancellation reason sounds temporary before showing a pause offer.",
                    "Check refund or chargeback cases before promising retention help.",
                    "Confirm the buyer can resume access cleanly after the pause window.",
                ],
                "source_context": source_context(),
                "review_only": True,
            }
        )
    risks.sort(key=lambda item: (item["risk_score"], item["estimated_revenue_saved_cents"]), reverse=True)
    return risks[: bounded_limit(limit)]


def estimate_pause_revenue_saved(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    save_rate: float | int | str | None = None,
) -> dict[str, Any]:
    rows = _load_retention_rows(db_path, product_id=product_id, date_range=date_range)
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    currency = metrics["product"].get("currency", "USD")
    return _estimate_from_rows(rows, currency=currency, save_rate=save_rate, date_range=date_range)


def get_retention_saver_summary(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
) -> dict[str, Any]:
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    rows = _load_retention_rows(db_path, product_id=product_id, date_range=date_range)
    currency = metrics["product"].get("currency", "USD")
    aggregate = _aggregate_retention(rows, currency=currency)
    estimate = _estimate_from_rows(rows, currency=currency, date_range=date_range)
    top_risks = list_cancellation_risks(db_path, product_id=product_id, date_range=date_range, limit=3)
    return {
        "product": metrics["product"],
        "date_range": date_range,
        "source_context": source_context(),
        "membership_churn": aggregate,
        "pause_revenue_estimate": {
            "save_rate_assumption": estimate["save_rate_assumption"],
            "save_rate_assumption_formatted": estimate["save_rate_assumption_formatted"],
            "estimated_saved_memberships": estimate["estimated_saved_memberships"],
            "estimated_revenue_saved_cents": estimate["estimated_revenue_saved_cents"],
            "estimated_revenue_saved": estimate["estimated_revenue_saved"],
            "scenario_range": estimate["scenario_range"],
        },
        "pause_offer_options": pause_offer_options(
            aggregate["revenue_lost_cents"],
            currency=currency,
            save_rate=DEFAULT_PAUSE_SAVE_RATE,
        ),
        "top_cancellation_risks": top_risks,
        "confidence": estimate["confidence"],
        "recommended_merchant_review_steps": [
            "Review the highest-risk products before adding any cancellation-screen pause copy.",
            "Keep pause offers opt-in and cancellation-intent-only; do not message buyers from this estimator.",
            "Decide whether 1-month or 3-month pauses are eligible for each membership product.",
            "Track pause offered, pause accepted, resumed, and later canceled as separate review metrics.",
        ],
        "risks": [
            "A pause can hide product-fit or onboarding problems if reasons are not reviewed.",
            "Paused memberships defer near-term revenue; saved revenue is counted only after a buyer resumes.",
            "Refund or chargeback cases should be reviewed before making a retention offer.",
            "The demo DB is seeded and synthetic, so these are planning estimates rather than production forecasts.",
        ],
        "read_only": True,
        "boundary": READ_ONLY_BOUNDARY,
    }


def build_pause_offer_plan(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
) -> dict[str, Any]:
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    rows = _load_retention_rows(db_path, product_id=product_id, date_range=date_range)
    currency = metrics["product"].get("currency", "USD")
    aggregate = _aggregate_retention(rows, currency=currency)
    estimate = _estimate_from_rows(rows, currency=currency, date_range=date_range)
    risks = list_cancellation_risks(db_path, product_id=product_id, date_range=date_range, limit=5)
    recommended_option_id = "pause-3-month" if any(risk["recommended_pause_offer"]["option_id"] == "pause-3-month" for risk in risks) else "pause-1-month"
    return {
        "product": metrics["product"],
        "date_range": date_range,
        "source_context": source_context(),
        "recommended_option_id": recommended_option_id,
        "offer_options": pause_offer_options(
            aggregate["revenue_lost_cents"],
            currency=currency,
            save_rate=DEFAULT_PAUSE_SAVE_RATE,
        ),
        "estimated_impact": {
            "at_risk_cancellations": estimate["at_risk_cancellations"],
            "revenue_at_risk": estimate["revenue_at_risk"],
            "estimated_saved_memberships": estimate["estimated_saved_memberships"],
            "estimated_revenue_saved": estimate["estimated_revenue_saved"],
            "save_rate_assumption_formatted": estimate["save_rate_assumption_formatted"],
            "method": estimate["method"],
        },
        "eligible_segments_to_review": [
            {
                "product_id": risk["product"]["id"],
                "product_name": risk["product"]["name"],
                "risk_level": risk["risk_level"],
                "suggested_offer": risk["recommended_pause_offer"],
                "estimated_revenue_saved": risk["estimated_revenue_saved"],
            }
            for risk in risks
            if risk["recommended_pause_offer"]["option_id"] != "monitor-only"
        ],
        "merchant_review_steps": [
            "Review cancellation reasons and classify them as temporary, product-fit, support, pricing, or duplicate purchase.",
            "Approve exact cancellation-screen copy for a 1-month pause and a 3-month pause.",
            "Define eligibility rules before implementation: active membership, no unresolved chargeback, no duplicate active pause.",
            "Confirm paused access, billing, resume date, and cancellation fallback behavior with engineering before shipping.",
            "Measure pause accepted, resumed, later canceled, and support-contact rate before expanding the offer.",
        ],
        "guardrails": [
            "Do not auto-pause memberships from this estimator.",
            "Do not email or contact buyers from this estimator.",
            "Do not count deferred pause months as saved revenue.",
            "Do not hide the normal cancellation path.",
        ],
        "confidence": estimate["confidence"],
        "read_only": True,
        "boundary": READ_ONLY_BOUNDARY,
    }


def retention_saver_overview_sentence(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
) -> str:
    summary = get_retention_saver_summary(db_path, product_id=product_id, date_range=date_range)
    churn = summary["membership_churn"]
    estimate = summary["pause_revenue_estimate"]
    product_name = summary["product"]["name"]
    return (
        f"{product_name} has {churn['canceled']:,} seeded cancellations at "
        f"{churn['churn_rate_formatted']} churn, {churn['revenue_lost']['formatted']} in modeled "
        f"lost membership revenue, and {estimate['estimated_revenue_saved']['formatted']} estimated saved "
        f"revenue at a {estimate['save_rate_assumption_formatted']} pause save-rate assumption."
    )


def get_retention_saver_summary_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
) -> dict[str, Any]:
    return get_retention_saver_summary(db_path, product_id=product_id, date_range=date_range)


def list_cancellation_risks_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    limit: int = 10,
) -> list[dict[str, Any]]:
    return list_cancellation_risks(db_path, product_id=product_id, date_range=date_range, limit=limit)


def build_pause_offer_plan_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
) -> dict[str, Any]:
    return build_pause_offer_plan(db_path, product_id=product_id, date_range=date_range)


def estimate_pause_revenue_saved_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    save_rate: float | int | str | None = None,
) -> dict[str, Any]:
    return estimate_pause_revenue_saved(db_path, product_id=product_id, date_range=date_range, save_rate=save_rate)
