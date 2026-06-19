"""Capital entry persistence operations."""

import sqlite3
from datetime import date
from pathlib import Path

from fundlog.config import get_database_path
from fundlog.errors import (
    CapitalEntryNotFoundError,
    CapitalEntryPortfolioMismatchError,
    DatabaseNotInitializedError,
    InsufficientCashError,
    InvalidLedgerEditError,
    InvalidLedgerRemoveError,
    PortfolioNotFoundError,
)

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


def record_outflow(
    portfolio_name: str,
    amount_minor: int,
    entry_date: date,
    note: str | None = None,
    database_path: Path | None = None,
) -> int:
    """Record an outflow when the active portfolio has sufficient cash."""
    path = database_path if database_path is not None else get_database_path()
    if not path.is_file():
        raise DatabaseNotInitializedError(
            "FundLog is not initialized. Run 'fundlog init' first."
        )

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
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

        cash_minor = connection.execute(
            """
            SELECT COALESCE(
                SUM(
                    CASE entry_type
                        WHEN 'inflow' THEN amount_minor
                        WHEN 'outflow' THEN -amount_minor
                    END
                ),
                0
            )
            FROM capital_entries
            WHERE portfolio_id = ? AND deleted_at IS NULL
            """,
            (portfolio[0],),
        ).fetchone()[0]
        if cash_minor < amount_minor:
            raise InsufficientCashError(
                f"Insufficient cash in portfolio '{portfolio_name}'."
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
            VALUES (?, 'outflow', ?, ?, ?)
            """,
            (portfolio[0], amount_minor, entry_date.isoformat(), note),
        )

    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return a capital entry ID.")
    return cursor.lastrowid


def edit_capital_entry(
    portfolio_name: str,
    entry_id: int,
    *,
    amount_minor: int | None = None,
    entry_date: date | None = None,
    note: str | None = None,
    database_path: Path | None = None,
) -> None:
    """Atomically update supplied fields on one active capital entry."""
    path = database_path if database_path is not None else get_database_path()
    if not path.is_file():
        raise DatabaseNotInitializedError(
            "FundLog is not initialized. Run 'fundlog init' first."
        )

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
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

        entry = connection.execute(
            """
            SELECT portfolio_id, entry_type, amount_minor, deleted_at
            FROM capital_entries
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()
        if entry is None:
            raise CapitalEntryNotFoundError(f"Capital entry {entry_id} does not exist.")
        if entry[3] is not None:
            raise CapitalEntryNotFoundError(f"Capital entry {entry_id} is not active.")
        if entry[0] != portfolio[0]:
            raise CapitalEntryPortfolioMismatchError(
                f"Capital entry {entry_id} does not belong to portfolio "
                f"'{portfolio_name}'."
            )

        if amount_minor is not None:
            cash_without_entry = connection.execute(
                """
                SELECT COALESCE(
                    SUM(
                        CASE entry_type
                            WHEN 'inflow' THEN amount_minor
                            WHEN 'outflow' THEN -amount_minor
                        END
                    ),
                    0
                )
                FROM capital_entries
                WHERE portfolio_id = ?
                    AND deleted_at IS NULL
                    AND id != ?
                """,
                (portfolio[0], entry_id),
            ).fetchone()[0]
            edited_effect = amount_minor if entry[1] == "inflow" else -amount_minor
            if cash_without_entry + edited_effect < 0:
                raise InvalidLedgerEditError("Edit would make portfolio cash negative.")

        assignments: list[str] = []
        values: list[int | str] = []
        if amount_minor is not None:
            assignments.append("amount_minor = ?")
            values.append(amount_minor)
        if entry_date is not None:
            assignments.append("entry_date = ?")
            values.append(entry_date.isoformat())
        if note is not None:
            assignments.append("note = ?")
            values.append(note)
        assignments.append("updated_at = CURRENT_TIMESTAMP")
        values.append(entry_id)

        connection.execute(
            f"UPDATE capital_entries SET {', '.join(assignments)} WHERE id = ?",
            values,
        )


def remove_capital_entry(
    portfolio_name: str,
    entry_id: int,
    database_path: Path | None = None,
) -> None:
    """Atomically soft-delete one active capital entry."""
    path = database_path if database_path is not None else get_database_path()
    if not path.is_file():
        raise DatabaseNotInitializedError(
            "FundLog is not initialized. Run 'fundlog init' first."
        )

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
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

        entry = connection.execute(
            """
            SELECT portfolio_id, deleted_at
            FROM capital_entries
            WHERE id = ?
            """,
            (entry_id,),
        ).fetchone()
        if entry is None:
            raise CapitalEntryNotFoundError(f"Capital entry {entry_id} does not exist.")
        if entry[1] is not None:
            raise CapitalEntryNotFoundError(f"Capital entry {entry_id} is not active.")
        if entry[0] != portfolio[0]:
            raise CapitalEntryPortfolioMismatchError(
                f"Capital entry {entry_id} does not belong to portfolio "
                f"'{portfolio_name}'."
            )

        cash_without_entry = connection.execute(
            """
            SELECT COALESCE(
                SUM(
                    CASE entry_type
                        WHEN 'inflow' THEN amount_minor
                        WHEN 'outflow' THEN -amount_minor
                    END
                ),
                0
            )
            FROM capital_entries
            WHERE portfolio_id = ?
                AND deleted_at IS NULL
                AND id != ?
            """,
            (portfolio[0], entry_id),
        ).fetchone()[0]
        if cash_without_entry < 0:
            raise InvalidLedgerRemoveError("Remove would make portfolio cash negative.")

        connection.execute(
            """
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (entry_id,),
        )
