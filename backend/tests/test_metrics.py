"""Phase 4 acceptance: metrics computation + insight generation, incl. edge cases."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.models.schemas import Metrics, Transaction
from app.pipeline.categorize import categorize_transactions
from app.pipeline.clean import ingest_and_clean
from app.pipeline.insights import generate_insights
from app.pipeline.metrics import compute_metrics

SAMPLE = Path(__file__).parent / "sample_statements" / "messy_sample.csv"


def _txn(amount, direction, category="Other", d=date(2025, 1, 1), desc="X") -> Transaction:
    return Transaction(
        date=d, description_raw=desc, description_clean=desc,
        amount=amount, direction=direction, category=category,
    )


def _analyzed_sample() -> list[Transaction]:
    result = ingest_and_clean(SAMPLE)
    categorize_transactions(result.transactions)
    return result.transactions


# --- Metrics on the sample -----------------------------------------------------------------


def test_totals_reconcile():
    m = compute_metrics(_analyzed_sample())
    assert m.total_income == pytest.approx(85_000.0)
    assert m.total_spend == pytest.approx(43_210.5)
    assert m.net_savings == pytest.approx(m.total_income - m.total_spend)


def test_savings_rate_between_0_and_1():
    m = compute_metrics(_analyzed_sample())
    assert 0.0 < m.savings_rate < 1.0


def test_top_categories_sorted_desc():
    m = compute_metrics(_analyzed_sample())
    amounts = [amt for _, amt in m.top_categories]
    assert amounts == sorted(amounts, reverse=True)
    assert m.top_categories[0][0] == "Rent"  # 25,000 is the largest category


def test_biggest_transaction_is_largest_debit():
    m = compute_metrics(_analyzed_sample())
    assert m.biggest_transaction is not None
    assert m.biggest_transaction.amount == pytest.approx(25_000.0)
    assert m.biggest_transaction.direction == "debit"


def test_by_month_present():
    m = compute_metrics(_analyzed_sample())
    assert "2025-01" in m.by_month


# --- Metrics edge cases --------------------------------------------------------------------


def test_empty_transactions_gives_zero_metrics():
    m = compute_metrics([])
    assert m.total_income == 0 and m.total_spend == 0 and m.net_savings == 0
    assert m.savings_rate == 0.0
    assert m.biggest_transaction is None
    assert m.top_categories == []


def test_no_income_does_not_divide_by_zero():
    m = compute_metrics([_txn(500, "debit"), _txn(200, "debit")])
    assert m.total_income == 0
    assert m.savings_rate == 0.0  # guarded
    assert m.net_savings == -700


def test_biggest_transaction_tie_breaks_on_latest_date():
    txns = [
        _txn(1000, "debit", d=date(2025, 1, 5), desc="EARLY"),
        _txn(1000, "debit", d=date(2025, 1, 20), desc="LATE"),
    ]
    m = compute_metrics(txns)
    assert m.biggest_transaction.description_clean == "LATE"


# --- Insights ------------------------------------------------------------------------------


def test_insights_at_least_three_and_cite_amounts():
    txns = _analyzed_sample()
    insights = generate_insights(txns, compute_metrics(txns))
    assert len(insights) >= 3
    assert any(any(ch.isdigit() for ch in line) for line in insights)


def test_insights_empty_statement_message():
    insights = generate_insights([], Metrics())
    assert len(insights) == 1
    assert "No valid transactions" in insights[0]


def test_insights_no_nan_or_none_text():
    txns = _analyzed_sample()
    for line in generate_insights(txns, compute_metrics(txns)):
        assert "None" not in line and "nan" not in line.lower()
