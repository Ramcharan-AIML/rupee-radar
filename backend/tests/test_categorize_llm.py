import os
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from app.config import get_settings
from app.models.schemas import Transaction
from app.pipeline.categorize import categorize_transactions
from app.store.db import init_db


@pytest.fixture(autouse=True)
def test_db():
    settings = get_settings()
    original_path = settings.db_path
    temp_path = "./data/test_categorize_llm_run.db"
    settings.db_path = temp_path

    init_db()

    yield

    settings.db_path = original_path

    for path in (temp_path, temp_path + "-wal", temp_path + "-shm"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def test_llm_fallback_classification_path():
    # Setup test transactions:
    # 1. Matches rule (ZOMATO -> Food)
    # 2. No rule match (XYZ -> Other/default)
    txns = [
        Transaction(
            date=date(2026, 1, 1),
            description_raw="UPI-ZOMATO-123",
            description_clean="ZOMATO",
            amount=250.0,
            direction="debit",
        ),
        Transaction(
            date=date(2026, 1, 2),
            description_raw="UPI-XYZ-MERCHANT",
            description_clean="XYZ",
            amount=500.0,
            direction="debit",
        ),
    ]

    mock_provider = MagicMock()
    mock_provider.classify_batch.return_value = {"XYZ": ("Shopping", 0.9)}

    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider):
        categorize_transactions(txns)

    # First txn matches rule-based categorization
    assert txns[0].category == "Food"
    assert txns[0].category_source == "rule"

    # Second txn falls back to LLM, hits mock provider, classifies as Shopping
    assert txns[1].category == "Shopping"
    assert txns[1].category_source == "llm"
    assert txns[1].confidence == 0.9

    # Mock provider should have been called with the uncached merchant
    mock_provider.classify_batch.assert_called_once_with(["XYZ"])


def test_caching_and_budget_blocks():
    txns = [
        Transaction(
            date=date(2026, 1, 1),
            description_raw="UPI-MERCH-A",
            description_clean="MERCH A",
            amount=10.0,
            direction="debit",
        ),
        Transaction(
            date=date(2026, 1, 2),
            description_raw="UPI-MERCH-A-REP",
            description_clean="MERCH A",  # Duplicate description
            amount=15.0,
            direction="debit",
        ),
    ]

    mock_provider = MagicMock()
    mock_provider.classify_batch.return_value = {"MERCH A": ("Bills", 0.95)}

    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider):
        # Run classification once: calls LLM and caches
        categorize_transactions(txns)

    assert txns[0].category == "Bills"
    assert txns[1].category == "Bills"
    mock_provider.classify_batch.assert_called_once_with(["MERCH A"])

    # Run again with a new list: should hit cache and NOT call the provider
    txns2 = [
        Transaction(
            date=date(2026, 1, 3),
            description_raw="UPI-MERCH-A-NEW",
            description_clean="MERCH A",
            amount=20.0,
            direction="debit",
        )
    ]
    mock_provider2 = MagicMock()
    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider2):
        categorize_transactions(txns2)

    assert txns2[0].category == "Bills"
    assert txns2[0].category_source == "llm"
    mock_provider2.classify_batch.assert_not_called()
