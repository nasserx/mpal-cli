"""Portfolio summary queries."""

from dataclasses import dataclass
from pathlib import Path

from fundlog.errors import PortfolioNotFoundError
from fundlog.storage.database import connect_database


@dataclass(frozen=True)
class PortfolioSummary:
    """Derived summary values for one portfolio."""

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
    """Return a summary derived from active capital and asset income."""
    with connect_database(database_path) as connection:
        row = connection.execute(
            """
            WITH capital_totals AS (
                SELECT
                    portfolio_id,
                    SUM(
                        CASE entry_type
                            WHEN 'inflow' THEN amount_minor
                            WHEN 'outflow' THEN -amount_minor
                        END
                    ) AS capital_minor
                FROM capital_entries
                WHERE deleted_at IS NULL
                GROUP BY portfolio_id
            ),
            income_totals AS (
                SELECT
                    a.portfolio_id,
                    SUM(t.income_minor) AS income_minor
                FROM assets AS a
                JOIN asset_transactions AS t ON t.asset_id = a.id
                WHERE a.deleted_at IS NULL
                    AND t.deleted_at IS NULL
                    AND t.transaction_type = 'income'
                GROUP BY a.portfolio_id
            )
            SELECT
                p.name,
                COALESCE(c.capital_minor, 0),
                COALESCE(i.income_minor, 0)
            FROM portfolios AS p
            LEFT JOIN capital_totals AS c ON c.portfolio_id = p.id
            LEFT JOIN income_totals AS i ON i.portfolio_id = p.id
            WHERE p.name = ? AND p.deleted_at IS NULL
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
            WITH capital_totals AS (
                SELECT
                    portfolio_id,
                    SUM(
                        CASE entry_type
                            WHEN 'inflow' THEN amount_minor
                            WHEN 'outflow' THEN -amount_minor
                        END
                    ) AS capital_minor
                FROM capital_entries
                WHERE deleted_at IS NULL
                GROUP BY portfolio_id
            ),
            income_totals AS (
                SELECT
                    a.portfolio_id,
                    SUM(t.income_minor) AS income_minor
                FROM assets AS a
                JOIN asset_transactions AS t ON t.asset_id = a.id
                WHERE a.deleted_at IS NULL
                    AND t.deleted_at IS NULL
                    AND t.transaction_type = 'income'
                GROUP BY a.portfolio_id
            )
            SELECT
                p.name,
                COALESCE(c.capital_minor, 0),
                COALESCE(i.income_minor, 0)
            FROM portfolios AS p
            LEFT JOIN capital_totals AS c ON c.portfolio_id = p.id
            LEFT JOIN income_totals AS i ON i.portfolio_id = p.id
            WHERE p.deleted_at IS NULL
            ORDER BY p.name ASC
            """
        ).fetchall()

    return [_summary_from_row(row) for row in rows]


def _summary_from_row(row: tuple[str, int, int]) -> PortfolioSummary:
    """Build a summary from active capital and income totals."""
    capital_minor = row[1]
    income_minor = row[2]
    positions_minor = 0
    cash_minor = capital_minor + income_minor
    return PortfolioSummary(
        portfolio_name=row[0],
        capital_minor=capital_minor,
        cash_minor=cash_minor,
        positions_minor=positions_minor,
        book_value_minor=cash_minor + positions_minor,
        realized_pnl_minor=0,
        income_minor=income_minor,
    )
