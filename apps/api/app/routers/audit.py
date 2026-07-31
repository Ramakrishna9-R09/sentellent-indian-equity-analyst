from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AnswerAudit
from app.schemas import AnswerAuditListResponse, AnswerAuditResponse
from app.services.auth import get_current_user

router = APIRouter(prefix="/audit", tags=["answer audit"])


@router.get("/answers", response_model=AnswerAuditListResponse)
def list_answer_audits(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    validation_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> AnswerAuditListResponse:
    query = select(AnswerAudit).where(AnswerAudit.user_id == user.id)
    count_query = select(func.count(AnswerAudit.id)).where(AnswerAudit.user_id == user.id)

    if validation_status:
        query = query.where(AnswerAudit.validation_status == validation_status)
        count_query = count_query.where(AnswerAudit.validation_status == validation_status)

    total = db.scalar(count_query) or 0
    offset = (page - 1) * page_size
    items = list(
        db.scalars(query.order_by(AnswerAudit.created_at.desc()).offset(offset).limit(page_size))
    )
    return AnswerAuditListResponse(
        items=[
            AnswerAuditResponse(
                id=item.id,
                request_id=item.request_id,
                user_id=item.user_id,
                thread_id=item.thread_id,
                question=item.question,
                retrieved_chunk_ids=item.retrieved_chunk_ids,
                cited_source_ids=item.cited_source_ids,
                validation_status=item.validation_status,
                model_name=item.model_name,
                latency_ms=item.latency_ms,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/answers/{request_id}", response_model=AnswerAuditResponse)
def get_answer_audit(
    request_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> AnswerAuditResponse:
    item = db.scalar(
        select(AnswerAudit).where(
            AnswerAudit.request_id == request_id,
            AnswerAudit.user_id == user.id,
        )
    )
    if item is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit record not found")
    return AnswerAuditResponse(
        id=item.id,
        request_id=item.request_id,
        user_id=item.user_id,
        thread_id=item.thread_id,
        question=item.question,
        retrieved_chunk_ids=item.retrieved_chunk_ids,
        cited_source_ids=item.cited_source_ids,
        validation_status=item.validation_status,
        model_name=item.model_name,
        latency_ms=item.latency_ms,
        created_at=item.created_at,
    )
