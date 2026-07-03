"""Phase 4 acceptance: the full /api/upload + /api/analysis flow over HTTP."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

SAMPLE = Path(__file__).parent / "sample_statements" / "messy_sample.csv"
client = TestClient(app)


def _upload():
    with open(SAMPLE, "rb") as fh:
        return client.post(
            "/api/upload",
            files={"file": ("messy_sample.csv", fh, "text/csv")},
        )


def test_upload_returns_valid_analysis():
    resp = _upload()
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert "session_id" in body
    analysis = body["analysis"]
    assert len(analysis["transactions"]) == 9
    assert len(analysis["insights"]) >= 3

    m = analysis["metrics"]
    assert m["total_income"] - m["total_spend"] == m["net_savings"]
    assert m["total_income"] == 85000.0

    report = body["schema_report"]
    assert report["parsed_rows"] == 9
    assert report["detected_columns"]["date"] == "Txn Date"


def test_get_analysis_roundtrip():
    session_id = _upload().json()["session_id"]
    resp = client.get(f"/api/analysis/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == session_id


def test_get_unknown_analysis_returns_404():
    resp = client.get("/api/analysis/does-not-exist")
    assert resp.status_code == 404


def test_empty_file_returns_400():
    resp = client.post("/api/upload", files={"file": ("empty.csv", b"", "text/csv")})
    assert resp.status_code == 400


def test_unsupported_file_type_returns_415():
    resp = client.post("/api/upload", files={"file": ("statement.pdf", b"%PDF-1.4", "application/pdf")})
    assert resp.status_code == 415


def test_categories_are_canonical_in_response():
    from app.constants import CANONICAL_CATEGORY_SET

    analysis = _upload().json()["analysis"]
    for txn in analysis["transactions"]:
        assert txn["category"] in CANONICAL_CATEGORY_SET
