from __future__ import annotations

import hashlib
import time
from collections import OrderedDict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class ResponseCache:
    """Simple in-memory LRU cache with TTL for GET responses."""

    def __init__(self, max_size: int = 256, default_ttl: int = 300) -> None:
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._store: OrderedDict[str, tuple[float, Response]] = OrderedDict()

    def _make_key(self, request: Request, user_id: str | None = None) -> str:
        parts = [request.url.path, str(request.url.query)]
        if user_id:
            parts.append(user_id)
        raw = "|".join(parts)
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> Response | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, response = entry
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return response

    def set(self, key: str, response: Response, ttl: int | None = None) -> None:
        expires_at = time.time() + (ttl or self._default_ttl)
        body = response.body
        cached = Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        self._store[key] = (expires_at, cached)
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def set_bytes(
        self,
        key: str,
        body: bytes,
        status_code: int,
        headers: dict[str, str],
        ttl: int | None = None,
    ) -> None:
        expires_at = time.time() + (ttl or self._default_ttl)
        cached = Response(content=body, status_code=status_code, headers=headers)
        self._store[key] = (expires_at, cached)
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def invalidate(self, prefix: str = "") -> int:
        if not prefix:
            count = len(self._store)
            self._store.clear()
            return count
        keys = [k for k in self._store if prefix in k]
        for k in keys:
            self._store.pop(k, None)
        return len(keys)


_cache = ResponseCache(max_size=256, default_ttl=60)


def get_cache() -> ResponseCache:
    return _cache


CACHE_CONTROL_HEADER = "public, max-age=60, stale-while-revalidate=30"
NO_CACHE_HEADER = "no-store, no-cache, must-revalidate"


class CacheMiddleware(BaseHTTPMiddleware):
    """Cache GET responses for public read-only endpoints."""

    _CACHED_PREFIXES = ("/api/stocks/search", "/api/sources")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "GET":
            response = await call_next(request)
            response.headers["Cache-Control"] = NO_CACHE_HEADER
            return response

        cache = get_cache()
        cacheable = any(request.url.path.startswith(p) for p in self._CACHED_PREFIXES)

        if cacheable:
            key = cache._make_key(request)
            cached = cache.get(key)
            if cached is not None:
                cached.headers["Cache-Control"] = CACHE_CONTROL_HEADER
                return cached

        response = await call_next(request)

        if cacheable and response.status_code == 200:
            if isinstance(response, Response) and hasattr(response, "body"):
                cache.set(key, response)
                response.headers["Cache-Control"] = CACHE_CONTROL_HEADER
                return response
            body = b"".join([chunk async for chunk in response.body_iterator])
            cache.set_bytes(
                key,
                body=body,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
            fresh = Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
            fresh.headers["Cache-Control"] = CACHE_CONTROL_HEADER
            return fresh

        return response
