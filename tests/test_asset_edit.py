"""CLI and accounting tests for individual asset transaction editing."""

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
    initial: str = "1000",
) -> Path:
    data_dir = tmp_path / "mpal-data"
    monkeypatch.setenv("MPAL_DATA_DIR", str(data_dir))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert (
        runner.invoke(
            app,
            ["portfolio", "create", portfolio, "--initial", initial],
        ).exit_code
        == 0
    )
    assert runner.invoke(app, ["asset", "add", symbol, "-p", portfolio]).exit_code == 0
    return data_dir / "mpal.db"


def _buy(
    reference: str = "stocks/AAPL",
    *,
    price: str = "100",
    quantity: str = "1",
    total: str | None = None,
    date: str | None = None,
    note: str | None = None,
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
    if date is not None:
        args.extend(["--date", date])
    if note is not None:
        args.extend(["--note", note])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def _sell(
    reference: str = "stocks/AAPL",
    *,
    price: str = "150",
    quantity: str = "1",
    total: str | None = None,
    date: str | None = None,
    note: str | None = None,
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
    if date is not None:
        args.extend(["--date", date])
    if note is not None:
        args.extend(["--note", note])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def _income(
    reference: str = "stocks/AAPL",
    amount: str = "10",
    *,
    date: str | None = None,
    note: str | None = None,
) -> None:
    portfolio, symbol = reference.split("/", maxsplit=1)
    args = ["asset", "income", symbol, amount, "-p", portfolio]
    if date is not None:
        args.extend(["--date", date])
    if note is not None:
        args.extend(["--note", note])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


def _edit(entry_no: str = "1", *, reference: str = "stocks/AAPL", **options: str):
    portfolio, symbol = reference.split("/", maxsplit=1)
    args = ["asset", "entry", "edit", symbol, entry_no, "-p", portfolio]
    for name, value in options.items():
        args.extend([f"--{name.replace('_', '-')}", value])
    return runner.invoke(app, args)


def _rows(database_path: Path):
    with sqlite3.connect(database_path) as connection:
        return connection.execute(
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
            ORDER BY entry_no
            """
        ).fetchall()


def test_asset_edit_requires_initialized_database(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))

    result = _edit(amount="20")

    assert result.exit_code == 1
    assert "Run 'mpal init' first." in result.output
    assert "Traceback" not in result.output


def test_asset_edit_requires_active_portfolio(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))
    assert runner.invoke(app, ["init"]).exit_code == 0

    result = _edit(amount="20")

    assert result.exit_code == 1
    assert "Active portfolio 'stocks' does not exist." in result.output


def test_asset_edit_requires_active_asset(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("MPAL_DATA_DIR", str(tmp_path / "mpal-data"))
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["portfolio", "create", "stocks"]).exit_code == 0

    result = _edit(amount="20")

    assert result.exit_code == 1
    assert "Active asset 'AAPL' does not exist in portfolio 'stocks'." in result.output


def test_asset_edit_requires_active_transaction(tmp_path: Path, monkeypatch) -> None:
    _initialize_asset(tmp_path, monkeypatch)

    result = _edit("99", amount="20")

    assert result.exit_code == 1
    assert "Asset transaction 99 does not exist" in result.output


def test_asset_edit_rejects_deleted_transaction(tmp_path: Path, monkeypatch) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10")
    assert (
        runner.invoke(
            app,
            ["asset", "entry", "delete", "AAPL", "1", "-p", "stocks", "--yes"],
        ).exit_code
        == 0
    )

    result = _edit("1", amount="20")

    assert result.exit_code == 1
    assert "Asset transaction 1 is not active." in result.output


def test_asset_edit_rejects_no_options(tmp_path: Path, monkeypatch) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10")

    result = runner.invoke(app, ["asset", "entry", "edit", "AAPL", "1", "-p", "stocks"])

    assert result.exit_code == 1
    assert "Provide at least one" in result.output


def test_asset_edit_rejects_invalid_options_for_income(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10")

    result = _edit("1", price="2")

    assert result.exit_code == 1
    assert "Income transactions can edit only amount, date, or note." in result.output
    assert _rows(database_path)[0][6:11] == (1000, 1000, 0, 0, 1000)


def test_asset_edit_rejects_invalid_options_for_trades(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")

    result = _edit("1", amount="20")

    assert result.exit_code == 1
    assert "Trade transactions cannot edit --amount" in result.output
    assert _rows(database_path)[0][6:11] == (10_000, -10_000, 10_000, 0, 0)


def test_editing_income_amount_updates_asset_and_portfolio_summaries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10")

    result = _edit("1", amount="32")
    asset_summary = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])
    portfolio_show = runner.invoke(app, ["summary", "-p", "stocks"])

    assert result.exit_code == 0
    assert _rows(database_path)[0][6:11] == (3200, 3200, 0, 0, 3200)
    assert "32.00" in asset_summary.output
    row = next(line for line in portfolio_show.output.splitlines() if "stocks" in line)
    assert "1,032.00" in row
    assert "32.00" in row


def test_editing_income_date_and_note_updates_log_display(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10", date="2026-06-20", note="old")

    result = _edit("1", date="2026-06-19", note="new")
    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    assert "2026-06-19" in log_result.output
    assert "new" in log_result.output
    assert "old" not in log_result.output


def test_editing_buy_price_quantity_fee_updates_total_and_derived_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")

    result = _edit("1", price="50", quantity="3", fee="2.50")

    assert result.exit_code == 0
    assert _rows(database_path)[0][3:11] == (
        "50",
        "3",
        250,
        15_250,
        -15_250,
        15_250,
        0,
        0,
    )


def test_editing_buy_with_subcent_computed_total_requires_total(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")

    result = _edit("1", price="0.000533", quantity="0.0538")

    assert result.exit_code == 1
    assert "not exactly representable in minor units" in result.output
    assert _rows(database_path)[0][3:11] == (
        "100",
        "1",
        0,
        10_000,
        -10_000,
        10_000,
        0,
        0,
    )


def test_editing_buy_with_subcent_computed_total_accepts_explicit_total(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")

    result = _edit("1", price="0.000533", quantity="0.0538", total="0.01")

    assert result.exit_code == 0
    assert _rows(database_path)[0][3:11] == (
        "0.000533",
        "0.0538",
        0,
        1,
        -1,
        1,
        0,
        0,
    )


def test_editing_buy_rejects_mismatching_exact_total(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")

    result = _edit("1", total="99.99")

    assert result.exit_code == 1
    assert "does not match price × quantity + fee" in result.output
    assert _rows(database_path)[0][6:11] == (10_000, -10_000, 10_000, 0, 0)


def test_asset_edit_rejects_invalid_values_without_traceback_or_changes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")
    before = _rows(database_path)

    cases = (
        {"price": "invalid"},
        {"quantity": "0"},
        {"fee": "-1"},
        {"total": "0"},
        {"date": "2999-01-01"},
    )
    for options in cases:
        result = _edit("1", **options)
        assert result.exit_code == 1
        assert "Traceback" not in result.output
        assert _rows(database_path) == before


def test_editing_buy_that_would_make_later_sell_invalid_is_rejected(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2")
    _sell(quantity="2", total="300.00")

    result = _edit("1", quantity="1")

    assert result.exit_code == 1
    assert "cannot be edited" in result.output
    assert "active asset" in result.output
    assert "ledger invalid" in result.output
    assert _rows(database_path)[0][4:11] == (
        "2",
        0,
        20_000,
        -20_000,
        20_000,
        0,
        0,
    )
    assert _rows(database_path)[1][8:11] == (-20_000, 10_000, 0)


def test_editing_sell_price_quantity_fee_updates_pnl_and_summaries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="3")
    _sell(price="150", quantity="1")

    result = _edit("2", price="200", quantity="2", fee="5")
    asset_summary = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    assert _rows(database_path)[1][3:11] == (
        "200",
        "2",
        500,
        39_500,
        39_500,
        -20_000,
        19_500,
        0,
    )
    row = next(line for line in asset_summary.output.splitlines() if "1" in line)
    assert "100.00" in row
    assert "+195.00" in row


def test_editing_sell_quantity_above_open_quantity_is_rejected_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")
    _sell(quantity="1")

    result = _edit("2", quantity="2", total="300.00")

    assert result.exit_code == 1
    assert "cannot be edited" in result.output
    assert "active asset" in result.output
    assert "ledger invalid" in result.output
    assert _rows(database_path)[1][4:11] == (
        "1",
        0,
        15_000,
        15_000,
        -10_000,
        5_000,
        0,
    )


def test_editing_sell_to_full_sell_leaves_zero_cost_basis(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2")
    _sell(quantity="1")

    result = _edit("2", quantity="2", total="300.00")
    asset_summary = runner.invoke(app, ["summary", "-p", "stocks", "-a", "AAPL"])

    assert result.exit_code == 0
    row = next(line for line in asset_summary.output.splitlines() if "+100.00" in line)
    assert " 0 " in row
    assert "--" in row
    assert "+100.00" in row


def test_editing_date_changes_log_order_not_replay_order(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="2", date="2026-06-20", note="buy")
    _sell(quantity="1", date="2026-06-21", note="sell")

    result = _edit("2", date="2026-06-19")
    log_result = runner.invoke(app, ["asset", "log", "AAPL", "-p", "stocks"])

    assert result.exit_code == 0
    assert log_result.output.index("sell") < log_result.output.index("buy")
    assert _rows(database_path)[1][8:11] == (-10_000, 5_000, 0)


def test_editing_note_only_preserves_accounting_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1", note="old")
    before = _rows(database_path)[0][6:11]

    result = _edit("1", note="new")

    assert result.exit_code == 0
    row = _rows(database_path)[0]
    assert row[6:11] == before
    assert row[11] == "new"


def test_edit_failure_is_atomic_on_replay_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _buy(quantity="1")
    _sell(quantity="1")
    before = _rows(database_path)

    result = _edit("1", quantity="0.5", total="50.00")

    assert result.exit_code == 1
    assert _rows(database_path) == before


def test_asset_edit_preserves_entry_numbers(tmp_path: Path, monkeypatch) -> None:
    database_path = _initialize_asset(tmp_path, monkeypatch)
    _income(amount="10")
    _buy(quantity="1")

    result = _edit("2", note="changed")

    assert result.exit_code == 0
    assert [row[0] for row in _rows(database_path)] == [1, 2]


def test_asset_edit_does_not_affect_other_assets(tmp_path: Path, monkeypatch) -> None:
    _initialize_asset(tmp_path, monkeypatch)
    assert runner.invoke(app, ["asset", "add", "MSFT", "-p", "stocks"]).exit_code == 0
    _income("stocks/AAPL", "10")
    _income("stocks/MSFT", "20")

    result = _edit("1", amount="30", reference="stocks/AAPL")
    assets = runner.invoke(app, ["asset", "list", "-p", "stocks"])

    assert result.exit_code == 0
    assert "30.00" in assets.output
    assert "20.00" in assets.output


def test_asset_edit_does_not_affect_other_portfolios(
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

    result = _edit("1", amount="30", reference="stocks/AAPL")
    summaries = runner.invoke(app, ["portfolio", "list"])

    assert result.exit_code == 0
    stocks_row = next(
        line for line in summaries.output.splitlines() if "stocks" in line
    )
    retirement_row = next(
        line for line in summaries.output.splitlines() if "retirement" in line
    )
    assert "1,030.00" in stocks_row
    assert "30.00" in stocks_row
    assert "520.00" in retirement_row
    assert "20.00" in retirement_row
