from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_PYTHON = Path("/Users/sc/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3")

if (
    not os.environ.get("GUMROAD_MCP_SMOKE_REEXEC")
    and BUNDLED_PYTHON.exists()
    and (sys.version_info < (3, 10) or importlib.util.find_spec("mcp") is None)
):
    env = os.environ.copy()
    env["GUMROAD_MCP_SMOKE_REEXEC"] = "1"
    os.execve(str(BUNDLED_PYTHON), [str(BUNDLED_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]], env)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


EXPECTED_TOOLS = {
    "get_gumroad_merchant_help_menu",
    "get_product_metrics",
    "get_traffic_sources",
    "get_refund_ops_summary",
    "list_refund_cases",
    "build_dispute_evidence_pack",
    "build_marketing_plan",
    "stage_tracked_campaign_action",
    "create_tracked_campaign_action",
    "list_tracked_campaigns",
    "list_agent_actions",
    "apply_agent_action",
    "generate_roadmap_artifact",
    "generate_architecture_diagram",
    "build_pause_offer_plan",
    "get_admin_api_cli_recommendation",
    "preview_admin_action",
    "generate_shortest_qa_tests",
}


def payload_from_result(result: Any) -> dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured
    if result.content:
        first = result.content[0]
        if isinstance(first, TextContent):
            return json.loads(first.text)
    raise AssertionError("MCP tool result did not contain structured JSON payload")


def assert_envelope(payload: dict[str, Any], tool_name: str) -> dict[str, Any]:
    assert payload["ok"] is True, payload
    assert payload["tool"] == tool_name, payload
    assert payload["data_source"] == "seeded_demo", payload
    assert payload["review_only"] is True, payload
    assert payload["will_execute"] is False, payload
    assert "result" in payload, payload
    return payload["result"]


async def call(session: ClientSession, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    result = await session.call_tool(name, arguments=arguments or {})
    return assert_envelope(payload_from_result(result), name)


async def run() -> dict[str, Any]:
    env = os.environ.copy()
    env["GUMROAD_MERCHANT_MODE"] = "seeded"
    server_params = StdioServerParameters(
        command=str(PROJECT_ROOT / "scripts" / "gumroad-merchant-mcp.sh"),
        args=[],
        env=env,
    )
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools_response = await session.list_tools()
            tool_names = {tool.name for tool in tools_response.tools}
            missing = sorted(EXPECTED_TOOLS - tool_names)
            assert not missing, f"Missing expected MCP tools: {missing}"

            help_menu = await call(session, "get_gumroad_merchant_help_menu")
            assert help_menu["sections"], help_menu
            assert "get_admin_api_cli_recommendation" in help_menu["available_tool_names"], help_menu
            assert help_menu["capability_parity"]["status"].startswith("MCP exposes"), help_menu

            refund_summary = await call(session, "get_refund_ops_summary")
            assert refund_summary["cases_needing_review"] >= 1, refund_summary
            assert refund_summary["boundary"], refund_summary

            refund_cases = await call(session, "list_refund_cases", {"mode": "dispute", "limit": 5})
            cases = refund_cases["items"]
            assert cases, refund_cases
            dispute_case = cases[0]

            dispute_pack = await call(
                session,
                "build_dispute_evidence_pack",
                {"case_id": dispute_case["case_id"]},
            )
            assert dispute_pack["review_only"] is True, dispute_pack
            assert dispute_pack["copy_text"], dispute_pack
            assert dispute_pack["evidence_checklist"], dispute_pack

            marketing_plan = await call(session, "build_marketing_plan", {"horizon_weeks": 4})
            assert marketing_plan.get("plan_steps"), marketing_plan

            pause_plan = await call(session, "build_pause_offer_plan")
            assert pause_plan.get("offer_options"), pause_plan

            admin_recommendation = await call(session, "get_admin_api_cli_recommendation")
            answers = admin_recommendation["open_question_answers"]
            assert answers["api_surface"]["recommendation"].startswith("Create a separate internal admin API"), admin_recommendation
            assert "gumroad admin" in answers["cli_shape"]["recommendation"], admin_recommendation

            admin_templates = await call(session, "list_admin_action_templates")
            action_ids = {item["id"] for item in admin_templates["items"]}
            for action_id in {"user_lookup", "compliance_review", "risk_state_change", "fee_update"}:
                assert action_id in action_ids, admin_templates

            admin_preview = await call(
                session,
                "preview_admin_action",
                {"action_id": "refund_review", "case_id": dispute_case["case_id"]},
            )
            assert admin_preview["will_execute"] is False, admin_preview
            assert admin_preview["command_text"], admin_preview

            qa_tests = await call(session, "generate_shortest_qa_tests", {"suite_id": "refund_ops", "limit": 2})
            assert qa_tests["tests"], qa_tests

            return {
                "passed": True,
                "tool_count": len(tool_names),
                "checked_tools": sorted(EXPECTED_TOOLS),
                "help_sections": [item["id"] for item in help_menu["sections"]],
                "sample_case_id": dispute_case["case_id"],
                "sample_admin_preview": admin_preview["command_text"],
                "admin_open_questions_resolved": sorted(answers.keys()),
                "qa_test_count": qa_tests["test_count"],
            }


def main() -> None:
    result = asyncio.run(run())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
