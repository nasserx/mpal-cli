"""CLI and accounting tests for manual asset sells."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    portfolio: str = "stocks",
    symbol: str = "AAPL",
    *,
    initial: str | None = None,
) -> Path:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    create_args = ["portfolio", "create", portfolio]
    if initial is not None:
        create_args.extend(["--initial", initial])
    assert runner.invoke(app, create_args).exit_code == 0
    assert runner.invoke(app, ["asset", "add", symbol, "-p", portfolio]).exit_code == 0
    return data_dir / "mpal.db"


def _buy(
    reference: str = "stocks/AAPL",
    price: str = "100",
    quantity: str = "3",
    *extra: str,
) -> None:
    portfolio, symbol = reference.split("/", maxsplit=1)
    result = runner.invoke(
        app,
        [
            "asset",
            "buy",
            symbol,
            "-p",
            portfolio,
            "--price",
            price,
            "--quantity",
            quantity,
            *extra,
        ],
    )
    assert result.exit_code == 0, result.output


def _sell_args(
    reference: str = "stocks/AAPL",
    price: str = "110",
    quantity: str = "1",
) -> list[str]:
    portfolio, symbol = reference.split("/", maxsplit=1)
    return [
        "asset",
        "sell",
        symbol,
        "-p",
        portfolio,
        "--price",
        price,
        "--quantity",
        quantity,
    ]


def test_sell_requires_initialized_database(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))

    result = runner.invoke(app, _sell_args())

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "symbol",
    ["/AAPL", "AAPL/", "AAPL/extra"],
)
def test_sell_rejects_invalid_symbol(
    tmp_path: Path,
    monkeypatch,
    symbol: str,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "asset",
            "sell",
            symbol,
            "-p",
            "stocks",
            "--price",
            "100",
            "--quantity",
            "1",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid symbol" in result.output


def test_sell_requires_active_portfolio(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, _sell_args())

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_sell_requires_active_asset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["portfolio", "create", "stocks"])

    result = runner.invoke(app, _sell_args())

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in result.output


@pytest.mark.parametrize(
    "price",
    ["invalid", "0", "-1", "1e3", "1.1234567890123456789"],
)
def test_sell_rejects_invalid_price(
    tmp_path: Path,
    monkeypatch,
    price: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(app, _sell_args(price=price))

    assert result.exit_code == 1
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


@pytest.mark.parametrize(
    "quantity",
    ["invalid", "0", "-1", "1e3", "1.1234567890123456789"],
)
def test_sell_rejects_invalid_quantity(
    tmp_path: Path,
    monkeypatch,
    quantity: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(app, _sell_args(quantity=quantity))

    assert result.exit_code == 1
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("--fee", "invalid", "Invalid amount: 'invalid'."),
        ("--fee", "-1", "Amount must be nonnegative."),
        ("--fee", "1.001", "Amount cannot have more than 2 decimal places."),
        ("--total", "invalid", "Invalid amount: 'invalid'."),
        ("--total", "0", "Amount must be greater than zero."),
        ("--total", "-1", "Amount must be greater than zero."),
        ("--total", "1.001", "Amount cannot have more than 2 decimal places."),
    ],
)
def test_sell_rejects_invalid_money_options(
    tmp_path: Path,
    monkeypatch,
    option: str,
    value: str,
    message: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(app, [*_sell_args(), option, value])

    assert result.exit_code == 1
    assert message in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


def test_sell_rejects_future_date(tmp_path: Path, monkeypatch) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()
    future_date = (date.today() + timedelta(days=1)).isoformat()

    result = runner.invoke(app, [*_sell_args(), "--date", future_date])

    assert result.exit_code == 1
    assert "Date cannot be in the future." in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


def test_sell_rejects_no_open_quantity(tmp_path: Path, monkeypatch) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, _sell_args())

    assert result.exit_code == 1
    assert "has no open quantity to sell" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


def test_sell_rejects_quantity_above_open_quantity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2")

    result = runner.invoke(app, _sell_args(quantity="3"))

    assert result.exit_code == 1
    assert "exceeds open quantity" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


def test_sell_creates_expected_transaction_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="3")

    result = runner.invoke(
        app,
        [
            *_sell_args(
                reference="stocks/aapl",
                price="110.5000",
                quantity="1.000",
            ),
            "--fee",
            "2.30",
            "--date",
            "2026-06-20",
            "--note",
            "Partial sell",
        ],
    )

    assert result.exit_code == 0
    assert "Sell recorded for asset 'AAPL' in portfolio 'stocks'." in result.output
    with sqlite3.connect(database_path) as connection:
        transaction = connection.execute(
            """
            SELECT
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
            FROM asset_transactions
            WHERE transaction_type = 'sell'
            """
        ).fetchone()

    assert transaction == (
        2,
        "sell",
        "2026-06-20",
        "110.5",
        "1",
        230,
        10_820,
        10_820,
        -10_000,
        820,
        0,
        "Partial sell",
    )


def test_sell_defaults_fee_to_zero_and_date_to_today(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(app, _sell_args())

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT fee_minor, total_minor, transaction_date
            FROM asset_transactions
            WHERE transaction_type = 'sell'
            """
        ).fetchone()
    assert row == (0, 11_000, date.today().isoformat())


