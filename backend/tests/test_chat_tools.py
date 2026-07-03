import os
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from app.config import get_settings
from app.models.schemas import Analysis, Metrics, Transaction
from app.store.db import init_db
from app.store.repository import save_analysis
from app.analyst.tools import get_category_breakdown, get_metrics, search_transactions
from app.analyst.chat import interact


@pytest.fixture(autouse=True)
def test_db():
    settings = get_settings()
    original_path = settings.db_path
    temp_path = "./data/test_chat_tools_run.db"
    settings.db_path = temp_path

    init_db()

    # Configure provider for test settings
    original_provider = settings.llm_provider
    original_key = settings.groq_api_key
    settings.llm_provider = "groq"
    settings.groq_api_key = "test_key"

    yield

    settings.db_path = original_path
    settings.llm_provider = original_provider
    settings.groq_api_key = original_key

    for path in (temp_path, temp_path + "-wal", temp_path + "-shm"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def test_chat_grounding_tools():
    # Insert an analysis session
    txn1 = Transaction(
        date=date(2026, 6, 1),
        description_raw="UPI-ZOMATO-ORDER",
        description_clean="ZOMATO",
        amount=350.0,
        direction="debit",
        category="Food",
    )
    txn2 = Transaction(
        date=date(2026, 6, 2),
        description_raw="HDFC SALARY NEFT",
        description_clean="SALARY",
        amount=50000.0,
        direction="credit",
        category="Salary",
    )
    metrics = Metrics(
        total_income=50000.0,
        total_spend=350.0,
        net_savings=49650.0,
        savings_rate=0.993,
        top_categories=[("Food", 350.0)],
    )
    analysis = Analysis(
        session_id="chat-session-1",
        transactions=[txn1, txn2],
        metrics=metrics,
        insights=[],
    )
    save_analysis(analysis)

    # 1. Test get_metrics
    metrics_str = get_metrics("chat-session-1")
    assert "Total Spend: INR 350.00" in metrics_str
    assert "Total Income: INR 50,000.00" in metrics_str

    # 2. Test get_category_breakdown
    breakdown_str = get_category_breakdown("chat-session-1")
    assert "Food: INR 350.00" in breakdown_str

    # 3. Test search_transactions
    search_str = search_transactions("chat-session-1", "zomato")
    assert "ZOMATO" in search_str
    assert "-INR 350.00" in search_str


def test_chat_interaction_orchestrator():
    # Insert session
    txn = Transaction(
        date=date(2026, 6, 1),
        description_raw="UPI-Netflix",
        description_clean="NETFLIX",
        amount=199.0,
        direction="debit",
        category="Subscriptions",
    )
    analysis = Analysis(
        session_id="chat-session-2",
        transactions=[txn],
        metrics=Metrics(total_spend=199.0),
    )
    save_analysis(analysis)

    mock_provider = MagicMock()
    # Mock first call (tool selection): selects search_transactions
    mock_provider.complete.return_value = '{"tool": "search_transactions", "arguments": {"query": "NETFLIX"}}'
    # Mock second call (final answer formulation)
    mock_provider.chat.return_value = "You spent INR 199.00 on Netflix."

    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider):
        res = interact("chat-session-2", "How much did I spend on Netflix?", [])

    assert res["answer"] == "You spent INR 199.00 on Netflix."
    assert "search_transactions(query='NETFLIX')" in res["used_tools"]

    # Verify model calls
    mock_provider.complete.assert_called_once()
    mock_provider.chat.assert_called_once()
