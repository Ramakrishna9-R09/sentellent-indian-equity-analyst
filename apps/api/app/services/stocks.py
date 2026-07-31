from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Stock

SEED_STOCKS = (
    {
        "symbol": "RELIANCE",
        "exchange": "NSE",
        "company_name": "Reliance Industries Limited",
        "nse_id": "RELIANCE",
        "bse_id": "500325",
        "yfinance_symbol": "RELIANCE.NS",
        "sector": "Energy",
    },
    {
        "symbol": "TCS",
        "exchange": "NSE",
        "company_name": "Tata Consultancy Services Limited",
        "nse_id": "TCS",
        "bse_id": "532540",
        "yfinance_symbol": "TCS.NS",
        "sector": "Information Technology",
    },
    {
        "symbol": "HDFCBANK",
        "exchange": "NSE",
        "company_name": "HDFC Bank Limited",
        "nse_id": "HDFCBANK",
        "bse_id": "500180",
        "yfinance_symbol": "HDFCBANK.NS",
        "sector": "Financial Services",
    },
    {
        "symbol": "INFY",
        "exchange": "NSE",
        "company_name": "Infosys Limited",
        "nse_id": "INFY",
        "bse_id": "500209",
        "yfinance_symbol": "INFY.NS",
        "sector": "Information Technology",
    },
    {
        "symbol": "ITC",
        "exchange": "NSE",
        "company_name": "ITC Limited",
        "nse_id": "ITC",
        "bse_id": "500875",
        "yfinance_symbol": "ITC.NS",
        "sector": "Consumer Defensive",
    },
)


def ensure_seed_stocks(db: Session) -> None:
    for payload in SEED_STOCKS:
        existing = db.scalar(
            select(Stock).where(
                Stock.symbol == payload["symbol"], Stock.exchange == payload["exchange"]
            )
        )
        if existing is None:
            db.add(Stock(**payload))
        else:
            changed = False
            for key in ("nse_id", "bse_id", "company_name", "yfinance_symbol", "sector"):
                value = payload.get(key)
                if value and getattr(existing, key) != value:
                    setattr(existing, key, value)
                    changed = True
            if changed:
                db.add(existing)
    db.commit()


def search_stocks(db: Session, query: str, limit: int = 12) -> list[Stock]:
    ensure_seed_stocks(db)
    needle = f"%{query.strip().upper()}%"
    return list(
        db.scalars(
            select(Stock)
            .where(or_(Stock.symbol.ilike(needle), Stock.company_name.ilike(needle)))
            .order_by(Stock.symbol)
            .limit(limit)
        )
    )


def get_or_create_stock(
    db: Session, symbol: str, exchange: str, company_name: str | None = None
) -> Stock:
    symbol = symbol.strip().upper()
    exchange = exchange.strip().upper()
    stock = db.scalar(select(Stock).where(Stock.symbol == symbol, Stock.exchange == exchange))
    if stock:
        return stock
    stock = Stock(
        symbol=symbol,
        exchange=exchange,
        company_name=company_name or symbol,
        yfinance_symbol=f"{symbol}.NS" if exchange == "NSE" else None,
    )
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock
