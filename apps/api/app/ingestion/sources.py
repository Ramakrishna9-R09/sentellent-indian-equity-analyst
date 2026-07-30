from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

import feedparser
import httpx
import yfinance as yf
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from app.config import get_settings
from app.models import Stock


@dataclass
class SourcePayload:
    source_type: str
    publisher: str
    canonical_url: str
    title: str
    content: str
    excerpt: str
    published_at: datetime | None
    metrics: dict[str, tuple[str, str, Decimal | None, str | None]] = field(default_factory=dict)

    @property
    def content_sha256(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    @property
    def fingerprint(self) -> str:
        identity = "|".join(
            [
                self.canonical_url.strip().lower(),
                self.title.strip().lower(),
                self.published_at.isoformat() if self.published_at else "",
                self.content_sha256,
            ]
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def parse_indian_number(raw: str) -> tuple[Decimal | None, str | None]:
    cleaned = raw.replace("Rs.", "").replace("₹", "").replace(",", "").strip()
    multiplier = Decimal("1")
    unit: str | None = None
    lower = cleaned.lower()
    if "crore" in lower or " cr" in lower:
        multiplier = Decimal("10000000")
        unit = "INR"
    elif "lakh" in lower or " lac" in lower:
        multiplier = Decimal("100000")
        unit = "INR"
    cleaned = re.sub(r"(?i)(crore|cr\.?|lakh|lac\.?|%)", "", cleaned).strip()
    try:
        return Decimal(cleaned) * multiplier, unit
    except InvalidOperation:
        return None, None


class ScreenerFundamentalsConnector:
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch(self, stock: Stock) -> list[SourcePayload]:
        if stock.exchange != "NSE":
            return []
        url = f"https://www.screener.in/company/{stock.symbol}/consolidated/"
        headers = {"User-Agent": self.settings.source_user_agent}
        response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else f"{stock.symbol} fundamentals"
        text = soup.get_text(" ", strip=True)
        metrics: dict[str, tuple[str, str, Decimal | None, str | None]] = {}
        labels = {
            "market_cap": "Market Cap",
            "current_price": "Current Price",
            "stock_pe": "Stock P/E",
            "book_value": "Book Value",
            "dividend_yield": "Dividend Yield",
            "roce": "ROCE",
            "roe": "ROE",
            "debt_to_equity": "Debt to equity",
        }
        for key, label in labels.items():
            match = re.search(
                rf"{re.escape(label)}\s*([₹Rs\.\s0-9,]+(?:Cr\.?|Crore|Lakh|%|x)?)",
                text,
                flags=re.IGNORECASE,
            )
            if match:
                raw = match.group(1).strip()
                numeric, unit = parse_indian_number(raw)
                metrics[key] = (label, raw, numeric, unit)
        excerpt = text[:1200]
        return [
            SourcePayload(
                source_type="fundamentals",
                publisher="Screener",
                canonical_url=url,
                title=title,
                content=excerpt,
                excerpt=excerpt[:400],
                published_at=datetime.now(UTC),
                metrics=metrics,
            )
        ]


class RSSNewsConnector:
    def __init__(self) -> None:
        self.settings = get_settings()

    def fetch(self, stock: Stock) -> list[SourcePayload]:
        aliases = {stock.symbol.lower(), stock.company_name.lower()}
        aliases.add(stock.company_name.split()[0].lower())
        cutoff = datetime.now(UTC) - timedelta(days=self.settings.news_lookback_days)
        payloads: list[SourcePayload] = []
        for feed_url in self.settings.parsed_news_feed_urls:
            try:
                response = httpx.get(
                    feed_url,
                    headers={"User-Agent": self.settings.source_user_agent},
                    timeout=15,
                    follow_redirects=True,
                )
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            except (httpx.HTTPError, ValueError):
                continue
            for entry in feed.entries:
                title = str(entry.get("title", "")).strip()
                summary = BeautifulSoup(str(entry.get("summary", "")), "html.parser").get_text(
                    " ", strip=True
                )
                haystack = f"{title} {summary}".lower()
                if not any(alias and alias in haystack for alias in aliases):
                    continue
                raw_date = entry.get("published") or entry.get("updated")
                try:
                    published_at = _as_utc(date_parser.parse(raw_date)) if raw_date else None
                except (TypeError, ValueError, OverflowError):
                    published_at = None
                if published_at and published_at < cutoff:
                    continue
                url = str(entry.get("link", feed_url))
                publisher = urlparse(url).netloc or urlparse(feed_url).netloc
                content = f"{title}\n\n{summary}".strip()
                if not content:
                    continue
                payloads.append(
                    SourcePayload(
                        source_type="news",
                        publisher=publisher,
                        canonical_url=url,
                        title=title or f"{stock.symbol} news",
                        content=content,
                        excerpt=summary[:500] or title[:500],
                        published_at=published_at,
                    )
                )
        return payloads


class PriceConnector:
    def fetch(self, stock: Stock) -> list[SourcePayload]:
        if not stock.yfinance_symbol:
            return []
        history = yf.Ticker(stock.yfinance_symbol).history(period="7d", auto_adjust=False)
        if history.empty:
            return []
        closes = history["Close"].dropna()
        last = Decimal(str(round(float(closes.iloc[-1]), 2)))
        change_5d: Decimal | None = None
        if len(closes) > 1 and closes.iloc[0] != 0:
            change_5d = Decimal(str(round(((closes.iloc[-1] / closes.iloc[0]) - 1) * 100, 2)))
        observed = history.index[-1].to_pydatetime()
        observed_at = _as_utc(observed)
        content = f"{stock.symbol} latest close: Rs. {last}. Observation time: {observed_at.isoformat()}."
        metrics: dict[str, tuple[str, str, Decimal | None, str | None]] = {
            "last_price_inr": ("Latest close", str(last), last, "INR"),
        }
        if change_5d is not None:
            metrics["price_change_5d_pct"] = (
                "5-day price change",
                f"{change_5d}%",
                change_5d,
                "percent",
            )
        return [
            SourcePayload(
                source_type="price",
                publisher="Yahoo Finance",
                canonical_url=f"https://finance.yahoo.com/quote/{stock.yfinance_symbol}/",
                title=f"{stock.symbol} INR price snapshot",
                content=content,
                excerpt=content,
                published_at=observed_at,
                metrics=metrics,
            )
        ]


def fetch_all_sources(stock: Stock) -> tuple[list[SourcePayload], list[str]]:
    payloads: list[SourcePayload] = []
    errors: list[str] = []
    for connector in (ScreenerFundamentalsConnector(), RSSNewsConnector(), PriceConnector()):
        try:
            payloads.extend(connector.fetch(stock))
        except Exception as exc:
            errors.append(f"{connector.__class__.__name__}: {str(exc)[:240]}")
    return payloads, errors
