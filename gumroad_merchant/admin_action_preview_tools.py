from __future__ import annotations

import copy
import shlex
from contextlib import closing
from pathlib import Path
from typing import Any

from gumroad_merchant.analytics_tools import money_payload, product_ids
from gumroad_merchant.database import connect_readonly, row_to_dict
from gumroad_merchant.refund_ops_tools import load_refund_audit_events, query_refund_case_rows


SOURCE_CONTEXT: dict[str, Any] = {
    "issue_id": 4677,
    "issue_reference": "Gumroad issue #4677",
    "issue_title": "Gumroad admin CLI",
    "issue_url": "https://github.com/antiwork/gumroad/issues/4677",
    "prototype_module": "Gumroad Merchant Admin/CLI Actions",
    "execution_scope": (
        "Seeded command workflows for Gumroad admin operations with preflight checks, "
        "required permissions, confirmation steps, and audit notes."
    ),
}

PREVIEW_BOUNDARY = (
    "Local command workflow with required inputs, permissions, confirmation steps, and audit notes."
)

ACTION_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "user_lookup",
        "title": "Exact user lookup",
        "category": "user_read",
        "description": "Run an exact admin lookup workflow for one user or creator identifier.",
        "required_inputs": ["user_id_or_email"],
        "optional_inputs": ["creator_id"],
        "risk_level": "low",
        "requires_human_approval": False,
        "real_gumroad_audit_required": True,
        "unsafe_write": False,
        "command_text": "gumroad-admin users lookup --user-id <user_id> --read-only",
        "audit_note": "User lookup workflow prepared with exact identifier scope.",
        "preflight_checks": [
            "Require exact user id, creator id, or email; do not allow broad fuzzy scans by default.",
            "Return the minimum admin fields needed for the support task.",
            "Record lookup reason in the production audit log.",
        ],
        "blocked_reason": None,
    },
    {
        "id": "purchase_lookup",
        "title": "Exact purchase lookup",
        "category": "purchase",
        "description": "Run an exact admin lookup workflow for one purchase ID.",
        "required_inputs": ["purchase_id"],
        "optional_inputs": ["buyer_email"],
        "risk_level": "low",
        "requires_human_approval": False,
        "real_gumroad_audit_required": False,
        "unsafe_write": False,
        "command_text": "gumroad-admin purchases lookup --purchase-id <purchase_id> --read-only",
        "audit_note": "Purchase lookup workflow prepared with exact identifier scope.",
        "preflight_checks": [
            "Confirm the purchase ID is exact, not a fuzzy buyer search.",
            "Verify the local seeded purchase exists before using facts in a live admin workflow.",
        ],
        "blocked_reason": None,
    },
    {
        "id": "refund_review",
        "title": "Refund review packet",
        "category": "refund_ops",
        "description": "Prepare a Refund Ops packet for a seeded case.",
        "required_inputs": ["case_id"],
        "optional_inputs": ["purchase_id"],
        "risk_level": "medium",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": False,
        "command_text": (
            "gumroad-admin refunds prepare --case-id <case_id> --purchase-id <purchase_id>"
        ),
        "audit_note": (
            "Refund packet prepared with decision context, evidence, and audit note."
        ),
        "preflight_checks": [
            "Confirm the Refund Ops case exists in the seeded local database.",
            "Review purchase, delivery, policy, support, and dispute evidence before a live decision.",
            "Require a scoped permission and audit event before issuing a refund.",
        ],
        "blocked_reason": None,
    },
    {
        "id": "compliance_review",
        "title": "Compliance review packet",
        "category": "compliance_review",
        "description": "Prepare a compliance packet for a creator, product, purchase, or Refund Ops case.",
        "required_inputs": ["target_id", "reason"],
        "optional_inputs": ["case_id", "product_id", "creator_id"],
        "risk_level": "medium",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": False,
        "command_text": (
            "gumroad-admin compliance prepare --target-id <target_id> --reason <reason>"
        ),
        "audit_note": "Compliance packet prepared with target, reason, evidence, and required approval path.",
        "preflight_checks": [
            "Confirm the exact review target and policy basis.",
            "Collect purchase, refund, payout, and support evidence before any enforcement action.",
            "Separate evidence gathering from state-changing compliance decisions.",
        ],
        "blocked_reason": None,
    },
    {
        "id": "add_note",
        "title": "Add admin note",
        "category": "admin_write",
        "description": "Prepare the command workflow for adding an internal admin note.",
        "required_inputs": ["purchase_id_or_case_id", "note"],
        "optional_inputs": ["actor"],
        "risk_level": "medium",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": (
            "gumroad-admin purchases notes add --purchase-id <purchase_id> --note <note> --confirm-required"
        ),
        "audit_note": "Admin note workflow prepared with exact target and note text.",
        "preflight_checks": [
            "Confirm the note is factual, minimal, and tied to a concrete purchase or case.",
            "Require human approval and Gumroad-side audit logging before any live note write.",
        ],
        "blocked_reason": "Admin note writes require merchant confirmation, scoped permission, and audit logging.",
    },
    {
        "id": "resend_receipt",
        "title": "Resend receipt",
        "category": "email_write",
        "description": "Prepare the command workflow for resending a purchase receipt email.",
        "required_inputs": ["purchase_id"],
        "optional_inputs": ["buyer_email"],
        "risk_level": "medium",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": "gumroad-admin purchases receipts resend --purchase-id <purchase_id> --confirm-required",
        "audit_note": "Receipt resend workflow prepared with buyer identity and support context.",
        "preflight_checks": [
            "Confirm buyer identity and receipt destination.",
            "Check do-not-contact and support context before any live resend.",
            "Require human approval and Gumroad-side audit logging before email delivery.",
        ],
        "blocked_reason": "Receipt resend requires merchant confirmation, scoped permission, and audit logging.",
    },
    {
        "id": "cancel_subscription",
        "title": "Cancel subscription",
        "category": "subscription_write",
        "description": "Prepare the command workflow for canceling a recurring purchase or subscription.",
        "required_inputs": ["purchase_id", "reason"],
        "optional_inputs": ["subscription_id"],
        "risk_level": "high",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": (
            "gumroad-admin subscriptions cancel --purchase-id <purchase_id> --reason <reason> --confirm-required"
        ),
        "audit_note": "Subscription cancellation workflow prepared with buyer request or policy basis.",
        "preflight_checks": [
            "Confirm the purchase is a recurring subscription or membership.",
            "Confirm buyer request or policy basis for cancellation.",
            "Require human approval and Gumroad-side audit logging before any live cancellation.",
        ],
        "blocked_reason": "Subscription cancellation requires merchant confirmation, scoped permission, and audit logging.",
    },
    {
        "id": "pause_membership",
        "title": "Pause membership",
        "category": "subscription_write",
        "description": "Prepare the command workflow for pausing a membership.",
        "required_inputs": ["purchase_id", "reason"],
        "optional_inputs": ["pause_until"],
        "risk_level": "high",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": (
            "gumroad-admin memberships pause --purchase-id <purchase_id> --reason <reason> --confirm-required"
        ),
        "audit_note": "Membership pause workflow prepared with duration, reason, and buyer-facing implications.",
        "preflight_checks": [
            "Confirm the purchase is a recurring membership.",
            "Confirm pause duration and buyer-facing implications.",
            "Require human approval and Gumroad-side audit logging before any live pause.",
        ],
        "blocked_reason": "Membership pause requires merchant confirmation, scoped permission, and audit logging.",
    },
    {
        "id": "risk_state_change",
        "title": "Change risk state",
        "category": "risk_write",
        "description": "Prepare the command workflow for changing a creator or account risk state.",
        "required_inputs": ["creator_id_or_user_id", "risk_state", "reason"],
        "optional_inputs": ["case_id", "expires_at"],
        "risk_level": "critical",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": (
            "gumroad-admin risk state set --creator-id <creator_id> --risk-state <risk_state> --reason <reason> --confirm-required"
        ),
        "audit_note": "Risk-state workflow prepared with policy basis, evidence, and approval route.",
        "preflight_checks": [
            "Confirm the exact creator or user scope.",
            "Require risk/compliance approval and a policy basis before any live risk-state change.",
            "Attach evidence and an expiration or review date where possible.",
        ],
        "blocked_reason": "Risk state changes are high-impact admin writes and are blocked in this prototype.",
    },
    {
        "id": "fee_update",
        "title": "Update fee policy",
        "category": "fee_write",
        "description": "Prepare the command workflow for changing a creator, product, or sale-scope fee override.",
        "required_inputs": ["creator_id_or_product_id", "fee_percent", "reason"],
        "optional_inputs": ["starts_at", "ends_at", "case_id"],
        "risk_level": "critical",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": (
            "gumroad-admin fees update --creator-id <creator_id> --fee-percent <fee_percent> --reason <reason> --confirm-required"
        ),
        "audit_note": "Fee update workflow prepared with exact scope, reason, and rollback path.",
        "preflight_checks": [
            "Confirm the exact fee scope, effective window, and rollback path.",
            "Require finance/legal approval for non-standard or retroactive fee behavior.",
            "Use idempotency and audit events before any live fee update.",
        ],
        "blocked_reason": "Fee updates are high-impact financial admin writes and are blocked in this prototype.",
    },
    {
        "id": "payout_hold",
        "title": "Place payout hold",
        "category": "payout_write",
        "description": "Prepare the command workflow for placing a payout hold on a creator or product scope.",
        "required_inputs": ["creator_id_or_product_id", "reason"],
        "optional_inputs": ["case_id"],
        "risk_level": "critical",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": (
            "gumroad-admin payouts hold --creator-id <creator_id> --reason <reason> --confirm-required"
        ),
        "audit_note": "Payout hold workflow prepared with exact scope, reason, and approval owner.",
        "preflight_checks": [
            "Confirm the exact creator/account scope.",
            "Confirm legal, risk, support, and finance approval before any live payout hold.",
            "Require Gumroad-side audit logging and escalation owner before live execution.",
        ],
        "blocked_reason": "Payout holds are high-impact financial admin writes and are blocked in this prototype.",
    },
    {
        "id": "payout_resume",
        "title": "Resume payout",
        "category": "payout_write",
        "description": "Prepare the command workflow for resuming payout eligibility.",
        "required_inputs": ["creator_id_or_product_id", "reason"],
        "optional_inputs": ["case_id"],
        "risk_level": "critical",
        "requires_human_approval": True,
        "real_gumroad_audit_required": True,
        "unsafe_write": True,
        "command_text": (
            "gumroad-admin payouts resume --creator-id <creator_id> --reason <reason> --confirm-required"
        ),
        "audit_note": "Payout resume workflow prepared with exact scope and hold-resolution evidence.",
        "preflight_checks": [
            "Confirm the exact creator/account scope.",
            "Confirm the hold-resolution evidence and finance approval before any live payout resume.",
            "Require Gumroad-side audit logging and escalation owner before live execution.",
        ],
        "blocked_reason": "Payout resume is a high-impact financial admin write and is blocked in this prototype.",
    },
]

