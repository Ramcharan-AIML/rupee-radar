"""[8] Category and Insight Cache.

Handles caching LLM outputs in SQLite to minimize network calls and control token consumption.
"""

from __future__ import annotations

from app.store.db import get_db_conn


def get_cached_category(description_clean: str) -> tuple[str, float] | None:
    """Retrieve the cached category and confidence for a cleaned description.

    Returns None if there is a cache miss.
    """
    with get_db_conn() as conn:
        row = conn.execute(
            """
            SELECT category, confidence
            FROM category_cache
            WHERE description_clean = ?
            """,
            (description_clean,),
        ).fetchone()

        if row:
            return row["category"], row["confidence"]
        return None


def set_cached_category(description_clean: str, category: str, confidence: float) -> None:
    """Save a category classification and confidence to the SQLite cache."""
    with get_db_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO category_cache (description_clean, category, confidence)
            VALUES (?, ?, ?)
            """,
            (description_clean, category, confidence),
        )
