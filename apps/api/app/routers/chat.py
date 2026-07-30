from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.graph import run_research
from app.database import get_db
from app.models import ChatMessage, ChatThread, SourceDocument, UserFollow
from app.routers.stocks import stock_response
from app.schemas import (
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ClaimResponse,
    RecommendationResponse,
    ThreadCreate,
    ThreadResponse,
)
from app.services.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["research chat"])
source_router = APIRouter(prefix="/sources", tags=["sources"])


def thread_response(thread: ChatThread) -> ThreadResponse:
    return ThreadResponse(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


@router.get("/threads", response_model=list[ThreadResponse])
def list_threads(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[ThreadResponse]:
    return [
        thread_response(thread)
        for thread in db.scalars(
            select(ChatThread)
            .where(ChatThread.user_id == user.id)
            .order_by(ChatThread.updated_at.desc())
        )
    ]


@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_thread(
    payload: ThreadCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ThreadResponse:
    thread = ChatThread(user_id=user.id, title=payload.title or "Research thread")
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread_response(thread)


@router.post("/threads/{thread_id}/messages", response_model=ChatResponse)
def send_message(
    thread_id: UUID,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ChatResponse:
    thread = db.scalar(select(ChatThread).where(ChatThread.id == thread_id, ChatThread.user_id == user.id))
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research thread not found")
    message = ChatMessage(thread_id=thread.id, role="user", content=payload.question)
    db.add(message)
    thread.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(message)
    result = run_research(
        db,
        user_id=user.id,
        thread_id=thread.id,
        chat_message_id=message.id,
        question=payload.question,
    )
    recommendations = [
        RecommendationResponse(
            stock=stock_response(item["stock"]),
            score=item["score"],
            reasons=item["reasons"],
            citation_ids=item["citation_ids"],
        )
        for item in result.get("recommendations", [])
    ]
    return ChatResponse(
        request_id=result["request_id"],
        answer_markdown=result["answer_markdown"],
        claims=[ClaimResponse(**claim) for claim in result.get("claims", [])],
        citations=[CitationResponse(**citation) for citation in result.get("citations", [])],
        recommendations=recommendations,
        data_gaps=result.get("data_gaps", []),
        profile_updates=result.get("profile_updates", []),
        retrieved_at=datetime.now(UTC),
    )


@source_router.get("/{source_id}")
def get_source(
    source_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> dict:
    source = db.scalar(
        select(SourceDocument)
        .join(UserFollow, UserFollow.stock_id == SourceDocument.stock_id)
        .where(SourceDocument.id == source_id, UserFollow.user_id == user.id)
    )
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return {
        "id": str(source.id),
        "type": source.source_type,
        "publisher": source.publisher,
        "title": source.title,
        "url": source.canonical_url,
        "published_at": source.published_at,
        "retrieved_at": source.retrieved_at,
        "excerpt": source.excerpt,
        "content": source.content,
    }
