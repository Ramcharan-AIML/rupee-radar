"""[5] Metrics — compute financial figures deterministically (architecture §0a: code does math).

All numbers shown anywhere in the app originate here. Guards cover the empty / no-income /
no-spend edge cases so we never divide by zero or emit NaN.
"""

from __future__ import annotations

from app.models.schemas import Metrics, Transaction


def compute_metrics(transactions: list[Transaction]) -> Metrics:
    """Compute totals, savings, top categories, biggest expense, and monthly spend."""
    if not transactions:
        return Metrics()

    debits = [t for t in transactions if t.direction == "debit"]
    credits = [t for t in transactions if t.direction == "credit"]

    total_income = sum(t.amount for t in credits)
    total_spend = sum(t.amount for t in debits)
    net_savings = total_income - total_spend
    savings_rate = (net_savings / total_income) if total_income > 0 else 0.0

    # Spend grouped by category (debits only), sorted desc; ties broken by name for determinism.
    cat_totals: dict[str, float] = {}
    for t in debits:
        cat_totals[t.category] = cat_totals.get(t.category, 0.0) + t.amount
    top_categories = sorted(cat_totals.items(), key=lambda kv: (-kv[1], kv[0]))

    # Biggest single expense (debit). Tie → most recent date (deterministic).
    biggest_transaction = (
        max(debits, key=lambda t: (t.amount, t.date)) if debits else None
    )

    # Spend per calendar month, keyed "YYYY-MM".
    by_month: dict[str, float] = {}
    for t in debits:
        key = t.date.strftime("%Y-%m")
        by_month[key] = by_month.get(key, 0.0) + t.amount

    return Metrics(
        total_income=total_income,
        total_spend=total_spend,
        net_savings=net_savings,
        savings_rate=savings_rate,
        top_categories=top_categories,
        biggest_transaction=biggest_transaction,
        by_month=dict(sorted(by_month.items())),
    )
