"""[10] Monthly Written Narrative Briefing.

Calls the LLM provider to write a 1-2 paragraph analytical briefing about the statement summary,
caching results in SQLite.
"""

from __future__ import annotations

import logging
from app.config import get_settings
from app.store.db import get_db_conn

logger = logging.getLogger(__name__)


def generate_narrative(session_id: str, summary_json: str) -> str | None:
    """Generate a 1-2 paragraph written summary of the user's statement via LLM."""
    settings = get_settings()

    # 1. Check if narrative is disabled
    if not settings.llm_enable_narrative or not settings.llm_enabled:
        return None

    # 2. Check SQLite cache first
    cached = _get_cached_narrative(session_id)
    if cached is not None:
        return cached

    # 3. Resolve provider
    from app.llm.factory import get_llm_provider
    provider = get_llm_provider()
    if provider is None:
        return None

    system_prompt = (
        "You are an expert personal finance analyst. Analyze the provided summary metrics of "
        "a user's statement and write a highly professional, engaging, and clear monthly financial "
        "narrative briefing (exactly 1 to 2 paragraphs long).\n"
        "Focus on outlining the spending overview, highlights, anomalies, and actionable savings advice.\n"
        "Rules:\n"
        "- All figures and amounts cited MUST be strictly grounded in the summary.\n"
        "- Do NOT make up any numbers or execute math outside what is shown.\n"
        "- Start directly with the analysis. Do not include greetings, introductions, or conversational filler."
    )

    try:
        narrative = provider.complete(summary_json, system_prompt=system_prompt)
        narrative = narrative.strip()

        # Save to SQLite cache
        _set_cached_narrative(session_id, narrative)
        return narrative
    except Exception as err:
        logger.error("LLM narrative generation failed: %s", err)
        return None


def _get_cached_narrative(session_id: str) -> str | None:
    with get_db_conn() as conn:
        row = conn.execute(
            "SELECT narrative FROM insight_cache WHERE cache_key = ?", (session_id,)
        ).fetchone()
        if row and row["narrative"]:
            return row["narrative"]
    return None


def _set_cached_narrative(session_id: str, narrative: str) -> None:
    with get_db_conn() as conn:
        conn.execute(
            """
            INSERT INTO insight_cache (cache_key, insights, narrative)
            VALUES (?, '[]', ?)
            ON CONFLICT(cache_key) DO UPDATE SET narrative=excluded.narrative
            """,
            (session_id, narrative),
        )
