from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import SessionLocal
from app.routers import auth, chat, profile, stocks
from app.services.stocks import ensure_seed_stocks

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Migrations are run by Docker Compose/ECS before the service starts.
    # Seed data is intentionally small and only supports an initial functional UI.
    try:
        with SessionLocal() as db:
            ensure_seed_stocks(db)
    except Exception:
        # Readiness exposes database failures; startup should not mask ECS diagnostics.
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    description="Grounded, cited RAG research for NSE/BSE investors. Not investment advice.",
)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_app_url],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(stocks.router, prefix=settings.api_prefix)
app.include_router(profile.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(chat.source_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/ready", tags=["health"])
def ready() -> dict[str, str]:
    with SessionLocal() as db:
        db.execute(text("SELECT 1"))
    return {"status": "ready", "service": "api"}
