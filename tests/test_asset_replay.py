"""Unit tests for internal asset transaction replay."""

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from mpal.asset_replay import AssetReplayTransaction, replay_asset_transactions
from mpal.errors import InvalidLedgerEditError


def _transaction(
    entry_no: int,
    transaction_type: str,
    *,
    price_text: str | None = None,
    quantity_text: str | None = None,
    fee_minor: int = 0,
    total_minor: int,
) -> AssetReplayTransaction:
    return AssetReplayTransaction(
        entry_no=entry_no,
        transaction_type=transaction_type,
        price_text=price_text,
        quantity_text=quantity_text,
        fee_minor=fee_minor,
        total_minor=total_minor,
    )


def _income(entry_no: int, total_minor: int) -> AssetReplayTransaction:
    return _transaction(entry_no, "income", total_minor=total_minor)


def _buy(
    entry_no: int,
    *,
    price_text: str,
    quantity_text: str,
    fee_minor: int = 0,
    total_minor: int,
) -> AssetReplayTransaction:
    return _transaction(
        entry_no,
        "buy",
        price_text=price_text,
        quantity_text=quantity_text,
        fee_minor=fee_minor,
        total_minor=total_minor,
    )


def _sell(
    entry_no: int,
    *,
    price_text: str,
    quantity_text: str,
    fee_minor: int = 0,
    total_minor: int,
) -> AssetReplayTransaction:
    return _transaction(
        entry_no,
        "sell",
        price_text=price_text,
        quantity_text=quantity_text,
        fee_minor=fee_minor,
        total_minor=total_minor,
    )


def test_replay_income_row() -> None:
    result = replay_asset_transactions([_income(1, 2_500)])

    assert result.transactions[0] == _expected(
        1,
        "income",
        None,
        None,
        0,
        2_500,
        2_500,
        0,
        0,
        2_500,
    )
    assert result.state.quantity == Decimal("0")
    assert result.state.cash_effect_minor == 2_500
    assert result.state.income_minor == 2_500


def test_replay_buy_row() -> None:
    result = replay_asset_transactions(
        [_buy(1, price_text="100", quantity_text="2", total_minor=20_000)]
    )

    assert result.transactions[0] == _expected(
        1,
        "buy",
        "100",
        "2",
        0,
        20_000,
        -20_000,
        20_000,
        0,
        0,
    )
    assert result.state.quantity == Decimal("2")
    assert result.state.cost_basis_minor == 20_000
    assert result.state.total_buy_cost_minor == 20_000


def test_replay_sell_row() -> None:
    result = replay_asset_transactions(
        [
            _buy(1, price_text="100", quantity_text="2", total_minor=20_000),
            _sell(2, price_text="150", quantity_text="1", total_minor=15_000),
        ]
    )

    assert result.transactions[1] == _expected(
        2,
        "sell",
        "150",
        "1",
        0,
        15_000,
        15_000,
        -10_000,
        5_000,
        0,
    )
    assert result.state.quantity == Decimal("1")
    assert result.state.cost_basis_minor == 10_000
    assert result.state.realized_pnl_minor == 5_000


def test_replay_buy_plus_partial_sell() -> None:
    result = replay_asset_transactions(
        [
            _buy(1, price_text="100", quantity_text="10", total_minor=100_000),
            _sell(2, price_text="150", quantity_text="3", total_minor=45_000),
        ]
    )

    assert result.transactions[1].position_effect_minor == -30_000
    assert result.transactions[1].realized_pnl_minor == 15_000
    assert result.state.quantity == Decimal("7")
    assert result.state.cost_basis_minor == 70_000


def test_replay_buy_plus_full_sell_leaves_zero_cost_basis() -> None:
    result = replay_asset_transactions(
        [
            _buy(1, price_text="0.005", quantity_text="2", total_minor=1),
            _sell(2, price_text="0.01", quantity_text="2", total_minor=2),
        ]
    )

    assert result.transactions[1].position_effect_minor == -1
    assert result.state.quantity == Decimal("0")
    assert result.state.cost_basis_minor == 0


