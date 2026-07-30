from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion.service import enqueue_refresh
from app.models import IngestionJob, Stock, UserFollow
from app.schemas import (
    FollowCreate,
    FollowResponse,
    IngestionStatusResponse,
    StockResponse,
)
from app.services.auth import get_current_user
from app.services.stocks import get_or_create_stock, search_stocks

router = APIRouter(tags=["stocks"])


def stock_response(stock: Stock) -> StockResponse:
    return StockResponse(
        id=stock.id,
        symbol=stock.symbol,
        exchange=stock.exchange,
        company_name=stock.company_name,
        sector=stock.sector,
        yfinance_symbol=stock.yfinance_symbol,
    )


def job_response(job: IngestionJob | None) -> IngestionStatusResponse | None:
    if job is None:
        return None
    return IngestionStatusResponse(
        id=job.id,
        stock_id=job.stock_id,
        status=job.status,
        trigger=job.trigger,
        attempt=job.attempt,
        correlation_id=job.correlation_id,
        created_at=job.created_at,
        completed_at=job.completed_at,
        last_error=job.last_error,
    )


@router.get("/stocks/search", response_model=list[StockResponse])
def search(
    q: str = Query(min_length=1, max_length=128),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[StockResponse]:
    return [stock_response(stock) for stock in search_stocks(db, q)]


@router.get("/follows", response_model=list[FollowResponse])
def list_follows(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> list[FollowResponse]:
    follows = list(
        db.scalars(
            select(UserFollow)
            .where(UserFollow.user_id == user.id)
            .order_by(UserFollow.created_at.desc())
        )
    )
    response: list[FollowResponse] = []
    for follow in follows:
        latest = db.scalar(
            select(IngestionJob)
            .where(IngestionJob.stock_id == follow.stock_id)
            .order_by(IngestionJob.created_at.desc())
            .limit(1)
        )
        response.append(
            FollowResponse(id=follow.id, stock=stock_response(follow.stock), latest_job=job_response(latest))
        )
    return response


@router.post("/follows", response_model=FollowResponse, status_code=status.HTTP_201_CREATED)
def follow(
    payload: FollowCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> FollowResponse:
    stock = get_or_create_stock(db, payload.symbol, payload.exchange, payload.company_name)
    follow_item = db.scalar(
        select(UserFollow).where(UserFollow.user_id == user.id, UserFollow.stock_id == stock.id)
    )
    if follow_item is None:
        follow_item = UserFollow(user_id=user.id, stock_id=stock.id)
        db.add(follow_item)
        db.commit()
        db.refresh(follow_item)
    job = enqueue_refresh(db, stock.id, "follow")
    return FollowResponse(id=follow_item.id, stock=stock_response(stock), latest_job=job_response(job))


@router.delete(
    "/follows/{stock_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
def unfollow(
    stock_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> None:
    follow_item = db.scalar(
        select(UserFollow).where(UserFollow.user_id == user.id, UserFollow.stock_id == stock_id)
    )
    if follow_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow relationship not found")
    db.delete(follow_item)
    db.commit()


@router.post("/stocks/{symbol}/refresh", response_model=IngestionStatusResponse)
def refresh(
    symbol: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> IngestionStatusResponse:
    stock = db.scalar(select(Stock).where(Stock.symbol == symbol.upper(), Stock.exchange == "NSE"))
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
    follows = db.scalar(
        select(UserFollow).where(UserFollow.user_id == user.id, UserFollow.stock_id == stock.id)
    )
    if follows is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Follow the stock before refreshing.")
    return job_response(enqueue_refresh(db, stock.id, "manual"))


@router.get("/stocks/{symbol}/status", response_model=IngestionStatusResponse)
def ingestion_status(
    symbol: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> IngestionStatusResponse:
    stock = db.scalar(select(Stock).where(Stock.symbol == symbol.upper(), Stock.exchange == "NSE"))
    if stock is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found")
    allowed = db.scalar(
        select(UserFollow).where(UserFollow.user_id == user.id, UserFollow.stock_id == stock.id)
    )
    if allowed is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Stock is not followed")
    job = db.scalar(
        select(IngestionJob)
        .where(IngestionJob.stock_id == stock.id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ingestion job found")
    return job_response(job)
