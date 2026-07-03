"""[3] Categorize — assign each transaction a canonical category.

First pass (this phase): deterministic rules (`rules.py`). Anything the rules can't confidently
classify stays `Other` with `category_source="default"`.

Second pass (Phase 9): an optional, token-frugal LLM fallback fills in the `Other`/low-
confidence transactions. For now that hook is a no-op so the pipeline runs with zero tokens.
"""

from typing import Optional

from app.constants import DEFAULT_CATEGORY, coerce_category
from app.models.schemas import Transaction
from app.pipeline.rules import match_category
from app.llm.provider import LLMProvider


def categorize_transactions(
    transactions: list[Transaction], provider: Optional[LLMProvider] = None
) -> list[Transaction]:
    """Categorize transactions in place (and return them).

    First pass: applies local regex/keyword rules.
    Second pass: calls the LLM provider fallback for remaining unclassified transactions.
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


def _llm_fallback(transactions: list[Transaction], provider: Optional[LLMProvider]) -> None:
    """LLM fallback pass: batches and classifies remaining uncached and 'Other' transactions."""
    if provider is None:
        from app.llm.factory import get_llm_provider
        provider = get_llm_provider()
    if provider is None:
        return

    import logging
    from app.config import get_settings
    from app.llm.cache import get_cached_category, set_cached_category
    from app.llm.budget import would_exceed

    logger = logging.getLogger(__name__)
    settings = get_settings()

    # Find transactions requiring fallback classification
    fallback_txns = [t for t in transactions if t.category == DEFAULT_CATEGORY or t.category_source == "default"]
    if not fallback_txns:
        return

    # Extract unique merchant tokens
    unique_merchants = list({t.description_clean for t in fallback_txns if t.description_clean})
    if not unique_merchants:
        return

    # Check cache first
    uncached_merchants = []
    for merchant in unique_merchants:
        cached = get_cached_category(merchant)
        if cached:
            cat, conf = cached
            for t in fallback_txns:
                if t.description_clean == merchant:
                    t.category = coerce_category(cat)
                    t.category_source = "llm"
                    t.confidence = conf
        else:
            uncached_merchants.append(merchant)

    if not uncached_merchants:
        return

    # Batch process remaining merchants through the LLM provider
    batch_size = settings.llm_categorize_batch
    for i in range(0, len(uncached_merchants), batch_size):
        batch = uncached_merchants[i : i + batch_size]

        # Pre-flight token budget check
        blocked, reason = would_exceed(settings.llm_max_tokens_per_call)
        if blocked:
            logger.warning("LLM Categorization batch blocked by budget guard: %s", reason)
            break

        try:
            classifications = provider.classify_batch(batch)
            for merchant in batch:
                if merchant in classifications:
                    cat, conf = classifications[merchant]
                    canonical_cat = coerce_category(cat)
                    set_cached_category(merchant, canonical_cat, conf)

                    for t in fallback_txns:
                        if t.description_clean == merchant:
                            t.category = canonical_cat
                            t.category_source = "llm"
                            t.confidence = conf
        except Exception as err:
            logger.error("LLM fallback categorization failed: %s", err)
            break

