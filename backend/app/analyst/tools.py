"""[11] SQLite Query Tools for Chat.

Code-level functions that query structured statement data from SQLite
to ground the chat bot in facts.
"""

from __future__ import annotations

import json
from app.store.db import get_db_conn


def get_metrics(session_id: str) -> str:
    """Return base metrics (totals, savings rate) for the session."""
    with get_db_conn() as conn:
        row = conn.execute(
            "SELECT metrics FROM analyses WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not row:
            return "Session not found."

        data = json.loads(row["metrics"])
        return (
            f"Totals:\n"
            f"- Total Income: INR {data.get('total_income', 0.0):,.2f}\n"
            f"- Total Spend: INR {data.get('total_spend', 0.0):,.2f}\n"
            f"- Net Savings: INR {data.get('net_savings', 0.0):,.2f}\n"
            f"- Savings Rate: {round(data.get('savings_rate', 0.0) * 100, 1)}%"
        )


def get_category_breakdown(session_id: str) -> str:
    """Return spending details grouped by category for the session."""
    with get_db_conn() as conn:
        rows = conn.execute(
            """
            SELECT category, SUM(amount) as total, COUNT(*) as count
            FROM transactions
            WHERE session_id = ? AND direction = 'debit'
            GROUP BY category
            ORDER BY total DESC
            """,
            (session_id,),
        ).fetchall()

        if not rows:
            return "No spending recorded by category."

        lines = ["Spending by Category:"]
        for r in rows:
            lines.append(f"- {r['category']}: INR {r['total']:,.2f} ({r['count']} transactions)")
        return "\n".join(lines)


def get_recurring(session_id: str) -> str:
    """Return detected recurring payments for the session."""
    with get_db_conn() as conn:
        rows = conn.execute(
            """
            SELECT merchant, category, cadence, typical_amount, occurrences
            FROM recurring_groups
            WHERE session_id = ?
            """,
            (session_id,),
        ).fetchall()

        if not rows:
            return "No recurring payments detected."

        lines = ["Detected Recurring Payments:"]
        for r in rows:
            lines.append(
                f"- {r['merchant']} ({r['category']}): INR {r['typical_amount']:,.2f} "
                f"[{r['cadence']}, {r['occurrences']}x]"
            )
        return "\n".join(lines)


def get_top_transactions(session_id: str, limit: int = 5) -> str:
    """Return top largest debit transactions for the session."""
    with get_db_conn() as conn:
        rows = conn.execute(
            """
            SELECT date, description_clean, category, amount
            FROM transactions
            WHERE session_id = ? AND direction = 'debit'
            ORDER BY amount DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

        if not rows:
            return "No transaction expenses found."

        lines = [f"Top {limit} Expenses:"]
        for r in rows:
            lines.append(
                f"- {r['date']}: {r['description_clean']} ({r['category']}) — INR {r['amount']:,.2f}"
            )
        return "\n".join(lines)


def search_transactions(session_id: str, query: str) -> str:
    """Search transactions matching description or category keywords."""
    clean_query = f"%{query.upper()}%"
    with get_db_conn() as conn:
        rows = conn.execute(
            """
            SELECT date, description_raw, description_clean, category, amount, direction
            FROM transactions
            WHERE session_id = ? AND (
                description_clean LIKE ? OR
                description_raw LIKE ? OR
                category LIKE ?
            )
            ORDER BY date DESC
            LIMIT 15
            """,
            (session_id, clean_query, clean_query, clean_query),
        ).fetchall()

        if not rows:
            return f"No transactions match the query: '{query}'."

        lines = [f"Search Results for '{query}' (capped to 15):"]
        for r in rows:
            sign = "+" if r["direction"] == "credit" else "-"
            lines.append(
                f"- {r['date']}: {r['description_clean']} ({r['category']}) — {sign}INR {r['amount']:,.2f}"
            )
        return "\n".join(lines)