ACTION_ALIASES = {
    "user": "user_lookup",
    "creator_lookup": "user_lookup",
    "lookup_user": "user_lookup",
    "exact_purchase_lookup": "purchase_lookup",
    "lookup_purchase": "purchase_lookup",
    "purchase": "purchase_lookup",
    "refund": "refund_review",
    "refund_case_review": "refund_review",
    "compliance": "compliance_review",
    "compliance_packet": "compliance_review",
    "admin_note": "add_note",
    "note": "add_note",
    "receipt": "resend_receipt",
    "resend": "resend_receipt",
    "cancel": "cancel_subscription",
    "pause": "pause_membership",
    "risk": "risk_state_change",
    "risk_state": "risk_state_change",
    "set_risk_state": "risk_state_change",
    "fee": "fee_update",
    "fee_change": "fee_update",
    "fee_override": "fee_update",
    "hold_payout": "payout_hold",
    "resume_payout": "payout_resume",
}


def _normalize_action_id(action_id: str) -> str:
    normalized = str(action_id or "").strip().lower().replace("-", "_").replace(" ", "_")
    return ACTION_ALIASES.get(normalized, normalized)


def _template_by_id(action_id: str) -> dict[str, Any] | None:
    normalized = _normalize_action_id(action_id)
    return next((template for template in ACTION_TEMPLATES if template["id"] == normalized), None)


