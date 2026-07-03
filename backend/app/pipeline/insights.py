"""[6] Insights — human-readable, amount-grounded spending insights (template baseline).

These are deterministic and built purely from computed `Metrics` (no LLM, no arithmetic in
prose beyond formatting the numbers code already produced). Always returns >= 3 insights for a
non-empty statement. Phase 10 adds an optional LLM "polish"/"generate" layer on top.
"""

from __future__ import annotations

from app.models.schemas import Metrics, Transaction


def _inr(amount: float) -> str:
    """Format a rupee amount with the ₹ symbol and thousands grouping (no decimals)."""
    return f"₹{amount:,.0f}"


def generate_insights(transactions: list[Transaction], metrics: Metrics) -> list[str]:
    """Return >= 3 plain-language insights citing real amounts (or a clear empty message)."""
    if not transactions:
        return [
            "No valid transactions were found in this statement. "
            "Try a different file or check the format."
        ]

    insights: list[str] = []

    # 1) Top spending category
    if metrics.top_categories and metrics.total_spend > 0:
        category, amount = metrics.top_categories[0]
        pct = round(amount / metrics.total_spend * 100)
        insights.append(
            f"Your biggest spending category was {category} at {_inr(amount)} "
            f"({pct}% of total spend)."
        )

    # 2) Total spend
    n_debits = sum(1 for t in transactions if t.direction == "debit")
    insights.append(
        f"You spent {_inr(metrics.total_spend)} across {n_debits} transaction(s) this period."
    )

    # 3) Savings (guarded for no-income / overspend)
    if metrics.total_income > 0:
        if metrics.net_savings >= 0:
            insights.append(
                f"You saved {_inr(metrics.net_savings)} — "
                f"{round(metrics.savings_rate * 100)}% of your {_inr(metrics.total_income)} income."
            )
        else:
            insights.append(
                f"You overspent by {_inr(abs(metrics.net_savings))} beyond your "
                f"{_inr(metrics.total_income)} income this period."
            )
    else:
        insights.append(
            "No income was detected this period, so a savings rate can't be calculated."
        )

    # 4) Biggest single expense
    if metrics.biggest_transaction is not None:
        bt = metrics.biggest_transaction
        insights.append(
            f"Your biggest single expense was {_inr(bt.amount)} to "
            f"{bt.description_clean.title()} on {bt.date:%d %b %Y}."
        )

    # 5) Subscriptions placeholder (real recurring totals arrive in Phase 6)
    subs = sum(
        t.amount for t in transactions
        if t.category == "Subscriptions" and t.direction == "debit"
    )
    if subs > 0:
        insights.append(
            f"You spent {_inr(subs)} on subscriptions. "
            "(Recurring detection will pin down exact monthly costs soon.)"
        )

    return insights
