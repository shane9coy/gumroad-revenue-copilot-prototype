from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from gumroad_merchant.settings import PROJECT_ROOT


_trace_context: ContextVar[dict[str, Any]] = ContextVar("gumroad_merchant_trace_context", default={})


def trace_path() -> Path:
    configured = os.environ.get("GUMROAD_MERCHANT_TRACE_PATH", "artifacts/agent_traces/gumroad_agent_traces.jsonl")
    path = Path(configured)
    return path if path.is_absolute() else PROJECT_ROOT / path


def set_trace_context(**values: Any):
    context = {key: value for key, value in values.items() if value is not None}
    return _trace_context.set(context)


def clear_trace_context(token) -> None:
    _trace_context.reset(token)


def trace_context() -> dict[str, Any]:
    return dict(_trace_context.get({}))


def _safe_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= 500 else f"{value[:497]}..."
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in list(value)[:20]]
    return str(value)


def payload_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return {
            "type": "dict",
            "keys": sorted(str(key) for key in value.keys())[:20],
            "item_count": len(value),
        }
    if isinstance(value, list):
        return {"type": "list", "item_count": len(value)}
    return {"type": type(value).__name__}


def trace_event(event: str, **fields: Any) -> None:
    path = trace_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **trace_context(),
        **{key: _safe_value(value) for key, value in fields.items() if value is not None},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")


@contextmanager
def trace_span(event: str, **fields: Any) -> Iterator[None]:
    started = time.perf_counter()
    trace_event(f"{event}.start", **fields)
    try:
        yield
    except Exception as exc:
        trace_event(
            f"{event}.error",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            error=f"{type(exc).__name__}: {exc}",
            **fields,
        )
        raise
    else:
        trace_event(
            f"{event}.end",
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            **fields,
        )
