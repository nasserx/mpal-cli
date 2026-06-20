"""Portfolio summary queries."""

from dataclasses import dataclass
from pathlib import Path

from fundlog.errors import PortfolioNotFoundError
from fundlog.storage.database import connect_database


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
    with connect_database(database_path) as connection:
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

    return _summary_from_row(row)


def get_all_portfolio_summaries(
    database_path: Path | None = None,
) -> list[PortfolioSummary]:
    """Return summaries for all active portfolios ordered by name."""
    with connect_database(database_path) as connection:
        rows = connection.execute(
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
            WHERE p.deleted_at IS NULL
            GROUP BY p.id, p.name
            ORDER BY p.name ASC
            """
        ).fetchall()

    return [_summary_from_row(row) for row in rows]


def _summary_from_row(row: tuple[str, int]) -> PortfolioSummary:
    """Build a v0.1 summary from a name and active capital total."""
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
