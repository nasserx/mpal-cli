"""End-to-end regression tests for asset accounting invariants."""

import ast
import sqlite3
from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

from mpal.cli import app
from mpal.storage import (
    get_all_portfolio_summaries,
    get_asset_summary,
    get_assets,
    get_portfolio_summary,
)

runner = CliRunner()


def _initialize(tmp_path: Path, monkeypatch) -> Path:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    _invoke("init")
    return data_dir / "mpal.db"


def _invoke(*arguments: str):
    result = runner.invoke(app, list(arguments))
    assert result.exit_code == 0, result.output
    return result


def _create_portfolio(name: str, initial: str) -> None:
    _invoke("portfolio", "create", name, "--initial", initial)


def _add_asset(portfolio: str, symbol: str) -> None:
    _invoke("asset", "add", symbol, "-p", portfolio)


def _buy(
    reference: str,
    *,
    price: str,
    quantity: str,
    total: str,
) -> None:
    portfolio, symbol = reference.split("/")
    _invoke(
        "asset",
        "buy",
        symbol,
        "-p",
        portfolio,
        "--price",
        price,
        "--quantity",
        quantity,
        "--total",
        total,
    )


def _sell(
    reference: str,
    *,
    price: str,
    quantity: str,
    total: str,
) -> None:
    portfolio, symbol = reference.split("/")
    _invoke(
        "asset",
        "sell",
        symbol,
        "-p",
        portfolio,
        "--price",
        price,
        "--quantity",
        quantity,
        "--total",
        total,
    )


def _income(reference: str, amount: str) -> None:
    portfolio, symbol = reference.split("/")
    _invoke("asset", "income", symbol, amount, "-p", portfolio)


