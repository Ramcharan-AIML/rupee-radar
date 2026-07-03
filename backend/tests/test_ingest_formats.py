import io
from datetime import date
from unittest.mock import MagicMock, patch
import pandas as pd
from app.pipeline.ingest import ingest_xlsx, ingest_pdf


def test_ingest_xlsx_parsing():
    # 1. Create a simple pandas excel spreadsheet in memory
    df = pd.DataFrame(
        [
            {
                "Transaction Date": "2026-06-01",
                "Narration Description": "UPI-ZOMATO-PAY",
                "Withdrawal Amount": "450.00",
                "Deposit Amount": "0.00",
                "Balance": "1000.00",
            }
        ]
    )

    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    xlsx_bytes = out.getvalue()

    # 2. Parse using ingest_xlsx
    res = ingest_xlsx(xlsx_bytes)
    assert res.report.total_rows == 1
    assert res.rows[0]["date"] == "2026-06-01"
    assert res.rows[0]["description"] == "UPI-ZOMATO-PAY"
    assert res.rows[0]["debit"] == "450.00"
    assert res.rows[0]["balance"] == "1000.00"


def test_ingest_pdf_line_regex_fallback():
    # Mock pdfplumber open structure
    mock_page = MagicMock()
    # No tables detected
    mock_page.extract_tables.return_value = []
    # Raw statement text
    mock_page.extract_text.return_value = (
        "Statement Period: Jun 2026\n"
        "01-06-2026 UPI-ZOMATO-PAY 450.00 1,000.00\n"
        "02-06-2026 INTEREST CREDIT 50.00 1,050.00\n"
    )

    mock_pdf = MagicMock()
    mock_pdf.__enter__.return_value = mock_pdf
    mock_pdf.pages = [mock_page]

    with patch("pdfplumber.open", return_value=mock_pdf):
        res = ingest_pdf(b"dummy pdf bytes")

    assert res.report.total_rows == 2
    # Row 1
    assert res.rows[0]["date"] == "01-06-2026"
    assert "UPI-ZOMATO-PAY" in res.rows[0]["description"]
    assert res.rows[0]["amount"] == "450.00"
    assert res.rows[0]["balance"] == "1,000.00"

    # Row 2
    assert res.rows[1]["date"] == "02-06-2026"
    assert "INTEREST CREDIT" in res.rows[1]["description"]
    assert res.rows[1]["amount"] == "50.00"
    assert res.rows[1]["balance"] == "1,050.00"