def test_replay_buy_income_sell_aggregates_correctly() -> None:
    result = replay_asset_transactions(
        [
            _buy(1, price_text="100", quantity_text="10", total_minor=100_000),
            _income(2, 2_000),
            _sell(3, price_text="150", quantity_text="3", total_minor=45_000),
        ]
    )

    assert result.state.quantity == Decimal("7")
    assert result.state.cost_basis_minor == 70_000
    assert result.state.cash_effect_minor == -53_000
    assert result.state.realized_pnl_minor == 15_000
    assert result.state.income_minor == 2_000
    assert result.state.total_buy_cost_minor == 100_000


def test_replay_multiple_buys_use_moving_average_cost() -> None:
    result = replay_asset_transactions(
        [
            _buy(1, price_text="100", quantity_text="1", total_minor=10_000),
            _buy(2, price_text="200", quantity_text="1", total_minor=20_000),
            _sell(3, price_text="180", quantity_text="1", total_minor=18_000),
        ]
    )

    assert result.transactions[2].position_effect_minor == -15_000
    assert result.transactions[2].realized_pnl_minor == 3_000
    assert result.state.quantity == Decimal("1")
    assert result.state.cost_basis_minor == 15_000


def test_replay_rejects_sell_greater_than_open_quantity() -> None:
    with pytest.raises(InvalidLedgerEditError, match="exceeds open quantity"):
        replay_asset_transactions(
            [
                _buy(1, price_text="100", quantity_text="1", total_minor=10_000),
                _sell(2, price_text="100", quantity_text="2", total_minor=20_000),
            ]
        )


def test_replay_rejects_sell_with_no_open_quantity() -> None:
    with pytest.raises(InvalidLedgerEditError, match="no open quantity"):
        replay_asset_transactions(
            [_sell(1, price_text="100", quantity_text="1", total_minor=10_000)]
        )


def test_replay_rejects_invalid_transaction_type() -> None:
    with pytest.raises(InvalidLedgerEditError, match="Unknown"):
        replay_asset_transactions([_transaction(1, "split", total_minor=1)])


@pytest.mark.parametrize("field", ["price", "quantity"])
def test_replay_rejects_missing_price_or_quantity_for_buy_sell(field: str) -> None:
    price_text = None if field == "price" else "100"
    quantity_text = None if field == "quantity" else "1"

    with pytest.raises(InvalidLedgerEditError, match=f"require a {field}"):
        replay_asset_transactions(
            [
                _buy(
                    1,
                    price_text=price_text,  # type: ignore[arg-type]
                    quantity_text=quantity_text,  # type: ignore[arg-type]
                    total_minor=10_000,
                )
            ]
        )

    with pytest.raises(InvalidLedgerEditError, match=f"require a {field}"):
        replay_asset_transactions(
            [
                _buy(1, price_text="100", quantity_text="1", total_minor=10_000),
                _sell(
                    2,
                    price_text=price_text,  # type: ignore[arg-type]
                    quantity_text=quantity_text,  # type: ignore[arg-type]
                    total_minor=10_000,
                ),
            ]
        )


def test_replay_rejects_invalid_income_shape() -> None:
    with pytest.raises(InvalidLedgerEditError, match="price or quantity"):
        replay_asset_transactions(
            [
                _transaction(
                    1,
                    "income",
                    price_text="1",
                    quantity_text=None,
                    total_minor=100,
                )
            ]
        )

    with pytest.raises(InvalidLedgerEditError, match="fee"):
        replay_asset_transactions(
            [_transaction(1, "income", fee_minor=1, total_minor=1)]
        )


