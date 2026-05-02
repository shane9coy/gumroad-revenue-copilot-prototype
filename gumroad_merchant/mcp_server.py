from __future__ import annotations

import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

from mcp.server.fastmcp import FastMCP

from gumroad_merchant.agent_actions import (
    apply_agent_action_tool,
    create_architecture_diagram_action_tool,
    create_roadmap_action_tool,
    create_tracked_campaign_action_tool,
    list_agent_actions_tool,
    stage_tracked_campaign_action_tool,
)
from gumroad_merchant.admin_action_preview_tools import (
    build_cli_command_preview as build_cli_command_preview_tool,
    get_admin_api_cli_recommendation as get_admin_api_cli_recommendation_tool,
    get_admin_action_preview_summary as get_admin_action_preview_summary_tool,
    list_admin_action_templates as list_admin_action_templates_tool,
    preview_admin_action as preview_admin_action_tool,
)
from gumroad_merchant.analytics_tools import (
    build_strategy_plan_tool,
    get_action_review_tool,
    get_dashboard_summary_tool,
    get_database_inventory_tool,
    get_detected_signals_tool,
    get_product_metrics_tool,
    get_traffic_sources_tool,
    search_products_tool,
)
from gumroad_merchant.content_radar_tools import (
    build_marketing_plan_tool,
    draft_campaign_assets_tool,
    get_content_radar_summary_tool,
    list_content_trends_tool,
)
from gumroad_merchant.database import refresh_database
from gumroad_merchant.help_tools import get_help_doc_inventory_tool, search_gumroad_help_docs_tool
from gumroad_merchant.refund_ops_tools import (
    build_dispute_evidence_pack_tool,
    draft_refund_reply_tool,
    get_refund_case_tool,
    get_refund_ops_summary_tool,
    get_refund_prevention_actions_tool,
    list_refund_cases_tool,
)
from gumroad_merchant.retention_saver_tools import (
    build_pause_offer_plan_tool,
    estimate_pause_revenue_saved_tool,
    get_retention_saver_summary_tool,
    list_cancellation_risks_tool,
)
from gumroad_merchant.settings import get_settings
from gumroad_merchant.shortest_qa_tools import (
    generate_shortest_qa_tests as generate_shortest_qa_tests_tool,
    get_shortest_qa_summary as get_shortest_qa_summary_tool,
    get_shortest_qa_test as get_shortest_qa_test_tool,
    list_shortest_qa_suites as list_shortest_qa_suites_tool,
)
from gumroad_merchant.tracked_campaigns import list_tracked_campaigns_tool


F = TypeVar("F", bound=Callable[..., Any])

DATA_SOURCE = "seeded_demo"
MODE_ENV = "GUMROAD_MERCHANT_MODE"
SERVER_NAME = "Gumroad Merchant"
SERVER_INSTRUCTIONS = (
    "Local seeded Gumroad Merchant tools for analytics, Refund Ops, Content Radar, "
    "Retention Saver, Admin Actions, Shortest QA, and Gumroad help-doc search. "
    "The seeded demo does not call Gumroad production services or mutate real "
    "creator accounts. Explicit agent action tools may write local test-profile "
    "action rows, tracked campaigns, or generated artifacts only. The production "
    "MCP direction is scoped read-write merchant automation: low-risk reads can run "
    "directly, while refunds, disputes, emails, posts, product edits, pricing, "
    "subscription, payout, product catalog, and sales workflows require scoped auth, "
    "preflight checks, confirmation, idempotency, and audit logs."
)

mcp = FastMCP(SERVER_NAME, instructions=SERVER_INSTRUCTIONS, json_response=True)


def db_path() -> Path:
    return get_settings().db_path


def ensure_seeded_runtime() -> None:
    os.environ[MODE_ENV] = "seeded"
    refresh_database(db_path(), force=False)


def envelope(
    tool: str,
    result: Any,
    ok: bool = True,
    error: dict[str, Any] | None = None,
    execution_mode: str = "seeded_analysis",
    requires_confirmation: bool = False,
    mode: str = "seeded",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": bool(ok),
        "tool": tool,
        "data_source": DATA_SOURCE,
        "execution_mode": execution_mode,
        "requires_confirmation": requires_confirmation,
        "mode": mode,
    }
    if ok:
        payload["result"] = result
    else:
        payload["error"] = error or {
            "message": "The MCP tool failed. Check the inputs and retry with a seeded product, case, signal, or test id.",
        }
        payload["result"] = {}
    return payload


