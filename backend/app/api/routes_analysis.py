"""`GET /api/analysis/{session_id}` — re-fetch a stored analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import Analysis
from app.store.session_store import get_session_store

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/analysis/{session_id}", response_model=Analysis)
def get_analysis(session_id: str) -> Analysis:
    analysis = get_session_store().get(session_id)
    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found or expired. Please upload the statement again.",
        )
    return analysis
