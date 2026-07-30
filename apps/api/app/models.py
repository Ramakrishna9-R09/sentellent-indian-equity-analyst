from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AppUser(Timestamped, Base):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    provider_subject: Mapped[str | None] = mapped_column(String(255), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    picture_url: Mapped[str | None] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    sessions: Mapped[list[AuthSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    profile: Mapped[InvestorProfile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class AuthSession(Base):
    __tablename__ = "auth_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[AppUser] = relationship(back_populates="sessions")


class Stock(Timestamped, Base):
    __tablename__ = "stock"
    __table_args__ = (
        UniqueConstraint("symbol", "exchange", name="uq_stock_symbol_exchange"),
        Index("ix_stock_company_name", "company_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    exchange: Mapped[str] = mapped_column(String(8), nullable=False, default="NSE")
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    nse_id: Mapped[str | None] = mapped_column(String(64))
    bse_id: Mapped[str | None] = mapped_column(String(64))
    yfinance_symbol: Mapped[str | None] = mapped_column(String(64))
    sector: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserFollow(Timestamped, Base):
    __tablename__ = "user_follow"
    __table_args__ = (UniqueConstraint("user_id", "stock_id", name="uq_user_follow"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    refresh_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    stock: Mapped[Stock] = relationship()


class IngestionJob(Timestamped, Base):
    __tablename__ = "ingestion_job"
    __table_args__ = (
        Index("ix_ingestion_job_claim", "status", "next_attempt_at", "created_at"),
        Index("ix_ingestion_job_stock_status", "stock_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="queued")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)

    stock: Mapped[Stock] = relationship()


class SourceDocument(Timestamped, Base):
    __tablename__ = "source_document"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_source_document_fingerprint"),
        Index("ix_source_document_stock_published", "stock_id", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(Text)

    stock: Mapped[Stock] = relationship()
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="source_document", cascade="all, delete-orphan"
    )


class DocumentChunk(Timestamped, Base):
    __tablename__ = "document_chunk"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id", "chunk_index", "chunker_version", name="uq_document_chunk_identity"
        ),
        Index("ix_document_chunk_stock_created", "stock_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_document.id", ondelete="CASCADE"), index=True
    )
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunker_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    source_document: Mapped[SourceDocument] = relationship(back_populates="chunks")


class EmbeddingCache(Timestamped, Base):
    __tablename__ = "embedding_cache"
    __table_args__ = (UniqueConstraint("content_sha256", "embedding_model", name="uq_embedding_cache"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)


class FundamentalSnapshot(Timestamped, Base):
    __tablename__ = "fundamental_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "stock_id", "metric_key", "as_of_date", "source_document_id", name="uq_fundamental_snapshot"
        ),
        Index("ix_fundamental_snapshot_stock_metric", "stock_id", "metric_key", "as_of_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_document.id", ondelete="CASCADE"), index=True
    )
    metric_key: Mapped[str] = mapped_column(String(128), nullable=False)
    raw_label: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_value: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    normalized_unit: Mapped[str | None] = mapped_column(String(64))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    as_of_date: Mapped[datetime | None] = mapped_column(Date)


class ArticleSignal(Timestamped, Base):
    __tablename__ = "article_signal"
    __table_args__ = (
        UniqueConstraint(
            "source_document_id", "stock_id", "extraction_version", name="uq_article_signal"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_document.id", ondelete="CASCADE"), index=True
    )
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    extraction_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    sentiment: Mapped[str] = mapped_column(String(16), nullable=False)
    impact: Mapped[str] = mapped_column(String(16), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    supporting_excerpt: Mapped[str] = mapped_column(Text, nullable=False)


class StockSignalDaily(Timestamped, Base):
    __tablename__ = "stock_signal_daily"
    __table_args__ = (UniqueConstraint("stock_id", "signal_date", name="uq_stock_signal_daily"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    signal_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sentiment_score: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)


class InvestorProfile(Timestamped, Base):
    __tablename__ = "investor_profile"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True
    )
    profile_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    persona_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    user: Mapped[AppUser] = relationship(back_populates="profile")


class ProfileFact(Timestamped, Base):
    __tablename__ = "profile_fact"
    __table_args__ = (Index("ix_profile_fact_user_key", "user_id", "key", "state"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    chat_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("chat_message.id", ondelete="SET NULL"), index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False, default=1)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ChatThread(Timestamped, Base):
    __tablename__ = "chat_thread"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    graph_checkpoint_id: Mapped[str | None] = mapped_column(String(255))


class ChatMessage(Base):
    __tablename__ = "chat_message"
    __table_args__ = (Index("ix_chat_message_thread_created", "thread_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_thread.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StockFeatureSnapshot(Timestamped, Base):
    __tablename__ = "stock_feature_snapshot"
    __table_args__ = (UniqueConstraint("stock_id", "as_of_date", name="uq_stock_feature_snapshot"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stock_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stock.id", ondelete="CASCADE"), index=True)
    as_of_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    income_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    value_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    momentum_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    source_map: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


class AnswerAudit(Base):
    __tablename__ = "answer_audit"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id", ondelete="CASCADE"), index=True)
    thread_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_thread.id", ondelete="SET NULL"))
    question: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    cited_source_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