def items_result(items: list[dict[str, Any]], **metadata: Any) -> dict[str, Any]:
    return {"items": items, **metadata}


def gumroad_merchant_help_menu_payload(section: str = "all") -> dict[str, Any]:
    normalized_section = str(section or "all").strip().lower().replace("-", "_").replace(" ", "_") or "all"
    sections = [
        {
            "id": "analytics",
            "title": "Analytics and next moves",
            "what_you_can_ask": [
                "Give me a portfolio revenue overview for the last 30 days.",
                "Show the top traffic sources and which one converts best.",
                "Build a realistic 3-month sales plan from current data.",
                "What action should I review first for this product?",
            ],
            "mcp_tools": [
                "get_product_metrics",
                "get_traffic_sources",
                "get_detected_signals",
                "get_dashboard_summary",
                "build_strategy_plan",
                "get_action_review",
            ],
        },
        {
            "id": "refund_ops",
            "title": "Refund Ops and chargeback disputes",
            "what_you_can_ask": [
                "Show Refund Ops cases that need review.",
                "Build a chargeback dispute evidence packet for the highest-risk case.",
                "Draft a buyer reply for this refund request.",
                "What should we change to reduce preventable refunds?",
            ],
            "mcp_tools": [
                "get_refund_ops_summary",
                "list_refund_cases",
                "get_refund_case",
                "build_dispute_evidence_pack",
                "draft_refund_reply",
                "get_refund_prevention_actions",
            ],
        },
        {
            "id": "growth",
            "title": "Content Radar and marketing plans",
            "what_you_can_ask": [
                "Find the best marketing angle from current analytics.",
                "Build a 4-week marketing plan.",
                "Draft campaign assets for the strongest trend.",
                "Which UTM campaign should we test next?",
                "Stage or create the tracked campaign row for the strongest trend.",
            ],
            "mcp_tools": [
                "get_content_radar_summary",
                "list_content_trends",
                "build_marketing_plan",
                "draft_campaign_assets",
                "stage_tracked_campaign_action",
                "create_tracked_campaign_action",
                "list_tracked_campaigns",
            ],
        },
        {
            "id": "actions",
            "title": "Local agent actions and artifacts",
            "what_you_can_ask": [
                "List pending agent actions.",
                "Apply this pending action.",
                "Generate a 30-day roadmap download.",
                "Generate the agent action architecture diagram.",
            ],
            "mcp_tools": [
                "list_agent_actions",
                "apply_agent_action",
                "generate_roadmap_artifact",
                "generate_architecture_diagram",
            ],
        },
        {
            "id": "retention",
            "title": "Retention Saver for memberships",
            "what_you_can_ask": [
                "Which products have the highest cancellation risk?",
                "Build a membership pause-offer plan.",
                "Estimate revenue saved if pause offers convert at 12%.",
                "Explain churn and refund mismatch before we change pricing.",
            ],
            "mcp_tools": [
                "get_retention_saver_summary",
                "list_cancellation_risks",
                "build_pause_offer_plan",
                "estimate_pause_revenue_saved",
            ],
        },
        {
            "id": "admin",
            "title": "Admin API and CLI actions",
            "what_you_can_ask": [
                "Answer Gumroad issue #4677's admin API/CLI open questions.",
                "List admin action templates.",
                "Prepare a user lookup command.",
                "Prepare a risk state change with confirmation requirements.",
                "Prepare a fee update command with audit requirements.",
            ],
            "mcp_tools": [
                "get_admin_api_cli_recommendation",
                "get_admin_action_preview_summary",
                "list_admin_action_templates",
                "build_cli_command_preview",
                "preview_admin_action",
            ],
        },
        {
            "id": "qa",
            "title": "Shortest QA",
            "what_you_can_ask": [
                "Generate QA tests for Refund Ops.",
                "Generate natural-language QA tests for Content Radar and Retention Saver.",
                "List QA suites.",
                "Show one QA test by id.",
            ],
            "mcp_tools": [
                "get_shortest_qa_summary",
                "list_shortest_qa_suites",
                "generate_shortest_qa_tests",
                "get_shortest_qa_test",
            ],
        },
        {
            "id": "search",
            "title": "Seeded product and help-doc search",
            "what_you_can_ask": [
                "Search products for Notion.",
                "Search Gumroad help docs for chargebacks.",
                "Which Gumroad help docs are loaded?",
                "Find docs about fees and Discover.",
            ],
            "mcp_tools": [
                "search_products",
                "search_gumroad_help_docs",
                "get_help_doc_inventory",
                "get_database_inventory",
            ],
        },
    ]
    selected_sections = sections if normalized_section == "all" else [
        item for item in sections if item["id"] == normalized_section
    ]
    if not selected_sections:
        selected_sections = sections
    tool_names = sorted({tool for item in sections for tool in item["mcp_tools"]} | {"get_gumroad_merchant_help_menu"})
    return {
        "name": "Gumroad Merchant MCP help menu",
        "summary": (
            "Ask your MCP-capable terminal agent to use Gumroad Merchant for analytics, Refund Ops, "
            "marketing, retention, admin API/CLI actions, QA generation, and seeded help-doc search."
        ),
        "capability_parity": {
            "status": "MCP exposes the chat agent's current business tool capabilities and adds MCP-specific discovery/admin helpers.",
            "not_in_mcp": [
                "browser UI state",
                "chat transcript persistence",
                "OpenAI chat model orchestration",
            ],
            "mcp_only_helpers": [
                "get_gumroad_merchant_help_menu",
                "get_admin_api_cli_recommendation",
                "get_shortest_qa_test",
                "apply_agent_action",
                "generate_architecture_diagram",
            ],
        },
        "how_to_use_in_terminal": [
            "Ask the terminal agent in natural language; it should call the relevant MCP tools.",
            "Start with: Use Gumroad Merchant to show me what I can do.",
            "Then ask for a specific workflow, such as a dispute packet, marketing plan, or admin command.",
        ],
        "common_parameters": {
            "product_id": "Use 'all' by default, or a seeded product id such as prod-audio-pack, prod-creator-os, prod-design-kit, or prod-zine-guide.",
            "date_range": "Use '30', '90', or 'all'.",
            "limit": "Most list tools accept a bounded integer limit.",
        },
        "sections": selected_sections,
        "available_tool_names": tool_names,
        "execution_scope": SERVER_INSTRUCTIONS,
    }


