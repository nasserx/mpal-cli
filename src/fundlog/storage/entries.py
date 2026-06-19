"""Capital entry persistence operations."""

import sqlite3
from datetime import date
from pathlib import Path

from fundlog.config import get_database_path
from fundlog.errors import DatabaseNotInitializedError, PortfolioNotFoundError

REQUIRED_TABLES = {"portfolios", "capital_entries"}


def record_inflow(
    portfolio_name: str,
    amount_minor: int,
    entry_date: date,
    note: str | None = None,
    database_path: Path | None = None,
) -> int:
    """Record an inflow for an active portfolio and return the entry ID."""
    path = database_path if database_path is not None else get_database_path()
    if not path.is_file():
        raise DatabaseNotInitializedError(
            "FundLog is not initialized. Run 'fundlog init' first."
        )

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not REQUIRED_TABLES.issubset(tables):
            raise DatabaseNotInitializedError(
                "FundLog is not initialized. Run 'fundlog init' first."
            )

        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        cursor = connection.execute(
            """
            INSERT INTO capital_entries (
                portfolio_id,
                entry_type,
                amount_minor,
                entry_date,
                note
            )
            VALUES (?, 'inflow', ?, ?, ?)
            """,
            (portfolio[0], amount_minor, entry_date.isoformat(), note),
        )

    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return a capital entry ID.")
    return cursor.lastrowid
