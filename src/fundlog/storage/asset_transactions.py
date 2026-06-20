"""Asset transaction persistence operations."""

from datetime import date
from pathlib import Path

from fundlog.errors import AssetNotFoundError, PortfolioNotFoundError
from fundlog.storage.database import connect_database, next_asset_transaction_no


def record_income(
    portfolio_name: str,
    symbol: str,
    amount_minor: int,
    transaction_date: date,
    note: str | None = None,
    database_path: Path | None = None,
) -> int:
    """Record manual income for one active asset and return its local number."""
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

        entry_no = next_asset_transaction_no(connection, asset[0])
        connection.execute(
            """
            INSERT INTO asset_transactions (
                asset_id,
                entry_no,
                transaction_type,
                transaction_date,
                price_text,
                quantity_text,
                fee_minor,
                total_minor,
                cash_effect_minor,
                position_effect_minor,
                realized_pnl_minor,
                income_minor,
                note
            )
            VALUES (?, ?, 'income', ?, NULL, NULL, 0, ?, ?, 0, 0, ?, ?)
            """,
            (
                asset[0],
                entry_no,
                transaction_date.isoformat(),
                amount_minor,
                amount_minor,
                amount_minor,
                note,
            ),
        )

    return entry_no
