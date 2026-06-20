"""Portfolio persistence operations."""

import sqlite3
from datetime import date
from pathlib import Path

from fundlog.config import get_database_path
from fundlog.errors import (
    DatabaseNotInitializedError,
    InvalidPortfolioNameError,
    PortfolioAlreadyExistsError,
    PortfolioNotFoundError,
)

REQUIRED_TABLES = {"portfolios", "capital_entries"}


def create_portfolio(name: str, database_path: Path | None = None) -> int:
    """Create an empty active portfolio and return its ID."""
    if not name.strip():
        raise InvalidPortfolioNameError("Portfolio name cannot be empty.")

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
    if not name.strip():
        raise InvalidPortfolioNameError("Portfolio name cannot be empty.")

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
                entry_type,
                amount_minor,
                entry_date
            )
            VALUES (?, 'inflow', ?, ?)
            """,
            (portfolio_id, amount_minor, entry_date.isoformat()),
        )

    return portfolio_id


def delete_portfolio(
    name: str,
    database_path: Path | None = None,
) -> None:
    """Atomically soft-delete a portfolio and all its active entries."""
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
