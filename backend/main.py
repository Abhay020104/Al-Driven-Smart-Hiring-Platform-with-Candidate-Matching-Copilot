"""
FastAPI application entry point.

Start with:
    uvicorn backend.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import Base, SessionLocal, engine
from backend.routers import (
    ai,
    ai_interview,
    auth,
    candidates,
    onboarding,
    roles,
    uploads,
)
from backend.seed import seed_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and seed data on startup."""
    # Import all models so Base.metadata knows about them
    import backend.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    yield  # application runs
    # Shutdown logic (if any) goes here


app = FastAPI(
    title="AI-Driven Smart Hiring Platform API",
    description="Backend API for the AI Recruitment Copilot — roles, candidates, and AI-powered features.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(roles.router)
app.include_router(candidates.router)
app.include_router(ai.router)
app.include_router(uploads.router)
app.include_router(onboarding.router)
app.include_router(ai_interview.router)


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "AI-Driven Smart Hiring Platform API"}
