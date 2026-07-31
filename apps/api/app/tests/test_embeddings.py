from __future__ import annotations

import math

from app.services.embeddings import EmbeddingService


def test_deterministic_fallback_produces_unit_vector() -> None:
    service = EmbeddingService()
    embedding = service.embed("test input text")
    assert len(embedding) == 1536
    norm = math.sqrt(sum(v * v for v in embedding))
    assert abs(norm - 1.0) < 0.01


def test_deterministic_fallback_is_deterministic() -> None:
    service = EmbeddingService()
    same_text = "identical input for determinism check"
    second = service.embed(same_text)
    third = service.embed(same_text)
    assert second == third


def test_deterministic_fallback_varies_with_input() -> None:
    service = EmbeddingService()
    emb1 = service.embed("alpha text")
    emb2 = service.embed("beta text")
    assert emb1 != emb2


def test_model_name_without_api_key() -> None:
    service = EmbeddingService()
    assert service.model_name == "deterministic-dev-fallback-v1"
    assert service.is_production_embedding is False
