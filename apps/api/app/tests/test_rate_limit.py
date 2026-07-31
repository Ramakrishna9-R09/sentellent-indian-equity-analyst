from __future__ import annotations

import time

from app.services.rate_limit import TokenBucket


def test_token_bucket_allows_initial_requests() -> None:
    bucket = TokenBucket(capacity=5, refill_rate=1.0)
    for _ in range(5):
        assert bucket.consume() is True


def test_token_bucket_rejects_when_empty() -> None:
    bucket = TokenBucket(capacity=3, refill_rate=0.1)
    for _ in range(3):
        bucket.consume()
    assert bucket.consume() is False


def test_token_bucket_refills_over_time() -> None:
    bucket = TokenBucket(capacity=2, refill_rate=100.0)
    bucket.consume()
    bucket.consume()
    assert bucket.consume() is False
    time.sleep(0.05)
    assert bucket.consume() is True
