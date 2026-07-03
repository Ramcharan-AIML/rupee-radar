import json
from datetime import date
from app.models.schemas import Metrics, RecurringGroup, Transaction
from app.pipeline.summary import build_compact_summary


def test_build_compact_summary():
    # Setup test transactions
    txns = [
        Transaction(
            date=date(2026, 6, 1),
            description_raw="UPI-Zomato",
            description_clean="ZOMATO",
            amount=450.0,
            direction="debit",
            category="Food",
        ),
        Transaction(
            date=date(2026, 6, 5),
            description_raw="UPI-RentPay",
            description_clean="RENTPAY",
            amount=15000.0,
            direction="debit",
            category="Rent",
        ),
    ]

    metrics = Metrics(
        total_income=20000.0,
        total_spend=15450.0,
        net_savings=4550.0,
        savings_rate=0.2275,
        top_categories=[("Rent", 15000.0), ("Food", 450.0)],
    )

    recurring = [
        RecurringGroup(
            merchant="RENTPAY",
            cadence="monthly",
            typical_amount=15000.0,
            occurrences=1,
            category="Rent",
        )
    ]

    summary_str = build_compact_summary(txns, metrics, recurring)
    parsed = json.loads(summary_str)

    # Assert totals
    assert parsed["totals"]["total_income"] == 20000.0
    assert parsed["totals"]["total_spend"] == 15450.0
    assert parsed["totals"]["net_savings"] == 4550.0
    assert parsed["totals"]["savings_rate_pct"] == 22.8

    # Assert categories
    assert len(parsed["categories"]) == 2
    assert parsed["categories"][0]["category"] == "Rent"
    assert parsed["categories"][0]["spend"] == 15000.0

    # Assert recurring
    assert len(parsed["recurring"]) == 1
    assert parsed["recurring"][0]["merchant"] == "RENTPAY"
    assert parsed["recurring"][0]["cadence"] == "monthly"

    # Assert top expenses
    assert len(parsed["top_expenses"]) == 2
    assert parsed["top_expenses"][0]["merchant"] == "RENTPAY"
    assert parsed["top_expenses"][0]["amount"] == 15000.0
