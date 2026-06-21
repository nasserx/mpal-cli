"""Capital entry persistence operations."""

import sqlite3
from datetime import date
from pathlib import Path

from mpal.errors import (
    CapitalEntryNotFoundError,
    InsufficientCashError,
    InvalidLedgerDeleteError,
    InvalidLedgerEditError,
    PortfolioNotFoundError,
)
from mpal.storage.database import connect_database, next_entry_no


def record_inflow(
    portfolio_name: str,
    amount_minor: int,
    entry_date: date,
    note: str | None = None,
    database_path: Path | None = None,
) -> int:
    """Record an inflow and return its internal row ID."""
    with connect_database(database_path) as connection:
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
                entry_no,
                entry_type,
                amount_minor,
                entry_date,
                note
            )
            VALUES (?, ?, 'inflow', ?, ?, ?)
            """,
            (
                portfolio[0],
                next_entry_no(connection, portfolio[0]),
                amount_minor,
                entry_date.isoformat(),
                note,
            ),
        )

    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return an internal entry row ID.")
    return cursor.lastrowid


def record_outflow(
    portfolio_name: str,
    amount_minor: int,
    entry_date: date,
    note: str | None = None,
    database_path: Path | None = None,
) -> int:
    """Record an outflow and return its internal row ID."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        cash_minor = _get_active_cash_minor(connection, portfolio[0])
        if cash_minor < amount_minor:
            raise InsufficientCashError(
                f"Insufficient cash in portfolio '{portfolio_name}'."
            )

        cursor = connection.execute(
            """
            INSERT INTO capital_entries (
                portfolio_id,
                entry_no,
                entry_type,
                amount_minor,
                entry_date,
                note
            )
            VALUES (?, ?, 'outflow', ?, ?, ?)
            """,
            (
                portfolio[0],
                next_entry_no(connection, portfolio[0]),
                amount_minor,
                entry_date.isoformat(),
                note,
            ),
        )

    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return an internal entry row ID.")
    return cursor.lastrowid


def edit_capital_entry(
    portfolio_name: str,
    entry_no: int,
    *,
    amount_minor: int | None = None,
    entry_date: date | None = None,
    note: str | None = None,
    database_path: Path | None = None,
) -> None:
    """Atomically update supplied fields on one active capital entry."""
    with connect_database(database_path) as connection:
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
            SELECT id, entry_type, amount_minor, deleted_at
            FROM capital_entries
            WHERE portfolio_id = ? AND entry_no = ?
            """,
            (portfolio[0], entry_no),
        ).fetchone()
        if entry is None:
            raise CapitalEntryNotFoundError(
                f"Capital entry {entry_no} does not exist in portfolio "
                f"'{portfolio_name}'."
            )
        if entry[3] is not None:
            raise CapitalEntryNotFoundError(f"Capital entry {entry_no} is not active.")

        if amount_minor is not None:
            cash_without_entry = _get_active_cash_minor(
                connection,
                portfolio[0],
                excluded_entry_id=entry[0],
            )
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
        values.append(entry[0])

        connection.execute(
            f"UPDATE capital_entries SET {', '.join(assignments)} WHERE id = ?",
            values,
        )


def delete_capital_entry(
    portfolio_name: str,
    entry_no: int,
    database_path: Path | None = None,
) -> None:
    """Atomically soft-delete one active capital entry."""
    with connect_database(database_path) as connection:
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
            SELECT id, deleted_at
            FROM capital_entries
            WHERE portfolio_id = ? AND entry_no = ?
            """,
            (portfolio[0], entry_no),
        ).fetchone()
        if entry is None:
            raise CapitalEntryNotFoundError(
                f"Capital entry {entry_no} does not exist in portfolio "
                f"'{portfolio_name}'."
            )
        if entry[1] is not None:
            raise CapitalEntryNotFoundError(f"Capital entry {entry_no} is not active.")

        cash_without_entry = _get_active_cash_minor(
            connection,
            portfolio[0],
            excluded_entry_id=entry[0],
        )
        if cash_without_entry < 0:
            raise InvalidLedgerDeleteError("Delete would make portfolio cash negative.")

        connection.execute(
            """
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (entry[0],),
        )


def reset_portfolio_entries(
    portfolio_name: str,
    database_path: Path | None = None,
) -> int:
    """Atomically soft-delete all active entries for one active portfolio."""
    with connect_database(database_path) as connection:
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
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE portfolio_id = ?
                AND deleted_at IS NULL
            """,
            (portfolio[0],),
        )

    return cursor.rowcount


def _get_active_cash_minor(
    connection: sqlite3.Connection,
    portfolio_id: int,
    *,
    excluded_entry_id: int | None = None,
) -> int:
    """Return current Cash from active capital and asset transaction effects."""
    excluded_clause = "" if excluded_entry_id is None else "AND id != ?"
    capital_parameters: tuple[int, ...] = (
        (portfolio_id,)
        if excluded_entry_id is None
        else (portfolio_id, excluded_entry_id)
    )
    capital_minor = connection.execute(
        f"""
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
            {excluded_clause}
        """,
        capital_parameters,
    ).fetchone()[0]
    asset_cash_minor = connection.execute(
        """
        SELECT COALESCE(SUM(t.cash_effect_minor), 0)
        FROM assets AS a
        JOIN asset_transactions AS t ON t.asset_id = a.id
        WHERE a.portfolio_id = ?
            AND a.deleted_at IS NULL
            AND t.deleted_at IS NULL
        """,
        (portfolio_id,),
    ).fetchone()[0]
    return capital_minor + asset_cash_minor
