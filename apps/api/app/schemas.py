from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None = None
    picture_url: str | None = None


class StockResponse(BaseModel):
    id: UUID
    symbol: str
    exchange: str
    company_name: str
    sector: str | None = None
    yfinance_symbol: str | None = None


class FollowCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", max_length=8)
    company_name: str | None = Field(default=None, max_length=255)


class IngestionStatusResponse(BaseModel):
    id: UUID
    stock_id: UUID
    status: str
    trigger: str
    attempt: int
    correlation_id: str
    created_at: datetime
    completed_at: datetime | None = None
    last_error: str | None = None


class FollowResponse(BaseModel):
    id: UUID
    stock: StockResponse
    latest_job: IngestionStatusResponse | None = None


class ThreadCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ThreadResponse(BaseModel):
    id: UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=4000)


class CitationResponse(BaseModel):
    id: str
    source_document_id: UUID
    title: str
    publisher: str
    url: str
    published_at: datetime | None = None
    excerpt: str


class ClaimResponse(BaseModel):
    text: str
    citation_ids: list[str]


class RecommendationResponse(BaseModel):
    stock: StockResponse
    score: float
    reasons: list[str]
    citation_ids: list[str]


class ChatResponse(BaseModel):
    request_id: str
    answer_markdown: str
    claims: list[ClaimResponse]
    citations: list[CitationResponse]
    recommendations: list[RecommendationResponse] = []
    data_gaps: list[str] = []
    profile_updates: list[dict[str, Any]] = []
    retrieved_at: datetime


class ProfileFactResponse(BaseModel):
    id: UUID
    key: str
    value: dict[str, Any]
    state: str
    source_message_id: UUID | None = None
    created_at: datetime


class ProfileResponse(BaseModel):
    profile: dict[str, Any]
    version: int
    facts: list[ProfileFactResponse]


class ProfilePatch(BaseModel):
    risk_tolerance: str | None = Field(default=None, pattern="^(conservative|moderate|aggressive)$")
    objectives: list[str] | None = None
    avoid_high_debt: bool | None = None
    max_debt_to_equity: float | None = Field(default=None, ge=0, le=20)
    horizon: str | None = Field(default=None, max_length=64)
    excluded_sectors: list[str] | None = None


class AnswerAuditResponse(BaseModel):
    id: UUID
    request_id: str
    user_id: UUID
    thread_id: UUID | None = None
    question: str
    retrieved_chunk_ids: list[str]
    cited_source_ids: list[str]
    validation_status: str
    model_name: str
    latency_ms: int
    created_at: datetime


class AnswerAuditListResponse(BaseModel):
    items: list[AnswerAuditResponse]
    total: int
    page: int
    page_size: int
