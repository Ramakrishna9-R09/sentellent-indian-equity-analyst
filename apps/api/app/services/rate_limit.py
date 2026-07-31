from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class TokenBucket:
    """Thread-safe token bucket for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self._lock = Lock()

    def consume(self) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting using a token bucket algorithm.

    Defaults: 60 requests per minute for general endpoints, 10 per minute for
    write-heavy endpoints (chat, follow).
    """

    _HEAVY_PATHS = ("/api/chat/", "/api/follows")

    def __init__(self, app, default_limit: int = 60, heavy_limit: int = 10) -> None:
        super().__init__(app)
        self._default_limit = default_limit
        self._heavy_limit = heavy_limit
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(default_limit, default_limit / 60.0)
        )
        self._heavy_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(heavy_limit, heavy_limit / 60.0)
        )
        self._last_cleanup = time.time()
        self._cleanup_interval = 300

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _maybe_cleanup(self) -> None:
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = now
            stale_keys = [
                k for k, b in self._buckets.items() if now - b.last_refill > 300
            ]
            for k in stale_keys:
                del self._buckets[k]
            stale_keys = [
                k for k, b in self._heavy_buckets.items() if now - b.last_refill > 300
            ]
            for k in stale_keys:
                del self._heavy_buckets[k]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        self._maybe_cleanup()

        if request.method == "GET":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        is_heavy = any(request.url.path.startswith(p) for p in self._HEAVY_PATHS)

        if is_heavy:
            bucket = self._heavy_buckets[client_ip]
            remaining = self._heavy_limit
        else:
            bucket = self._buckets[client_ip]
            remaining = self._default_limit

        if not bucket.consume():
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please slow down."},
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(remaining),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(remaining)
        response.headers["X-RateLimit-Remaining"] = str(max(0, int(bucket.tokens)))
        return response
