"""[8] Token Budget Guard.

Enforces rolling window rate limits (RPM, TPM, RPD, TPD) and daily soft caps for Groq LLM calls.
Tracks actual consumption using the SQLite database.
"""

from __future__ import annotations

import time

from app.config import get_settings
from app.store.db import get_db_conn


def get_rolling_usage() -> dict[str, int]:
    """Calculate the rolling LLM usage for the last 60 seconds (RPM/TPM) and 24 hours (RPD/TPD)."""
    now = time.time()
    minute_ago = now - 60.0
    day_ago = now - 86400.0

    with get_db_conn() as conn:
        # Request / Token usage in the last 60 seconds
        min_row = conn.execute(
            """
            SELECT COUNT(*) as rpm, COALESCE(SUM(total_tokens), 0) as tpm
            FROM llm_usage
            WHERE timestamp >= ?
            """,
            (minute_ago,),
        ).fetchone()

        # Request / Token usage in the last 24 hours
        day_row = conn.execute(
            """
            SELECT COUNT(*) as rpd, COALESCE(SUM(total_tokens), 0) as tpd
            FROM llm_usage
            WHERE timestamp >= ?
            """,
            (day_ago,),
        ).fetchone()

        return {
            "rpm": min_row["rpm"],
            "tpm": min_row["tpm"],
            "rpd": day_row["rpd"],
            "tpd": day_row["tpd"],
        }


def would_exceed(projected_tokens: int) -> tuple[bool, str | None]:
    """Determine if a request with projected_tokens would breach limits.

    Checks soft budgets and provider rate limits.
    Returns (True, reason) if it exceeds, otherwise (False, None).
    """
    settings = get_settings()
    if not settings.llm_enabled:
        return True, "LLM provider is disabled or not configured"

    limits = settings.provider_limits
    usage = get_rolling_usage()

    # Soft daily budget constraint (applicable universally)
    if usage["tpd"] + projected_tokens > settings.llm_daily_token_budget:
        return (
            True,
            f"Daily token budget exceeded. Soft budget: {settings.llm_daily_token_budget}, "
            f"Current usage: {usage['tpd']}, Projected: {projected_tokens}.",
        )

    # Provider hard constraints
    if limits is not None:
        if usage["rpm"] + 1 > limits.requests_per_minute:
            return True, "Breaches RPM (Requests Per Minute) rate limit."
        if usage["tpm"] + projected_tokens > limits.tokens_per_minute:
            return True, "Breaches TPM (Tokens Per Minute) rate limit."
        if usage["rpd"] + 1 > limits.requests_per_day:
            return True, "Breaches RPD (Requests Per Day) rate limit."
        if usage["tpd"] + projected_tokens > limits.tokens_per_day:
            return True, "Breaches TPD (Tokens Per Day) rate limit."

    return False, None


def get_retry_after(projected_tokens: int) -> float:
    """Calculate wait time (in seconds) before projected_tokens will fit the limits.

    Returns 0.0 if the request fits immediately.
    """
    now = time.time()
    minute_ago = now - 60.0

    settings = get_settings()
    limits = settings.provider_limits

    # If no rate limits, we don't need back-off delays (e.g. Ollama)
    if not limits:
        return 0.0

    # Read last 60 seconds calls to calculate wait time
    with get_db_conn() as conn:
        calls = conn.execute(
            """
            SELECT timestamp, total_tokens
            FROM llm_usage
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
            """,
            (minute_ago,),
        ).fetchall()

    if not calls:
        return 0.0

    # 1. RPM wait: oldest request must fall out of the 60s window
    rpm_wait = 0.0
    if len(calls) >= limits.requests_per_minute:
        oldest_call_time = calls[0]["timestamp"]
        rpm_wait = max(0.0, (oldest_call_time + 60.0) - now)

    # 2. TPM wait: enough tokens must fall out of the 60s window to host projected_tokens
    tpm_wait = 0.0
    current_tokens = sum(c["total_tokens"] for c in calls)
    if current_tokens + projected_tokens > limits.tokens_per_minute:
        accumulated_tokens = current_tokens
        for c in calls:
            accumulated_tokens -= c["total_tokens"]
            if accumulated_tokens + projected_tokens <= limits.tokens_per_minute:
                tpm_wait = max(0.0, (c["timestamp"] + 60.0) - now)
                break
        else:
            tpm_wait = 60.0

    return max(rpm_wait, tpm_wait)


def record_usage(prompt_tokens: int, completion_tokens: int) -> None:
    """Record LLM token consumption into the SQLite database."""
    total = prompt_tokens + completion_tokens
    with get_db_conn() as conn:
        conn.execute(
            """
            INSERT INTO llm_usage (timestamp, prompt_tokens, completion_tokens, total_tokens)
            VALUES (?, ?, ?, ?)
            """,
            (time.time(), prompt_tokens, completion_tokens, total),
        )
