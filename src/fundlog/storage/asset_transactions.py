"""Asset transaction persistence operations."""

from datetime import date
from decimal import Decimal, localcontext
from pathlib import Path

from fundlog.errors import (
    AssetNotFoundError,
    InvalidTradeTotalError,
    PortfolioNotFoundError,
)
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


def calculate_buy_total_minor(
    price: Decimal,
    quantity: Decimal,
    fee_minor: int,
    provided_total_minor: int | None,
) -> int:
    """Resolve an exact buy cash outflow without implicit money rounding."""
    with localcontext() as context:
        context.prec = 80
        computed_minor = price * quantity * Decimal(100) + Decimal(fee_minor)

    computed_is_exact = computed_minor == computed_minor.to_integral_value()
    if provided_total_minor is None:
        if not computed_is_exact:
            raise InvalidTradeTotalError(
                "Buy total is not exactly representable in minor units. "
                "Provide --total from the broker or exchange statement."
            )
        return int(computed_minor)

    if computed_is_exact and int(computed_minor) != provided_total_minor:
        raise InvalidTradeTotalError(
            "Provided --total does not match price × quantity + fee."
        )
    return provided_total_minor


def record_buy(
    portfolio_name: str,
    symbol: str,
    price: Decimal,
    quantity: Decimal,
    fee_minor: int,
    total_minor: int,
    transaction_date: date,
    note: str | None = None,
    database_path: Path | None = None,
) -> int:
    """Record one exact manual buy and return its asset-local number."""
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
            VALUES (?, ?, 'buy', ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
            """,
            (
                asset[0],
                entry_no,
                transaction_date.isoformat(),
                format(price, "f"),
                format(quantity, "f"),
                fee_minor,
                total_minor,
                -total_minor,
                total_minor,
                note,
            ),
        )

    return entry_no
