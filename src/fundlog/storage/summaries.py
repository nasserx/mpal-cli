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

    portfolio_name: str
    capital_minor: int
    cash_minor: int
    positions_minor: int
    book_value_minor: int
    realized_pnl_minor: int
    income_minor: int


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

    capital_minor = row[1]
    positions_minor = 0
    return PortfolioSummary(
        portfolio_name=row[0],
        capital_minor=capital_minor,
        cash_minor=capital_minor,
        positions_minor=positions_minor,
        book_value_minor=capital_minor + positions_minor,
        realized_pnl_minor=0,
        income_minor=0,
    )
