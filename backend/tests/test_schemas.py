"""Phase 1 acceptance: schemas serialize/deserialize round-trip; validators hold."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.constants import CANONICAL_CATEGORIES
from app.models.schemas import (
    Analysis,
    Metrics,
    RecurringGroup,
    SchemaReport,
    Transaction,
    UploadResponse,
)


def _sample_transaction(**overrides) -> Transaction:
    base = dict(
        date=date(2025, 1, 12),
        description_raw="UPI/SWIGGY*ORDER/427183920@okhdfcbank",
        description_clean="SWIGGY",
        amount=458.0,
        direction="debit",
        category="Food",
        category_source="rule",
        confidence=0.95,
    )
    base.update(overrides)
    return Transaction(**base)


def _sample_analysis() -> Analysis:
    txns = [
        _sample_transaction(),
        _sample_transaction(
            description_raw="NEFT-CR-SALARY JAN-ACME CORP",
            description_clean="SALARY ACME CORP",
            amount=85000.0,
            direction="credit",
            category="Salary",
        ),
    ]
    recurring = [
        RecurringGroup(
            merchant="NETFLIX",
            cadence="monthly",
            typical_amount=499.0,
            occurrences=3,
            category="Subscriptions",
        )
    ]
    metrics = Metrics(
        total_income=85000.0,
        total_spend=458.0,
        net_savings=84542.0,
        savings_rate=0.9946,
        top_categories=[("Food", 458.0)],
        biggest_transaction=txns[1],
        by_month={"2025-01": 458.0},
    )
    return Analysis(
        transactions=txns,
        recurring=recurring,
        metrics=metrics,
        insights=["Food was your biggest spend category at ₹458."],
    )


def test_transaction_round_trip():
    txn = _sample_transaction()
    restored = Transaction.model_validate_json(txn.model_dump_json())
    assert restored == txn


def test_analysis_round_trip_preserves_everything():
    analysis = _sample_analysis()
    restored = Analysis.model_validate_json(analysis.model_dump_json())
    assert restored == analysis
    # tuples survive the JSON (list) round-trip back into tuples
    assert restored.metrics.top_categories == [("Food", 458.0)]
    assert isinstance(restored.metrics.top_categories[0], tuple)


def test_upload_response_round_trip():
    resp = UploadResponse(
        session_id="abc123",
        analysis=_sample_analysis(),
        schema_report=SchemaReport(
            detected_columns={"date": "Txn Date", "amount": "Amount", "balance": None},
            total_rows=10,
            parsed_rows=8,
            dropped_rows=2,
            confidence=0.9,
            warnings=["2 balance rows skipped"],
        ),
    )
    restored = UploadResponse.model_validate_json(resp.model_dump_json())
    assert restored == resp


@pytest.mark.parametrize("category", CANONICAL_CATEGORIES)
def test_all_canonical_categories_accepted(category):
    assert _sample_transaction(category=category).category == category


def test_non_canonical_category_rejected():
    with pytest.raises(ValidationError):
        _sample_transaction(category="Groceries")


def test_negative_amount_rejected():
    with pytest.raises(ValidationError):
        _sample_transaction(amount=-1.0)


def test_empty_analysis_defaults_are_valid():
    analysis = Analysis()
    assert analysis.transactions == []
    assert analysis.metrics.biggest_transaction is None
    # default factory still gives a usable session id + timestamp
    assert analysis.session_id
    assert analysis.created_at is not None