def test_sell_uses_shared_asset_local_number_sequence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "income", "AAPL", "10", "-p", "stocks"])
    _buy()

    result = runner.invoke(app, _sell_args())

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT entry_no, transaction_type
            FROM asset_transactions
            ORDER BY entry_no
            """
        ).fetchall()
    assert rows == [(1, "income"), (2, "buy"), (3, "sell")]


def test_sell_without_total_rejects_subcent_cash_effect(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", "0.000533", "0.0538", "--total", "0.01")

    result = runner.invoke(
        app,
        _sell_args(price="0.000533", quantity="0.0538"),
    )

    assert result.exit_code == 1
    assert "not exactly representable in minor units" in result.output
    assert "Provide --total" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


def test_sell_with_total_accepts_subcent_computed_amount(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", "0.000533", "0.0538", "--total", "0.01")

    result = runner.invoke(
        app,
        [
            *_sell_args(price="0.000533", quantity="0.0538"),
            "--total",
            "0.01",
        ],
    )

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT total_minor, cash_effect_minor, position_effect_minor,
                   realized_pnl_minor
            FROM asset_transactions
            WHERE transaction_type = 'sell'
            """
        ).fetchone()
    assert row == (1, 1, -1, 0)


def test_sell_with_total_rejects_exact_computed_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy()

    result = runner.invoke(app, [*_sell_args(), "--total", "109.99"])

    assert result.exit_code == 1
    assert "does not match price × quantity - fee" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 1


