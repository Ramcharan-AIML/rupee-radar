"""Manual pipeline tester: run a CSV bank statement through ingest → clean → categorize.

Usage (from the `backend/` directory, with the venv active):

    python scripts/test_pipeline.py
    python scripts/test_pipeline.py ../sample_data/rupeeradar_sample_statement.csv

It prints the detected column mapping, the SchemaReport (rows parsed/dropped), and the cleaned
+ categorized transactions — so you can eyeball that messy descriptions, dates, amounts,
direction, and categories were parsed correctly. (Metrics, recurring detection and the web UI
come in later phases.)
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

# Allow running as `python scripts/test_pipeline.py` from the backend/ dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.categorize import categorize_transactions  # noqa: E402
from app.pipeline.clean import ingest_and_clean  # noqa: E402

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "sample_data" / "rupeeradar_sample_statement.csv"


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    result = ingest_and_clean(path)
    categorize_transactions(result.transactions)
    report = result.report
    txns = result.transactions

    print(f"\nFile: {path}")
    print("=" * 92)
    print("DETECTED COLUMNS")
    for field_name, source in report.detected_columns.items():
        if source:
            print(f"  {field_name:<12} -> {source}")
    print(
        f"\nROWS: total={report.total_rows}  parsed={report.parsed_rows}  "
        f"dropped={report.dropped_rows}  detection_confidence={report.confidence}"
    )
    if report.warnings:
        print("WARNINGS:")
        for w in report.warnings:
            print(f"  - {w}")

    print("\n" + "=" * 100)
    print(f"{'DATE':<12}{'DIR':<8}{'AMOUNT':>12}  {'CATEGORY':<14}{'SRC':<9}{'MERCHANT (clean)':<26}")
    print("-" * 100)
    for t in txns:
        print(
            f"{t.date.isoformat():<12}{t.direction:<8}{t.amount:>12,.2f}  "
            f"{t.category:<14}{t.category_source:<9}{t.description_clean[:25]:<26}"
        )

    total_in = sum(t.amount for t in txns if t.direction == "credit")
    total_out = sum(t.amount for t in txns if t.direction == "debit")
    print("-" * 100)
    print(
        f"{'TOTALS':<12}{'':<8}{'':>12}  credits=Rs {total_in:,.2f}  debits=Rs {total_out:,.2f}"
    )

    # Category breakdown (debits only) — a preview of the Phase 4 metrics.
    spend_by_cat = Counter()
    for t in txns:
        if t.direction == "debit":
            spend_by_cat[t.category] += t.amount
    print("\nSPEND BY CATEGORY (debits):")
    for cat, amt in spend_by_cat.most_common():
        print(f"  {cat:<14} Rs {amt:>12,.2f}")
    print("\n(note: full metrics/recurring/insights arrive in Phase 4-6)")
    print()


if __name__ == "__main__":
    main()
