from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


ChatRole = Literal["user", "assistant"]
VALID_ROLES = {"user", "assistant"}
ChatStatus = Literal["received", "processing", "completed", "failed"]
VALID_STATUSES = {"received", "processing", "completed", "failed"}
DEFAULT_SESSION_TITLES = {"", "Gumroad Merchant", "Untitled conversation", "New conversation"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def auto_session_title(content: str, max_chars: int = 88) -> str | None:
    normalized = " ".join(str(content or "").split())
    if not normalized:
        return None

    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    title = " ".join(sentences[:2]) if sentences else normalized
    title = title.strip().rstrip(" .!?")
    if not title:
        return None

    if len(title) <= max_chars:
        return title

    truncated = title[: max_chars + 1].rsplit(" ", 1)[0].strip()
    return f"{(truncated or title[:max_chars]).rstrip(' .,;:!?')}..."


def session_title_is_default(title: str | None) -> bool:
    return " ".join(str(title or "").split()) in DEFAULT_SESSION_TITLES


def apply_auto_session_title(conn: sqlite3.Connection, session_id: str, content: str) -> None:
    title = auto_session_title(content)
    if not title:
        return

    timestamp = now_iso()
    conn.execute(
        """
        UPDATE chat_sessions
        SET title = ?, updated_at = ?
        WHERE id = ?
          AND archived_at IS NULL
          AND (
            title IS NULL
            OR TRIM(title) = ''
            OR title IN ('Gumroad Merchant', 'Untitled conversation', 'New conversation')
          )
        """,
        (title, timestamp, session_id),
    )


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 60000")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            date_range TEXT,
            title TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            latest_message_at TEXT,
            message_count INTEGER NOT NULL DEFAULT 0,
            saved_at TEXT,
            archived_at TEXT
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            status TEXT NOT NULL DEFAULT 'completed' CHECK(status IN ('received', 'processing', 'completed', 'failed')),
            content TEXT NOT NULL,
            citations_json TEXT NOT NULL DEFAULT '[]',
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
            ON chat_messages(session_id, created_at, id);
        """
    )
    columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()
    }
    if "saved_at" not in columns:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN saved_at TEXT")
    if "archived_at" not in columns:
        conn.execute("ALTER TABLE chat_sessions ADD COLUMN archived_at TEXT")
    message_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
    }
    if "status" not in message_columns:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
    conn.commit()


def ensure_session(
    conn: sqlite3.Connection,
    session_id: str,
    product_id: str = "all",
    date_range: str = "30",
    title: str | None = None,
) -> None:
    ensure_schema(conn)
    timestamp = now_iso()
    conn.execute(
        """
        INSERT INTO chat_sessions(id, product_id, date_range, title, created_at, updated_at, latest_message_at, message_count)
        VALUES (?, ?, ?, ?, ?, ?, NULL, 0)
        ON CONFLICT(id) DO UPDATE SET
            product_id = excluded.product_id,
            date_range = excluded.date_range,
            title = CASE
                WHEN chat_sessions.title IS NULL
                    OR TRIM(chat_sessions.title) = ''
                    OR chat_sessions.title IN ('Gumroad Merchant', 'Untitled conversation', 'New conversation')
                THEN COALESCE(excluded.title, chat_sessions.title)
                ELSE chat_sessions.title
            END,
            updated_at = excluded.updated_at
        """,
        (session_id, product_id, date_range, title, timestamp, timestamp),
    )
    conn.commit()


def update_session_counts(conn: sqlite3.Connection, session_id: str, latest_message_at: str) -> None:
    conn.execute(
        """
        UPDATE chat_sessions
        SET
            updated_at = ?,
            latest_message_at = ?,
            message_count = (
                SELECT COUNT(*) FROM chat_messages WHERE session_id = ?
            )
        WHERE id = ?
        """,
        (latest_message_at, latest_message_at, session_id, session_id),
    )


def append_message(
    conn: sqlite3.Connection,
    session_id: str,
    role: ChatRole,
    content: str,
    citations: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
    status: ChatStatus = "completed",
) -> int:
    normalized_session = (session_id or "").strip()
    normalized_role = str(role).strip().lower()
    normalized_status = str(status).strip().lower()
    normalized_content = str(content).strip()
    if not normalized_session:
        raise ValueError("session_id cannot be empty")
    if normalized_role not in VALID_ROLES:
        raise ValueError("role must be user or assistant")
    if normalized_status not in VALID_STATUSES:
        raise ValueError("status must be received, processing, completed, or failed")
    if not normalized_content:
        raise ValueError("content cannot be empty")
    ensure_schema(conn)
    existing_session = conn.execute(
        "SELECT title FROM chat_sessions WHERE id = ? AND archived_at IS NULL",
        (normalized_session,),
    ).fetchone()
    if existing_session:
        if normalized_role == "user" and session_title_is_default(existing_session["title"]):
            apply_auto_session_title(conn, normalized_session, normalized_content)
    else:
        ensure_session(
            conn,
            normalized_session,
            title=auto_session_title(normalized_content) if normalized_role == "user" else None,
        )
    timestamp = now_iso()
    cursor = conn.execute(
        """
        INSERT INTO chat_messages(session_id, role, status, content, citations_json, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_session,
            normalized_role,
            normalized_status,
            normalized_content,
            json.dumps(citations or [], ensure_ascii=True),
            json.dumps(metadata or {}, ensure_ascii=True),
            timestamp,
        ),
    )
    update_session_counts(conn, normalized_session, timestamp)
    conn.commit()
    return int(cursor.lastrowid)


