from __future__ import annotations

from unittest.mock import MagicMock

from app.agent.graph import ResearchState, _citation


def test_citation_structure() -> None:
    from dataclasses import dataclass
    from datetime import UTC, datetime
    from uuid import uuid4

    @dataclass
    class MockEvidence:
        source_document_id: str
        title: str
        publisher: str
        url: str
        published_at: datetime | None
        excerpt: str

    evidence = MockEvidence(
        source_document_id=str(uuid4()),
        title="Test Article",
        publisher="Test Publisher",
        url="http://example.com",
        published_at=datetime.now(UTC),
        excerpt="Test excerpt",
    )
    citation = _citation(evidence, "S1")
    assert citation["id"] == "S1"
    assert citation["title"] == "Test Article"
    assert citation["publisher"] == "Test Publisher"
    assert citation["url"] == "http://example.com"
    assert citation["excerpt"] == "Test excerpt"


def test_research_state_has_required_keys() -> None:
    required_keys = [
        "db", "user_id", "thread_id", "chat_message_id",
        "question", "request_id", "started_at", "profile",
        "profile_updates", "stocks", "intent", "evidence",
        "citations", "claims", "recommendations", "answer_markdown",
        "data_gaps", "validation_status",
    ]
    for key in required_keys:
        assert key in ResearchState.__annotations__


def test_intent_detection_recommendation() -> None:
    from app.agent.graph import _resolve_intent

    class MockDB:
        def execute(self, query):
            return MagicMock()
    mock_db = MockDB()

    state: ResearchState = {
        "db": mock_db,
        "user_id": "user123",
        "question": "Recommend stocks for my portfolio",
        "stocks": [],
    }
    result = _resolve_intent(state)
    assert result["intent"] == "recommendation"


def test_intent_detection_research() -> None:
    from app.agent.graph import _resolve_intent

    class MockDB:
        def execute(self, query):
            return MagicMock()
    mock_db = MockDB()

    state: ResearchState = {
        "db": mock_db,
        "user_id": "user123",
        "question": "What is the current price of RELIANCE?",
        "stocks": [],
    }
    result = _resolve_intent(state)
    assert result["intent"] == "research"
