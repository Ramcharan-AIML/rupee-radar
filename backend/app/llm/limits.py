"""Authoritative provider rate limits.

Single source of truth for the free-tier ceilings the budget guard (Phase 8) must enforce.
All four windows matter, but for ``llama-3.3-70b-versatile`` the **tokens-per-minute (1,000)**
limit is by far the tightest — it dictates how small each request must be.

These can be overridden per-account via env settings (see `config.py`).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimits:
    """Rolling-window ceilings for an LLM provider/model."""

    requests_per_minute: int
    tokens_per_minute: int
    requests_per_day: int
    tokens_per_day: int


# Known Groq free-tier limits, keyed by model id.
GROQ_LIMITS: dict[str, RateLimits] = {
    "llama-3.3-70b-versatile": RateLimits(
        requests_per_minute=30,
        tokens_per_minute=1_000,   # binding constraint
        requests_per_day=12_000,
        tokens_per_day=100_000,
    ),
}

# Fallback used when a specific Groq model isn't in the table above.
_GROQ_DEFAULT = RateLimits(
    requests_per_minute=30,
    tokens_per_minute=1_000,
    requests_per_day=12_000,
    tokens_per_day=100_000,
)


def limits_for(provider: str, model: str) -> RateLimits | None:
    """Return the rate limits for a provider/model.

    Returns ``None`` for providers without enforced limits (``ollama`` runs locally, ``none``
    makes no calls) — i.e. effectively unlimited.
    """
    if provider == "groq":
        return GROQ_LIMITS.get(model, _GROQ_DEFAULT)
    return None
