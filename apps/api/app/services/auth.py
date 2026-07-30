from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AppUser, AuthSession, InvestorProfile

settings = get_settings()
oauth = OAuth()

if settings.google_client_id and settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def _utcnow() -> datetime:
    return datetime.now(UTC)


def get_or_create_user(
    db: Session,
    *,
    email: str,
    provider_subject: str | None = None,
    display_name: str | None = None,
    picture_url: str | None = None,
) -> AppUser:
    query = select(AppUser).where(AppUser.email == email.lower())
    user = db.scalar(query)
    if user is None:
        user = AppUser(
            email=email.lower(),
            provider_subject=provider_subject,
            display_name=display_name,
            picture_url=picture_url,
            last_login_at=_utcnow(),
        )
        db.add(user)
        db.flush()
        db.add(InvestorProfile(user_id=user.id, profile_json={}))
    else:
        user.provider_subject = provider_subject or user.provider_subject
        user.display_name = display_name or user.display_name
        user.picture_url = picture_url or user.picture_url
        user.last_login_at = _utcnow()
    db.commit()
    db.refresh(user)
    return user


def create_session(db: Session, user: AppUser) -> str:
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    session = AuthSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=_utcnow() + timedelta(hours=settings.session_ttl_hours),
    )
    db.add(session)
    db.commit()
    return token


def get_current_user(request: Request, db: Session = Depends(get_db)) -> AppUser:
    if settings.dev_bypass_auth:
        return get_or_create_user(
            db,
            email=settings.dev_user_email,
            provider_subject=f"dev:{settings.dev_user_email}",
            display_name="Local demo investor",
        )

    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    auth_session = db.scalar(
        select(AuthSession).where(
            AuthSession.token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > _utcnow(),
        )
    )
    if auth_session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    user = db.get(AppUser, auth_session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return user


def revoke_session(request: Request, db: Session) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    auth_session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if auth_session:
        auth_session.revoked_at = _utcnow()
        db.commit()
