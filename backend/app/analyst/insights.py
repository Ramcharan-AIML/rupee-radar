"""[10] LLM-Powered Analyst Insights.

Wraps the template-based insights and applies an LLM polish/generation layer,
caching results in SQLite.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from app.config import get_settings
from app.store.db import get_db_conn

if TYPE_CHECKING:
    from app.models.schemas import Metrics, Transaction

logger = logging.getLogger(__name__)


def generate_analyst_insights(
    session_id: str,
    transactions: list[Transaction],
    metrics: Metrics,
    summary_json: str,
) -> list[str]:
    """Return a list of financial insights, using the LLM for polishing/generation if enabled."""
    from app.pipeline.insights import generate_insights as generate_base_insights

    settings = get_settings()
    base_insights = generate_base_insights(transactions, metrics)

    # 1. If LLM insights are disabled, return base templates immediately
    if settings.llm_insight_mode == "off" or not settings.llm_enabled:
        return base_insights

    # 2. Check SQLite cache first
    cached_insights = _get_cached_insights(session_id)
    if cached_insights is not None:
        return cached_insights

    # 3. Resolve LLM provider
    from app.llm.factory import get_llm_provider
    provider = get_llm_provider()
    if provider is None:
        return base_insights

    try:
        if settings.llm_insight_mode == "polish":
            insights = _polish_insights(provider, base_insights)
        else:  # "generate"
            insights = _generate_fresh_insights(provider, summary_json)

        # Cache results in DB
        _set_cached_insights(session_id, insights)
        return insights
    except Exception as err:
        logger.error("LLM insights generation failed, falling back to base templates: %s", err)
        return base_insights


def _polish_insights(provider: any, base_insights: list[str]) -> list[str]:
    """Use the LLM to rewrite the deterministic template insights cohesively."""
    system_prompt = (
        "You are a professional personal finance analyst. Polish and rewrite the list of "
        "template-generated spending insights to read naturally, cohesively, and professionally.\n"
        "Rules:\n"
        "- Do NOT modify or hallucinate any numbers, categories, or names.\n"
        "- Do NOT perform any arithmetic calculations.\n"
        "- Keep exactly the same number of insights.\n"
        "- Respond with a JSON object matching this schema:\n"
        '{\n  "insights": ["Polished insight 1", "Polished insight 2"]\n}'
    )

    prompt = f"Base insights to polish:\n{json.dumps(base_insights)}"

    raw_content = provider.complete(prompt, system_prompt=system_prompt)
    parsed = json.loads(_clean_json_text(raw_content))
    return parsed["insights"]


def _generate_fresh_insights(provider: any, summary_json: str) -> list[str]:
    """Use the LLM to generate analytical spending insights from the summary metrics."""
    system_prompt = (
        "You are an expert personal finance analyst. Analyze the provided summary metrics of "
        "a user's statement and generate exactly 3 to 5 highly specific, actionable spending insights "
        "(e.g., highlighting anomalies, potential cash leaks, or savings advice).\n"
        "Rules:\n"
        "- All figures and amounts cited MUST be strictly grounded in the summary.\n"
        "- Do NOT make up any numbers or execute math outside what is shown.\n"
        "- Respond with a JSON object matching this schema:\n"
        '{\n  "insights": ["Actionable insight 1", "Actionable insight 2"]\n}'
    )

    raw_content = provider.complete(summary_json, system_prompt=system_prompt)
    parsed = json.loads(_clean_json_text(raw_content))
    return parsed["insights"]


def _get_cached_insights(session_id: str) -> list[str] | None:
    with get_db_conn() as conn:
        row = conn.execute(
            "SELECT insights FROM insight_cache WHERE cache_key = ?", (session_id,)
        ).fetchone()
        if row:
            return json.loads(row["insights"])
    return None


def _set_cached_insights(session_id: str, insights: list[str]) -> None:
    with get_db_conn() as conn:
        conn.execute(
            """
            INSERT INTO insight_cache (cache_key, insights, narrative)
            VALUES (?, ?, NULL)
            ON CONFLICT(cache_key) DO UPDATE SET insights=excluded.insights
            """,
            (session_id, json.dumps(insights)),
        )


def _clean_json_text(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
