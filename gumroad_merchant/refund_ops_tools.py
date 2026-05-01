from __future__ import annotations

import json
from collections import Counter
from contextlib import closing
from pathlib import Path
from typing import Any

from gumroad_merchant.analytics_tools import (
    build_metrics,
    format_percent,
    money_payload,
    product_ids,
)
from gumroad_merchant.database import connect_readonly, row_to_dict


CASE_TYPE_LABELS = {
    "refund_request": "Refund request",
    "voluntary_refund_review": "Refund review",
    "chargeback_dispute": "Chargeback dispute",
}


def case_mode(case_type: str) -> str:
    if case_type == "chargeback_dispute":
        return "dispute"
    return "review"


def normalize_case(row: Any, currency: str = "USD") -> dict[str, Any]:
    item = row_to_dict(row)
    item["label"] = CASE_TYPE_LABELS.get(item["case_type"], "Refund case")
    item["mode"] = case_mode(item["case_type"])
    item["amount"] = money_payload(item["amount_cents"], currency)
    item["timeline"] = json.loads(item.pop("timeline_json") or "[]")
    item["evidence"] = json.loads(item.pop("evidence_json") or "[]")
    return item


def query_refund_case_rows(
    db_path: Path | str,
    product_id: str = "all",
    case_id: str | None = None,
) -> list[dict[str, Any]]:
    with closing(connect_readonly(db_path)) as conn:
        ids = product_ids(conn, product_id)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        params: list[Any] = [*ids]
        case_filter = ""
        if case_id:
            case_filter = " AND case_id = ?"
            params.append(case_id)
        product_rows = conn.execute(
            f"SELECT id, currency FROM products WHERE id IN ({placeholders})",
            ids,
        ).fetchall()
        currency_by_product = {row["id"]: row["currency"] for row in product_rows}
        rows = conn.execute(
            f"""
            SELECT *
            FROM refund_cases
            WHERE product_id IN ({placeholders}){case_filter}
            ORDER BY
                CASE status
                    WHEN 'evidence_due' THEN 0
                    WHEN 'needs_review' THEN 1
                    WHEN 'reply_drafted' THEN 2
                    ELSE 3
                END,
                risk_score DESC,
                due_at ASC
            """,
            params,
        ).fetchall()
    return [
        normalize_case(row, currency_by_product.get(row["product_id"], "USD"))
        for row in rows
    ]


