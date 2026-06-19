"""Single-portfolio summary queries."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from fundlog.config import get_database_path
from fundlog.errors import DatabaseNotInitializedError, PortfolioNotFoundError

REQUIRED_TABLES = {"portfolios", "capital_entries"}


@dataclass(frozen=True)
class PortfolioSummary:
    """Derived v0.1 summary values for one portfolio."""

    portfolio_id: int
    portfolio_name: str
    capital_minor: int
    cash_minor: int
    invested_minor: int
    value_minor: int


def get_portfolio_summary(
    portfolio_name: str,
    database_path: Path | None = None,
) -> PortfolioSummary:
    """Return a summary derived from active capital entries."""
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

        row = connection.execute(
            """
            SELECT
                p.id,
                p.name,
                COALESCE(
                    SUM(
                        CASE e.entry_type
                            WHEN 'inflow' THEN e.amount_minor
                            WHEN 'outflow' THEN -e.amount_minor
                        END
                    ),
                    0
                )
            FROM portfolios AS p
            LEFT JOIN capital_entries AS e
                ON e.portfolio_id = p.id
                AND e.deleted_at IS NULL
            WHERE p.name = ? AND p.deleted_at IS NULL
            GROUP BY p.id, p.name
            """,
            (portfolio_name,),
        ).fetchone()

    if row is None:
        raise PortfolioNotFoundError(
            f"Active portfolio '{portfolio_name}' does not exist."
        )

    capital_minor = row[2]
    invested_minor = 0
    return PortfolioSummary(
        portfolio_id=row[0],
        portfolio_name=row[1],
        capital_minor=capital_minor,
        cash_minor=capital_minor,
        invested_minor=invested_minor,
        value_minor=capital_minor + invested_minor,
    )
