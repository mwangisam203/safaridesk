from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import time

from fastapi import HTTPException, Request, status

from app.core.config import settings


@dataclass(frozen=True)
class RateLimit:
    scope: str
    limit: int
    window_seconds: int


_hits: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()

    cloudflare_ip = request.headers.get("cf-connecting-ip")
    if cloudflare_ip:
        return cloudflare_ip.strip()

    if request.client:
        return request.client.host

    return "unknown"


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()


def check_rate_limit(request: Request, rule: RateLimit) -> None:
    if not settings.RATE_LIMIT_ENABLED:
        return

    now = time()
    key = f"{rule.scope}:{_client_id(request)}"
    cutoff = now - rule.window_seconds

    with _lock:
        bucket = _hits[key]
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= rule.limit:
            retry_after = max(1, int(rule.window_seconds - (now - bucket[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)


def rate_limit(scope: str, limit: int, window_seconds: int):
    rule = RateLimit(scope=scope, limit=limit, window_seconds=window_seconds)

    def dependency(request: Request) -> None:
        check_rate_limit(request, rule)

    return dependency