def load_refund_audit_events(db_path: Path | str, case_id: str) -> list[dict[str, Any]]:
    with closing(connect_readonly(db_path)) as conn:
        rows = conn.execute(
            """
            SELECT actor, action, amount_cents, note, created_at
            FROM refund_audit_events
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
    return [
        {
            **row_to_dict(row),
            "amount": money_payload(row["amount_cents"]),
        }
        for row in rows
    ]


def get_refund_prevention_actions_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
) -> list[dict[str, Any]]:
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    product = metrics["product"]
    cases = query_refund_case_rows(db_path, product_id=product_id)
    current = metrics["current"]
    derived = metrics["derived"]
    source_by_name = {source["name"].lower(): source for source in metrics["current_sources"]}
    discover = next(
        (source for source in metrics["current_sources"] if "discover" in source["name"].lower()),
        None,
    )
    actions: list[dict[str, Any]] = []

    if discover and current["refunds"] > 0:
        actions.append(
            {
                "id": "discover-refund-fit",
                "title": "High refund rate from Gumroad Discover",
                "impact": "Reduce expectation-mismatch refunds before widening Discover reach.",
                "evidence": [
                    f"{discover['views']:,} Discover views",
                    f"{discover['sales']:,} Discover sales",
                    f"{format_percent(derived['current_refund_rate'])} refund rate",
                ],
                "recommended_action": "Add format, compatibility, and included-file details above the buy button for Discover visitors.",
                "review_only": True,
            }
        )

    if any("compatibility" in case["reason"].lower() for case in cases):
        actions.append(
            {
                "id": "compatibility-expectations",
                "title": "Refunds mention compatibility",
                "impact": "Clarifies whether the product works for the buyer before checkout.",
                "evidence": ["Compatibility appears in the seeded refund-case reasons"],
                "recommended_action": "Add a supported-tools line, setup requirements, and one plain-language example of what is not included.",
                "review_only": True,
            }
        )

    if any(case["case_type"] == "chargeback_dispute" for case in cases):
        actions.append(
            {
                "id": "support-delay-dispute-risk",
                "title": "Support delay likely drove dispute risk",
                "impact": "Reduces the chance that a buyer bypasses support and opens a payment dispute.",
                "evidence": [
                    f"{sum(1 for case in cases if case['case_type'] == 'chargeback_dispute')} chargeback dispute case",
                    "Evidence packet requires support-thread review",
                ],
                "recommended_action": "Reply with access help within one business day and copy the audit note before making a refund decision.",
                "review_only": True,
            }
        )

    direct = source_by_name.get("direct")
    if direct and direct["views"] > 100:
        actions.append(
            {
                "id": "direct-policy-copy",
                "title": "Direct buyers need clearer refund expectations",
                "impact": "Direct traffic often mixes email, apps, bookmarks, and private shares, so the checkout copy has to do more work.",
                "evidence": [f"{direct['views']:,} direct views", f"{direct['sales']:,} direct sales"],
                "recommended_action": "Move refund expectations and delivery timing into the first screen instead of relying on support follow-up.",
                "review_only": True,
            }
        )

    if not actions:
        actions.append(
            {
                "id": "baseline-refund-monitoring",
                "title": "Keep refund monitoring active",
                "impact": "Refund pressure is not elevated enough to justify a broad product-page rewrite.",
                "evidence": [
                    f"{current['refunds']:,} refunds",
                    f"{format_percent(derived['current_refund_rate'])} refund rate",
                ],
                "recommended_action": f"Keep {product['name']} stable and review new cases before changing price or policy copy.",
                "review_only": True,
            }
        )

    return actions[:4]


def get_refund_ops_summary_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
) -> dict[str, Any]:
    metrics = build_metrics(db_path, product_id=product_id, date_range=date_range)
    cases = query_refund_case_rows(db_path, product_id=product_id)
    current = metrics["current"]
    derived = metrics["derived"]
    disputed_amount_cents = sum(case["amount_cents"] for case in cases if case["case_type"] == "chargeback_dispute")
    review_count = sum(1 for case in cases if case["status"] in {"needs_review", "evidence_due", "reply_drafted"})
    amount_under_review_cents = sum(case["amount_cents"] for case in cases)
    mode_counts = Counter(case["mode"] for case in cases)
    type_counts = Counter(case["case_type"] for case in cases)
    reason_counts = Counter(case["reason"] for case in cases)
    refund_rate = derived["current_refund_rate"]
    previous_refund_rate = derived["previous_refund_rate"]
    return {
        "product": metrics["product"],
        "date_range": date_range,
        "refund_rate": refund_rate,
        "refund_rate_formatted": format_percent(refund_rate),
        "previous_refund_rate": previous_refund_rate,
        "previous_refund_rate_formatted": format_percent(previous_refund_rate),
        "refunds": current["refunds"],
        "refund_amount_cents": current["refund_cents"],
        "refund_amount": money_payload(current["refund_cents"], metrics["product"]["currency"]),
        "disputed_amount_cents": disputed_amount_cents,
        "disputed_amount": money_payload(disputed_amount_cents, metrics["product"]["currency"]),
        "amount_under_review_cents": amount_under_review_cents,
        "amount_under_review": money_payload(amount_under_review_cents, metrics["product"]["currency"]),
        "cases_needing_review": review_count,
        "case_count": len(cases),
        "mode_counts": {
            "prevent": len(get_refund_prevention_actions_tool(db_path, product_id=product_id, date_range=date_range)),
            "review": mode_counts.get("review", 0),
            "dispute": mode_counts.get("dispute", 0),
        },
        "case_type_counts": dict(type_counts),
        "top_reasons": [{"reason": reason, "count": count} for reason, count in reason_counts.most_common(4)],
        "preventable_refund_estimate_cents": round(current["refund_cents"] * 0.42),
        "preventable_refund_estimate": money_payload(
            round(current["refund_cents"] * 0.42),
            metrics["product"]["currency"],
        ),
        "read_only": True,
        "boundary": "Seeded local Refund Ops cases only; no refunds, emails, disputes, or product edits are performed.",
    }


def list_refund_cases_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    mode: str = "all",
    limit: int = 10,
) -> list[dict[str, Any]]:
    _ = date_range
    normalized_mode = (mode or "all").strip().lower()
    cases = query_refund_case_rows(db_path, product_id=product_id)
    if normalized_mode in {"review", "dispute"}:
        cases = [case for case in cases if case["mode"] == normalized_mode]
    return cases[: max(1, min(25, int(limit or 10)))]


def get_refund_case_tool(db_path: Path | str, case_id: str) -> dict[str, Any]:
    cases = query_refund_case_rows(db_path, product_id="all", case_id=case_id)
    if not cases:
        return {"found": False, "case_id": case_id}
    case = cases[0]
    return {
        "found": True,
        **case,
        "audit_events": load_refund_audit_events(db_path, case_id),
    }


def build_dispute_evidence_pack_tool(db_path: Path | str, case_id: str) -> dict[str, Any]:
    case = get_refund_case_tool(db_path, case_id)
    if not case.get("found"):
        return case
    is_dispute = case["case_type"] == "chargeback_dispute"
    copy_text = case["dispute_evidence"] if is_dispute else case["buyer_reply"]
    return {
        "found": True,
        "case_id": case_id,
        "case_type": case["case_type"],
        "label": case["label"],
        "ready_for_review": is_dispute and case["evidence_score"] >= 70,
        "warning": "" if is_dispute else "This is a refund request, not a chargeback dispute. Use the buyer reply path.",
        "copy_text": copy_text,
        "audit_note": case["audit_note"],
        "evidence_checklist": case["evidence"],
        "timeline": case["timeline"],
        "policy_snapshot": case["policy_snapshot"],
        "review_only": True,
        "source_url": "https://gumroad.com/help/article/134-how-does-gumroad-handle-chargebacks.html",
    }


def draft_refund_reply_tool(db_path: Path | str, case_id: str) -> dict[str, Any]:
    case = get_refund_case_tool(db_path, case_id)
    if not case.get("found"):
        return case
    return {
        "found": True,
        "case_id": case_id,
        "copy_text": case["buyer_reply"],
        "recommended_action": case["recommended_action"],
        "audit_note": case["audit_note"],
        "review_only": True,
    }


def refund_ops_overview_sentence(db_path: Path | str, product_id: str = "all", date_range: str = "30") -> str:
    summary = get_refund_ops_summary_tool(db_path, product_id=product_id, date_range=date_range)
    verb = "have" if summary["product"]["id"] == "all" else "has"
    return (
        f"{summary['product']['name']} {verb} {summary['refunds']:,} refunds at "
        f"{summary['refund_rate_formatted']} refund rate, "
        f"{summary['cases_needing_review']} Refund Ops cases needing review, "
        f"{summary['disputed_amount']['formatted']} in chargeback dispute exposure, and "
        f"{summary['preventable_refund_estimate']['formatted']} in estimated preventable refunds."
    )
