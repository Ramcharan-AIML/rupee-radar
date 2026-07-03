"""`POST /api/upload` — the end-to-end pipeline over HTTP.

ingest → clean → categorize → metrics → insights → build `Analysis`, store it, return it.
Raw file bytes are read, parsed, and discarded (only the structured `Analysis` is kept).
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.models.schemas import Analysis, UploadResponse
from app.pipeline.categorize import categorize_transactions
from app.pipeline.clean import ingest_and_clean
from app.pipeline.insights import generate_insights
from app.pipeline.metrics import compute_metrics
from app.store.session_store import get_session_store

router = APIRouter(prefix="/api", tags=["upload"])

_ALLOWED_SUFFIXES = (".csv", ".txt")


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(file: UploadFile = File(...)) -> UploadResponse:
    settings = get_settings()

    filename = file.filename or "upload"
    if not filename.lower().endswith(_ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a CSV statement "
            "(XLSX/PDF support is coming later).",
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
        cleaned = ingest_and_clean(content)
    except Exception as exc:  # noqa: BLE001 — surface a friendly parse error, never a 500
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse the file as a bank-statement CSV: {exc}",
        ) from exc

    categorize_transactions(cleaned.transactions)
    metrics = compute_metrics(cleaned.transactions)
    insights = generate_insights(cleaned.transactions, metrics)

    analysis = Analysis(
        transactions=cleaned.transactions,
        recurring=[],  # populated in Phase 6
        metrics=metrics,
        insights=insights,
    )
    get_session_store().put(analysis)

    return UploadResponse(
        session_id=analysis.session_id,
        analysis=analysis,
        schema_report=cleaned.report,
    )
