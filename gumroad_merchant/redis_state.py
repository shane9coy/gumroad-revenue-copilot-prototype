from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class RedisStatus:
    enabled: bool
    available: bool
    error: str | None = None


class RedisRuntime:
    def __init__(self, redis_url: str, namespace: str = "gumroad-merchant") -> None:
        self.redis_url = redis_url
        self.namespace = namespace
        self._client = None
        self._error: str | None = None

    def key(self, *parts: str) -> str:
        clean = ":".join(str(part).strip().replace(":", "-") for part in parts if str(part).strip())
        return f"{self.namespace}:{clean}"

    def client(self):
        if self._client is not None:
            return self._client
        try:
            import redis

            self._client = redis.Redis.from_url(
                self.redis_url,
                socket_connect_timeout=0.25,
                socket_timeout=0.5,
                decode_responses=True,
            )
            self._client.ping()
        except Exception as exc:  # Redis is optional in the demo.
            self._error = f"{type(exc).__name__}: {exc}"
            self._client = None
        return self._client

    def status(self) -> RedisStatus:
        client = self.client()
        return RedisStatus(enabled=bool(self.redis_url), available=client is not None, error=self._error)

    def touch_session(self, session_id: str, product_id: str, date_range: str, ttl_seconds: int = 86400) -> None:
        client = self.client()
        if client is None:
            return
        client.hset(
            self.key("session", session_id),
            mapping={
                "product_id": product_id,
                "date_range": date_range,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        client.expire(self.key("session", session_id), ttl_seconds)

    def rate_limit_hit(self, session_id: str, limit: int = 30, window_seconds: int = 60) -> bool:
        client = self.client()
        if client is None:
            return False
        key = self.key("rate", session_id)
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
        return int(count) > limit

    def in_flight_key(self, session_id: str, message: str) -> str:
        digest = hashlib.sha256(message.encode("utf-8")).hexdigest()[:16]
        return self.key("inflight", session_id, digest)

    def set_in_flight(
        self,
        session_id: str,
        message: str,
        ttl_seconds: int = 45,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        client = self.client()
        if client is None:
            return True
        value = json.dumps(
            {
                "started_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
            },
            ensure_ascii=True,
        )
        return bool(client.set(self.in_flight_key(session_id, message), value, nx=True, ex=ttl_seconds))

    def clear_in_flight(self, session_id: str, message: str) -> None:
        client = self.client()
        if client is not None:
            client.delete(self.in_flight_key(session_id, message))
