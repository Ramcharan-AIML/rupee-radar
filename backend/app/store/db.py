"""Database helper modules — connection manager and migrations initialization.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

from app.config import get_settings


def init_db() -> None:
    """Initialize the SQLite database schema if tables do not exist."""
    settings = get_settings()
    db_path = settings.db_path

    # Ensure parent directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")

        # Create analyses table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            session_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            metrics TEXT NOT NULL,
            insights TEXT NOT NULL,
            narrative TEXT
        );
        """)

        # Migration: alter table if analyses lacks narrative column
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(analyses);")
        columns = [col[1] for col in cursor.fetchall()]
        if "narrative" not in columns:
            conn.execute("ALTER TABLE analyses ADD COLUMN narrative TEXT;")

        # Create transactions table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            date TEXT NOT NULL,
            description_raw TEXT NOT NULL,
            description_clean TEXT NOT NULL,
            amount REAL NOT NULL,
            direction TEXT NOT NULL,
            category TEXT NOT NULL,
            category_source TEXT NOT NULL,
            confidence REAL NOT NULL,
            is_recurring INTEGER NOT NULL,
            recurring_group_id TEXT,
            FOREIGN KEY (session_id) REFERENCES analyses (session_id) ON DELETE CASCADE
        );
        """)

        # Create recurring_groups table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS recurring_groups (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            merchant TEXT NOT NULL,
            cadence TEXT NOT NULL,
            typical_amount REAL NOT NULL,
            occurrences INTEGER NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES analyses (session_id) ON DELETE CASCADE
        );
        """)

        # Create category_cache table (Phase 8/9 helper)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS category_cache (
            description_clean TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            confidence REAL NOT NULL
        );
        """)

        # Create insight_cache table (Phase 8/10 helper)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS insight_cache (
            cache_key TEXT PRIMARY KEY,
            insights TEXT NOT NULL,
            narrative TEXT
        );
        """)

        # Create chat_history table (Phase 8/11 helper)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)

        # Create llm_usage table (Phase 8 rate limit helper)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL
        );
        """)

        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db_conn() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional, thread-safe connection to the SQLite database.

    Enforces foreign keys.
    """
    settings = get_settings()
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
