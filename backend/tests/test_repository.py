import os
from datetime import date, datetime, timezone
import pytest

from app.config import get_settings
from app.models.schemas import Analysis, Metrics, RecurringGroup, Transaction
from app.store.db import init_db
from app.store.repository import get_analysis, list_analyses, save_analysis


@pytest.fixture(autouse=True)
def test_db():
    """Setup a temporary database and tear it down after test completion."""
    settings = get_settings()
    original_path = settings.db_path
    temp_path = "./data/test_repository_run.db"
    settings.db_path = temp_path

    init_db()

    yield

    settings.db_path = original_path
    # Clean up files
    for path in (temp_path, temp_path + "-wal", temp_path + "-shm"):
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def test_save_and_retrieve_analysis():
    # Construct complete analysis
    txn = Transaction(
        date=date(2026, 6, 1),
        description_raw="UPI-RentPay",
        description_clean="RENTPAY",
        amount=12000.0,
        direction="debit",
        category="Rent",
        is_recurring=True,
        recurring_group_id="rec_rent_1",
    )
    rec = RecurringGroup(
        id="rec_rent_1",
        merchant="RENTPAY",
        cadence="monthly",
        typical_amount=12000.0,
        occurrences=1,
        category="Rent",
    )
    metrics = Metrics(
        total_income=0.0,
        total_spend=12000.0,
        net_savings=-12000.0,
        savings_rate=0.0,
        top_categories=[("Rent", 12000.0)],
        biggest_transaction=txn,
        by_month={"2026-06": 12000.0},
    )
    analysis = Analysis(
        session_id="test-session-123",
        created_at=datetime(2026, 7, 3, 10, 0, 0, tzinfo=timezone.utc),
        transactions=[txn],
        recurring=[rec],
        metrics=metrics,
        insights=["Rent is high."],
    )

    save_analysis(analysis)

    retrieved = get_analysis("test-session-123")
    assert retrieved is not None
    assert retrieved.session_id == "test-session-123"
    assert retrieved.created_at == analysis.created_at
    assert len(retrieved.transactions) == 1
    assert retrieved.transactions[0].id == txn.id
    assert retrieved.transactions[0].date == date(2026, 6, 1)
    assert retrieved.transactions[0].is_recurring is True
    assert retrieved.transactions[0].recurring_group_id == "rec_rent_1"

    assert len(retrieved.recurring) == 1
    assert retrieved.recurring[0].merchant == "RENTPAY"
    assert retrieved.recurring[0].cadence == "monthly"

    assert retrieved.metrics.total_spend == 12000.0
    assert retrieved.metrics.top_categories == [("Rent", 12000.0)]
    assert retrieved.insights == ["Rent is high."]


def test_list_analyses():
    metrics = Metrics(total_spend=100.0)
    analysis1 = Analysis(
        session_id="session-1",
        created_at=datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc),
        metrics=metrics,
        insights=["Insight 1"],
    )
    analysis2 = Analysis(
        session_id="session-2",
        created_at=datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc),
        metrics=metrics,
        insights=["Insight 2"],
    )

    save_analysis(analysis1)
    save_analysis(analysis2)

    history = list_analyses()
    assert len(history) == 2
    # Ordered by created_at DESC
    assert history[0].session_id == "session-2"
    assert history[1].session_id == "session-1"
    assert history[0].metrics.total_spend == 100.0
    assert history[0].insights == ["Insight 2"]
