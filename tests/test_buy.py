"""CLI and accounting tests for manual asset buys."""

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    portfolio: str = "stocks",
    symbol: str = "AAPL",
    *,
    initial: str | None = None,
) -> Path:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    create_args = ["portfolio", "create", portfolio]
    if initial is not None:
        create_args.extend(["--initial", initial])
    assert runner.invoke(app, create_args).exit_code == 0
    assert runner.invoke(app, ["asset", "add", symbol, "-p", portfolio]).exit_code == 0
    return data_dir / "fundlog.db"


def _buy_args(
    reference: str = "stocks/AAPL",
    price: str = "234.43",
    quantity: str = "3",
) -> list[str]:
    portfolio, symbol = reference.split("/", maxsplit=1)
    return [
        "asset",
        "buy",
        symbol,
        "-p",
        portfolio,
        "--price",
        price,
        "--quantity",
        quantity,
    ]


def test_buy_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, _buy_args())

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "symbol",
    ["/AAPL", "AAPL/", "AAPL/extra"],
)
def test_buy_rejects_invalid_symbol(
    tmp_path: Path,
    monkeypatch,
    symbol: str,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "asset",
            "buy",
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


def test_buy_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, _buy_args())

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_buy_requires_active_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["portfolio", "create", "stocks"])

    result = runner.invoke(app, _buy_args())

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in (
        result.output
    )


@pytest.mark.parametrize(
    "price",
    ["invalid", "0", "-1", "1e3", "1.1234567890123456789"],
)
def test_buy_rejects_invalid_price(
    tmp_path: Path,
    monkeypatch,
    price: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, _buy_args(price=price))

    assert result.exit_code == 1
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


@pytest.mark.parametrize(
    "quantity",
    ["invalid", "0", "-1", "1e3", "1.1234567890123456789"],
)
def test_buy_rejects_invalid_quantity(
    tmp_path: Path,
    monkeypatch,
    quantity: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, _buy_args(quantity=quantity))

    assert result.exit_code == 1
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


@pytest.mark.parametrize(
    ("fee", "message"),
    [
        ("invalid", "Invalid amount: 'invalid'."),
        ("-1", "Amount must be nonnegative."),
        ("1.001", "Amount cannot have more than 2 decimal places."),
    ],
)
def test_buy_rejects_invalid_fee(
    tmp_path: Path,
    monkeypatch,
    fee: str,
    message: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, [*_buy_args(), "--fee", fee])

    assert result.exit_code == 1
    assert message in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


@pytest.mark.parametrize(
    ("total", "message"),
    [
        ("invalid", "Invalid amount: 'invalid'."),
        ("0", "Amount must be greater than zero."),
        ("-1", "Amount must be greater than zero."),
        ("1.001", "Amount cannot have more than 2 decimal places."),
    ],
)
def test_buy_rejects_invalid_total(
    tmp_path: Path,
    monkeypatch,
    total: str,
    message: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, [*_buy_args(), "--total", total])

    assert result.exit_code == 1
    assert message in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


def test_buy_rejects_future_date(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    future_date = (date.today() + timedelta(days=1)).isoformat()

    result = runner.invoke(app, [*_buy_args(), "--date", future_date])

    assert result.exit_code == 1
    assert "Date cannot be in the future." in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


def test_buy_creates_expected_transaction_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            *_buy_args(reference="stocks/aapl", price="234.4300", quantity="3.000"),
            "--fee",
            "2.30",
            "--date",
            "2026-06-20",
            "--note",
            "Initial buy",
        ],
    )

    assert result.exit_code == 0
    assert "Buy recorded for asset 'AAPL' in portfolio 'stocks'." in result.output
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
            """
        ).fetchone()

    assert transaction == (
        1,
        "buy",
        "2026-06-20",
        "234.43",
        "3",
        230,
        70_559,
        -70_559,
        70_559,
        0,
        0,
        "Initial buy",
    )


def test_buy_defaults_fee_to_zero_and_date_to_today(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, _buy_args())

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT fee_minor, total_minor, transaction_date
            FROM asset_transactions
            """
        ).fetchone()
    assert row == (0, 70_329, date.today().isoformat())


def test_buy_accepts_explicit_zero_fee(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, [*_buy_args(), "--fee", "0"])

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        fee_minor = connection.execute(
            "SELECT fee_minor FROM asset_transactions"
        ).fetchone()[0]
    assert fee_minor == 0