def _public_template(template: dict[str, Any]) -> dict[str, Any]:
    item = copy.deepcopy(template)
    item["action_ready"] = True
    item["execution_mode"] = "admin_action_workflow"
    item["requires_confirmation"] = bool(item.get("requires_human_approval"))
    item["source_context"] = copy.deepcopy(SOURCE_CONTEXT)
    return item


def _has_value(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _normalize_inputs(inputs: dict[str, Any] | None = None, **overrides: Any) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for source in (inputs or {}, overrides):
        for key, value in source.items():
            if _has_value(value):
                normalized[key] = value
    return normalized


def _quote_or_placeholder(value: Any, placeholder: str) -> str:
    if not _has_value(value):
        return f"<{placeholder}>"
    return shlex.quote(str(value))


def _join_command(parts: list[str]) -> str:
    return " ".join(part for part in parts if part)


def _render_command(action_id: str, inputs: dict[str, Any]) -> str:
    purchase_id = inputs.get("purchase_id")
    case_id = inputs.get("case_id")
    note = inputs.get("note")
    reason = inputs.get("reason")
    buyer_email = inputs.get("buyer_email")
    subscription_id = inputs.get("subscription_id")
    pause_until = inputs.get("pause_until")
    creator_id = inputs.get("creator_id")
    user_id = inputs.get("user_id")
    user_email = inputs.get("email") or inputs.get("user_email") or buyer_email
    target_id_input = inputs.get("target_id")
    risk_state = inputs.get("risk_state")
    fee_percent = inputs.get("fee_percent")
    starts_at = inputs.get("starts_at")
    ends_at = inputs.get("ends_at")
    expires_at = inputs.get("expires_at")
    product_id = inputs.get("product_id")
    target_id = creator_id or (product_id if product_id and product_id != "all" else None)
    target_flag = "--creator-id" if creator_id else "--product-id"

    if action_id == "user_lookup":
        parts = ["gumroad-admin", "users", "lookup"]
        if user_id:
            parts.extend(["--user-id", _quote_or_placeholder(user_id, "user_id")])
        elif creator_id:
            parts.extend(["--creator-id", _quote_or_placeholder(creator_id, "creator_id")])
        else:
            parts.extend(["--email", _quote_or_placeholder(user_email, "user_email")])
        parts.append("--read-only")
        return _join_command(parts)

    if action_id == "purchase_lookup":
        parts = [
            "gumroad-admin",
            "purchases",
            "lookup",
            "--purchase-id",
            _quote_or_placeholder(purchase_id, "purchase_id"),
            "--read-only",
        ]
        if buyer_email:
            parts.extend(["--buyer-email", _quote_or_placeholder(buyer_email, "buyer_email")])
        return _join_command(parts)

    if action_id == "refund_review":
        return _join_command(
            [
                "gumroad-admin",
                "refunds",
                "review",
                "--case-id",
                _quote_or_placeholder(case_id, "case_id"),
                "--purchase-id",
                _quote_or_placeholder(purchase_id, "purchase_id"),
                "--confirm-required",
            ]
        )

    if action_id == "compliance_review":
        target = target_id_input or case_id or purchase_id or target_id
        parts = [
            "gumroad-admin",
            "compliance",
            "review",
            "--target-id",
            _quote_or_placeholder(target, "target_id"),
            "--reason",
            _quote_or_placeholder(reason, "reason"),
            "--confirm-required",
        ]
        if case_id:
            parts.extend(["--case-id", _quote_or_placeholder(case_id, "case_id")])
        if product_id and product_id != "all":
            parts.extend(["--product-id", _quote_or_placeholder(product_id, "product_id")])
        return _join_command(parts)

    if action_id == "add_note":
        parts = [
            "gumroad-admin",
            "purchases",
            "notes",
            "add",
            "--purchase-id",
            _quote_or_placeholder(purchase_id, "purchase_id"),
            "--note",
            _quote_or_placeholder(note, "note"),
            "--confirm-required",
        ]
        if case_id:
            parts.extend(["--case-id", _quote_or_placeholder(case_id, "case_id")])
        return _join_command(parts)

    if action_id == "resend_receipt":
        return _join_command(
            [
                "gumroad-admin",
                "purchases",
                "receipts",
                "resend",
                "--purchase-id",
                _quote_or_placeholder(purchase_id, "purchase_id"),
                "--confirm-required",
            ]
        )

    if action_id == "cancel_subscription":
        parts = [
            "gumroad-admin",
            "subscriptions",
            "cancel",
            "--purchase-id",
            _quote_or_placeholder(purchase_id, "purchase_id"),
            "--reason",
            _quote_or_placeholder(reason, "reason"),
            "--confirm-required",
        ]
        if subscription_id:
            parts.extend(["--subscription-id", _quote_or_placeholder(subscription_id, "subscription_id")])
        return _join_command(parts)

    if action_id == "pause_membership":
        parts = [
            "gumroad-admin",
            "memberships",
            "pause",
            "--purchase-id",
            _quote_or_placeholder(purchase_id, "purchase_id"),
            "--reason",
            _quote_or_placeholder(reason, "reason"),
            "--confirm-required",
        ]
        if pause_until:
            parts.extend(["--pause-until", _quote_or_placeholder(pause_until, "pause_until")])
        return _join_command(parts)

    if action_id == "risk_state_change":
        target = creator_id or user_id or target_id_input
        target_flag = "--user-id" if user_id and not creator_id else "--creator-id"
        parts = [
            "gumroad-admin",
            "risk",
            "state",
            "set",
            target_flag,
            _quote_or_placeholder(target, "creator_id_or_user_id"),
            "--risk-state",
            _quote_or_placeholder(risk_state, "risk_state"),
            "--reason",
            _quote_or_placeholder(reason, "reason"),
            "--confirm-required",
        ]
        if case_id:
            parts.extend(["--case-id", _quote_or_placeholder(case_id, "case_id")])
        if expires_at:
            parts.extend(["--expires-at", _quote_or_placeholder(expires_at, "expires_at")])
        return _join_command(parts)

    if action_id == "fee_update":
        target = creator_id or (product_id if product_id and product_id != "all" else None) or target_id_input
        target_flag = "--product-id" if product_id and product_id != "all" and not creator_id else "--creator-id"
        parts = [
            "gumroad-admin",
            "fees",
            "update",
            target_flag,
            _quote_or_placeholder(target, "creator_id_or_product_id"),
            "--fee-percent",
            _quote_or_placeholder(fee_percent, "fee_percent"),
            "--reason",
            _quote_or_placeholder(reason, "reason"),
            "--confirm-required",
        ]
        if starts_at:
            parts.extend(["--starts-at", _quote_or_placeholder(starts_at, "starts_at")])
        if ends_at:
            parts.extend(["--ends-at", _quote_or_placeholder(ends_at, "ends_at")])
        return _join_command(parts)

    if action_id == "payout_hold":
        return _join_command(
            [
                "gumroad-admin",
                "payouts",
                "hold",
                target_flag,
                _quote_or_placeholder(target_id, "creator_id_or_product_id"),
                "--reason",
                _quote_or_placeholder(reason, "reason"),
                "--confirm-required",
            ]
        )

    if action_id == "payout_resume":
        return _join_command(
            [
                "gumroad-admin",
                "payouts",
                "resume",
                target_flag,
                _quote_or_placeholder(target_id, "creator_id_or_product_id"),
                "--reason",
                _quote_or_placeholder(reason, "reason"),
                "--confirm-required",
            ]
        )

    return "gumroad-admin <unknown-action> --confirm-required"


def list_admin_action_templates() -> list[dict[str, Any]]:
    """Return the simulated admin CLI templates exposed by this prototype."""
    return [_public_template(template) for template in ACTION_TEMPLATES]


def build_cli_command_preview(
    action_id: str,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Render a command string without executing it."""
    normalized_action_id = _normalize_action_id(action_id)
    template = _template_by_id(normalized_action_id)
    if not template:
        return {
            "found": False,
            "action_id": normalized_action_id,
            "command_text": "",
            "required_inputs": [],
            "risk_level": "unknown",
            "audit_note": "Unknown admin action requested. No command was rendered.",
            "preflight_checks": [
                {
                    "check": "known template",
                    "status": "failed",
                    "detail": f"No admin action template exists for {action_id!r}.",
                }
            ],
            "blocked_reason": "Unknown admin action template.",
            "action_ready": False,
            "execution_mode": "unknown_admin_action",
            "requires_confirmation": True,
            "source_context": copy.deepcopy(SOURCE_CONTEXT),
        }

    normalized_inputs = _normalize_inputs(inputs)
    return {
        "found": True,
        "action_id": normalized_action_id,
        "title": template["title"],
        "category": template["category"],
        "command_text": _render_command(normalized_action_id, normalized_inputs),
        "required_inputs": copy.deepcopy(template["required_inputs"]),
        "optional_inputs": copy.deepcopy(template["optional_inputs"]),
        "risk_level": template["risk_level"],
        "requires_human_approval": bool(template["requires_human_approval"]),
        "real_gumroad_audit_required": bool(template["real_gumroad_audit_required"]),
        "unsafe_write": bool(template["unsafe_write"]),
        "audit_note": template["audit_note"],
        "preflight_checks": [
            {"check": check, "status": "pending", "detail": "Requires endpoint/tool context to verify."}
            for check in template["preflight_checks"]
        ],
        "blocked_reason": template["blocked_reason"],
        "provided_inputs": normalized_inputs,
        "action_ready": True,
        "execution_mode": "admin_action_workflow",
        "requires_confirmation": bool(template["requires_human_approval"]),
        "source_context": copy.deepcopy(SOURCE_CONTEXT),
    }


def _load_purchase(db_path: Path | str, purchase_id: str) -> dict[str, Any] | None:
    with closing(connect_readonly(db_path)) as conn:
        row = conn.execute(
            """
            SELECT
                customer_sales.*,
                products.name AS product_name,
                products.creator AS creator,
                products.currency AS currency
            FROM customer_sales
            JOIN products ON products.id = customer_sales.product_id
            WHERE customer_sales.purchase_id = ?
            """,
            (purchase_id,),
        ).fetchone()
    if not row:
        return None

    item = row_to_dict(row)
    currency = item["currency"]
    return {
        "purchase_id": item["purchase_id"],
        "product": {
            "id": item["product_id"],
            "name": item["product_name"],
            "creator": item["creator"],
            "currency": currency,
        },
        "buyer": {
            "name": item["buyer_name"],
            "email": item["buyer_email"],
            "do_not_contact": bool(item["do_not_contact"]),
        },
        "purchase_date": item["purchase_date"],
        "purchase_time_utc": item["purchase_time_utc"],
        "state": item["state"],
        "country": item["country"],
        "source": {
            "referrer": item["referrer"],
            "discover": bool(item["discover"]),
            "utm_source": item["utm_source"],
            "utm_medium": item["utm_medium"],
            "utm_campaign": item["utm_campaign"],
            "utm_destination": item["utm_destination"],
        },
        "payment_type": item["payment_type"],
        "variant": item["variant"],
        "discount_code": item["discount_code"],
        "refunded": bool(item["refunded"]),
        "recurring_charge": bool(item["recurring_charge"]),
        "recurrence": item["recurrence"],
        "amounts": {
            "subtotal": money_payload(item["subtotal_cents"], currency),
            "tax": money_payload(item["tax_cents"], currency),
            "sale_price": money_payload(item["sale_price_cents"], currency),
            "fee": money_payload(item["fee_cents"], currency),
            "net_total": money_payload(item["net_total_cents"], currency),
            "partial_refund": money_payload(item["partial_refund_cents"], currency),
        },
    }


def _load_product(db_path: Path | str, product_id: str | None) -> dict[str, Any] | None:
    if not product_id or product_id == "all":
        return None
    with closing(connect_readonly(db_path)) as conn:
        row = conn.execute(
            """
            SELECT id, name, creator, category, currency
            FROM products
            WHERE id = ?
            """,
            (product_id,),
        ).fetchone()
    return row_to_dict(row) if row else None


def _load_refund_case(db_path: Path | str, case_id: str | None) -> dict[str, Any] | None:
    if not case_id:
        return None
    cases = query_refund_case_rows(db_path, product_id="all", case_id=case_id)
    if not cases:
        return None
    case = cases[0]
    case["audit_events"] = load_refund_audit_events(db_path, case_id)
    return case


def _missing_required_inputs(template: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for required in template["required_inputs"]:
        if required == "purchase_id_or_case_id":
            if not _has_value(inputs.get("purchase_id")) and not _has_value(inputs.get("case_id")):
                missing.append(required)
        elif required == "creator_id_or_product_id":
            product_id = inputs.get("product_id")
            if not _has_value(inputs.get("creator_id")) and (not _has_value(product_id) or product_id == "all"):
                missing.append(required)
        elif not _has_value(inputs.get(required)):
            missing.append(required)
    return missing


def _check(status: str, check: str, detail: str) -> dict[str, str]:
    return {"check": check, "status": status, "detail": detail}


def _build_preflight_checks(
    template: dict[str, Any],
    inputs: dict[str, Any],
    purchase: dict[str, Any] | None,
    refund_case: dict[str, Any] | None,
    product: dict[str, Any] | None,
) -> list[dict[str, str]]:
    action_id = template["id"]
    missing = _missing_required_inputs(template, inputs)
    checks = [
        _check("passed", "execution scope", PREVIEW_BOUNDARY),
        _check(
            "failed" if missing else "passed",
            "required inputs",
            f"Missing required input(s): {', '.join(missing)}." if missing else "All required action inputs are present.",
        ),
    ]

    if _has_value(inputs.get("purchase_id")):
        checks.append(
            _check(
                "passed" if purchase else "failed",
                "seeded purchase lookup",
                (
                    f"Purchase {inputs['purchase_id']} exists in the local seeded database."
                    if purchase
                    else f"Purchase {inputs['purchase_id']} was not found in the local seeded database."
                ),
            )
        )
    elif any(required in template["required_inputs"] for required in ("purchase_id", "purchase_id_or_case_id")):
        checks.append(_check("pending", "seeded purchase lookup", "No purchase ID was provided."))

    if _has_value(inputs.get("case_id")):
        checks.append(
            _check(
                "passed" if refund_case else "failed",
                "Refund Ops case lookup",
                (
                    f"Refund Ops case {inputs['case_id']} exists in the local seeded database."
                    if refund_case
                    else f"Refund Ops case {inputs['case_id']} was not found in the local seeded database."
                ),
            )
        )
    elif action_id == "refund_review":
        checks.append(_check("failed", "Refund Ops case lookup", "Refund workflows require a case ID."))

    if action_id in {"cancel_subscription", "pause_membership"}:
        if purchase:
            checks.append(
                _check(
                    "passed" if purchase["recurring_charge"] else "failed",
                    "recurring purchase",
                    (
                        f"{purchase['purchase_id']} is marked as recurring ({purchase['recurrence'] or 'recurring'})."
                        if purchase["recurring_charge"]
                        else f"{purchase['purchase_id']} is not marked as recurring in the seeded facts."
                    ),
                )
            )
        else:
            checks.append(_check("pending", "recurring purchase", "Cannot verify recurring status without a purchase."))

    if action_id in {"payout_hold", "payout_resume"}:
        if _has_value(inputs.get("creator_id")):
            checks.append(_check("pending", "payout target", "Creator ID is supplied but not verified by seeded data."))
        elif product:
            checks.append(
                _check(
                    "passed",
                    "payout target",
                    f"Product scope resolves locally to {product['name']} by {product['creator']}.",
                )
            )
        else:
            checks.append(
                _check(
                    "failed",
                    "payout target",
                    "Payout workflows require an exact creator ID or one seeded product ID, not all products.",
                )
            )

    if action_id == "resend_receipt" and purchase:
        checks.append(
            _check(
                "failed" if purchase["buyer"]["do_not_contact"] else "passed",
                "buyer contact status",
                (
                    "Buyer is marked do-not-contact in the seeded facts."
                    if purchase["buyer"]["do_not_contact"]
                    else "Buyer is not marked do-not-contact in the seeded facts."
                ),
            )
        )

    if template["unsafe_write"]:
        checks.append(_check("blocked", "write boundary", template["blocked_reason"]))
    else:
        checks.append(_check("passed", "write requirements", "Template is a read action or requires explicit confirmation."))

    if template["requires_human_approval"]:
        checks.append(
            _check(
                "pending",
                "human approval",
                "Human approval is required before any corresponding live Gumroad admin action.",
            )
        )
    else:
        checks.append(_check("not_required", "human approval", "This workflow is a read action."))

    if template["real_gumroad_audit_required"]:
        checks.append(
            _check(
                "pending",
                "real Gumroad audit",
                "Any live action must be recorded through Gumroad-side audit logging outside this prototype.",
            )
        )
    return checks


def _blocked_reason(
    template: dict[str, Any],
    inputs: dict[str, Any],
    purchase: dict[str, Any] | None,
    refund_case: dict[str, Any] | None,
    product: dict[str, Any] | None,
) -> str | None:
    missing = _missing_required_inputs(template, inputs)
    if missing:
        return f"Missing required input(s): {', '.join(missing)}."
    if _has_value(inputs.get("purchase_id")) and not purchase:
        return f"Purchase {inputs['purchase_id']} was not found in the local seeded database."
    if _has_value(inputs.get("case_id")) and not refund_case:
        return f"Refund Ops case {inputs['case_id']} was not found in the local seeded database."
    if template["id"] == "refund_review" and not refund_case:
        return "Refund workflows require a seeded Refund Ops case."
    if template["id"] in {"cancel_subscription", "pause_membership"} and purchase and not purchase["recurring_charge"]:
        return f"{purchase['purchase_id']} is not a recurring purchase in the seeded facts."
    if template["id"] in {"payout_hold", "payout_resume"} and not inputs.get("creator_id") and not product:
        return "Payout workflows require an exact creator ID or seeded product ID."
    if template["unsafe_write"]:
        return str(template["blocked_reason"])
    return None


def _compose_audit_note(
    template: dict[str, Any],
    inputs: dict[str, Any],
    purchase: dict[str, Any] | None,
    refund_case: dict[str, Any] | None,
) -> str:
    action_id = template["id"]
    if action_id == "refund_review" and refund_case:
        return f"{refund_case['audit_note']} Refund workflow prepared with evidence and next execution step."
    if action_id == "add_note":
        target = inputs.get("purchase_id") or inputs.get("case_id") or "the selected target"
        return f"Admin note workflow prepared for {target}. Note: {inputs.get('note', '<note>')}"
    if action_id == "resend_receipt" and purchase:
        return (
            f"Receipt resend workflow prepared for {purchase['purchase_id']} to "
            f"{purchase['buyer']['email']} with confirmation required."
        )
    if action_id in {"cancel_subscription", "pause_membership"} and purchase:
        verb = "cancel subscription" if action_id == "cancel_subscription" else "pause membership"
        return f"{verb.title()} workflow prepared for {purchase['purchase_id']} with confirmation required."
    if action_id in {"payout_hold", "payout_resume"}:
        target = inputs.get("creator_id") or inputs.get("product_id") or "the selected payout target"
        verb = "place payout hold" if action_id == "payout_hold" else "resume payout"
        return f"{verb.title()} workflow prepared for {target} with confirmation required."
    return str(template["audit_note"])


def preview_admin_action(
    db_path: Path | str,
    action_id: str,
    purchase_id: str | None = None,
    case_id: str | None = None,
    product_id: str | None = None,
    buyer_email: str | None = None,
    note: str | None = None,
    reason: str | None = None,
    actor: str | None = None,
    subscription_id: str | None = None,
    pause_until: str | None = None,
    creator_id: str | None = None,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a full admin action workflow against seeded local facts."""
    normalized_action_id = _normalize_action_id(action_id)
    template = _template_by_id(normalized_action_id)
    if not template:
        return build_cli_command_preview(action_id, inputs=inputs)

    normalized_inputs = _normalize_inputs(
        inputs,
        purchase_id=purchase_id,
        case_id=case_id,
        product_id=product_id,
        buyer_email=buyer_email,
        note=note,
        reason=reason,
        actor=actor,
        subscription_id=subscription_id,
        pause_until=pause_until,
        creator_id=creator_id,
    )

    refund_case = _load_refund_case(db_path, normalized_inputs.get("case_id"))
    if refund_case:
        normalized_inputs.setdefault("purchase_id", refund_case["purchase_id"])
        normalized_inputs.setdefault("product_id", refund_case["product_id"])
        normalized_inputs.setdefault("reason", refund_case["reason"])
        if normalized_action_id == "add_note":
            normalized_inputs.setdefault("note", refund_case["audit_note"])

    purchase = None
    if _has_value(normalized_inputs.get("purchase_id")):
        purchase = _load_purchase(db_path, str(normalized_inputs["purchase_id"]))
        if purchase:
            normalized_inputs.setdefault("buyer_email", purchase["buyer"]["email"])
            normalized_inputs.setdefault("product_id", purchase["product"]["id"])

    product = _load_product(db_path, normalized_inputs.get("product_id"))
    command_preview = build_cli_command_preview(normalized_action_id, inputs=normalized_inputs)
    preflight_checks = _build_preflight_checks(template, normalized_inputs, purchase, refund_case, product)
    blocked_reason = _blocked_reason(template, normalized_inputs, purchase, refund_case, product)

    return {
        "found": True,
        "action_id": normalized_action_id,
        "title": template["title"],
        "category": template["category"],
        "command_text": command_preview["command_text"],
        "required_inputs": copy.deepcopy(template["required_inputs"]),
        "optional_inputs": copy.deepcopy(template["optional_inputs"]),
        "provided_inputs": normalized_inputs,
        "risk_level": template["risk_level"],
        "requires_human_approval": bool(template["requires_human_approval"]),
        "real_gumroad_audit_required": bool(template["real_gumroad_audit_required"]),
        "unsafe_write": bool(template["unsafe_write"]),
        "audit_note": _compose_audit_note(template, normalized_inputs, purchase, refund_case),
        "preflight_checks": preflight_checks,
        "blocked_reason": blocked_reason,
        "resolved_context": {
            "purchase": purchase,
            "refund_case": refund_case,
            "product": product,
        },
        "action_ready": True,
        "execution_mode": "admin_action_workflow",
        "requires_confirmation": bool(template["requires_human_approval"]),
        "source_context": copy.deepcopy(SOURCE_CONTEXT),
    }


def _purchase_examples(db_path: Path | str, product_id: str, limit: int) -> list[dict[str, Any]]:
    with closing(connect_readonly(db_path)) as conn:
        ids = product_ids(conn, product_id)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT purchase_id, product_id, item_name, buyer_email, sale_price_cents,
                   payment_type, refunded, recurring_charge, recurrence
            FROM customer_sales
            WHERE product_id IN ({placeholders})
            ORDER BY purchase_date DESC, purchase_id ASC
            LIMIT ?
            """,
            [*ids, max(1, min(25, int(limit or 6)))],
        ).fetchall()
    return [
        {
            "purchase_id": row["purchase_id"],
            "product_id": row["product_id"],
            "item_name": row["item_name"],
            "buyer_email": row["buyer_email"],
            "sale_price": money_payload(row["sale_price_cents"]),
            "payment_type": row["payment_type"],
            "refunded": bool(row["refunded"]),
            "recurring_charge": bool(row["recurring_charge"]),
            "recurrence": row["recurrence"],
        }
        for row in rows
    ]


def _compact_action_preview(action_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    preview = build_cli_command_preview(action_id, inputs=inputs)
    return {
        "action_id": preview["action_id"],
        "title": preview.get("title", ""),
        "command_text": preview["command_text"],
        "required_inputs": preview["required_inputs"],
        "risk_level": preview["risk_level"],
        "audit_note": preview["audit_note"],
        "blocked_reason": preview["blocked_reason"],
    }


def _case_suggestions(refund_case: dict[str, Any]) -> list[dict[str, Any]]:
    inputs = {
        "case_id": refund_case["case_id"],
        "purchase_id": refund_case["purchase_id"],
        "product_id": refund_case["product_id"],
        "reason": refund_case["reason"],
        "note": refund_case["audit_note"],
    }
    action_ids = ["purchase_lookup", "refund_review", "add_note"]
    combined_text = " ".join(
        str(refund_case.get(key, "")) for key in ("buyer_issue", "recommended_action", "reason")
    ).lower()
    if refund_case["case_type"] == "refund_request" or "access" in combined_text:
        action_ids.append("resend_receipt")
    if refund_case["case_type"] == "chargeback_dispute":
        action_ids.append("payout_hold")
    return [_compact_action_preview(action_id, inputs) for action_id in action_ids]


def get_admin_api_cli_recommendation() -> dict[str, Any]:
    """Resolve Gumroad issue #4677's API/CLI open questions as an implementation plan."""
    prioritized_actions = [
        {
            "phase": 1,
            "name": "Read-only exact lookup",
            "actions": ["user_lookup", "purchase_lookup"],
            "why_first": "Low mutation risk, high operator value, and required by most later admin workflows.",
            "contract_shape": [
                "GET /internal/admin/users/lookup?email=... or ?user_id=...",
                "GET /internal/admin/purchases/{purchase_id}",
            ],
            "live_controls": [
                "Exact identifiers only by default.",
                "Minimum scoped admin response fields.",
                "Audit reason required even for reads.",
            ],
        },
        {
            "phase": 2,
            "name": "Review packet generation",
            "actions": ["refund_review", "compliance_review"],
            "why_first": "Automates evidence gathering for Gumclaw and staff without crossing into state-changing decisions.",
            "contract_shape": [
                "POST /internal/admin/refunds/{case_id}/review-packet",
                "POST /internal/admin/compliance/reviews/prepare",
            ],
            "live_controls": [
                "Return evidence, policy snapshot, timeline, recommended next step, and audit note.",
                "Refunds, dispute responses, restrictions, and account changes require a separate confirmed execution step.",
            ],
        },
        {
            "phase": 3,
            "name": "Gated admin writes",
            "actions": ["risk_state_change", "fee_update", "add_note", "resend_receipt"],
            "why_later": "These create financial, compliance, account, or buyer-contact side effects and need approvals first.",
            "contract_shape": [
                "POST /internal/admin/risk/state-changes/prepare",
                "POST /internal/admin/risk/state-changes/{prepared_action_id}/execute",
                "POST /internal/admin/fees/updates/prepare",
                "POST /internal/admin/fees/updates/{prepared_action_id}/execute",
            ],
            "live_controls": [
                "Prepare-before-execute required.",
                "Idempotency key required for execute.",
                "Role, scope, reason, approval, and audit event required.",
                "Human approval required for high-impact actions.",
            ],
        },
    ]
    return {
        "source_context": copy.deepcopy(SOURCE_CONTEXT),
        "issue_problem": {
            "what": "Expose Gumroad admin functionality through an API and/or CLI so admin operations do not require the web UI.",
            "why": (
                "Programmatic admin access unblocks automation for Gumclaw, speeds bulk operations, "
                "and creates a stable foundation for tooling around risk reviews, user management, fee updates, "
                "and compliance workflows."
            ),
        },
        "pinned_decisions_to_preserve": [
            "Do not build the CLI around the current OpenAPI/helper-tools spec approach.",
            "Use an explicit admin API/client contract as the source of truth.",
            "Put the CLI under a gumroad admin namespace inside the existing Gumroad CLI.",
            "Reuse existing admin/helper behavior where it is already correct.",
            "Place the clearer backend contract under /internal/admin.",
        ],
        "open_question_answers": {
            "which_admin_actions_to_prioritize": prioritized_actions,
            "auth_model": {
                "recommendation": "Use existing Gumroad admin identity and role checks to mint short-lived scoped admin CLI tokens.",
                "avoid": [
                    "Long-lived static API keys for human admins.",
                    "Using browser session cookies as the CLI auth primitive.",
                    "Public OAuth app scopes for internal admin actions.",
                ],
                "required_controls": [
                    "2FA-backed login or device/browser auth flow.",
                    "Per-action scopes such as admin:read:user, admin:review:compliance, admin:write:risk, admin:write:fees.",
                    "Actor, reason, target, source IP/device, and request id in every audit event.",
                    "Short token lifetime with revocation and least-privilege scopes.",
                ],
            },
            "api_surface": {
                "recommendation": "Create a separate internal admin API under /internal/admin, not the public v2 API.",
                "why": [
                    "Admin actions have different auth, audit, approval, and abuse-risk requirements than public creator APIs.",
                    "Keeping it internal avoids leaking admin-only semantics into the public API versioning contract.",
                    "The CLI can use a typed admin client without treating OpenAPI as the source of truth.",
                ],
            },
            "cli_shape": {
                "recommendation": "Extend the existing Gumroad CLI with a gumroad admin namespace.",
                "examples": [
                    "gumroad admin users lookup --email buyer@example.com --reason support-review",
                    "gumroad admin purchases lookup --purchase-id demo-123 --read-only",
                    "gumroad admin refunds prepare --case-id refund-123 --confirm-required",
                    "gumroad admin compliance prepare --target-id creator-123 --reason chargeback-risk --confirm-required",
                    "gumroad admin risk state set --creator-id creator-123 --risk-state elevated --reason chargeback-spike --confirm-required",
                    "gumroad admin fees update --creator-id creator-123 --fee-percent 10 --reason contract-change --confirm-required",
                ],
            },
        },
        "production_contract_defaults": {
            "request_fields": [
                "actor_id",
                "reason",
                "target_type",
                "target_id",
                "idempotency_key for writes",
                "confirmation_token or prepared_action_id before execution",
            ],
            "response_fields": [
                "request_id",
                "action_id",
                "resolved_target",
                "preflight_checks",
                "diff_or_evidence",
                "audit_event_summary",
                "blocked_reason",
                "requires_approval",
                "expires_at for prepared actions",
            ],
            "error_style": "Return actionable errors that tell the CLI or agent which identifier, scope, approval, or reason is missing.",
        },
        "mcp_demo_mapping": {
            "purpose": "Use Gumroad Merchant MCP as a local command-workflow harness for the proposed admin API/CLI contract.",
            "tools": [
                "get_admin_api_cli_recommendation",
                "list_admin_action_templates",
                "build_cli_command_preview",
                "preview_admin_action",
            ],
            "boundary": PREVIEW_BOUNDARY,
        },
        "acceptance_tests": [
            "List admin action templates and confirm user lookup, compliance review, risk state change, and fee update are present.",
            "Prepare each prioritized command and verify it returns command_text, preflight_checks, audit_note, execution_mode, and requires_confirmation.",
            "Verify write-like actions are blocked in the prototype and require human approval in the proposed live contract.",
            "Verify the recommendation keeps admin APIs under /internal/admin and CLI commands under gumroad admin.",
            "Verify all responses include a clear audit/logging requirement.",
        ],
        "action_ready": True,
        "execution_mode": "admin_cli_plan",
        "requires_confirmation": True,
    }


def get_admin_action_preview_summary(
    db_path: Path | str,
    product_id: str = "all",
    limit: int = 6,
) -> dict[str, Any]:
    """Return available admin actions plus seeded Refund Ops ties for an endpoint or agent."""
    max_items = max(1, min(25, int(limit or 6)))
    refund_cases = query_refund_case_rows(db_path, product_id=product_id)[:max_items]
    return {
        "source_context": copy.deepcopy(SOURCE_CONTEXT),
        "boundary": PREVIEW_BOUNDARY,
        "action_ready": True,
        "execution_mode": "admin_action_workflows",
        "requires_confirmation": True,
        "template_count": len(ACTION_TEMPLATES),
        "api_cli_recommendation": get_admin_api_cli_recommendation(),
        "templates": list_admin_action_templates(),
        "blocked_write_templates": [
            template["id"] for template in ACTION_TEMPLATES if template["unsafe_write"]
        ],
        "seeded_purchase_examples": _purchase_examples(db_path, product_id=product_id, limit=max_items),
        "refund_ops_case_suggestions": [
            {
                "case_id": refund_case["case_id"],
                "purchase_id": refund_case["purchase_id"],
                "product_id": refund_case["product_id"],
                "label": refund_case["label"],
                "case_type": refund_case["case_type"],
                "status": refund_case["status"],
                "risk_score": refund_case["risk_score"],
                "audit_note": refund_case["audit_note"],
                "suggested_actions": _case_suggestions(refund_case),
            }
            for refund_case in refund_cases
        ],
    }
