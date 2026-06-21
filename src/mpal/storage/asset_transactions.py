"""Asset transaction persistence operations."""

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path

from mpal.errors import (
    AssetNotFoundError,
    InsufficientAssetQuantityError,
    InvalidTradeTotalError,
    PortfolioNotFoundError,
)
from mpal.storage.database import connect_database, next_asset_transaction_no


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


def calculate_sell_total_minor(
    price: Decimal,
    quantity: Decimal,
    fee_minor: int,
    provided_total_minor: int | None,
) -> int:
    """Resolve exact net sell proceeds without implicit money rounding."""
    with localcontext() as context:
        context.prec = 80
        computed_minor = price * quantity * Decimal(100) - Decimal(fee_minor)

    if computed_minor <= 0:
        raise InvalidTradeTotalError("Net sell proceeds must be greater than zero.")

    computed_is_exact = computed_minor == computed_minor.to_integral_value()
    if provided_total_minor is None:
        if not computed_is_exact:
            raise InvalidTradeTotalError(
                "Sell total is not exactly representable in minor units. "
                "Provide --total from the broker or exchange statement."
            )
        return int(computed_minor)

    if computed_is_exact and int(computed_minor) != provided_total_minor:
        raise InvalidTradeTotalError(
            "Provided --total does not match price × quantity - fee."
        )
    return provided_total_minor


def record_sell(
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
    """Record one manual sell using moving-average book-cost allocation."""
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
            SELECT transaction_type, quantity_text, position_effect_minor
            FROM asset_transactions
            WHERE asset_id = ? AND deleted_at IS NULL
            """,
            (asset[0],),
        ).fetchall()
        open_quantity = sum(
            (
                Decimal(row[1]) if row[0] == "buy" else -Decimal(row[1])
                for row in rows
                if row[0] in {"buy", "sell"} and row[1] is not None
            ),
            Decimal(0),
        )
        if open_quantity <= 0:
            raise InsufficientAssetQuantityError(
                f"Asset '{symbol}' has no open quantity to sell."
            )
        if quantity > open_quantity:
            raise InsufficientAssetQuantityError(
                f"Sell quantity exceeds open quantity for asset '{symbol}'."
            )

        open_cost_basis_minor = sum(row[2] for row in rows)
        if quantity == open_quantity:
            relieved_cost_basis_minor = open_cost_basis_minor
        else:
            with localcontext() as context:
                context.prec = 80
                exact_relief = Decimal(open_cost_basis_minor) * quantity / open_quantity
                relieved_cost_basis_minor = int(
                    exact_relief.quantize(
                        Decimal("1"),
                        rounding=ROUND_HALF_EVEN,
                    )
                )

        realized_pnl_minor = total_minor - relieved_cost_basis_minor
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
            VALUES (?, ?, 'sell', ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                asset[0],
                entry_no,
                transaction_date.isoformat(),
                format(price, "f"),
                format(quantity, "f"),
                fee_minor,
                total_minor,
                total_minor,
                -relieved_cost_basis_minor,
                realized_pnl_minor,
                note,
            ),
        )

    return entry_no
