from __future__ import annotations

import hashlib
import math

from langchain_openai import OpenAIEmbeddings

from app.config import get_settings


class EmbeddingService:
    """Production uses the configured embedding model; local fallback is only for development."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = (
            OpenAIEmbeddings(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_embedding_model,
                dimensions=self.settings.embedding_dimensions,
            )
            if self.settings.openai_api_key
            else None
        )

    @property
    def model_name(self) -> str:
        return self.settings.openai_embedding_model if self._client else "deterministic-dev-fallback-v1"

    @property
    def is_production_embedding(self) -> bool:
        return self._client is not None

    def embed(self, text: str) -> list[float]:
        if self._client is not None:
            return self._client.embed_query(text)
        return self._deterministic_fallback(text)

    def _deterministic_fallback(self, text: str) -> list[float]:
        """Stable non-semantic vector for local API/UI verification without a provider key."""
        dimension = self.settings.embedding_dimensions
        values: list[float] = []
        seed = text.encode("utf-8")
        counter = 0
        while len(values) < dimension:
            digest = hashlib.sha512(seed + counter.to_bytes(4, "big")).digest()
            for byte in digest:
                values.append((byte / 127.5) - 1.0)
                if len(values) == dimension:
                    break
            counter += 1
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]
