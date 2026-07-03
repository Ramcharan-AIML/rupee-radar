"""Health-check endpoint.

`GET /api/health` reports liveness plus the current LLM provider status so the frontend can
show whether AI features are available (and degrade gracefully when they are not).
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.config import get_settings

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
    llm_enabled: bool
    model: str


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        llm_provider=settings.llm_provider,
        llm_enabled=settings.llm_enabled,
        model=settings.active_model,
    )
