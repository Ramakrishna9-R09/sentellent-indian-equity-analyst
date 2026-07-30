from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any, Literal, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.retrieval import Evidence, resolve_tickers, retrieve_evidence, source_evidence
from app.models import AnswerAudit, ChatMessage, Stock, StockFeatureSnapshot, UserFollow
from app.services.embeddings import EmbeddingService
from app.services.profiles import apply_profile_patch, extract_profile_patch, get_profile


class ResearchState(TypedDict, total=False):
    db: Session
    user_id: UUID
    thread_id: UUID
    chat_message_id: UUID
    question: str
    request_id: str
    started_at: float
    profile: dict[str, Any]
    profile_updates: list[dict[str, Any]]
    stocks: list[Stock]
    intent: Literal["research", "recommendation"]
    evidence: list[Evidence]
    citations: list[dict[str, Any]]
    claims: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    answer_markdown: str
    data_gaps: list[str]
    validation_status: str


def _citation(evidence: Evidence, citation_id: str) -> dict[str, Any]:
    return {
        "id": citation_id,
        "source_document_id": evidence.source_document_id,
        "title": evidence.title,
        "publisher": evidence.publisher,
        "url": evidence.url,
        "published_at": evidence.published_at,
        "excerpt": evidence.excerpt,
    }


def _load_profile(state: ResearchState) -> ResearchState:
    profile = get_profile(state["db"], state["user_id"])
    state["profile"] = profile.profile_json or {}
    return state


def _extract_memory(state: ResearchState) -> ResearchState:
    patch = extract_profile_patch(state["question"])
    state["profile_updates"] = apply_profile_patch(
        state["db"],
        user_id=state["user_id"],
        patch=patch,
        chat_message_id=state["chat_message_id"],
    )
    state["profile"] = get_profile(state["db"], state["user_id"]).profile_json or {}
    return state


def _resolve_intent(state: ResearchState) -> ResearchState:
    lower = state["question"].lower()
    state["intent"] = (
        "recommendation"
        if any(token in lower for token in ("recommend", "what should i buy", "best stocks", "pick stocks"))
        else "research"
    )
    state["stocks"] = resolve_tickers(state["db"], state["user_id"], state["question"])
    return state


def _retrieve(state: ResearchState) -> ResearchState:
    state["evidence"] = retrieve_evidence(
        state["db"],
        stock_ids=[stock.id for stock in state["stocks"]],
        question=state["question"],
    )
    return state


def _rank_candidates(state: ResearchState) -> ResearchState:
    db = state["db"]
    profile = state["profile"]
    followed = db.execute(
        select(Stock, StockFeatureSnapshot)
        .join(UserFollow, UserFollow.stock_id == Stock.id)
        .join(
            StockFeatureSnapshot,
            StockFeatureSnapshot.stock_id == Stock.id,
            isouter=True,
        )
        .where(UserFollow.user_id == state["user_id"])
        .order_by(StockFeatureSnapshot.as_of_date.desc().nullslast())
    ).all()

    weights = {
        "quality_score": Decimal("0.20"),
        "income_score": Decimal("0.15"),
        "value_score": Decimal("0.15"),
        "momentum_score": Decimal("0.15"),
        "risk_score": Decimal("0.20"),
        "sentiment_score": Decimal("0.15"),
    }
    if profile.get("risk_tolerance") == "conservative":
        weights.update(
            {
                "quality_score": Decimal("0.28"),
                "income_score": Decimal("0.24"),
                "value_score": Decimal("0.10"),
                "momentum_score": Decimal("0.05"),
                "risk_score": Decimal("0.25"),
                "sentiment_score": Decimal("0.08"),
            }
        )
    objectives = set(profile.get("objectives") or [])
    if "income" in objectives:
        weights["income_score"] += Decimal("0.10")
        weights["momentum_score"] -= Decimal("0.05")
        weights["value_score"] -= Decimal("0.05")

    candidates: list[dict[str, Any]] = []
    max_debt = profile.get("max_debt_to_equity")
    if profile.get("avoid_high_debt") and max_debt is None:
        max_debt = 1.0

    deduped: set[UUID] = set()
    for stock, features in followed:
        if stock.id in deduped:
            continue
        deduped.add(stock.id)
        if features is None:
            continue
        if max_debt is not None and (
            features.debt_to_equity is None or float(features.debt_to_equity) > float(max_debt)
        ):
            continue
        components = [
            Decimal(str(getattr(features, key)))
            for key in weights
            if getattr(features, key) is not None
        ]
        if len(components) < 2:
            continue
        weighted_total = sum(
            Decimal(str(getattr(features, key))) * weight
            for key, weight in weights.items()
            if getattr(features, key) is not None
        )
        available_weight = sum(
            weight for key, weight in weights.items() if getattr(features, key) is not None
        )
        if not available_weight:
            continue
        score = float(weighted_total / available_weight)
        source_ids = list((features.source_map or {}).values())
        candidates.append(
            {
                "stock": stock,
                "score": round(score, 2),
                "source_ids": source_ids,
                "reasons": [
                    "Score is calculated from the latest ingested, source-backed quality, income, risk, value, momentum, and sentiment features."
                ],
            }
        )
    state["recommendations"] = sorted(candidates, key=lambda item: item["score"], reverse=True)[:3]
    return state


