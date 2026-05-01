#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gumroad_merchant.agent_harness import run_agent_chat  # noqa: E402
from gumroad_merchant.database import refresh_database  # noqa: E402
from gumroad_merchant.openai_costs import daily_run_cost_rows  # noqa: E402
from gumroad_merchant.settings import get_settings, openai_key_present  # noqa: E402


DAILY_MERCHANT_OP_PROMPT = """
Run the daily Merchant Op brief for the selected product scope and date range.
Compute revenue, conversion, refund, churn, UTM, source, and location reads with
tools first. Then return a compact brief with:
1. the portfolio state in one sentence,
2. the top three priorities,
3. recommended actions,
4. automation drafts or safe local actions worth staging next.
Keep the model context tight; do not dump raw tables.
""".strip()


def print_cost_note() -> None:
    print("Cost note, standard token pricing:")
    print("run_size,nano,mini")
    for row in daily_run_cost_rows():
        run_size = f"{row['input_tokens']} input + {row['output_tokens']} output"
        print(f"{run_size},{row['nano']},{row['mini']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one compact daily Gumroad Merchant Op brief.")
    parser.add_argument("--product-id", default="all")
    parser.add_argument("--date-range", default="30")
    parser.add_argument("--db-path", default="")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Show config, prompt, and cost note without calling OpenAI.")
    parser.add_argument("--json", action="store_true", help="Print the agent result as JSON.")
    args = parser.parse_args()

    settings = get_settings()
    db_path = Path(args.db_path) if args.db_path else settings.db_path
    refresh_database(db_path, force=args.force_refresh)

    print(f"model={settings.openai_agent_model}")
    print(f"verbosity={settings.openai_agent_verbosity}")
    print(f"max_turns={settings.openai_agent_max_turns}")
    print(f"openai_key_present={openai_key_present()}")
    print_cost_note()

    if args.dry_run:
        print("\nPrompt:")
        print(DAILY_MERCHANT_OP_PROMPT)
        return

    if not openai_key_present():
        raise SystemExit("OPENAI_API_KEY is not present in .env or .env.local.")

    result = run_agent_chat(
        db_path,
        DAILY_MERCHANT_OP_PROMPT,
        product_id=args.product_id,
        date_range=args.date_range,
        use_fallback=False,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "answer": result.answer,
                    "citations": result.citations,
                    "model": result.model,
                    "fallback": result.fallback,
                    "error": result.error,
                },
                indent=2,
            )
        )
        return
    print("\nDaily Merchant Op brief:")
    print(result.answer)
    print(f"\nmodel={result.model} fallback={result.fallback}")
    if result.error:
        print(f"error={result.error}")


if __name__ == "__main__":
    main()
