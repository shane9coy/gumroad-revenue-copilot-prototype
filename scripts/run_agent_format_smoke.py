from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEN_TURN_CONVERSATION = [
    "Give me a concise monthly overview for all products.",
    "What traffic source is working best, and why?",
    "Now compare that to refund risk. Keep it digestible.",
    "Show me the top Refund Ops case and what we should do next.",
    "Draft the buyer reply for the highest priority refund request.",
    "Build a chargeback dispute packet if one is available.",
    "What should we change to reduce future refunds?",
    "Give me one realistic 3-month revenue goal.",
    "What should I ask you next as the merchant?",
    "Summarize this chat in 3 bullets.",
]


TWENTY_TURN_CONVERSATION = [
    "Start with a concise portfolio overview.",
    "Which product has the clearest growth signal?",
    "What source is underperforming despite volume?",
    "What would you do with Gumroad Discover traffic?",
    "Switch to refund prevention. What pattern matters most?",
    "List the refund cases that need review.",
    "Open the highest risk case and explain the evidence.",
    "Draft a copyable buyer response for that case.",
    "Now build a dispute evidence packet if this is a chargeback.",
    "What audit note should the merchant save?",
    "Switch to Content Radar. What trend should we use first?",
    "Build a 4-week marketing plan for that trend.",
    "Draft one campaign asset, but keep it short.",
    "Switch to Retention Saver. What can pause offers save?",
    "Which cancellation risk should we resolve first?",
    "Prepare the best admin action for this context.",
    "Generate QA tests for Refund Ops and Content Radar.",
    "What Gumroad help doc source should we cite for chargebacks?",
    "What needs confirmation before execution?",
    "Close with a concise prioritized next-step list.",
]


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 90) -> dict[str, Any]:
    data = None
    headers = {"accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: {exc.code} {detail}") from exc


def paragraph_blocks(answer: str) -> list[str]:
    normalized = answer.strip().replace("\r\n", "\n")
    if not normalized:
        return []
    return [block.strip() for block in normalized.split("\n\n") if block.strip()]


def formatting_report(answer: str) -> dict[str, Any]:
    blocks = paragraph_blocks(answer)
    lines = [line for line in answer.strip().splitlines() if line.strip()]
    bullet_lines = [
        line
        for line in lines
        if line.lstrip().startswith(("-", "*", "1.", "2.", "3.", "4.", "5."))
    ]
    max_block_chars = max((len(block) for block in blocks), default=0)
    word_count = len(answer.split())
    is_wall_text = word_count > 95 and len(blocks) <= 1 and len(bullet_lines) < 2
    too_long = word_count > 380
    return {
        "blocks": len(blocks),
        "lines": len(lines),
        "bullet_lines": len(bullet_lines),
        "max_block_chars": max_block_chars,
        "word_count": word_count,
        "is_wall_text": is_wall_text,
        "too_long": too_long,
        "passes": not is_wall_text and not too_long,
    }


def run_conversation(api_base: str, label: str, prompts: list[str], product_id: str, date_range: str) -> dict[str, Any]:
    session = request_json(
        "GET",
        f"{api_base}/api/agent/chat/session?{urllib.parse.urlencode({'product_id': product_id, 'date_range': date_range})}",
        timeout=20,
    )
    session_id = session["session_id"]
    turns = []
    started = time.time()
    for index, prompt in enumerate(prompts, start=1):
        turn_started = time.time()
        response = request_json(
            "POST",
            f"{api_base}/api/agent/chat",
            {
                "session_id": session_id,
                "message": prompt,
                "product_id": product_id,
                "date_range": date_range,
            },
        )
        answer = response["answer"]
        turns.append(
            {
                "turn": index,
                "user": prompt,
                "assistant": answer,
                "formatting": formatting_report(answer),
                "fallback": response.get("fallback", False),
                "model": response.get("model", "unknown"),
                "citation_labels": [item.get("label") for item in response.get("citations", [])],
                "elapsed_seconds": round(time.time() - turn_started, 2),
            }
        )
        print(
            f"{label} turn {index:02d}/{len(prompts)} "
            f"ok fallback={turns[-1]['fallback']} words={turns[-1]['formatting']['word_count']} "
            f"blocks={turns[-1]['formatting']['blocks']}"
        )
    failed_turns = [turn for turn in turns if not turn["formatting"]["passes"]]
    return {
        "label": label,
        "session_id": session_id,
        "turn_count": len(turns),
        "elapsed_seconds": round(time.time() - started, 2),
        "failed_formatting_turns": [turn["turn"] for turn in failed_turns],
        "turns": turns,
    }


def write_markdown(output_path: Path, result: dict[str, Any]) -> None:
    lines = [
        f"# Gumroad Merchant Agent Smoke: {result['label']}",
        "",
        f"- Session: `{result['session_id']}`",
        f"- Turns: {result['turn_count']}",
        f"- Elapsed: {result['elapsed_seconds']}s",
        f"- Formatting failures: {result['failed_formatting_turns'] or 'none'}",
        "",
    ]
    for turn in result["turns"]:
        report = turn["formatting"]
        lines.extend(
            [
                f"## Turn {turn['turn']}",
                "",
                f"**User:** {turn['user']}",
                "",
                "**Assistant:**",
                "",
                turn["assistant"].strip(),
                "",
                "**Formatting:** "
                f"words={report['word_count']}, blocks={report['blocks']}, "
                f"bullet_lines={report['bullet_lines']}, max_block_chars={report['max_block_chars']}, "
                f"passes={report['passes']}",
                "",
                f"**Model:** `{turn['model']}` · fallback={turn['fallback']} · elapsed={turn['elapsed_seconds']}s",
                "",
                f"**Citations:** {', '.join(label for label in turn['citation_labels'] if label) or 'none'}",
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument("--output-dir", default="artifacts/smoke_conversations")
    parser.add_argument("--product-id", default="all")
    parser.add_argument("--date-range", default="30")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    request_json("GET", f"{args.api_base}/api/health", timeout=20)
    request_json("POST", f"{args.api_base}/api/agent/data/refresh?force=false", timeout=30)

    results = [
        run_conversation(args.api_base, "10-pass-format", TEN_TURN_CONVERSATION, args.product_id, args.date_range),
        run_conversation(args.api_base, "20-pass-format", TWENTY_TURN_CONVERSATION, args.product_id, args.date_range),
    ]

    for result in results:
        write_markdown(output_dir / f"gumroad_agent_{result['label']}_{timestamp}.md", result)

    summary = {
        "generated_at": timestamp,
        "api_base": args.api_base,
        "results": [
            {
                "label": result["label"],
                "session_id": result["session_id"],
                "turn_count": result["turn_count"],
                "elapsed_seconds": result["elapsed_seconds"],
                "failed_formatting_turns": result["failed_formatting_turns"],
            }
            for result in results
        ],
    }
    summary_path = output_dir / f"gumroad_agent_format_smoke_summary_{timestamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
