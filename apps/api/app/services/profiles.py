from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InvestorProfile, ProfileFact
from app.services.embeddings import EmbeddingService


def default_profile() -> dict[str, Any]:
    return {
        "risk_tolerance": None,
        "objectives": [],
        "avoid_high_debt": False,
        "max_debt_to_equity": None,
        "horizon": None,
        "excluded_sectors": [],
    }


def get_profile(db: Session, user_id: UUID) -> InvestorProfile:
    profile = db.get(InvestorProfile, user_id)
    if profile is None:
        profile = InvestorProfile(user_id=user_id, profile_json=default_profile())
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def extract_profile_patch(message: str) -> dict[str, Any]:
    """Only write durable memory from an explicit first-person preference statement."""
    lower = message.lower()
    if not re.search(r"\b(i am|i'm|i prefer|i avoid|my profile|my goal|i want)\b", lower):
        return {}

    patch: dict[str, Any] = {}
    if "conservative" in lower:
        patch["risk_tolerance"] = "conservative"
    elif "moderate" in lower or "balanced" in lower:
        patch["risk_tolerance"] = "moderate"
    elif "aggressive" in lower or "high risk" in lower:
        patch["risk_tolerance"] = "aggressive"

    objectives: list[str] = []
    if "dividend" in lower or "income" in lower:
        objectives.append("income")
    if "growth" in lower:
        objectives.append("growth")
    if "value" in lower:
        objectives.append("value")
    if objectives:
        patch["objectives"] = objectives

    if re.search(r"(avoid|no|not).{0,32}(high[- ]debt|debt)", lower):
        patch["avoid_high_debt"] = True
        patch["max_debt_to_equity"] = 1.0
    if "long term" in lower or "long-term" in lower:
        patch["horizon"] = "long_term"
    elif "short term" in lower or "short-term" in lower:
        patch["horizon"] = "short_term"
    return patch


def apply_profile_patch(
    db: Session,
    *,
    user_id: UUID,
    patch: dict[str, Any],
    chat_message_id: UUID | None,
    source: str = "chat",
) -> list[dict[str, Any]]:
    if not patch:
        return []
    profile = get_profile(db, user_id)
    current = {**default_profile(), **(profile.profile_json or {})}
    updates: list[dict[str, Any]] = []

    for key, value in patch.items():
        if value is None or current.get(key) == value:
            continue
        db.query(ProfileFact).filter(
            ProfileFact.user_id == user_id,
            ProfileFact.key == key,
            ProfileFact.state == "active",
        ).update(
            {
                "state": "superseded",
                "valid_to": datetime.now(UTC),
            },
            synchronize_session=False,
        )
        current[key] = value
        fact = ProfileFact(
            user_id=user_id,
            chat_message_id=chat_message_id,
            key=key,
            value_json={"value": value, "source": source},
            confidence=1,
            state="active",
        )
        db.add(fact)
        updates.append({"key": key, "value": value})

    if updates:
        profile.profile_json = current
        profile.version += 1
        profile.persona_embedding = EmbeddingService().embed(
            json.dumps(current, sort_keys=True, separators=(",", ":"))
        )
        db.commit()
    return updates


def list_active_facts(db: Session, user_id: UUID) -> list[ProfileFact]:
    return list(
        db.scalars(
            select(ProfileFact)
            .where(ProfileFact.user_id == user_id, ProfileFact.state == "active")
            .order_by(ProfileFact.created_at.desc())
        )
    )