def test_scenarios_a_through_d_preserve_complete_accounting(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _create_portfolio("stocks", "1000.00")
    _add_asset("stocks", "AAPL")

    _buy("stocks/AAPL", price="100", quantity="10", total="1000.00")

    asset = get_asset_summary("stocks", "AAPL", database_path)
    portfolio = get_portfolio_summary("stocks", database_path)
    assert asset.quantity == Decimal("10")
    assert asset.cost_basis_minor == 100_000
    assert asset.realized_pnl_minor == 0
    assert asset.income_minor == 0
    assert portfolio.capital_minor == 100_000
    assert portfolio.cash_minor == 0
    assert portfolio.positions_minor == 100_000
    assert portfolio.book_value_minor == 100_000
    assert portfolio.realized_pnl_minor == 0
    assert portfolio.income_minor == 0
    summary = _invoke("asset", "summary", "AAPL", "-p", "stocks")
    assert " 10 " in summary.output
    assert "1,000.00" in summary.output
    assert "100.00" in summary.output
    assert "0.00%" in summary.output

    _sell("stocks/AAPL", price="150", quantity="3", total="450.00")

    asset = get_asset_summary("stocks", "AAPL", database_path)
    portfolio = get_portfolio_summary("stocks", database_path)
    assert asset.quantity == Decimal("7")
    assert asset.cost_basis_minor == 70_000
    assert asset.realized_pnl_minor == 15_000
    assert asset.income_minor == 0
    assert portfolio.cash_minor == 45_000
    assert portfolio.positions_minor == 70_000
    assert portfolio.book_value_minor == 115_000
    assert portfolio.realized_pnl_minor == 15_000
    assert portfolio.income_minor == 0
    summary = _invoke("asset", "summary", "AAPL", "-p", "stocks")
    assert " 7 " in summary.output
    assert "700.00" in summary.output
    assert "100.00" in summary.output
    assert "150.00" in summary.output
    assert "15.00%" in summary.output
    portfolio_output = _invoke("portfolio", "show", "stocks")
    assert "15.00%" in portfolio_output.output

    _income("stocks/AAPL", "20.00")

    asset = get_asset_summary("stocks", "AAPL", database_path)
    portfolio = get_portfolio_summary("stocks", database_path)
    assert asset.quantity == Decimal("7")
    assert asset.cost_basis_minor == 70_000
    assert asset.realized_pnl_minor == 15_000
    assert asset.income_minor == 2_000
    assert portfolio.cash_minor == 47_000
    assert portfolio.positions_minor == 70_000
    assert portfolio.book_value_minor == 117_000
    assert portfolio.realized_pnl_minor == 15_000
    assert portfolio.income_minor == 2_000
    assert "17.00%" in _invoke("asset", "summary", "AAPL", "-p", "stocks").output
    assert "17.00%" in _invoke("portfolio", "show", "stocks").output

    _sell("stocks/AAPL", price="100", quantity="7", total="700.00")

    asset = get_asset_summary("stocks", "AAPL", database_path)
    portfolio = get_portfolio_summary("stocks", database_path)
    assert asset.quantity == Decimal("0")
    assert asset.cost_basis_minor == 0
    assert asset.realized_pnl_minor == 15_000
    assert asset.income_minor == 2_000
    assert portfolio.cash_minor == 117_000
    assert portfolio.positions_minor == 0
    assert portfolio.book_value_minor == 117_000
    summary = _invoke("asset", "summary", "AAPL", "-p", "stocks")
    row = next(line for line in summary.output.splitlines() if "150.00" in line)
    assert " 0 " in row
    assert "--" in row
    assert "20.00" in row
    assert "17.00%" in row

    with sqlite3.connect(database_path) as connection:
        buy_basis, relieved_basis, remaining_basis = connection.execute(
            """
            SELECT
                SUM(CASE WHEN transaction_type = 'buy'
                         THEN position_effect_minor ELSE 0 END),
                -SUM(CASE WHEN transaction_type = 'sell'
                          THEN position_effect_minor ELSE 0 END),
                SUM(position_effect_minor)
            FROM asset_transactions
            WHERE deleted_at IS NULL
            """
        ).fetchone()
    assert buy_basis == relieved_basis + remaining_basis
    assert remaining_basis == 0


def test_multiple_assets_are_isolated_and_portfolio_totals_are_additive(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _create_portfolio("stocks", "2000.00")
    _invoke("asset", "add", "AAPL", "MSFT", "-p", "stocks")
    _buy("stocks/AAPL", price="100", quantity="10", total="1000.00")
    _sell("stocks/AAPL", price="150", quantity="3", total="450.00")
    _income("stocks/AAPL", "20.00")
    _buy("stocks/MSFT", price="50", quantity="4", total="200.00")
    _sell("stocks/MSFT", price="80", quantity="1", total="80.00")
    _income("stocks/MSFT", "10.00")

    listed = {asset.symbol: asset for asset in get_assets("stocks", database_path)}
    aapl = get_asset_summary("stocks", "AAPL", database_path)
    msft = get_asset_summary("stocks", "MSFT", database_path)
    assert listed["AAPL"] == aapl
    assert listed["MSFT"] == msft
    assert (
        aapl.quantity,
        aapl.cost_basis_minor,
        aapl.realized_pnl_minor,
        aapl.income_minor,
        aapl.total_buy_cost_minor,
    ) == (Decimal("7"), 70_000, 15_000, 2_000, 100_000)
    assert (
        msft.quantity,
        msft.cost_basis_minor,
        msft.realized_pnl_minor,
        msft.income_minor,
        msft.total_buy_cost_minor,
    ) == (Decimal("3"), 15_000, 3_000, 1_000, 20_000)

    portfolio = get_portfolio_summary("stocks", database_path)
    assert (
        portfolio.capital_minor,
        portfolio.cash_minor,
        portfolio.positions_minor,
        portfolio.book_value_minor,
        portfolio.realized_pnl_minor,
        portfolio.income_minor,
    ) == (200_000, 136_000, 85_000, 221_000, 18_000, 3_000)
    assert "10.50%" in _invoke("portfolio", "show", "stocks").output
    assert "17.00%" in _invoke("asset", "summary", "AAPL", "-p", "stocks").output
    assert "20.00%" in _invoke("asset", "summary", "MSFT", "-p", "stocks").output


def test_same_symbol_is_isolated_by_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _create_portfolio("stocks", "1000.00")
    _create_portfolio("retirement", "500.00")
    _add_asset("stocks", "AAPL")
    _add_asset("retirement", "AAPL")
    _buy("stocks/AAPL", price="100", quantity="5", total="500.00")
    _income("stocks/AAPL", "10.00")
    _buy("retirement/AAPL", price="100", quantity="2", total="200.00")
    _sell("retirement/AAPL", price="150", quantity="1", total="150.00")

    stocks_asset = get_asset_summary("stocks", "AAPL", database_path)
    retirement_asset = get_asset_summary("retirement", "AAPL", database_path)
    assert (
        stocks_asset.quantity,
        stocks_asset.cost_basis_minor,
        stocks_asset.realized_pnl_minor,
        stocks_asset.income_minor,
    ) == (Decimal("5"), 50_000, 0, 1_000)
    assert (
        retirement_asset.quantity,
        retirement_asset.cost_basis_minor,
        retirement_asset.realized_pnl_minor,
        retirement_asset.income_minor,
    ) == (Decimal("1"), 10_000, 5_000, 0)

    summaries = {
        summary.portfolio_name: summary
        for summary in get_all_portfolio_summaries(database_path)
    }
    assert (
        summaries["stocks"].cash_minor,
        summaries["stocks"].positions_minor,
        summaries["stocks"].realized_pnl_minor,
        summaries["stocks"].income_minor,
    ) == (51_000, 50_000, 0, 1_000)
    assert (
        summaries["retirement"].cash_minor,
        summaries["retirement"].positions_minor,
        summaries["retirement"].realized_pnl_minor,
        summaries["retirement"].income_minor,
    ) == (45_000, 10_000, 5_000, 0)


def test_asset_delete_removes_only_its_effects_and_preserves_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _create_portfolio("stocks", "2000.00")
    _invoke("asset", "add", "AAPL", "MSFT", "-p", "stocks")
    _buy("stocks/AAPL", price="100", quantity="10", total="1000.00")
    _sell("stocks/AAPL", price="150", quantity="3", total="450.00")
    _income("stocks/AAPL", "20.00")
    _buy("stocks/MSFT", price="50", quantity="4", total="200.00")
    _sell("stocks/MSFT", price="80", quantity="1", total="80.00")
    _income("stocks/MSFT", "10.00")

    _invoke("asset", "delete", "AAPL", "-p", "stocks", "--yes")

    assert [asset.symbol for asset in get_assets("stocks", database_path)] == ["MSFT"]
    msft = get_asset_summary("stocks", "MSFT", database_path)
    assert (
        msft.quantity,
        msft.cost_basis_minor,
        msft.realized_pnl_minor,
        msft.income_minor,
    ) == (Decimal("3"), 15_000, 3_000, 1_000)
    portfolio = get_portfolio_summary("stocks", database_path)
    assert (
        portfolio.cash_minor,
        portfolio.positions_minor,
        portfolio.book_value_minor,
        portfolio.realized_pnl_minor,
        portfolio.income_minor,
    ) == (189_000, 15_000, 204_000, 3_000, 1_000)
    list_output = _invoke("asset", "summary", "-p", "stocks").output
    all_output = _invoke("portfolio", "list").output
    assert "AAPL" not in list_output
    assert "MSFT" in list_output
    assert "1,890.00" in all_output
    assert "150.00" in all_output

    deleted_summary = runner.invoke(app, ["asset", "summary", "AAPL", "-p", "stocks"])
    deleted_log = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])
    assert deleted_summary.exit_code == 1
    assert deleted_log.exit_code == 1

    with sqlite3.connect(database_path) as connection:
        asset_rows = connection.execute(
            "SELECT symbol, deleted_at FROM assets ORDER BY symbol"
        ).fetchall()
        transaction_rows = connection.execute(
            """
            SELECT a.symbol, COUNT(*),
                   SUM(CASE WHEN t.deleted_at IS NULL THEN 1 ELSE 0 END)
            FROM assets AS a
            JOIN asset_transactions AS t ON t.asset_id = a.id
            GROUP BY a.id, a.symbol
            ORDER BY a.symbol
            """
        ).fetchall()
    assert asset_rows[0][0] == "AAPL"
    assert asset_rows[0][1] is not None
    assert asset_rows[1] == ("MSFT", None)
    assert transaction_rows == [("AAPL", 3, 0), ("MSFT", 3, 3)]


