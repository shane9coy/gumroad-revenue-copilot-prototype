"""Reviewable local Shortest-style QA scenarios for Gumroad Merchant.

The generated tests are deterministic natural-language journeys for human or
agent review. They do not automate a browser, call external services, or mutate
Gumroad Merchant data.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


QA_VERSION = "shortest-qa-v1"

REQUIRED_QA_FIELDS = (
    "id",
    "suite_id",
    "target_surface",
    "setup",
    "steps",
    "assertions",
    "risk_covered",
    "pass_fail_evidence",
)

_SUITES: tuple[dict[str, Any], ...] = (
    {
        "id": "refund_ops",
        "name": "Refund Ops",
        "purpose": "Verify review-only refund, dispute, buyer-reply, and audit-note journeys.",
        "target_surfaces": ["Refund Ops panel", "Refund Ops API", "Merchant chat refund routing"],
    },
    {
        "id": "content_radar",
        "name": "Content Radar",
        "purpose": "Verify creator-facing content, metadata, and positioning recommendations.",
        "target_surfaces": ["Analytics signals", "Product content review", "Action review payload"],
    },
    {
        "id": "retention_saver",
        "name": "Retention Saver",
        "purpose": "Verify churn, refund, and customer-export summaries stay strategic and privacy-safe.",
        "target_surfaces": ["Retention dashboard", "Churn/refund correlation", "Customer export summary"],
    },
    {
        "id": "admin_action_preview",
        "name": "Admin/CLI Action Preview",
        "purpose": "Verify admin and CLI previews expose suggested actions without applying them.",
        "target_surfaces": ["Admin action preview", "CLI smoke output", "Review-only action payloads"],
    },
    {
        "id": "merchant_chat_fallback",
        "name": "Merchant Chat Fallback Routing",
        "purpose": "Verify deterministic chat routing when live model access is unavailable or disabled.",
        "target_surfaces": ["Merchant chat", "Fallback router", "Help-doc routing"],
    },
)


_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "id": "refund_ops_dispute_packet_review_only",
        "suite_id": "refund_ops",
        "title": "Chargeback evidence packet can be reviewed without being submitted",
        "priority": "critical",
        "target_surface": "Refund Ops dispute mode and Merchant chat refund routing",
        "persona": "Creator reviewing a high-risk chargeback before taking action",
        "setup": [
            "Use the seeded Gumroad Merchant dataset.",
            "Select product prod-audio-pack or all products.",
            "Keep the agent in deterministic fallback mode or force the Refund Ops endpoint directly.",
        ],
        "steps": [
            "Open Refund Ops and switch to Dispute mode.",
            "Ask Merchant chat: Build the chargeback evidence packet for the highest-risk dispute.",
            "Open the returned case detail and compare the timeline, evidence checklist, policy snapshot, and audit note.",
            "Stop before any external submission step.",
        ],
        "assertions": [
            "The answer names a chargeback dispute case and includes a review-only boundary.",
            "The packet includes purchase evidence, delivery/access evidence, product-page promise review, and support-thread review.",
            "The response includes an audit note but does not claim that Gumroad, Stripe, PayPal, or the card network received the packet.",
            "The case remains a local seeded case with no mutation or send status.",
        ],
        "risk_covered": [
            "Accidental dispute submission from a preview flow.",
            "Incomplete evidence packet causing a creator to trust a weak dispute response.",
            "Incorrect routing of chargeback requests into normal refund replies.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Response or JSON includes review_only=true or the phrase review-only.",
                "Evidence checklist has purchase, delivery/access, product-page, and support-contact items.",
                "No text says submitted, sent, refunded, won, or closed as a completed external action.",
            ],
            "fail": [
                "The journey applies the dispute response, sends an email, issues a refund, or marks the case resolved.",
                "The packet lacks an audit note or policy snapshot.",
                "The case is treated as a buyer reply instead of a chargeback dispute.",
            ],
            "capture": ["case_id", "case_type", "ready_for_review", "copy_text", "audit_note"],
        },
        "source_tools": ["list_refund_cases_tool", "build_dispute_evidence_pack_tool", "run_agent_chat"],
        "read_only": True,
    },
    {
        "id": "refund_ops_buyer_reply_manual_decision",
        "suite_id": "refund_ops",
        "title": "Buyer reply draft keeps the refund decision manual",
        "priority": "high",
        "target_surface": "Refund Ops review queue and buyer-reply preview",
        "persona": "Creator deciding how to respond to a refund request",
        "setup": [
            "Use seeded Refund Ops cases.",
            "Select Review mode or ask for the top refund request reply.",
            "Do not connect a mail sender or payment API.",
        ],
        "steps": [
            "Ask for the top buyer reply draft.",
            "Read the recommended action, copy text, and audit note.",
            "Check whether the draft explains the included files, compatibility notes, and support path.",
            "Confirm the refund decision remains a manual review step.",
        ],
        "assertions": [
            "The output is a draft buyer reply, not a sent email.",
            "The draft gives the buyer a support-first path before any refund decision.",
            "The audit note records triage context without claiming a refund was issued.",
            "The case amount and case label are visible enough for a creator to verify the target case.",
        ],
        "risk_covered": [
            "Sending a refund response automatically.",
            "Skipping support resolution for expectation or compatibility issues.",
            "Losing case context when copying a draft response.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Response includes draft/review-only language.",
                "Response includes recommended_action and audit_note.",
                "No outbound email, refund, or case-close side effect is described.",
            ],
            "fail": [
                "The draft says the refund has already been approved or denied.",
                "The journey hides the case id or amount from the reviewer.",
                "The response recommends contacting the buyer without providing copy or rationale.",
            ],
            "capture": ["case_id", "label", "amount.formatted", "copy_text", "recommended_action"],
        },
        "source_tools": ["list_refund_cases_tool", "draft_refund_reply_tool", "run_agent_chat"],
        "read_only": True,
    },
    {
        "id": "content_radar_discover_metadata_gap",
        "suite_id": "content_radar",
        "title": "Discover metadata gap is framed as a content fix, not a ranking guarantee",
        "priority": "high",
        "target_surface": "Content Radar signal card and action review payload",
        "persona": "Creator investigating why Discover traffic is not converting cleanly",
        "setup": [
            "Use seeded product prod-design-kit.",
            "Keep date range at 30 days.",
            "Load detected signals or the action review payload.",
        ],
        "steps": [
            "Ask for the next content move for Minimal Landing Page Kit.",
            "Open the Content Radar or detected-signals output for missing category/tags.",
            "Review the recommendation and the evidence behind it.",
            "Check that the recommendation asks for metadata and copy cleanup rather than promising algorithmic reach.",
        ],
        "assertions": [
            "The journey points to category, tags, description, reviews, or Discover impressions as evidence.",
            "The action stays in review mode and describes what the creator should inspect or edit.",
            "The wording does not claim Gumroad Discover placement will improve automatically.",
            "The recommendation is specific to buyer, use case, format, or included assets.",
        ],
        "risk_covered": [
            "Overpromising Discover ranking outcomes.",
            "Making generic SEO advice detached from seeded product evidence.",
            "Confusing content recommendation with an auto-applied product edit.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Signal or answer references metadata completeness, Discover impressions, or missing tags/category.",
                "Action payload includes label, copy_text, and steps for human review.",
                "No mutation status or saved product edit is returned.",
            ],
            "fail": [
                "The recommendation says Gumroad will rank the product higher as a guaranteed outcome.",
                "The payload lacks evidence for why this product needs metadata work.",
                "The flow edits product copy without a preview.",
            ],
            "capture": ["product.id", "signal.id", "signal.title", "evidence", "action.steps"],
        },
        "source_tools": ["get_detected_signals_tool", "get_action_review_tool"],
        "read_only": True,
    },
    {
        "id": "content_radar_source_angle_reuse",
        "suite_id": "content_radar",
        "title": "Winning source angle is reused as a testable content hypothesis",
        "priority": "medium",
        "target_surface": "Traffic-source analytics and Content Radar recommendation",
        "persona": "Creator deciding whether to reuse a strong campaign angle on the product page",
        "setup": [
            "Use all products or prod-creator-os.",
            "Load traffic sources, UTM links, and detected signals.",
            "Do not change paid spend, product price, or page copy during the test.",
        ],
        "steps": [
            "Ask which source is strongest and what content angle should be reused.",
            "Compare the answer with the current top traffic source and UTM campaign.",
            "Confirm the recommendation describes a controlled content test.",
            "Check that direct traffic is treated as ambiguous attribution rather than proof of organic demand.",
        ],
        "assertions": [
            "The response cites source conversion, sales, revenue, or UTM evidence.",
            "The recommendation keeps the page stable except for a proposed reviewable copy test.",
            "Direct traffic is caveated as possibly containing apps, email, bookmarks, or private shares.",
            "The action is a hypothesis to review, not a command to broaden spend.",
        ],
        "risk_covered": [
            "Misreading source quality from raw traffic alone.",
            "Crediting Direct traffic without attribution cleanup.",
            "Turning a content hypothesis into an unreviewed campaign change.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Answer includes at least one source name plus sales, conversion, or revenue.",
                "Answer uses language like test, review, compare, or track.",
                "No auto-launch or budget-change language appears.",
            ],
            "fail": [
                "The source recommendation is based only on views.",
                "The journey says to widen spend immediately.",
                "The output ignores UTM or attribution cleanliness when direct traffic is involved.",
            ],
            "capture": ["source.name", "source.sales", "source.conversion", "utm.campaign", "recommendation"],
        },
        "source_tools": ["get_traffic_sources_tool", "get_dashboard_summary_tool", "run_agent_chat"],
        "read_only": True,
    },
    {
        "id": "retention_saver_churn_refund_mismatch",
        "suite_id": "retention_saver",
        "title": "Churn and refunds are diagnosed as expectation-fit risk before pricing changes",
        "priority": "high",
        "target_surface": "Retention Saver dashboard and strategy fallback answer",
        "persona": "Creator reviewing whether retention issues require a product-page or pricing change",
        "setup": [
            "Use prod-audio-pack or all products.",
            "Load dashboard summary with churn, refund rate, and correlations.",
            "Keep customer-level rows summarized; do not expose buyer names or emails.",
        ],
        "steps": [
            "Ask Merchant chat for the retention risk behind churn and refunds.",
            "Open the churn x refunds correlation insight.",
            "Compare the recommendation with refund rate and canceled subscription evidence.",
            "Confirm the next move focuses on expectations, onboarding, compatibility, or audience fit before pricing.",
        ],
        "assertions": [
            "The response includes churn and refund evidence from the selected product or portfolio.",
            "The recommendation does not jump directly to a price cut or mass coupon.",
            "The customer export stays aggregate-only and does not return buyer names or emails.",
            "The action is framed as review-only strategy.",
        ],
        "risk_covered": [
            "Misdiagnosing churn/refunds as only a pricing problem.",
            "Leaking synthetic customer details into strategy answers.",
            "Overcorrecting the offer before fixing expectation mismatch.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Answer includes churn rate or canceled count and refund rate or refund count.",
                "Customer export evidence is summarized and privacy-safe.",
                "Recommendation mentions expectations, onboarding, compatibility, or audience fit.",
            ],
            "fail": [
                "The answer exposes buyer names, emails, or row-level customer data.",
                "The first recommendation is a blanket price cut without evidence.",
                "The flow applies retention emails, coupons, or product edits automatically.",
            ],
            "capture": ["churn.rate", "churn.canceled", "refund_rate", "customer_sales.privacy_note", "correlation.title"],
        },
        "source_tools": ["get_dashboard_summary_tool", "build_strategy_plan_tool", "run_agent_chat"],
        "read_only": True,
    },
    {
        "id": "retention_saver_do_not_contact_boundary",
        "suite_id": "retention_saver",
        "title": "Customer export summary respects do-not-contact and sample-data boundaries",
        "priority": "medium",
        "target_surface": "Retention Saver customer export summary",
        "persona": "Creator considering a retention save campaign from customer export data",
        "setup": [
            "Use dashboard summary for all products.",
            "Inspect customer_sales summary fields only.",
            "Treat all customer export rows as synthetic samples.",
        ],
        "steps": [
            "Ask what customer export data can safely support a retention decision.",
            "Review sample row count, do-not-contact count, refunded rows, recurring rows, and top referrers.",
            "Confirm the answer uses aggregate counts and summary warnings.",
            "Confirm the answer avoids generating an outreach list or sending campaign copy.",
        ],
        "assertions": [
            "The output includes sample_only=true or equivalent warning language.",
            "The output includes the do-not-contact count when discussing outreach.",
            "No buyer name, buyer email, or individual purchase row is returned.",
            "The recommendation is to review strategy, not contact every customer.",
        ],
        "risk_covered": [
            "Ignoring do-not-contact status in retention workflows.",
            "Treating synthetic sample rows as source-of-truth revenue.",
            "Producing outreach actions from aggregate QA data.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "customer_sales.sample_only is true or answer says synthetic sample.",
                "privacy_note or summary_warning is present.",
                "No buyer_name or buyer_email keys appear in the returned payload.",
            ],
            "fail": [
                "The flow exports customer emails.",
                "The answer treats sample rows as portfolio revenue totals.",
                "The journey recommends contacting do-not-contact buyers.",
            ],
            "capture": [
                "customer_sales.sample_row_count",
                "customer_sales.sample_do_not_contact_rows",
                "customer_sales.summary_warning",
                "customer_sales.privacy_note",
            ],
        },
        "source_tools": ["get_dashboard_summary_tool", "load_customer_sales_summary"],
        "read_only": True,
    },
    {
        "id": "admin_preview_action_payload_no_mutation",
        "suite_id": "admin_action_preview",
        "title": "Admin action preview exposes copy and steps without applying the action",
        "priority": "critical",
        "target_surface": "Admin/CLI Action Preview payload",
        "persona": "Internal reviewer checking a suggested product-page or metadata action",
        "setup": [
            "Use a known signal id from detected signals.",
            "Select a product with an actionable recommendation, such as prod-design-kit or prod-audio-pack.",
            "Run through endpoint, agent tool, or CLI preview only.",
        ],
        "steps": [
            "Request the action review for one signal id.",
            "Inspect the payload label, copy_text, action kind, and ordered steps.",
            "Confirm the payload gives the reviewer enough context to approve, edit, or reject.",
            "Verify no product, price, refund, email, or dispute state changed after preview.",
        ],
        "assertions": [
            "The result has found=true for a valid signal id.",
            "The action includes a human-readable label, copy_text, and steps.",
            "The recommendation is contextualized by product evidence.",
            "The result does not include an applied, saved, sent, or submitted status.",
        ],
        "risk_covered": [
            "Admin preview silently mutating production-like state.",
            "Reviewer receiving an action without enough evidence to judge it.",
            "Action payloads becoming too low-level for a merchant workflow.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Payload includes action.kind, action.label, action.copy_text, and action.steps.",
                "Payload remains a preview and contains no mutation status.",
                "Running the preview twice returns the same content for the same input.",
            ],
            "fail": [
                "The preview writes product metadata or changes a case status.",
                "The action has no steps or no copy text.",
                "The second run differs without a changed input.",
            ],
            "capture": ["signal_id", "found", "action.kind", "action.label", "action.steps"],
        },
        "source_tools": ["get_detected_signals_tool", "get_action_review_tool"],
        "read_only": True,
    },
    {
        "id": "admin_preview_cli_smoke_json_shape",
        "suite_id": "admin_action_preview",
        "title": "CLI smoke returns reviewable JSON with suite coverage and no external dependency",
        "priority": "medium",
        "target_surface": "scripts/run_shortest_qa_smoke.py",
        "persona": "Developer validating QA scenario generation before wiring endpoints",
        "setup": [
            "Run from the Gumroad Merchant prototype repo root.",
            "Do not start a browser or backend server.",
            "Do not require OpenAI, Redis, or network access.",
        ],
        "steps": [
            "Run python3 scripts/run_shortest_qa_smoke.py.",
            "Read the printed checks JSON.",
            "Confirm all required suites are represented.",
            "Confirm every test has setup, steps, assertions, risk_covered, and pass/fail evidence.",
        ],
        "assertions": [
            "The script exits with status 0.",
            "The printed checks object has passed=true.",
            "The generator output is JSON serializable.",
            "The smoke does not write to Gumroad data or call external services.",
        ],
        "risk_covered": [
            "QA generator drifting into non-serializable structures.",
            "A suite being accidentally removed from the local catalog.",
            "Smoke validation depending on live services.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "stdout includes passed=true.",
                "suite_count is at least five and test_count is at least the scenario catalog size.",
                "No browser, backend, Redis, OpenAI, or network prerequisite is required.",
            ],
            "fail": [
                "Smoke exits non-zero.",
                "A required suite id is missing.",
                "JSON serialization fails.",
            ],
            "capture": ["checks.passed", "checks.suite_coverage", "checks.required_field_coverage"],
        },
        "source_tools": ["get_shortest_qa_summary", "generate_shortest_qa_tests", "list_shortest_qa_suites"],
        "read_only": True,
    },
    {
        "id": "chat_fallback_refund_ops_route",
        "suite_id": "merchant_chat_fallback",
        "title": "Fallback chat routes refund operations into Refund Ops instead of generic strategy",
        "priority": "critical",
        "target_surface": "Merchant chat deterministic fallback router",
        "persona": "Creator without live model access asking for refund triage",
        "setup": [
            "Force deterministic fallback mode or run without an OpenAI key.",
            "Use product prod-audio-pack or all products.",
            "Seeded SQLite data is available locally.",
        ],
        "steps": [
            "Ask: Which refund case needs review first, and can you draft the buyer reply?",
            "Read the response, citations, and fallback flag.",
            "Confirm the route returns Refund Ops case evidence instead of a generic growth plan.",
            "Confirm the answer keeps the reply as a draft.",
        ],
        "assertions": [
            "The result has fallback=true.",
            "The response includes a refund case id or Refund Ops summary.",
            "Citations include refund_case or refund-ops summary context.",
            "The output does not claim the buyer reply was sent.",
        ],
        "risk_covered": [
            "Refund triage questions falling through to generic next-move strategy.",
            "Fallback mode losing safety boundaries from live-agent instructions.",
            "Creator mistaking a draft reply for a sent message.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "fallback is true.",
                "Answer includes refund case, buyer reply draft, review-only, or audit note language.",
                "Citations include product and refund case or refund summary evidence.",
            ],
            "fail": [
                "Answer gives only marketing strategy with no refund case evidence.",
                "Answer says it sent the reply or issued the refund.",
                "fallback is false when live model access was disabled.",
            ],
            "capture": ["fallback", "answer", "citations[].type", "model"],
        },
        "source_tools": ["run_agent_chat", "fallback_chat", "fallback_refund_ops"],
        "read_only": True,
    },
    {
        "id": "chat_fallback_mixed_help_analytics_route",
        "suite_id": "merchant_chat_fallback",
        "title": "Fallback chat combines analytics and help-doc citations for refund payout questions",
        "priority": "high",
        "target_surface": "Merchant chat mixed analytics/help-doc fallback route",
        "persona": "Creator asking how rising refunds affect payout balance",
        "setup": [
            "Force deterministic fallback mode.",
            "Use all products and the 30-day range.",
            "Seeded Gumroad help-doc corpus is loaded locally.",
        ],
        "steps": [
            "Ask: Our refunds are up in analytics; how can that affect payout balance according to Gumroad docs?",
            "Read the response and citations.",
            "Check that the answer includes selected analytics and loaded Gumroad documentation.",
            "Confirm the answer says when policy detail is only known from the loaded local corpus.",
        ],
        "assertions": [
            "The response includes refund count, refund amount, or refund rate from seeded analytics.",
            "The response includes Gumroad help-doc source URLs for policy context.",
            "Citations include both product and help_doc types.",
            "The route does not invent unsupported policy beyond the loaded docs.",
        ],
        "risk_covered": [
            "Policy answers being invented without doc citations.",
            "Analytics-only route ignoring Gumroad payout policy context.",
            "Help-doc-only route ignoring the merchant's selected product analytics.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Answer contains a metric such as refund rate or refunded amount.",
                "Answer contains at least one gumroad.com help source URL.",
                "Citation types include product and help_doc.",
            ],
            "fail": [
                "The answer has no source URL for policy claims.",
                "The answer has no seeded analytics evidence.",
                "The answer asserts a policy outside the loaded help docs.",
            ],
            "capture": ["answer", "citations[].type", "citations[].excerpt"],
        },
        "source_tools": ["run_agent_chat", "fallback_mixed_help_analytics", "search_gumroad_help_docs_tool"],
        "read_only": True,
    },
    {
        "id": "chat_fallback_unknown_policy_boundary",
        "suite_id": "merchant_chat_fallback",
        "title": "Fallback chat refuses unsupported policy questions with closest loaded sources",
        "priority": "high",
        "target_surface": "Merchant chat unknown-policy fallback route",
        "persona": "Creator asking for unsupported crypto payout policy",
        "setup": [
            "Force deterministic fallback mode.",
            "Ask a policy question outside the seeded Gumroad docs.",
            "Keep help-doc search limited to the local corpus.",
        ],
        "steps": [
            "Ask whether Gumroad supports crypto payouts or token-gated Bitcoin settlement.",
            "Read the answer and citations.",
            "Confirm the answer says the loaded docs do not answer the question.",
            "Confirm any citations are labeled as closest loaded sources, not proof of the unsupported claim.",
        ],
        "assertions": [
            "The response contains a clear unknown-from-loaded-docs statement.",
            "The response does not invent support for crypto, Bitcoin, or token-gated payout settlement.",
            "Closest sources, if present, come from the loaded Gumroad corpus.",
            "The fallback route remains deterministic and local.",
        ],
        "risk_covered": [
            "Invented Gumroad policy.",
            "Misusing nearby citations as proof for an unsupported answer.",
            "Live-model absence causing lower safety in policy routing.",
        ],
        "pass_fail_evidence": {
            "pass": [
                "Answer includes I do not know that from the loaded Gumroad docs or equivalent.",
                "No statement says crypto payouts are supported.",
                "Any citations are help_doc citations from gumroad.com source URLs.",
            ],
            "fail": [
                "The answer gives unsupported crypto payout instructions.",
                "The answer cites a nearby doc as if it proves the unsupported policy.",
                "The route fails open into generic advice.",
            ],
            "capture": ["answer", "citations[].type", "citations[].label", "fallback"],
        },
        "source_tools": ["run_agent_chat", "fallback_unknown_help_docs", "search_gumroad_help_docs_tool"],
        "read_only": True,
    },
)


_FILTER_ALIASES = {
    "admin_cli_action_preview": "admin_action_preview",
    "admin_action": "admin_action_preview",
    "cli_action_preview": "admin_action_preview",
    "merchant_chat_fallback_routing": "merchant_chat_fallback",
    "chat_fallback": "merchant_chat_fallback",
    "fallback_routing": "merchant_chat_fallback",
}


def _normalize_filter(value: str | None) -> str:
    normalized = (
        str(value or "all")
        .strip()
        .lower()
        .replace("/", "_")
        .replace("-", "_")
        .replace(" ", "_")
    )
    return _FILTER_ALIASES.get(normalized or "all", normalized or "all")



def _scenario_matches(
    scenario: dict[str, Any],
    suite_id: str,
    target_surface: str,
    priority: str,
) -> bool:
    if suite_id != "all" and scenario["suite_id"] != suite_id:
        return False
    if priority != "all" and scenario.get("priority") != priority:
        return False
    if target_surface != "all":
        haystack = " ".join(
            [
                str(scenario.get("target_surface", "")),
                str(scenario.get("title", "")),
                " ".join(str(item) for item in scenario.get("risk_covered", [])),
            ]
        ).lower()
        if target_surface.replace("_", " ") not in haystack and target_surface not in haystack:
            return False
    return True


def _limit_items(items: list[dict[str, Any]], limit: int | str | None) -> list[dict[str, Any]]:
    if limit is None:
        return items
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return items
    if value <= 0:
        return []
    return items[: min(value, 50)]


def _suite_counts() -> dict[str, int]:
    counts = {suite["id"]: 0 for suite in _SUITES}
    for scenario in _SCENARIOS:
        counts[scenario["suite_id"]] = counts.get(scenario["suite_id"], 0) + 1
    return counts


def list_shortest_qa_suites() -> list[dict[str, Any]]:
    """Return available Shortest QA suites with deterministic scenario counts."""
    counts = _suite_counts()
    return [
        {
            **deepcopy(suite),
            "scenario_count": counts.get(suite["id"], 0),
            "read_only": True,
        }
        for suite in _SUITES
    ]


def generate_shortest_qa_tests(
    suite_id: str = "all",
    target_surface: str = "all",
    priority: str = "all",
    limit: int | str | None = None,
) -> dict[str, Any]:
    """Return natural-language QA journeys filtered for endpoint or agent use."""
    normalized_suite = _normalize_filter(suite_id)
    normalized_surface = _normalize_filter(target_surface)
    normalized_priority = _normalize_filter(priority)
    tests = [
        deepcopy(scenario)
        for scenario in _SCENARIOS
        if _scenario_matches(scenario, normalized_suite, normalized_surface, normalized_priority)
    ]
    tests = _limit_items(tests, limit)
    suite_ids = sorted({test["suite_id"] for test in tests})
    return {
        "version": QA_VERSION,
        "title": "Gumroad Merchant Shortest QA scenarios",
        "description": (
            "Deterministic local user-journey tests for reviewing Gumroad Merchant "
            "Refund Ops, Content Radar, Retention Saver, Admin Action Preview, and chat fallback behavior."
        ),
        "filters": {
            "suite_id": normalized_suite,
            "target_surface": normalized_surface,
            "priority": normalized_priority,
            "limit": limit,
        },
        "read_only": True,
        "deterministic": True,
        "external_dependencies": [],
        "required_fields": list(REQUIRED_QA_FIELDS),
        "suite_count": len(suite_ids),
        "test_count": len(tests),
        "suite_ids": suite_ids,
        "tests": tests,
    }


def get_shortest_qa_summary() -> dict[str, Any]:
    """Return a compact summary of generated QA coverage."""
    suites = list_shortest_qa_suites()
    scenario_ids = [scenario["id"] for scenario in _SCENARIOS]
    surfaces = sorted({scenario["target_surface"] for scenario in _SCENARIOS})
    priorities = sorted({scenario["priority"] for scenario in _SCENARIOS})
    return {
        "version": QA_VERSION,
        "name": "Gumroad Merchant Shortest QA Generator",
        "purpose": "Generate reviewable local QA journeys instead of low-level unit tests.",
        "read_only": True,
        "deterministic": True,
        "external_dependencies": [],
        "suite_count": len(suites),
        "test_count": len(_SCENARIOS),
        "suites": suites,
        "scenario_ids": scenario_ids,
        "target_surfaces": surfaces,
        "priorities": priorities,
        "required_fields": list(REQUIRED_QA_FIELDS),
        "coverage": {
            "refund_ops": "Refund queue, buyer reply draft, dispute evidence packet, audit boundary.",
            "content_radar": "Discover metadata gap, source angle reuse, attribution caution.",
            "retention_saver": "Churn/refund mismatch, customer export sample and privacy boundaries.",
            "admin_action_preview": "Action preview JSON shape, CLI smoke, no mutation.",
            "merchant_chat_fallback": "Refund Ops route, mixed help/analytics route, unknown policy boundary.",
        },
    }


def get_shortest_qa_test(test_id: str) -> dict[str, Any]:
    """Return one QA scenario by id, or a JSON-safe not-found payload."""
    normalized = str(test_id or "").strip()
    for scenario in _SCENARIOS:
        if scenario["id"] == normalized:
            return {"found": True, "test": deepcopy(scenario)}
    return {
        "found": False,
        "test_id": normalized,
        "available_test_ids": [scenario["id"] for scenario in _SCENARIOS],
    }


def shortest_qa_overview_sentence() -> str:
    """Return a concise natural-language summary for chat or CLI display."""
    summary = get_shortest_qa_summary()
    suite_names = ", ".join(suite["name"] for suite in summary["suites"])
    return (
        f"{summary['name']} provides {summary['test_count']} deterministic review-only "
        f"Shortest-style scenarios across {summary['suite_count']} suites: {suite_names}."
    )
