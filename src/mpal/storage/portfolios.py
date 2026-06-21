"""Portfolio persistence operations."""

import sqlite3
from datetime import date
from pathlib import Path

from mpal.errors import (
    InvalidPortfolioNameError,
    PortfolioAlreadyExistsError,
    PortfolioNotFoundError,
)
from mpal.storage.database import connect_database, next_entry_no


def create_portfolio(name: str, database_path: Path | None = None) -> int:
    """Create an empty active portfolio and return its ID."""
    _validate_portfolio_name(name)

    with connect_database(database_path) as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO portfolios (name) VALUES (?)",
                (name,),
            )
        except sqlite3.IntegrityError as error:
            raise PortfolioAlreadyExistsError(
                f"An active portfolio named '{name}' already exists."
            ) from error

    if cursor.lastrowid is None:
        raise RuntimeError("SQLite did not return a portfolio ID.")
    return cursor.lastrowid


def create_portfolio_with_initial(
    name: str,
    amount_minor: int,
    entry_date: date,
    database_path: Path | None = None,
) -> int:
    """Atomically create a portfolio and its initial inflow entry."""
    _validate_portfolio_name(name)

    with connect_database(database_path) as connection:
        try:
            portfolio_cursor = connection.execute(
                "INSERT INTO portfolios (name) VALUES (?)",
                (name,),
            )
        except sqlite3.IntegrityError as error:
            raise PortfolioAlreadyExistsError(
                f"An active portfolio named '{name}' already exists."
            ) from error

        portfolio_id = portfolio_cursor.lastrowid
        if portfolio_id is None:
            raise RuntimeError("SQLite did not return a portfolio ID.")

        connection.execute(
            """
            INSERT INTO capital_entries (
                portfolio_id,
                entry_no,
                entry_type,
                amount_minor,
                entry_date
            )
            VALUES (?, ?, 'inflow', ?, ?)
            """,
            (
                portfolio_id,
                next_entry_no(connection, portfolio_id),
                amount_minor,
                entry_date.isoformat(),
            ),
        )

    return portfolio_id


def _validate_portfolio_name(name: str) -> None:
    """Validate a portfolio name against the current naming rules."""
    if not name.strip():
        raise InvalidPortfolioNameError("Portfolio name cannot be empty.")
    if "/" in name:
        raise InvalidPortfolioNameError("Portfolio name cannot contain '/'.")


def delete_portfolio(
    name: str,
    database_path: Path | None = None,
) -> None:
    """Atomically soft-delete a portfolio and all its active entries."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(f"Active portfolio '{name}' does not exist.")

        connection.execute(
            """
            UPDATE capital_entries
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE portfolio_id = ?
                AND deleted_at IS NULL
            """,
            (portfolio[0],),
        )
        connection.execute(
            """
            UPDATE portfolios
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
                AND deleted_at IS NULL
            """,
            (portfolio[0],),
        )
