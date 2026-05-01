from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from hashlib import sha256
from pathlib import Path
from typing import Any

from gumroad_merchant.database import connect, connect_readonly, ensure_schema, now_iso
from gumroad_merchant.tracked_campaigns import (
    build_tracked_campaign_payload,
    create_tracked_campaign_tool,
    product_destination_url,
    tracking_url,
)


TRACKED_CAMPAIGN_ACTION = "tracked_campaign.create"
ROADMAP_ACTION = "roadmap.generate"
ARCHITECTURE_DIAGRAM_ACTION = "architecture_diagram.generate"


def stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def action_id() -> str:
    return f"act-{uuid.uuid4().hex[:16]}"


def idempotency_key(action_type: str, payload: dict[str, Any]) -> str:
    digest = sha256(stable_json({"type": action_type, "payload": payload}).encode("utf-8")).hexdigest()
    return f"{action_type}:{digest[:32]}"


def load_json(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def row_to_action(row: sqlite3.Row) -> dict[str, Any]:
    result = load_json(row["result_json"])
    if (
        row["action_type"] == TRACKED_CAMPAIGN_ACTION
        and result.get("destination_source") == "provided"
        and result.get("destination") == product_destination_url(str(result.get("product_name") or ""))
    ):
        result["destination_source"] = "demo_generated"
    return {
        "id": row["id"],
        "action_type": row["action_type"],
        "status": row["status"],
        "idempotency_key": row["idempotency_key"],
        "product_id": row["product_id"],
        "date_range": row["date_range"],
        "payload": load_json(row["payload_json"]),
        "result": result,
        "error": row["error"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "applied_at": row["applied_at"],
        "rejected_at": row["rejected_at"],
    }


def add_audit_event(
    conn: sqlite3.Connection,
    action_id_: str,
    event_type: str,
    note: str,
    payload: dict[str, Any] | None = None,
    actor: str = "merchant-agent",
) -> None:
    conn.execute(
        """
        INSERT INTO action_audit_events(action_id, actor, event_type, note, payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (action_id_, actor, event_type, note, stable_json(payload or {}), now_iso()),
    )


def create_pending_action(
    db_path: Path | str,
    action_type: str,
    payload: dict[str, Any],
    product_id: str = "all",
    date_range: str = "30",
    created_by: str = "merchant-agent",
    note: str | None = None,
) -> dict[str, Any]:
    key = idempotency_key(action_type, payload)
    now = now_iso()
    with closing(connect(db_path)) as conn:
        ensure_schema(conn)
        try:
            conn.execute(
                """
                INSERT INTO agent_actions(
                    id, action_type, status, idempotency_key, product_id, date_range,
                    payload_json, result_json, created_by, created_at, updated_at
                )
                VALUES (?, ?, 'pending', ?, ?, ?, ?, '{}', ?, ?, ?)
                """,
                (
                    action_id(),
                    action_type,
                    key,
                    product_id or "all",
                    date_range or "30",
                    stable_json(payload),
                    created_by,
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM agent_actions WHERE idempotency_key = ?", (key,)).fetchone()
            add_audit_event(conn, row["id"], "pending_created", note or f"Staged {action_type}.", {"action_type": action_type})
            conn.commit()
        except sqlite3.IntegrityError:
            row = conn.execute("SELECT * FROM agent_actions WHERE idempotency_key = ?", (key,)).fetchone()
        if not row:
            raise RuntimeError("Agent action was not saved.")
        return row_to_action(row)


def get_agent_action(db_path: Path | str, action_id_: str) -> dict[str, Any] | None:
    with closing(connect_readonly(db_path)) as conn:
        row = conn.execute("SELECT * FROM agent_actions WHERE id = ?", (action_id_,)).fetchone()
    return row_to_action(row) if row else None


def latest_pending_action(
    db_path: Path | str,
    action_type: str,
    product_id: str = "all",
    date_range: str = "30",
) -> dict[str, Any] | None:
    with closing(connect_readonly(db_path)) as conn:
        row = conn.execute(
            """
            SELECT * FROM agent_actions
            WHERE action_type = ?
              AND status = 'pending'
              AND product_id = ?
              AND date_range = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (action_type, product_id or "all", date_range or "30"),
        ).fetchone()
    return row_to_action(row) if row else None


def list_agent_actions_tool(
    db_path: Path | str,
    action_type: str = "all",
    status: str = "all",
    product_id: str = "all",
    limit: int = 50,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 100))
    clauses: list[str] = []
    params: list[Any] = []
    if action_type and action_type != "all":
        clauses.append("action_type = ?")
        params.append(action_type)
    if status and status != "all":
        clauses.append("status = ?")
        params.append(status)
    if product_id and product_id != "all":
        clauses.append("product_id = ?")
        params.append(product_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with closing(connect_readonly(db_path)) as conn:
        rows = conn.execute(
            f"SELECT * FROM agent_actions {where} ORDER BY created_at DESC LIMIT ?",
            [*params, limit],
        ).fetchall()
    return [row_to_action(row) for row in rows]


def tracked_campaign_preview(payload: dict[str, Any]) -> dict[str, Any]:
    campaign = payload["campaign"]
    return {
        "product_id": payload["product_id"],
        "product_name": payload["product_name"],
        "title": payload["title"],
        "campaign": campaign,
        "source": payload["source"],
        "medium": payload["medium"],
        "destination": payload["destination_url"],
        "destination_source": payload["destination_source"],
        "tracking_url": tracking_url(payload["destination_url"], payload["source"], payload["medium"], campaign),
        "reason": payload["reason"],
        "attribution_window_days": 7,
    }


def stage_tracked_campaign_action_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    title: str | None = None,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    destination_url: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    payload = build_tracked_campaign_payload(
        db_path,
        product_id=product_id,
        date_range=date_range,
        title=title,
        source=source,
        medium=medium,
        campaign=campaign,
        destination_url=destination_url,
        reason=reason,
    )
    payload["selected_product_id"] = product_id or "all"
    action = create_pending_action(
        db_path,
        TRACKED_CAMPAIGN_ACTION,
        payload,
        product_id=product_id or "all",
        date_range=date_range or "30",
        note="Staged a tracked campaign for explicit merchant approval.",
    )
    return {"action": action, "preview": tracked_campaign_preview(payload)}


def apply_agent_action_tool(db_path: Path | str, action_id_: str) -> dict[str, Any]:
    action = get_agent_action(db_path, action_id_)
    if not action:
        raise ValueError(f"Agent action {action_id_} was not found.")
    if action["status"] == "applied":
        return {"action": action, "result": action["result"], "already_applied": True}
    if action["status"] != "pending":
        raise ValueError(f"Agent action {action_id_} is {action['status']} and cannot be applied.")
    payload = action["payload"]
    try:
        if action["action_type"] == TRACKED_CAMPAIGN_ACTION:
            result = create_tracked_campaign_tool(
                db_path,
                product_id=payload.get("product_id") or action["product_id"],
                date_range=payload.get("date_range") or action["date_range"],
                title=payload.get("title"),
                source=payload.get("source"),
                medium=payload.get("medium"),
                campaign=payload.get("campaign"),
                destination_url=payload.get("destination_url"),
                destination_source=payload.get("destination_source"),
                reason=payload.get("reason"),
            )
        elif action["action_type"] == ROADMAP_ACTION:
            from gumroad_merchant.roadmap_artifacts import generate_roadmap_artifact

            result = generate_roadmap_artifact(
                db_path,
                product_id=payload.get("product_id") or action["product_id"],
                date_range=payload.get("date_range") or action["date_range"],
                horizon_days=int(payload.get("horizon_days") or 30),
            )
        elif action["action_type"] == ARCHITECTURE_DIAGRAM_ACTION:
            from gumroad_merchant.architecture_diagram_tools import generate_architecture_diagram_artifact

            result = generate_architecture_diagram_artifact(
                diagram_type=payload.get("diagram_type") or "agent-action-system",
                title=payload.get("title"),
            )
        else:
            raise ValueError(f"Unsupported action type: {action['action_type']}")
        now = now_iso()
        with closing(connect(db_path)) as conn:
            ensure_schema(conn)
            conn.execute(
                """
                UPDATE agent_actions
                SET status = 'applied', result_json = ?, error = NULL, updated_at = ?, applied_at = ?
                WHERE id = ?
                """,
                (stable_json(result), now, now, action_id_),
            )
            add_audit_event(conn, action_id_, "applied", f"Applied {action['action_type']}.", result)
            conn.commit()
        updated = get_agent_action(db_path, action_id_)
        return {"action": updated, "result": result, "already_applied": False}
    except Exception as exc:
        now = now_iso()
        with closing(connect(db_path)) as conn:
            ensure_schema(conn)
            conn.execute(
                "UPDATE agent_actions SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                (str(exc), now, action_id_),
            )
            add_audit_event(conn, action_id_, "failed", f"{action['action_type']} failed: {exc}")
            conn.commit()
        raise


def apply_latest_pending_action_tool(
    db_path: Path | str,
    action_type: str,
    product_id: str = "all",
    date_range: str = "30",
) -> dict[str, Any] | None:
    pending = latest_pending_action(db_path, action_type=action_type, product_id=product_id, date_range=date_range)
    if not pending:
        return None
    return apply_agent_action_tool(db_path, pending["id"])


def create_tracked_campaign_action_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    title: str | None = None,
    source: str | None = None,
    medium: str | None = None,
    campaign: str | None = None,
    destination_url: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    staged = stage_tracked_campaign_action_tool(
        db_path,
        product_id=product_id,
        date_range=date_range,
        title=title,
        source=source,
        medium=medium,
        campaign=campaign,
        destination_url=destination_url,
        reason=reason,
    )
    applied = apply_agent_action_tool(db_path, staged["action"]["id"])
    return {"action": applied["action"], "campaign": applied["result"], "already_applied": applied["already_applied"]}


def create_roadmap_action_tool(
    db_path: Path | str,
    product_id: str = "all",
    date_range: str = "30",
    horizon_days: int = 30,
) -> dict[str, Any]:
    payload = {
        "product_id": product_id or "all",
        "date_range": date_range or "30",
        "horizon_days": 60 if int(horizon_days) >= 60 else 30,
        "format": "html",
    }
    action = create_pending_action(
        db_path,
        ROADMAP_ACTION,
        payload,
        product_id=payload["product_id"],
        date_range=payload["date_range"],
        note=f"Staged a {payload['horizon_days']}-day downloadable roadmap.",
    )
    applied = apply_agent_action_tool(db_path, action["id"])
    return {"action": applied["action"], "artifact": applied["result"], "already_applied": applied["already_applied"]}


def create_architecture_diagram_action_tool(
    db_path: Path | str,
    diagram_type: str = "agent-action-system",
    title: str | None = None,
) -> dict[str, Any]:
    payload = {
        "diagram_type": diagram_type or "agent-action-system",
        "title": title or "Gumroad Merchant agent action architecture",
    }
    action = create_pending_action(
        db_path,
        ARCHITECTURE_DIAGRAM_ACTION,
        payload,
        product_id="all",
        date_range="all",
        note="Staged deterministic architecture diagram generation.",
    )
    applied = apply_agent_action_tool(db_path, action["id"])
    return {"action": applied["action"], "artifact": applied["result"], "already_applied": applied["already_applied"]}
