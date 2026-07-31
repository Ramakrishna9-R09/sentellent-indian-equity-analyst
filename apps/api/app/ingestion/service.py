from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Connection, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine
from app.ingestion.sources import SourcePayload, fetch_all_sources
from app.models import (
    ArticleSignal,
    DocumentChunk,
    EmbeddingCache,
    FundamentalSnapshot,
    IngestionJob,
    SourceDocument,
    Stock,
    StockFeatureSnapshot,
    StockSignalDaily,
    UserFollow,
)
from app.services.archive import archive_source_payload
from app.services.embeddings import EmbeddingService

settings = get_settings()


class ArticleTag(BaseModel):
    sentiment: str = Field(pattern="^(positive|neutral|negative|mixed)$")
    impact: str = Field(pattern="^(low|medium|high)$")
    event_type: str = Field(max_length=64)
    confidence: float = Field(ge=0, le=1)
    supporting_excerpt: str = Field(min_length=1, max_length=500)
    mentioned_tickers: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("confidence", mode="before")
    @classmethod
    def coerce_confidence(cls, value):
        if isinstance(value, str):
            return float(value)
        return value

    @field_validator("mentioned_tickers", mode="before")
    @classmethod
    def coerce_mentioned_tickers(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _chunk_text(text_value: str, chunk_size: int = 900, overlap: int = 140) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text_value).strip()
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        if end < len(cleaned):
            boundary = cleaned.rfind(". ", start, end)
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(cleaned):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _sentiment_score(sentiment: str) -> Decimal:
    return {
        "positive": Decimal("1"),
        "neutral": Decimal("0"),
        "negative": Decimal("-1"),
        "mixed": Decimal("0"),
    }.get(sentiment, Decimal("0"))


_TICKER_ALIASES = {
    "reliance": "RELIANCE",
    "reliance industries": "RELIANCE",
    "tcs": "TCS",
    "tata consultancy": "TCS",
    "hdfc bank": "HDFCBANK",
    "hdfcbank": "HDFCBANK",
    "infosys": "INFY",
    "infy": "INFY",
    "itc": "ITC",
    "hcl": "HCLTECH",
    "hcltech": "HCLTECH",
    "wipro": "WIPRO",
    "tech mahindra": "TECHM",
    "techm": "TECHM",
    "lti": "LTIM",
    "ltimindtree": "LTIM",
    "larsen": "LT",
    "lt": "LT",
    "bajaj finance": "BAJFINANCE",
    "bajaj finserv": "BAJAJFINSV",
    "maruti": "MARUTI",
    "sbi": "SBIN",
    "state bank of india": "SBIN",
    "hul": "HINDUNILVR",
    "hindustan unilever": "HINDUNILVR",
    "tata motors": "TATAMOTORS",
    "adani enterprises": "ADANIENT",
    "adani": "ADANIENT",
    "asian paints": "ASIANPAINT",
    "bharti airtel": "BHARTIARTL",
    "airtel": "BHARTIARTL",
    "titan": "TITAN",
    "nestle": "NESTLEIND",
    "axis bank": "AXISBANK",
    "icici bank": "ICICIBANK",
    "kotak": "KOTAKBANK",
    "sun pharma": "SUNPHARMA",
    "cipla": "CIPLA",
    "dr reddy": "DRREDDY",
}


def _mentioned_tickers(payload: SourcePayload) -> list[str]:
    text_value = f"{payload.title} {payload.content}".lower()
    found: list[str] = []
    for alias, symbol in _TICKER_ALIASES.items():
        if alias in text_value and symbol not in found:
            found.append(symbol)
    return found


def _heuristic_article_tag(payload: SourcePayload) -> ArticleTag:
    text_value = f"{payload.title} {payload.content}".lower()
    positives = ("growth", "profit", "beats", "gain", "upbeat", "order win", "dividend", "buyback")
    negatives = ("debt", "loss", "fall", "decline", "probe", "downgrade", "risk", "lawsuit")
    positive_hits = sum(term in text_value for term in positives)
    negative_hits = sum(term in text_value for term in negatives)
    if positive_hits and negative_hits:
        sentiment = "mixed"
    elif positive_hits > negative_hits:
        sentiment = "positive"
    elif negative_hits > positive_hits:
        sentiment = "negative"
    else:
        sentiment = "neutral"
    impact = "high" if any(term in text_value for term in ("results", "earnings", "merger", "debt")) else "medium"
    event_type = "earnings" if any(term in text_value for term in ("result", "earnings", "profit")) else "news"
    return ArticleTag(
        sentiment=sentiment,
        impact=impact,
        event_type=event_type,
        confidence=0.55,
        supporting_excerpt=(payload.excerpt or payload.content)[:480],
        mentioned_tickers=_mentioned_tickers(payload),
    )


