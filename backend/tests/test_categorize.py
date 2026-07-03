"""Phase 3 acceptance: rule-based categorization on the sample + targeted edge cases."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.constants import CANONICAL_CATEGORY_SET
from app.models.schemas import Transaction
from app.pipeline.categorize import categorize_transactions
from app.pipeline.clean import ingest_and_clean
from app.pipeline.rules import match_category

SAMPLE = Path(__file__).parent / "sample_statements" / "messy_sample.csv"


def _txn(description_clean: str, direction: str = "debit") -> Transaction:
    return Transaction(
        date=date(2025, 1, 1),
        description_raw=description_clean,
        description_clean=description_clean,
        amount=100.0,
        direction=direction,
    )


# --- End-to-end on the sample --------------------------------------------------------------


def test_sample_categories_match_expected():
    result = ingest_and_clean(SAMPLE)
    categorize_transactions(result.transactions)
    by_desc = {t.description_clean: t.category for t in result.transactions}

    assert by_desc["SWIGGY ORDER"] == "Food"
    assert by_desc["ACME CORP SALARY JAN"] == "Salary"
    assert by_desc["AMAZON INDIA PVT LTD"] == "Shopping"
    assert by_desc["NETFLIX COM SUBSCRIPTION"] == "Subscriptions"
    assert by_desc["HDFC RENT LANDLORD"] == "Rent"
    assert by_desc["ZOMATO ORDER"] == "Food"
    assert by_desc["UBER INDIA TRIP"] == "Travel"
    assert by_desc["ZERODHA SIP MUTUAL FUND"] == "Investments"


def test_matched_transactions_have_rule_source():
    result = ingest_and_clean(SAMPLE)
    categorize_transactions(result.transactions)
    swiggy = next(t for t in result.transactions if t.description_clean == "SWIGGY ORDER")
    assert swiggy.category_source == "rule"
    assert swiggy.confidence > 0


def test_unknown_falls_back_to_other_default():
    result = ingest_and_clean(SAMPLE)
    categorize_transactions(result.transactions)
    cash = next(t for t in result.transactions if "CASH WITHDRAWAL" in t.description_clean)
    assert cash.category == "Other"
    assert cash.category_source == "default"
    assert cash.confidence == 0.0


def test_every_category_is_canonical():
    result = ingest_and_clean(SAMPLE)
    categorize_transactions(result.transactions)
    for txn in result.transactions:
        assert txn.category in CANONICAL_CATEGORY_SET


# --- Targeted rule edge cases --------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("SWIGGY ORDER", "Food"),
        ("NETFLIX SUBSCRIPTION", "Subscriptions"),
        ("UBER INDIA TRIP", "Travel"),
        ("INDIAN OIL PETROL PUMP", "Travel"),
        ("BESCOM ELECTRICITY BILL", "Bills"),
        ("AIRTEL PREPAID RECHARGE", "Bills"),
        ("FLIPKART INTERNET", "Shopping"),
        ("HDFC HOME LOAN", "EMI"),
        ("ZERODHA BROKING SIP MUTUAL FUND", "Investments"),
    ],
)
def test_match_category_known_merchants(text, expected):
    match = match_category(text, "debit")
    assert match is not None and match[0] == expected


def test_amazon_prime_precedence_over_shopping():
    # Subscriptions rule is ordered before Shopping → AMAZON PRIME must be Subscriptions.
    match = match_category("AMAZON PRIME MEMBERSHIP", "debit")
    assert match is not None and match[0] == "Subscriptions"


def test_rent_does_not_match_rental():
    # Word-boundary guard: "RENTAL" must not be categorized as Rent.
    match = match_category("RENTAL CAR BOOKING", "debit")
    assert match is None or match[0] != "Rent"


def test_salary_only_on_credit():
    assert match_category("INFOSYS SALARY", "credit")[0] == "Salary"
    # A debit containing "salary" must not be classified as Salary income.
    assert match_category("SALARY ADVANCE REPAYMENT", "debit") != ("Salary", 0.95)


def test_no_match_returns_none():
    assert match_category("XYZ ENTERPRISES", "debit") is None
    assert match_category("APOLLO PHARMACY", "debit") is None
    assert match_category("", "debit") is None
