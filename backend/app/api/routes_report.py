"""`GET /api/report/{session_id}` — statement report exporter routes.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from app.report.generator import export_csv, export_html, export_pdf
from app.store.repository import get_analysis

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report/{session_id}")
def download_report(
    session_id: str,
    format: str = Query("html", regex="^(html|csv|pdf)$"),
) -> Response:
    """Download statement analysis report in HTML, CSV, or PDF format."""
    analysis = get_analysis(session_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis record not found. Please upload the statement again.",
        )

    filename = f"rupeeradar_report_{session_id[:8]}"

    if format == "csv":
        csv_data = export_csv(analysis)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )

    if format == "html":
        html_data = export_html(analysis)
        return HTMLResponse(content=html_data)

    if format == "pdf":
        try:
            pdf_data = export_pdf(analysis)
            return Response(
                content=pdf_data,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
            )
        except OSError as err:
            # Cairo/GTK+ libraries missing on Windows host
            raise HTTPException(
                status_code=422,
                detail=str(err),
            ) from err

    raise HTTPException(status_code=400, detail="Invalid format parameter.")
