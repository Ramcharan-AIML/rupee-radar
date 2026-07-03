"""Core domain schemas (architecture §3.2).

These typed contracts are what the pipeline fills and the API returns. They are intentionally
strict about the things that matter (canonical categories, non-negative amounts) and lenient
about ordering so they round-trip cleanly through JSON.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.constants import CANONICAL_CATEGORY_SET, DEFAULT_CATEGORY

Direction = Literal["debit", "credit"]
CategorySource = Literal["rule", "llm", "default"]
Cadence = Literal["weekly", "monthly", "quarterly", "yearly", "irregular"]


def new_id() -> str:
    """Generate a short unique identifier."""
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Transaction(BaseModel):
    """A single cleaned, categorized transaction."""

    id: str = Field(default_factory=new_id)
    date: date
    description_raw: str
    description_clean: str = ""
    amount: float  # absolute value; direction carries the sign
    direction: Direction
    category: str = DEFAULT_CATEGORY
    category_source: CategorySource = "default"
    confidence: float = 0.0
    is_recurring: bool = False
    recurring_group_id: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def _amount_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount must be non-negative (sign is encoded in `direction`)")
        return v

    @field_validator("category")
    @classmethod
    def _category_canonical(cls, v: str) -> str:
        if v not in CANONICAL_CATEGORY_SET:
            raise ValueError(f"category {v!r} is not a canonical category")
        return v


class RecurringGroup(BaseModel):
    """A detected recurring payment (subscription, EMI, rent, SIP, insurance…)."""

    id: str = Field(default_factory=new_id)
    merchant: str
    cadence: Cadence
    typical_amount: float
    occurrences: int
    category: str

    @field_validator("category")
    @classmethod
    def _category_canonical(cls, v: str) -> str:
        if v not in CANONICAL_CATEGORY_SET:
            raise ValueError(f"category {v!r} is not a canonical category")
        return v


class Metrics(BaseModel):
    """Computed financial metrics. All numbers are produced deterministically in code."""

    total_income: float = 0.0
    total_spend: float = 0.0
    net_savings: float = 0.0
    savings_rate: float = 0.0  # net_savings / total_income; 0.0 when income is 0
    top_categories: list[tuple[str, float]] = Field(default_factory=list)
    biggest_transaction: Optional[Transaction] = None  # None for an empty analysis
    by_month: dict[str, float] = Field(default_factory=dict)  # "YYYY-MM" -> spend


class SchemaReport(BaseModel):
    """What the ingest step detected — surfaced to the UI so parsing is transparent."""

    detected_columns: dict[str, Optional[str]] = Field(default_factory=dict)
    total_rows: int = 0
    parsed_rows: int = 0
    dropped_rows: int = 0
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class Analysis(BaseModel):
    """The full result of analyzing one statement — the API's primary payload."""

    session_id: str = Field(default_factory=new_id)
    created_at: datetime = Field(default_factory=_utcnow)
    transactions: list[Transaction] = Field(default_factory=list)
    recurring: list[RecurringGroup] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    insights: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """Response for `POST /api/upload` — the analysis plus how the file was parsed."""

    session_id: str
    analysis: Analysis
    schema_report: SchemaReport
