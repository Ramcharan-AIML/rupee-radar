"""[1] Ingest & parse — load a bank-statement file into raw rows + a SchemaReport.

Phase 2 supports CSV (the primary format). The hard part is that every bank lays out its
statement differently, so we **auto-detect** which columns hold the date, description, and
amount(s) by fuzzy-matching the headers against known synonyms. XLSX/PDF arrive in Phase 13.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from app.models.schemas import SchemaReport

# Canonical field -> header synonyms (normalized, lowercase, alnum-only when compared).
_SYNONYMS: dict[str, list[str]] = {
    "date": ["date", "txndate", "transactiondate", "valuedate", "postingdate", "trandate"],
    "description": [
        "description", "narration", "particulars", "details", "remarks", "remark",
        "transactiondetails", "naration",
    ],
    "debit": [
        "debit", "withdrawal", "withdrawalamt", "withdrawaldr", "debitamount", "paidout",
        "dr", "withdrawals",
    ],
    "credit": [
        "credit", "deposit", "depositamt", "depositcr", "creditamount", "paidin", "cr",
        "deposits",
    ],
    "balance": ["balance", "closingbalance", "runningbalance", "availablebalance", "bal"],
    "amount": ["amount", "amt", "transactionamount", "txnamount"],
    "type": ["type", "drcr", "transactiontype", "crdr"],
}

# Order matters: claim the more specific columns (debit/credit/balance) before "amount".
_FIELD_PRIORITY = ["date", "description", "debit", "credit", "balance", "amount", "type"]


def _norm(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(header).lower())


def _score(header_norm: str, synonyms: list[str]) -> int:
    """3 = exact, 2 = substring either way, 0 = no match."""
    best = 0
    for syn in synonyms:
        if header_norm == syn:
            return 3
        if syn and (syn in header_norm or header_norm in syn):
            best = max(best, 2)
    return best


def detect_columns(headers: list[str]) -> tuple[dict[str, Optional[str]], list[str]]:
    """Map canonical fields to source headers. Returns (mapping, warnings)."""
    norm_map = {h: _norm(h) for h in headers}
    mapping: dict[str, Optional[str]] = {f: None for f in _SYNONYMS}
    taken: set[str] = set()

    for field_name in _FIELD_PRIORITY:
        synonyms = _SYNONYMS[field_name]
        best_header, best_score = None, 0
        for header in headers:
            if header in taken:
                continue
            s = _score(norm_map[header], synonyms)
            if s > best_score:
                best_header, best_score = header, s
        if best_header is not None and best_score > 0:
            mapping[field_name] = best_header
            taken.add(best_header)

    warnings: list[str] = []
    if mapping["date"] is None:
        warnings.append("Could not detect a date column.")
    if mapping["description"] is None:
        warnings.append("Could not detect a description/narration column.")
    if mapping["amount"] is None and mapping["debit"] is None and mapping["credit"] is None:
        warnings.append("Could not detect an amount (or debit/credit) column.")
    return mapping, warnings


def _confidence(mapping: dict[str, Optional[str]]) -> float:
    has_date = mapping["date"] is not None
    has_desc = mapping["description"] is not None
    has_amount = any(mapping[f] is not None for f in ("amount", "debit", "credit"))
    return round(sum([has_date, has_desc, has_amount]) / 3, 2)


@dataclass
class IngestResult:
    rows: list[dict[str, str]]            # raw values keyed by canonical field
    columns: dict[str, Optional[str]]      # canonical field -> source header
    report: SchemaReport = field(default_factory=SchemaReport)


def ingest_csv(source: Union[str, Path, bytes]) -> IngestResult:
    """Read a CSV into raw rows keyed by detected canonical fields."""
    if isinstance(source, bytes):
        buffer: Union[io.BytesIO, str, Path] = io.BytesIO(source)
    else:
        buffer = source

    # Keep everything as raw strings; let the clean step interpret values.
    df = pd.read_csv(
        buffer,
        dtype=str,
        keep_default_na=False,
        skipinitialspace=True,
        encoding="utf-8",
    )
    df.columns = [str(c).strip() for c in df.columns]

    mapping, warnings = detect_columns(list(df.columns))

    rows: list[dict[str, str]] = []
    for _, raw in df.iterrows():
        row = {
            canonical: str(raw[source_col]).strip()
            for canonical, source_col in mapping.items()
            if source_col is not None and source_col in df.columns
        }
        rows.append(row)

    report = SchemaReport(
        detected_columns=mapping,
        total_rows=len(rows),
        confidence=_confidence(mapping),
        warnings=warnings,
    )
    return IngestResult(rows=rows, columns=mapping, report=report)
