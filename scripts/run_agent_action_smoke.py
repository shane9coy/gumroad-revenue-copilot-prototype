#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gumroad_merchant.agent_actions import (  # noqa: E402
    TRACKED_CAMPAIGN_ACTION,
    apply_agent_action_tool,
    create_architecture_diagram_action_tool,
    create_roadmap_action_tool,
    list_agent_actions_tool,
    stage_tracked_campaign_action_tool,
)
from gumroad_merchant.agent_harness import run_agent_chat  # noqa: E402
from gumroad_merchant.database import refresh_database  # noqa: E402
from gumroad_merchant.tracked_campaigns import list_tracked_campaigns_tool  # noqa: E402


def count_rows(db_path: Path, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0])
    finally:
        conn.close()


def cleanup_artifact(result: dict) -> None:
    artifact = result.get("artifact") or result.get("result") or {}
    path = artifact.get("file_path")
    if path:
        try:
            Path(path).unlink()
        except FileNotFoundError:
            pass


def main() -> None:
    os.environ["OPENAI_API_KEY"] = ""
    db_path = Path("/tmp/gumroad-agent-action-smoke.sqlite")
    if db_path.exists():
        db_path.unlink()

    refresh_database(db_path, force=True)

    staged = stage_tracked_campaign_action_tool(db_path, product_id="all", date_range="30")
    assert staged["action"]["status"] == "pending", staged
    assert staged["preview"]["tracking_url"].startswith("https://gumroad.com/l/"), staged
    assert count_rows(db_path, "tracked_campaigns") == 0

    applied = apply_agent_action_tool(db_path, staged["action"]["id"])
    assert applied["action"]["status"] == "applied", applied
    assert applied["result"]["tracking_url"], applied
    assert count_rows(db_path, "tracked_campaigns") == 1

    repeated = apply_agent_action_tool(db_path, staged["action"]["id"])
    assert repeated["already_applied"] is True, repeated
    assert count_rows(db_path, "tracked_campaigns") == 1

    refresh_database(db_path, force=True)
    assert len(list_tracked_campaigns_tool(db_path)) == 1
    assert len(list_agent_actions_tool(db_path, action_type=TRACKED_CAMPAIGN_ACTION, status="applied")) == 1

    roadmap = create_roadmap_action_tool(db_path, product_id="all", date_range="30", horizon_days=30)
    assert roadmap["artifact"]["download_url"].startswith("/api/artifacts/roadmaps/"), roadmap
    assert Path(roadmap["artifact"]["file_path"]).exists(), roadmap

    diagram = create_architecture_diagram_action_tool(db_path)
    assert diagram["artifact"]["download_url"].startswith("/api/artifacts/architecture/"), diagram
    assert Path(diagram["artifact"]["file_path"]).exists(), diagram

    chat_db_path = Path("/tmp/gumroad-agent-action-chat-smoke.sqlite")
    if chat_db_path.exists():
        chat_db_path.unlink()
    refresh_database(chat_db_path, force=True)
    offer = run_agent_chat(chat_db_path, "What Content Radar move should we use first?", product_id="all", date_range="30")
    assert "staged action" in offer.answer.lower() or "already created" in offer.answer.lower(), offer.answer
    confirm = run_agent_chat(
        chat_db_path,
        "boom, okay",
        product_id="all",
        date_range="30",
        conversation_history=[{"role": "assistant", "content": offer.answer}],
    )
    assert "tracking url" in confirm.answer.lower(), confirm.answer
    assert count_rows(chat_db_path, "tracked_campaigns") == 1
    second_confirm = run_agent_chat(
        chat_db_path,
        "boom, okay",
        product_id="all",
        date_range="30",
        conversation_history=[{"role": "assistant", "content": offer.answer}],
    )
    assert count_rows(chat_db_path, "tracked_campaigns") == 1
    assert "reused" in second_confirm.answer.lower() or "tracking url" in second_confirm.answer.lower(), second_confirm.answer

    cleanup_artifact(roadmap)
    cleanup_artifact(diagram)
    print("agent action smoke passed")


if __name__ == "__main__":
    main()
