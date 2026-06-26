"""Capital entry log queries."""

from dataclasses import dataclass
from pathlib import Path

from mpal.errors import PortfolioNotFoundError
from mpal.storage.database import connect_database


@dataclass(frozen=True)
class CapitalEntry:
    """One active capital entry displayed by the log command."""

    entry_no: int
    entry_date: str
    entry_type: str
    amount_minor: int
    note: str | None


@dataclass(frozen=True)
class CapitalState:
    """Capital-only current state for one active portfolio."""

    portfolio_name: str
    deposits_minor: int
    withdrawals_minor: int
    net_capital_minor: int


def get_capital_state(
    portfolio_name: str,
    database_path: Path | None = None,
) -> CapitalState:
    """Return capital-only current state for one active portfolio."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        row = connection.execute(
            """
            SELECT
                COALESCE(
                    SUM(CASE WHEN entry_type = 'inflow' THEN amount_minor ELSE 0 END),
                    0
                ),
                COALESCE(
                    SUM(CASE WHEN entry_type = 'outflow' THEN amount_minor ELSE 0 END),
                    0
                )
            FROM capital_entries
            WHERE portfolio_id = ? AND deleted_at IS NULL
            """,
            (portfolio[0],),
        ).fetchone()

    deposits_minor = row[0]
    withdrawals_minor = row[1]
    return CapitalState(
        portfolio_name=portfolio_name,
        deposits_minor=deposits_minor,
        withdrawals_minor=withdrawals_minor,
        net_capital_minor=deposits_minor - withdrawals_minor,
    )


def get_capital_entry_log(
    portfolio_name: str,
    database_path: Path | None = None,
) -> list[CapitalEntry]:
    """Return active entries ordered by date and then entry number."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        rows = connection.execute(
            """
            SELECT entry_no, entry_date, entry_type, amount_minor, note
            FROM capital_entries
            WHERE portfolio_id = ? AND deleted_at IS NULL
            ORDER BY entry_date ASC, entry_no ASC
            """,
            (portfolio[0],),
        ).fetchall()

    return [
        CapitalEntry(
            entry_no=row[0],
            entry_date=row[1],
            entry_type=row[2],
            amount_minor=row[3],
            note=row[4],
        )
        for row in rows
    ]