def _compose(state: ResearchState) -> ResearchState:
    evidence = state.get("evidence", [])
    citations: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    data_gaps: list[str] = []

    if state["intent"] == "recommendation":
        recommendation_source_ids = [
            source_id
            for item in state.get("recommendations", [])
            for source_id in item["source_ids"]
        ]
        source_items = source_evidence(state["db"], recommendation_source_ids)
        for item in source_items:
            if not any(existing["source_document_id"] == item.source_document_id for existing in citations):
                citations.append(_citation(item, f"S{len(citations) + 1}"))
        citation_for_source = {str(item["source_document_id"]): item["id"] for item in citations}
        rendered_recommendations: list[dict[str, Any]] = []
        for candidate in state.get("recommendations", []):
            citation_ids = [
                citation_for_source[source_id]
                for source_id in candidate["source_ids"]
                if source_id in citation_for_source
            ]
            if not citation_ids:
                continue
            rendered_recommendations.append(
                {
                    "stock": candidate["stock"],
                    "score": candidate["score"],
                    "reasons": candidate["reasons"],
                    "citation_ids": citation_ids,
                }
            )
        state["recommendations"] = rendered_recommendations
        if not rendered_recommendations:
            state["answer_markdown"] = (
                "I don't have enough fresh, source-backed data to rank profile-matched stocks. "
                "Follow and refresh more tickers, then ask again."
            )
            data_gaps.append("No candidate had enough fresh cited features after applying your profile rules.")
        else:
            lines = [
                "Here are the highest-ranked followed stocks that passed your saved profile rules. "
                "These are research candidates, not investment advice:"
            ]
            for candidate in rendered_recommendations:
                refs = ", ".join(f"[{citation_id}]" for citation_id in candidate["citation_ids"])
                lines.append(
                    f"- {candidate['stock'].symbol}: score {candidate['score']}/100. "
                    f"{candidate['reasons'][0]} {refs}"
                )
                claims.append(
                    {
                        "text": f"{candidate['stock'].symbol} is profile-matched from current ingested features.",
                        "citation_ids": candidate["citation_ids"],
                    }
                )
            state["answer_markdown"] = "\n".join(lines)
    elif not evidence:
        state["answer_markdown"] = "I don't have that in the ingested data."
        data_gaps.append("No matching ingested source was retrieved for this question.")
    else:
        stock_names = ", ".join(sorted({item.stock_symbol for item in evidence}))
        for item in evidence:
            citation_id = f"S{len(citations) + 1}"
            citations.append(_citation(item, citation_id))
            claims.append(
                {
                    "text": f"{item.stock_symbol}: {item.excerpt}",
                    "citation_ids": [citation_id],
                }
            )
        answer_lines = [
            f"I found {len(evidence)} relevant ingested source(s) for {stock_names}.",
            "The evidence below is limited to retrieved sources and may not reflect real-time market conditions:",
        ]
        for claim, citation in zip(claims[:4], citations[:4], strict=False):
            answer_lines.append(f"- {claim['text']} [{citation['id']}]")
        state["answer_markdown"] = "\n".join(answer_lines)

    state["citations"] = citations
    state["claims"] = claims
    state["data_gaps"] = data_gaps
    return state


def _validate(state: ResearchState) -> ResearchState:
    known_ids = {item["id"] for item in state.get("citations", [])}
    valid = bool(state.get("data_gaps")) or all(
        claim.get("citation_ids") and set(claim["citation_ids"]).issubset(known_ids)
        for claim in state.get("claims", [])
    )
    if not valid:
        state["answer_markdown"] = "I don't have that in the ingested data."
        state["claims"] = []
        state["citations"] = []
        state["recommendations"] = []
        state["data_gaps"] = ["Citation validation rejected an unsupported claim."]
        state["validation_status"] = "rejected"
    else:
        state["validation_status"] = "validated"
    return state


def _persist(state: ResearchState) -> ResearchState:
    db = state["db"]
    db.add(
        ChatMessage(
            thread_id=state["thread_id"],
            role="assistant",
            content=state["answer_markdown"],
        )
    )
    db.add(
        AnswerAudit(
            request_id=state["request_id"],
            user_id=state["user_id"],
            thread_id=state["thread_id"],
            question=state["question"],
            retrieved_chunk_ids=[str(item.chunk_id) for item in state.get("evidence", [])],
            cited_source_ids=[str(item["source_document_id"]) for item in state.get("citations", [])],
            validation_status=state["validation_status"],
            model_name=EmbeddingService().model_name,
            latency_ms=int((time.perf_counter() - state["started_at"]) * 1000),
        )
    )
    db.commit()
    return state


def _route_after_retrieval(state: ResearchState) -> Literal["rank", "compose"]:
    return "rank" if state["intent"] == "recommendation" else "compose"


def build_research_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("load_profile", _load_profile)
    graph.add_node("extract_memory", _extract_memory)
    graph.add_node("resolve_intent", _resolve_intent)
    graph.add_node("retrieve", _retrieve)
    graph.add_node("rank", _rank_candidates)
    graph.add_node("compose", _compose)
    graph.add_node("validate", _validate)
    graph.add_node("persist", _persist)
    graph.add_edge(START, "load_profile")
    graph.add_edge("load_profile", "extract_memory")
    graph.add_edge("extract_memory", "resolve_intent")
    graph.add_edge("resolve_intent", "retrieve")
    graph.add_conditional_edges("retrieve", _route_after_retrieval, {"rank": "rank", "compose": "compose"})
    graph.add_edge("rank", "compose")
    graph.add_edge("compose", "validate")
    graph.add_edge("validate", "persist")
    graph.add_edge("persist", END)
    return graph.compile()


research_graph = build_research_graph()


def run_research(
    db: Session, *, user_id: UUID, thread_id: UUID, chat_message_id: UUID, question: str
) -> ResearchState:
    return research_graph.invoke(
        {
            "db": db,
            "user_id": user_id,
            "thread_id": thread_id,
            "chat_message_id": chat_message_id,
            "question": question,
            "request_id": uuid.uuid4().hex,
            "started_at": time.perf_counter(),
        }
    )
