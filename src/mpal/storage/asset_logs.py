"""Read-only asset transaction log queries."""

from dataclasses import dataclass
from pathlib import Path

from mpal.errors import AssetNotFoundError, PortfolioNotFoundError
from mpal.storage.database import connect_database


@dataclass(frozen=True)
class AssetTransaction:
    """One active transaction displayed by an asset log."""

    entry_no: int
    transaction_date: str
    transaction_type: str
    price_text: str | None
    quantity_text: str | None
    fee_minor: int
    total_minor: int
    note: str | None


def get_asset_transaction_log(
    portfolio_name: str,
    symbol: str,
    database_path: Path | None = None,
) -> list[AssetTransaction]:
    """Return active asset transactions ordered by date and local number."""
    with connect_database(database_path) as connection:
        portfolio = connection.execute(
            "SELECT id FROM portfolios WHERE name = ? AND deleted_at IS NULL",
            (portfolio_name,),
        ).fetchone()
        if portfolio is None:
            raise PortfolioNotFoundError(
                f"Active portfolio '{portfolio_name}' does not exist."
            )

        asset = connection.execute(
            """
            SELECT id
            FROM assets
            WHERE portfolio_id = ?
                AND symbol = ?
                AND deleted_at IS NULL
            """,
            (portfolio[0], symbol),
        ).fetchone()
        if asset is None:
            raise AssetNotFoundError(
                f"Active asset '{symbol}' does not exist in portfolio "
                f"'{portfolio_name}'."
            )

        rows = connection.execute(
            """
            SELECT
                entry_no,
                transaction_date,
                transaction_type,
                price_text,
                quantity_text,
                fee_minor,
                total_minor,
                note
            FROM asset_transactions
            WHERE asset_id = ? AND deleted_at IS NULL
            ORDER BY transaction_date ASC, entry_no ASC
            """,
            (asset[0],),
        ).fetchall()

    return [
        AssetTransaction(
            entry_no=row[0],
            transaction_date=row[1],
            transaction_type=row[2],
            price_text=row[3],
            quantity_text=row[4],
            fee_minor=row[5],
            total_minor=row[6],
            note=row[7],
        )
        for row in rows
    ]
