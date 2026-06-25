"""Deterministic asset transaction replay for correction workflows."""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from mpal.errors import InvalidLedgerEditError, InvalidPriceError, InvalidQuantityError
from mpal.numbers import parse_price, parse_quantity


@dataclass(frozen=True)
class AssetReplayTransaction:
    """One asset transaction input for replay."""

    entry_no: int
    transaction_type: str
    price_text: str | None
    quantity_text: str | None
    fee_minor: int
    total_minor: int


@dataclass(frozen=True)
class ReplayedAssetTransaction:
    """One transaction with recalculated accounting effects."""

    entry_no: int
    transaction_type: str
    price_text: str | None
    quantity_text: str | None
    fee_minor: int
    total_minor: int
    cash_effect_minor: int
    position_effect_minor: int
    realized_pnl_minor: int
    income_minor: int


@dataclass(frozen=True)
class AssetReplayState:
    """Aggregate state after replaying one asset ledger."""

    quantity: Decimal
    cost_basis_minor: int
    cash_effect_minor: int
    realized_pnl_minor: int
    income_minor: int
    total_buy_cost_minor: int


@dataclass(frozen=True)
class AssetReplayResult:
    """Replayed transactions and the resulting aggregate state."""

    transactions: tuple[ReplayedAssetTransaction, ...]
    state: AssetReplayState


def replay_asset_transactions(
    transactions: list[AssetReplayTransaction] | tuple[AssetReplayTransaction, ...],
) -> AssetReplayResult:
    """Replay asset transactions in asset-local entry number order."""
    open_quantity = Decimal(0)
    open_cost_basis_minor = 0
    cash_effect_minor = 0
    realized_pnl_minor = 0
    income_minor = 0
    total_buy_cost_minor = 0
    replayed: list[ReplayedAssetTransaction] = []

    for transaction in sorted(transactions, key=lambda item: item.entry_no):
        _validate_entry_no(transaction.entry_no)
        _validate_money_fields(transaction)

        match transaction.transaction_type:
            case "income":
                row = _replay_income(transaction)
            case "buy":
                row, open_quantity, open_cost_basis_minor = _replay_buy(
                    transaction,
                    open_quantity,
                    open_cost_basis_minor,
                )
                total_buy_cost_minor += transaction.total_minor
            case "sell":
                row, open_quantity, open_cost_basis_minor = _replay_sell(
                    transaction,
                    open_quantity,
                    open_cost_basis_minor,
                )
                realized_pnl_minor += row.realized_pnl_minor
            case _:
                raise InvalidLedgerEditError(
                    f"Unknown asset transaction type '{transaction.transaction_type}'."
                )

        if open_quantity < 0:
            raise InvalidLedgerEditError("Replay would make asset quantity negative.")
        if open_cost_basis_minor < 0:
            raise InvalidLedgerEditError("Replay would make asset Cost Basis negative.")

        cash_effect_minor += row.cash_effect_minor
        income_minor += row.income_minor
        replayed.append(row)

    return AssetReplayResult(
        transactions=tuple(replayed),
        state=AssetReplayState(
            quantity=open_quantity,
            cost_basis_minor=open_cost_basis_minor,
            cash_effect_minor=cash_effect_minor,
            realized_pnl_minor=realized_pnl_minor,
            income_minor=income_minor,
            total_buy_cost_minor=total_buy_cost_minor,
        ),
    )


def _replay_income(transaction: AssetReplayTransaction) -> ReplayedAssetTransaction:
    if transaction.price_text is not None or transaction.quantity_text is not None:
        raise InvalidLedgerEditError(
            "Income transactions cannot have price or quantity."
        )
    if transaction.fee_minor != 0:
        raise InvalidLedgerEditError("Income transactions cannot have a fee.")

    return ReplayedAssetTransaction(
        entry_no=transaction.entry_no,
        transaction_type="income",
        price_text=None,
        quantity_text=None,
        fee_minor=0,
        total_minor=transaction.total_minor,
        cash_effect_minor=transaction.total_minor,
        position_effect_minor=0,
        realized_pnl_minor=0,
        income_minor=transaction.total_minor,
    )


def _replay_buy(
    transaction: AssetReplayTransaction,
    open_quantity: Decimal,
    open_cost_basis_minor: int,
) -> tuple[ReplayedAssetTransaction, Decimal, int]:
    price, quantity = _parse_trade_values(transaction)
    _validate_buy_total(price, quantity, transaction.fee_minor, transaction.total_minor)

    row = ReplayedAssetTransaction(
        entry_no=transaction.entry_no,
        transaction_type="buy",
        price_text=transaction.price_text,
        quantity_text=transaction.quantity_text,
        fee_minor=transaction.fee_minor,
        total_minor=transaction.total_minor,
        cash_effect_minor=-transaction.total_minor,
        position_effect_minor=transaction.total_minor,
        realized_pnl_minor=0,
        income_minor=0,
    )
    return (
        row,
        open_quantity + quantity,
        open_cost_basis_minor + transaction.total_minor,
    )


