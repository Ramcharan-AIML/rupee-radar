"""Shared constants — the single source of truth for canonical categories.

Every part of the pipeline (rules, LLM fallback, defaults) must emit a category from this
list, and only this list. See edge-cases invariant #2.
"""

from __future__ import annotations

# The 10 canonical spending categories (context §7 / architecture §7).
CANONICAL_CATEGORIES: tuple[str, ...] = (
    "Food",
    "Travel",
    "Shopping",
    "Bills",
    "EMI",
    "Subscriptions",
    "Salary",
    "Rent",
    "Investments",
    "Other",
)

# Fallback category for anything unmatched / unknown.
DEFAULT_CATEGORY: str = "Other"

# Fast membership lookup.
CANONICAL_CATEGORY_SET: frozenset[str] = frozenset(CANONICAL_CATEGORIES)


def is_canonical(category: str) -> bool:
    """Return True if ``category`` is one of the canonical categories."""
    return category in CANONICAL_CATEGORY_SET


def coerce_category(category: str | None) -> str:
    """Map any value to a canonical category, falling back to ``DEFAULT_CATEGORY``.

    Used as a safety net for untrusted sources (e.g. LLM output) so a non-canonical label
    can never leak into the analysis.
    """
    if category and category in CANONICAL_CATEGORY_SET:
        return category
    return DEFAULT_CATEGORY
