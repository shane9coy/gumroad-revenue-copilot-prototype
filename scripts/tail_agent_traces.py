from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


DEFAULT_TRACE_PATH = Path("artifacts/agent_traces/gumroad_agent_traces.jsonl")


def format_event(record: dict) -> str:
    pieces = [
        record.get("ts", ""),
        record.get("event", ""),
    ]
    if record.get("duration_ms") is not None:
        pieces.append(f"{record['duration_ms']}ms")
    if record.get("tool"):
        pieces.append(f"tool={record['tool']}")
    if record.get("fallback") is not None:
        pieces.append(f"fallback={record['fallback']}")
    if record.get("answer_words") is not None:
        pieces.append(f"words={record['answer_words']}")
    if record.get("error"):
        pieces.append(f"error={record['error']}")
    if record.get("trace_id"):
        pieces.append(f"trace={record['trace_id']}")
    return " | ".join(str(piece) for piece in pieces if piece)


def emit_line(line: str, trace_id: str | None = None) -> None:
    try:
        record = json.loads(line)
    except json.JSONDecodeError:
        return
    if trace_id and record.get("trace_id") != trace_id:
        return
    print(format_event(record), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tail Gumroad Merchant agent JSONL traces.")
    parser.add_argument("--path", default=str(DEFAULT_TRACE_PATH))
    parser.add_argument("--trace-id", default=None)
    parser.add_argument("--lines", type=int, default=80)
    parser.add_argument("--follow", action="store_true")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"Trace file does not exist yet: {path}")

    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[-max(1, args.lines):]:
        emit_line(line, trace_id=args.trace_id)

    if not args.follow:
        return

    with path.open("r", encoding="utf-8") as handle:
        handle.seek(0, 2)
        while True:
            line = handle.readline()
            if line:
                emit_line(line, trace_id=args.trace_id)
            else:
                time.sleep(0.2)


if __name__ == "__main__":
    main()
