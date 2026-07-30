from app.ingestion.service import _chunk_text
from app.ingestion.sources import parse_indian_number


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
