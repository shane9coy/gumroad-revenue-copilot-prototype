from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gumroad_merchant.agent_actions import (
    ARCHITECTURE_DIAGRAM_ACTION,
    ROADMAP_ACTION,
    TRACKED_CAMPAIGN_ACTION,
    apply_latest_pending_action_tool,
    create_architecture_diagram_action_tool,
    create_roadmap_action_tool,
    create_tracked_campaign_action_tool,
    list_agent_actions_tool,
    stage_tracked_campaign_action_tool,
)
from gumroad_merchant.admin_action_preview_tools import (
    build_cli_command_preview as build_cli_command_preview_tool,
    get_admin_action_preview_summary as get_admin_action_preview_summary_tool,
    list_admin_action_templates as list_admin_action_templates_tool,
    preview_admin_action as preview_admin_action_tool,
)
from gumroad_merchant.analytics_tools import (
    build_strategy_plan_tool,
    detect_signals_for_metrics,
    format_currency,
    format_percent,
    get_action_review_tool,
    get_dashboard_summary_tool,
    get_database_inventory_tool,
    get_detected_signals_tool,
    get_product_metrics_tool,
    get_traffic_sources_tool,
    load_dashboard_summary,
    search_products_tool,
)
from gumroad_merchant.content_radar_tools import (
    build_marketing_plan_tool,
    content_radar_overview_sentence,
    draft_campaign_assets_tool,
    get_content_radar_summary_tool,
    list_content_trends_tool,
)
from gumroad_merchant.help_tools import get_help_doc_inventory_tool, search_gumroad_help_docs_tool
from gumroad_merchant.observability import payload_summary, trace_event, trace_span
from gumroad_merchant.refund_ops_tools import (
    build_dispute_evidence_pack_tool,
    draft_refund_reply_tool,
    get_refund_case_tool,
    get_refund_ops_summary_tool,
    get_refund_prevention_actions_tool,
    list_refund_cases_tool,
    refund_ops_overview_sentence,
)
from gumroad_merchant.retention_saver_tools import (
    build_pause_offer_plan_tool,
    estimate_pause_revenue_saved_tool,
    get_retention_saver_summary_tool,
    list_cancellation_risks_tool,
    retention_saver_overview_sentence,
)
from gumroad_merchant.settings import get_settings, openai_key_present
from gumroad_merchant.shortest_qa_tools import (
    generate_shortest_qa_tests as generate_shortest_qa_tests_tool,
    get_shortest_qa_summary as get_shortest_qa_summary_tool,
    list_shortest_qa_suites as list_shortest_qa_suites_tool,
    shortest_qa_overview_sentence,
)
from gumroad_merchant.tracked_campaigns import list_tracked_campaigns_tool

try:
    from agents import Agent, ModelSettings, RunConfig, Runner, function_tool
except Exception:  # pragma: no cover - optional dependency in static-only mode.
    Agent = None
    ModelSettings = None
    RunConfig = None
    Runner = None
    function_tool = None


logging.getLogger("agents").setLevel(logging.CRITICAL)
logging.getLogger("openai.agents").setLevel(logging.CRITICAL)


UNKNOWN_ACCESS_MESSAGE = (
    "I only know the seeded Gumroad Merchant analytics data and loaded Gumroad help docs in this demo. "
    "Ask about products, revenue, conversion, refunds, traffic sources, next moves, fees, payouts, "
    "Stripe/PayPal, chargebacks, refunds, taxes, or where to find those docs."
)

SYSTEM_PROMPT = """
You are Gumroad Merchant, a hooded cart-merchant guide embedded in Gumroad analytics.

You help creators understand seeded product analytics and decide the next action
or automation draft. You can inspect local SQLite analytics through scoped local tools: products,
views, sales, revenue, conversion, refunds, traffic sources, churn, UTM links, and
customer export summaries, detected next-move signals, and realistic growth plans.
You can also search a seeded local corpus of official Gumroad pricing/help docs for
creator money-ops questions: fees, payouts, payout timing, Stripe/PayPal processor
references, chargebacks, refund/payout impact, taxes/Merchant of Record notes, and
where to find those docs in Gumroad Help Center sections.

You are not a generic support bot. Your job is merchant strategy: monthly overview,
past-period diagnosis, realistic 3-month and 6-month sales goals, conversion
improvements, source-quality analysis, UTM attribution cleanup, refund/churn risk,
offer packaging, controlled experiments, Refund Ops triage,
    chargeback dispute evidence packs, Content Radar campaign planning, Retention
    Saver pause-offer estimates, Admin actions, and Shortest-style QA
test generation.

Rules:
- Use tools before making factual claims about product analytics.
- Use search_gumroad_help_docs before answering Gumroad policy/help-doc questions.
- Do not claim access to production Gumroad data. This demo uses seeded local data.
- Do not claim the help corpus is live. It is a seeded local official-doc corpus.
- Do not invent products, sales, conversion, traffic sources, refunds, or citations.
- Do not invent Gumroad policy. If an answer is not in the loaded Gumroad docs, say so.
- Do not apply edits, send emails, change prices, or mutate products unless the workflow has the required confirmation step.
- You may stage local agent_actions and apply them only when the user explicitly
  asks you to create/generate/build the artifact or confirms your offer to do it.
  Approved actions can create local tracked_campaigns rows, downloadable roadmap
  artifacts, or architecture diagram artifacts. They never post, email, spend,
  edit a Gumroad product, or call production Gumroad APIs.
- Refund Ops outputs are prepared replies, evidence packets, audit notes, and prevention actions with next execution steps.
- Campaign, trend, admin, membership, subscription, and QA lanes are seeded local workflows with explicit confirmation and audit requirements.
- Keep conversations short, but informative. Do not skip any details or data
  points that change the decision. Simple greetings can be brief, but analytical
  answers should include the relevant metrics, interpretation, evidence, and
  next step.
- Format answers for scanning: use short paragraphs separated by blank lines,
  or up to 5 bullets when a list is clearer. Keep each paragraph to 1-3
  sentences. Lead with the direct answer, then add evidence and next action.
- For analytical answers, include four parts when applicable: what the signal
  says, why it matters, the evidence behind it, and the next action.
- For daily Merchant Op runs, keep the model layer focused: tools compute metrics,
  you summarize the merchant brief, recommend actions, and stage local automations
  when the user asks or confirms.
- Do not dump raw analytics tables. Carry forward only numbers that change the
  decision.
- Cite concrete evidence in natural language: product name, date range, metric,
  traffic source, signal, or action label.
- For Gumroad policy/help answers, include the source URL inline in the answer.
- Prefer realistic goals over hype: anchor goals to current revenue, average order
  value, conversion rate, traffic quality, refunds, and churn.
- Treat customer export rows as synthetic samples only. Never use sample customer
  rows as portfolio revenue, sales, refund, conversion, or AOV totals; use
  product metrics for those totals.
- Any field ending in `_cents` is cents, not dollars. When a tool returns a
  nested `formatted` money value, use that formatted value in the answer.
- If the loaded data cannot answer the question, say that plainly.
""".strip()


@dataclass(frozen=True)
class AgentChatResult:
    answer: str
    citations: list[dict[str, Any]]
    model: str
    fallback: bool = False
    error: str | None = None


def configured_model() -> str:
    return get_settings().openai_agent_model


def run_config() -> Any:
    if RunConfig is None:
        return None
    return RunConfig(
        workflow_name="Gumroad Merchant Analytics Chat",
        tracing_disabled=not get_settings().openai_agent_tracing,
    )


def citation(type_: str, id_: int | str | None, label: str, excerpt: str | None = None) -> dict[str, Any]:
    return {"type": type_, "id": id_, "label": label, "excerpt": excerpt}


def product_citation(metrics: dict[str, Any]) -> dict[str, Any]:
    product = metrics["product"]
    current = metrics["current"]
    derived = metrics["derived"]
    excerpt = (
        f"{current['sales']:,} sales, {format_currency(current['revenue_cents'], product['currency'])}, "
        f"{format_percent(derived['current_conversion'])} conversion."
    )
    return citation("product", product["id"], product["name"], excerpt)


