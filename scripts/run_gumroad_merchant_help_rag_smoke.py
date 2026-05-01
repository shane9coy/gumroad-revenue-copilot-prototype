#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gumroad_merchant.agent_harness import run_agent_chat  # noqa: E402
from gumroad_merchant.database import refresh_database  # noqa: E402
from gumroad_merchant.help_tools import get_help_doc_inventory_tool, search_gumroad_help_docs_tool  # noqa: E402
from gumroad_merchant.settings import get_settings, openai_key_present  # noqa: E402


SMOKE_PROMPTS = [
    {
        "id": "analytics_monthly_overview",
        "kind": "analytics",
        "message": "Give me a source-of-truth monthly overview for all products. Keep it concise.",
    },
    {
        "id": "analytics_top_source",
        "kind": "analytics",
        "message": "Which traffic source is strongest right now and what should I do with it?",
    },
    {
        "id": "analytics_refund_risk",
        "kind": "analytics",
        "message": "Which product has the biggest refund or expectation risk?",
        "product_id": "prod-audio-pack",
    },
    {
        "id": "analytics_three_month_goal",
        "kind": "analytics",
        "message": "Set a realistic three-month sales goal and tell me how we get there.",
    },
    {
        "id": "analytics_mixed_refunds_payouts",
        "kind": "analytics_mixed",
        "message": "Our refunds are up in the analytics; how can that affect payout balance according to Gumroad docs?",
    },
    {
        "id": "docs_fees",
        "kind": "help_doc",
        "message": "What are Gumroad's fees for direct sales and Discover?",
    },
    {
        "id": "docs_payouts",
        "kind": "help_doc",
        "message": "When do I get paid and where is the payout dashboard?",
    },
    {
        "id": "docs_stripe_paypal",
        "kind": "help_doc",
        "message": "Do I need Stripe or PayPal, and where do those processor reviews matter?",
    },
    {
        "id": "docs_chargebacks",
        "kind": "help_doc",
        "message": "What happens with chargebacks, and how can I reduce them?",
    },
    {
        "id": "docs_where_find",
        "kind": "help_doc",
        "message": "Where do I find payout exports, balance activity, and sales analytics docs?",
    },
]

UNKNOWN_POLICY_PROMPT = "Does Gumroad support crypto payouts or token-gated Bitcoin settlement?"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def citation_types(turn: dict[str, Any]) -> set[str]:
    return {str(item.get("type")) for item in turn.get("citations", [])}


def has_source_link(answer: str) -> bool:
    return "https://gumroad.com" in answer


def run_transcript(use_live: bool) -> dict[str, Any]:
    settings = get_settings()
    snapshot = refresh_database(settings.db_path, force=True)
    history: list[dict[str, str]] = []
    turns: list[dict[str, Any]] = []
    for index, prompt in enumerate(SMOKE_PROMPTS, start=1):
        result = run_agent_chat(
            db_path=settings.db_path,
            message=prompt["message"],
            product_id=prompt.get("product_id", "all"),
            date_range=prompt.get("date_range", "30"),
            conversation_history=history,
            use_fallback=not use_live,
        )
        turn = {
            "turn": index,
            "id": prompt["id"],
            "kind": prompt["kind"],
            "product_id": prompt.get("product_id", "all"),
            "date_range": prompt.get("date_range", "30"),
            "sent_at": now_iso(),
            "user": prompt["message"],
            "assistant": result.answer,
            "citations": result.citations,
            "model": result.model,
            "fallback": result.fallback,
            "error": result.error,
        }
        turns.append(turn)
        history.append({"role": "user", "content": prompt["message"]})
        history.append({"role": "assistant", "content": result.answer})

    unknown = run_agent_chat(
        db_path=settings.db_path,
        message=UNKNOWN_POLICY_PROMPT,
        product_id="all",
        date_range="30",
        conversation_history=history,
        use_fallback=True,
    )
    inventory = get_help_doc_inventory_tool(settings.db_path)
    direct_docs_search = search_gumroad_help_docs_tool(settings.db_path, query="fees payouts chargebacks Stripe PayPal", limit=5)
    checks = build_checks(turns, unknown, inventory, direct_docs_search, use_live)
    return {
        "started_at": now_iso(),
        "mode": "live-openai" if use_live else "deterministic-sql-fallback",
        "openai_key_present": openai_key_present(),
        "context": {"product_id": "all", "date_range": "30"},
        "snapshot": snapshot.as_dict(),
        "help_doc_inventory": inventory,
        "checks": checks,
        "turns": turns,
        "assertion_turns": [
            {
                "id": "unknown_policy",
                "user": UNKNOWN_POLICY_PROMPT,
                "assistant": unknown.answer,
                "citations": unknown.citations,
                "model": unknown.model,
                "fallback": unknown.fallback,
            }
        ],
        "completed_at": now_iso(),
    }


def build_checks(
    turns: list[dict[str, Any]],
    unknown: Any,
    inventory: dict[str, Any],
    direct_docs_search: list[dict[str, Any]],
    use_live: bool,
) -> dict[str, Any]:
    help_turns = [turn for turn in turns if turn["kind"] == "help_doc"]
    analytics_turns = [turn for turn in turns if turn["kind"] in {"analytics", "analytics_mixed"}]
    mixed_turn = next(turn for turn in turns if turn["id"] == "analytics_mixed_refunds_payouts")
    checks = {
        "mode": "live-openai" if use_live else "deterministic-sql-fallback",
        "turn_count": len(turns),
        "analytics_prompt_count": len(analytics_turns),
        "help_doc_prompt_count": len(help_turns),
        "history_message_count": len(turns) * 2,
        "all_turns_have_citations": all(bool(turn["citations"]) for turn in turns),
        "help_doc_answers_include_source_links": all(has_source_link(turn["assistant"]) for turn in help_turns),
        "help_doc_turns_have_help_doc_citations": all("help_doc" in citation_types(turn) for turn in help_turns),
        "mixed_turn_has_product_and_help_doc_citations": {"product", "help_doc"}.issubset(citation_types(mixed_turn)),
        "mixed_turn_combines_metrics_and_source_links": (
            ("%" in mixed_turn["assistant"] or "$" in mixed_turn["assistant"])
            and has_source_link(mixed_turn["assistant"])
        ),
        "unknown_policy_says_not_loaded": "I do not know that from the loaded Gumroad docs" in unknown.answer,
        "direct_docs_search_returns_sources": bool(direct_docs_search)
        and all(str(item.get("source_url", "")).startswith("https://gumroad.com") for item in direct_docs_search),
        "help_doc_inventory_loaded": inventory.get("doc_count", 0) >= 5 and inventory.get("chunk_count", 0) >= 15,
    }
    checks["passed"] = all(value for key, value in checks.items() if key not in {"mode"})
    return checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Gumroad Merchant analytics + help-doc RAG smoke transcript.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use the OpenAI Agents SDK instead of deterministic SQL fallback.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "artifacts" / "gumroad_merchant_help_rag_smoke_2026-04-30.json"),
        help="Path to write the JSON smoke transcript.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    transcript = run_transcript(use_live=bool(args.live))
    output.write_text(json.dumps(transcript, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"wrote {output}")
    print(json.dumps(transcript["checks"], indent=2, ensure_ascii=True))
    return 0 if transcript["checks"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
