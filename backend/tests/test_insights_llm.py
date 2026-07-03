import os
from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from app.config import get_settings
from app.models.schemas import Metrics, Transaction
from app.analyst.insights import generate_analyst_insights
from app.analyst.narrative import generate_narrative
from app.store.db import init_db


@pytest.fixture(autouse=True)
def test_db():
    settings = get_settings()
    original_path = settings.db_path
    temp_path = "./data/test_insights_llm_run.db"
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


def test_insights_polishing_and_caching():
    txns = [
        Transaction(
            date=date(2026, 6, 1),
            description_raw="UPI-Zomato",
            description_clean="ZOMATO",
            amount=450.0,
            direction="debit",
            category="Food",
        )
    ]
    metrics = Metrics(total_spend=450.0, top_categories=[("Food", 450.0)])
    summary_json = "{}"

    mock_provider = MagicMock()
    # Mock json response mapping to polished insights
    mock_provider.complete.return_value = '{"insights": ["Polished Food expense of 450"]}'

    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider):
        # First call: hits provider and caches
        insights = generate_analyst_insights("session-ins-123", txns, metrics, summary_json)
        assert insights == ["Polished Food expense of 450"]
        mock_provider.complete.assert_called_once()

    # Second call: hits cache, provider shouldn't be called
    mock_provider2 = MagicMock()
    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider2):
        insights2 = generate_analyst_insights("session-ins-123", txns, metrics, summary_json)
        assert insights2 == ["Polished Food expense of 450"]
        mock_provider2.complete.assert_not_called()


def test_narrative_generation_and_caching():
    summary_json = '{"totals": {"total_spend": 1000}}'
    mock_provider = MagicMock()
    mock_provider.complete.return_value = "This is a polished narrative briefing."

    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider):
        # First call: calls provider and caches
        narrative = generate_narrative("session-narr-123", summary_json)
        assert narrative == "This is a polished narrative briefing."
        mock_provider.complete.assert_called_once()

    # Second call: hits cache
    mock_provider2 = MagicMock()
    with patch("app.llm.factory.get_llm_provider", return_value=mock_provider2):
        narrative2 = generate_narrative("session-narr-123", summary_json)
        assert narrative2 == "This is a polished narrative briefing."
        mock_provider2.complete.assert_not_called()
