"""CLI tests for active asset accounting summaries."""

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    *,
    portfolio: str = "stocks",
    symbols: tuple[str, ...] = ("AAPL",),
) -> Path:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["portfolio", "create", portfolio]).exit_code == 0
    assert (
        runner.invoke(app, ["asset", "add", *symbols, "-p", portfolio]).exit_code == 0
    )
    return data_dir / "mpal.db"


def _buy(
    reference: str,
    *,
    price: str,
    quantity: str,
    total: str | None = None,
) -> None:
    portfolio, symbol = reference.split("/", maxsplit=1)
    arguments = [
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
    if total is not None:
        arguments.extend(["--total", total])
    assert runner.invoke(app, arguments).exit_code == 0


def _sell(reference: str, *, price: str, quantity: str) -> None:
    portfolio, symbol = reference.split("/", maxsplit=1)
    result = runner.invoke(
        app,
        [
            "asset",
            "sell",
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


def test_asset_summary_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "symbol",
    ["/AAPL", "AAPL/", "AAPL/extra"],
)
def test_asset_summary_rejects_invalid_symbol(
    tmp_path: Path,
    monkeypatch,
    symbol: str,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", symbol])

    assert result.exit_code == 1
    assert "Invalid symbol" in result.output
    assert "Traceback" not in result.output


def test_portfolio_asset_summary_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert not (data_dir / "mpal.db").exists()


def test_portfolio_asset_summary_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_portfolio_asset_summary_shows_empty_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["portfolio", "create", "stocks"])

    result = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    assert result.exit_code == 0
    assert "No active assets for portfolio 'stocks'." in result.output


def test_portfolio_asset_summary_shows_all_aggregates_in_symbol_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, symbols=("MSFT", "AAPL"))
    _buy("stocks/AAPL", price="100", quantity="10")
    _sell("stocks/AAPL", price="150", quantity="3")
    runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"])
    _buy("stocks/MSFT", price="50", quantity="4")
    _sell("stocks/MSFT", price="80", quantity="1")
    runner.invoke(app, ["asset", "income", "MSFT", "10", "-p", "stocks"])

    result = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    assert result.exit_code == 0
    for column in (
        "Asset/Portfolio",
        "Quantity",
        "Cost Basis",
        "Average Cost",
        "Realized PnL",
        "Income",
        "Realized Return",
    ):
        assert column in result.output
    assert "Asset • Portfolio" not in result.output
    assert "A/P" not in result.output
    assert "A • P" not in result.output
    assert result.output.index("AAPL") < result.output.index("MSFT")
    aapl_row = next(line for line in result.output.splitlines() if "AAPL" in line)
    msft_row = next(line for line in result.output.splitlines() if "MSFT" in line)
    assert "AAPL • Stocks" in aapl_row
    assert "MSFT • Stocks" in msft_row
    assert "AAPL/stocks" not in result.output
    assert "MSFT/stocks" not in result.output
    assert " 7 " in aapl_row
    assert "700.00" in aapl_row
    assert "100.00" in aapl_row
    assert "+150.00" in aapl_row
    assert "20.00" in aapl_row
    assert "+17.00%" in aapl_row
    assert " 3 " in msft_row
    assert "150.00" in msft_row
    assert "50.00" in msft_row
    assert "+30.00" in msft_row
    assert "10.00" in msft_row
    assert "+20.00%" in msft_row
    assert " ID " not in result.output.upper()


def test_portfolio_asset_summary_capitalizes_portfolio_label_for_display_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, portfolio="etfs", symbols=("ETHA",))

    result = runner.invoke(app, ["asset", "list", "-p", "etfs"])

    assert result.exit_code == 0
    assert "Asset/Portfolio" in result.output
    assert "Asset • Portfolio" not in result.output
    assert "ETHA • Etfs" in result.output
    assert "ETHA/etfs" not in result.output


