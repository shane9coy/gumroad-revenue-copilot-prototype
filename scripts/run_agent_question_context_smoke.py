#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_MODEL = "gpt-5.4-nano"

LIVE_PROBE = (
    "Provide an operator diagnostic for the selected scope. Use tools for factual claims. "
    "Include two exact observations, one cited risk, and one next action."
)

FIVE_TURN_CONVERSATION = [
    "Explain the Recent signal section for all products over the last 30 days. Include revenue, sales, conversion, refund rate, top source, and the single next action.",
    "Explain the Suggested next moves section for all products over the last 30 days. Include the top three recommendations, their confidence, and the specific evidence behind each.",
    "Explain the Content Radar section for all products over the last 30 days. Include the selected trend, fit score, KPI baseline or target, evidence, risk, and whether to create a tracked campaign.",
    "Explain the Retention Saver section for all products over the last 30 days. Include churn, canceled memberships, lost recurring revenue, saved-revenue estimate, pause offers, and the top risk.",
    "Explain the Shortest QA section for Gumroad Merchant. Include suite count, assertion count, active suite, pass/fail evidence, and what should run first.",
]

TEN_TURN_CONVERSATION = [
    "Explain the Recent signal section for all products over the last 30 days with exact current metrics and one next action.",
    "Explain the traffic-source section for all products over the last 30 days. Compare views, sales, conversion, revenue, and source quality.",
    "Explain the Suggested next moves cards. For each visible recommendation, cite the reason, evidence, confidence, and the action it should stage.",
    "Explain Refund Ops in Prevent mode. Include refund rate, previous refund rate, disputed exposure, preventable estimate, and the first prevention action.",
    "Explain the highest-priority refund or dispute detail. Include purchase facts, risk score, recommended action, evidence, and what should not be executed automatically.",
    "Explain Content Radar's selected marketing plan. Include trend fit, channel, KPI, rationale, evidence, risks, and UTM campaign fields.",
    "Explain Retention Saver's pause-before-cancel plan. Include churn, lost revenue, saved estimate, pause options, save assumption, and the top cancellation risk.",
    "Explain Admin Actions. Include template count, reads, writes, selected command, required inputs, preflight checks, and audit note.",
    "Explain Shortest QA. Include active suite, target surface, risk covered, steps, assertions, and pass/fail evidence.",
    "Explain UTM links and attribution cleanup. Include campaign rows, clicks, sales, conversion, revenue, and which campaign deserves another test.",
]


def request_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = 120) -> dict[str, Any]:
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
    word_count = len(answer.split())
    max_block_chars = max((len(block) for block in blocks), default=0)
    return {
        "blocks": len(blocks),
        "lines": len(lines),
        "bullet_lines": len(bullet_lines),
        "word_count": word_count,
        "max_block_chars": max_block_chars,
        "passes": bool(answer.strip()) and not (word_count > 110 and len(blocks) <= 1 and len(bullet_lines) < 2),
    }


def data_tokens(answer: str) -> list[str]:
    patterns = [
        r"\$[0-9][0-9,]*(?:\.[0-9]{2})?",
        r"\b[0-9]+(?:\.[0-9]+)?%",
        r"\b[0-9][0-9,]*\s+(?:views|sales|refunds|cases|trends|checks|assertions|suites|clicks|memberships|canceled)\b",
        r"\brisk\s+[0-9]+/100\b",
        r"\bfit\s+[0-9]+/100\b",
        r"\b[0-9]+/100\s+(?:fit|trend|risk)\b",
        r"\butm_[a-z]+=[^\\s,;]+",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, answer, flags=re.IGNORECASE))
    normalized = []
    seen = set()
    for token in found:
        item = " ".join(str(token).split()).lower()
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)
    return normalized


def answer_signature(answer: str) -> str:
    normalized = re.sub(r"\s+", " ", answer.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]


def min_data_tokens_for_prompt(prompt: str) -> int:
    lowered = prompt.lower()
    if "utm" in lowered or "campaign rows" in lowered or "attribution cleanup" in lowered:
        return 4
    if "include" in lowered and any(
        term in lowered
        for term in (
            "revenue",
            "sales",
            "conversion",
            "refund",
            "churn",
            "clicks",
            "risk score",
            "fit score",
        )
    ):
        return 2
    return 0


def run_turn(api_base: str, session_id: str, prompt: str, product_id: str, date_range: str) -> dict[str, Any]:
    started = time.time()
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
    answer = response.get("answer", "")
    citations = response.get("citations", [])
    tokens = data_tokens(answer)
    report = formatting_report(answer)
    model = response.get("model", "unknown")
    fallback = bool(response.get("fallback", False))
    required_data_tokens = min_data_tokens_for_prompt(prompt)
    data_requirement_passes = len(tokens) >= required_data_tokens
    return {
        "user": prompt,
        "assistant": answer,
        "model": model,
        "fallback": fallback,
        "citations": citations,
        "citation_labels": [item.get("label") for item in citations if item.get("label")],
        "data_tokens": tokens,
        "data_token_count": len(tokens),
        "required_data_token_count": required_data_tokens,
        "formatting": report,
        "answer_signature": answer_signature(answer),
        "elapsed_seconds": round(time.time() - started, 2),
        "passes": (
            model == EXPECTED_MODEL
            and report["passes"]
            and data_requirement_passes
            and (len(tokens) >= 2 or len(citations) >= 1)
        ),
    }


def new_session(api_base: str, product_id: str, date_range: str) -> str:
    query = urllib.parse.urlencode({"product_id": product_id, "date_range": date_range})
    session = request_json("GET", f"{api_base}/api/agent/chat/session?{query}", timeout=30)
    return str(session["session_id"])


