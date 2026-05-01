from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from gumroad_merchant.database import connect_readonly, row_to_dict
from gumroad_merchant.help_corpus import DEFAULT_HELP_CATEGORY, HELP_CORPUS_VERSION


STOPWORDS = {
    "a",
    "about",
    "am",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "get",
    "go",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "what",
    "when",
    "where",
    "why",
    "with",
    "you",
}

SYNONYMS = {
    "paid": ["payout", "payouts"],
    "pay": ["payout", "payouts"],
    "payment": ["payout", "processor"],
    "payments": ["payout", "processor"],
    "fee": ["fees", "pricing"],
    "fees": ["fee", "pricing"],
    "refund": ["refunds", "balance"],
    "refunds": ["refund", "balance"],
    "dispute": ["chargeback", "chargebacks"],
    "disputes": ["chargeback", "chargebacks"],
    "chargeback": ["chargebacks", "dispute"],
    "chargebacks": ["chargeback", "dispute"],
    "tax": ["taxes", "merchant", "record"],
    "taxes": ["tax", "merchant", "record"],
    "stripe": ["processor"],
    "paypal": ["processor"],
    "reduce": ["lower", "chargeback", "chargebacks"],
    "lower": ["reduce"],
    "export": ["csv", "dashboard"],
    "exports": ["csv", "dashboard"],
}


def normalize_limit(limit: int | str | None) -> int:
    try:
        value = int(limit or 5)
    except (TypeError, ValueError):
        value = 5
    return max(1, min(12, value))


def query_tokens(query: str) -> list[str]:
    tokens = []
    for token in re.findall(r"[a-z0-9]+", (query or "").lower()):
        if len(token) <= 1 or token in STOPWORDS:
            continue
        tokens.append(token)
        tokens.extend(SYNONYMS.get(token, []))
    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            deduped.append(token)
            seen.add(token)
    return deduped[:14]


def fts_query(query: str) -> str:
    tokens = query_tokens(query)
    if not tokens:
        return ""
    return " OR ".join(f"{token}*" for token in tokens)


def decode_examples(value: str) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed if str(item).strip()]


def format_help_chunk(row: sqlite3.Row, rank: float | None = None) -> dict[str, Any]:
    item = row_to_dict(row)
    examples = decode_examples(item.pop("example_questions_json", "[]"))
    item["example_questions"] = examples
    item["excerpt"] = item["content"]
    item["source_url"] = item["url"]
    item["citation_label"] = f"{item['title']} - {item['section_heading']}"
    if rank is not None:
        item["rank"] = rank
    return item


