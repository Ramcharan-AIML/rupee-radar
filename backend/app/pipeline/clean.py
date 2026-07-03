"""[2] Clean & normalize — turn raw ingested rows into structured `Transaction`s.

Responsibilities:
- Parse messy dates (mixed formats, Indian DD/MM default) into ISO `date`.
- Normalize amounts (strip ₹/commas/`Cr`/`Dr`/parentheses) and resolve `direction`,
  reconciling separate debit/credit columns or a single signed amount column.
- Clean descriptions: strip payment-rail prefixes, reference numbers, VPAs, and noise to a
  usable merchant token (the only text later sent to the LLM).
- Drop non-transaction rows (headers, opening/closing balance, totals, unparseable dates).

Categories are left at the default here; Phase 3 assigns them.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd

from app.models.schemas import Direction, SchemaReport, Transaction
from app.pipeline.ingest import IngestResult

# --- Description cleaning vocab -------------------------------------------------------------

# Payment-rail / channel prefixes and structural noise tokens to discard.
_NOISE_TOKENS = {
    # rails / channels
    "UPI", "IMPS", "NEFT", "RTGS", "POS", "ACH", "ATM", "ECS", "MMT", "IB", "NWD", "VPS",
    "CHQ", "EMI",
    # structural noise
    "REF", "REFNO", "PAYMENT", "PMT", "FROM", "TO", "TXN", "TRANSACTION", "ID", "NO", "NA",
    "P2A", "P2M", "BIL", "BILLPAY", "AUTOPAY", "TRANSFER", "TRF", "VIA",
    "CR", "DR", "D", "C",
}

# Rows whose description marks them as non-transactions (belt-and-suspenders alongside the
# "no amount" check).
_NON_TXN_MARKERS = (
    "OPENING BALANCE", "CLOSING BALANCE", "BALANCE B/F", "BALANCE C/F", "B/F", "C/F",
    "OPENING BAL", "CLOSING BAL", "TOTAL", "GRAND TOTAL", "STATEMENT SUMMARY",
)


def parse_date(value: object) -> Optional[date]:
    """Parse a messy date string into a `date`, or None if unparseable.

    Uses day-first interpretation (Indian statements). Returns None for headers / blanks.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        if re.match(r"^\d{4}-\d{1,2}-\d{1,2}", s):
            # ISO (YYYY-MM-DD) is unambiguous and month-first — don't apply day-first.
            ts = pd.to_datetime(s, errors="raise")
        else:
            # format="mixed" infers each value independently (handles mixed formats in one
            # file) and avoids the day-first warning.
            ts = pd.to_datetime(s, dayfirst=True, format="mixed", errors="raise")
    except (ValueError, TypeError, OverflowError):
        return None
    if pd.isna(ts):
        return None
    return ts.date()


def parse_amount_cell(value: object) -> Optional[float]:
    """Parse a single amount cell to a non-negative magnitude, or None if blank/non-numeric.

    Handles ₹/Rs/INR symbols, Indian comma grouping, `Cr`/`Dr` suffixes, and parentheses.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    s = re.sub(r"(?i)(₹|rs\.?|inr)", "", s)
    s = re.sub(r"(?i)\b(cr|dr)\b", "", s)
    s = s.replace(",", "").replace(" ", "").lstrip("+-")
    if not s or s == ".":
        return None
    try:
        return abs(float(s))
    except ValueError:
        return None


def parse_signed_amount(
    value: object, type_hint: Optional[str] = None
) -> Optional[tuple[float, Direction]]:
    """Parse a single signed amount column into (magnitude, direction).

    Direction precedence: explicit `Cr`/`Dr` (in value or type column) > sign/parentheses >
    default to debit.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None

    direction: Optional[Direction] = None
    hint = f"{raw} {type_hint or ''}".lower()
    if re.search(r"\bcr\b", hint):
        direction = "credit"
    elif re.search(r"\bdr\b", hint):
        direction = "debit"

    is_negative = raw.startswith("-") or (raw.startswith("(") and raw.endswith(")"))
    magnitude = parse_amount_cell(raw)
    if magnitude is None:
        return None

    if direction is None:
        # No explicit Cr/Dr hint: negative/parenthesized → debit; otherwise default to debit
        # (a single unsigned amount column is overwhelmingly spend). A `type` column or
        # debit/credit columns resolve this precisely when present.
        direction = "debit"
    elif is_negative and direction == "credit":
        direction = "debit"  # sign overrides a stray "cr" token when they conflict
    return magnitude, direction


