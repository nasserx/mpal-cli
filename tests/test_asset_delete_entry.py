"""CLI and accounting tests for individual asset transaction deletion."""

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from mpal.cli import app

runner = CliRunner()


def _initialize_asset(
    tmp_path: Path,
    monkeypatch,
    portfolio: str = "stocks",
    symbol: str = "AAPL",
    *,
    initial: str | None = "1000",
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
    *,
    price: str = "100",
    quantity: str = "1",
    total: str | None = None,
) -> None:
    portfolio, symbol = reference.split("/", maxsplit=1)
    args = [
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
        args.extend(["--total", total])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def _sell(
    reference: str = "stocks/AAPL",
    *,
    price: str = "150",
    quantity: str = "1",
    total: str | None = None,
) -> None:
    portfolio, symbol = reference.split("/", maxsplit=1)
    args = [
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
    if total is not None:
        args.extend(["--total", total])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def _income(reference: str = "stocks/AAPL", amount: str = "10") -> None:
    portfolio, symbol = reference.split("/", maxsplit=1)
    result = runner.invoke(app, ["asset", "income", symbol, amount, "-p", portfolio])
    assert result.exit_code == 0, result.output


def _delete_entry(
    entry_no: str = "1",
    *,
    reference: str = "stocks/AAPL",
    yes: bool = True,
):
    portfolio, symbol = reference.split("/", maxsplit=1)
    args = ["asset", "entry", "delete", symbol, entry_no, "-p", portfolio]
    if yes:
        args.append("--yes")
    return runner.invoke(app, args)


def _asset_rows(database_path: Path):
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
            """
            SELECT
                entry_no,
                transaction_type,
                cash_effect_minor,
                position_effect_minor,
                realized_pnl_minor,
                income_minor,
                deleted_at
            FROM asset_transactions
            ORDER BY entry_no
            """
        ).fetchall()


def test_delete_entry_requires_initialized_database(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))

    result = _delete_entry()

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert "Traceback" not in result.output


def test_delete_entry_requires_active_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = _delete_entry()

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_delete_entry_requires_active_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["portfolio", "create", "stocks"]).exit_code == 0

    result = _delete_entry()

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in result.output


