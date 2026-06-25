"""Asset transaction persistence operations."""

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path

from mpal.amounts import parse_amount_minor
from mpal.asset_replay import AssetReplayTransaction, replay_asset_transactions
from mpal.errors import (
    AssetNotFoundError,
    AssetTransactionNotFoundError,
    InsufficientAssetQuantityError,
    InvalidLedgerDeleteError,
    InvalidLedgerEditError,
    InvalidTradeTotalError,
    PortfolioNotFoundError,
)
from mpal.numbers import parse_price, parse_quantity
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


def delete_asset_transaction_entry(
    portfolio_name: str,
    symbol: str,
    entry_no: int,
    database_path: Path | None = None,
) -> None:
    """Soft-delete one active asset transaction after replaying the remainder."""
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

        target = connection.execute(
            """
            SELECT id, deleted_at
            FROM asset_transactions
            WHERE asset_id = ? AND entry_no = ?
            """,
            (asset[0], entry_no),
        ).fetchone()
        if target is None:
            raise AssetTransactionNotFoundError(
                f"Asset transaction {entry_no} does not exist for asset "
                f"'{symbol}' in portfolio '{portfolio_name}'."
            )
        if target[1] is not None:
            raise AssetTransactionNotFoundError(
                f"Asset transaction {entry_no} is not active."
            )

        remaining_rows = connection.execute(
            """
            SELECT
                entry_no,
                transaction_type,
                price_text,
                quantity_text,
                fee_minor,
                total_minor
            FROM asset_transactions
            WHERE asset_id = ?
                AND deleted_at IS NULL
                AND id != ?
            ORDER BY entry_no ASC
            """,
            (asset[0], target[0]),
        ).fetchall()
        remaining_transactions = [
            AssetReplayTransaction(
                entry_no=row[0],
                transaction_type=row[1],
                price_text=row[2],
                quantity_text=row[3],
                fee_minor=row[4],
                total_minor=row[5],
            )
            for row in remaining_rows
        ]

        try:
            replay = replay_asset_transactions(remaining_transactions)
        except InvalidLedgerEditError as error:
            raise InvalidLedgerDeleteError(
                "Asset transaction cannot be deleted because it would make "
                "the remaining asset ledger invalid."
            ) from error

        for transaction in replay.transactions:
            connection.execute(
                """
                UPDATE asset_transactions
                SET cash_effect_minor = ?,
                    position_effect_minor = ?,
                    realized_pnl_minor = ?,
                    income_minor = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE asset_id = ?
                    AND entry_no = ?
                    AND deleted_at IS NULL
                """,
                (
                    transaction.cash_effect_minor,
                    transaction.position_effect_minor,
                    transaction.realized_pnl_minor,
                    transaction.income_minor,
                    asset[0],
                    transaction.entry_no,
                ),
            )

        connection.execute(
            """
            UPDATE asset_transactions
            SET deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (target[0],),
        )


def edit_asset_transaction_entry(
    portfolio_name: str,
    symbol: str,
    entry_no: int,
    *,
    amount: str | None = None,
    price: str | None = None,
    quantity: str | None = None,
    fee: str | None = None,
    total: str | None = None,
    transaction_date: date | None = None,
    note: str | None = None,
    database_path: Path | None = None,
) -> None:
    """Edit one active asset transaction and replay active transaction effects."""
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

        target = connection.execute(
            """
            SELECT
                id,
                transaction_type,
                transaction_date,
                price_text,
                quantity_text,
                fee_minor,
                total_minor,
                note,
                deleted_at
            FROM asset_transactions
            WHERE asset_id = ? AND entry_no = ?
            """,
            (asset[0], entry_no),
        ).fetchone()
        if target is None:
            raise AssetTransactionNotFoundError(
                f"Asset transaction {entry_no} does not exist for asset "
                f"'{symbol}' in portfolio '{portfolio_name}'."
            )
        if target[8] is not None:
            raise AssetTransactionNotFoundError(
                f"Asset transaction {entry_no} is not active."
            )

        edited = _resolve_asset_transaction_edit(
            transaction_type=target[1],
            current_date=target[2],
            current_price_text=target[3],
            current_quantity_text=target[4],
            current_fee_minor=target[5],
            current_total_minor=target[6],
            amount=amount,
            price=price,
            quantity=quantity,
            fee=fee,
            total=total,
            transaction_date=transaction_date,
        )

        active_rows = connection.execute(
            """
            SELECT
                entry_no,
                transaction_type,
                price_text,
                quantity_text,
                fee_minor,
                total_minor
            FROM asset_transactions
            WHERE asset_id = ? AND deleted_at IS NULL
            ORDER BY entry_no ASC
            """,
            (asset[0],),
        ).fetchall()
        replay_inputs = []
        for row in active_rows:
            if row[0] == entry_no:
                replay_inputs.append(
                    AssetReplayTransaction(
                        entry_no=entry_no,
                        transaction_type=target[1],
                        price_text=edited["price_text"],
                        quantity_text=edited["quantity_text"],
                        fee_minor=edited["fee_minor"],
                        total_minor=edited["total_minor"],
                    )
                )
                continue
            replay_inputs.append(
                AssetReplayTransaction(
                    entry_no=row[0],
                    transaction_type=row[1],
                    price_text=row[2],
                    quantity_text=row[3],
                    fee_minor=row[4],
                    total_minor=row[5],
                )
            )

        try:
            replay = replay_asset_transactions(replay_inputs)
        except InvalidLedgerEditError as error:
            raise InvalidLedgerEditError(
                "Asset transaction cannot be edited because it would make "
                "the active asset ledger invalid."
            ) from error

        connection.execute(
            """
            UPDATE asset_transactions
            SET transaction_date = ?,
                price_text = ?,
                quantity_text = ?,
                fee_minor = ?,
                total_minor = ?,
                note = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                edited["transaction_date"],
                edited["price_text"],
                edited["quantity_text"],
                edited["fee_minor"],
                edited["total_minor"],
                note if note is not None else target[7],
                target[0],
            ),
        )

        for transaction in replay.transactions:
            connection.execute(
                """
                UPDATE asset_transactions
                SET cash_effect_minor = ?,
                    position_effect_minor = ?,
                    realized_pnl_minor = ?,
                    income_minor = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE asset_id = ?
                    AND entry_no = ?
                    AND deleted_at IS NULL
                """,
                (
                    transaction.cash_effect_minor,
                    transaction.position_effect_minor,
                    transaction.realized_pnl_minor,
                    transaction.income_minor,
                    asset[0],
                    transaction.entry_no,
                ),
            )