def test_portfolio_asset_summary_excludes_deleted_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, symbols=("AAPL", "MSFT"))
    _buy("stocks/AAPL", price="100", quantity="1")
    _buy("stocks/MSFT", price="50", quantity="1")
    runner.invoke(app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"])

    result = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    assert result.exit_code == 0
    assert "AAPL" not in result.output
    assert "MSFT" in result.output


def test_asset_summary_is_removed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, symbols=("AAPL", "MSFT"))
    _buy("stocks/AAPL", price="100", quantity="1")

    official = runner.invoke(app, ["asset", "list", "-p", "stocks"])
    removed = runner.invoke(app, ["asset", "summary", "-p", "stocks"])
    help_result = runner.invoke(app, ["asset", "--help"])

    assert official.exit_code == 0
    assert removed.exit_code == 2
    assert "No such command 'summary'" in removed.output
    assert "summary" not in help_result.output
    assert "list" in help_result.output
    assert "show" not in help_result.output


def test_global_asset_list_shows_assets_across_active_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, portfolio="stocks", symbols=("AAPL",))
    assert runner.invoke(app, ["portfolio", "create", "etfs"]).exit_code == 0
    assert runner.invoke(app, ["asset", "add", "ETHA", "-p", "etfs"]).exit_code == 0
    assert runner.invoke(app, ["asset", "add", "AAPL", "-p", "etfs"]).exit_code == 0
    _buy("stocks/AAPL", price="100", quantity="3")
    _buy("etfs/AAPL", price="50", quantity="2")
    _buy("etfs/ETHA", price="25", quantity="4")

    result = runner.invoke(app, ["asset", "list"])

    assert result.exit_code == 0
    assert "Asset/Portfolio" in result.output
    assert "Asset • Portfolio" not in result.output
    assert "A/P" not in result.output
    assert "A • P" not in result.output
    assert "AAPL • Stocks" in result.output
    assert "AAPL • Etfs" in result.output
    assert "ETHA • Etfs" in result.output
    assert "AAPL/stocks" not in result.output
    assert "AAPL/etfs" not in result.output
    assert "ETHA/etfs" not in result.output
    stocks_row = next(
        line for line in result.output.splitlines() if "AAPL • Stocks" in line
    )
    etfs_row = next(
        line for line in result.output.splitlines() if "AAPL • Etfs" in line
    )
    assert " 3 " in stocks_row
    assert " 2 " in etfs_row
    assert " ID " not in result.output.upper()


def test_global_asset_list_excludes_deleted_assets_and_deleted_portfolios(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, portfolio="stocks", symbols=("AAPL",))
    assert runner.invoke(app, ["portfolio", "create", "closed"]).exit_code == 0
    assert runner.invoke(app, ["asset", "add", "MSFT", "-p", "stocks"]).exit_code == 0
    assert runner.invoke(app, ["asset", "add", "ETHA", "-p", "closed"]).exit_code == 0
    assert (
        runner.invoke(
            app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"]
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["portfolio", "delete", "closed", "--yes"]).exit_code == 0

    result = runner.invoke(app, ["asset", "list"])

    assert result.exit_code == 0
    assert "MSFT • Stocks" in result.output
    assert "MSFT/stocks" not in result.output
    assert "AAPL • Stocks" not in result.output
    assert "AAPL/stocks" not in result.output
    assert "ETHA • Closed" not in result.output
    assert "ETHA/closed" not in result.output


def test_global_asset_list_shows_empty_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "list"])

    assert result.exit_code == 0
    assert "No active assets." in result.output


def test_global_asset_list_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "list"])

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert not (data_dir / "mpal.db").exists()


def test_asset_summary_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_asset_summary_requires_active_asset(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["portfolio", "create", "stocks"])

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in (
        result.output
    )


def test_asset_summary_fails_for_deleted_asset(tmp_path: Path, monkeypatch) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "delete", "AAPL", "-p", "stocks", "--yes"])

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in (
        result.output
    )


