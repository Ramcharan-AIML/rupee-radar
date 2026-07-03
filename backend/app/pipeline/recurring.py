"""[6] Recurring Payment Detection.

Heuristics to group transactions by merchant, check amount stability, and infer cadence.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.models.schemas import RecurringGroup

if TYPE_CHECKING:
    from app.models.schemas import Cadence, Transaction


def detect_recurring_payments(transactions: list[Transaction]) -> list[RecurringGroup]:
    """Analyze debit transactions to group them and detect recurring payments.

    A recurring group must have:
    - At least 2 occurrences.
    - Stable amounts (Coefficient of Variation <= 0.15).
    - Inferred cadence based on average date gaps.

    Mutates transaction objects to set `is_recurring = True` and `recurring_group_id`.
    """
    debits = [t for t in transactions if t.direction == "debit"]
    groups: dict[str, list[Transaction]] = {}
    for t in debits:
        if t.description_clean:
            groups.setdefault(t.description_clean, []).append(t)

    recurring_groups: list[RecurringGroup] = []

    for merchant, txns in groups.items():
        if len(txns) < 2:
            continue

        # Sort chronologically
        txns_sorted = sorted(txns, key=lambda x: x.date)

        # Compute gaps in days
        gaps = [(txns_sorted[i].date - txns_sorted[i - 1].date).days for i in range(1, len(txns_sorted))]

        # Amount stability analysis (Coefficient of Variation)
        amounts = [t.amount for t in txns_sorted]
        n = len(amounts)
        mean_amount = sum(amounts) / n
        variance = sum((x - mean_amount) ** 2 for x in amounts) / n
        std_dev = math.sqrt(variance)
        cov = std_dev / mean_amount if mean_amount > 0 else 0.0

        if cov > 0.15:
            # Amounts vary too much to be recurring subscriptions / EMIs / rent
            continue

        # Infer cadence based on gaps
        mean_gap = sum(gaps) / len(gaps)

        if len(gaps) > 1:
            gap_variance = sum((g - mean_gap) ** 2 for g in gaps) / len(gaps)
            gap_std = math.sqrt(gap_variance)
            # If standard deviation of gaps is high (relative to mean), it's irregular
            if mean_gap > 0 and (gap_std / mean_gap) > 0.4:
                cadence: Cadence = "irregular"
            else:
                cadence = _infer_cadence_from_gap(mean_gap)
        else:
            cadence = _infer_cadence_from_gap(mean_gap)

        # Determine dominant category
        categories = [t.category for t in txns_sorted]
        dominant_category = max(set(categories), key=categories.count)

        rec_group = RecurringGroup(
            merchant=merchant,
            cadence=cadence,
            typical_amount=round(mean_amount, 2),
            occurrences=n,
            category=dominant_category,
        )
        recurring_groups.append(rec_group)

        # Update individual transactions
        for t in txns:
            t.is_recurring = True
            t.recurring_group_id = rec_group.id

    return recurring_groups


def _infer_cadence_from_gap(mean_gap: float) -> Cadence:
    if 5 <= mean_gap <= 10:
        return "weekly"
    if 25 <= mean_gap <= 35:
        return "monthly"
    if 75 <= mean_gap <= 105:
        return "quarterly"
    if 335 <= mean_gap <= 395:
        return "yearly"
    return "irregular"
