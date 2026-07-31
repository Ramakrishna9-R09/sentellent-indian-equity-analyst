from __future__ import annotations

import time

from app.services.cache import ResponseCache


def test_cache_set_and_get() -> None:
    from starlette.responses import Response

    cache = ResponseCache(max_size=10, default_ttl=60)
    response = Response(content=b"hello", status_code=200)
    cache.set("key1", response)
    result = cache.get("key1")
    assert result is not None
    assert result.status_code == 200


def test_cache_miss_returns_none() -> None:
    cache = ResponseCache(max_size=10, default_ttl=60)
    assert cache.get("nonexistent") is None


def test_cache_expiry() -> None:
    from starlette.responses import Response

    cache = ResponseCache(max_size=10, default_ttl=0)
    response = Response(content=b"expire", status_code=200)
    cache.set("key1", response)
    time.sleep(0.01)
    assert cache.get("key1") is None


def test_cache_lru_eviction() -> None:
    from starlette.responses import Response

    cache = ResponseCache(max_size=2, default_ttl=60)
    cache.set("a", Response(content=b"a", status_code=200))
    cache.set("b", Response(content=b"b", status_code=200))
    cache.set("c", Response(content=b"c", status_code=200))
    assert cache.get("a") is None
    assert cache.get("b") is not None
    assert cache.get("c") is not None


def test_cache_invalidate_all() -> None:
    from starlette.responses import Response

    cache = ResponseCache(max_size=10, default_ttl=60)
    cache.set("x", Response(content=b"x", status_code=200))
    cache.set("y", Response(content=b"y", status_code=200))
    count = cache.invalidate()
    assert count == 2
    assert cache.get("x") is None
    assert cache.get("y") is None


def test_cache_invalidate_by_prefix() -> None:
    from starlette.responses import Response

    cache = ResponseCache(max_size=10, default_ttl=60)
    cache.set("/api/stocks/search?q=TCS", Response(content=b"a", status_code=200))
    cache.set("/api/sources/123", Response(content=b"b", status_code=200))
    count = cache.invalidate("/api/stocks")
    assert count == 1
    assert cache.get("/api/stocks/search?q=TCS") is None
    assert cache.get("/api/sources/123") is not None