def update_message_status(
    conn: sqlite3.Connection,
    message_id: int,
    status: ChatStatus,
    metadata: dict[str, Any] | None = None,
) -> None:
    ensure_schema(conn)
    normalized_status = str(status).strip().lower()
    if normalized_status not in VALID_STATUSES:
        raise ValueError("status must be received, processing, completed, or failed")

    if metadata is None:
        conn.execute(
            """
            UPDATE chat_messages
            SET status = ?
            WHERE id = ?
            """,
            (normalized_status, message_id),
        )
    else:
        conn.execute(
            """
            UPDATE chat_messages
            SET status = ?, metadata_json = ?
            WHERE id = ?
            """,
            (
                normalized_status,
                json.dumps(metadata or {}, ensure_ascii=True),
                message_id,
            ),
        )
    conn.commit()


def record_turn(
    conn: sqlite3.Connection,
    session_id: str,
    user_message: str,
    assistant_answer: str,
    citations: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_message_id = append_message(conn, session_id, "user", user_message, status="received")
    assistant_message_id = append_message(
        conn,
        session_id,
        "assistant",
        assistant_answer,
        citations=citations,
        metadata=metadata,
    )
    return {
        "session_id": session_id,
        "user_message_id": user_message_id,
        "assistant_message_id": assistant_message_id,
    }


def decode_json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def session_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "product_id": row["product_id"] or "all",
        "date_range": row["date_range"] or "30",
        "title": row["title"] or "Untitled conversation",
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "latest_message_at": row["latest_message_at"],
        "message_count": int(row["message_count"] or 0),
        "saved_at": row["saved_at"],
        "archived_at": row["archived_at"],
    }


def list_sessions(conn: sqlite3.Connection, recent_limit: int = 10, saved_limit: int = 50) -> dict[str, list[dict[str, Any]]]:
    ensure_schema(conn)
    bounded_recent_limit = max(1, min(25, int(recent_limit or 10)))
    bounded_saved_limit = max(1, min(100, int(saved_limit or 50)))
    recent_rows = conn.execute(
        """
        SELECT *
        FROM chat_sessions
        WHERE archived_at IS NULL
        ORDER BY COALESCE(latest_message_at, updated_at, created_at) DESC, created_at DESC
        LIMIT ?
        """,
        (bounded_recent_limit,),
    ).fetchall()
    saved_rows = conn.execute(
        """
        SELECT *
        FROM chat_sessions
        WHERE archived_at IS NULL AND saved_at IS NOT NULL
        ORDER BY saved_at DESC, COALESCE(latest_message_at, updated_at, created_at) DESC
        LIMIT ?
        """,
        (bounded_saved_limit,),
    ).fetchall()
    return {
        "recent": [session_record(row) for row in recent_rows],
        "saved": [session_record(row) for row in saved_rows],
    }


def get_session(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    ensure_schema(conn)
    row = conn.execute(
        """
        SELECT *
        FROM chat_sessions
        WHERE id = ? AND archived_at IS NULL
        """,
        (session_id,),
    ).fetchone()
    return session_record(row) if row else None


def update_session(
    conn: sqlite3.Connection,
    session_id: str,
    title: str | None = None,
    saved: bool | None = None,
) -> dict[str, Any] | None:
    ensure_schema(conn)
    current = get_session(conn, session_id)
    if not current:
        return None
    timestamp = now_iso()
    updates = ["updated_at = ?"]
    values: list[Any] = [timestamp]
    if title is not None:
        cleaned_title = " ".join(str(title).split())[:120]
        if cleaned_title:
            updates.append("title = ?")
            values.append(cleaned_title)
    if saved is not None:
        updates.append("saved_at = ?")
        values.append(timestamp if saved else None)
    values.append(session_id)
    conn.execute(
        f"""
        UPDATE chat_sessions
        SET {", ".join(updates)}
        WHERE id = ? AND archived_at IS NULL
        """,
        values,
    )
    conn.commit()
    return get_session(conn, session_id)


def archive_session(conn: sqlite3.Connection, session_id: str) -> dict[str, Any] | None:
    ensure_schema(conn)
    current = get_session(conn, session_id)
    if not current:
        return None
    timestamp = now_iso()
    conn.execute(
        """
        UPDATE chat_sessions
        SET archived_at = ?, updated_at = ?
        WHERE id = ? AND archived_at IS NULL
        """,
        (timestamp, timestamp, session_id),
    )
    conn.commit()
    archived = current.copy()
    archived["archived_at"] = timestamp
    archived["updated_at"] = timestamp
    return archived


def load_messages(conn: sqlite3.Connection, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
    ensure_schema(conn)
    rows = conn.execute(
        """
        SELECT id, session_id, role, status, content, citations_json, metadata_json, created_at
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT ?
        """,
        (session_id, max(1, min(200, int(limit or 50)))),
    ).fetchall()
    output = []
    for row in reversed(rows):
        output.append(
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "role": row["role"],
                "status": row["status"],
                "content": row["content"],
                "citations": decode_json(row["citations_json"], []),
                "metadata": decode_json(row["metadata_json"], {}),
                "created_at": row["created_at"],
            }
        )
    return output


def history_for_agent(messages: list[dict[str, Any]], limit: int = 8) -> list[dict[str, str]]:
    recent = messages[-max(0, min(20, int(limit or 8))) :]
    return [
        {"role": str(message["role"]), "content": str(message["content"])}
        for message in recent
        if message.get("role") in VALID_ROLES and message.get("content")
    ]
