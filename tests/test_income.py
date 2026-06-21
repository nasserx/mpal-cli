"""CLI and accounting tests for manual asset income."""

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


def test_income_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "symbol",
    ["/AAPL", "AAPL/", "AAPL/extra"],
)
def test_income_rejects_invalid_symbol(
    tmp_path: Path,
    monkeypatch,
    symbol: str,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, ["asset", "income", symbol, "32", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Invalid symbol" in result.output
    assert "Traceback" not in result.output


def test_income_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_income_requires_active_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["portfolio", "create", "stocks"])

    result = runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in (
        result.output
    )


@pytest.mark.parametrize(
    ("amount", "message"),
    [
        ("invalid", "Invalid amount: 'invalid'."),
        ("0", "Amount must be greater than zero."),
        ("-1", "Amount must be greater than zero."),
        ("1.001", "Amount cannot have more than 2 decimal places."),
    ],
)
def test_income_rejects_invalid_amount(
    tmp_path: Path,
    monkeypatch,
    amount: str,
    message: str,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, ["asset", "income", "AAPL", amount, "-p", "stocks"])

    assert result.exit_code == 1
    assert message in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


def test_income_rejects_future_date(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    future_date = (date.today() + timedelta(days=1)).isoformat()

    result = runner.invoke(
        app,
        ["asset", "income", "AAPL", "32", "--date", future_date, "-p", "stocks"],
    )

    assert result.exit_code == 1
    assert "Date cannot be in the future." in result.output
    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM asset_transactions"
        ).fetchone()[0]
    assert count == 0


def test_income_creates_expected_transaction_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(
        app,
        [
            "asset",
            "income",
            "aapl",
            "32.50",
            "-p",
            "stocks",
            "--date",
            "2026-06-20",
            "--note",
            "Dividend",
        ],
    )

    assert result.exit_code == 0
    assert "Income recorded for asset 'AAPL' in portfolio 'stocks'." in result.output
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
                note,
                deleted_at
            FROM asset_transactions
            """
        ).fetchone()

    assert transaction == (
        1,
        "income",
        "2026-06-20",
        None,
        None,
        0,
        3250,
        3250,
        0,
        0,
        3250,
        "Dividend",
        None,
    )


def test_income_defaults_to_today_and_uses_next_asset_local_number(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)

    first = runner.invoke(app, ["asset", "income", "AAPL", "10", "-p", "stocks"])
    second = runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"])

    assert first.exit_code == 0
    assert second.exit_code == 0
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT entry_no, transaction_date, income_minor
            FROM asset_transactions
            ORDER BY entry_no
            """
        ).fetchall()

    assert rows == [
        (1, date.today().isoformat(), 1000),
        (2, date.today().isoformat(), 2000),
    ]


def test_income_entry_numbers_are_local_to_each_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "add", "MSFT", "-p", "stocks"])

    runner.invoke(app, ["asset", "income", "AAPL", "10", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "MSFT", "20", "-p", "stocks"])

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT a.symbol, t.entry_no
            FROM asset_transactions AS t
            JOIN assets AS a ON a.id = t.asset_id
            ORDER BY a.symbol
            """
        ).fetchall()
    assert rows == [("AAPL", 1), ("MSFT", 1)]


def test_income_appears_in_asset_log_with_placeholders_and_total(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(
        app,
        [
            "asset",
            "income",
            "AAPL",
            "1234.50",
            "-p",
            "stocks",
            "--date",
            "2026-06-20",
            "--note",
            "Dividend",
        ],
    )

    result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "Dividend" in line)
    assert "income" in row
    assert row.count("--") == 3
    assert "1,234.50" in row


def test_asset_list_sums_income_and_keeps_zero_realized_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "AAPL", "8.50", "-p", "stocks"])

    result = runner.invoke(app, ["asset", "summary", "-p", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "AAPL" in line)
    assert "40.50" in row
    assert "0.00%" in row


def test_portfolio_summary_includes_income_in_cash_book_value_and_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])

    result = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "stocks" in line)
    assert "1,000.00" in row
    assert row.count("1,032.00") == 2
    assert "32.00" in row
    assert "3.20%" in row


def test_portfolio_return_is_zero_when_capital_is_zero(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])

    result = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "stocks" in line)
    assert row.count("32.00") == 3
    assert "0.00%" in row


def test_summary_all_includes_income_per_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["portfolio", "create", "crypto", "--initial", "500"])
    runner.invoke(app, ["asset", "add", "BTC", "-p", "crypto"])
    runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "BTC", "25", "-p", "crypto"])

    result = runner.invoke(app, ["portfolio", "list"])

    assert result.exit_code == 0
    crypto_row = next(line for line in result.output.splitlines() if "crypto" in line)
    stocks_row = next(line for line in result.output.splitlines() if "stocks" in line)
    assert "525.00" in crypto_row
    assert "25.00" in crypto_row
    assert "5.00%" in crypto_row
    assert "1,020.00" in stocks_row
    assert "20.00" in stocks_row
    assert "2.00%" in stocks_row


def test_asset_delete_soft_deletes_income_transactions_and_removes_summary_effect(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])

    delete_result = runner.invoke(
        app,
        ["asset", "delete", "AAPL", "-p", "stocks", "--yes"],
    )
    summary_result = runner.invoke(app, ["portfolio", "show", "stocks"])
    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert delete_result.exit_code == 0
    assert summary_result.exit_code == 0
    row = next(line for line in summary_result.output.splitlines() if "stocks" in line)
    assert row.count("1,000.00") == 3
    assert "32.00" not in row
    assert log_result.exit_code == 1
    assert "Active asset 'AAPL' does not exist" in log_result.output
    with sqlite3.connect(database_path) as connection:
        transaction_deleted_at = connection.execute(
            "SELECT deleted_at FROM asset_transactions"
        ).fetchone()[0]
    assert transaction_deleted_at is not None


def test_deleting_one_asset_preserves_other_asset_income(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, initial="1000")
    runner.invoke(app, ["asset", "add", "MSFT", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "AAPL", "32", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "MSFT", "18", "-p", "stocks"])

    runner.invoke(app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"])
    summary_result = runner.invoke(app, ["portfolio", "show", "stocks"])
    list_result = runner.invoke(app, ["asset", "summary", "-p", "stocks"])

    summary_row = next(
        line for line in summary_result.output.splitlines() if "stocks" in line
    )
    assert "1,018.00" in summary_row
    assert "18.00" in summary_row
    assert "1.80%" in summary_row
    assert "AAPL" not in list_result.output
    assert "MSFT" in list_result.output
    assert "18.00" in list_result.output
