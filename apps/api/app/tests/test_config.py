from __future__ import annotations

import os
from unittest.mock import patch

from app.config import Settings


def test_settings_defaults() -> None:
    with patch.dict(os.environ, {}, clear=False):
        settings = Settings()
        assert settings.app_name == "Sentellent Indian Equity Analyst"
        assert settings.environment == "development"
        assert settings.api_prefix == "/api"
        assert settings.dev_bypass_auth is True


def test_settings_resolved_database_url_from_parts() -> None:
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "",
            "DATABASE_HOST": "db.example.com",
            "DATABASE_PORT": "5433",
            "DATABASE_NAME": "testdb",
            "DATABASE_USER": "testuser",
            "DATABASE_PASSWORD": "testpass",
        },
        clear=False,
    ):
        settings = Settings()
        url = settings.resolved_database_url
        assert "db.example.com" in url
        assert "5433" in url
        assert "testdb" in url


def test_settings_parsed_news_feed_urls() -> None:
    with patch.dict(
        os.environ,
        {"NEWS_FEED_URLS": "http://a.com, http://b.com ,  "},
        clear=False,
    ):
        settings = Settings()
        urls = settings.parsed_news_feed_urls
        assert urls == ["http://a.com", "http://b.com"]


def test_embedding_dimensions_validator() -> None:
    with patch.dict(os.environ, {"EMBEDDING_DIMENSIONS": "1536"}, clear=False):
        settings = Settings()
        assert settings.embedding_dimensions == 1536