def test_partial_sell_uses_moving_average_cost_basis(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")
    _buy(price="200", quantity="1")

    result = runner.invoke(app, _sell_args(price="180", quantity="1"))

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        sell = connection.execute(
            """
            SELECT position_effect_minor, realized_pnl_minor
            FROM asset_transactions
            WHERE transaction_type = 'sell'
            """
        ).fetchone()
        remaining_basis = connection.execute(
            """
            SELECT SUM(position_effect_minor)
            FROM asset_transactions
            WHERE deleted_at IS NULL
            """
        ).fetchone()[0]
    assert sell == (-15_000, 3_000)
    assert remaining_basis == 15_000


def test_full_sell_relieves_all_remaining_cost_basis(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", "0.005", "2", "--total", "0.01")
    assert (
        runner.invoke(
            app,
            _sell_args(price="0.01", quantity="1"),
        ).exit_code
        == 0
    )

    result = runner.invoke(app, _sell_args(price="0.01", quantity="1"))

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT position_effect_minor
            FROM asset_transactions
            WHERE transaction_type = 'sell'
            ORDER BY entry_no
            """
        ).fetchall()
        totals = connection.execute(
            """
            SELECT SUM(position_effect_minor),
                   SUM(CASE transaction_type
                           WHEN 'buy' THEN CAST(quantity_text AS NUMERIC)
                           WHEN 'sell' THEN -CAST(quantity_text AS NUMERIC)
                       END)
            FROM asset_transactions
            """
        ).fetchone()
    assert rows == [(0,), (-1,)]
    assert totals == (0, 0)


def test_partial_sell_uses_half_even_minor_unit_allocation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", "0.005", "2", "--total", "0.01")

    result = runner.invoke(app, _sell_args(price="0.01", quantity="1"))

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        sell = connection.execute(
            """
            SELECT position_effect_minor, realized_pnl_minor
            FROM asset_transactions
            WHERE transaction_type = 'sell'
            """
        ).fetchone()
        remaining_basis = connection.execute(
            "SELECT SUM(position_effect_minor) FROM asset_transactions"
        ).fetchone()[0]
    assert sell == (0, 1)
    assert remaining_basis == 1


def test_partial_sell_half_even_rounds_odd_tie_to_even(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(price="0.015", quantity="2")

    result = runner.invoke(app, _sell_args(price="0.01", quantity="1"))

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        sell = connection.execute(
            """
            SELECT position_effect_minor, realized_pnl_minor
            FROM asset_transactions
            WHERE transaction_type = 'sell'
            """
        ).fetchone()
        remaining_basis = connection.execute(
            "SELECT SUM(position_effect_minor) FROM asset_transactions"
        ).fetchone()[0]
    assert sell == (-2, -1)
    assert remaining_basis == 1


def test_sell_appears_in_asset_log_with_formatted_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", "123456.0543", "3.5", "--total", "432096.19")
    result = runner.invoke(
        app,
        [
            *_sell_args(price="123456.0543", quantity="1.5000"),
            "--fee",
            "1.25",
            "--total",
            "185183.96",
            "--note",
            "Large sell",
        ],
    )
    assert result.exit_code == 0

    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    row = next(line for line in log_result.output.splitlines() if "Large sell" in line)
    assert "sell" in row
    assert "123,456.0543" in row
    assert "1.5" in row
    assert "1.25" in row
    assert "185,183.96" in row


def test_asset_list_aggregates_sell_results_and_income(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="2")
    runner.invoke(app, ["asset", "income", "AAPL", "10", "-p", "stocks"])
    runner.invoke(app, _sell_args(price="150", quantity="1"))

    result = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    row = next(line for line in result.output.splitlines() if "AAPL" in line)
    assert " 1 " in row
    assert "100.00" in row
    assert "50.00" in row
    assert "10.00" in row
    assert "30.00%" in row


def test_portfolio_summary_applies_sell_accounting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    _buy(price="100", quantity="3")
    runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"])

    result = runner.invoke(app, _sell_args(price="150", quantity="1"))
    assert result.exit_code == 0
    summary = runner.invoke(app, ["summary", "-p", "stocks"])

    row = next(line for line in summary.output.splitlines() if "stocks" in line)
    assert "870.00" in row
    assert "200.00" in row
    assert "1,070.00" in row
    assert "50.00" in row
    assert "20.00" in row
    assert "7.00%" in row


def test_summary_all_includes_sell_effects_per_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["portfolio", "create", "crypto", "--initial", "500"])
    runner.invoke(app, ["asset", "add", "BTC", "-p", "crypto"])
    _buy(price="100", quantity="2")
    _buy(reference="crypto/BTC", price="50", quantity="2")
    runner.invoke(app, _sell_args(price="150", quantity="1"))
    runner.invoke(
        app,
        _sell_args(reference="crypto/BTC", price="75", quantity="1"),
    )

    result = runner.invoke(app, ["portfolio", "list"])

    crypto_row = next(line for line in result.output.splitlines() if "crypto" in line)
    stocks_row = next(line for line in result.output.splitlines() if "stocks" in line)
    assert "475.00" in crypto_row
    assert "50.00" in crypto_row
    assert "25.00" in crypto_row
    assert "950.00" in stocks_row
    assert "100.00" in stocks_row
    assert "50.00" in stocks_row


def test_asset_delete_removes_sell_effects_from_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch, initial="1000")
    _buy(price="100", quantity="2")
    runner.invoke(app, _sell_args(price="150", quantity="1"))

    runner.invoke(app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"])
    summary = runner.invoke(app, ["summary", "-p", "stocks"])

    row = next(line for line in summary.output.splitlines() if "stocks" in line)
    assert row.count("1,000.00") == 3
    assert "50.00" not in row
    with sqlite3.connect(database_path) as connection:
        active_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM asset_transactions
            WHERE deleted_at IS NULL
            """
        ).fetchone()[0]
    assert active_count == 0


def test_deleting_one_asset_preserves_other_asset_sell_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["asset", "add", "MSFT", "-p", "stocks"])
    _buy(price="100", quantity="2")
    _buy(reference="stocks/MSFT", price="50", quantity="2")
    runner.invoke(app, _sell_args(price="150", quantity="1"))
    runner.invoke(
        app,
        _sell_args(reference="stocks/MSFT", price="75", quantity="1"),
    )

    runner.invoke(app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"])
    summary = runner.invoke(app, ["summary", "-p", "stocks"])
    assets = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    row = next(line for line in summary.output.splitlines() if "stocks" in line)
    assert "975.00" in row
    assert "50.00" in row
    assert "25.00" in row
    assert "AAPL" not in assets.output
    assert "MSFT" in assets.output
