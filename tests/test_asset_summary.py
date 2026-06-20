"""CLI tests for active asset accounting summaries."""

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fundlog.cli import app

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    *,
    portfolio: str = "stocks",
    symbols: tuple[str, ...] = ("AAPL",),
) -> Path:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["create", portfolio]).exit_code == 0
    assert runner.invoke(app, ["asset", "add", portfolio, *symbols]).exit_code == 0
    return data_dir / "fundlog.db"


def _buy(
    reference: str,
    *,
    price: str,
    quantity: str,
    total: str | None = None,
) -> None:
    arguments = [
        "buy",
        reference,
        "--price",
        price,
        "--quantity",
        quantity,
    ]
    if total is not None:
        arguments.extend(["--total", total])
    assert runner.invoke(app, arguments).exit_code == 0


def _sell(reference: str, *, price: str, quantity: str) -> None:
    result = runner.invoke(
        app,
        ["sell", reference, "--price", price, "--quantity", quantity],
    )
    assert result.exit_code == 0


def test_asset_summary_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "reference",
    ["/AAPL", "stocks/", "stocks/AAPL/extra"],
)
def test_asset_summary_rejects_invalid_asset_reference(
    tmp_path: Path,
    monkeypatch,
    reference: str,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, ["asset", "summary", reference])

    assert result.exit_code == 1
    assert "Invalid asset reference" in result.output
    assert "Traceback" not in result.output


def test_portfolio_asset_summary_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))

    result = runner.invoke(app, ["asset", "summary", "stocks"])

    assert result.exit_code == 1
    assert "Run 'fundlog init' first." in result.output
    assert not (data_dir / "fundlog.db").exists()


def test_portfolio_asset_summary_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "summary", "stocks"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_portfolio_asset_summary_shows_empty_message(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["asset", "summary", "stocks"])

    assert result.exit_code == 0
    assert "No active assets for portfolio 'stocks'." in result.output


def test_portfolio_asset_summary_shows_all_aggregates_in_symbol_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, symbols=("MSFT", "AAPL"))
    _buy("stocks/AAPL", price="100", quantity="10")
    _sell("stocks/AAPL", price="150", quantity="3")
    runner.invoke(app, ["income", "stocks/AAPL", "20"])
    _buy("stocks/MSFT", price="50", quantity="4")
    _sell("stocks/MSFT", price="80", quantity="1")
    runner.invoke(app, ["income", "stocks/MSFT", "10"])

    result = runner.invoke(app, ["asset", "summary", "stocks"])

    assert result.exit_code == 0
    for column in (
        "Asset",
        "Quantity",
        "Cost Basis",
        "Average Cost",
        "Realized PnL",
        "Income",
        "Realized Return",
    ):
        assert column in result.output
    assert result.output.index("AAPL") < result.output.index("MSFT")
    aapl_row = next(line for line in result.output.splitlines() if "AAPL" in line)
    msft_row = next(line for line in result.output.splitlines() if "MSFT" in line)
    assert " 7 " in aapl_row
    assert "700.00" in aapl_row
    assert " 100 " in aapl_row
    assert "+150.00" in aapl_row
    assert "20.00" in aapl_row
    assert "+17.00%" in aapl_row
    assert " 3 " in msft_row
    assert "150.00" in msft_row
    assert " 50 " in msft_row
    assert "+30.00" in msft_row
    assert "10.00" in msft_row
    assert "+20.00%" in msft_row
    assert " ID " not in result.output.upper()


def test_portfolio_asset_summary_excludes_deleted_assets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, symbols=("AAPL", "MSFT"))
    _buy("stocks/AAPL", price="100", quantity="1")
    _buy("stocks/MSFT", price="50", quantity="1")
    runner.invoke(app, ["asset", "delete", "stocks/AAPL", "--yes"])

    result = runner.invoke(app, ["asset", "summary", "stocks"])

    assert result.exit_code == 0
    assert "AAPL" not in result.output
    assert "MSFT" in result.output


def test_asset_list_is_hidden_compatibility_alias(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch, symbols=("AAPL", "MSFT"))
    _buy("stocks/AAPL", price="100", quantity="1")

    official = runner.invoke(app, ["asset", "summary", "stocks"])
    alias = runner.invoke(app, ["asset", "list", "stocks"])
    help_result = runner.invoke(app, ["asset", "--help"])

    assert official.exit_code == 0
    assert alias.exit_code == 0
    assert alias.output == official.output
    assert "list" not in help_result.output


def test_asset_summary_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_asset_summary_requires_active_asset(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    runner.invoke(app, ["init"])
    runner.invoke(app, ["create", "stocks"])

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in (
        result.output
    )


def test_asset_summary_fails_for_deleted_asset(tmp_path: Path, monkeypatch) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    runner.invoke(app, ["asset", "delete", "stocks/AAPL", "--yes"])

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in (
        result.output
    )


def test_empty_asset_summary_has_documented_columns_and_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = runner.invoke(app, ["asset", "summary", "stocks/aapl"])

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

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "1,000.00" in line)
    assert " 10 " in row
    assert " 100 " in row
    assert row.count("0.00") >= 2
    assert "0.00%" in row


def test_income_without_buy_cost_keeps_zero_realized_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    assert runner.invoke(app, ["income", "stocks/AAPL", "25"]).exit_code == 0

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 0
    assert "25.00" in result.output
    assert "0.00%" in result.output


def test_buy_plus_income_uses_total_buy_cost_for_realized_return(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")
    assert runner.invoke(app, ["income", "stocks/AAPL", "50"]).exit_code == 0

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

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

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 0
    row = next(line for line in result.output.splitlines() if "700.00" in line)
    assert " 7 " in row
    assert " 100 " in row
    assert "150.00" in row
    assert "15.00%" in row


def test_partial_sell_return_includes_income(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy("stocks/AAPL", price="100", quantity="10")
    _sell("stocks/AAPL", price="150", quantity="3")
    assert runner.invoke(app, ["income", "stocks/AAPL", "50"]).exit_code == 0

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

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

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

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

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

    assert result.exit_code == 0
    assert "3.333333333333333333" in result.output
    assert "10.00" in result.output


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

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

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

    result = runner.invoke(app, ["asset", "summary", "stocks/AAPL"])

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
    before = runner.invoke(app, ["asset", "summary", "stocks/MSFT"])

    assert (
        runner.invoke(
            app,
            ["asset", "delete", "stocks/AAPL", "--yes"],
        ).exit_code
        == 0
    )
    after = runner.invoke(app, ["asset", "summary", "stocks/MSFT"])

    assert before.exit_code == 0
    assert after.exit_code == 0
    assert after.output == before.output
