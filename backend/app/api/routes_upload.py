"""`POST /api/upload` — the end-to-end pipeline over HTTP.

ingest → clean → categorize → metrics → insights → build `Analysis`, store it, return it.
Raw file bytes are read, parsed, and discarded (only the structured `Analysis` is kept).
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import Analysis, UploadResponse, new_id
from app.pipeline.categorize import categorize_transactions
from app.pipeline.clean import ingest_and_clean
from app.pipeline.metrics import compute_metrics
from app.pipeline.recurring import detect_recurring_payments
from app.pipeline.summary import build_compact_summary
from app.analyst.insights import generate_analyst_insights
from app.analyst.narrative import generate_narrative
from app.store.repository import save_analysis

router = APIRouter(prefix="/api", tags=["upload"])

_ALLOWED_SUFFIXES = ("..csv", ".csv", ".txt", ".xlsx", ".xls", ".pdf")  # Support loose matches


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(file: UploadFile = File(...)) -> UploadResponse:
    settings = get_settings()

    filename = file.filename or "upload"
    if not filename.lower().endswith(_ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a CSV, Excel (XLSX), or PDF statement.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.max_upload_mb} MB.",
        )

    try:
        cleaned = ingest_and_clean(content, filename)
    except Exception as exc:  # noqa: BLE001 — surface a friendly parse error, never a 500
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse the bank-statement file: {exc}",
        ) from exc

    categorize_transactions(cleaned.transactions)
    recurring_groups = detect_recurring_payments(cleaned.transactions)
    metrics = compute_metrics(cleaned.transactions)

    session_id = new_id()
    summary_json = build_compact_summary(cleaned.transactions, metrics, recurring_groups)
    insights = generate_analyst_insights(session_id, cleaned.transactions, metrics, summary_json)
    narrative = generate_narrative(session_id, summary_json)

    analysis = Analysis(
        session_id=session_id,
        transactions=cleaned.transactions,
        recurring=recurring_groups,
        metrics=metrics,
        insights=insights,
        narrative=narrative,
    )
    save_analysis(analysis)

    return UploadResponse(
        session_id=analysis.session_id,
        analysis=analysis,
        schema_report=cleaned.report,
    )
