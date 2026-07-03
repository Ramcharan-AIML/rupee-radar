import json
from datetime import date
from app.models.schemas import Analysis, Metrics, Transaction
from app.report.generator import export_csv, export_html


def test_export_csv_and_html():
    txn = Transaction(
        date=date(2026, 6, 1),
        description_raw="UPI-Netflix-Payment",
        description_clean="NETFLIX",
        amount=199.0,
        direction="debit",
        category="Subscriptions",
    )
    analysis = Analysis(
        session_id="session-rep-1",
        transactions=[txn],
        metrics=Metrics(total_spend=199.0, top_categories=[("Subscriptions", 199.0)]),
        insights=["You spent on Netflix"],
        narrative="A short narrative description",
    )

    # 1. Test CSV
    csv_str = export_csv(analysis)
    assert "NETFLIX" in csv_str
    assert "199.0" in csv_str
    assert "Subscriptions" in csv_str

    # 2. Test HTML
    html_str = export_html(analysis)
    assert "RupeeRadar" in html_str
    assert "A short narrative description" in html_str
    assert "199.00" in html_str
    assert "session-rep-1"[:12] in html_str