def _resolve_asset_transaction_edit(
    *,
    transaction_type: str,
    current_date: str,
    current_price_text: str | None,
    current_quantity_text: str | None,
    current_fee_minor: int,
    current_total_minor: int,
    amount: str | None,
    price: str | None,
    quantity: str | None,
    fee: str | None,
    total: str | None,
    transaction_date: date | None,
) -> dict[str, int | str | None]:
    edited_date = (
        current_date if transaction_date is None else transaction_date.isoformat()
    )

    if transaction_type == "income":
        if any(value is not None for value in (price, quantity, fee, total)):
            raise InvalidLedgerEditError(
                "Income transactions can edit only amount, date, or note."
            )
        edited_total = (
            current_total_minor if amount is None else parse_amount_minor(amount)
        )
        return {
            "transaction_date": edited_date,
            "price_text": None,
            "quantity_text": None,
            "fee_minor": 0,
            "total_minor": edited_total,
        }

    if amount is not None:
        raise InvalidLedgerEditError(
            "Trade transactions cannot edit --amount; use --total for trade totals."
        )
    if transaction_type not in {"buy", "sell"}:
        raise InvalidLedgerEditError(
            f"Unknown asset transaction type '{transaction_type}'."
        )
    if current_price_text is None:
        raise InvalidLedgerEditError("Trade transactions require a price.")
    if current_quantity_text is None:
        raise InvalidLedgerEditError("Trade transactions require a quantity.")

    edited_price = (
        parse_price(current_price_text) if price is None else parse_price(price)
    )
    edited_quantity = (
        parse_quantity(current_quantity_text)
        if quantity is None
        else parse_quantity(quantity)
    )
    edited_fee = (
        current_fee_minor if fee is None else parse_amount_minor(fee, allow_zero=True)
    )
    provided_total = None if total is None else parse_amount_minor(total)
    numeric_changed = any(value is not None for value in (price, quantity, fee, total))
    if not numeric_changed:
        edited_total = current_total_minor
    elif transaction_type == "buy":
        edited_total = calculate_buy_total_minor(
            edited_price,
            edited_quantity,
            edited_fee,
            provided_total,
        )
    else:
        edited_total = calculate_sell_total_minor(
            edited_price,
            edited_quantity,
            edited_fee,
            provided_total,
        )

    return {
        "transaction_date": edited_date,
        "price_text": format(edited_price, "f"),
        "quantity_text": format(edited_quantity, "f"),
        "fee_minor": edited_fee,
        "total_minor": edited_total,
    }
