"""`GET /api/analysis/{session_id}` and `GET /api/history` — retrieve analysis details and history.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import Analysis, AnalysisHistoryItem
from app.store.repository import get_analysis as db_get_analysis
from app.store.repository import list_analyses as db_list_analyses

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/history", response_model=list[AnalysisHistoryItem])
def list_history() -> list[AnalysisHistoryItem]:
    """Retrieve history of all uploaded financial statements."""
    return db_list_analyses()


@router.get("/analysis/{session_id}", response_model=Analysis)
def get_analysis(session_id: str) -> Analysis:
    """Fetch a completed analysis by its session ID."""
    analysis = db_get_analysis(session_id)
    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found in local database. Please upload the statement again.",
        )
    return analysis