def rerank_results(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lowered = (query or "").lower()

    def boost(item: dict[str, Any]) -> float:
        chunk_id = str(item.get("chunk_id", ""))
        score = float(item.get("rank", 0.0))
        if any(term in lowered for term in ("fee", "pricing", "direct", "discover")) and item["doc_id"] == "pricing-fees-and-taxes":
            score -= 4.0
        if any(term in lowered for term in ("when", "paid", "payout timing", "friday")) and chunk_id.endswith("::payout-period"):
            score -= 5.0
        if any(term in lowered for term in ("dashboard", "export", "csv", "balance activity")) and chunk_id.endswith("::payouts-dashboard-navigation"):
            score -= 5.0
        if any(term in lowered for term in ("stripe", "paypal", "processor")) and "stripe-paypal" in chunk_id:
            score -= 4.0
        if "chargeback" in lowered and any(term in lowered for term in ("reduce", "lower", "prevent", "avoid")) and chunk_id.endswith("::lower-chargeback-rate"):
            score -= 8.0
        if any(term in lowered for term in ("refund", "negative balance", "balance")) and chunk_id.endswith("::credits-refunds-chargebacks"):
            score -= 5.0
        if any(term in lowered for term in ("where", "find", "docs", "help center", "sales analytics")) and item["doc_id"] == "help-center-section-map":
            score -= 5.0
        return score

    return sorted(results, key=lambda item: (boost(item), item["title"], item["section_heading"]))


def search_with_fts(conn: sqlite3.Connection, query: str, category: str, limit: int) -> list[dict[str, Any]]:
    normalized = fts_query(query)
    if not normalized:
        return []
    rows = conn.execute(
        """
        SELECT
            c.chunk_id,
            c.doc_id,
            c.section_id,
            c.title,
            c.section_heading,
            c.url,
            c.category,
            c.source_type,
            c.content,
            c.example_questions_json,
            bm25(help_doc_chunks_fts) AS rank
        FROM help_doc_chunks_fts
        JOIN help_doc_chunks c ON c.chunk_id = help_doc_chunks_fts.chunk_id
        WHERE help_doc_chunks_fts MATCH ?
          AND (? = 'all' OR c.category = ?)
        ORDER BY rank ASC, c.title ASC, c.section_heading ASC
        LIMIT ?
        """,
        (normalized, category, category, limit),
    ).fetchall()
    return [format_help_chunk(row, rank=float(row["rank"])) for row in rows]


def search_with_like(conn: sqlite3.Connection, query: str, category: str, limit: int) -> list[dict[str, Any]]:
    tokens = query_tokens(query)
    if not tokens:
        return []
    like_terms = [f"%{token}%" for token in tokens[:8]]
    conditions = " OR ".join(["LOWER(title || ' ' || section_heading || ' ' || content) LIKE ?"] * len(like_terms))
    rows = conn.execute(
        f"""
        SELECT
            chunk_id,
            doc_id,
            section_id,
            title,
            section_heading,
            url,
            category,
            source_type,
            content,
            example_questions_json
        FROM help_doc_chunks
        WHERE ({conditions})
          AND (? = 'all' OR category = ?)
        ORDER BY title ASC, section_heading ASC
        LIMIT ?
        """,
        (*like_terms, category, category, limit),
    ).fetchall()
    return [format_help_chunk(row) for row in rows]


def search_gumroad_help_docs_tool(
    db_path: Path | str,
    query: str,
    category: str = DEFAULT_HELP_CATEGORY,
    limit: int | str = 5,
) -> list[dict[str, Any]]:
    normalized_category = (category or DEFAULT_HELP_CATEGORY).strip().lower() or DEFAULT_HELP_CATEGORY
    if normalized_category not in {DEFAULT_HELP_CATEGORY, "all"}:
        normalized_category = DEFAULT_HELP_CATEGORY
    max_results = normalize_limit(limit)
    with closing(connect_readonly(db_path)) as conn:
        try:
            results = search_with_fts(conn, query, normalized_category, max_results * 3)
        except sqlite3.OperationalError:
            results = []
        if not results:
            results = search_with_like(conn, query, normalized_category, max_results * 3)
    return rerank_results(query, results)[:max_results]


def get_help_doc_inventory_tool(db_path: Path | str) -> dict[str, Any]:
    with closing(connect_readonly(db_path)) as conn:
        doc_count = conn.execute("SELECT COUNT(*) AS n FROM help_docs").fetchone()["n"]
        chunk_count = conn.execute("SELECT COUNT(*) AS n FROM help_doc_chunks").fetchone()["n"]
        categories = conn.execute(
            """
            SELECT category, COUNT(*) AS chunks
            FROM help_doc_chunks
            GROUP BY category
            ORDER BY category
            """
        ).fetchall()
        docs = conn.execute(
            """
            SELECT doc_id, title, url, category, source_type, seeded_at
            FROM help_docs
            ORDER BY doc_id
            """
        ).fetchall()
    return {
        "corpus_version": HELP_CORPUS_VERSION,
        "doc_count": int(doc_count),
        "chunk_count": int(chunk_count),
        "categories": [row_to_dict(row) for row in categories],
        "docs": [row_to_dict(row) for row in docs],
        "access": "seeded official Gumroad help/pricing corpus in local SQLite FTS; read-only",
    }
