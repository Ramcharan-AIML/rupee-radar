"""`GET /api/usage` — track token budget and rate limits.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import get_settings
from app.llm.budget import get_rolling_usage, would_exceed

router = APIRouter(prefix="/api", tags=["usage"])


class UsageResponse(BaseModel):
    used: int
    remaining: int
    provider: str
    degraded: bool
    per_minute: int
    per_day: int


@router.get("/usage", response_model=UsageResponse)
def get_usage() -> UsageResponse:
    """Retrieve current token consumption details, limits, and budget health."""
    settings = get_settings()
    usage = get_rolling_usage()

    used = usage["tpd"]
    budget = settings.llm_daily_token_budget
    remaining = max(0, budget - used)

    # If the provider is 'none' or budget is completely exhausted, we are in degraded mode.
    # Also if the next small prompt of 200 tokens would be blocked.
    degraded = not settings.llm_enabled or remaining <= 0
    if not degraded:
        blocked, _ = would_exceed(200)
        degraded = blocked

    return UsageResponse(
        used=used,
        remaining=remaining,
        provider=settings.llm_provider,
        degraded=degraded,
        per_minute=usage["tpm"],
        per_day=usage["tpd"],
    )
