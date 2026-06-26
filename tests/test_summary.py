"""Tests for the global summary command."""

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def _use_temp_data_dir(tmp_path: Path, monkeypatch) -> Path:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    return data_dir


def _init(tmp_path: Path, monkeypatch) -> Path:
    data_dir = _use_temp_data_dir(tmp_path, monkeypatch)
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    return data_dir


def _record_profitable_asset(
    portfolio: str,
    symbol: str,
    *,
    buy_quantity: str,
    buy_price: str,
    sell_quantity: str,
    sell_price: str,
    income: str,
) -> None:
    assert runner.invoke(app, ["asset", "add", symbol, "-p", portfolio]).exit_code == 0
    assert (
        runner.invoke(
            app,
            [
                "asset",
                "buy",
                symbol,
                "-p",
                portfolio,
                "--price",
                buy_price,
                "--quantity",
                buy_quantity,
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "asset",
                "sell",
                symbol,
                "-p",
                portfolio,
                "--price",
                sell_price,
                "--quantity",
                sell_quantity,
            ],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["asset", "income", symbol, income, "-p", portfolio]
        ).exit_code
        == 0
    )


def test_summary_appears_in_top_level_help() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "│ summary " in result.output


def test_summary_help_describes_global_active_portfolio_summary() -> None:
    result = runner.invoke(app, ["summary", "--help"])

    assert result.exit_code == 0
    assert "Show a global summary across active portfolios." in result.output


def test_summary_requires_initialized_database(tmp_path: Path, monkeypatch) -> None:
    data_dir = _use_temp_data_dir(tmp_path, monkeypatch)

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert not (data_dir / "mpal.db").exists()


def test_summary_empty_initialized_database_shows_zero_table(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "TOTAL CAPITAL" in result.output
    assert "TOTAL INCOME" in result.output
    assert "REALIZED P&L" in result.output
    assert "RETURN" in result.output
    assert result.output.count("0.00") >= 3
    assert "0.00%" in result.output
    assert "No active portfolios." not in result.output


def test_summary_one_portfolio_totals_are_correct(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    assert (
        runner.invoke(
            app, ["portfolio", "create", "stocks", "--initial", "10000"]
        ).exit_code
        == 0
    )
    _record_profitable_asset(
        "stocks",
        "AAPL",
        buy_quantity="10",
        buy_price="100",
        sell_quantity="4",
        sell_price="200",
        income="100",
    )

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "10,000.00" in result.output
    assert "100.00" in result.output
    assert "+400.00" in result.output
    assert "+5.00%" in result.output


def test_summary_multiple_portfolios_are_aggregated_from_global_totals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    assert (
        runner.invoke(
            app, ["portfolio", "create", "stocks", "--initial", "10000"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app, ["portfolio", "create", "bonds", "--initial", "30000"]
        ).exit_code
        == 0
    )
    _record_profitable_asset(
        "stocks",
        "AAPL",
        buy_quantity="10",
        buy_price="100",
        sell_quantity="4",
        sell_price="200",
        income="100",
    )
    _record_profitable_asset(
        "bonds",
        "BND",
        buy_quantity="10",
        buy_price="100",
        sell_quantity="5",
        sell_price="270",
        income="80",
    )

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "40,000.00" in result.output
    assert "180.00" in result.output
    assert "+1,250.00" in result.output
    assert "+3.58%" in result.output


def test_summary_ignores_deleted_portfolios(tmp_path: Path, monkeypatch) -> None:
    _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "stocks", "--initial", "10000"])
    runner.invoke(app, ["portfolio", "create", "cash", "--initial", "500"])
    runner.invoke(app, ["portfolio", "delete", "stocks", "--yes"])

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "500.00" in result.output
    assert "10,000.00" not in result.output
    assert "stocks" not in result.output
    assert "cash" not in result.output


def test_summary_ignores_deleted_capital_entries_and_asset_transactions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "stocks"])
    runner.invoke(app, ["capital", "deposit", "1000", "-p", "stocks"])
    runner.invoke(app, ["capital", "deposit", "500", "-p", "stocks"])
    runner.invoke(app, ["capital", "entry", "delete", "2", "-p", "stocks"])
    runner.invoke(app, ["asset", "add", "AAPL", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "AAPL", "50", "-p", "stocks"])
    runner.invoke(
        app, ["asset", "entry", "delete", "AAPL", "1", "-p", "stocks", "--yes"]
    )

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "1,000.00" in result.output
    assert "500.00" not in result.output
    assert "50.00" not in result.output


