from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ProfileFactResponse, ProfilePatch, ProfileResponse
from app.services.auth import get_current_user
from app.services.profiles import apply_profile_patch, get_profile, list_active_facts

router = APIRouter(prefix="/profile", tags=["profile"])


def profile_response(db: Session, user_id) -> ProfileResponse:
    profile = get_profile(db, user_id)
    facts = list_active_facts(db, user_id)
    return ProfileResponse(
        profile=profile.profile_json or {},
        version=profile.version,
        facts=[
            ProfileFactResponse(
                id=fact.id,
                key=fact.key,
                value=fact.value_json,
                state=fact.state,
                source_message_id=fact.chat_message_id,
                created_at=fact.created_at,
            )
            for fact in facts
        ],
    )


@router.get("", response_model=ProfileResponse)
def get_investor_profile(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ProfileResponse:
    return profile_response(db, user.id)


@router.patch("", response_model=ProfileResponse)
def update_investor_profile(
    patch: ProfilePatch,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> ProfileResponse:
    apply_profile_patch(
        db,
        user_id=user.id,
        patch=patch.model_dump(exclude_none=True),
        chat_message_id=None,
        source="profile_editor",
    )
    return profile_response(db, user.id)
