"""[1] Ingest & parse — load a bank-statement file into raw rows + a SchemaReport.

Supports CSV, Excel (XLSX), and PDF statements.
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


def ingest(content: bytes, filename: str) -> IngestResult:
    """Read a bank statement file and parse it into standard canonical row records.

    Dispatches to CSV, XLSX, or PDF parsers based on filename extension.
    """
    ext = filename.lower()
    if ext.endswith((".xlsx", ".xls")):
        return ingest_xlsx(content)
    if ext.endswith(".pdf"):
        return ingest_pdf(content)
    return ingest_csv(content)


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


def ingest_xlsx(content: bytes) -> IngestResult:
    """Read an Excel statement sheet into raw rows."""
    df = pd.read_excel(io.BytesIO(content), dtype=str, keep_default_na=False)
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


def ingest_pdf(content: bytes) -> IngestResult:
    """Scrape text from PDF and scan for transaction records.

    Uses a hybrid approach:
    1. Looks for structured PDF tables.
    2. Falls back to line-by-line regex scanning for dates and numeric amounts.
    """
    import pdfplumber

    rows: list[dict[str, str]] = []
    parsed_via_table = False

    # Regex patterns for date, description, and amounts mapping fallback
    date_pattern = re.compile(
        r"\b(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\b|\b(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})\b|\b(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{2,4})\b",
        re.IGNORECASE,
    )
    # Simple amount regex (requires decimal dot like .00 or .50)
    amount_pattern = re.compile(r"\b(\d{1,3}(?:,\d{3})*(?:\.\d{2}))\b")

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            # 1. Try Structured Tables first
            tables = page.extract_tables()
            for table in tables:
                if len(table) > 1:
                    headers = [str(cell or "").strip() for cell in table[0]]
                    mapping, warnings = detect_columns(headers)
                    if _confidence(mapping) >= 0.5:
                        for row_data in table[1:]:
                            row = {}
                            for canonical, col_name in mapping.items():
                                if col_name is not None:
                                    try:
                                        col_idx = headers.index(col_name)
                                        row[canonical] = str(row_data[col_idx] or "").strip()
                                    except (ValueError, IndexError):
                                        pass
                            if row:
                                rows.append(row)
                        parsed_via_table = True

            if parsed_via_table:
                continue

            # 2. Line-by-line Regex Scraper Fallback
            text = page.extract_text()
            if not text:
                continue

            for line in text.split("\n"):
                line = line.strip()
                date_match = date_pattern.search(line)
                if not date_match:
                    continue

                date_str = next(g for g in date_match.groups() if g is not None)
                remaining = line.replace(date_str, "", 1).strip()

                amounts = []
                for match in amount_pattern.finditer(remaining):
                    val_str = match.group(1)
                    val_clean = val_str.replace(",", "")
                    try:
                        val = float(val_clean)
                        if val > 0.0:
                            amounts.append((val_str, val))
                    except ValueError:
                        pass

                if not amounts:
                    continue

                # Clean description out by removing amounts
                desc = remaining
                for val_str, _ in amounts:
                    desc = desc.replace(val_str, "", 1)
                desc = re.sub(r"\s+", " ", desc).strip()

                # Map amounts: if >=2 amounts, assume second-to-last is txn amount, last is balance
                if len(amounts) >= 2:
                    tx_amount = amounts[-2][0]
                    balance = amounts[-1][0]
                else:
                    tx_amount = amounts[0][0]
                    balance = ""

                rows.append(
                    {
                        "date": date_str,
                        "description": desc or "UNKNOWN TRANSACTION",
                        "amount": tx_amount,
                        "balance": balance,
                    }
                )

    mapping = {"date": "date", "description": "description", "amount": "amount"}
    report = SchemaReport(
        detected_columns=mapping,
        total_rows=len(rows),
        confidence=1.0 if rows else 0.0,
        warnings=["Parsed unstructured PDF via regex scanning."] if not parsed_via_table else [],
    )

    return IngestResult(rows=rows, columns=mapping, report=report)