def test_summary_total_capital_is_deposits_minus_withdrawals(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "stocks"])
    runner.invoke(app, ["capital", "deposit", "1000", "-p", "stocks"])
    runner.invoke(app, ["capital", "withdraw", "250", "-p", "stocks"])

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "750.00" in result.output
    assert "1,000.00" not in result.output


def test_summary_sums_asset_income_across_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "stocks", "--initial", "1000"])
    runner.invoke(app, ["portfolio", "create", "funds", "--initial", "1000"])
    runner.invoke(app, ["asset", "add", "AAPL", "-p", "stocks"])
    runner.invoke(app, ["asset", "add", "BND", "-p", "funds"])
    runner.invoke(app, ["asset", "income", "AAPL", "12.34", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "BND", "56.78", "-p", "funds"])

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "69.12" in result.output


def test_summary_sums_realized_sell_pnl_across_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "stocks", "--initial", "2000"])
    runner.invoke(app, ["portfolio", "create", "funds", "--initial", "2000"])
    _record_profitable_asset(
        "stocks",
        "AAPL",
        buy_quantity="10",
        buy_price="100",
        sell_quantity="1",
        sell_price="150",
        income="1",
    )
    _record_profitable_asset(
        "funds",
        "BND",
        buy_quantity="10",
        buy_price="100",
        sell_quantity="2",
        sell_price="125",
        income="1",
    )

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "+100.00" in result.output


def test_summary_return_is_not_average_of_portfolio_returns(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "small", "--initial", "100"])
    runner.invoke(app, ["portfolio", "create", "large", "--initial", "9900"])
    runner.invoke(app, ["asset", "add", "INC", "-p", "small"])
    runner.invoke(app, ["asset", "income", "INC", "100", "-p", "small"])

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "10,000.00" in result.output
    assert "100.00" in result.output
    assert "+1.00%" in result.output
    assert "+50.00%" not in result.output


def test_summary_zero_total_capital_displays_zero_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "stocks"])
    runner.invoke(app, ["asset", "add", "AAPL", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "AAPL", "10", "-p", "stocks"])

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "10.00" in result.output
    assert "0.00%" in result.output
    assert "+0.00%" not in result.output


def test_summary_headers_are_exact_uppercase(tmp_path: Path, monkeypatch) -> None:
    _init(tmp_path, monkeypatch)

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    for header in ("TOTAL CAPITAL", "TOTAL INCOME", "REALIZED P&L", "RETURN"):
        assert header in result.output
    for old_header in ("Total Capital", "Total Income", "Realized PnL"):
        assert old_header not in result.output


def test_summary_uses_existing_formatting_without_decimal_tails_or_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = _init(tmp_path, monkeypatch)
    runner.invoke(app, ["portfolio", "create", "stocks", "--initial", "1234567.89"])
    runner.invoke(app, ["asset", "add", "AAPL", "-p", "stocks"])
    runner.invoke(app, ["asset", "income", "AAPL", "1.23", "-p", "stocks"])
    with sqlite3.connect(data_dir / "mpal.db") as connection:
        portfolio_id = connection.execute(
            "SELECT id FROM portfolios WHERE name = 'stocks'"
        ).fetchone()[0]
        asset_id = connection.execute(
            "SELECT id FROM assets WHERE symbol = 'AAPL'"
        ).fetchone()[0]

    result = runner.invoke(app, ["summary"])

    assert result.exit_code == 0
    assert "1,234,567.89" in result.output
    assert "1.23" in result.output
    assert "000000000000" not in result.output
    assert "stocks" not in result.output
    assert "AAPL" not in result.output
    assert f" {portfolio_id} " not in result.output
    assert f" {asset_id} " not in result.output