def test_soft_deleted_transaction_is_excluded_from_every_read_model(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize(tmp_path, monkeypatch)
    _create_portfolio("stocks", "1000.00")
    _add_asset("stocks", "AAPL")
    _income("stocks/AAPL", "20.00")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE asset_transactions
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE transaction_type = 'income'
            """
        )

    listed = get_assets("stocks", database_path)[0]
    summary = get_asset_summary("stocks", "AAPL", database_path)
    portfolio = get_portfolio_summary("stocks", database_path)
    all_summaries = get_all_portfolio_summaries(database_path)
    assert listed == summary
    assert summary.income_minor == 0
    assert summary.quantity == 0
    assert summary.cost_basis_minor == 0
    assert portfolio.cash_minor == 100_000
    assert portfolio.book_value_minor == 100_000
    assert portfolio.income_minor == 0
    assert all_summaries == [portfolio]
    log_output = _invoke("asset", "log", "AAPL", "-p", "stocks").output
    assert "No active transactions" in log_output


def test_financial_modules_contain_no_float_arithmetic() -> None:
    project_root = Path(__file__).parents[1]
    modules = (
        "src/mpal/amounts.py",
        "src/mpal/numbers.py",
        "src/mpal/storage/asset_transactions.py",
        "src/mpal/storage/assets.py",
        "src/mpal/storage/summaries.py",
        "src/mpal/output/console.py",
    )

    for relative_path in modules:
        tree = ast.parse((project_root / relative_path).read_text(encoding="utf-8"))
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
        assert not float_literals, relative_path
        assert not float_calls, relative_path
