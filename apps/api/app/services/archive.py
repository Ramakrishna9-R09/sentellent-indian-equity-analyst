from __future__ import annotations

import json
from datetime import UTC, datetime

from app.config import get_settings
from app.ingestion.sources import SourcePayload

settings = get_settings()


def archive_source_payload(stock_symbol: str, payload: SourcePayload) -> str | None:
    """Persist the exact ingested source payload when an archive bucket is configured."""
    if not settings.source_archive_bucket:
        return None

    import boto3

    published = payload.published_at or datetime.now(UTC)
    object_key = (
        f"raw-sources/stock={stock_symbol}/date={published.date().isoformat()}/"
        f"{payload.content_sha256}.json"
    )
    body = json.dumps(
        {
            "stock_symbol": stock_symbol,
            "source_type": payload.source_type,
            "publisher": payload.publisher,
            "canonical_url": payload.canonical_url,
            "title": payload.title,
            "content": payload.content,
            "excerpt": payload.excerpt,
            "published_at": payload.published_at.isoformat() if payload.published_at else None,
            "metrics": payload.metrics,
            "content_sha256": payload.content_sha256,
            "fingerprint": payload.fingerprint,
            "archived_at": datetime.now(UTC).isoformat(),
        },
        default=str,
        separators=(",", ":"),
    ).encode("utf-8")
    client = boto3.client("s3", region_name=settings.aws_region)
    client.put_object(
        Bucket=settings.source_archive_bucket,
        Key=object_key,
        Body=body,
        ContentType="application/json",
        ServerSideEncryption="AES256",
    )
    return object_key
