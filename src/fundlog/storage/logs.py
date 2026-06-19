"""Capital entry log queries."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from fundlog.config import get_database_path
from fundlog.errors import DatabaseNotInitializedError, PortfolioNotFoundError

REQUIRED_TABLES = {"portfolios", "capital_entries"}


@dataclass(frozen=True)
class CapitalEntry:
    """One active capital entry displayed by the log command."""

    entry_id: int
    entry_date: str
    entry_type: str
    amount_minor: int
    note: str | None


def get_capital_entry_log(
    portfolio_name: str,
    database_path: Path | None = None,
) -> list[CapitalEntry]:
    """Return active entries ordered by date and then entry ID."""
    path = database_path if database_path is not None else get_database_path()
    if not path.is_file():
        raise DatabaseNotInitializedError(
            "FundLog is not initialized. Run 'fundlog init' first."
        )

    with sqlite3.connect(path) as connection:
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

        rows = connection.execute(
            """
            SELECT id, entry_date, entry_type, amount_minor, note
            FROM capital_entries
            WHERE portfolio_id = ? AND deleted_at IS NULL
            ORDER BY entry_date ASC, id ASC
            """,
            (portfolio[0],),
        ).fetchall()

    return [
        CapitalEntry(
            entry_id=row[0],
            entry_date=row[1],
            entry_type=row[2],
            amount_minor=row[3],
            note=row[4],
        )
        for row in rows
    ]