def _replay_sell(
    transaction: AssetReplayTransaction,
    open_quantity: Decimal,
    open_cost_basis_minor: int,
) -> tuple[ReplayedAssetTransaction, Decimal, int]:
    price, quantity = _parse_trade_values(transaction)
    _validate_sell_total(
        price,
        quantity,
        transaction.fee_minor,
        transaction.total_minor,
    )

    if open_quantity <= 0:
        raise InvalidLedgerEditError("Replay sell has no open quantity.")
    if quantity > open_quantity:
        raise InvalidLedgerEditError("Replay sell quantity exceeds open quantity.")

    if quantity == open_quantity:
        relieved_cost_basis_minor = open_cost_basis_minor
        remaining_quantity = Decimal(0)
        remaining_cost_basis_minor = 0
    else:
        with localcontext() as context:
            context.prec = 80
            exact_relief = Decimal(open_cost_basis_minor) * quantity / open_quantity
            relieved_cost_basis_minor = int(
                exact_relief.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
            )
        remaining_quantity = open_quantity - quantity
        remaining_cost_basis_minor = open_cost_basis_minor - relieved_cost_basis_minor

    realized_pnl_minor = transaction.total_minor - relieved_cost_basis_minor
    row = ReplayedAssetTransaction(
        entry_no=transaction.entry_no,
        transaction_type="sell",
        price_text=transaction.price_text,
        quantity_text=transaction.quantity_text,
        fee_minor=transaction.fee_minor,
        total_minor=transaction.total_minor,
        cash_effect_minor=transaction.total_minor,
        position_effect_minor=-relieved_cost_basis_minor,
        realized_pnl_minor=realized_pnl_minor,
        income_minor=0,
    )
    return row, remaining_quantity, remaining_cost_basis_minor


def _parse_trade_values(transaction: AssetReplayTransaction) -> tuple[Decimal, Decimal]:
    if transaction.price_text is None:
        raise InvalidLedgerEditError("Trade transactions require a price.")
    if transaction.quantity_text is None:
        raise InvalidLedgerEditError("Trade transactions require a quantity.")

    try:
        price = parse_price(transaction.price_text)
        quantity = parse_quantity(transaction.quantity_text)
    except (InvalidPriceError, InvalidQuantityError) as error:
        raise InvalidLedgerEditError(str(error)) from error

    return price, quantity


def _validate_buy_total(
    price: Decimal,
    quantity: Decimal,
    fee_minor: int,
    total_minor: int,
) -> None:
    with localcontext() as context:
        context.prec = 80
        computed_minor = price * quantity * Decimal(100) + Decimal(fee_minor)

    if computed_minor == computed_minor.to_integral_value():
        computed_total_minor = int(computed_minor)
        if computed_total_minor != total_minor:
            raise InvalidLedgerEditError(
                "Stored buy total does not match price × quantity + fee."
            )


def _validate_sell_total(
    price: Decimal,
    quantity: Decimal,
    fee_minor: int,
    total_minor: int,
) -> None:
    with localcontext() as context:
        context.prec = 80
        computed_minor = price * quantity * Decimal(100) - Decimal(fee_minor)

    if computed_minor <= 0:
        raise InvalidLedgerEditError(
            "Replay sell net proceeds must be greater than zero."
        )
    if computed_minor == computed_minor.to_integral_value():
        computed_total_minor = int(computed_minor)
        if computed_total_minor != total_minor:
            raise InvalidLedgerEditError(
                "Stored sell total does not match price × quantity - fee."
            )


def _validate_entry_no(entry_no: int) -> None:
    if not isinstance(entry_no, int) or isinstance(entry_no, bool) or entry_no <= 0:
        raise InvalidLedgerEditError("Asset transaction entry number must be positive.")


def _validate_money_fields(transaction: AssetReplayTransaction) -> None:
    if (
        not isinstance(transaction.fee_minor, int)
        or isinstance(transaction.fee_minor, bool)
        or transaction.fee_minor < 0
    ):
        raise InvalidLedgerEditError("Asset transaction fee must be nonnegative.")
    if (
        not isinstance(transaction.total_minor, int)
        or isinstance(transaction.total_minor, bool)
        or transaction.total_minor <= 0
    ):
        raise InvalidLedgerEditError(
            "Asset transaction total must be greater than zero."
        )
