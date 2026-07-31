from decimal import Decimal

from app.ingestion.service import _chunk_text, _heuristic_article_tag, _sentiment_score
from app.ingestion.sources import SourcePayload, _is_foreign_lookalike, parse_indian_number


def test_chunker_is_deterministic_and_preserves_all_input() -> None:
    source = "Sentence one. " * 300
    first = _chunk_text(source)
    second = _chunk_text(source)

    assert first == second
    assert len(first) > 1
    assert first[0].startswith("Sentence one.")


def test_indian_currency_normalization() -> None:
    value, unit = parse_indian_number("Rs. 1,234.50 Cr.")

    assert value == 12345000000
    assert unit == "INR"


def test_indian_lakh_normalization() -> None:
    value, unit = parse_indian_number("Rs. 5.5 Lakh")
    assert value == 550000
    assert unit == "INR"


def test_plain_number_normalization() -> None:
    value, unit = parse_indian_number("42.5")
    assert value == Decimal("42.5")
    assert unit is None


def test_chunker_handles_empty_input() -> None:
    assert _chunk_text("") == []
    assert _chunk_text("   ") == []


def test_chunker_handles_short_input() -> None:
    result = _chunk_text("Short text.")
    assert result == ["Short text."]


def test_sentiment_score_mapping() -> None:
    assert _sentiment_score("positive") == Decimal("1")
    assert _sentiment_score("negative") == Decimal("-1")
    assert _sentiment_score("neutral") == Decimal("0")
    assert _sentiment_score("mixed") == Decimal("0")
    assert _sentiment_score("unknown") == Decimal("0")


def test_heuristic_article_tag_positive() -> None:
    payload = SourcePayload(
        source_type="news",
        publisher="test",
        canonical_url="http://example.com",
        title="Company reports profit growth and beats estimates",
        content="The company showed strong growth with increased profits.",
        excerpt="Profit growth",
        published_at=None,
    )
    tag = _heuristic_article_tag(payload)
    assert tag.sentiment == "positive"


def test_heuristic_article_tag_negative() -> None:
    payload = SourcePayload(
        source_type="news",
        publisher="test",
        canonical_url="http://example.com",
        title="Company faces debt issues and loss",
        content="The company has significant debt and reported a loss this quarter.",
        excerpt="Debt issues",
        published_at=None,
    )
    tag = _heuristic_article_tag(payload)
    assert tag.sentiment == "negative"


def test_heuristic_article_tag_mixed() -> None:
    payload = SourcePayload(
        source_type="news",
        publisher="test",
        canonical_url="http://example.com",
        title="Company profit but faces debt risk",
        content="Profit increased but the company carries high debt levels.",
        excerpt="Mixed signals",
        published_at=None,
    )
    tag = _heuristic_article_tag(payload)
    assert tag.sentiment == "mixed"


def test_heuristic_article_tag_neutral() -> None:
    payload = SourcePayload(
        source_type="news",
        publisher="test",
        canonical_url="http://example.com",
        title="Company holds annual meeting",
        content="The company held its annual shareholder meeting today.",
        excerpt="Annual meeting",
        published_at=None,
    )
    tag = _heuristic_article_tag(payload)
    assert tag.sentiment == "neutral"


def test_foreign_lookalike_reliance_inc_excluded() -> None:
    assert _is_foreign_lookalike("Reliance, Inc. Stock 12-Month Price Target Raised", "target $392")
    assert _is_foreign_lookalike("Reliance Steel stock price target on strong earnings", "BMO raises")


def test_foreign_lookalike_nyse_excluded() -> None:
    assert _is_foreign_lookalike("Reliance Inc to list on NYSE", "cross-listing news")


def test_foreign_lookalike_keeps_indian_articles() -> None:
    assert not _is_foreign_lookalike("Reliance Industries Q1 results: Analysts turn bullish", "Nifty gains")
    assert not _is_foreign_lookalike("TCS, Infosys shares rise on IT momentum", "sector rally")
