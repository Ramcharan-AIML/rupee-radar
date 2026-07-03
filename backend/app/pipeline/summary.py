"""[10] Compact Summary Generator.

Compiles transaction metrics into a compact text block to send to the LLM (summaries only).
No raw transaction lists are sent, protecting tokens and privacy.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.schemas import Metrics, RecurringGroup, Transaction


def build_compact_summary(
    transactions: list[Transaction], metrics: Metrics, recurring: list[RecurringGroup]
) -> str:
    """Format overall statement metrics into a dense, token-frugal text summary."""
    # 1. Base metrics
    summary: dict[str, any] = {
        "totals": {
            "total_income": round(metrics.total_income, 2),
            "total_spend": round(metrics.total_spend, 2),
            "net_savings": round(metrics.net_savings, 2),
            "savings_rate_pct": round(metrics.savings_rate * 100, 1),
        },
        "categories": [
            {"category": cat, "spend": round(amt, 2)} for cat, amt in metrics.top_categories
        ],
        "recurring": [
            {
                "merchant": r.merchant,
                "cadence": r.cadence,
                "typical_amount": round(r.typical_amount, 2),
                "category": r.category,
            }
            for r in recurring
        ],
    }

    # 2. Get top 5 largest debit transactions
    debits = [t for t in transactions if t.direction == "debit"]
    debits_sorted = sorted(debits, key=lambda x: x.amount, reverse=True)
    summary["top_expenses"] = [
        {
            "merchant": t.description_clean,
            "amount": round(t.amount, 2),
            "category": t.category,
            "date": t.date.isoformat(),
        }
        for t in debits_sorted[:5]
    ]

    return json.dumps(summary, indent=2)
