"""Phase 2 acceptance: ingest + clean on the messy sample, plus unit tests for the parsers."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.pipeline.clean import (
    clean,
    clean_description,
    ingest_and_clean,
    parse_amount_cell,
    parse_date,
    parse_signed_amount,
)
from app.pipeline.ingest import detect_columns, ingest_csv

SAMPLE = Path(__file__).parent / "sample_statements" / "messy_sample.csv"

# Valid transactions expected from the sample (9 of 13 rows; 4 are non-transaction rows).
EXPECTED_TXN_COUNT = 9


# --- Column detection ----------------------------------------------------------------------


def test_detect_columns_maps_indian_statement_headers():
    headers = ["Txn Date", "Narration", "Chq/Ref No", "Withdrawal (Dr)", "Deposit (Cr)", "Closing Balance"]
    mapping, warnings = detect_columns(headers)
    assert mapping["date"] == "Txn Date"
    assert mapping["description"] == "Narration"
    assert mapping["debit"] == "Withdrawal (Dr)"
    assert mapping["credit"] == "Deposit (Cr)"
    assert mapping["balance"] == "Closing Balance"
    assert warnings == []


def test_ingest_reports_schema_and_confidence():
    result = ingest_csv(SAMPLE)
    assert result.report.total_rows == 13
    assert result.report.confidence == 1.0
    assert result.columns["date"] == "Txn Date"


# --- End-to-end clean on the sample --------------------------------------------------------


def test_clean_parses_expected_transaction_count():
    result = ingest_and_clean(SAMPLE)
    assert len(result.transactions) == EXPECTED_TXN_COUNT
    assert result.report.parsed_rows == EXPECTED_TXN_COUNT
    assert result.report.dropped_rows == 13 - EXPECTED_TXN_COUNT


def test_balance_header_and_total_rows_excluded():
    result = ingest_and_clean(SAMPLE)
    for txn in result.transactions:
        upper = txn.description_raw.upper()
        assert "OPENING BALANCE" not in upper
        assert "CLOSING BALANCE" not in upper
        assert upper != "TOTAL"


def test_dates_parsed_to_iso_across_formats():
    result = ingest_and_clean(SAMPLE)
    by_desc = {t.description_clean: t for t in result.transactions}
    # 02/01/2025 (DD/MM), 07 Jan 2025, 2025-01-10 all parse correctly
    assert by_desc["SWIGGY ORDER"].date == date(2025, 1, 2)
    assert by_desc["AMAZON INDIA PVT LTD"].date == date(2025, 1, 7)
    assert by_desc["NETFLIX COM SUBSCRIPTION"].date == date(2025, 1, 10)


def test_amounts_and_direction_reconciled():
    result = ingest_and_clean(SAMPLE)
    by_desc = {t.description_clean: t for t in result.transactions}

    swiggy = by_desc["SWIGGY ORDER"]
    assert swiggy.amount == 458.0
    assert swiggy.direction == "debit"

    salary = by_desc["ACME CORP SALARY JAN"]
    assert salary.amount == 85000.0
    assert salary.direction == "credit"

    rent = by_desc["HDFC RENT LANDLORD"]
    assert rent.amount == 25000.0
    assert rent.direction == "debit"


def test_description_clean_strips_noise():
    result = ingest_and_clean(SAMPLE)
    for txn in result.transactions:
        c = txn.description_clean
        assert "UPI" not in c.split()
        assert "@" not in c
        assert "REF" not in c.split()
        assert not any(ch.isdigit() for ch in c)  # no reference numbers survive
        assert c == c.upper()
        assert c  # never empty


# --- Unit tests: amount parsing ------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("₹1,23,456.78", 123456.78),
        ("5,000.00 Dr", 5000.0),
        ("(1,200.00)", 1200.0),
        ("Rs. 99.50", 99.50),
        ("499.00", 499.0),
        ("", None),
        ("   ", None),
        ("N/A", None),
        ("--", None),
    ],
)
def test_parse_amount_cell(raw, expected):
    assert parse_amount_cell(raw) == expected


@pytest.mark.parametrize(
    "raw,hint,expected",
    [
        ("₹500.00 Cr", None, (500.0, "credit")),
        ("1,000.00 Dr", None, (1000.0, "debit")),
        ("-500", None, (500.0, "debit")),
        ("(750.00)", None, (750.0, "debit")),
        ("2,500.00", "CR", (2500.0, "credit")),
        ("2,500.00", None, (2500.0, "debit")),  # unsigned defaults to debit
    ],
)
def test_parse_signed_amount(raw, hint, expected):
    assert parse_signed_amount(raw, hint) == expected


# --- Unit tests: date parsing --------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("12/01/2025", date(2025, 1, 12)),   # day-first
        ("05-01-2025", date(2025, 1, 5)),
        ("07 Jan 2025", date(2025, 1, 7)),
        ("2025-01-15", date(2025, 1, 15)),
        ("Txn Date", None),                   # header text
        ("", None),
        ("N/A", None),
    ],
)
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


# --- Unit tests: description cleaning ------------------------------------------------------


@pytest.mark.parametrize(
    "raw,must_contain,must_not_contain",
    [
        ("UPI/SWIGGY*ORDER/427183920@okhdfcbank/Payment from", "SWIGGY", "427183920"),
        ("NEFT-CR-ACME CORP SALARY JAN-REF99281", "ACME", "REF99281"),
        ("POS/AMAZON INDIA PVT LTD/REF8842", "AMAZON", "8842"),
        ("ACH/D/NETFLIX COM/SUBSCRIPTION/8829102", "NETFLIX", "ACH"),
    ],
)
def test_clean_description_extracts_merchant(raw, must_contain, must_not_contain):
    cleaned = clean_description(raw)
    assert must_contain in cleaned
    assert must_not_contain not in cleaned


def test_clean_description_never_empty():
    assert clean_description("") == "UNKNOWN"
    assert clean_description("UPI/99999/REF123") != ""  # over-stripped → fallback


def test_clean_returns_updated_report_counts():
    result = clean(ingest_csv(SAMPLE))
    assert result.report.parsed_rows + result.report.dropped_rows == result.report.total_rows
