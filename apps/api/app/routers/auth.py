from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.schemas import UserResponse
from app.services.auth import (
    create_session,
    get_current_user,
    get_or_create_user,
    oauth,
    revoke_session,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()


@router.get("/google/login")
async def google_login(request: Request):
    if settings.dev_bypass_auth:
        return RedirectResponse(settings.web_app_url)
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured.",
        )
    logger.info(
        "Google OAuth login requested: redirect_uri=%s client_id_configured=%s web_app_url=%s",
        settings.google_redirect_uri,
        bool(settings.google_client_id),
        settings.web_app_url,
    )
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if settings.dev_bypass_auth:
        return RedirectResponse(settings.web_app_url)
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo") or await oauth.google.userinfo(token=token)
    except Exception as exc:
        logger.exception("Google OAuth callback failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="OAuth callback failed") from exc
    email = userinfo.get("email")
    subject = userinfo.get("sub")
    if not email or not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google identity is incomplete")
    user = get_or_create_user(
        db,
        email=email,
        provider_subject=subject,
        display_name=userinfo.get("name"),
        picture_url=userinfo.get("picture"),
    )
    session_token = create_session(db, user)
    response = RedirectResponse(settings.web_app_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: Session = Depends(get_db)) -> Response:
    revoke_session(request, db)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response


@router.get("/me", response_model=UserResponse)
def me(user=Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        picture_url=user.picture_url,
    )
