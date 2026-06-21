"""Focused tests for semantic financial output formatting."""

from datetime import date
from pathlib import Path

from typer.testing import CliRunner

from fundlog.cli import app
from fundlog.output import console as console_output
from fundlog.output.formatting import (
    format_capital_entry_amount,
    format_capital_entry_type,
    format_income_money,
    format_profit_loss_money,
    format_profit_loss_percent,
    format_signed_percent,
)
from fundlog.output.theme import INCOME, LOSS, PROFIT, TABLE_CELL
from fundlog.storage.asset_logs import AssetTransaction

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    *,
    initial: str = "1000",
) -> None:
    data_dir = tmp_path / "fundlog-data"
    monkeypatch.setenv("FUNDLOG_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["portfolio", "create", "stocks", "--initial", initial],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["asset", "add", "AAPL", "-p", "stocks"]).exit_code == 0


def _buy(*, price: str, quantity: str) -> None:
    result = runner.invoke(
        app,
        [
            "asset",
            "buy",
            "AAPL",
            "-p",
            "stocks",
            "--price",
            price,
            "--quantity",
            quantity,
        ],
    )
    assert result.exit_code == 0


def _sell(*, price: str, quantity: str) -> None:
    result = runner.invoke(
        app,
        [
            "asset",
            "sell",
            "AAPL",
            "-p",
            "stocks",
            "--price",
            price,
            "--quantity",
            quantity,
        ],
    )
    assert result.exit_code == 0


def test_asset_outputs_omit_standalone_title_and_keep_tables(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")

    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])
    summary_result = runner.invoke(app, ["asset", "summary", "AAPL", "-p", "stocks"])

    for result in (log_result, summary_result):
        assert result.exit_code == 0
        assert "AAPL/stocks" not in result.output

    assert "Date" in log_result.output
    assert "Type" in log_result.output
    assert "100.00" in log_result.output
    assert "Quantity" in summary_result.output
    assert "Cost Basis" in summary_result.output
    assert "100.00" in summary_result.output


def test_positive_profit_and_returns_show_explicit_plus_sign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")
    _sell(price="150", quantity="1")

    asset_list = runner.invoke(app, ["asset", "summary", "-p", "stocks"])
    asset_summary = runner.invoke(app, ["asset", "summary", "AAPL", "-p", "stocks"])
    portfolio = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert "+50.00" in asset_list.output
    assert "+50.00%" in asset_list.output
    assert "+50.00" in asset_summary.output
    assert "+50.00%" in asset_summary.output
    assert "+50.00" in portfolio.output
    assert "+5.00%" in portfolio.output


def test_negative_profit_and_returns_keep_minus_sign(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")
    _sell(price="80", quantity="1")

    asset_summary = runner.invoke(app, ["asset", "summary", "AAPL", "-p", "stocks"])
    portfolio = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert "-20.00" in asset_summary.output
    assert "-20.00%" in asset_summary.output
    assert "-20.00" in portfolio.output
    assert "-2.00%" in portfolio.output


def test_zero_profit_and_returns_remain_unsigned(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="1")

    asset_summary = runner.invoke(app, ["asset", "summary", "AAPL", "-p", "stocks"])
    portfolio = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert "+0.00" not in asset_summary.output
    assert "+0.00%" not in asset_summary.output
    assert "+0.00" not in portfolio.output
    assert "+0.00%" not in portfolio.output
    assert "0.00%" in asset_summary.output
    assert "0.00%" in portfolio.output


def test_semantic_result_helpers_use_reusable_theme_styles() -> None:
    assert format_profit_loss_money(1).style == PROFIT
    assert format_profit_loss_money(-1).style == LOSS
    assert format_profit_loss_money(0).style == TABLE_CELL
    assert format_profit_loss_percent(1, 100).style == PROFIT
    assert format_profit_loss_percent(-1, 100).style == LOSS
    assert format_profit_loss_percent(0, 100).style == TABLE_CELL
    assert format_profit_loss_percent(1, -100).style == LOSS
    assert format_profit_loss_percent(-1, -100).style == PROFIT
    assert format_income_money(1).style == INCOME


def test_capital_log_styles_withdrawals_only() -> None:
    assert format_capital_entry_type("outflow").plain == "withdraw"
    assert format_capital_entry_type("outflow").style == LOSS
    assert format_capital_entry_amount("outflow", 25_000).plain == "250.00"
    assert format_capital_entry_amount("outflow", 25_000).style == LOSS

    assert format_capital_entry_type("inflow").plain == "deposit"
    assert format_capital_entry_type("inflow").style == TABLE_CELL
    assert format_capital_entry_amount("inflow", 100_000).plain == "1,000.00"
    assert format_capital_entry_amount("inflow", 100_000).style == TABLE_CELL


def test_signed_percent_uses_exact_formula_and_neutral_zero() -> None:
    assert format_signed_percent(1700, 10_000) == "+17.00%"
    assert format_signed_percent(-1700, 10_000) == "-17.00%"
    assert format_signed_percent(0, 10_000) == "0.00%"
    assert format_signed_percent(1700, 0) == "0.00%"


def test_asset_log_styles_only_income_total_as_income(
    monkeypatch,
) -> None:
    styled_amounts: list[int] = []

    def record_income_style(amount_minor: int):
        styled_amounts.append(amount_minor)
        return format_income_money(amount_minor)

    monkeypatch.setattr(console_output, "format_income_money", record_income_style)
    transactions = [
        AssetTransaction(
            1, date.today().isoformat(), "buy", "100", "1", 0, 10_000, None
        ),
        AssetTransaction(
            2, date.today().isoformat(), "sell", "110", "1", 0, 11_000, None
        ),
        AssetTransaction(
            3, date.today().isoformat(), "income", None, None, 0, 500, None
        ),
    ]

    console_output.print_asset_transaction_log("stocks", "AAPL", transactions)

    assert styled_amounts == [500]


def test_buy_sell_income_formulas_remain_correct_with_signed_display(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(price="100", quantity="10")
    _sell(price="150", quantity="3")
    assert (
        runner.invoke(app, ["asset", "income", "AAPL", "20", "-p", "stocks"]).exit_code
        == 0
    )

    asset_summary = runner.invoke(app, ["asset", "summary", "AAPL", "-p", "stocks"])
    portfolio = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert "+150.00" in asset_summary.output
    assert "20.00" in asset_summary.output
    assert "+17.00%" in asset_summary.output
    assert "+150.00" in portfolio.output
    assert "20.00" in portfolio.output
    assert "+17.00%" in portfolio.output
