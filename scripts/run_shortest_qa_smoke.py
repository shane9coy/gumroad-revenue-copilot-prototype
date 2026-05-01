#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gumroad_merchant.shortest_qa_tools import (  # noqa: E402
    REQUIRED_QA_FIELDS,
    generate_shortest_qa_tests,
    get_shortest_qa_summary,
    list_shortest_qa_suites,
)


REQUIRED_SUITES = {
    "refund_ops",
    "content_radar",
    "retention_saver",
    "admin_action_preview",
    "merchant_chat_fallback",
}


def check_required_fields(test: dict[str, Any]) -> bool:
    return all(field in test and test[field] for field in REQUIRED_QA_FIELDS)


def check_pass_fail_evidence(test: dict[str, Any]) -> bool:
    evidence = test.get("pass_fail_evidence", {})
    return bool(evidence.get("pass")) and bool(evidence.get("fail")) and bool(evidence.get("capture"))


def run_smoke() -> dict[str, Any]:
    summary = get_shortest_qa_summary()
    suites = list_shortest_qa_suites()
    payload = generate_shortest_qa_tests()
    payload_again = generate_shortest_qa_tests()
    tests = payload["tests"]
    suite_ids = {suite["id"] for suite in suites}
    test_suite_ids = {test["suite_id"] for test in tests}
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    serialized_again = json.dumps(payload_again, sort_keys=True, ensure_ascii=True)
    checks = {
        "summary_counts_match_payload": summary["test_count"] == payload["test_count"],
        "required_suite_coverage": REQUIRED_SUITES.issubset(suite_ids) and REQUIRED_SUITES.issubset(test_suite_ids),
        "required_field_coverage": all(check_required_fields(test) for test in tests),
        "pass_fail_evidence_coverage": all(check_pass_fail_evidence(test) for test in tests),
        "json_serializable": bool(serialized),
        "deterministic_output": serialized == serialized_again,
        "read_only_payload": payload["read_only"] is True and all(test.get("read_only") is True for test in tests),
        "no_external_dependencies": payload["external_dependencies"] == [],
    }
    checks["passed"] = all(checks.values())
    return {
        "summary": {
            "suite_count": summary["suite_count"],
            "test_count": summary["test_count"],
            "version": summary["version"],
        },
        "suite_ids": sorted(suite_ids),
        "test_suite_ids": sorted(test_suite_ids),
        "checks": checks,
    }


def main() -> int:
    result = run_smoke()
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["checks"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