def tag_article(payload: SourcePayload) -> ArticleTag:
    """Use a structured LLM when configured, with a deterministic safe fallback for local work."""
    if not settings.openai_api_key and not settings.groq_api_key:
        return _heuristic_article_tag(payload)
    try:
        from langchain_openai import ChatOpenAI

        if settings.groq_api_key:
            model = ChatOpenAI(
                model=settings.groq_chat_model,
                api_key=settings.groq_api_key,
                base_url=settings.groq_base_url,
                temperature=0,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
        else:
            model = ChatOpenAI(
                model=settings.openai_chat_model,
                api_key=settings.openai_api_key,
                temperature=0,
                model_kwargs={"response_format": {"type": "json_object"}},
            )
        prompt = (
            "Classify this Indian-market article. Return ONLY a JSON object with exactly these keys: "
            "sentiment (one of positive|neutral|negative|mixed), impact (one of low|medium|high), "
            "event_type (short label), confidence (a number between 0 and 1), "
            "supporting_excerpt (a short quoted sentence from the article), "
            'mentioned_tickers (an array of uppercase NSE ticker symbols of the stocks the article '
            "talks about, e.g. [\"RELIANCE\", \"TCS\"], empty array if none). "
            f"Title: {payload.title}\nContent: {payload.content[:6000]}"
        )
        raw = model.invoke(prompt).content
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1])
        return ArticleTag.model_validate(data)
    except Exception:
        return _heuristic_article_tag(payload)


def enqueue_refresh(db: Session, stock_id: uuid.UUID, trigger: str) -> IngestionJob:
    existing = db.scalar(
        select(IngestionJob)
        .where(IngestionJob.stock_id == stock_id, IngestionJob.status.in_(("queued", "running")))
        .order_by(IngestionJob.created_at.desc())
    )
    if existing:
        return existing
    job = IngestionJob(
        stock_id=stock_id,
        trigger=trigger,
        status="queued",
        correlation_id=uuid.uuid4().hex,
        next_attempt_at=_utcnow(),
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(IngestionJob)
            .where(IngestionJob.stock_id == stock_id, IngestionJob.status.in_(("queued", "running")))
            .order_by(IngestionJob.created_at.desc())
        )
        if existing is None:
            raise
        return existing
    db.refresh(job)
    return job


def enqueue_due_refreshes(db: Session) -> int:
    """Queue only stale followed tickers; the unique active-job index makes this idempotent."""
    cutoff = _utcnow() - timedelta(hours=min(settings.news_refresh_hours, settings.price_refresh_hours))
    followed_stock_ids = list(
        db.scalars(
            select(UserFollow.stock_id)
            .where(UserFollow.refresh_enabled.is_(True))
            .distinct()
        )
    )
    queued = 0
    for stock_id in followed_stock_ids:
        latest_completed_at = db.scalar(
            select(IngestionJob.completed_at)
            .where(IngestionJob.stock_id == stock_id, IngestionJob.status == "succeeded")
            .order_by(IngestionJob.completed_at.desc())
            .limit(1)
        )
        if latest_completed_at is None or latest_completed_at < cutoff:
            enqueue_refresh(db, stock_id, "scheduled")
            queued += 1
    return queued


