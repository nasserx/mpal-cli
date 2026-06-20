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
            transaction_totals AS (
                SELECT
                    a.portfolio_id,
                    SUM(t.cash_effect_minor) AS cash_effect_minor,
                    SUM(t.position_effect_minor) AS position_effect_minor,
                    SUM(t.realized_pnl_minor) AS realized_pnl_minor,
                    SUM(t.income_minor) AS income_minor
                FROM assets AS a
                JOIN asset_transactions AS t ON t.asset_id = a.id
                WHERE a.deleted_at IS NULL
                    AND t.deleted_at IS NULL
                GROUP BY a.portfolio_id
            )
            SELECT
                p.name,
                COALESCE(c.capital_minor, 0),
                COALESCE(t.cash_effect_minor, 0),
                COALESCE(t.position_effect_minor, 0),
                COALESCE(t.realized_pnl_minor, 0),
                COALESCE(t.income_minor, 0)
            FROM portfolios AS p
            LEFT JOIN capital_totals AS c ON c.portfolio_id = p.id
            LEFT JOIN transaction_totals AS t ON t.portfolio_id = p.id
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
            transaction_totals AS (
                SELECT
                    a.portfolio_id,
                    SUM(t.cash_effect_minor) AS cash_effect_minor,
                    SUM(t.position_effect_minor) AS position_effect_minor,
                    SUM(t.realized_pnl_minor) AS realized_pnl_minor,
                    SUM(t.income_minor) AS income_minor
                FROM assets AS a
                JOIN asset_transactions AS t ON t.asset_id = a.id
                WHERE a.deleted_at IS NULL
                    AND t.deleted_at IS NULL
                GROUP BY a.portfolio_id
            )
            SELECT
                p.name,
                COALESCE(c.capital_minor, 0),
                COALESCE(t.cash_effect_minor, 0),
                COALESCE(t.position_effect_minor, 0),
                COALESCE(t.realized_pnl_minor, 0),
                COALESCE(t.income_minor, 0)
            FROM portfolios AS p
            LEFT JOIN capital_totals AS c ON c.portfolio_id = p.id
            LEFT JOIN transaction_totals AS t ON t.portfolio_id = p.id
            WHERE p.deleted_at IS NULL
            ORDER BY p.name ASC
            """
        ).fetchall()

    return [_summary_from_row(row) for row in rows]


def _summary_from_row(
    row: tuple[str, int, int, int, int, int],
) -> PortfolioSummary:
    """Build a summary from active capital and transaction totals."""
    capital_minor = row[1]
    cash_effect_minor = row[2]
    positions_minor = row[3]
    realized_pnl_minor = row[4]
    income_minor = row[5]
    cash_minor = capital_minor + cash_effect_minor
    return PortfolioSummary(
        portfolio_name=row[0],
        capital_minor=capital_minor,
        cash_minor=cash_minor,
        positions_minor=positions_minor,
        book_value_minor=cash_minor + positions_minor,
        realized_pnl_minor=realized_pnl_minor,
        income_minor=income_minor,
    )