def tool_envelope(name: str, local_write: bool = False) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            ensure_seeded_runtime()
            try:
                return envelope(
                    name,
                    func(*args, **kwargs),
                    execution_mode="local_test_write" if local_write else "seeded_analysis",
                    requires_confirmation=False,
                    mode="local_test_write" if local_write else "seeded",
                )
            except Exception as exc:  # MCP boundary: return agent-actionable errors, not stack traces.
                return envelope(
                    name,
                    {},
                    ok=False,
                    execution_mode="local_test_write" if local_write else "seeded_analysis",
                    requires_confirmation=False,
                    mode="local_test_write" if local_write else "seeded",
                    error={
                        "message": f"{name} could not complete: {exc}",
                        "next_step": "Check product_id, date_range, case_id, signal_id, action_id, or suite_id and retry.",
                        "error_type": exc.__class__.__name__,
                    },
                )

        return cast(F, wrapper)

    return decorator


@mcp.tool()
@tool_envelope("get_gumroad_merchant_help_menu")
def get_gumroad_merchant_help_menu(section: str = "all") -> dict[str, Any]:
    """Return a terminal-friendly help menu with Gumroad Merchant capabilities, starter prompts, and tool names."""
    return gumroad_merchant_help_menu_payload(section=section)


@mcp.tool()
@tool_envelope("get_database_inventory")
def get_database_inventory() -> dict[str, Any]:
    """Return seeded local database inventory and snapshot metadata for Gumroad Merchant."""
    return get_database_inventory_tool(db_path())


