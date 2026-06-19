"""Portfolio persistence operations."""

import sqlite3
from pathlib import Path

from fundlog.config import get_database_path
from fundlog.errors import (
    DatabaseNotInitializedError,
    InvalidPortfolioNameError,
    PortfolioAlreadyExistsError,
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
