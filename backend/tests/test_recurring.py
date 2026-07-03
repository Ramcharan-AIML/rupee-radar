from datetime import date
from app.models.schemas import Transaction
from app.pipeline.recurring import detect_recurring_payments


def test_detect_monthly_recurring():
    # 3 monthly transactions to the same merchant with stable amounts
    txns = [
        Transaction(
            date=date(2026, 1, 1),
            description_raw="UPI-Netflix-1",
            description_clean="NETFLIX",
            amount=199.00,
            direction="debit",
            category="Subscriptions",
        ),
        Transaction(
            date=date(2026, 2, 1),
            description_raw="UPI-Netflix-2",
            description_clean="NETFLIX",
            amount=199.00,
            direction="debit",
            category="Subscriptions",
        ),
        Transaction(
            date=date(2026, 3, 3),  # 30 days gap approx
            description_raw="UPI-Netflix-3",
            description_clean="NETFLIX",
            amount=199.00,
            direction="debit",
            category="Subscriptions",
        ),
    ]

    groups = detect_recurring_payments(txns)
    assert len(groups) == 1
    g = groups[0]
    assert g.merchant == "NETFLIX"
    assert g.cadence == "monthly"
    assert g.typical_amount == 199.00
    assert g.occurrences == 3
    assert g.category == "Subscriptions"

    # Verify transactions mutated
    assert all(t.is_recurring for t in txns)
    assert all(t.recurring_group_id == g.id for t in txns)


def test_reject_unstable_amounts():
    # Transactions to the same merchant but widely different amounts
    txns = [
        Transaction(
            date=date(2026, 1, 1),
            description_raw="UPI-Zomato-1",
            description_clean="ZOMATO",
            amount=200.00,
            direction="debit",
            category="Food",
        ),
        Transaction(
            date=date(2026, 1, 8),
            description_raw="UPI-Zomato-2",
            description_clean="ZOMATO",
            amount=1200.00,  # Huge amount difference
            direction="debit",
            category="Food",
        ),
        Transaction(
            date=date(2026, 1, 15),
            description_raw="UPI-Zomato-3",
            description_clean="ZOMATO",
            amount=150.00,
            direction="debit",
            category="Food",
        ),
    ]

    groups = detect_recurring_payments(txns)
    assert len(groups) == 0
    assert all(not t.is_recurring for t in txns)


def test_detect_weekly_recurring():
    txns = [
        Transaction(
            date=date(2026, 1, 1),
            description_raw="Weekly Groceries 1",
            description_clean="SUPERMARKET",
            amount=1500.00,
            direction="debit",
            category="Food",
        ),
        Transaction(
            date=date(2026, 1, 8),
            description_raw="Weekly Groceries 2",
            description_clean="SUPERMARKET",
            amount=1510.00,  # Small deviation (CoV <= 0.15)
            direction="debit",
            category="Food",
        ),
        Transaction(
            date=date(2026, 1, 15),
            description_raw="Weekly Groceries 3",
            description_clean="SUPERMARKET",
            amount=1490.00,
            direction="debit",
            category="Food",
        ),
    ]

    groups = detect_recurring_payments(txns)
    assert len(groups) == 1
    assert groups[0].cadence == "weekly"
    assert groups[0].typical_amount == 1500.00  # mean is 1500