def claim_next_job(db: Session) -> IngestionJob | None:
    now = _utcnow()
    job = db.scalar(
        select(IngestionJob)
        .where(
            IngestionJob.status == "queued",
            or_(IngestionJob.next_attempt_at.is_(None), IngestionJob.next_attempt_at <= now),
        )
        .order_by(IngestionJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if job is None:
        return None
    job.status = "running"
    job.attempt += 1
    job.started_at = now
    job.last_error = None
    db.commit()
    db.refresh(job)
    return job


def _acquire_stock_lock(connection: Connection, stock_id: uuid.UUID) -> bool:
    return bool(
        connection.execute(
            text("SELECT pg_try_advisory_lock(hashtext(CAST(:stock_id AS text)))"),
            {"stock_id": str(stock_id)},
        ).scalar()
    )


def _release_stock_lock(connection: Connection, stock_id: uuid.UUID) -> None:
    connection.execute(
        text("SELECT pg_advisory_unlock(hashtext(CAST(:stock_id AS text)))"),
        {"stock_id": str(stock_id)},
    )


def _embed_cached(db: Session, text_value: str, service: EmbeddingService) -> list[float]:
    content_sha = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
    cached = db.scalar(
        select(EmbeddingCache).where(
            EmbeddingCache.content_sha256 == content_sha,
            EmbeddingCache.embedding_model == service.model_name,
        )
    )
    if cached is not None:
        return cached.embedding
    embedding = service.embed(text_value)
    db.add(
        EmbeddingCache(
            content_sha256=content_sha,
            embedding_model=service.model_name,
            embedding=embedding,
        )
    )
    db.flush()
    return embedding


def _store_fundamentals(
    db: Session,
    *,
    stock: Stock,
    source_document: SourceDocument,
    payload: SourcePayload,
) -> None:
    as_of = payload.published_at.date() if payload.published_at else date.today()
    for metric_key, (raw_label, raw_value, normalized, unit) in payload.metrics.items():
        exists = db.scalar(
            select(FundamentalSnapshot.id).where(
                FundamentalSnapshot.stock_id == stock.id,
                FundamentalSnapshot.metric_key == metric_key,
                FundamentalSnapshot.as_of_date == as_of,
                FundamentalSnapshot.source_document_id == source_document.id,
            )
        )
        if exists:
            continue
        db.add(
            FundamentalSnapshot(
                stock_id=stock.id,
                source_document_id=source_document.id,
                metric_key=metric_key,
                raw_label=raw_label,
                raw_value=raw_value,
                normalized_value=normalized,
                normalized_unit=unit,
                currency="INR" if unit == "INR" or metric_key.endswith("_inr") else "N/A",
                as_of_date=as_of,
            )
        )


def _store_chunks(
    db: Session,
    *,
    stock: Stock,
    source_document: SourceDocument,
    service: EmbeddingService,
) -> int:
    created = 0
    for index, text_value in enumerate(_chunk_text(source_document.content)):
        text_sha = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
        existing = db.scalar(
            select(DocumentChunk.id).where(
                DocumentChunk.source_document_id == source_document.id,
                DocumentChunk.chunk_index == index,
                DocumentChunk.chunker_version == "v1",
            )
        )
        if existing:
            continue
        db.add(
            DocumentChunk(
                source_document_id=source_document.id,
                stock_id=stock.id,
                chunk_index=index,
                chunker_version="v1",
                embedding_model=service.model_name,
                text=text_value,
                text_sha256=text_sha,
                token_estimate=max(1, len(text_value.split())),
                embedding=_embed_cached(db, text_value, service),
            )
        )
        created += 1
    return created


def _store_article_signal(
    db: Session, *, stock: Stock, source_document: SourceDocument, payload: SourcePayload
) -> None:
    if payload.source_type != "news":
        return
    existing = db.scalar(
        select(ArticleSignal.id).where(
            ArticleSignal.source_document_id == source_document.id,
            ArticleSignal.stock_id == stock.id,
            ArticleSignal.extraction_version == "v1",
        )
    )
    if existing:
        return
    tag = tag_article(payload)
    db.add(
        ArticleSignal(
            source_document_id=source_document.id,
            stock_id=stock.id,
            extraction_version="v1",
            sentiment=tag.sentiment,
            impact=tag.impact,
            event_type=tag.event_type,
            confidence=Decimal(str(tag.confidence)),
            supporting_excerpt=tag.supporting_excerpt,
            mentioned_tickers=tag.mentioned_tickers,
        )
    )
    signal_day = (payload.published_at or _utcnow()).date()
    insert_stmt = insert(StockSignalDaily).values(
        id=uuid.uuid4(),
        stock_id=stock.id,
        signal_date=signal_day,
        article_count=1,
        sentiment_score=_sentiment_score(tag.sentiment),
    )
    db.execute(
        insert_stmt.on_conflict_do_update(
            constraint="uq_stock_signal_daily",
            set_={
                "article_count": StockSignalDaily.article_count + 1,
                "sentiment_score": StockSignalDaily.sentiment_score + _sentiment_score(tag.sentiment),
                "updated_at": func.now(),
            },
        )
    )


def _latest_metrics(db: Session, stock_id: uuid.UUID) -> dict[str, FundamentalSnapshot]:
    snapshots = list(
        db.scalars(
            select(FundamentalSnapshot)
            .where(FundamentalSnapshot.stock_id == stock_id)
            .order_by(FundamentalSnapshot.as_of_date.desc(), FundamentalSnapshot.created_at.desc())
        )
    )
    latest: dict[str, FundamentalSnapshot] = {}
    for snapshot in snapshots:
        latest.setdefault(snapshot.metric_key, snapshot)
    return latest


def _bounded(value: Decimal | float | None) -> Decimal | None:
    if value is None:
        return None
    return max(Decimal("0"), min(Decimal("100"), Decimal(str(value))))


def _refresh_feature_snapshot(db: Session, stock_id: uuid.UUID) -> None:
    metrics = _latest_metrics(db, stock_id)

    def value(key: str) -> Decimal | None:
        snapshot = metrics.get(key)
        return snapshot.normalized_value if snapshot else None

    roce = value("roce")
    roe = value("roe")
    debt = value("debt_to_equity")
    yield_value = value("dividend_yield")
    pe = value("stock_pe")
    change = value("price_change_5d_pct")
    quality = _bounded(((roce or 0) + (roe or 0)) / 2) if roce is not None or roe is not None else None
    income = _bounded((yield_value or 0) * 10) if yield_value is not None else None
    value_score = _bounded(100 - min(pe or Decimal("100"), Decimal("100"))) if pe is not None else None
    momentum = _bounded(50 + (change or 0) * 4) if change is not None else None
    risk = _bounded(100 - min((debt or 0) * 30, Decimal("100"))) if debt is not None else None
    sentiment = db.scalar(
        select(func.coalesce(func.sum(StockSignalDaily.sentiment_score), 0)).where(
            StockSignalDaily.stock_id == stock_id,
            StockSignalDaily.signal_date >= date.today() - timedelta(days=30),
        )
    )
    sentiment_score = _bounded(50 + Decimal(str(sentiment or 0)) * 5)
    source_map = {
        key: str(snapshot.source_document_id)
        for key, snapshot in metrics.items()
        if snapshot.normalized_value is not None
    }
    existing = db.scalar(
        select(StockFeatureSnapshot).where(
            StockFeatureSnapshot.stock_id == stock_id,
            StockFeatureSnapshot.as_of_date == date.today(),
        )
    )
    values = {
        "quality_score": quality,
        "income_score": income,
        "value_score": value_score,
        "momentum_score": momentum,
        "risk_score": risk,
        "sentiment_score": sentiment_score,
        "debt_to_equity": debt,
        "source_map": source_map,
    }
    if existing:
        for key, field_value in values.items():
            setattr(existing, key, field_value)
    else:
        db.add(StockFeatureSnapshot(stock_id=stock_id, as_of_date=date.today(), **values))


def _store_new_payload(
    db: Session, *, stock: Stock, payload: SourcePayload, service: EmbeddingService
) -> tuple[bool, int]:
    existing = db.scalar(
        select(SourceDocument).where(SourceDocument.fingerprint == payload.fingerprint)
    )
    if existing:
        return False, 0
    source = SourceDocument(
        stock_id=stock.id,
        source_type=payload.source_type,
        publisher=payload.publisher,
        canonical_url=payload.canonical_url,
        title=payload.title,
        content=payload.content,
        excerpt=payload.excerpt,
        published_at=payload.published_at,
        content_sha256=payload.content_sha256,
        fingerprint=payload.fingerprint,
        s3_key=archive_source_payload(stock.symbol, payload),
    )
    db.add(source)
    db.flush()
    _store_fundamentals(db, stock=stock, source_document=source, payload=payload)
    chunk_count = _store_chunks(db, stock=stock, source_document=source, service=service)
    _store_article_signal(db, stock=stock, source_document=source, payload=payload)
    return True, chunk_count


def process_job(db: Session, job: IngestionJob) -> None:
    stock = db.get(Stock, job.stock_id)
    if stock is None:
        raise ValueError("Stock does not exist")
    with engine.connect() as lock_connection:
        if not _acquire_stock_lock(lock_connection, stock.id):
            job.status = "queued"
            job.next_attempt_at = _utcnow() + timedelta(seconds=30)
            db.commit()
            return
        try:
            payloads, connector_errors = fetch_all_sources(stock)
            if not payloads:
                raise RuntimeError("No source payload was returned. " + " | ".join(connector_errors))
            service = EmbeddingService()
            inserted_sources = 0
            inserted_chunks = 0
            for payload in payloads:
                inserted, chunks = _store_new_payload(db, stock=stock, payload=payload, service=service)
                inserted_sources += int(inserted)
                inserted_chunks += chunks
            _refresh_feature_snapshot(db, stock.id)
            job.status = "succeeded"
            job.completed_at = _utcnow()
            job.last_error = (
                f"{inserted_sources} new sources, {inserted_chunks} chunks. "
                + ("Connector warnings: " + " | ".join(connector_errors) if connector_errors else "")
            )
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            _release_stock_lock(lock_connection, stock.id)
            lock_connection.commit()


def mark_job_failure(db: Session, job_id: uuid.UUID, error: Exception) -> None:
    job = db.get(IngestionJob, job_id)
    if job is None:
        return
    job.last_error = str(error)[:2000]
    if job.attempt >= settings.ingestion_max_attempts:
        job.status = "failed"
        job.completed_at = _utcnow()
    else:
        job.status = "queued"
        job.next_attempt_at = _utcnow() + timedelta(minutes=2 ** min(job.attempt, 5))
    db.commit()


def run_one_job(db: Session) -> IngestionJob | None:
    job = claim_next_job(db)
    if job is None:
        return None
    try:
        process_job(db, job)
    except Exception as exc:
        mark_job_failure(db, job.id, exc)
    return db.get(IngestionJob, job.id)
