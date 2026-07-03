"""SQLite implementation of data access repository.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING

from app.models.schemas import Analysis, AnalysisHistoryItem, Metrics, RecurringGroup, Transaction
from app.store.db import get_db_conn

if TYPE_CHECKING:
    pass


def save_analysis(analysis: Analysis) -> None:
    """Persist an analysis object recursively into the SQLite database."""
    with get_db_conn() as conn:
        # 1. Insert or replace analysis header
        conn.execute(
            """
            INSERT OR REPLACE INTO analyses (session_id, created_at, metrics, insights)
            VALUES (?, ?, ?, ?)
            """,
            (
                analysis.session_id,
                analysis.created_at.isoformat(),
                analysis.metrics.model_dump_json(),
                json.dumps(analysis.insights),
            ),
        )

        # 2. Clear old transactions and insert current ones
        conn.execute("DELETE FROM transactions WHERE session_id = ?", (analysis.session_id,))
        for t in analysis.transactions:
            conn.execute(
                """
                INSERT INTO transactions (
                    id, session_id, date, description_raw, description_clean, amount,
                    direction, category, category_source, confidence, is_recurring, recurring_group_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t.id,
                    analysis.session_id,
                    t.date.isoformat(),
                    t.description_raw,
                    t.description_clean,
                    t.amount,
                    t.direction,
                    t.category,
                    t.category_source,
                    t.confidence,
                    1 if t.is_recurring else 0,
                    t.recurring_group_id,
                ),
            )

        # 3. Clear old recurring groups and insert current ones
        conn.execute("DELETE FROM recurring_groups WHERE session_id = ?", (analysis.session_id,))
        for r in analysis.recurring:
            conn.execute(
                """
                INSERT INTO recurring_groups (
                    id, session_id, merchant, cadence, typical_amount, occurrences, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r.id,
                    analysis.session_id,
                    r.merchant,
                    r.cadence,
                    r.typical_amount,
                    r.occurrences,
                    r.category,
                ),
            )


def get_analysis(session_id: str) -> Analysis | None:
    """Retrieve and assemble a complete Analysis object by its session ID."""
    with get_db_conn() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            return None

        # Assemble transactions
        tx_rows = conn.execute(
            "SELECT * FROM transactions WHERE session_id = ? ORDER BY date DESC", (session_id,)
        ).fetchall()
        transactions = []
        for r in tx_rows:
            transactions.append(
                Transaction(
                    id=r["id"],
                    date=date.fromisoformat(r["date"]),
                    description_raw=r["description_raw"],
                    description_clean=r["description_clean"],
                    amount=r["amount"],
                    direction=r["direction"],
                    category=r["category"],
                    category_source=r["category_source"],
                    confidence=r["confidence"],
                    is_recurring=bool(r["is_recurring"]),
                    recurring_group_id=r["recurring_group_id"],
                )
            )

        # Assemble recurring groups
        rec_rows = conn.execute(
            "SELECT * FROM recurring_groups WHERE session_id = ?", (session_id,)
        ).fetchall()
        recurring = []
        for r in rec_rows:
            recurring.append(
                RecurringGroup(
                    id=r["id"],
                    merchant=r["merchant"],
                    cadence=r["cadence"],
                    typical_amount=r["typical_amount"],
                    occurrences=r["occurrences"],
                    category=r["category"],
                )
            )

        # Unpack metrics and insights
        metrics_dict = json.loads(row["metrics"])
        metrics = Metrics(**metrics_dict)
        insights = json.loads(row["insights"])

        created_at_str = row["created_at"]
        if created_at_str.endswith("Z"):
            created_at_str = created_at_str[:-1] + "+00:00"
        created_at = datetime.fromisoformat(created_at_str)

        return Analysis(
            session_id=row["session_id"],
            created_at=created_at,
            transactions=transactions,
            recurring=recurring,
            metrics=metrics,
            insights=insights,
        )


def list_analyses() -> list[AnalysisHistoryItem]:
    """Retrieve summaries of all analyses stored in database, ordered by creation date desc."""
    with get_db_conn() as conn:
        rows = conn.execute(
            "SELECT session_id, created_at, metrics, insights FROM analyses ORDER BY created_at DESC"
        ).fetchall()

        history = []
        for r in rows:
            metrics_dict = json.loads(r["metrics"])
            created_at_str = r["created_at"]
            if created_at_str.endswith("Z"):
                created_at_str = created_at_str[:-1] + "+00:00"
            created_at = datetime.fromisoformat(created_at_str)

            history.append(
                AnalysisHistoryItem(
                    session_id=r["session_id"],
                    created_at=created_at,
                    metrics=Metrics(**metrics_dict),
                    insights=json.loads(r["insights"]),
                )
            )
        return history