def test_empty_asset_summary_has_documented_columns_and_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "aapl"])

    assert result.exit_code == 0
    columns = (
        "Quantity",
        "Cost Basis",
        "Average Cost",
        "Realized PnL",
        "Income",
        "Realized Return",
    )
    positions = [result.output.index(column) for column in columns]
    assert positions == sorted(positions)
    assert "AAPL/stocks" not in result.output
    assert " ID " not in result.output.upper()
    assert "--" in result.output
    assert result.output.count("0.00") >= 4
    assert "0.00%" in result.output


def test_asset_summary_after_buy_shows_open_accounting_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "1,000.00" in line)
    assert " 10 " in row
    assert "100.00" in row
    assert row.count("0.00") >= 2
    assert "0.00%" in row


def test_income_without_buy_cost_keeps_zero_realized_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    assert (
        runner.invoke(app, ["asset", "income", "AAPL", "25", "-p", "stocks"]).exit_code
        == 0
    )

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "25.00" in result.output
    assert "0.00%" in result.output


def test_buy_plus_income_uses_total_buy_cost_for_realized_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")
    assert (
        runner.invoke(app, ["asset", "income", "AAPL", "50", "-p", "stocks"]).exit_code
        == 0
    )

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "50.00" in result.output
    assert "5.00%" in result.output


def test_partial_sell_reduces_quantity_and_cost_basis_and_shows_pnl(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")
    _sell("stocks/AAPL", price="150", quantity="3")

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "700.00" in line)
    assert " 7 " in row
    assert "100.00" in row
    assert "150.00" in row
    assert "15.00%" in row


def test_partial_sell_return_includes_income(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")
    _sell("stocks/AAPL", price="150", quantity="3")
    assert (
        runner.invoke(app, ["asset", "income", "AAPL", "50", "-p", "stocks"]).exit_code
        == 0
    )

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "150.00" in result.output
    assert "50.00" in result.output
    assert "20.00%" in result.output


def test_full_sell_keeps_realized_results_with_no_average_cost(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")
    _sell("stocks/AAPL", price="120", quantity="10")

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "200.00" in line)
    assert " 0 " in row
    assert "0.00" in row
    assert "--" in row
    assert "20.00%" in row


def test_average_cost_uses_price_style_precision(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(
        "stocks/AAPL",
        price="0.333333",
        quantity="3",
        total="10.00",
    )

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "3.333333" in result.output
    assert "3.333333333333333333" not in result.output
    assert "10.00" in result.output


def test_average_cost_uses_inferred_two_decimal_price_scale(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="1.00", quantity="1")
    _buy("stocks/AAPL", price="1.31", quantity="2")

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "1.21" in result.output
    assert "1.206666" not in result.output


def test_tiny_average_cost_uses_inferred_price_precision(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="0.00334", quantity="1000")

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "0.00334" in result.output


def test_quantity_and_money_columns_use_distinct_formatting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(
        "stocks/AAPL",
        price="0.000001",
        quantity="123456.0543",
        total="1000.00",
    )

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "123,456.0543" in result.output
    assert "1,000.00" in result.output
    assert "123,456.05 │" not in result.output


def test_soft_deleted_transactions_are_excluded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE asset_transactions
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE transaction_type = 'buy'
            """
        )

    result = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert "1,000.00" not in result.output
    assert "--" in result.output
    assert "0.00%" in result.output


def test_deleting_one_asset_does_not_change_another_asset_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, symbols=("AAPL", "MSFT"))
    _buy("stocks/AAPL", price="100", quantity="10")
    _buy("stocks/MSFT", price="50", quantity="4")
    before = runner.invoke(app, ["summary", "-p", "stocks", "-a", "MSFT"])

    assert (
        runner.invoke(
            app,
            ["asset", "delete", "AAPL", "-p", "stocks", "--yes"],
        ).exit_code
        == 0
    )
    after = runner.invoke(app, ["summary", "-p", "stocks", "-a", "MSFT"])

    assert before.exit_code == 0
    assert after.exit_code == 0
    assert after.output == before.output