@pytest.mark.parametrize(
    "transaction",
    [
        _buy(1, price_text="100", quantity_text="1", fee_minor=150, total_minor=10_150),
        _sell(2, price_text="100", quantity_text="1", fee_minor=150, total_minor=9_850),
    ],
)
def test_replay_validates_exact_computed_trade_total(
    transaction: AssetReplayTransaction,
) -> None:
    transactions = (
        [_buy(1, price_text="100", quantity_text="1", total_minor=10_000), transaction]
        if transaction.transaction_type == "sell"
        else [transaction]
    )

    result = replay_asset_transactions(transactions)

    assert result.transactions[-1].total_minor == transaction.total_minor


@pytest.mark.parametrize(
    "transaction",
    [
        _buy(1, price_text="0.000533", quantity_text="0.0538", total_minor=1),
        _sell(2, price_text="0.000533", quantity_text="0.0538", total_minor=1),
    ],
)
def test_replay_accepts_stored_total_for_subcent_computed_trade_total(
    transaction: AssetReplayTransaction,
) -> None:
    transactions = (
        [_buy(1, price_text="0.000533", quantity_text="0.0538", total_minor=1)]
        + [transaction]
        if transaction.transaction_type == "sell"
        else [transaction]
    )

    result = replay_asset_transactions(transactions)

    assert result.transactions[-1].total_minor == 1


@pytest.mark.parametrize(
    "transaction",
    [
        _buy(1, price_text="100", quantity_text="1", total_minor=9_999),
        _sell(2, price_text="100", quantity_text="1", total_minor=9_999),
    ],
)
def test_replay_rejects_mismatched_stored_total_when_computed_total_is_exact(
    transaction: AssetReplayTransaction,
) -> None:
    transactions = (
        [_buy(1, price_text="100", quantity_text="1", total_minor=10_000), transaction]
        if transaction.transaction_type == "sell"
        else [transaction]
    )

    with pytest.raises(InvalidLedgerEditError, match="does not match"):
        replay_asset_transactions(transactions)


def test_replay_uses_entry_number_order_not_input_or_date_order() -> None:
    result = replay_asset_transactions(
        [
            _sell(2, price_text="150", quantity_text="1", total_minor=15_000),
            _buy(1, price_text="100", quantity_text="2", total_minor=20_000),
        ]
    )

    assert [transaction.entry_no for transaction in result.transactions] == [1, 2]
    assert result.state.quantity == Decimal("1")


def test_replay_rejects_invalid_money_and_quantity_values() -> None:
    with pytest.raises(InvalidLedgerEditError, match="fee"):
        replay_asset_transactions(
            [_buy(1, price_text="100", quantity_text="1", fee_minor=-1, total_minor=1)]
        )

    with pytest.raises(InvalidLedgerEditError, match="total"):
        replay_asset_transactions(
            [_buy(1, price_text="100", quantity_text="1", total_minor=0)]
        )

    with pytest.raises(InvalidLedgerEditError, match="Quantity"):
        replay_asset_transactions(
            [_buy(1, price_text="100", quantity_text="0", total_minor=1)]
        )


def test_asset_replay_module_contains_no_float_arithmetic() -> None:
    project_root = Path(__file__).parents[1]
    tree = ast.parse(
        (project_root / "src/mpal/asset_replay.py").read_text(encoding="utf-8")
    )
    float_literals = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
    float_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "float"
    ]
    assert not float_literals
    assert not float_calls


def _expected(
    entry_no: int,
    transaction_type: str,
    price_text: str | None,
    quantity_text: str | None,
    fee_minor: int,
    total_minor: int,
    cash_effect_minor: int,
    position_effect_minor: int,
    realized_pnl_minor: int,
    income_minor: int,
):
    from mpal.asset_replay import ReplayedAssetTransaction

    return ReplayedAssetTransaction(
        entry_no=entry_no,
        transaction_type=transaction_type,
        price_text=price_text,
        quantity_text=quantity_text,
        fee_minor=fee_minor,
        total_minor=total_minor,
        cash_effect_minor=cash_effect_minor,
        position_effect_minor=position_effect_minor,
        realized_pnl_minor=realized_pnl_minor,
        income_minor=income_minor,
    )