def signal_citations(signals: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return [
        citation("signal", signal["id"], signal["title"], f"{signal['label']} - {signal['confidence']} confidence")
        for signal in signals[:limit]
    ]


def refund_case_citations(cases: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return [
        citation(
            "refund_case",
            case["case_id"],
            f"{case['label']} - {case['status'].replace('_', ' ')}",
            f"{format_currency(case['amount_cents'])} under review, risk {case['risk_score']}/100",
        )
        for case in cases[:limit]
    ]


def content_trend_citations(trends: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return [
        citation(
            "content_trend",
            trend["id"],
            trend["title"],
            f"{trend['channel']} campaign, {trend['expected_kpi']['target_formatted']} target KPI",
        )
        for trend in trends[:limit]
    ]


def tracked_campaign_citation(campaign: dict[str, Any]) -> dict[str, Any]:
    return citation(
        "tracked_campaign",
        campaign["id"],
        campaign["campaign"],
        f"{campaign['source']} / {campaign['medium']} saved as {campaign['status']} with 7-day attribution.",
    )


def retention_citation(summary: dict[str, Any]) -> dict[str, Any]:
    churn = summary["membership_churn"]
    estimate = summary["pause_revenue_estimate"]
    return citation(
        "retention",
        "retention-saver",
        "Retention Saver summary",
        f"{churn['canceled']:,} cancellations; {estimate['estimated_revenue_saved']['formatted']} estimated saved.",
    )


def admin_action_citations(actions: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return [
        citation(
            "admin_action",
            action["action_id"],
            action.get("title", action["action_id"]),
            f"{action.get('risk_level', 'unknown')} risk; command workflow ready.",
        )
        for action in actions[:limit]
    ]


def qa_test_citations(tests: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return [
        citation(
            "qa_test",
            test["id"],
            test["title"],
            f"{test['suite_id']} - {test['priority']} priority",
        )
        for test in tests[:limit]
    ]


def source_citations(sources: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return [
        citation(
            "source",
            source["name"],
            source["name"],
            f"{source['sales']:,} sales, {format_percent(source['conversion'])} conversion",
        )
        for source in sources[:limit]
    ]


def help_doc_citations(chunks: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    return [
        citation(
            "help_doc",
            chunk["chunk_id"],
            f"{chunk['title']} - {chunk['section_heading']}",
            chunk["source_url"],
        )
        for chunk in chunks[:limit]
    ]


def build_agent(db_path: Path | str) -> Any:
    if Agent is None or function_tool is None:
        raise RuntimeError("OpenAI Agents SDK is not installed.")

    def call_tool(tool_name: str, fields: dict[str, Any], func, *args, **kwargs):
        with trace_span(f"tool.{tool_name}", tool=tool_name, args=fields):
            result = func(*args, **kwargs)
        trace_event("tool.result", tool=tool_name, result=payload_summary(result))
        return result

    @function_tool
    def get_database_inventory() -> dict[str, Any]:
        """Return the seeded local analytics inventory available to Gumroad Merchant."""
        return call_tool("get_database_inventory", {}, get_database_inventory_tool, db_path)

    @function_tool
    def get_product_metrics(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Return product or portfolio metrics for the selected date range."""
        return call_tool(
            "get_product_metrics",
            {"product_id": product_id, "date_range": date_range},
            get_product_metrics_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def get_traffic_sources(product_id: str = "all", date_range: str = "30", limit: int = 6) -> list[dict[str, Any]]:
        """Return top current traffic sources for a product or portfolio."""
        return call_tool(
            "get_traffic_sources",
            {"product_id": product_id, "date_range": date_range, "limit": limit},
            get_traffic_sources_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            limit=limit,
        )

    @function_tool
    def get_detected_signals(product_id: str = "all", date_range: str = "30") -> list[dict[str, Any]]:
        """Return deterministic next-move signals from the selected analytics."""
        return call_tool(
            "get_detected_signals",
            {"product_id": product_id, "date_range": date_range},
            get_detected_signals_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def get_dashboard_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Return churn, top locations, UTM links, customer export summary, and correlation insights."""
        return call_tool(
            "get_dashboard_summary",
            {"product_id": product_id, "date_range": date_range},
            get_dashboard_summary_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def build_strategy_plan(product_id: str = "all", date_range: str = "30", horizon_months: int = 3) -> dict[str, Any]:
        """Return a realistic 3- or 6-month merchant strategy plan grounded in the SQLite analytics."""
        return call_tool(
            "build_strategy_plan",
            {"product_id": product_id, "date_range": date_range, "horizon_months": horizon_months},
            build_strategy_plan_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            horizon_months=horizon_months,
        )

    @function_tool
    def get_action_review(signal_id: str, product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Return the action payload for one detected signal."""
        return call_tool(
            "get_action_review",
            {"signal_id": signal_id, "product_id": product_id, "date_range": date_range},
            get_action_review_tool,
            db_path,
            signal_id=signal_id,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def get_refund_ops_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Return Refund Ops summary metrics, review queue counts, dispute exposure, and prevention estimate."""
        return call_tool(
            "get_refund_ops_summary",
            {"product_id": product_id, "date_range": date_range},
            get_refund_ops_summary_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def list_refund_cases(product_id: str = "all", date_range: str = "30", mode: str = "all", limit: int = 10) -> list[dict[str, Any]]:
        """Return seeded refund request and chargeback dispute cases for review."""
        return call_tool(
            "list_refund_cases",
            {"product_id": product_id, "date_range": date_range, "mode": mode, "limit": limit},
            list_refund_cases_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            mode=mode,
            limit=limit,
        )

    @function_tool
    def get_refund_case(case_id: str) -> dict[str, Any]:
        """Return one seeded Refund Ops case, including evidence, timeline, and audit events."""
        return call_tool("get_refund_case", {"case_id": case_id}, get_refund_case_tool, db_path, case_id=case_id)

    @function_tool
    def build_dispute_evidence_pack(case_id: str) -> dict[str, Any]:
        """Return a chargeback dispute evidence packet for a Refund Ops case."""
        return call_tool(
            "build_dispute_evidence_pack",
            {"case_id": case_id},
            build_dispute_evidence_pack_tool,
            db_path,
            case_id=case_id,
        )

    @function_tool
    def draft_refund_reply(case_id: str) -> dict[str, Any]:
        """Return a prepared buyer reply for a refund request."""
        return call_tool("draft_refund_reply", {"case_id": case_id}, draft_refund_reply_tool, db_path, case_id=case_id)

    @function_tool
    def get_refund_prevention_actions(product_id: str = "all", date_range: str = "30") -> list[dict[str, Any]]:
        """Return actions that can reduce future refunds."""
        return call_tool(
            "get_refund_prevention_actions",
            {"product_id": product_id, "date_range": date_range},
            get_refund_prevention_actions_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def get_content_radar_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Return seeded Content Radar summary metrics and top marketing opportunities."""
        return call_tool(
            "get_content_radar_summary",
            {"product_id": product_id, "date_range": date_range},
            get_content_radar_summary_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def list_content_trends(product_id: str = "all", date_range: str = "30", limit: int = 6) -> list[dict[str, Any]]:
        """Return seeded content trend angles with channel, UTM campaign, KPI, risks, and evidence."""
        return call_tool(
            "list_content_trends",
            {"product_id": product_id, "date_range": date_range, "limit": limit},
            list_content_trends_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            limit=limit,
        )

    @function_tool
    def build_marketing_plan(product_id: str = "all", date_range: str = "30", horizon_weeks: int = 4) -> dict[str, Any]:
        """Return a Content Radar marketing plan grounded in seeded trend data."""
        return call_tool(
            "build_marketing_plan",
            {"product_id": product_id, "date_range": date_range, "horizon_weeks": horizon_weeks},
            build_marketing_plan_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            horizon_weeks=horizon_weeks,
        )

    @function_tool
    def draft_campaign_assets(product_id: str = "all", date_range: str = "30", trend_id: str | None = None, channel: str | None = None) -> dict[str, Any]:
        """Return campaign drafts for a seeded trend."""
        return call_tool(
            "draft_campaign_assets",
            {"product_id": product_id, "date_range": date_range, "trend_id": trend_id, "channel": channel},
            draft_campaign_assets_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            trend_id=trend_id,
            channel=channel,
        )

    @function_tool
    def create_tracked_campaign(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Apply an approved local tracked-campaign action and return the generated UTM tracking URL."""
        return call_tool(
            "create_tracked_campaign",
            {"product_id": product_id, "date_range": date_range},
            create_tracked_campaign_action_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def stage_tracked_campaign(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Stage a pending local tracked-campaign action for user approval."""
        return call_tool(
            "stage_tracked_campaign",
            {"product_id": product_id, "date_range": date_range},
            stage_tracked_campaign_action_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def list_tracked_campaigns(product_id: str = "all", limit: int = 20) -> list[dict[str, Any]]:
        """List local tracked campaign draft rows created in this demo."""
        return call_tool(
            "list_tracked_campaigns",
            {"product_id": product_id, "limit": limit},
            list_tracked_campaigns_tool,
            db_path,
            product_id=product_id,
            limit=limit,
        )

    @function_tool
    def list_agent_actions(action_type: str = "all", status: str = "all", product_id: str = "all", limit: int = 20) -> list[dict[str, Any]]:
        """List local pending/applied agent actions and audit-ready payloads."""
        return call_tool(
            "list_agent_actions",
            {"action_type": action_type, "status": status, "product_id": product_id, "limit": limit},
            list_agent_actions_tool,
            db_path,
            action_type=action_type,
            status=status,
            product_id=product_id,
            limit=limit,
        )

    @function_tool
    def generate_roadmap_artifact(product_id: str = "all", date_range: str = "30", horizon_days: int = 30) -> dict[str, Any]:
        """Generate an approved downloadable local 30-day or 60-day roadmap artifact."""
        return call_tool(
            "generate_roadmap_artifact",
            {"product_id": product_id, "date_range": date_range, "horizon_days": horizon_days},
            create_roadmap_action_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            horizon_days=horizon_days,
        )

    @function_tool
    def generate_architecture_diagram(diagram_type: str = "agent-action-system") -> dict[str, Any]:
        """Generate an approved downloadable local architecture diagram artifact."""
        return call_tool(
            "generate_architecture_diagram",
            {"diagram_type": diagram_type},
            create_architecture_diagram_action_tool,
            db_path,
            diagram_type=diagram_type,
        )

    @function_tool
    def get_retention_saver_summary(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Return membership churn and pause-offer savings estimates tied to Gumroad issue #4884."""
        return call_tool(
            "get_retention_saver_summary",
            {"product_id": product_id, "date_range": date_range},
            get_retention_saver_summary_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def list_cancellation_risks(product_id: str = "all", date_range: str = "30", limit: int = 10) -> list[dict[str, Any]]:
        """Return seeded cancellation risk rows for reviewing membership pause offers."""
        return call_tool(
            "list_cancellation_risks",
            {"product_id": product_id, "date_range": date_range, "limit": limit},
            list_cancellation_risks_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            limit=limit,
        )

    @function_tool
    def build_pause_offer_plan(product_id: str = "all", date_range: str = "30") -> dict[str, Any]:
        """Return a 1-month/3-month membership pause plan."""
        return call_tool(
            "build_pause_offer_plan",
            {"product_id": product_id, "date_range": date_range},
            build_pause_offer_plan_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
        )

    @function_tool
    def estimate_pause_revenue_saved(product_id: str = "all", date_range: str = "30", save_rate: str | None = None) -> dict[str, Any]:
        """Return the modeled revenue saved from pause offers using seeded churn data."""
        return call_tool(
            "estimate_pause_revenue_saved",
            {"product_id": product_id, "date_range": date_range, "save_rate": save_rate},
            estimate_pause_revenue_saved_tool,
            db_path,
            product_id=product_id,
            date_range=date_range,
            save_rate=save_rate,
        )

    @function_tool
    def get_admin_action_preview_summary(product_id: str = "all", limit: int = 6) -> dict[str, Any]:
        """Return admin action templates and Refund Ops case suggestions."""
        return call_tool(
            "get_admin_action_preview_summary",
            {"product_id": product_id, "limit": limit},
            get_admin_action_preview_summary_tool,
            db_path,
            product_id=product_id,
            limit=limit,
        )

    @function_tool
    def list_admin_action_templates() -> list[dict[str, Any]]:
        """Return admin action templates."""
        return call_tool("list_admin_action_templates", {}, list_admin_action_templates_tool)

    @function_tool
    def preview_admin_action(action_id: str = "purchase_lookup", purchase_id: str | None = None, case_id: str | None = None, product_id: str | None = None, reason: str | None = None, note: str | None = None) -> dict[str, Any]:
        """Return a full admin action workflow with intent text, preflight checks, and required inputs."""
        return call_tool(
            "preview_admin_action",
            {"action_id": action_id, "purchase_id": purchase_id, "case_id": case_id, "product_id": product_id},
            preview_admin_action_tool,
            db_path,
            action_id=action_id,
            purchase_id=purchase_id,
            case_id=case_id,
            product_id=product_id,
            reason=reason,
            note=note,
        )

    @function_tool
    def build_cli_command_preview(action_id: str = "purchase_lookup") -> dict[str, Any]:
        """Render one simulated CLI command string without executing it."""
        return call_tool("build_cli_command_preview", {"action_id": action_id}, build_cli_command_preview_tool, action_id)

    @function_tool
    def get_shortest_qa_summary() -> dict[str, Any]:
        """Return local Shortest QA suite coverage for Gumroad Merchant."""
        return call_tool("get_shortest_qa_summary", {}, get_shortest_qa_summary_tool)

    @function_tool
    def list_shortest_qa_suites() -> list[dict[str, Any]]:
        """Return Shortest QA suite metadata."""
        return call_tool("list_shortest_qa_suites", {}, list_shortest_qa_suites_tool)

    @function_tool
    def generate_shortest_qa_tests(suite_id: str = "all", target_surface: str = "all", priority: str = "all", limit: int | None = None) -> dict[str, Any]:
        """Return deterministic natural-language QA journeys for the agent lanes."""
        return call_tool(
            "generate_shortest_qa_tests",
            {"suite_id": suite_id, "target_surface": target_surface, "priority": priority, "limit": limit},
            generate_shortest_qa_tests_tool,
            suite_id=suite_id,
            target_surface=target_surface,
            priority=priority,
            limit=limit,
        )

    @function_tool
    def search_products(query: str = "", limit: int = 5) -> list[dict[str, Any]]:
        """Search seeded demo products by name, creator, category, or tag."""
        return call_tool("search_products", {"query": query, "limit": limit}, search_products_tool, db_path, query=query, limit=limit)

    @function_tool
    def search_gumroad_help_docs(query: str, category: str = "money_ops", limit: int = 5) -> list[dict[str, Any]]:
        """Search seeded official Gumroad help/pricing docs through read-only SQLite FTS."""
        return call_tool(
            "search_gumroad_help_docs",
            {"query": query, "category": category, "limit": limit},
            search_gumroad_help_docs_tool,
            db_path,
            query=query,
            category=category,
            limit=limit,
        )

    @function_tool
    def get_help_doc_inventory() -> dict[str, Any]:
        """Return the seeded Gumroad help/pricing docs available to Gumroad Merchant."""
        return call_tool("get_help_doc_inventory", {}, get_help_doc_inventory_tool, db_path)

    return Agent(
        name="Gumroad Merchant",
        instructions=SYSTEM_PROMPT,
        model=configured_model(),
        model_settings=ModelSettings(verbosity=get_settings().openai_agent_verbosity) if ModelSettings is not None else None,
        tools=[
            get_database_inventory,
            get_product_metrics,
            get_traffic_sources,
            get_detected_signals,
            get_dashboard_summary,
            build_strategy_plan,
            get_action_review,
            get_refund_ops_summary,
            list_refund_cases,
            get_refund_case,
            build_dispute_evidence_pack,
            draft_refund_reply,
            get_refund_prevention_actions,
            get_content_radar_summary,
            list_content_trends,
            build_marketing_plan,
            draft_campaign_assets,
            stage_tracked_campaign,
            create_tracked_campaign,
            list_tracked_campaigns,
            list_agent_actions,
            generate_roadmap_artifact,
            generate_architecture_diagram,
            get_retention_saver_summary,
            list_cancellation_risks,
            build_pause_offer_plan,
            estimate_pause_revenue_saved,
            get_admin_action_preview_summary,
            list_admin_action_templates,
            preview_admin_action,
            get_shortest_qa_summary,
            list_shortest_qa_suites,
            generate_shortest_qa_tests,
            search_products,
            search_gumroad_help_docs,
            get_help_doc_inventory,
        ],
    )


def build_agent_input(
    message: str,
    product_id: str,
    date_range: str,
    conversation_history: list[dict[str, str]] | None = None,
) -> str:
    history_lines = []
    for item in (conversation_history or [])[-4:]:
        role = str(item.get("role", "")).strip().lower()
        content = " ".join(str(item.get("content", "")).split())
        if len(content) > 500:
            content = content[:497].rstrip() + "..."
        if role in {"user", "assistant"} and content:
            history_lines.append(f"{role}: {content}")
    history = "Recent conversation:\n" + "\n".join(history_lines) if history_lines else ""
    return "\n\n".join(
        part
        for part in [
            f"Selected product id: {product_id or 'all'}",
            f"Selected date range: {date_range or '30'}",
            history,
            f"User question: {message.strip()}",
            (
                "Answer as Gumroad Merchant. Use only the tools needed for factual claims: analytics tools "
                "for metrics, search_gumroad_help_docs for help/policy facts. Keep conversations short, "
                "but informative. Do not skip any details or data points that change the decision. Include the signal, "
                "why it matters, the deciding evidence, and the next action or automation draft when applicable. "
                "Do not dump raw rows or restate the whole table."
            ),
        ]
        if part
    )


def is_greeting(message: str) -> bool:
    normalized = re.sub(r"[^a-z0-9 ]+", " ", message.lower()).strip()
    return normalized in {"hi", "hello", "hey", "yo", "sup", "who are you", "what are you"}


def asks_inventory(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("what data", "data loaded", "inventory", "what do you know", "database", "what docs"))


def asks_help_docs(message: str) -> bool:
    lowered = message.lower()
    terms = (
        "fee",
        "fees",
        "pricing",
        "payout",
        "paid",
        "payment processor",
        "processor",
        "stripe",
        "paypal",
        "chargeback",
        "chargebacks",
        "dispute",
        "disputes",
        "refund policy",
        "refunds affect",
        "negative balance",
        "sales tax",
        "taxes",
        "merchant of record",
        "where do i find",
        "where can i find",
        "where is",
        "help docs",
        "help center",
        "payout dashboard",
        "balance page",
        "export payout",
        "export balance",
    )
    return any(term in lowered for term in terms)


def asks_unknown_help_policy(message: str) -> bool:
    lowered = message.lower()
    unsupported_terms = (
        "crypto",
        "cryptocurrency",
        "bitcoin",
        "ethereum",
        "token-gated",
        "token gated",
        "business license",
        "create my llc",
        "form an llc",
    )
    return asks_help_docs(message) and any(term in lowered for term in unsupported_terms)


def asks_mixed_help_analytics(message: str) -> bool:
    lowered = message.lower()
    ownership_terms = ("my ", "our ", "this product", "selected product", "all products", "portfolio", "analytics say", "metrics show")
    analytics_terms = (
        "product",
        "products",
        "sales",
        "revenue",
        "conversion",
        "traffic",
        "source",
        "refund",
        "refunds",
        "churn",
        "goal",
        "strategy",
        "analytics",
        "metrics",
    )
    return asks_help_docs(message) and any(term in lowered for term in ownership_terms) and any(
        term in lowered for term in analytics_terms
    )


def asks_sources(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("source", "traffic", "referrer", "utm", "channel"))


def asks_utm_attribution(message: str) -> bool:
    lowered = message.lower()
    if "content radar" in lowered:
        return False
    utm_terms = ("utm links", "utm link", "attribution cleanup", "attribution", "tracked campaign", "tracked campaigns")
    evidence_terms = ("campaign rows", "clicks", "sales", "conversion", "revenue", "deserves another test", "cleanup")
    return any(term in lowered for term in utm_terms) and any(term in lowered for term in evidence_terms)


def asks_monthly_overview(message: str) -> bool:
    lowered = message.lower()
    overview_terms = ("overview", "monthly read", "monthly summary", "source-of-truth", "source of truth")
    planning_terms = ("goal", "plan", "three month", "3 month", "six month", "6 month", "next 3", "next 6")
    return any(term in lowered for term in overview_terms) and not any(term in lowered for term in planning_terms)


def asks_dashboard_signal(message: str) -> bool:
    """Detect prompts staged by dashboard signal clicks.

    This is a fallback-only classifier. When the live agent is available,
    dashboard and feature prompts should still reach the model so follow-up
    evaluation does not feel like a static template.
    """
    lowered = message.lower()
    staged_markers = (
        "current value:",
        "ask merchant",
        "staged",
        "analyze the current data shown here",
        "use these current data points",
        "use these current recommendation rows",
        "use these current refund ops data points",
        "use these current trend data points",
        "use these current pause and churn data points",
        "use these current action data points",
        "use these current qa data points",
        "use the current source sort",
        "use the current geography scope",
        "use these buyer-location rows",
        "use these utm rows",
        "pull the churn panel data into the answer",
        "chart signal",
        "utm campaign signal",
        "location signal",
        "churn signal",
        "cross-signal",
    )
    return any(term in lowered for term in staged_markers)


def asks_refunds(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("refund", "refunds", "chargeback", "dispute"))


def asks_content_radar(message: str) -> bool:
    lowered = message.lower()
    return any(
        term in lowered
        for term in (
            "content radar",
            "content angle",
            "content angles",
            "trend",
            "trending",
            "marketing plan",
            "campaign",
            "post idea",
            "post ideas",
            "utm campaign",
            "draft campaign",
        )
    )


def recent_campaign_offer(conversation_history: list[dict[str, str]] | None) -> bool:
    for item in reversed((conversation_history or [])[-6:]):
        content = str(item.get("content", "")).lower()
        if "tracked campaign" in content and any(term in content for term in ("create", "generate", "tracking url", "tracking link")):
            return True
        if "utm" in content and "tracking" in content and any(term in content for term in ("create", "generate")):
            return True
    return False


def is_confirmation(message: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", message.lower()).strip()
    return normalized in {"yes", "yep", "yeah", "ok", "okay", "do it", "create it", "generate it", "go ahead", "boom okay", "boom ok"}


def asks_create_tracked_campaign(message: str, conversation_history: list[dict[str, str]] | None = None) -> bool:
    lowered = message.lower().strip()
    normalized = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
    campaign_terms = ("tracked campaign", "campaign link", "tracking link", "tracking url", "utm link", "utm campaign")
    create_terms = ("create", "generate", "build", "make", "save", "add")
    analysis_terms = (
        "whether to",
        "whether i",
        "whether we",
        "should i",
        "should we",
        "worth creating",
        "worth testing",
        "decide if",
        "recommend whether",
    )
    explicit = (
        not any(term in lowered for term in analysis_terms)
        and any(term in lowered for term in campaign_terms)
        and any(term in lowered for term in create_terms)
    )
    confirmation = normalized in {"yes", "yep", "yeah", "ok", "okay", "do it", "create it", "generate it", "go ahead", "boom okay", "boom ok"}
    return explicit or (confirmation and recent_campaign_offer(conversation_history))


def recent_roadmap_offer(conversation_history: list[dict[str, str]] | None) -> bool:
    for item in reversed((conversation_history or [])[-6:]):
        content = str(item.get("content", "")).lower()
        if "roadmap" in content and any(term in content for term in ("download", "generate", "create")):
            return True
    return False


def asks_roadmap_artifact(message: str, conversation_history: list[dict[str, str]] | None = None) -> bool:
    lowered = message.lower()
    explicit = "roadmap" in lowered and any(term in lowered for term in ("download", "generate", "create", "make", "artifact", "html", "pdf", "30-day", "60-day"))
    return explicit or (is_confirmation(message) and recent_roadmap_offer(conversation_history))


def requested_roadmap_days(message: str) -> int:
    lowered = message.lower()
    return 60 if "60" in lowered or "sixty" in lowered else 30


def asks_architecture_diagram_artifact(message: str) -> bool:
    lowered = message.lower()
    return ("architecture diagram" in lowered or "architectural diagram" in lowered) and any(
        term in lowered for term in ("generate", "create", "make", "download", "tool", "artifact", "diagram")
    )


def asks_retention_saver(message: str) -> bool:
    lowered = message.lower()
    return any(
        term in lowered
        for term in (
            "retention saver",
            "pause membership",
            "pause memberships",
            "pause offer",
            "pause before cancel",
            "membership pause",
            "reduce cancellations",
            "save churn",
            "revenue saved",
            "subscription pause",
        )
    )


def asks_admin_preview(message: str) -> bool:
    lowered = message.lower()
    return any(
        term in lowered
        for term in (
            "admin action",
            "admin cli",
            "cli action",
            "command preview",
            "gumroad admin",
            "preview command",
            "admin action",
            "read action",
            "write action",
        )
    )


def asks_shortest_qa(message: str) -> bool:
    lowered = message.lower()
    return any(
        term in lowered
        for term in (
            "shortest",
            "qa generator",
            "qa tests",
            "qa test",
            "test journey",
            "natural-language qa",
            "natural language qa",
            "generate tests",
            "smoke tests",
        )
    )


def asks_refund_ops(message: str) -> bool:
    lowered = message.lower()
    refund_terms = ("refund", "refunds", "chargeback", "dispute")
    workflow_terms = (
        "review",
        "case",
        "cases",
        "packet",
        "evidence",
        "reply",
        "audit",
        "ops",
        "build",
        "copy",
    )
    return any(term in lowered for term in refund_terms) and any(term in lowered for term in workflow_terms)


def asks_dispute_pack(message: str) -> bool:
    lowered = message.lower()
    dispute_terms = ("dispute", "chargeback")
    packet_terms = ("packet", "evidence", "build", "compile", "fight", "respond to")
    return any(term in lowered for term in dispute_terms) and any(term in lowered for term in packet_terms)


def asks_refund_prevention(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("reduce", "prevent", "lower", "avoid"))


def asks_refund_reply(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("reply", "buyer response", "buyer email", "draft response", "respond"))


def asks_refund_audit_note(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("audit", "admin note", "admin comment", "record this"))


def asks_refund_case_queue(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in ("queue", "case", "cases", "triage", "highest risk", "review request"))


def asks_active_refund_ops_action(message: str) -> bool:
    return (
        asks_dispute_pack(message)
        or asks_refund_reply(message)
        or asks_refund_audit_note(message)
        or asks_refund_case_queue(message)
        or asks_refund_prevention(message)
    )


def asks_strategy(message: str) -> bool:
    lowered = message.lower()
    return any(
        term in lowered
        for term in (
            "strategy",
            "goal",
            "goals",
            "plan",
            "monthly overview",
            "overview",
            "three month",
            "3 month",
            "six month",
            "6 month",
            "next 3",
            "next 6",
            "grow",
            "growth",
            "marketing",
            "smart",
        )
    )


def requested_horizon(message: str) -> int:
    lowered = message.lower()
    return 6 if any(term in lowered for term in ("six", "6 month", "next 6", "six-month")) else 3


def fallback_greeting() -> AgentChatResult:
    model = configured_model()
    return AgentChatResult(
        answer=(
            "I am Gumroad Merchant, your hooded analytics guide for this seeded Gumroad dashboard.\n\n"
            "I can explain what the dashboard is showing, why a signal matters, and what the next move should be. "
            "When the local OpenAI agent is unavailable, I use deterministic SQLite fallback tools so the answer is still grounded in the same seeded data.\n\n"
            "Good things to ask:\n"
            "- Monthly and multi-month performance reads.\n"
            "- Why a source, refund, churn, UTM, or Content Radar signal matters.\n"
            "- Action-ready next moves such as tracked campaigns, roadmap downloads, and section explanations.\n\n"
            "I will not post, email, refund, spend, or edit Gumroad production data from this demo."
        ),
        citations=[],
        model=model,
        fallback=True,
    )


def fallback_inventory(db_path: Path | str) -> AgentChatResult:
    model = configured_model()
    inventory = get_database_inventory_tool(db_path)
    answer = (
        "Seeded local inventory:\n"
        f"- {inventory['product_count']} products.\n"
        f"- {inventory['current_views']:,} current views, {inventory['current_sales']:,} current sales, and "
        f"{format_currency(inventory['current_revenue_cents'])} in current-period revenue.\n"
        f"- {inventory['traffic_source_rows']:,} traffic-source rows and {inventory['customer_sale_rows']:,} synthetic customer export rows.\n"
        f"- {inventory['help_doc_count']:,} official Gumroad help/pricing docs split into {inventory['help_chunk_count']:,} searchable FTS chunks.\n\n"
        "I query it through read-only SQLite tools."
    )
    return AgentChatResult(
        answer=answer,
        citations=[citation("summary", "inventory", "Seeded SQLite analytics", inventory["access"])],
        model=model,
        fallback=True,
    )


def fallback_sources(db_path: Path | str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    sources = get_traffic_sources_tool(db_path, product_id=product_id, date_range=date_range, limit=4)
    product = metrics["product"]
    if not sources:
        return AgentChatResult(UNKNOWN_ACCESS_MESSAGE, [], model=model, fallback=True)
    fragments = [
        f"{source['name']} has {source['sales']:,} sales at {format_percent(source['conversion'])} conversion"
        for source in sources[:3]
    ]
    top = sources[0]
    answer = (
        f"For {product['name']}, the strongest current traffic read is {top['name']} because it combines volume with "
        f"{format_percent(top['conversion'])} conversion and {format_currency(top['revenue_cents'], product['currency'])} in revenue.\n\n"
        "Current source evidence:\n"
        + "\n".join(f"- {fragment}" for fragment in fragments)
        + "\n\nHow I would interpret it: a source with higher-than-average conversion is usually telling you which buyer promise, audience, or distribution context is already resonating. "
        "The useful move is not to blindly spend more; it is to reuse that source's language in one controlled product-page or campaign test and keep attribution clean.\n\n"
        "Next action: create one tracked link for the winning source, run it for the selected period, and compare its conversion against the portfolio average."
    )
    return AgentChatResult(answer, [product_citation(metrics), *source_citations(sources)], model=model, fallback=True)


def fallback_utm_attribution(db_path: Path | str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    dashboard = load_dashboard_summary(db_path, product_id=product_id, date_range=date_range)
    product = metrics["product"]
    links = dashboard.get("top_utm_links") or dashboard.get("utm_links", [])
    if not links:
        return AgentChatResult("No UTM links are available for this selected scope.", [product_citation(metrics)], model=model, fallback=True)

    rows = []
    for link in links[:5]:
        rows.append(
            f"- {link['campaign']} ({link['source']}/{link['medium']}): "
            f"{link['clicks']:,} clicks, {link['sales']:,} sales, {format_percent(link['conversion'])} conversion, "
            f"{format_currency(link['revenue_cents'], product['currency'])} revenue."
        )
    best = max(links, key=lambda item: (item.get("conversion", 0), item.get("sales", 0), item.get("revenue_cents", 0)))
    answer = (
        f"For {product['name']}, UTM links should be read as attribution evidence, not broad demand proof.\n\n"
        "Current tracked campaign rows:\n"
        + "\n".join(rows)
        + "\n\n"
        f"The next campaign I would retest is {best['campaign']} because it has "
        f"{best['sales']:,} sales at {format_percent(best['conversion'])} conversion and "
        f"{format_currency(best['revenue_cents'], product['currency'])} revenue. "
        "Keep source/medium/campaign names stable so the next read is comparable instead of mixing direct, referral, and campaign traffic."
    )
    return AgentChatResult(
        answer,
        [
            product_citation(metrics),
            citation(
                "summary",
                "utm-links",
                "Tracked UTM links",
                f"{len(links)} tracked campaign rows loaded for the selected scope.",
            ),
            *signal_citations(detect_signals_for_metrics(metrics), limit=2),
        ],
        model=model,
        fallback=True,
    )


def fallback_monthly_overview(db_path: Path | str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    dashboard = load_dashboard_summary(db_path, product_id=product_id, date_range=date_range)
    signals = detect_signals_for_metrics(metrics)
    product = metrics["product"]
    current = metrics["current"]
    derived = metrics["derived"]
    top_source = metrics["current_sources"][0] if metrics["current_sources"] else None
    concern = (
        f"refund pressure at {format_percent(derived['current_refund_rate'])}"
        if derived["current_refund_rate"] >= 0.06
        else f"conversion at {format_percent(derived['current_conversion'])}"
    )
    answer = (
        f"For {product['name']}, current-period revenue is {format_currency(current['revenue_cents'], product['currency'])} "
        f"from {current['sales']:,} sales and {current['views']:,} views.\n\n"
        "Key read:\n"
        f"- Conversion: {format_percent(derived['current_conversion'])}.\n"
        f"- Refund rate: {format_percent(derived['current_refund_rate'])}.\n"
        f"- Churn: {format_percent(dashboard['churn']['rate'])}.\n\n"
        f"I would watch {concern} first because it is the clearest place where revenue can leak even when traffic or sales look healthy. "
        "The point is to separate demand from friction: traffic tells you buyers are arriving, conversion tells you whether the page is doing its job, and refunds/churn tell you whether the promise matched the delivered product."
    )
    if top_source:
        answer += (
            f"\n\nTop source: {top_source['name']} has "
            f"{top_source['sales']:,} sales at {format_percent(top_source['conversion'])} conversion. "
            "That makes it the first place I would look for language or audience clues before changing price, packaging, or promotion."
        )
    return AgentChatResult(
        answer,
        [product_citation(metrics), *source_citations(metrics["current_sources"][:1]), *signal_citations(signals, limit=2)],
        model=model,
        fallback=True,
    )


def fallback_refunds(db_path: Path | str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    cases = list_refund_cases_tool(db_path, product_id=product_id, date_range=date_range, mode="all", limit=5)
    summary = get_refund_ops_summary_tool(db_path, product_id=product_id, date_range=date_range)
    actions = get_refund_prevention_actions_tool(db_path, product_id=product_id, date_range=date_range)
    answer = (
        f"{refund_ops_overview_sentence(db_path, product_id=product_id, date_range=date_range)}\n\n"
        f"First prevention move: {actions[0]['title']}.\n"
        f"Recommended action: {actions[0]['recommended_action']}"
    )
    if cases:
        lead_case = cases[0]
        answer += (
            f"\n\nTop case: {lead_case['label'].lower()} {lead_case['case_id']} "
            f"with {lead_case['amount']['formatted']} under review.\n"
            "Recommended action: "
            f"{lead_case['recommended_action']}"
        )
    citations = [
        product_citation(metrics),
        citation(
            "summary",
            "refund-ops",
            "Refund Ops summary",
            f"{summary['cases_needing_review']} cases needing review; {summary['disputed_amount']['formatted']} disputed.",
        ),
        *refund_case_citations(cases),
    ]
    return AgentChatResult(answer, citations, model=model, fallback=True)


def fallback_refund_ops(db_path: Path | str, message: str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    cases = list_refund_cases_tool(db_path, product_id=product_id, date_range=date_range, mode="all", limit=5)
    if asks_dispute_pack(message):
        dispute_cases = list_refund_cases_tool(db_path, product_id=product_id, date_range=date_range, mode="dispute", limit=1)
        if dispute_cases:
            pack = build_dispute_evidence_pack_tool(db_path, dispute_cases[0]["case_id"])
            answer = (
                f"I found {dispute_cases[0]['case_id']} as the top chargeback dispute.\n\n"
                f"Status: {'ready' if pack['ready_for_action'] else 'needs one more check'} for merchant action.\n\n"
                f"Copy packet: {pack['copy_text']}\n\n"
                f"Audit note: {pack['audit_note']}"
            )
            return AgentChatResult(
                answer,
                [product_citation(metrics), *refund_case_citations(dispute_cases)],
                model=model,
                fallback=True,
            )
        return AgentChatResult(
            f"No chargeback dispute cases are open for this selection. {refund_ops_overview_sentence(db_path, product_id, date_range)}",
            [product_citation(metrics)],
            model=model,
            fallback=True,
        )
    if asks_refund_reply(message):
        review_cases = list_refund_cases_tool(db_path, product_id=product_id, date_range=date_range, mode="review", limit=1)
        if review_cases:
            draft = draft_refund_reply_tool(db_path, review_cases[0]["case_id"])
            answer = (
                f"Buyer reply for {review_cases[0]['case_id']} is ready.\n\n"
                f"Reply draft: {draft['copy_text']}\n\n"
                f"Recommended action: {draft['recommended_action']}\n\n"
                f"Audit note: {draft['audit_note']}"
            )
            return AgentChatResult(
                answer,
                [product_citation(metrics), *refund_case_citations(review_cases)],
                model=model,
                fallback=True,
            )
    if asks_refund_audit_note(message):
        if cases:
            case = cases[0]
            answer = (
                f"Audit note for {case['case_id']}:\n{case['audit_note']}\n\n"
                "This records the review packet only; no refund, dispute, email, or product edit is submitted."
            )
            return AgentChatResult(
                answer,
                [product_citation(metrics), *refund_case_citations([case])],
                model=model,
                fallback=True,
            )
    if asks_refund_case_queue(message):
        if cases:
            fragments = [
                f"{case['case_id']} ({case['label']}, {case['amount']['formatted']}, risk {case['risk_score']}/100)"
                for case in cases[:3]
            ]
            answer = (
                "Top Refund Ops cases:\n"
                + "\n".join(f"- {fragment}" for fragment in fragments)
                + "\n\nStart with the first case because it has the highest dispute/review urgency."
            )
            return AgentChatResult(
                answer,
                [product_citation(metrics), *refund_case_citations(cases[:3])],
                model=model,
                fallback=True,
            )
    if asks_refund_prevention(message):
        actions = get_refund_prevention_actions_tool(db_path, product_id=product_id, date_range=date_range)
        action_lines = "\n".join(f"- {action['title']}: {action['recommended_action']}" for action in actions[:3])
        answer = f"To reduce refunds:\n{action_lines}"
        return AgentChatResult(answer, [product_citation(metrics)], model=model, fallback=True)
    return fallback_refunds(db_path, product_id, date_range)


def fallback_content_radar(db_path: Path | str, message: str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    summary = get_content_radar_summary_tool(db_path, product_id=product_id, date_range=date_range)
    trends = list_content_trends_tool(db_path, product_id=product_id, date_range=date_range, limit=3)
    if "draft" in message.lower() or "copy" in message.lower():
        assets = draft_campaign_assets_tool(db_path, product_id=product_id, date_range=date_range)
        lead = assets["assets"][0] if assets.get("assets") else {}
        answer = (
            f"{content_radar_overview_sentence(db_path, product_id, date_range)}\n\n"
            f"Copyable {lead.get('asset_type', 'campaign')} draft:\n"
            f"{lead.get('draft_copy', assets.get('boundary', 'No draft available.'))}"
        )
    else:
        plan = build_marketing_plan_tool(db_path, product_id=product_id, date_range=date_range, horizon_weeks=4)
        lead = trends[0] if trends else {}
        first_step = plan["plan_steps"][0] if plan.get("plan_steps") else {}
        staged = stage_tracked_campaign_action_tool(db_path, product_id=product_id, date_range=date_range)
        action = staged["action"]
        preview = staged["preview"]
        action_note = (
            f"I already created this tracked campaign as action {action['id']}; tracking URL: {action['result'].get('tracking_url', preview['tracking_url'])}"
            if action["status"] == "applied"
            else f"I staged action {action['id']} for the local tracked campaign row. Say \"create it\" and I will apply it once and return the saved URL."
        )
        answer = (
            f"{content_radar_overview_sentence(db_path, product_id, date_range)}\n\n"
            f"Start with: {lead.get('title', 'the top content angle')} on {lead.get('channel', 'the best-fit channel')}.\n\n"
            f"Week 1 move: {first_step.get('move', 'publish one tracked content test')}.\n\n"
            f"Because this is tied to {preview['product_name']} and a measurable 7-day UTM read, it is worth isolating before widening promotion.\n\n"
            f"{action_note}\n\n"
            "Use the prepared plan to schedule the campaign, assign the owner, and set the measurement window."
        )
    return AgentChatResult(
        answer,
        [
            product_citation(metrics),
            citation("summary", "content-radar", "Content Radar summary", f"{summary['trend_count']} seeded trends available."),
            *content_trend_citations(trends),
        ],
        model=model,
        fallback=True,
    )


def fallback_create_tracked_campaign(db_path: Path | str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    applied = apply_latest_pending_action_tool(
        db_path,
        action_type=TRACKED_CAMPAIGN_ACTION,
        product_id=product_id,
        date_range=date_range,
    )
    if applied:
        campaign = applied["result"]
        already_applied = applied["already_applied"]
        action = applied["action"]
    else:
        created = create_tracked_campaign_action_tool(db_path, product_id=product_id, date_range=date_range)
        campaign = created["campaign"]
        already_applied = created["already_applied"]
        action = created["action"]
    metrics = get_product_metrics_tool(db_path, product_id=campaign["product_id"], date_range=date_range)
    verb = "Reused the existing applied action" if already_applied else "Created the local tracked campaign draft"
    answer = (
        f"{verb} for {campaign['product_name']}: {campaign['campaign']} (action {action['id']}). "
        f"Tracking URL: {campaign['tracking_url']}\n\n"
        f"Reason: {campaign['reason']}\n\n"
        "The row is now saved in Tracked campaigns with 7-day attribution; no post, email, spend, or product edit was made."
    )
    return AgentChatResult(
        answer,
        [
            product_citation(metrics),
            tracked_campaign_citation(campaign),
        ],
        model=model,
        fallback=True,
    )


def fallback_roadmap_artifact(db_path: Path | str, message: str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    horizon_days = requested_roadmap_days(message)
    created = create_roadmap_action_tool(db_path, product_id=product_id, date_range=date_range, horizon_days=horizon_days)
    artifact = created["artifact"]
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    answer = (
        f"Generated the {artifact['horizon_days']}-day roadmap download:\n{artifact['download_url']}\n\n"
        "Why this roadmap: it pulls from the current local analytics, detected signals, and Content Radar opportunities, so the plan is tied to measurable campaign reads instead of a generic checklist.\n\n"
        "No email was sent and no Gumroad production data was changed."
    )
    return AgentChatResult(
        answer,
        [
            product_citation(metrics),
            citation("action", created["action"]["id"], artifact["title"], artifact["download_url"]),
        ],
        model=model,
        fallback=True,
    )


def fallback_architecture_diagram_artifact(db_path: Path | str) -> AgentChatResult:
    model = configured_model()
    created = create_architecture_diagram_action_tool(db_path, diagram_type="agent-action-system")
    artifact = created["artifact"]
    answer = (
        f"Generated the architecture diagram artifact:\n{artifact['download_url']}\n\n"
        "What it shows: the live agent action path from chat suggestion to pending action, explicit confirmation, one-time local write, downloadable artifacts, and audit events.\n\n"
        "This is generated by the repo-local Python diagram tool, not by a Codex-only runtime skill."
    )
    return AgentChatResult(
        answer,
        [citation("action", created["action"]["id"], artifact["title"], artifact["download_url"])],
        model=model,
        fallback=True,
    )


def fallback_retention_saver(db_path: Path | str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    summary = get_retention_saver_summary_tool(db_path, product_id=product_id, date_range=date_range)
    plan = build_pause_offer_plan_tool(db_path, product_id=product_id, date_range=date_range)
    option = next(
        (item for item in plan["offer_options"] if item["id"] == plan["recommended_option_id"]),
        plan["offer_options"][0],
    )
    answer = (
        f"{retention_saver_overview_sentence(db_path, product_id, date_range)}\n\n"
        f"First pause option to review: {option['label']}.\n"
        f"Best for: {option['best_for']}.\n\n"
        f"Execution note: {plan['execution_notes'][0]}\n\n"
        "This is tied to Gumroad issue #4884 and prepares the next membership-pause workflow."
    )
    return AgentChatResult(
        answer,
        [product_citation(metrics), retention_citation(summary)],
        model=model,
        fallback=True,
    )


def fallback_admin_preview(db_path: Path | str, message: str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    summary = get_admin_action_preview_summary_tool(db_path, product_id=product_id, limit=4)
    action_id = "pause_membership" if "pause" in message.lower() else "purchase_lookup"
    if "refund" in message.lower() or "case" in message.lower():
        action_id = "refund_review"
    if "receipt" in message.lower():
        action_id = "resend_receipt"
    first_case = summary["refund_ops_case_suggestions"][0] if summary["refund_ops_case_suggestions"] else {}
    preview = preview_admin_action_tool(
        db_path,
        action_id=action_id,
        case_id=first_case.get("case_id"),
        purchase_id=first_case.get("purchase_id"),
        product_id=product_id if product_id != "all" else first_case.get("product_id"),
        reason=first_case.get("label"),
    )
    answer = (
        "Admin Actions is ready.\n\n"
        f"Suggested action: {preview['title']}.\n"
        f"Risk: {preview['risk_level']}.\n"
        f"Execution note: {preview.get('blocked_reason') or 'read action ready.'}\n\n"
        f"Audit note: {preview['audit_note']}"
    )
    return AgentChatResult(
        answer,
        [product_citation(metrics), *admin_action_citations([preview])],
        model=model,
        fallback=True,
    )


def fallback_shortest_qa(db_path: Path | str, message: str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    suite_id = "all"
    lowered = message.lower()
    if "refund" in lowered:
        suite_id = "refund_ops"
    elif "content" in lowered or "marketing" in lowered:
        suite_id = "content_radar"
    elif "retention" in lowered or "pause" in lowered or "churn" in lowered:
        suite_id = "retention_saver"
    elif "admin" in lowered or "cli" in lowered:
        suite_id = "admin_action_preview"
    tests = generate_shortest_qa_tests_tool(suite_id=suite_id, limit=4)
    first = tests["tests"][0] if tests["tests"] else {}
    answer = (
        f"{shortest_qa_overview_sentence()}\n\n"
        f"For this request I generated {tests['test_count']} scenario(s).\n\n"
        f"Start with: {first.get('title', 'the first generated scenario')}.\n"
        f"Risk covered: {', '.join(first.get('risk_covered', [])[:2])}.\n\n"
        "These are natural-language review journeys, not mutating browser automation."
    )
    return AgentChatResult(
        answer,
        [product_citation(metrics), *qa_test_citations(tests["tests"])],
        model=model,
        fallback=True,
    )


def source_lines(chunks: list[dict[str, Any]], limit: int = 3) -> str:
    lines = []
    for chunk in chunks[:limit]:
        lines.append(f"{chunk['title']} - {chunk['section_heading']}: {chunk['source_url']}")
    return "\n".join(lines)


def fallback_unknown_help_docs(message: str, chunks: list[dict[str, Any]] | None = None) -> AgentChatResult:
    model = configured_model()
    appendix = ""
    if chunks:
        appendix = "\n\nClosest loaded sources:\n" + source_lines(chunks, limit=2)
    return AgentChatResult(
        (
            "I do not know that from the loaded Gumroad docs. "
            "The local corpus only covers official Gumroad money-ops docs for fees, payouts, "
            "Stripe/PayPal processor references, chargebacks, refund/payout impact, taxes, "
            "Merchant of Record notes, and related Help Center navigation."
            f"{appendix}"
        ),
        help_doc_citations(chunks or [], limit=2),
        model=model,
        fallback=True,
    )


def fallback_help_docs(db_path: Path | str, message: str) -> AgentChatResult:
    model = configured_model()
    chunks = search_gumroad_help_docs_tool(db_path, query=message, category="money_ops", limit=4)
    if asks_unknown_help_policy(message):
        return fallback_unknown_help_docs(message, chunks)
    if not chunks:
        return fallback_unknown_help_docs(message)
    bullets = []
    for chunk in chunks[:3]:
        bullets.append(f"- {chunk['section_heading']}: {chunk['excerpt']}")
    answer = "From the loaded Gumroad docs:\n" + "\n".join(bullets)
    answer += "\n\nSources:\n" + source_lines(chunks, limit=3)
    return AgentChatResult(answer, help_doc_citations(chunks), model=model, fallback=True)


def fallback_mixed_help_analytics(db_path: Path | str, message: str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    chunks = search_gumroad_help_docs_tool(db_path, query=message, category="money_ops", limit=3)
    product = metrics["product"]
    current = metrics["current"]
    derived = metrics["derived"]
    analytics = (
        f"For {product['name']}, the seeded analytics show {current['refunds']:,} refunds, "
        f"{format_currency(current['refund_cents'], product['currency'])} refunded, and a "
        f"{format_percent(derived['current_refund_rate'])} refund rate for the selected period."
    )
    if chunks:
        docs = (
            f" The loaded Gumroad docs say refunds or chargebacks can affect payout balance, "
            f"and negative Gumroad balances may be recovered through the payment processor. "
            f"Operationally, I would clarify expectations before checkout and review the payout "
            f"dashboard/export if refunds keep rising."
        )
        answer = analytics + docs + "\n\nSources:\n" + source_lines(chunks, limit=3)
        citations = [product_citation(metrics), *help_doc_citations(chunks)]
    else:
        answer = analytics + "\n\nI do not know the policy side from the loaded Gumroad docs."
        citations = [product_citation(metrics)]
    return AgentChatResult(answer, citations, model=model, fallback=True)


def fallback_next_moves(db_path: Path | str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    signals = detect_signals_for_metrics(metrics)
    dashboard = load_dashboard_summary(db_path, product_id=product_id, date_range=date_range)
    product = metrics["product"]
    current = metrics["current"]
    derived = metrics["derived"]
    lead_signal = signals[0]
    def evidence_line(item: dict[str, Any]) -> str:
        comparison = f" ({item['comparison']})" if item.get("comparison") else ""
        return f"- {item['label']}: {item['value']}{comparison}"

    evidence_lines = "\n".join(
        evidence_line(item) for item in lead_signal.get("evidence", [])[:2]
    )
    answer = (
        f"For {product['name']}, current revenue is {format_currency(current['revenue_cents'], product['currency'])} "
        f"from {current['sales']:,} sales at {format_percent(derived['current_conversion'])} conversion.\n\n"
        f"My first next move: {lead_signal['title']}.\n\n"
        f"Why I am choosing it: {lead_signal['recommendation']} This is the best first move because it is tied to a visible signal instead of a vague optimization idea. "
        "If the signal improves, you learn what to scale; if it does not, you avoided changing too many variables at once.\n\n"
        f"Evidence:\n{evidence_lines}\n\n"
        f"Action: {lead_signal['action']['label']}. I can help turn that into a tracked campaign or local automation where the action type supports it."
    )
    if dashboard.get("churn", {}).get("canceled"):
        answer += (
            f"\n\nChurn is also readable: {dashboard['churn']['canceled']:,} canceled subscriptions in the seeded dashboard. "
            "Treat that as a retention pressure signal, not proof that this growth move caused churn."
        )
    return AgentChatResult(answer, [product_citation(metrics), *signal_citations(signals)], model=model, fallback=True)


def fallback_strategy(db_path: Path | str, message: str, product_id: str, date_range: str) -> AgentChatResult:
    model = configured_model()
    plan = build_strategy_plan_tool(
        db_path,
        product_id=product_id,
        date_range=date_range,
        horizon_months=requested_horizon(message),
    )
    product = plan["product"]
    baseline = plan["baseline"]
    target = plan["monthly_targets"][-1]
    first_moves = "\n".join(f"- {pillar['name']}: {pillar['move']}" for pillar in plan["pillars"][1:4])
    answer = (
        f"For {product['name']}, I would set the {plan['horizon_months']}-month goal at "
        f"{format_currency(target['revenue_cents'], product['currency'])}/month, up from "
        f"{format_currency(baseline['monthly_revenue_cents'], product['currency'])}/month now.\n\n"
        f"That means about {target['sales']:,} monthly sales, {target['views']:,} visits, and "
        f"{format_percent(target['target_conversion'])} conversion.\n\n"
        f"My plan:\n{first_moves}"
    )
    citations = [
        citation("summary", "strategy-plan", f"{plan['horizon_months']}-month strategy plan", plan["realistic_goal"]),
        citation(
            "summary",
            "baseline",
            "Current monthly baseline",
            f"{baseline['monthly_sales']:,} sales, {format_percent(baseline['conversion'])} conversion",
        ),
        *signal_citations(plan["signals"], limit=2),
    ]
    return AgentChatResult(answer, citations, model=model, fallback=True)


def fallback_chat(
    db_path: Path | str,
    message: str,
    product_id: str,
    date_range: str,
    error: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> AgentChatResult:
    if is_greeting(message):
        return fallback_greeting()
    if asks_inventory(message):
        return fallback_inventory(db_path)
    if asks_shortest_qa(message):
        result = fallback_shortest_qa(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_admin_preview(message):
        result = fallback_admin_preview(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_retention_saver(message):
        result = fallback_retention_saver(db_path, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_architecture_diagram_artifact(message):
        result = fallback_architecture_diagram_artifact(db_path)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_roadmap_artifact(message, conversation_history):
        result = fallback_roadmap_artifact(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_create_tracked_campaign(message, conversation_history):
        result = fallback_create_tracked_campaign(db_path, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_utm_attribution(message):
        result = fallback_utm_attribution(db_path, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_content_radar(message):
        result = fallback_content_radar(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_refund_ops(message) and asks_active_refund_ops_action(message):
        result = fallback_refund_ops(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_mixed_help_analytics(message):
        result = fallback_mixed_help_analytics(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_help_docs(message) and not asks_active_refund_ops_action(message):
        result = fallback_help_docs(db_path, message)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_refund_ops(message):
        result = fallback_refund_ops(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_help_docs(message):
        result = fallback_help_docs(db_path, message)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_monthly_overview(message):
        result = fallback_monthly_overview(db_path, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_strategy(message):
        result = fallback_strategy(db_path, message, product_id, date_range)
        return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))
    if asks_sources(message):
        return fallback_sources(db_path, product_id, date_range)
    if asks_refunds(message):
        return fallback_refunds(db_path, product_id, date_range)
    result = fallback_next_moves(db_path, product_id, date_range)
    return AgentChatResult(result.answer, result.citations, model=result.model, fallback=True, error=sanitize_error(error))


def sanitize_error(error: str | None) -> str | None:
    if not error:
        return None
    lowered = str(error).lower()
    if "api key redacted" in lowered and "authentication" in lowered:
        return "OpenAI authentication failed; API key redacted."
    if "invalid_api_key" in lowered or "incorrect api key" in lowered:
        return "OpenAI authentication failed; API key redacted."
    sanitized = re.sub(r"sk-[A-Za-z0-9_*\\-]+", "sk-REDACTED", str(error))
    sanitized = re.sub(r"api[_ -]?key[^,}]+", "api key redacted", sanitized, flags=re.IGNORECASE)
    return sanitized[:500]


def extract_citations(db_path: Path | str, product_id: str, date_range: str, question: str, answer: str) -> list[dict[str, Any]]:
    if asks_help_docs(question) and not asks_mixed_help_analytics(question):
        return help_doc_citations(search_gumroad_help_docs_tool(db_path, query=question, category="money_ops", limit=3), limit=3)
    metrics = get_product_metrics_tool(db_path, product_id=product_id, date_range=date_range)
    citations = [product_citation(metrics)]
    if asks_content_radar(question):
        citations.append(
            citation(
                "summary",
                "content-radar",
                "Content Radar summary",
                content_radar_overview_sentence(db_path, product_id=product_id, date_range=date_range),
            )
        )
        citations.extend(content_trend_citations(list_content_trends_tool(db_path, product_id=product_id, date_range=date_range, limit=3)))
    if asks_retention_saver(question):
        citations.append(retention_citation(get_retention_saver_summary_tool(db_path, product_id=product_id, date_range=date_range)))
    if asks_admin_preview(question):
        summary = get_admin_action_preview_summary_tool(db_path, product_id=product_id, limit=3)
        previews = [
            (suggestion.get("suggested_actions") or suggestion.get("suggested_previews"))[0]
            for suggestion in summary.get("refund_ops_case_suggestions", [])
            if suggestion.get("suggested_actions") or suggestion.get("suggested_previews")
        ]
        citations.extend(admin_action_citations(previews or [{"action_id": "purchase_lookup", "title": "Exact purchase lookup", "risk_level": "low"}]))
    if asks_shortest_qa(question):
        tests = generate_shortest_qa_tests_tool(limit=3)["tests"]
        citations.extend(qa_test_citations(tests))
    if asks_refund_ops(question):
        citations.append(
            citation(
                "summary",
                "refund-ops",
                "Refund Ops summary",
                refund_ops_overview_sentence(db_path, product_id=product_id, date_range=date_range),
            )
        )
        citations.extend(refund_case_citations(list_refund_cases_tool(db_path, product_id=product_id, date_range=date_range, limit=3)))
    if asks_sources(question):
        citations.extend(source_citations(get_traffic_sources_tool(db_path, product_id=product_id, date_range=date_range)))
    if asks_help_docs(question):
        citations.extend(help_doc_citations(search_gumroad_help_docs_tool(db_path, query=question, category="money_ops", limit=3)))
    citations.extend(signal_citations(detect_signals_for_metrics(metrics), limit=2))
    seen: set[tuple[str, str]] = set()
    deduped = []
    for item in citations:
        key = (str(item["type"]), str(item["id"]))
        if key not in seen:
            deduped.append(item)
            seen.add(key)
    return deduped[:5]


def run_agent_chat(
    db_path: Path | str,
    message: str,
    product_id: str = "all",
    date_range: str = "30",
    conversation_history: list[dict[str, str]] | None = None,
    use_fallback: bool | None = None,
) -> AgentChatResult:
    cleaned = message.strip()
    if not cleaned:
        raise ValueError("message cannot be empty")
    model = configured_model()
    trace_event(
        "agent.chat.start",
        model=model,
        product_id=product_id,
        date_range=date_range,
        message_chars=len(cleaned),
        history_items=len(conversation_history or []),
    )
    if is_greeting(cleaned):
        trace_event("agent.chat.short_circuit", reason="greeting")
        return fallback_greeting()
    if asks_inventory(cleaned):
        trace_event("agent.chat.short_circuit", reason="inventory")
        return fallback_inventory(db_path)
    if asks_unknown_help_policy(cleaned):
        trace_event("agent.chat.short_circuit", reason="unknown_help_policy")
        return fallback_help_docs(db_path, cleaned)
    if asks_architecture_diagram_artifact(cleaned):
        trace_event("agent.chat.short_circuit", reason="architecture_diagram")
        return fallback_architecture_diagram_artifact(db_path)
    if asks_roadmap_artifact(cleaned, conversation_history):
        trace_event("agent.chat.short_circuit", reason="roadmap_artifact")
        return fallback_roadmap_artifact(db_path, cleaned, product_id=product_id, date_range=date_range)
    if asks_create_tracked_campaign(cleaned, conversation_history):
        trace_event("agent.chat.short_circuit", reason="create_tracked_campaign")
        return fallback_create_tracked_campaign(db_path, product_id=product_id, date_range=date_range)
    should_fallback = use_fallback is True or Agent is None or Runner is None or not openai_key_present()
    if should_fallback:
        trace_event(
            "agent.chat.fallback",
            reason="forced_or_unavailable",
            use_fallback=use_fallback,
            agent_sdk_available=Agent is not None and Runner is not None,
            openai_key_present=openai_key_present(),
        )
        return fallback_chat(
            db_path,
            cleaned,
            product_id=product_id,
            date_range=date_range,
            conversation_history=conversation_history,
        )
    try:
        with trace_span("agent.build"):
            agent = build_agent(db_path)
        kwargs: dict[str, Any] = {"max_turns": get_settings().openai_agent_max_turns}
        config = run_config()
        if config is not None:
            kwargs["run_config"] = config
        agent_input = build_agent_input(cleaned, product_id=product_id, date_range=date_range, conversation_history=conversation_history)
        with trace_span("agent.runner.run_sync", model=model, max_turns=kwargs["max_turns"], input_chars=len(agent_input)):
            result = Runner.run_sync(
                agent,
                agent_input,
                **kwargs,
            )
        answer = str(getattr(result, "final_output", result)).strip()
        if not answer:
            raise RuntimeError("OpenAI Agents SDK returned an empty answer")
        trace_event("agent.chat.live_result", answer_words=len(answer.split()))
        return AgentChatResult(
            answer=answer,
            citations=extract_citations(db_path, product_id, date_range, cleaned, answer),
            model=model,
            fallback=False,
        )
    except Exception as exc:
        trace_event("agent.chat.live_error", error=sanitize_error(f"{type(exc).__name__}: {exc}"))
        return fallback_chat(
            db_path,
            cleaned,
            product_id=product_id,
            date_range=date_range,
            error=sanitize_error(f"{type(exc).__name__}: {exc}"),
            conversation_history=conversation_history,
        )