def run_conversation(api_base: str, label: str, prompts: list[str], product_id: str, date_range: str) -> dict[str, Any]:
    session_id = new_session(api_base, product_id, date_range)
    turns = []
    started = time.time()
    for index, prompt in enumerate(prompts, start=1):
        result = run_turn(api_base, session_id, prompt, product_id, date_range)
        result["turn"] = index
        turns.append(result)
        print(
            f"{label} turn {index:02d}/{len(prompts)} "
            f"model={result['model']} fallback={result['fallback']} "
            f"data={result['data_token_count']} citations={len(result['citations'])} "
            f"pass={result['passes']} elapsed={result['elapsed_seconds']}s"
        )
    signatures = [turn["answer_signature"] for turn in turns]
    all_data_tokens = sorted({token for turn in turns for token in turn["data_tokens"]})
    failed_turns = [turn["turn"] for turn in turns if not turn["passes"]]
    return {
        "label": label,
        "session_id": session_id,
        "turn_count": len(turns),
        "elapsed_seconds": round(time.time() - started, 2),
        "unique_answer_count": len(set(signatures)),
        "unique_data_token_count": len(all_data_tokens),
        "unique_data_tokens": all_data_tokens,
        "failed_turns": failed_turns,
        "passes": not failed_turns and len(set(signatures)) == len(signatures) and len(all_data_tokens) >= len(turns) * 2,
        "turns": turns,
    }


def write_markdown(path: Path, result: dict[str, Any], live_probe: dict[str, Any]) -> None:
    lines = [
        f"# Gumroad Merchant Question Context Smoke: {result['label']}",
        "",
        f"- Session: `{result['session_id']}`",
        f"- Turns: {result['turn_count']}",
        f"- Elapsed: {result['elapsed_seconds']}s",
        f"- Unique answers: {result['unique_answer_count']}/{result['turn_count']}",
        f"- Unique data tokens: {result['unique_data_token_count']}",
        f"- Failed turns: {result['failed_turns'] or 'none'}",
        f"- Passes: {result['passes']}",
        "",
        "## Live Model Probe",
        "",
        f"- Model: `{live_probe['model']}`",
        f"- Fallback: `{live_probe['fallback']}`",
        f"- Data tokens: {live_probe['data_token_count']}",
        f"- Citations: {', '.join(live_probe['citation_labels']) or 'none'}",
        f"- Passes: `{live_probe['passes'] and not live_probe['fallback']}`",
        "",
    ]
    for turn in result["turns"]:
        fmt = turn["formatting"]
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
                "**Checks:** "
                f"model={turn['model']}, fallback={turn['fallback']}, "
                f"data_tokens={turn['data_token_count']}, citations={len(turn['citations'])}, "
                f"words={fmt['word_count']}, blocks={fmt['blocks']}, pass={turn['passes']}",
                "",
                f"**Data tokens:** {', '.join(turn['data_tokens']) or 'none'}",
                "",
                f"**Citations:** {', '.join(turn['citation_labels']) or 'none'}",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test question-mark context and Gumroad Merchant chat data grounding.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001")
    parser.add_argument("--output-dir", default="artifacts/smoke_conversations")
    parser.add_argument("--product-id", default="all")
    parser.add_argument("--date-range", default="30")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    health = request_json("GET", f"{args.api_base}/api/health", timeout=30)
    refresh = request_json("POST", f"{args.api_base}/api/agent/data/refresh?force=false", timeout=45)
    products = request_json("GET", f"{args.api_base}/api/analytics/products", timeout=45)

    live_session = new_session(args.api_base, args.product_id, args.date_range)
    live_probe = run_turn(args.api_base, live_session, LIVE_PROBE, args.product_id, args.date_range)
    live_probe["passes_live"] = live_probe["passes"] and not live_probe["fallback"]
    print(
        "live-probe "
        f"model={live_probe['model']} fallback={live_probe['fallback']} "
        f"data={live_probe['data_token_count']} citations={len(live_probe['citations'])} "
        f"pass={live_probe['passes_live']}"
    )

    results = [
        run_conversation(args.api_base, "5-pass-question-context", FIVE_TURN_CONVERSATION, args.product_id, args.date_range),
        run_conversation(args.api_base, "10-pass-question-context", TEN_TURN_CONVERSATION, args.product_id, args.date_range),
    ]

    for result in results:
        write_markdown(output_dir / f"gumroad_agent_{result['label']}_{timestamp}.md", result, live_probe)

    summary = {
        "generated_at": timestamp,
        "api_base": args.api_base,
        "health": health,
        "refresh": refresh,
        "product_count": len(products.get("products", [])),
        "expected_model": EXPECTED_MODEL,
        "live_probe": {
            "model": live_probe["model"],
            "fallback": live_probe["fallback"],
            "passes_live": live_probe["passes_live"],
            "data_token_count": live_probe["data_token_count"],
            "citation_labels": live_probe["citation_labels"],
            "elapsed_seconds": live_probe["elapsed_seconds"],
        },
        "results": [
            {
                "label": result["label"],
                "session_id": result["session_id"],
                "turn_count": result["turn_count"],
                "elapsed_seconds": result["elapsed_seconds"],
                "unique_answer_count": result["unique_answer_count"],
                "unique_data_token_count": result["unique_data_token_count"],
                "failed_turns": result["failed_turns"],
                "passes": result["passes"],
            }
            for result in results
        ],
    }
    summary_path = output_dir / f"gumroad_agent_question_context_smoke_summary_{timestamp}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    failed = [result["label"] for result in results if not result["passes"]]
    if failed or not live_probe["passes_live"]:
        raise SystemExit(f"question context smoke failed: live_probe={live_probe['passes_live']} failed={failed}")


if __name__ == "__main__":
    main()