def test_buy_uses_next_asset_local_number_after_income(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "income", "AAPL", "10", "-p", "stocks"])

    result = runner.invoke(app, _buy_args())

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT entry_no, transaction_type
            FROM asset_transactions
            ORDER BY entry_no
            """
        ).fetchall()
    assert rows == [(1, "income"), (2, "buy")]


def test_buy_without_total_rejects_subcent_cash_effect(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        _buy_args(price="0.000533", quantity="0.0538"),
    )

    assert result.exit_code == 1
    assert "not exactly representable in minor units" in result.output
    assert "Provide --total" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


def test_buy_with_total_accepts_subcent_computed_amount(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            *_buy_args(price="0.000533", quantity="0.0538"),
            "--total",
            "0.01",
        ],
    )

    assert result.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT price_text, quantity_text, total_minor,
                   cash_effect_minor, position_effect_minor
            FROM asset_transactions
            """
        ).fetchone()
    assert row == ("0.000533", "0.0538", 1, -1, 1)


def test_buy_with_total_rejects_exact_computed_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, [*_buy_args(), "--total", "703.30"])

    assert result.exit_code == 1
    assert "does not match price × quantity + fee" in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


def test_buy_appears_in_asset_log_with_formatted_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(
        app,
        [
            *_buy_args(price="123456.0543", quantity="3.5000"),
            "--fee",
            "1.25",
            "--total",
            "432096.19",
            "--note",
            "Large buy",
        ],
    )

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "Large buy" in line)
    assert "buy" in row
    assert "123,456.0543" in row
    assert "3.5" in row
    assert "1.25" in row
    assert "432,096.19" in row


def test_asset_list_aggregates_buys_and_income(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, _buy_args(price="100", quantity="2"))
    runner.invoke(app, _buy_args(price="50", quantity="1"))
    runner.invoke(app, ["asset", "income", "AAPL", "25", "-p", "stocks"])

    result = runner.invoke(app, ["asset", "summary", "-p", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "AAPL" in line)
    assert " 3 " in row
    assert "250.00" in row
    assert "25.00" in row
    assert "10.00%" in row


def test_asset_list_realized_pnl_remains_zero_after_buy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, _buy_args(price="100", quantity="1"))

    result = runner.invoke(app, ["asset", "summary", "-p", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "AAPL" in line)
    assert row.count("0.00") >= 2


def test_portfolio_summary_applies_buy_cash_and_position_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, _buy_args(price="100", quantity="3"))

    result = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "stocks" in line)
    assert row.count("1,000.00") == 2
    assert "700.00" in row
    assert "300.00" in row
    assert "0.00%" in row


def test_buy_does_not_change_income_or_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"])
    runner.invoke(app, _buy_args(price="100", quantity="3"))

    result = runner.invoke(app, ["portfolio", "show", "stocks"])

    row = next(line for line in result.output.splitlines() if "stocks" in line)
    assert "720.00" in row
    assert "300.00" in row
    assert "1,020.00" in row
    assert "20.00" in row
    assert "2.00%" in row


def test_summary_all_includes_buy_effects_per_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["portfolio", "create", "crypto", "--initial", "500"])
    runner.invoke(app, ["asset", "add", "BTC", "-p", "crypto"])
    runner.invoke(app, _buy_args(price="100", quantity="3"))
    runner.invoke(
        app,
        _buy_args(reference="crypto/BTC", price="50", quantity="2"),
    )

    result = runner.invoke(app, ["portfolio", "list"])

    assert result.exit_code == 0
    crypto_row = next(line for line in result.output.splitlines() if "crypto" in line)
    stocks_row = next(line for line in result.output.splitlines() if "stocks" in line)
    assert "400.00" in crypto_row
    assert "100.00" in crypto_row
    assert "700.00" in stocks_row
    assert "300.00" in stocks_row


def test_asset_delete_removes_buy_effects_from_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, _buy_args(price="100", quantity="3"))

    runner.invoke(app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"])
    summary_result = runner.invoke(app, ["portfolio", "show", "stocks"])

    row = next(line for line in summary_result.output.splitlines() if "stocks" in line)
    assert row.count("1,000.00") == 3
    assert "300.00" not in row
    with sqlite3.connect(database_path) as connection:
        deleted_at = connection.execute(
            "SELECT deleted_at FROM asset_transactions"
        ).fetchone()[0]
    assert deleted_at is not None


def test_deleting_one_asset_preserves_other_asset_buy_effects(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["asset", "add", "MSFT", "-p", "stocks"])
    runner.invoke(app, _buy_args(price="100", quantity="3"))
    runner.invoke(
        app,
        _buy_args(reference="stocks/MSFT", price="50", quantity="2"),
    )

    runner.invoke(app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"])
    summary_result = runner.invoke(app, ["portfolio", "show", "stocks"])
    list_result = runner.invoke(app, ["asset", "summary", "-p", "stocks"])

    summary_row = next(
        line for line in summary_result.output.splitlines() if "stocks" in line
    )
    assert "900.00" in summary_row
    assert "100.00" in summary_row
    assert "AAPL" not in list_result.output
    assert "MSFT" in list_result.output
