"""Tests for portfolio allocation by book value."""

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def _init(tmp_path: Path, monkeypatch) -> Path:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    return data_dir


def _create_portfolio(name: str, initial: str | None = None) -> None:
    args = ["portfolio", "create", name]
    if initial is not None:
        args.extend(["--initial", initial])
    result = runner.invoke(app, args)
    assert result.exit_code == 0


def _buy(portfolio: str, symbol: str, *, price: str, quantity: str) -> None:
    assert runner.invoke(app, ["asset", "add", symbol, "-p", portfolio]).exit_code == 0
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
        ],
    )
    assert result.exit_code == 0


def _row(output: str, portfolio: str) -> str:
    return next(line for line in output.splitlines() if portfolio in line)


def test_portfolio_allocation_appears_in_help() -> None:
    result = runner.invoke(app, ["portfolio", "--help"])

    assert result.exit_code == 0
    assert "│ allocation " in result.output


def test_portfolio_allocation_help_explains_book_value_basis() -> None:
    result = runner.invoke(app, ["portfolio", "allocation", "--help"])

    assert result.exit_code == 0
    assert "Show active portfolio allocation by book value." in result.output
    assert "Book value is total cash plus open position book cost." in result.output
    assert "Allocation is not" in result.output
    assert "market value" in result.output
    assert "mpal does not use live prices" in result.output


def test_portfolio_allocation_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert not (data_dir / "mpal.db").exists()


def test_portfolio_allocation_empty_initialized_database_is_clean(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    assert "No active portfolios." in result.output
    assert "Traceback" not in result.output


def test_portfolio_allocation_one_positive_portfolio_is_full_allocation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    _create_portfolio("stocks", "1000")

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    for column in (
        "PORTFOLIO",
        "TOTAL CASH",
        "POSITIONS",
        "BOOK VALUE",
        "ALLOCATION",
    ):
        assert column in result.output
    row = _row(result.output, "stocks")
    assert "1,000.00" in row
    assert "0.00" in row
    assert "100.00%" in row
    assert "+100.00%" not in row


def test_portfolio_allocation_uses_book_value_not_capital_or_cash_alone(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    _create_portfolio("stocks", "1000")
    _create_portfolio("cash", "1000")
    runner.invoke(app, ["withdraw", "500", "-p", "cash"])
    _buy("stocks", "AAPL", price="200", quantity="1")

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    stocks_row = _row(result.output, "stocks")
    cash_row = _row(result.output, "cash")
    assert "800.00" in stocks_row
    assert "200.00" in stocks_row
    assert "1,000.00" in stocks_row
    assert "66.67%" in stocks_row
    assert "500.00" in cash_row
    assert "33.33%" in cash_row
    assert "50.00%" not in result.output


def test_portfolio_allocation_sorts_by_book_value_then_name(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    _create_portfolio("beta", "200")
    _create_portfolio("alpha", "200")
    _create_portfolio("large", "500")

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    row_positions = [result.output.index(name) for name in ("large", "alpha", "beta")]
    assert row_positions == sorted(row_positions)


def test_portfolio_allocation_ignores_deleted_portfolios_and_entries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    _create_portfolio("active", "1000")
    _create_portfolio("deleted", "5000")
    runner.invoke(app, ["portfolio", "delete", "deleted", "--yes"])
    runner.invoke(app, ["deposit", "250", "-p", "active"])
    runner.invoke(app, ["capital", "entry", "delete", "2", "-p", "active"])

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    assert "active" in result.output
    assert "deleted" not in result.output
    assert "5,000.00" not in result.output
    assert "1,250.00" not in result.output
    assert "1,000.00" in result.output
    assert "100.00%" in result.output


def test_portfolio_allocation_ignores_deleted_assets_and_transactions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    _create_portfolio("stocks", "1000")
    _buy("stocks", "AAPL", price="200", quantity="1")
    runner.invoke(
        app, ["asset", "entry", "delete", "AAPL", "1", "-p", "stocks", "--yes"]
    )
    _buy("stocks", "MSFT", price="50", quantity="1")
    runner.invoke(app, ["asset", "delete", "MSFT", "-p", "stocks", "--yes"])

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    row = _row(result.output, "stocks")
    assert row.count("1,000.00") == 2
    assert "200.00" not in row
    assert "50.00" not in row


def test_portfolio_allocation_zero_total_book_value_displays_zero_percent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _init(tmp_path, monkeypatch)
    _create_portfolio("empty")

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    row = _row(result.output, "empty")
    assert row.count("0.00") >= 3
    assert "0.00%" in row
    assert "+0.00%" not in row


def test_portfolio_allocation_hides_decimal_tails_and_internal_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = _init(tmp_path, monkeypatch)
    _create_portfolio("stocks", "1234.56")
    with sqlite3.connect(data_dir / "mpal.db") as connection:
        portfolio_id = connection.execute(
            "SELECT id FROM portfolios WHERE name = 'stocks'"
        ).fetchone()[0]

    result = runner.invoke(app, ["portfolio", "allocation"])

    assert result.exit_code == 0
    assert "1,234.56" in result.output
    assert "000000000000" not in result.output
    assert f" {portfolio_id} " not in result.output
