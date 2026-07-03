"""[12] Report Generator.

Compiles statement analyses into downloadable formats: HTML, CSV, and PDF.
WeasyPrint import is safely wrapped in try-catch blocks to prevent Windows Cairo loading crashes.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from jinja2 import Template

from app.models.schemas import Analysis

logger = logging.getLogger(__name__)

# Safely check for WeasyPrint and cairo DLL graphics dependencies
WEASYPRINT_AVAILABLE = False
try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError) as err:
    logger.warning(
        "WeasyPrint is not fully functional (likely missing Cairo/GTK+ libraries on Windows). "
        "PDF downloads will fallback gracefully. Details: %s",
        err,
    )


def export_csv(analysis: Analysis) -> str:
    """Export transaction records to a standard CSV string."""
    import pandas as pd

    rows = []
    for t in analysis.transactions:
        rows.append(
            {
                "Date": t.date.isoformat(),
                "Description (Raw)": t.description_raw,
                "Description (Clean)": t.description_clean,
                "Amount": t.amount,
                "Direction": t.direction,
                "Category": t.category,
                "Source": t.category_source,
                "Is Recurring": "Yes" if t.is_recurring else "No",
            }
        )

    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def export_html(analysis: Analysis) -> str:
    """Compile statement metrics into a formatted print-friendly HTML report."""
    template_path = os.path.join(os.path.dirname(__file__), "report_template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template_text = f.read()

    template = Template(template_text)
    generated_at = datetime.now().strftime("%d %b %Y, %I:%M %p")

    return template.render(
        session_id=analysis.session_id,
        generated_at=generated_at,
        metrics=analysis.metrics,
        insights=analysis.insights,
        narrative=analysis.narrative,
        recurring=analysis.recurring,
    )


def export_pdf(analysis: Analysis) -> bytes:
    """Convert HTML report into standard PDF bytes.

    Raises OSError if WeasyPrint / Cairo binaries are missing on Windows.
    """
    if not WEASYPRINT_AVAILABLE:
        raise OSError(
            "PDF generation requires GTK+/Cairo dependencies to be installed on Windows. "
            "Please use the print-friendly HTML layout option and print to PDF using your browser."
        )

    html_content = export_html(analysis)
    return weasyprint.HTML(string=html_content).write_pdf()