@mcp.tool()
@tool_envelope("get_product_metrics")
def get_product_metrics(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return seeded product metrics for all products or one product over 30, 90, or all days."""
    return get_product_metrics_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("get_traffic_sources")
def get_traffic_sources(product_id: str = "all", date_range: str = "30", limit: int = 6) -> dict[str, Any]:
    """Return top seeded traffic sources with views, sales, conversion, AOV, and revenue."""
    items = get_traffic_sources_tool(db_path(), product_id=product_id, date_range=date_range, limit=limit)
    return items_result(items, product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("get_detected_signals")
def get_detected_signals(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return evidence-backed seeded revenue signals for merchant actions."""
    items = get_detected_signals_tool(db_path(), product_id=product_id, date_range=date_range)
    return items_result(items, product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("get_dashboard_summary")
def get_dashboard_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return churn, top locations, UTM links, customer-sales summary, and correlation insights."""
    return get_dashboard_summary_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("build_strategy_plan")
def build_strategy_plan(product_id: str = "all", date_range: str = "30", horizon_months: int = 3) -> dict[str, Any]:
    """Build a realistic 3- or 6-month seeded merchant strategy plan from analytics evidence."""
    return build_strategy_plan_tool(
        db_path(),
        product_id=product_id,
        date_range=date_range,
        horizon_months=horizon_months,
    )


@mcp.tool()
@tool_envelope("get_action_review")
def get_action_review(signal_id: str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return the action payload for one detected signal id."""
    return get_action_review_tool(db_path(), signal_id=signal_id, product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("get_refund_ops_summary")
def get_refund_ops_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return Refund Ops metrics, case counts, dispute exposure, and preventable refund estimate."""
    return get_refund_ops_summary_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("list_refund_cases")
def list_refund_cases(product_id: str = "all", date_range: str = "30", mode: str = "all", limit: int = 10) -> dict[str, Any]:
    """List seeded refund request and chargeback dispute cases for review."""
    items = list_refund_cases_tool(
        db_path(),
        product_id=product_id,
        date_range=date_range,
        mode=mode,
        limit=limit,
    )
    return items_result(items, product_id=product_id, date_range=date_range, mode=mode)


@mcp.tool()
@tool_envelope("get_refund_case")
def get_refund_case(case_id: str) -> dict[str, Any]:
    """Return one seeded Refund Ops case with evidence, timeline, policy snapshot, and audit events."""
    return get_refund_case_tool(db_path(), case_id=case_id)


@mcp.tool()
@tool_envelope("build_dispute_evidence_pack")
def build_dispute_evidence_pack(case_id: str) -> dict[str, Any]:
    """Build a chargeback dispute evidence packet for one Refund Ops case."""
    return build_dispute_evidence_pack_tool(db_path(), case_id=case_id)


@mcp.tool()
@tool_envelope("draft_refund_reply")
def draft_refund_reply(case_id: str) -> dict[str, Any]:
    """Draft a buyer refund reply for one seeded case without sending anything."""
    return draft_refund_reply_tool(db_path(), case_id=case_id)


@mcp.tool()
@tool_envelope("get_refund_prevention_actions")
def get_refund_prevention_actions(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return actions that can reduce future refunds by product/source pattern."""
    items = get_refund_prevention_actions_tool(db_path(), product_id=product_id, date_range=date_range)
    return items_result(items, product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("get_content_radar_summary")
def get_content_radar_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return seeded Content Radar opportunity metrics and top marketing signals."""
    return get_content_radar_summary_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("list_content_trends")
def list_content_trends(product_id: str = "all", date_range: str = "30", limit: int = 6) -> dict[str, Any]:
    """List seeded content trend angles with channel, campaign, KPI, risk, and evidence."""
    items = list_content_trends_tool(db_path(), product_id=product_id, date_range=date_range, limit=limit)
    return items_result(items, product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("build_marketing_plan")
def build_marketing_plan(product_id: str = "all", date_range: str = "30", horizon_weeks: int = 4) -> dict[str, Any]:
    """Build a Content Radar marketing plan from seeded trend signals."""
    return build_marketing_plan_tool(
        db_path(),
        product_id=product_id,
        date_range=date_range,
        horizon_weeks=horizon_weeks,
    )


@mcp.tool()
@tool_envelope("draft_campaign_assets")
def draft_campaign_assets(
    product_id: str = "all",
    date_range: str = "30",
    trend_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:
    """Draft campaign assets for a seeded trend and channel."""
    return draft_campaign_assets_tool(
        db_path(),
        product_id=product_id,
        date_range=date_range,
        trend_id=trend_id,
        channel=channel,
    )


@mcp.tool()
@tool_envelope("stage_tracked_campaign_action", local_write=True)
def stage_tracked_campaign_action(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Stage a local pending tracked-campaign action for approval without creating the campaign row."""
    return stage_tracked_campaign_action_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("create_tracked_campaign_action", local_write=True)
def create_tracked_campaign_action(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Apply a local tracked-campaign action once and return the saved UTM URL."""
    return create_tracked_campaign_action_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("list_tracked_campaigns")
def list_tracked_campaigns(product_id: str = "all", limit: int = 20) -> dict[str, Any]:
    """List local tracked campaign rows created in the test profile."""
    items = list_tracked_campaigns_tool(db_path(), product_id=product_id, limit=limit)
    return items_result(items, product_id=product_id)


@mcp.tool()
@tool_envelope("list_agent_actions")
def list_agent_actions(
    action_type: str = "all",
    status: str = "all",
    product_id: str = "all",
    limit: int = 20,
) -> dict[str, Any]:
    """List local pending/applied agent actions."""
    items = list_agent_actions_tool(db_path(), action_type=action_type, status=status, product_id=product_id, limit=limit)
    return items_result(items, action_type=action_type, status=status, product_id=product_id)


@mcp.tool()
@tool_envelope("apply_agent_action", local_write=True)
def apply_agent_action(action_id: str) -> dict[str, Any]:
    """Apply one pending local agent action by id. Idempotent once applied."""
    return apply_agent_action_tool(db_path(), action_id)


@mcp.tool()
@tool_envelope("generate_roadmap_artifact", local_write=True)
def generate_roadmap_artifact(product_id: str = "all", date_range: str = "30", horizon_days: int = 30) -> dict[str, Any]:
    """Generate a downloadable local 30-day or 60-day roadmap artifact."""
    return create_roadmap_action_tool(db_path(), product_id=product_id, date_range=date_range, horizon_days=horizon_days)


@mcp.tool()
@tool_envelope("generate_architecture_diagram", local_write=True)
def generate_architecture_diagram(diagram_type: str = "agent-action-system") -> dict[str, Any]:
    """Generate a downloadable local architecture diagram artifact."""
    return create_architecture_diagram_action_tool(db_path(), diagram_type=diagram_type)


@mcp.tool()
@tool_envelope("get_retention_saver_summary")
def get_retention_saver_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Return membership churn and pause-offer savings estimates from seeded local facts."""
    return get_retention_saver_summary_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("list_cancellation_risks")
def list_cancellation_risks(product_id: str = "all", date_range: str = "30", limit: int = 10) -> dict[str, Any]:
    """List seeded cancellation risk rows for membership retention review."""
    items = list_cancellation_risks_tool(db_path(), product_id=product_id, date_range=date_range, limit=limit)
    return items_result(items, product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("build_pause_offer_plan")
def build_pause_offer_plan(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
    """Build a one-month and three-month membership pause-offer plan."""
    return build_pause_offer_plan_tool(db_path(), product_id=product_id, date_range=date_range)


@mcp.tool()
@tool_envelope("estimate_pause_revenue_saved")
def estimate_pause_revenue_saved(product_id: str = "all", date_range: str = "30", save_rate: str | None = None) -> dict[str, Any]:
    """Estimate modeled membership revenue saved from pause offers using seeded churn data."""
    return estimate_pause_revenue_saved_tool(
        db_path(),
        product_id=product_id,
        date_range=date_range,
        save_rate=save_rate,
    )


@mcp.tool()
@tool_envelope("get_admin_action_preview_summary")
def get_admin_action_preview_summary(product_id: str = "all", limit: int = 6) -> dict[str, Any]:
    """Return simulated admin CLI action templates and Refund Ops case suggestions."""
    return get_admin_action_preview_summary_tool(db_path(), product_id=product_id, limit=limit)


@mcp.tool()
@tool_envelope("get_admin_api_cli_recommendation")
def get_admin_api_cli_recommendation() -> dict[str, Any]:
    """Resolve Gumroad issue #4677 open questions with an admin API/CLI recommendation."""
    return get_admin_api_cli_recommendation_tool()


@mcp.tool()
@tool_envelope("list_admin_action_templates")
def list_admin_action_templates() -> dict[str, Any]:
    """List simulated Gumroad admin action templates with required confirmation steps."""
    return items_result(list_admin_action_templates_tool())


@mcp.tool()
@tool_envelope("build_cli_command_preview")
def build_cli_command_preview(
    action_id: str = "purchase_lookup",
    purchase_id: str | None = None,
    case_id: str | None = None,
    product_id: str | None = None,
    creator_id: str | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
    target_id: str | None = None,
    risk_state: str | None = None,
    fee_percent: str | None = None,
    reason: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Render one simulated Gumroad admin CLI command string without executing it."""
    return build_cli_command_preview_tool(
        action_id,
        inputs={
            "purchase_id": purchase_id,
            "case_id": case_id,
            "product_id": product_id,
            "creator_id": creator_id,
            "user_id": user_id,
            "user_email": user_email,
            "target_id": target_id,
            "risk_state": risk_state,
            "fee_percent": fee_percent,
            "reason": reason,
            "note": note,
        },
    )


@mcp.tool()
@tool_envelope("preview_admin_action")
def preview_admin_action(
    action_id: str = "purchase_lookup",
    purchase_id: str | None = None,
    case_id: str | None = None,
    product_id: str | None = None,
    creator_id: str | None = None,
    user_id: str | None = None,
    user_email: str | None = None,
    target_id: str | None = None,
    risk_state: str | None = None,
    fee_percent: str | None = None,
    starts_at: str | None = None,
    ends_at: str | None = None,
    expires_at: str | None = None,
    reason: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Return a full admin CLI action package with command text, checks, and execution notes."""
    return preview_admin_action_tool(
        db_path(),
        action_id=action_id,
        purchase_id=purchase_id,
        case_id=case_id,
        product_id=product_id,
        inputs={
            "creator_id": creator_id,
            "user_id": user_id,
            "user_email": user_email,
            "target_id": target_id,
            "risk_state": risk_state,
            "fee_percent": fee_percent,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "expires_at": expires_at,
        },
        reason=reason,
        note=note,
    )


@mcp.tool()
@tool_envelope("get_shortest_qa_summary")
def get_shortest_qa_summary() -> dict[str, Any]:
    """Return deterministic Shortest QA suite coverage for Gumroad Merchant."""
    return get_shortest_qa_summary_tool()


@mcp.tool()
@tool_envelope("list_shortest_qa_suites")
def list_shortest_qa_suites() -> dict[str, Any]:
    """List Shortest QA suite metadata."""
    return items_result(list_shortest_qa_suites_tool())


@mcp.tool()
@tool_envelope("generate_shortest_qa_tests")
def generate_shortest_qa_tests(
    suite_id: str = "all",
    target_surface: str = "all",
    priority: str = "all",
    limit: int | None = None,
) -> dict[str, Any]:
    """Generate deterministic natural-language QA journeys for Gumroad Merchant lanes."""
    return generate_shortest_qa_tests_tool(
        suite_id=suite_id,
        target_surface=target_surface,
        priority=priority,
        limit=limit,
    )


@mcp.tool()
@tool_envelope("get_shortest_qa_test")
def get_shortest_qa_test(test_id: str) -> dict[str, Any]:
    """Return one deterministic Shortest QA scenario by id."""
    return get_shortest_qa_test_tool(test_id)


@mcp.tool()
@tool_envelope("search_products")
def search_products(query: str = "", limit: int = 5) -> dict[str, Any]:
    """Search seeded Gumroad Merchant products by name, creator, category, or tag."""
    items = search_products_tool(db_path(), query=query, limit=limit)
    return items_result(items, query=query)


@mcp.tool()
@tool_envelope("search_gumroad_help_docs")
def search_gumroad_help_docs(query: str, category: str = "money_ops", limit: int = 5) -> dict[str, Any]:
    """Search seeded official Gumroad help/pricing docs through local SQLite FTS."""
    items = search_gumroad_help_docs_tool(db_path(), query=query, category=category, limit=limit)
    return items_result(items, query=query, category=category)


@mcp.tool()
@tool_envelope("get_help_doc_inventory")
def get_help_doc_inventory() -> dict[str, Any]:
    """Return the seeded Gumroad help/pricing docs available to Gumroad Merchant."""
    return get_help_doc_inventory_tool(db_path())


def main() -> None:
    ensure_seeded_runtime()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
