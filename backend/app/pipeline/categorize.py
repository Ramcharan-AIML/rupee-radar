"""[3] Categorize — assign each transaction a canonical category.

First pass (this phase): deterministic rules (`rules.py`). Anything the rules can't confidently
classify stays `Other` with `category_source="default"`.

Second pass (Phase 9): an optional, token-frugal LLM fallback fills in the `Other`/low-
confidence transactions. For now that hook is a no-op so the pipeline runs with zero tokens.
"""

from __future__ import annotations

from typing import Optional

from app.constants import DEFAULT_CATEGORY, coerce_category
from app.models.schemas import Transaction
from app.pipeline.rules import match_category


def categorize_transactions(
    transactions: list[Transaction], provider: Optional[object] = None
) -> list[Transaction]:
    """Categorize transactions in place (and return them).

    ``provider`` is accepted for forward-compatibility with the Phase 9 LLM fallback; it is
    ignored here.
    """
    for txn in transactions:
        match = match_category(txn.description_clean, txn.direction)
        if match is not None:
            category, confidence = match
            txn.category = coerce_category(category)  # safety net: never non-canonical
            txn.category_source = "rule"
            txn.confidence = confidence
        else:
            txn.category = DEFAULT_CATEGORY
            txn.category_source = "default"
            txn.confidence = 0.0

    _llm_fallback(transactions, provider)
    return transactions


def _llm_fallback(transactions: list[Transaction], provider: Optional[object]) -> None:
    """No-op placeholder for the Phase 9 LLM fallback (rules-first, deduped, batched, cached).

    Intentionally does nothing in Phase 3 so categorization stays deterministic and free.
    """
    return None
