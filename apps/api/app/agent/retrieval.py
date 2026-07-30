from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk, SourceDocument, Stock, UserFollow
from app.services.embeddings import EmbeddingService


@dataclass
class Evidence:
    chunk_id: UUID
    source_document_id: UUID
    stock_id: UUID
    stock_symbol: str
    title: str
    publisher: str
    url: str
    published_at: object
    excerpt: str
    text: str
    score: float


def followed_stocks(db: Session, user_id: UUID) -> list[Stock]:
    return list(
        db.scalars(
            select(Stock)
            .join(UserFollow, UserFollow.stock_id == Stock.id)
            .where(UserFollow.user_id == user_id)
            .order_by(Stock.symbol)
        )
    )


def resolve_tickers(db: Session, user_id: UUID, question: str) -> list[Stock]:
    candidates = followed_stocks(db, user_id)
    lower = question.lower()
    matched = [
        stock
        for stock in candidates
        if stock.symbol.lower() in lower
        or stock.company_name.lower() in lower
        or stock.company_name.split()[0].lower() in lower
    ]
    return matched or candidates


def retrieve_evidence(
    db: Session,
    *,
    stock_ids: list[UUID],
    question: str,
    limit: int = 8,
) -> list[Evidence]:
    if not stock_ids:
        return []
    embedding_service = EmbeddingService()
    query_embedding = embedding_service.embed(question)
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    rows = db.execute(
        select(DocumentChunk, SourceDocument, Stock, distance.label("distance"))
        .join(SourceDocument, SourceDocument.id == DocumentChunk.source_document_id)
        .join(Stock, Stock.id == DocumentChunk.stock_id)
        .where(
            DocumentChunk.stock_id.in_(stock_ids),
            DocumentChunk.embedding_model == embedding_service.model_name,
        )
        .order_by(distance)
        .limit(limit * 2)
    ).all()

    evidence: list[Evidence] = []
    seen_sources: set[UUID] = set()
    for chunk, source, stock, raw_distance in rows:
        if source.id in seen_sources:
            continue
        seen_sources.add(source.id)
        evidence.append(
            Evidence(
                chunk_id=chunk.id,
                source_document_id=source.id,
                stock_id=stock.id,
                stock_symbol=stock.symbol,
                title=source.title,
                publisher=source.publisher,
                url=source.canonical_url,
                published_at=source.published_at,
                excerpt=(source.excerpt or chunk.text)[:500],
                text=chunk.text,
                score=max(0.0, 1.0 - float(raw_distance)),
            )
        )
        if len(evidence) == limit:
            break
    return evidence


def source_evidence(db: Session, source_ids: list[str]) -> list[Evidence]:
    if not source_ids:
        return []
    rows = db.execute(
        select(SourceDocument, Stock)
        .join(Stock, Stock.id == SourceDocument.stock_id)
        .where(SourceDocument.id.in_(source_ids))
    ).all()
    return [
        Evidence(
            chunk_id=source.id,
            source_document_id=source.id,
            stock_id=stock.id,
            stock_symbol=stock.symbol,
            title=source.title,
            publisher=source.publisher,
            url=source.canonical_url,
            published_at=source.published_at,
            excerpt=(source.excerpt or source.content)[:500],
            text=source.content,
            score=1.0,
        )
        for source, stock in rows
    ]