def clean_description(raw: str) -> str:
    """Reduce a messy narration to a usable merchant token (uppercased).

    Falls back to a best-effort value rather than returning empty (edge case C4).
    """
    if not raw:
        return "UNKNOWN"
    text = raw.upper()
    # Drop UPI/VPA handles entirely (e.g. "427183920@OKHDFCBANK") before tokenizing, so the
    # bank-handle suffix doesn't survive as a fake merchant token.
    text = re.sub(r"[\w.\-]+@[\w.\-]+", " ", text)
    # split on anything that isn't a letter or digit
    tokens = re.split(r"[^A-Z0-9]+", text)
    kept: list[str] = []
    for tok in tokens:
        if not tok:
            continue
        if tok in _NOISE_TOKENS:
            continue
        if len(tok) == 1:
            continue
        if tok.isdigit():  # pure reference numbers
            continue
        if tok.startswith("REF") and tok[3:].isdigit():
            continue
        if any(ch.isdigit() for ch in tok) and any(ch.isalpha() for ch in tok):
            # mixed alnum tokens are usually reference ids (e.g. N99281, Z551)
            continue
        kept.append(tok)

    cleaned = " ".join(kept).strip()
    if cleaned:
        return cleaned
    # fallback: first alphabetic token from the raw text, else UNKNOWN
    for tok in tokens:
        if tok and any(ch.isalpha() for ch in tok):
            return tok
    return "UNKNOWN"


def _is_non_txn_marker(description_raw: str) -> bool:
    upper = description_raw.upper()
    return any(marker in upper for marker in _NON_TXN_MARKERS)


@dataclass
class CleanResult:
    transactions: list[Transaction]
    report: SchemaReport


def clean(ingested: IngestResult) -> CleanResult:
    """Convert ingested raw rows into cleaned `Transaction`s + an updated SchemaReport."""
    columns = ingested.columns
    has_debit_credit = columns.get("debit") is not None or columns.get("credit") is not None

    transactions: list[Transaction] = []
    warnings: list[str] = list(ingested.report.warnings)
    dropped = 0

    for row in ingested.rows:
        txn_date = parse_date(row.get("date"))
        if txn_date is None:
            dropped += 1  # header repeat / total row / blank or unparseable date
            continue

        description_raw = (row.get("description") or "").strip()

        if has_debit_credit:
            debit_val = parse_amount_cell(row.get("debit"))
            credit_val = parse_amount_cell(row.get("credit"))
            debit_val = debit_val if (debit_val and debit_val > 0) else None
            credit_val = credit_val if (credit_val and credit_val > 0) else None

            if debit_val and credit_val:
                warnings.append(
                    f"Row has both debit and credit values ({description_raw[:40]}); skipped."
                )
                dropped += 1
                continue
            if debit_val:
                amount, direction = debit_val, "debit"
            elif credit_val:
                amount, direction = credit_val, "credit"
            else:
                dropped += 1  # no amount → balance / opening / closing row
                continue
        else:
            signed = parse_signed_amount(row.get("amount"), row.get("type"))
            if signed is None or signed[0] <= 0:
                dropped += 1
                continue
            amount, direction = signed

        if _is_non_txn_marker(description_raw):
            dropped += 1
            continue

        transactions.append(
            Transaction(
                date=txn_date,
                description_raw=description_raw,
                description_clean=clean_description(description_raw),
                amount=amount,
                direction=direction,
            )
        )

    report = ingested.report.model_copy(
        update={
            "parsed_rows": len(transactions),
            "dropped_rows": dropped,
            "warnings": warnings,
        }
    )
    return CleanResult(transactions=transactions, report=report)


def ingest_and_clean(source) -> CleanResult:
    """Convenience: ingest a CSV then clean it (used from Phase 4's upload route)."""
    from app.pipeline.ingest import ingest_csv

    return clean(ingest_csv(source))