def test_delete_entry_requires_active_transaction(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    missing = _delete_entry("99")

    assert missing.exit_code == 1
    assert "Asset transaction 99 does not exist" in missing.output

    _income(amount="10")
    first_delete = _delete_entry("1")
    second_delete = _delete_entry("1")

    assert first_delete.exit_code == 0
    assert second_delete.exit_code == 1
    assert "Asset transaction 1 is not active." in second_delete.output


def test_delete_entry_requires_yes_and_without_yes_changes_nothing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10")

    result = _delete_entry("1", yes=False)

    assert result.exit_code == 1
    assert "requires the --yes confirmation flag" in result.output
    assert _asset_rows(database_path) == [(1, "income", 1000, 0, 0, 1000, None)]


def test_delete_entry_soft_deletes_income_transaction_and_updates_summaries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _income(amount="32")

    result = _delete_entry("1")
    asset_summary = runner.invoke(app, ["asset", "show", "AAPL", "-p", "stocks"])
    portfolio_show = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 0
    assert "Asset transaction 1 deleted" in result.output
    row = _asset_rows(database_path)[0]
    assert row[:6] == (1, "income", 3200, 0, 0, 3200)
    assert row[6] is not None
    assert "32.00" not in asset_summary.output
    portfolio_row = next(
        line for line in portfolio_show.output.splitlines() if "stocks" in line
    )
    assert portfolio_row.count("1,000.00") == 3
    assert "32.00" not in portfolio_row


def test_delete_entry_soft_deletes_buy_with_no_dependent_sells(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2")

    result = _delete_entry("1")
    asset_summary = runner.invoke(app, ["asset", "show", "AAPL", "-p", "stocks"])
    portfolio_show = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 0
    row = _asset_rows(database_path)[0]
    assert row[:6] == (1, "buy", -20_000, 20_000, 0, 0)
    assert row[6] is not None
    assert " 2 " not in asset_summary.output
    assert "200.00" not in asset_summary.output
    portfolio_row = next(
        line for line in portfolio_show.output.splitlines() if "stocks" in line
    )
    assert portfolio_row.count("1,000.00") == 3
    assert "200.00" not in portfolio_row


def test_delete_entry_rejects_buy_when_later_sell_would_be_invalid(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")
    _sell(quantity="1")

    result = _delete_entry("1")

    assert result.exit_code == 1
    assert "cannot be deleted" in result.output
    assert "remaining asset" in result.output
    assert "ledger invalid" in result.output
    assert _asset_rows(database_path) == [
        (1, "buy", -10_000, 10_000, 0, 0, None),
        (2, "sell", 15_000, -10_000, 5_000, 0, None),
    ]


def test_delete_entry_soft_deletes_sell_and_restores_open_position(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2")
    _sell(quantity="1")

    result = _delete_entry("2")
    asset_summary = runner.invoke(app, ["asset", "show", "AAPL", "-p", "stocks"])
    portfolio_show = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 0
    assert _asset_rows(database_path)[1][:6] == (2, "sell", 15_000, -10_000, 5_000, 0)
    assert _asset_rows(database_path)[1][6] is not None
    row = next(line for line in asset_summary.output.splitlines() if "2" in line)
    assert "200.00" in row
    assert "+50.00" not in row
    portfolio_row = next(
        line for line in portfolio_show.output.splitlines() if "stocks" in line
    )
    assert "800.00" in portfolio_row
    assert "200.00" in portfolio_row
    assert "50.00" not in portfolio_row


def test_delete_entry_full_sell_restores_open_position(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2")
    _sell(quantity="2", total="300.00")

    result = _delete_entry("2")
    asset_summary = runner.invoke(app, ["asset", "show", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    row = next(line for line in asset_summary.output.splitlines() if "2" in line)
    assert "200.00" in row
    assert "+100.00" not in row


def test_deleted_transaction_disappears_from_asset_log_and_numbers_are_stable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10")
    _buy(quantity="1")
    _income(amount="20")

    result = _delete_entry("2")
    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])
    _income(amount="30")

    assert result.exit_code == 0
    assert " 2 " not in log_result.output
    assert "10.00" in log_result.output
    assert "20.00" in log_result.output
    assert _asset_rows(database_path)[-1][:2] == (4, "income")


def test_remaining_transaction_derived_fields_are_replayed_after_delete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(price="0.005", quantity="2", total="0.01")
    _sell(price="0.01", quantity="1")
    _sell(price="0.01", quantity="1")

    result = _delete_entry("2")

    assert result.exit_code == 0
    assert _asset_rows(database_path) == [
        (1, "buy", -1, 1, 0, 0, None),
        (2, "sell", 1, 0, 1, 0, _asset_rows(database_path)[1][6]),
        (3, "sell", 1, 0, 1, 0, None),
    ]
    assert _asset_rows(database_path)[1][6] is not None


def test_deleting_one_asset_transaction_does_not_affect_another_asset(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    assert runner.invoke(app, ["asset", "add", "MSFT", "-p", "stocks"]).exit_code == 0
    _income("stocks/AAPL", "10")
    _income("stocks/MSFT", "20")

    result = _delete_entry("1", reference="stocks/AAPL")
    assets = runner.invoke(app, ["asset", "list", "-p", "stocks"])
    portfolio = runner.invoke(app, ["portfolio", "show", "stocks"])

    assert result.exit_code == 0
    assert "MSFT" in assets.output
    assert "20.00" in assets.output
    portfolio_row = next(
        line for line in portfolio.output.splitlines() if "stocks" in line
    )
    assert "1,020.00" in portfolio_row
    assert "20.00" in portfolio_row


def test_deleting_one_portfolio_asset_transaction_does_not_affect_another_portfolio(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    assert (
        runner.invoke(
            app,
            ["portfolio", "create", "retirement", "--initial", "500"],
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(app, ["asset", "add", "AAPL", "-p", "retirement"]).exit_code == 0
    )
    _income("stocks/AAPL", "10")
    _income("retirement/AAPL", "20")

    result = _delete_entry("1", reference="stocks/AAPL")
    summaries = runner.invoke(app, ["portfolio", "list"])

    assert result.exit_code == 0
    stocks_row = next(
        line for line in summaries.output.splitlines() if "stocks" in line
    )
    retirement_row = next(
        line for line in summaries.output.splitlines() if "retirement" in line
    )
    assert "1,000.00" in stocks_row
    assert "20.00" not in stocks_row
    assert "520.00" in retirement_row
    assert "20.00" in retirement_row


def test_asset_summary_and_portfolio_list_update_after_delete_entry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2")
    _sell(quantity="1")
    _income(amount="25")

    result = _delete_entry("2")
    asset_summary = runner.invoke(app, ["asset", "list", "-p", "stocks"])
    portfolio_list = runner.invoke(app, ["portfolio", "list"])

    assert result.exit_code == 0
    asset_row = next(
        line for line in asset_summary.output.splitlines() if "AAPL" in line
    )
    portfolio_row = next(
        line for line in portfolio_list.output.splitlines() if "stocks" in line
    )
    assert " 2 " in asset_row
    assert "200.00" in asset_row
    assert "25.00" in asset_row
    assert "825.00" in portfolio_row
    assert "200.00" in portfolio_row
    assert "25.00" in portfolio_row
